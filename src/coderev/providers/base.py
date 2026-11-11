"""Model providers. Bring your own key: CodeRev never ships a hosted model."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class ProviderError(RuntimeError):
    """Raised when a provider call fails in a way the caller should report."""


@runtime_checkable
class Provider(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str:  # pragma: no cover - protocol
        ...
