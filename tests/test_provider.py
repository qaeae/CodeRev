"""Provider request-shape tests.

Locks the wire format for OpenAI-compatible endpoints (DeepSeek in particular),
so a config regression shows up in CI instead of in a failed workflow.
"""

import json
import urllib.request

import pytest

from coderev.providers import OpenAICompatProvider
from coderev.providers.base import ProviderError


class FakeResponse:
    status = 200

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_deepseek_url_and_payload(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data)
        captured["auth"] = request.get_header("Authorization")
        return FakeResponse(b'{"choices":[{"message":{"content":"{\\"summary\\":\\"ok\\"}"}}]}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    provider = OpenAICompatProvider(
        api_key="sk-test",
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1/",
    )
    assert provider.complete("system", "user") == '{"summary":"ok"}'

    assert captured["url"] == "https://api.deepseek.com/v1/chat/completions"
    assert captured["body"]["model"] == "deepseek-chat"
    assert captured["body"]["response_format"] == {"type": "json_object"}
    assert captured["auth"] == "Bearer sk-test"
    assert [m["role"] for m in captured["body"]["messages"]] == ["system", "user"]


def test_missing_key_fails_fast():
    with pytest.raises(ProviderError, match="API key"):
        OpenAICompatProvider(api_key="", model="deepseek-chat")


def test_missing_model_fails_fast():
    with pytest.raises(ProviderError, match="模型名"):
        OpenAICompatProvider(api_key="sk-test", model="")
