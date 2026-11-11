"""Prompt construction.

Two constraints drive the design:
1. Rules are injected, not implied — the model must cite a rule id.
2. Output is JSON only; anything else is unusable downstream.
"""

from __future__ import annotations

from .diff import FileDiff
from .rules import Rule

SYSTEM_PROMPT = """你是一名资深代码审查者。你的输出会被机器解析，必须严格遵守以下规则：

1. 只报告能用「文件路径 + 行号」定位的问题；无法定位的结论一律不要输出。
2. 每条问题必须引用一条给定的规则 id；没有匹配规则时不要硬凑。
3. 宁可少报，不可误报。不确定就不要报。
4. 不要评论代码风格偏好，除非它违反了给定规则。
5. 只输出 JSON，不要 markdown 代码块，不要解释。

输出格式：
{
  "summary": "一句话说明这次改动做了什么、风险在哪",
  "risk_level": "low|medium|high",
  "findings": [
    {
      "path": "src/foo.java",
      "line_start": 42,
      "line_end": 45,
      "severity": "suggestion|warning|blocker",
      "rule_id": "java-spring/transaction-boundary",
      "title": "一句话问题",
      "detail": "为什么这是问题（引用具体代码）",
      "suggestion": "怎么改（可给代码片段）",
      "confidence": 0.0
    }
  ]
}"""


def _rule_block(rules: list[Rule]) -> str:
    if not rules:
        return "（本次没有匹配到规则，只报告明显正确性问题）"

    chunks = []
    for rule in rules:
        lines = [f"### {rule.id}（{rule.name}，默认级别 {rule.severity}）", rule.intent]
        if rule.examples.get("bad"):
            lines.append(f"反例：\n{rule.examples['bad']}")
        if rule.examples.get("good"):
            lines.append(f"正例：\n{rule.examples['good']}")
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks)


def build_user_prompt(
    diff_text: str,
    files: dict[str, FileDiff],
    rules: list[Rule],
    max_diff_chars: int = 12_000,
) -> str:
    changed = "\n".join(
        f"- {path}（新增 {len(diff.added)} 行）" for path, diff in sorted(files.items())
    )
    truncated = diff_text[:max_diff_chars]
    if len(diff_text) > max_diff_chars:
        truncated += "\n...（diff 已截断）"

    return f"""## 变更文件
{changed or "（无）"}

## 可用规则
{_rule_block(rules)}

## 变更内容
```diff
{truncated}
```

现在输出 JSON。"""
