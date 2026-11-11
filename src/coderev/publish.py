"""Publish review results to a pull request.

Idempotency strategy (v0.2):
- one summary comment, found by a hidden marker, updated in place;
- inline findings recreated each run (stale ones deleted first).

Re-running on the same PR therefore converges instead of piling up comments.
"""

from __future__ import annotations

from dataclasses import dataclass

from .github import GitHubClient
from .models import Finding, ReviewResult
from .render import SEVERITY_LABEL, render_markdown

SUMMARY_MARKER = "<!-- coderev:summary -->"
FINDING_MARKER = "<!-- coderev:finding -->"


@dataclass
class PublishResult:
    summary_action: str
    inline_created: int
    inline_deleted: int


def finding_body(finding: Finding) -> str:
    parts = [f"**{SEVERITY_LABEL.get(finding.severity, finding.severity)}** {finding.title}"]
    if finding.detail:
        parts.append(finding.detail)
    if finding.suggestion:
        parts.extend(["**建议**", "```", finding.suggestion, "```"])
    parts.append(f"<sub>规则 `{finding.rule_id}` · 置信度 {finding.confidence:.0%}</sub>")
    parts.append(FINDING_MARKER)
    return "\n\n".join(parts)


def publish(
    client: GitHubClient,
    pr: int,
    result: ReviewResult,
    *,
    dropped: int = 0,
    truncated: bool = False,
    run_id: str = "",
) -> PublishResult:
    body = render_markdown(result, run_id=run_id, dropped=dropped, truncated=truncated)
    body = f"{body}\n{SUMMARY_MARKER}"

    existing = client.list_issue_comments(pr)
    summary = next((c for c in existing if SUMMARY_MARKER in (c.get("body") or "")), None)

    if summary:
        client.update_issue_comment(int(summary["id"]), body)
        summary_action = "updated"
    else:
        client.create_issue_comment(pr, body)
        summary_action = "created"

    stale = [c for c in client.list_review_comments(pr) if FINDING_MARKER in (c.get("body") or "")]
    for comment in stale:
        client.delete_review_comment(int(comment["id"]))

    commit_id = ""
    if result.findings:
        commit_id = str(client.get_pull(pr)["head"]["sha"])

    created = 0
    for finding in result.findings:
        client.create_review_comment(
            pr,
            commit_id=commit_id,
            path=finding.path,
            line=finding.line_start,
            body=finding_body(finding),
        )
        created += 1

    return PublishResult(
        summary_action=summary_action,
        inline_created=created,
        inline_deleted=len(stale),
    )
