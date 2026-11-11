"""Server-side settings: allowlist, limits, runtime knobs.

Deliberately NOT read from the reviewed repository (`.coderev.yml`): the
allowlist decides who may consume this service, so the repository itself must
not be able to grant that permission.

The file is re-read when its mtime changes, so editing a mounted
`config/server.yml` takes effect without restarting the container.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_PATH = Path("config/server.yml")


@dataclass(frozen=True)
class ServerSettings:
    repos: tuple[str, ...] = ()
    max_changed_lines: int = 1500
    workers: int = 2
    db_path: str = "data/coderev.db"


def parse_settings(data: dict | None) -> ServerSettings:
    data = data or {}
    if not isinstance(data, dict):
        raise ValueError("config/server.yml 顶层必须是对象")

    repos = data.get("repos") or []
    if not isinstance(repos, list):
        raise ValueError("repos 必须是数组")

    limits = data.get("limits") or {}
    server = data.get("server") or {}
    if not isinstance(limits, dict) or not isinstance(server, dict):
        raise ValueError("limits / server 必须是对象")

    max_changed_lines = int(limits.get("max_changed_lines", 1500))
    workers = int(server.get("workers", 2))
    if max_changed_lines < 0:
        raise ValueError("max_changed_lines 不能为负")
    if workers < 1:
        raise ValueError("workers 至少为 1")

    return ServerSettings(
        repos=tuple(str(item) for item in repos),
        max_changed_lines=max_changed_lines,
        workers=workers,
        db_path=str(server.get("db", "data/coderev.db")),
    )


def load_settings(path: str | Path) -> ServerSettings:
    file = Path(path)
    if not file.is_file():
        return ServerSettings()
    data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
    return parse_settings(data)


class SettingsProvider:
    """Hot-reloading accessor; safe for a single writer (the file system)."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or os.environ.get("CODEREV_SERVER_CONFIG") or DEFAULT_PATH)
        self._mtime: float | None = None
        self._settings = ServerSettings()
        self._reload_if_changed()

    def _reload_if_changed(self) -> None:
        try:
            mtime = self.path.stat().st_mtime
        except OSError:
            self._mtime = None
            self._settings = ServerSettings()
            return

        if mtime != self._mtime:
            self._settings = load_settings(self.path)
            self._mtime = mtime

    def get(self) -> ServerSettings:
        self._reload_if_changed()
        return self._settings
