"""Guardrails applied to every model response.

Rule of the product: a finding that cannot be located in the diff does not
exist. Test gaps follow the same principle — they must point at a file that
this pull request actually touches.
"""

from __future__ import annotations

from dataclasses import replace

from .diff import FileDiff
from .models import Finding, ReviewResult, TestGap


def apply_guardrails(
    result: ReviewResult,
    files: dict[str, FileDiff],
    *,
    min_confidence: float = 0.6,
    max_findings: int = 8,
    max_test_gaps: int = 3,
) -> tuple[ReviewResult, list[dict], bool]:
    """Filter out untrustworthy findings and test gaps.

    Returns (filtered_result, dropped_items, truncated).
    """
    kept: list[Finding] = []
    dropped: list[dict] = []
    seen: set[tuple[str, int, str]] = set()

    for finding in result.sorted_findings():
        reason = _reject_reason(finding, files, min_confidence, seen)
        if reason:
            dropped.append({"kind": "finding", "item": finding.to_dict(), "reason": reason})
            continue
        seen.add(finding.key)
        kept.append(finding)

    truncated = len(kept) > max_findings

    gaps: list[TestGap] = []
    seen_gaps: set[tuple[str, str]] = set()
    for gap in result.test_gaps:
        reason = _reject_gap_reason(gap, files, min_confidence, seen_gaps)
        if reason:
            dropped.append({"kind": "test_gap", "item": gap.to_dict(), "reason": reason})
            continue
        seen_gaps.add(gap.key)
        gaps.append(gap)

    for extra in gaps[max_test_gaps:]:
        dropped.append(
            {
                "kind": "test_gap",
                "item": extra.to_dict(),
                "reason": f"测试缺口超过上限 {max_test_gaps}",
            }
        )
    gaps = gaps[:max_test_gaps]

    return replace(result, findings=kept[:max_findings], test_gaps=gaps), dropped, truncated


def _reject_reason(
    finding: Finding,
    files: dict[str, FileDiff],
    min_confidence: float,
    seen: set[tuple[str, int, str]],
) -> str | None:
    if finding.path not in files:
        return "path 不在本次 diff 中"
    if not files[finding.path].contains(finding.line_start):
        return f"第 {finding.line_start} 行不是本次新增/修改行"
    if finding.confidence < min_confidence:
        return f"置信度 {finding.confidence:.2f} 低于阈值 {min_confidence:.2f}"
    if finding.key in seen:
        return "重复意见"
    return None


def _reject_gap_reason(
    gap: TestGap,
    files: dict[str, FileDiff],
    min_confidence: float,
    seen: set[tuple[str, str]],
) -> str | None:
    if gap.path not in files:
        return "path 不在本次 diff 中"
    if gap.confidence < min_confidence:
        return f"置信度 {gap.confidence:.2f} 低于阈值 {min_confidence:.2f}"
    if gap.key in seen:
        return "重复的测试缺口"
    return None
