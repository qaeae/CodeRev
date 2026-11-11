"""Minimal GitHub REST client.

No SDK dependency on purpose: the surface we need is four endpoints, and a
hand-rolled client keeps install time near zero (important for GitHub Actions).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

# transport(method, url, headers, body) -> (status, body_bytes)
Transport = Callable[[str, str, dict[str, str], bytes | None], tuple[int, bytes]]


class GitHubError(RuntimeError):
    """Any non-2xx response, with enough context to debug."""


def _default_transport(
    method: str, url: str, headers: dict[str, str], body: bytes | None
) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


@dataclass
class GitHubClient:
    repo: str
    token: str
    api_url: str = "https://api.github.com"
    transport: Transport | None = None

    def __post_init__(self) -> None:
        if "/" not in self.repo:
            raise ValueError(f"repo 必须是 owner/name 格式：{self.repo!r}")
        if not self.token:
            raise ValueError("缺少 GitHub token（设置 GITHUB_TOKEN）")

    # ------------------------------------------------------------------ http
    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        accept: str = "application/vnd.github+json",
    ) -> bytes:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": accept,
            "User-Agent": "coderev",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        status, raw = (self.transport or _default_transport)(
            method, f"{self.api_url}{path}", headers, body
        )
        if status >= 400:
            raise GitHubError(f"{method} {path} -> {status}: {raw[:300]!r}")
        return raw

    # ------------------------------------------------------------------- api
    def get_pull(self, number: int) -> dict[str, Any]:
        return json.loads(self._request("GET", f"/repos/{self.repo}/pulls/{number}"))

    def get_diff(self, number: int) -> str:
        raw = self._request(
            "GET",
            f"/repos/{self.repo}/pulls/{number}",
            accept="application/vnd.github.v3.diff",
        )
        return raw.decode("utf-8", errors="replace")

    def list_issue_comments(self, number: int) -> list[dict[str, Any]]:
        return json.loads(
            self._request("GET", f"/repos/{self.repo}/issues/{number}/comments?per_page=100")
        )

    def create_issue_comment(self, number: int, body: str) -> dict[str, Any]:
        return json.loads(
            self._request("POST", f"/repos/{self.repo}/issues/{number}/comments", {"body": body})
        )

    def update_issue_comment(self, comment_id: int, body: str) -> dict[str, Any]:
        return json.loads(
            self._request(
                "PATCH", f"/repos/{self.repo}/issues/comments/{comment_id}", {"body": body}
            )
        )

    def list_review_comments(self, number: int) -> list[dict[str, Any]]:
        return json.loads(
            self._request("GET", f"/repos/{self.repo}/pulls/{number}/comments?per_page=100")
        )

    def create_review_comment(
        self, number: int, *, commit_id: str, path: str, line: int, body: str
    ) -> dict[str, Any]:
        return json.loads(
            self._request(
                "POST",
                f"/repos/{self.repo}/pulls/{number}/comments",
                {"body": body, "commit_id": commit_id, "path": path, "line": line, "side": "RIGHT"},
            )
        )

    def delete_review_comment(self, comment_id: int) -> None:
        self._request("DELETE", f"/repos/{self.repo}/pulls/comments/{comment_id}")
