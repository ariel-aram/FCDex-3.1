from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

MERGE_WEEKLY_LIMIT = 5


def calendar_week_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return [start, end) for the current ISO calendar week in the active timezone."""
    moment = now or timezone.now()
    week_start = moment - timedelta(days=moment.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    return week_start, week_start + timedelta(days=7)


def weekly_merge_limit_reached(count: int, *, limit: int = MERGE_WEEKLY_LIMIT) -> bool:
    return count >= limit


def weekly_merge_limit_message(*, limit: int = MERGE_WEEKLY_LIMIT) -> str:
    return (
        f"You've reached the weekly merge limit ({limit} per player). "
        "The limit resets at the start of each calendar week (Monday, server time)."
    )


def merge_special_blocked_message(special_name: str) -> str:
    return (
        f"**{special_name}** cards cannot be merged — they are already forged merge results."
    )
