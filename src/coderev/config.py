"""`.coderev.yml` loading.

Config lives with the repo so review policy is reviewable like code.
CLI flags win over the file; the file wins over defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_NAMES = (".coderev.yml", ".coderev.yaml")


@dataclass
class ReviewConfig:
    provider: str = "mock"
    model: str = ""
    base_url: str = ""
    rules: str = "rules/examples"
    min_confidence: float = 0.6
    max_findings: int = 8
    ignore_paths: list[str] = field(default_factory=list)
    post: bool = True


@dataclass
class Config:
    review: ReviewConfig = field(default_factory=ReviewConfig)
    source: str = "<defaults>"


def find_config(start: Path) -> Path | None:
    for name in DEFAULT_CONFIG_NAMES:
        candidate = start / name
        if candidate.is_file():
            return candidate
    return None


def load_config(path: str | Path | None = None, start: Path | None = None) -> Config:
    """Load config from an explicit path, else search `start` (default: cwd)."""
    if path is None:
        path = find_config(start or Path.cwd())
        if path is None:
            return Config()

    file = Path(path)
    data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}

    if not isinstance(data, dict):
        raise ValueError(f"{file}: 顶层必须是对象")

    version = data.get("version", 1)
    if version != 1:
        raise ValueError(f"{file}: 不支持的 version {version!r}（当前只支持 1）")

    review_data = data.get("review") or {}
    if not isinstance(review_data, dict):
        raise ValueError(f"{file}: review 必须是对象")

    defaults = ReviewConfig()
    review = ReviewConfig(
        provider=str(review_data.get("provider", defaults.provider)),
        model=str(review_data.get("model", defaults.model)),
        base_url=str(review_data.get("base_url", defaults.base_url)),
        rules=str(review_data.get("rules", defaults.rules)),
        min_confidence=float(review_data.get("min_confidence", defaults.min_confidence)),
        max_findings=int(review_data.get("max_findings", defaults.max_findings)),
        ignore_paths=[str(p) for p in (review_data.get("ignore_paths") or [])],
        post=bool(review_data.get("post", defaults.post)),
    )

    if not 0 <= review.min_confidence <= 1:
        raise ValueError(f"{file}: min_confidence 必须在 0 到 1 之间")
    if review.max_findings < 1:
        raise ValueError(f"{file}: max_findings 必须大于 0")

    return Config(review=review, source=str(file))


def as_dict(config: Config) -> dict[str, Any]:
    return {
        "source": config.source,
        "review": {
            "provider": config.review.provider,
            "model": config.review.model,
            "base_url": config.review.base_url,
            "rules": config.review.rules,
            "min_confidence": config.review.min_confidence,
            "max_findings": config.review.max_findings,
            "ignore_paths": config.review.ignore_paths,
            "post": config.review.post,
        },
    }
