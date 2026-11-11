"""HTTP server smoke tests — no network beyond localhost."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from coderev.server import create_server


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
