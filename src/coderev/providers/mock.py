"""Offline provider used by tests and `--provider mock`."""

from __future__ import annotations

import json
from pathlib import Path


class MockProvider:
    """Returns a canned response — no network, no key.

    This is what makes the whole pipeline testable in CI.
    """

    name = "mock"

    def __init__(self, response: str) -> None:
        self._response = response

    @classmethod
    def from_file(cls, path: str | Path) -> "MockProvider":
        payload = Path(path).read_text(encoding="utf-8")
        json.loads(payload)  # fail fast on bad fixtures
        return cls(payload)

    def complete(self, system: str, user: str) -> str:
        return self._response
