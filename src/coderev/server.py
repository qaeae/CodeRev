"""Minimal HTTP server: health endpoints + GitHub webhook receiver.

Standard library only. The webhook handler verifies the HMAC signature before
touching anything, then hands off to the delivery store (dedupe) — actual
review execution lands in the next PR.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

from . import __version__
from .serverconfig import SettingsProvider
from .store import DeliveryStore
from .webhook import (
    DELIVERY_HEADER,
    EVENT_HEADER,
    SIGNATURE_HEADER,
    is_allowed,
    parse_event,
    verify_signature,
)

MAX_BODY_BYTES = 1024 * 1024  # 1 MiB
Routes = dict[str, Callable[[], dict]]


def _make_handler(
    routes: Routes,
    settings_provider: SettingsProvider,
    store: DeliveryStore,
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = f"coderev/{__version__}"

        # ---------------------------------------------------------- GET
        def do_GET(self) -> None:  # noqa: N802 - http.server API
            path = self.path.split("?", 1)[0]
            route = routes.get(path)
            if route is None:
                self._send(404, {"error": "not found", "path": path})
                return
            self._send(200, route())

        # --------------------------------------------------------- POST
        def do_POST(self) -> None:  # noqa: N802 - http.server API
            path = self.path.split("?", 1)[0]
            if path != "/webhook":
                self._send(404, {"error": "not found", "path": path})
                return

            try:
                length = int(self.headers.get("Content-Length") or "0")
            except ValueError:
                self._send(400, {"error": "invalid content-length"})
                return

            if length <= 0:
                self._send(400, {"error": "empty body"})
                return
            if length > MAX_BODY_BYTES:
                self._send(413, {"error": "payload too large", "limit": MAX_BODY_BYTES})
                return

            self._handle_webhook(self.rfile.read(length))

        def _handle_webhook(self, body: bytes) -> None:
            secret = os.environ.get("CODEREV_WEBHOOK_SECRET", "")
            if not secret:
                self._send(503, {"error": "webhook secret not configured"})
                return

            if not verify_signature(secret, body, self.headers.get(SIGNATURE_HEADER)):
                self._send(401, {"error": "invalid signature"})
                return

            delivery = (self.headers.get(DELIVERY_HEADER) or "").strip()
            if not delivery:
                self._send(400, {"error": f"missing {DELIVERY_HEADER}"})
                return

            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send(400, {"error": "invalid json"})
                return

            event, reason = parse_event(self.headers.get(EVENT_HEADER), payload, delivery)
            if event is None:
                self.log_reason(reason)
                self._send(204, None)
                return

            settings = settings_provider.get()
            if not is_allowed(event.repo, settings.repos):
                self.log_reason(f"{event.repo} 不在白名单")
                self._send(204, None)
                return

            if store.is_duplicate(event.delivery):
                self._send(200, {"status": "duplicate", "delivery": delivery})
                return

            store.record(event)
            self._send(
                202,
                {
                    "status": "accepted",
                    "delivery": delivery,
                    "repo": event.repo,
                    "pr": event.number,
                    "head_sha": event.head_sha,
                },
            )

        # -------------------------------------------------------- helpers
        def log_reason(self, reason: str) -> None:
            print(f"webhook skipped: {reason}", flush=True)

        def _send(self, status: int, payload: dict | None) -> None:
            data = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            if payload is not None:
                self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if data:
                self.wfile.write(data)

        def log_message(self, fmt: str, *args) -> None:  # pragma: no cover
            pass

    return Handler


def create_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    *,
    settings_provider: SettingsProvider | None = None,
    store: DeliveryStore | None = None,
) -> ThreadingHTTPServer:
    provider = settings_provider or SettingsProvider()
    delivery_store = store or DeliveryStore(":memory:")
    routes: Routes = {
        "/healthz": lambda: {"status": "ok", "version": __version__},
        "/readyz": lambda: {
            "status": "ready",
            "version": __version__,
            "deliveries": delivery_store.count(),
        },
    }
    return ThreadingHTTPServer((host, port), _make_handler(routes, provider, delivery_store))
