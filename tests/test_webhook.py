"""Webhook verification and event parsing — the security boundary."""

import hashlib
import hmac

from coderev.webhook import is_allowed, parse_event, verify_signature

SECRET = "s3cr3t"
BODY = b'{"action":"opened"}'
PAYLOAD = {
    "action": "opened",
    "number": 7,
    "repository": {"full_name": "Acme/Project"},
    "pull_request": {"draft": False, "head": {"sha": "abc123"}},
}


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_valid_signature():
    assert verify_signature(SECRET, BODY, _sign(SECRET, BODY)) is True


def test_tampered_body_fails():
    assert verify_signature(SECRET, BODY + b" ", _sign(SECRET, BODY)) is False


def test_wrong_secret_fails():
    assert verify_signature("other", BODY, _sign(SECRET, BODY)) is False


def test_missing_signature_fails():
    assert verify_signature(SECRET, BODY, None) is False
    assert verify_signature(SECRET, BODY, "") is False


def test_non_sha256_prefix_fails():
    assert verify_signature(SECRET, BODY, "sha1=deadbeef") is False


def test_empty_secret_fails():
    assert verify_signature("", BODY, _sign("", BODY)) is False


# ---------------------------------------------------------------- parsing


def test_accepts_pull_request_opened():
    event, reason = parse_event("pull_request", PAYLOAD, "delivery-1")
    assert reason == "ok"
    assert event is not None
    assert event.repo == "Acme/Project"
    assert event.number == 7
    assert event.head_sha == "abc123"
    assert event.delivery == "delivery-1"


def test_ignores_other_event_types():
    event, reason = parse_event("issues", PAYLOAD, "d")
    assert event is None
    assert "事件类型" in reason


def test_ignores_unrelated_actions():
    payload = dict(PAYLOAD, action="labeled")
    event, reason = parse_event("pull_request", payload, "d")
    assert event is None
    assert "action" in reason


def test_skips_draft():
    payload = dict(PAYLOAD, pull_request={"draft": True, "head": {"sha": "abc"}})
    event, reason = parse_event("pull_request", payload, "d")
    assert event is None
    assert "draft" in reason


def test_missing_fields_are_ignored():
    event, reason = parse_event("pull_request", {"action": "opened"}, "d")
    assert event is None
    assert "缺少" in reason


def test_allowlist_is_case_insensitive():
    assert is_allowed("Acme/Project", ("acme/project",)) is True
    assert is_allowed("acme/other", ("acme/project",)) is False
    assert is_allowed("acme/project", ()) is False
