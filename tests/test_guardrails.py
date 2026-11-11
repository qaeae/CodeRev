"""Guardrail tests — the product's core promise lives here."""

import json
from pathlib import Path

from coderev.diff import parse_unified_diff
from coderev.models import ReviewResult
from coderev.validate import apply_guardrails

FIXTURES = Path(__file__).parent / "fixtures"
DIFF = (FIXTURES / "example.diff").read_text(encoding="utf-8")
MOCK = json.loads((FIXTURES / "mock-response.json").read_text(encoding="utf-8"))


def _run(**kwargs):
    files = parse_unified_diff(DIFF)
    result = ReviewResult.from_dict(MOCK)
    return apply_guardrails(result, files, **kwargs)


def test_only_locatable_findings_survive():
    filtered, dropped, truncated = _run(min_confidence=0.6, max_findings=8)

    assert len(filtered.findings) == 1
    finding = filtered.findings[0]
    assert finding.path.endswith("OrderService.java")
    assert finding.line_start == 42
    assert finding.rule_id == "java-spring/transaction-boundary"

    reasons = [item["reason"] for item in dropped]
    assert any("path" in r for r in reasons)
    assert any("行" in r for r in reasons)
    assert any("置信度" in r for r in reasons)
    assert any("重复" in r for r in reasons)
    assert truncated is False


def test_low_confidence_threshold_is_configurable():
    filtered, dropped, _ = _run(min_confidence=0.2, max_findings=8)
    # 置信度 0.3 的那条会进来，但重复项仍被去重
    assert len(filtered.findings) == 2
    assert all(f.confidence >= 0.2 for f in filtered.findings)


def test_max_findings_truncates_and_flags():
    files = parse_unified_diff(DIFF)
    payload = {
        "summary": "",
        "risk_level": "low",
        "findings": [
            {
                "path": "src/payment/client.py",
                "line_start": 11,
                "title": f"问题 {i}",
                "rule_id": f"rule-{i}",
                "severity": "warning",
                "confidence": 0.9,
            }
            for i in range(5)
        ],
    }
    filtered, _, truncated = apply_guardrails(
        ReviewResult.from_dict(payload), files, min_confidence=0.5, max_findings=3
    )
    assert len(filtered.findings) == 3
    assert truncated is True


def test_severity_sorted_first():
    files = parse_unified_diff(DIFF)
    payload = {
        "summary": "",
        "risk_level": "low",
        "findings": [
            {"path": "src/payment/client.py", "line_start": 11, "title": "建议", "severity": "suggestion", "confidence": 0.9},
            {"path": "src/payment/client.py", "line_start": 12, "title": "阻断", "severity": "blocker", "confidence": 0.7},
        ],
    }
    filtered, _, _ = apply_guardrails(ReviewResult.from_dict(payload), files, min_confidence=0.5, max_findings=8)
    assert [f.severity for f in filtered.findings] == ["blocker", "suggestion"]
