"""Rules as code.

A rule lives in a YAML file next to the repo it reviews. That makes rules
reviewable (diff, PR, blame) instead of hidden in a database.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SEVERITIES = {"suggestion", "warning", "blocker"}


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    intent: str
    severity: str = "warning"
    language: str = ""
    applies_to: tuple[str, ...] = ("**/*",)
    examples: dict[str, str] = field(default_factory=dict)

    def matches(self, path: str) -> bool:
        return any(_glob_match(path, pattern) for pattern in self.applies_to)


def _glob_match(path: str, pattern: str) -> bool:
    """fnmatch plus a minimal `**/` (fnmatch treats * as crossing slashes)."""
    if "**/" in pattern:
        prefix, rest = pattern.split("**/", 1)
        if not path.startswith(prefix):
            return False
        return fnmatch.fnmatch(path[len(prefix) :], rest)
    return fnmatch.fnmatch(path, pattern)


def _as_rule(item: dict[str, Any], source: str) -> Rule:
    missing = [key for key in ("id", "name", "intent") if not item.get(key)]
    if missing:
        raise ValueError(f"{source}: 规则缺少字段 {', '.join(missing)}")

    severity = str(item.get("severity", "warning")).lower()
    if severity not in SEVERITIES:
        raise ValueError(f"{source}: 非法 severity {severity!r}")

    applies_to = item.get("applies_to") or ["**/*"]
    if isinstance(applies_to, str):
        applies_to = [applies_to]

    examples = item.get("examples") or {}
    if not isinstance(examples, dict):
        examples = {}

    return Rule(
        id=str(item["id"]),
        name=str(item["name"]),
        intent=str(item["intent"]).strip(),
        severity=severity,
        language=str(item.get("language", "")),
        applies_to=tuple(str(p) for p in applies_to),
        examples={str(k): str(v) for k, v in examples.items()},
    )


def load_rules(path: Path) -> list[Rule]:
    """Load a rule file, or every *.yaml under a directory."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"规则路径不存在: {path}")

    files = sorted(path.rglob("*.yaml")) if path.is_dir() else [path]
    rules: list[Rule] = []

    for file in files:
        data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
        if isinstance(data, dict) and "rules" in data:
            items = data["rules"]
        elif isinstance(data, list):
            items = data
        else:
            items = [data]

        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"{file}: 规则必须是对象")
            rules.append(_as_rule(item, str(file)))

    return rules


def match_rules(rules: list[Rule], paths: list[str]) -> list[Rule]:
    return [rule for rule in rules if any(rule.matches(path) for path in paths)]


def validate_rules(rules: list[Rule]) -> list[str]:
    """Return human-readable problems; empty list means OK."""
    problems: list[str] = []
    seen: set[str] = set()

    for rule in rules:
        if rule.id in seen:
            problems.append(f"重复的规则 id: {rule.id}")
        seen.add(rule.id)

        if not rule.intent:
            problems.append(f"{rule.id}: 缺少 intent（为什么这是问题）")
        if not rule.applies_to:
            problems.append(f"{rule.id}: applies_to 不能为空")
        if "bad" not in rule.examples:
            problems.append(f"{rule.id}: 缺少正例 examples.bad")

    return problems
