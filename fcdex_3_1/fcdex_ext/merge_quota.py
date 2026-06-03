from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.utils import timezone

from bd_models.models import Player
from fcdex_3_1.fcdex_ext.merge_config import DEFAULT_PERIOD_DAYS, DEFAULT_WEEKLY_CAP
from fcdex_3_1.fcdex_ext.merge_limits import calendar_week_bounds
from fcdex_3_1.models import MergeLog, MergeQuotaSettings, PlayerMergeQuota


@dataclass(frozen=True, slots=True)
class MergeQuotaSnapshot:
    used: int
    cap: int
    period_start: datetime
    period_end: datetime
    premium_bonus: int
    cap_override: int | None


async def get_merge_quota_settings() -> MergeQuotaSettings:
    settings, _ = await MergeQuotaSettings.objects.aget_or_create(
        pk=1, defaults={"weekly_cap": DEFAULT_WEEKLY_CAP, "period_days": DEFAULT_PERIOD_DAYS}
    )
    return settings


def period_bounds(period_days: int, *, now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return [start, end) for the active quota window."""
    moment = now or timezone.now()
    if period_days == 7:
        return calendar_week_bounds(moment)
    start = moment - timedelta(days=period_days)
    return start, moment


async def get_player_merge_quota_row(player: Player) -> PlayerMergeQuota | None:
    return await PlayerMergeQuota.objects.filter(player=player).afirst()


async def count_player_merges_in_period(player: Player, *, period_start: datetime, period_end: datetime) -> int:
    return await MergeLog.objects.filter(
        player=player, created_at__gte=period_start, created_at__lt=period_end
    ).acount()


async def get_player_effective_cap(player: Player, settings: MergeQuotaSettings | None = None) -> int:
    settings = settings or await get_merge_quota_settings()
    override = await get_player_merge_quota_row(player)
    if override is not None and override.cap_override is not None:
        base = override.cap_override
    else:
        base = settings.weekly_cap
    bonus = override.premium_bonus if override is not None else 0
    return max(1, base + bonus)


async def get_merge_quota_snapshot(player: Player) -> MergeQuotaSnapshot:
    settings = await get_merge_quota_settings()
    period_start, period_end = period_bounds(settings.period_days)
    used = await count_player_merges_in_period(player, period_start=period_start, period_end=period_end)
    override = await get_player_merge_quota_row(player)
    return MergeQuotaSnapshot(
        used=used,
        cap=await get_player_effective_cap(player, settings),
        period_start=period_start,
        period_end=period_end,
        premium_bonus=override.premium_bonus if override is not None else 0,
        cap_override=override.cap_override if override is not None else None,
    )


def merge_quota_limit_reached(used: int, cap: int) -> bool:
    return used >= cap


def format_progress_bar(used: int, cap: int, *, width: int = 12) -> str:
    if cap < 1:
        cap = 1
    ratio = min(used / cap, 1.0)
    filled = min(width, round(ratio * width))
    empty = width - filled
    # Use the same block height for both segments — LIGHT SHADE (░) sits higher than FULL BLOCK (█) in Discord.
    return f"`{'█' * filled}{'·' * empty}`"


def format_reset_line(*, period_days: int, period_end: datetime) -> str:
    if period_days == 7:
        return "-# Quota resets **Monday** (server time) at the start of the calendar week."
    return f"-# Rolling window — oldest merges fall off after **{period_days}** days."


def merge_quota_limit_message(*, cap: int, period_days: int) -> str:
    if period_days == 7:
        reset = "The limit resets at the start of each calendar week (Monday, server time)."
    else:
        reset = f"The limit uses a rolling **{period_days}**-day window."
    return f"You've reached your merge quota ({cap} per period). {reset}"


def format_quota_status_block(snapshot: MergeQuotaSnapshot, *, settings_period_days: int) -> str:
    remaining = max(snapshot.cap - snapshot.used, 0)
    bar = format_progress_bar(snapshot.used, snapshot.cap)
    bonus_line = ""
    if snapshot.premium_bonus:
        bonus_line = f"\n-# Includes **+{snapshot.premium_bonus}** premium bonus merges."
    if snapshot.cap_override is not None:
        bonus_line += f"\n-# Personal cap override: **{snapshot.cap_override}**."
    reset = format_reset_line(period_days=settings_period_days, period_end=snapshot.period_end)
    return (
        f"**Merge quota** · `{snapshot.used}` / `{snapshot.cap}` used · `{remaining}` remaining\n"
        f"{bar}{bonus_line}\n"
        f"{reset}"
    )
