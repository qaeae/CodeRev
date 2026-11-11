"""Minimal HTTP server.

v0.3 only ships health endpoints; the webhook route arrives with the
self-hosted service task (#3). Standard library only — the container image
should stay small and dependency-free.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

from . import __version__

Routes = dict[str, Callable[[], dict]]


def _make_handler(routes: Routes) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = f"coderev/{__version__}"

        def do_GET(self) -> None:  # noqa: N802 - http.server API
            path = self.path.split("?", 1)[0]
            route = routes.get(path)
            if route is None:
                self._send(404, {"error": "not found", "path": path})
                return
            self._send(200, route())

        def _send(self, status: int, payload: dict) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt: str, *args) -> None:  # pragma: no cover
            # 默认日志会打到 stderr，容器里交给编排层收集
            pass

    return Handler


def create_server(host: str = "0.0.0.0", port: int = 8080) -> ThreadingHTTPServer:
    routes: Routes = {
        "/healthz": lambda: {"status": "ok", "version": __version__},
        "/readyz": lambda: {"status": "ready", "version": __version__},
    }
    return ThreadingHTTPServer((host, port), _make_handler(routes))


def serve(host: str = "0.0.0.0", port: int = 8080) -> None:
    server = create_server(host, port)
    print(f"coderev {__version__} listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        server.server_close()
