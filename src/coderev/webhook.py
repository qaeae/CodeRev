"""GitHub webhook verification and event parsing.

Pure functions only: no I/O, no globals. That is what makes the security
boundary testable without a running server.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any

SIGNATURE_HEADER = "X-Hub-Signature-256"
EVENT_HEADER = "X-GitHub-Event"
DELIVERY_HEADER = "X-GitHub-Delivery"

# 触发审查的 action；其余（labeled/edited/closed…）一律忽略
PR_ACTIONS = frozenset({"opened", "synchronize", "reopened", "ready_for_review"})


def verify_signature(secret: str, body: bytes, signature: str | None) -> bool:
    """Constant-time check of `sha256=<hex>` against the raw body."""
    if not secret or not signature:
        return False

    signature = signature.strip()
    if not signature.startswith("sha256="):
        return False

    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={digest}", signature)


def is_allowed(repo: str, allowed: tuple[str, ...]) -> bool:
    """Case-insensitive match against the server-side allowlist."""
    target = repo.lower()
    return any(target == item.lower() for item in allowed)


@dataclass(frozen=True)
class PullRequestEvent:
    delivery: str
    repo: str
    number: int
    head_sha: str
    action: str


def parse_event(
    event_type: str | None,
    payload: dict[str, Any],
    delivery: str,
) -> tuple[PullRequestEvent | None, str]:
    """Return (event, reason). `event is None` means "ignore quietly"."""
    if event_type != "pull_request":
        return None, f"忽略事件类型 {event_type!r}"

    action = str(payload.get("action") or "")
    if action not in PR_ACTIONS:
        return None, f"忽略 action {action!r}"

    pull_request = payload.get("pull_request") or {}
    if pull_request.get("draft"):
        return None, "draft PR 跳过"

    repo = str((payload.get("repository") or {}).get("full_name") or "")
    number = payload.get("number") or pull_request.get("number")
    head_sha = str((pull_request.get("head") or {}).get("sha") or "")

    if not repo or not number or not head_sha:
        return None, "payload 缺少必要字段（repository / number / head.sha）"

    return (
        PullRequestEvent(
            delivery=delivery,
            repo=repo,
            number=int(number),
            head_sha=head_sha,
            action=action,
        ),
        "ok",
    )
