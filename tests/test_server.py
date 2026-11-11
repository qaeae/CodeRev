"""HTTP server smoke tests — no network beyond localhost."""

import hashlib
import hmac
import http.client
import json
import threading
import urllib.error
import urllib.request

import pytest

from coderev.server import create_server
from coderev.serverconfig import SettingsProvider
from coderev.store import DeliveryStore

SECRET = "test-secret"


def _sign(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def server():
    srv = create_server("127.0.0.1", 0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)


def _url(server, path: str) -> str:
    host, port = server.server_address
    return f"http://{host}:{port}{path}"


def test_healthz(server):
    with urllib.request.urlopen(_url(server, "/healthz"), timeout=5) as response:
        assert response.status == 200
        assert response.headers["Content-Type"].startswith("application/json")
        payload = json.loads(response.read())

    assert payload["status"] == "ok"
    assert payload["version"]


def test_readyz(server):
    with urllib.request.urlopen(_url(server, "/readyz"), timeout=5) as response:
        payload = json.loads(response.read())

    assert payload["status"] == "ready"


def test_unknown_route_returns_404(server):
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(_url(server, "/nope"), timeout=5)

    assert exc.value.code == 404
    payload = json.loads(exc.value.read())
    assert payload["error"] == "not found"


def test_query_string_is_ignored(server):
    with urllib.request.urlopen(_url(server, "/healthz?probe=1"), timeout=5) as response:
        assert json.loads(response.read())["status"] == "ok"


# ---------------------------------------------------------------- webhook


def _post(server, body: bytes, headers: dict[str, str]) -> tuple[int, bytes]:
    host, port = server.server_address
    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        conn.request("POST", "/webhook", body=body, headers=headers)
        response = conn.getresponse()
        return response.status, response.read()
    finally:
        conn.close()


def _headers(
    body: bytes,
    *,
    event: str = "pull_request",
    delivery: str = "d-1",
    signature: str | None = None,
) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-GitHub-Event": event,
        "X-GitHub-Delivery": delivery,
        "X-Hub-Signature-256": signature if signature is not None else _sign(body),
    }


def _payload(**overrides) -> bytes:
    data = {
        "action": "opened",
        "number": 7,
        "repository": {"full_name": "acme/project"},
        "pull_request": {"draft": False, "head": {"sha": "abc123"}},
    }
    data.update(overrides)
    return json.dumps(data).encode()


@pytest.fixture
def webhook_server(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEREV_WEBHOOK_SECRET", SECRET)
    config = tmp_path / "server.yml"
    config.write_text("repos:\n  - acme/project\n", encoding="utf-8")

    store = DeliveryStore(":memory:")
    srv = create_server(
        "127.0.0.1", 0, settings_provider=SettingsProvider(config), store=store
    )
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)
        store.close()


def test_webhook_without_secret_returns_503(server, monkeypatch):
    monkeypatch.delenv("CODEREV_WEBHOOK_SECRET", raising=False)
    body = _payload()
    status, _ = _post(server, body, _headers(body))
    assert status == 503


def test_webhook_rejects_bad_signature(webhook_server):
    body = _payload()
    status, _ = _post(webhook_server, body, _headers(body, signature="sha256=deadbeef"))
    assert status == 401


def test_webhook_accepts_valid_delivery(webhook_server):
    body = _payload()
    status, raw = _post(webhook_server, body, _headers(body))

    assert status == 202
    data = json.loads(raw)
    assert data["status"] == "accepted"
    assert data["repo"] == "acme/project"
    assert data["pr"] == 7


def test_webhook_is_idempotent(webhook_server):
    body = _payload()
    headers = _headers(body)

    assert _post(webhook_server, body, headers)[0] == 202
    status, raw = _post(webhook_server, body, headers)

    assert status == 200
    assert json.loads(raw)["status"] == "duplicate"


def test_webhook_ignores_repo_outside_allowlist(webhook_server):
    body = _payload(repository={"full_name": "evil/repo"})
    status, _ = _post(webhook_server, body, _headers(body, delivery="d-evil"))
    assert status == 204


def test_webhook_ignores_draft(webhook_server):
    body = _payload(pull_request={"draft": True, "head": {"sha": "abc"}})
    status, _ = _post(webhook_server, body, _headers(body, delivery="d-draft"))
    assert status == 204


def test_webhook_ignores_other_events(webhook_server):
    body = _payload()
    status, _ = _post(webhook_server, body, _headers(body, event="issues", delivery="d-9"))
    assert status == 204


class FakeWorker:
    def __init__(self) -> None:
        self.jobs = []

    def submit(self, job) -> None:
        self.jobs.append(job)


def test_webhook_enqueues_review_job(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEREV_WEBHOOK_SECRET", SECRET)
    config = tmp_path / "server.yml"
    config.write_text("repos:\n  - acme/project\n", encoding="utf-8")

    worker = FakeWorker()
    store = DeliveryStore(":memory:")
    srv = create_server(
        "127.0.0.1",
        0,
        settings_provider=SettingsProvider(config),
        store=store,
        worker=worker,
    )
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        body = _payload()
        status, _ = _post(srv, body, _headers(body, delivery="d-queue"))
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)
        store.close()

    assert status == 202
    assert len(worker.jobs) == 1
    assert worker.jobs[0].number == 7
    assert worker.jobs[0].repo == "acme/project"
