"""Rule loading and matching tests."""

from pathlib import Path

import pytest

from coderev.rules import load_rules, match_rules, validate_rules

RULES_DIR = Path(__file__).parents[1] / "rules" / "examples"


def test_load_example_pack():
    rules = load_rules(RULES_DIR)
    ids = {rule.id for rule in rules}
    assert "java-spring/transaction-boundary" in ids
    assert "java-spring/hardcoded-secret" in ids


def test_match_by_applies_to():
    rules = load_rules(RULES_DIR)
    matched = match_rules(rules, ["src/main/java/com/acme/order/OrderService.java"])
    assert any(rule.id == "java-spring/transaction-boundary" for rule in matched)

    unmatched = match_rules(rules, ["docs/readme.md"])
    assert unmatched == []


def test_example_pack_is_valid():
    assert validate_rules(load_rules(RULES_DIR)) == []


def test_missing_fields_raise(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("rules:\n  - id: broken\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_rules(bad)


def test_invalid_severity_raises(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "rules:\n  - id: x\n    name: x\n    intent: x\n    severity: fatal\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_rules(bad)
