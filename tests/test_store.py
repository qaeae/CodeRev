"""Delivery store: dedupe must survive restarts."""

from coderev.store import DeliveryStore
from coderev.webhook import PullRequestEvent

EVENT = PullRequestEvent(delivery="d-1", repo="acme/project", number=7, head_sha="abc", action="opened")


def test_record_then_duplicate():
    store = DeliveryStore(":memory:")
    assert store.count() == 0
    assert store.record(EVENT) is True
    assert store.count() == 1
    assert store.is_duplicate("d-1") is True
    assert store.record(EVENT) is False
    assert store.count() == 1


def test_persists_across_instances(tmp_path):
    path = tmp_path / "deliveries.db"

    first = DeliveryStore(path)
    assert first.record(EVENT) is True
    first.close()

    second = DeliveryStore(path)
    assert second.is_duplicate("d-1") is True
    assert second.count() == 1
    second.close()


def test_unknown_delivery_is_not_duplicate():
    store = DeliveryStore(":memory:")
    assert store.is_duplicate("nope") is False
