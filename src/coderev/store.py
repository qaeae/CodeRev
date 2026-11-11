"""SQLite-backed delivery store.

Why SQLite: zero dependency, single file, survives restarts. It is also the
place where the dedupe guarantee lives, so it has to be durable.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from .webhook import PullRequestEvent

SCHEMA = """
CREATE TABLE IF NOT EXISTS deliveries (
    id          TEXT PRIMARY KEY,
    repo        TEXT NOT NULL,
    pr          INTEGER NOT NULL,
    head_sha    TEXT NOT NULL,
    received_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_deliveries_repo_pr ON deliveries(repo, pr);
"""


class DeliveryStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def is_duplicate(self, delivery_id: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM deliveries WHERE id = ?", (delivery_id,)
            ).fetchone()
        return row is not None

    def record(self, event: PullRequestEvent) -> bool:
        """Insert; return False when the delivery id already exists."""
        with self._lock:
            cursor = self._conn.execute(
                "INSERT OR IGNORE INTO deliveries (id, repo, pr, head_sha, received_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (event.delivery, event.repo, event.number, event.head_sha, time.time()),
            )
            self._conn.commit()
        return cursor.rowcount == 1

    def count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM deliveries").fetchone()
        return int(row[0]) if row else 0

    def close(self) -> None:
        with self._lock:
            self._conn.close()
