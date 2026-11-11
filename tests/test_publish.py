"""Publishing tests — idempotency is the point."""

from coderev.models import Finding, ReviewResult
from coderev.publish import FINDING_MARKER, SUMMARY_MARKER, finding_body, publish


class FakeClient:
    def __init__(self, issue_comments=None, review_comments=None):
        self.issue_comments = issue_comments or []
        self.review_comments = review_comments or []
        self.created_summary = None
        self.updated = []
        self.deleted = []
        self.created_inline = []
        self.pull_calls = 0

    def list_issue_comments(self, pr):
        return self.issue_comments

    def create_issue_comment(self, pr, body):
        self.created_summary = body
        return {"id": 1}

    def update_issue_comment(self, comment_id, body):
        self.updated.append((comment_id, body))
        return {"id": comment_id}

    def list_review_comments(self, pr):
        return self.review_comments

    def delete_review_comment(self, comment_id):
        self.deleted.append(comment_id)

    def get_pull(self, pr):
        self.pull_calls += 1
        return {"head": {"sha": "deadbeef"}}

    def create_review_comment(self, pr, *, commit_id, path, line, body):
        self.created_inline.append((path, line, commit_id, body))
        return {"id": 2}


def _result(count: int = 1) -> ReviewResult:
    return ReviewResult(
        summary="改了支付",
        risk_level="medium",
        findings=[
            Finding(
                path="src/a.py",
                line_start=10 + i,
                title=f"问题 {i}",
                rule_id="rule",
                severity="warning",
                confidence=0.8,
            )
            for i in range(count)
        ],
    )


def test_creates_summary_and_inline_when_first_run():
    client = FakeClient()
    outcome = publish(client, 5, _result(2), run_id="r1")

    assert outcome.summary_action == "created"
    assert outcome.inline_created == 2
    assert outcome.inline_deleted == 0
    assert SUMMARY_MARKER in client.created_summary
    assert client.pull_calls == 1
    assert client.created_inline[0][2] == "deadbeef"


def test_updates_existing_summary_and_replaces_inline():
    client = FakeClient(
        issue_comments=[{"id": 77, "body": f"old\n{SUMMARY_MARKER}"}],
        review_comments=[
            {"id": 501, "body": f"stale\n{FINDING_MARKER}"},
            {"id": 502, "body": "human comment, keep me"},
        ],
    )
    outcome = publish(client, 5, _result(1), run_id="r2")

    assert outcome.summary_action == "updated"
    assert client.updated and client.updated[0][0] == 77
    assert client.created_summary is None
    assert client.deleted == [501]  # 只删自己的，不动人类的评论
    assert outcome.inline_deleted == 1


def test_no_findings_skips_inline_and_pull_lookup():
    client = FakeClient()
    outcome = publish(client, 5, ReviewResult(summary="干净", findings=[]), run_id="r3")

    assert outcome.inline_created == 0
    assert client.pull_calls == 0
    assert client.created_inline == []


def test_finding_body_carries_marker_and_rule():
    body = finding_body(_result(1).findings[0])
    assert FINDING_MARKER in body
    assert "rule" in body
    assert "80%" in body


def test_suggestion_fence_has_no_blank_line():
    finding = Finding(
        path="src/a.py",
        line_start=3,
        title="硬编码密钥",
        rule_id="python/hardcoded-secret",
        severity="blocker",
        suggestion='API_KEY = os.environ["API_KEY"]',
        confidence=0.9,
    )
    body = finding_body(finding)
    assert '```\nAPI_KEY = os.environ["API_KEY"]\n```' in body
