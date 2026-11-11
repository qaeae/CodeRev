"""GitHub client tests — no network, transport is injected."""

import json

import pytest

from coderev.github import GitHubClient, GitHubError


class FakeTransport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, url, headers, body):
        self.calls.append({"method": method, "url": url, "headers": headers, "body": body})
        return self.responses.pop(0)


def _client(transport):
    return GitHubClient(repo="acme/demo", token="t0ken", transport=transport)


def test_repo_must_be_owner_name():
    with pytest.raises(ValueError):
        GitHubClient(repo="demo", token="x")


def test_token_required():
    with pytest.raises(ValueError):
        GitHubClient(repo="acme/demo", token="")


def test_get_diff_uses_diff_accept_header():
    transport = FakeTransport((200, b"diff --git a/x b/x\n"))
    diff = _client(transport).get_diff(12)

    assert diff.startswith("diff --git")
    call = transport.calls[0]
    assert call["method"] == "GET"
    assert call["url"].endswith("/repos/acme/demo/pulls/12")
    assert "v3.diff" in call["headers"]["Accept"]


def test_create_review_comment_payload():
    transport = FakeTransport((201, b'{"id": 1}'))
    _client(transport).create_review_comment(
        7, commit_id="abc123", path="src/a.py", line=5, body="hi"
    )

    call = transport.calls[0]
    payload = json.loads(call["body"])
    assert payload == {
        "body": "hi",
        "commit_id": "abc123",
        "path": "src/a.py",
        "line": 5,
        "side": "RIGHT",
    }


def test_error_response_raises_with_status():
    transport = FakeTransport((403, b'{"message":"forbidden"}'))
    with pytest.raises(GitHubError) as exc:
        _client(transport).get_pull(1)
    assert "403" in str(exc.value)


def test_update_issue_comment_patch():
    transport = FakeTransport((200, b'{"id": 9}'))
    _client(transport).update_issue_comment(9, "new body")
    call = transport.calls[0]
    assert call["method"] == "PATCH"
    assert call["url"].endswith("/repos/acme/demo/issues/comments/9")
