"""Config loading + environment override tests."""

from pathlib import Path

import pytest

from coderev.config import load_config


def test_defaults_when_no_file(tmp_path: Path):
    config = load_config(None, start=tmp_path, env={})
    assert config.review.provider == "mock"
    assert config.review.min_confidence == 0.6
    assert config.review.max_findings == 8
    assert config.source == "<defaults>"
    assert config.env_overrides == []


def test_auto_discovery(tmp_path: Path):
    (tmp_path / ".coderev.yml").write_text(
        "version: 1\nreview:\n  provider: openai\n  model: deepseek-chat\n",
        encoding="utf-8",
    )
    config = load_config(None, start=tmp_path, env={})
    assert config.review.provider == "openai"
    assert config.review.model == "deepseek-chat"


def test_rejects_unknown_version(tmp_path: Path):
    path = tmp_path / "c.yml"
    path.write_text("version: 2\nreview: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="version"):
        load_config(path, env={})


def test_rejects_out_of_range_confidence(tmp_path: Path):
    path = tmp_path / "c.yml"
    path.write_text("version: 1\nreview:\n  min_confidence: 1.5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="min_confidence"):
        load_config(path, env={})


def test_posts_default_true(tmp_path: Path):
    config = load_config(None, start=tmp_path, env={})
    assert config.review.post is True


# ---------------------------------------------------------------- env overrides


def test_env_overrides_file_values(tmp_path: Path):
    (tmp_path / ".coderev.yml").write_text(
        "version: 1\nreview:\n  provider: mock\n  model: from-file\n", encoding="utf-8"
    )
    config = load_config(
        None,
        start=tmp_path,
        env={"CODEREV_PROVIDER": "openai", "CODEREV_MODEL": "deepseek-chat"},
    )
    assert config.review.provider == "openai"
    assert config.review.model == "deepseek-chat"
    assert set(config.env_overrides) == {"CODEREV_PROVIDER", "CODEREV_MODEL"}


def test_env_works_without_config_file(tmp_path: Path):
    config = load_config(
        None,
        start=tmp_path,
        env={
            "CODEREV_MIN_CONFIDENCE": "0.8",
            "CODEREV_MAX_FINDINGS": "3",
            "CODEREV_POST": "false",
            "CODEREV_RULES": "custom/rules",
        },
    )
    assert config.review.min_confidence == 0.8
    assert config.review.max_findings == 3
    assert config.review.post is False
    assert config.review.rules == "custom/rules"


def test_empty_env_values_are_ignored(tmp_path: Path):
    config = load_config(None, start=tmp_path, env={"CODEREV_MODEL": ""})
    assert config.review.model == ""
    assert config.env_overrides == []


def test_invalid_env_value_raises(tmp_path: Path):
    with pytest.raises(ValueError, match="CODEREV_MAX_FINDINGS"):
        load_config(None, start=tmp_path, env={"CODEREV_MAX_FINDINGS": "many"})

    with pytest.raises(ValueError, match="CODEREV_POST"):
        load_config(None, start=tmp_path, env={"CODEREV_POST": "maybe"})

    with pytest.raises(ValueError, match="min_confidence"):
        load_config(None, start=tmp_path, env={"CODEREV_MIN_CONFIDENCE": "2"})
