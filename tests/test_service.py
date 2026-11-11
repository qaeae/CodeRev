"""Service layer: one implementation shared by CLI and worker."""

from pathlib import Path

import pytest

from coderev.providers import MockProvider
from coderev.service import ModelOutputError, review_diff, review_pull_request
from coderev.config import ReviewConfig

FIXTURES = Path(__file__).parent / "fixtures"
DIFF = (FIXTURES / "example.diff").read_text(encoding="utf-8")
RESPONSE = (FIXTURES / "mock-response.json").read_text(encoding="utf-8")
RULES = Path(__file__).parents[1] / "rules" / "examples"


def test_review_diff_runs_the_whole_pipeline():
    outcome = review_diff(DIFF, provider=MockProvider(RESPONSE), rules_path=RULES)

    assert len(outcome.result.findings) == 1
    assert len(outcome.result.test_gaps) == 1
    assert outcome.changed_lines == 6  # 4 added in java + 2 in python
    assert outcome.run_id
    assert outcome.dropped  # 无法定位的都被记录


def test_empty_diff_returns_empty_outcome():
    outcome = review_diff("", provider=MockProvider("{}"))
    assert outcome.changed_lines == 0
    assert outcome.result.findings == []


def test_bad_json_raises():
    with pytest.raises(ModelOutputError):
        review_diff(DIFF, provider=MockProvider("not json"))


def test_over_threshold_annotates_summary():
    outcome = review_diff(
        DIFF, provider=MockProvider(RESPONSE), rules_path=RULES, max_changed_lines=2
    )
    assert "超过阈值" in outcome.result.summary


class FakeClient:
    def __init__(self, diff: str) -> None:
        self._diff = diff
        self.published = 0

    def get_diff(self, number: int) -> str:
        return self._diff

    def list_issue_comments(self, number):
        return []

    def create_issue_comment(self, number, body):
        self.published += 1
        return {"id": 1}

    def update_issue_comment(self, comment_id, body):
        return {"id": comment_id}

    def list_review_comments(self, number):
        return []

    def delete_review_comment(self, comment_id):
        pass

    def get_pull(self, number):
        return {"head": {"sha": "deadbeef"}}

    def create_review_comment(self, number, *, commit_id, path, line, body):
        return {"id": 2}


def test_review_pull_request_publishes():
    client = FakeClient(DIFF)
    outcome = review_pull_request(
        client,
        7,
        provider=MockProvider(RESPONSE),
        review=ReviewConfig(rules=str(RULES)),
        post=True,
    )

    assert outcome.published is not None
    assert outcome.published.summary_action == "created"
    assert client.published == 1


def test_review_pull_request_can_skip_publish():
    client = FakeClient(DIFF)
    outcome = review_pull_request(
        client,
        7,
        provider=MockProvider(RESPONSE),
        review=ReviewConfig(rules=str(RULES)),
        post=False,
    )

    assert outcome.published is None
    assert client.published == 0


def test_empty_diff_does_not_publish():
    client = FakeClient("")
    outcome = review_pull_request(
        client,
        7,
        provider=MockProvider("{}"),
        review=ReviewConfig(rules=str(RULES)),
        post=True,
    )

    assert outcome.published is None
    assert client.published == 0
