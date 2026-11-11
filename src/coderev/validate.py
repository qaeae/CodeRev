"""Guardrails applied to every model response.

Rule of the product: a finding that cannot be located in the diff does not
exist. This module is where that rule is enforced.
"""

from __future__ import annotations

from dataclasses import replace

from .diff import FileDiff
from .models import Finding, ReviewResult


def apply_guardrails(
    result: ReviewResult,
    files: dict[str, FileDiff],
    *,
    min_confidence: float = 0.6,
    max_findings: int = 8,
) -> tuple[ReviewResult, list[dict], bool]:
    """Filter out untrustworthy findings.

    Returns (filtered_result, dropped_items, truncated).
    """
    kept: list[Finding] = []
    dropped: list[dict] = []
    seen: set[tuple[str, int, str]] = set()

    for finding in result.sorted_findings():
        reason = _reject_reason(finding, files, min_confidence, seen)
        if reason:
            dropped.append({"finding": finding.to_dict(), "reason": reason})
            continue
        seen.add(finding.key)
        kept.append(finding)

    truncated = len(kept) > max_findings
    return replace(result, findings=kept[:max_findings]), dropped, truncated


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
