"""Review orchestration shared by the CLI and the webhook worker.

Why a service layer: if the CLI and the server each kept their own copy of
"fetch diff → build prompt → call model → guard → publish", the two would drift
within a release or two. There is exactly one implementation, here.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .config import ReviewConfig
from .diff import parse_unified_diff
from .github import GitHubClient
from .models import ReviewResult
from .prompt import SYSTEM_PROMPT, build_user_prompt
from .providers import Provider
from .publish import PublishResult, publish
from .rules import load_rules, match_rules
from .validate import apply_guardrails


class ModelOutputError(RuntimeError):
    """Model returned something that is not the agreed JSON shape."""


@dataclass
class ReviewOutcome:
    run_id: str
    result: ReviewResult
    dropped: list[dict] = field(default_factory=list)
    truncated: bool = False
    published: PublishResult | None = None
    changed_lines: int = 0


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def parse_model_json(text: str) -> dict:
    try:
        return json.loads(_strip_fence(text))
    except json.JSONDecodeError as exc:
        raise ModelOutputError(f"模型输出不是合法 JSON：{exc}") from exc


def review_diff(
    diff_text: str,
    *,
    provider: Provider,
    rules_path: str | Path | None = None,
    min_confidence: float = 0.6,
    max_findings: int = 8,
    max_test_gaps: int = 3,
    max_changed_lines: int = 1500,
) -> ReviewOutcome:
    """Run the whole review pipeline over a unified diff."""
    run_id = uuid.uuid4().hex[:12]
    files = parse_unified_diff(diff_text)

    if not files:
        return ReviewOutcome(
            run_id=run_id,
            result=ReviewResult(summary="没有可审查的新增行"),
        )

    changed_lines = sum(len(diff.added) for diff in files.values())

    rules = []
    if rules_path:
        rules = match_rules(load_rules(Path(rules_path)), list(files))

    prompt = build_user_prompt(diff_text, files, rules)
    raw = provider.complete(SYSTEM_PROMPT, prompt)
    result = ReviewResult.from_dict(parse_model_json(raw))

    filtered, dropped, truncated = apply_guardrails(
        result,
        files,
        min_confidence=min_confidence,
        max_findings=max_findings,
        max_test_gaps=max_test_gaps,
    )

    if changed_lines > max_changed_lines:
        note = f"本次变更 {changed_lines} 行，超过阈值 {max_changed_lines}，diff 可能被截断。"
        filtered.summary = f"{filtered.summary}（{note}）" if filtered.summary else note

    return ReviewOutcome(
        run_id=run_id,
        result=filtered,
        dropped=dropped,
        truncated=truncated,
        changed_lines=changed_lines,
    )


def review_pull_request(
    client: GitHubClient,
    number: int,
    *,
    provider: Provider,
    review: ReviewConfig,
    post: bool = True,
) -> ReviewOutcome:
    """Fetch a PR diff, review it, optionally publish the result."""
    outcome = review_diff(
        client.get_diff(number),
        provider=provider,
        rules_path=review.rules,
        min_confidence=review.min_confidence,
        max_findings=review.max_findings,
    )

    if post and outcome.changed_lines > 0:
        outcome.published = publish(
            client,
            number,
            outcome.result,
            dropped=len(outcome.dropped),
            truncated=outcome.truncated,
            run_id=outcome.run_id,
        )

    return outcome
