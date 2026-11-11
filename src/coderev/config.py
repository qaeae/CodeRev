"""`.coderev.yml` loading + environment overrides.

Precedence: CLI flags > environment variables > config file > defaults.
Environment overrides exist so the container image can be configured without
mounting a file (see docker-compose).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Mapping

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
    env_overrides: list[str] = field(default_factory=list)


def _parse_bool(raw: str) -> bool:
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError("布尔值只接受 true/false、1/0、yes/no、on/off")


ENV_FIELDS: dict[str, tuple[str, Callable[[str], Any]]] = {
    "CODEREV_PROVIDER": ("provider", str),
    "CODEREV_MODEL": ("model", str),
    "CODEREV_BASE_URL": ("base_url", str),
    "CODEREV_RULES": ("rules", str),
    "CODEREV_MIN_CONFIDENCE": ("min_confidence", float),
    "CODEREV_MAX_FINDINGS": ("max_findings", int),
    "CODEREV_POST": ("post", _parse_bool),
}


def find_config(start: Path) -> Path | None:
    for name in DEFAULT_CONFIG_NAMES:
        candidate = start / name
        if candidate.is_file():
            return candidate
    return None


def apply_env_overrides(config: Config, env: Mapping[str, str] | None = None) -> Config:
    """Overlay CODEREV_* environment variables onto a config."""
    source = os.environ if env is None else env
    review = config.review
    applied: list[str] = []

    for key, (field_name, parser) in ENV_FIELDS.items():
        raw = source.get(key)
        if raw is None or str(raw).strip() == "":
            continue
        try:
            value = parser(str(raw).strip())
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key}={raw!r} 无效：{exc}") from exc
        review = replace(review, **{field_name: value})
        applied.append(key)

    if not applied:
        return config
    return Config(review=review, source=config.source, env_overrides=applied)


def _validate(review: ReviewConfig, where: str) -> None:
    if not 0 <= review.min_confidence <= 1:
        raise ValueError(f"{where}: min_confidence 必须在 0 到 1 之间")
    if review.max_findings < 1:
        raise ValueError(f"{where}: max_findings 必须大于 0")
    if not review.provider:
        raise ValueError(f"{where}: provider 不能为空")


def load_config(
    path: str | Path | None = None,
    start: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> Config:
    """Load config from an explicit path, else search `start` (default: cwd)."""
    if path is None:
        found = find_config(start or Path.cwd())
        if found is None:
            config = apply_env_overrides(Config(), env)
            _validate(config.review, config.source)
            return config
        path = found

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

    config = apply_env_overrides(Config(review=review, source=str(file)), env)
    _validate(config.review, config.source)
    return config


def as_dict(config: Config) -> dict[str, Any]:
    return {
        "source": config.source,
        "env_overrides": config.env_overrides,
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
