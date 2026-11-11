"""Rendering and CLI smoke tests."""

from pathlib import Path

from coderev.cli import main
from coderev.models import Finding, ReviewResult
from coderev.render import render_markdown

FIXTURES = Path(__file__).parent / "fixtures"
RULES_DIR = Path(__file__).parents[1] / "rules" / "examples"


def test_render_contains_table_and_marker():
    result = ReviewResult(
        summary="改了支付流程",
        risk_level="medium",
        findings=[
            Finding(
                path="src/a.java",
                line_start=12,
                title="事务内调用外部接口",
                rule_id="java-spring/transaction-boundary",
                severity="warning",
                confidence=0.8,
            )
        ],
    )
    text = render_markdown(result, run_id="abc123")
    assert "## CodeRev 审查摘要" in text
    assert "src/a.java:12" in text
    assert "java-spring/transaction-boundary" in text
    assert "<!-- coderev:run_id=abc123 -->" in text


def test_cli_review_json(capsys):
    code = main(
        [
            "review",
            "--diff",
            str(FIXTURES / "example.diff"),
            "--provider",
            "mock",
            "--mock-response",
            str(FIXTURES / "mock-response.json"),
            "--rules",
            str(RULES_DIR),
        ]
    )
    assert code == 0

    out = capsys.readouterr().out
    assert '"findings"' in out
    assert "OrderService.java" in out
    assert '"truncated": false' in out


def test_cli_review_markdown(capsys):
    code = main(
        [
            "review",
            "--diff",
            str(FIXTURES / "example.diff"),
            "--provider",
            "mock",
            "--mock-response",
            str(FIXTURES / "mock-response.json"),
            "--markdown",
        ]
    )
    assert code == 0
    assert "## CodeRev 审查摘要" in capsys.readouterr().out


def test_cli_rules_validate(capsys):
    assert main(["rules", "validate", "--path", str(RULES_DIR)]) == 0
    assert "通过校验" in capsys.readouterr().out
