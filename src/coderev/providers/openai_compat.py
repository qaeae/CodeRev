"""OpenAI-compatible chat provider.

Works with OpenAI, DeepSeek, Moonshot, vLLM, Ollama (openai-compatible mode),
and anything else exposing `/chat/completions`.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .base import ProviderError


class OpenAICompatProvider:
    name = "openai-compatible"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 90,
    ) -> None:
        if not api_key:
            raise ProviderError("缺少 API key（设置 CODEREV_API_KEY）")
        if not model:
            raise ProviderError("缺少模型名（--model 或 CODEREV_MODEL）")

        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self._model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise ProviderError(f"模型接口返回 {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ProviderError(f"模型接口不可达: {exc}") from exc

        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"模型返回格式异常: {str(body)[:300]}") from exc
