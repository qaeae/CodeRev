"""Background worker for webhook-triggered reviews.

Three guarantees:
1. a bounded pool — a burst of PRs cannot spawn unbounded threads;
2. one job at a time per pull request — idempotent publishing deletes and
   recreates inline comments, so two concurrent runs would fight;
3. one retry — transient model/network failures should not silently drop a PR.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Job:
    repo: str
    number: int
    head_sha: str
    delivery: str

    @property
    def key(self) -> tuple[str, int]:
        return (self.repo, self.number)


class ReviewWorker:
    def __init__(
        self,
        handler: Callable[[Job], None],
        *,
        workers: int = 2,
        retry_delay: float = 5.0,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self._handler = handler
        self._retry_delay = retry_delay
        self._log = logger or (lambda message: print(f"worker: {message}", flush=True))
        self._pool = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="coderev")
        self._locks: dict[tuple[str, int], threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def _lock_for(self, key: tuple[str, int]) -> threading.Lock:
        with self._locks_guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._locks[key] = lock
            return lock

    def submit(self, job: Job) -> None:
        self._pool.submit(self._run, job)

    def _run(self, job: Job) -> None:
        lock = self._lock_for(job.key)
        with lock:
            for attempt in (1, 2):
                try:
                    self._handler(job)
                    return
                except Exception as exc:  # noqa: BLE001 - worker boundary
                    if attempt == 2:
                        self._log(f"{job.repo}#{job.number} 失败（已重试一次）: {exc}")
                        return
                    self._log(f"{job.repo}#{job.number} 失败，{self._retry_delay}s 后重试: {exc}")
                    if self._retry_delay:
                        time.sleep(self._retry_delay)

    def shutdown(self, wait: bool = True) -> None:
        self._pool.shutdown(wait=wait)
