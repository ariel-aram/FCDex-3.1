from __future__ import annotations

from datetime import datetime
from datetime import timezone as dt_timezone

from fcdex_3_1.fcdex_ext.merge_quota import (
    MergeQuotaSnapshot,
    format_progress_bar,
    format_quota_status_block,
    merge_quota_limit_message,
    merge_quota_limit_reached,
)


def test_merge_quota_limit_reached():
    assert not merge_quota_limit_reached(4, 5)
    assert merge_quota_limit_reached(5, 5)


def test_format_progress_bar_full_and_empty():
    assert format_progress_bar(5, 5) == f"`{'█' * 12}`"
    assert format_progress_bar(0, 5) == f"`{'·' * 12}`"
    assert "█" in format_progress_bar(1, 5)
    assert "·" in format_progress_bar(1, 5)


def test_merge_quota_limit_message_weekly():
    message = merge_quota_limit_message(cap=8, period_days=7)
    assert "8" in message
    assert "Monday" in message


def test_format_quota_status_block_includes_bar():
    snapshot = MergeQuotaSnapshot(
        used=2,
        cap=5,
        period_start=datetime(2026, 5, 25, tzinfo=dt_timezone.utc),
        period_end=datetime(2026, 6, 1, tzinfo=dt_timezone.utc),
        premium_bonus=1,
        cap_override=None,
    )
    block = format_quota_status_block(snapshot, settings_period_days=7)
    assert "2" in block and "5" in block
    assert "█" in block or "·" in block
    assert "premium" in block.lower()
