"""Render findings as a GitHub-ready Markdown comment."""

from __future__ import annotations

from .models import ReviewResult

SEVERITY_LABEL = {"blocker": "🛑 阻断", "warning": "⚠️ 警告", "suggestion": "💡 建议"}
RISK_LABEL = {"high": "高", "medium": "中", "low": "低"}


def render_markdown(
    result: ReviewResult,
    *,
    run_id: str = "",
    dropped: int = 0,
    truncated: bool = False,
    footer: str = "",
) -> str:
    lines: list[str] = ["## CodeRev 审查摘要", ""]

    risk = RISK_LABEL.get(result.risk_level, result.risk_level)
    lines.append(f"**风险等级：{risk}**" + (f" · {result.summary}" if result.summary else ""))
    lines.append("")

    if not result.findings:
        lines.append("未发现可定位的问题。")
    else:
        lines.append(f"### 发现的问题（{len(result.findings)}）")
        lines.append("")
        lines.append("| 级别 | 位置 | 规则 | 问题 |")
        lines.append("|---|---|---|---|")
        for finding in result.findings:
            location = f"`{finding.path}:{finding.line_start}`"
            if finding.line_end and finding.line_end != finding.line_start:
                location = f"`{finding.path}:{finding.line_start}-{finding.line_end}`"
            label = SEVERITY_LABEL.get(finding.severity, finding.severity)
            lines.append(f"| {label} | {location} | `{finding.rule_id}` | {finding.title} |")
        lines.append("")

        for finding in result.findings:
            lines.append(f"#### `{finding.path}:{finding.line_start}` {finding.title}")
            if finding.detail:
                lines.append("")
                lines.append(finding.detail)
            if finding.suggestion:
                lines.append("")
                lines.append("**建议**")
                lines.append("")
                lines.append("```")
                lines.append(finding.suggestion)
                lines.append("```")
            lines.append(f"\n<sub>规则 `{finding.rule_id}` · 置信度 {finding.confidence:.0%}</sub>")
            lines.append("")

    if result.test_gaps:
        lines.append(f"### 测试缺口（{len(result.test_gaps)}）")
        lines.append("")
        for gap in result.test_gaps:
            lines.append(f"#### `{gap.path}` · `{gap.symbol}`")
            if gap.reason:
                lines.append("")
                lines.append(gap.reason)
            if gap.cases:
                lines.append("")
                for case in gap.cases:
                    lines.append(f"- {case}")
            lines.append(f"\n<sub>置信度 {gap.confidence:.0%} · 仅建议，不会自动生成</sub>")
            lines.append("")

    if dropped:
        lines.append(f"> 另有 {dropped} 条意见因无法定位或置信度不足未展示。")
    if truncated:
        lines.append("> 意见数超过展示上限，已按严重级别截断。")

    lines.append("")
    lines.append("---")
    lines.append("由 [CodeRev](https://github.com/qaeae/CodeRev) 生成 · 默认只评论、不阻断")
    if footer:
        lines.append(footer)
    if run_id:
        lines.append(f"<!-- coderev:run_id={run_id} -->")

    return "\n".join(lines).strip() + "\n"
