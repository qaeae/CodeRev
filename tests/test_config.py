"""Config loading tests."""

from pathlib import Path

import pytest

from coderev.config import load_config


def test_defaults_when_no_file(tmp_path: Path):
    config = load_config(None, start=tmp_path)
    assert config.review.provider == "mock"
    assert config.review.min_confidence == 0.6
    assert config.review.max_findings == 8
    assert config.source == "<defaults>"


def test_auto_discovery(tmp_path: Path):
    (tmp_path / ".coderev.yml").write_text(
        "version: 1\nreview:\n  provider: openai\n  model: deepseek-chat\n",
        encoding="utf-8",
    )
    config = load_config(None, start=tmp_path)
    assert config.review.provider == "openai"
    assert config.review.model == "deepseek-chat"


def test_rejects_unknown_version(tmp_path: Path):
    path = tmp_path / "c.yml"
    path.write_text("version: 2\nreview: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="version"):
        load_config(path)


def test_rejects_out_of_range_confidence(tmp_path: Path):
    path = tmp_path / "c.yml"
    path.write_text("version: 1\nreview:\n  min_confidence: 1.5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="min_confidence"):
        load_config(path)


def test_posts_default_true(tmp_path: Path):
    config = load_config(None, start=tmp_path)
    assert config.review.post is True
