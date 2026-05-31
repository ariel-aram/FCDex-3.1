from __future__ import annotations

import sys
from types import ModuleType

_bd_models = ModuleType("bd_models")
_bd_models_models = ModuleType("bd_models.models")
_bd_models_models.BallInstance = object
_bd_models_models.Player = object
_bd_models.models = _bd_models_models
sys.modules.setdefault("bd_models", _bd_models)
sys.modules.setdefault("bd_models.models", _bd_models_models)

from fcdex_3_0.fcdex_ext.leaderboard_logic import (  # noqa: E402
    ENTRIES_PER_PAGE,
    UNKNOWN_USER,
    LeaderboardEntry,
    LeaderboardMetric,
    LeaderboardScope,
    format_entry_line,
    format_leaderboard_body,
    format_viewer_footer,
    normalize_metric_for_scope,
    page_count,
    resolve_default_scope,
    resolve_scope,
    server_metric_allowed,
    slice_page,
)


def test_default_scope_in_guild():
    assert resolve_default_scope(in_guild=True) == LeaderboardScope.SERVER
    assert resolve_default_scope(in_guild=False) == LeaderboardScope.GLOBAL


def test_resolve_scope_forces_global_in_dm():
    scope, notice = resolve_scope(LeaderboardScope.SERVER, in_guild=False, in_dm=True)
    assert scope == LeaderboardScope.GLOBAL
    assert notice is not None
    assert "global" in notice.lower()


def test_resolve_scope_keeps_global_in_dm():
    scope, notice = resolve_scope(LeaderboardScope.GLOBAL, in_guild=False, in_dm=True)
    assert scope == LeaderboardScope.GLOBAL
    assert notice is None


def test_resolve_scope_defaults_in_guild():
    scope, notice = resolve_scope(None, in_guild=True, in_dm=False)
    assert scope == LeaderboardScope.SERVER
    assert notice is None


def test_server_metric_only_clubballs():
    assert server_metric_allowed(LeaderboardMetric.CLUBBALLS) is True
    assert server_metric_allowed(LeaderboardMetric.BATTLES_WON) is False


def test_normalize_metric_for_server_non_clubballs():
    metric, notice = normalize_metric_for_scope(LeaderboardMetric.BATTLES_WON, LeaderboardScope.SERVER)
    assert metric == LeaderboardMetric.CLUBBALLS
    assert notice is not None
    assert "clubballs" in notice.lower()


def test_normalize_metric_global_unchanged():
    metric, notice = normalize_metric_for_scope(LeaderboardMetric.MERGES, LeaderboardScope.GLOBAL)
    assert metric == LeaderboardMetric.MERGES
    assert notice is None


def test_format_entry_line_medals():
    first = format_entry_line(
        LeaderboardEntry(rank=1, discord_id=123, score=42), LeaderboardMetric.CLUBBALLS, display_name="Alice"
    )
    second = format_entry_line(
        LeaderboardEntry(rank=2, discord_id=456, score=30), LeaderboardMetric.CLUBBALLS, display_name="Bob"
    )
    fourth = format_entry_line(
        LeaderboardEntry(rank=4, discord_id=789, score=10), LeaderboardMetric.CLUBBALLS, display_name="Carol"
    )
    assert first.startswith("🥇")
    assert second.startswith("🥈")
    assert "`#4`" in fourth
    assert "**Alice**" in first
    assert "**42**" in first
    assert "clubballs" in first
    assert "<@" not in first
    assert "<@" not in second
    assert "<@" not in fourth


def test_format_leaderboard_body_no_mentions():
    body = format_leaderboard_body(
        [LeaderboardEntry(rank=1, discord_id=999, score=5)],
        scope=LeaderboardScope.GLOBAL,
        metric=LeaderboardMetric.CLUBBALLS,
        page=0,
        total=10,
        display_names={999: "TestPlayer"},
    )
    assert "**TestPlayer**" in body
    assert "<@999>" not in body
    assert "<@" not in body


def test_format_leaderboard_body_unknown_display_name():
    body = format_leaderboard_body(
        [LeaderboardEntry(rank=1, discord_id=999, score=5)],
        scope=LeaderboardScope.GLOBAL,
        metric=LeaderboardMetric.CLUBBALLS,
        page=0,
        total=10,
    )
    assert f"**{UNKNOWN_USER}**" in body
    assert "<@" not in body


def test_format_viewer_footer():
    assert "unranked" in format_viewer_footer(None, 0, LeaderboardMetric.CLUBBALLS)
    assert format_viewer_footer(3, 42, LeaderboardMetric.CLUBBALLS) == "You: **#3** · **42** clubballs"


def test_page_count_and_slice():
    entries = [LeaderboardEntry(rank=i, discord_id=i, score=i) for i in range(1, 11)]
    assert page_count(10, per_page=ENTRIES_PER_PAGE) == 2
    assert len(slice_page(entries, 0)) == ENTRIES_PER_PAGE
    assert slice_page(entries, 1)[0].rank == 6


def test_format_leaderboard_body_empty():
    body = format_leaderboard_body(
        [], scope=LeaderboardScope.GLOBAL, metric=LeaderboardMetric.CLUBBALLS, page=0, total=10
    )
    assert "No ranked players yet" in body
    assert "Global" in body
