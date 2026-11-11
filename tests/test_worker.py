"""Worker guarantees: retry once, one job per PR at a time."""

import threading
import time

from coderev.worker import Job, ReviewWorker


def _job(number: int = 1) -> Job:
    return Job(repo="acme/project", number=number, head_sha="abc", delivery=f"d-{number}")


def test_retries_once_then_succeeds():
    calls = []

    def handler(job: Job) -> None:
        calls.append(job.number)
        if len(calls) == 1:
            raise RuntimeError("transient")

    worker = ReviewWorker(handler, workers=1, retry_delay=0, logger=lambda _: None)
    worker.submit(_job())
    worker.shutdown(wait=True)

    assert len(calls) == 2


def test_gives_up_after_two_attempts():
    calls = []

    def handler(job: Job) -> None:
        calls.append(job.number)
        raise RuntimeError("always broken")

    logs = []
    worker = ReviewWorker(handler, workers=1, retry_delay=0, logger=logs.append)
    worker.submit(_job())
    worker.shutdown(wait=True)

    assert len(calls) == 2
    assert any("失败" in line for line in logs)


def test_same_pr_is_serialized():
    active = 0
    peak = 0
    lock = threading.Lock()

    def handler(job: Job) -> None:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.05)
        with lock:
            active -= 1

    worker = ReviewWorker(handler, workers=4, retry_delay=0, logger=lambda _: None)
    for index in range(4):
        worker.submit(Job(repo="acme/project", number=1, head_sha="abc", delivery=f"d-{index}"))
    worker.shutdown(wait=True)

    assert peak == 1


def test_different_prs_can_overlap():
    active = 0
    peak = 0
    lock = threading.Lock()
    started = threading.Event()

    def handler(job: Job) -> None:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        started.set()
        time.sleep(0.1)
        with lock:
            active -= 1

    worker = ReviewWorker(handler, workers=2, retry_delay=0, logger=lambda _: None)
    worker.submit(_job(1))
    started.wait(timeout=2)
    worker.submit(_job(2))
    worker.shutdown(wait=True)

    assert peak == 2
