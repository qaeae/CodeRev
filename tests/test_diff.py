"""Diff parsing tests."""

from pathlib import Path

from coderev.diff import parse_unified_diff

FIXTURE = Path(__file__).parent / "fixtures" / "example.diff"


def test_parses_added_lines_on_new_side():
    files = parse_unified_diff(FIXTURE.read_text(encoding="utf-8"))

    order = files["src/main/java/com/acme/order/OrderService.java"]
    assert order.added == {42, 43, 44, 45}

    payment = files["src/payment/client.py"]
    assert payment.added == {11, 12}


def test_context_and_removed_lines_do_not_count():
    files = parse_unified_diff(FIXTURE.read_text(encoding="utf-8"))
    # 第 40 行是上下文，第 11 行的删除行不占新文件行号
    assert 40 not in files["src/main/java/com/acme/order/OrderService.java"].added
    assert 10 not in files["src/payment/client.py"].added


def test_ignores_deleted_files_and_empty_diffs():
    diff = "diff --git a/x b/x\n--- a/x\n+++ /dev/null\n@@ -1 +0,0 @@\n-gone\n"
    assert parse_unified_diff(diff) == {}

    assert parse_unified_diff("") == {}


def test_contains():
    files = parse_unified_diff(FIXTURE.read_text(encoding="utf-8"))
    assert files["src/payment/client.py"].contains(12)
    assert not files["src/payment/client.py"].contains(99)
