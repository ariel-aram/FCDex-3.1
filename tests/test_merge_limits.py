from __future__ import annotations

import asyncio
import importlib.util
import sys
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from fcdex_3_0.fcdex_ext.merge_limits import (
    MERGE_WEEKLY_LIMIT,
    calendar_week_bounds,
    merge_special_blocked_message,
    weekly_merge_limit_message,
    weekly_merge_limit_reached,
)

ROOT = Path(__file__).resolve().parents[1]


def test_calendar_week_bounds_starts_on_monday():
    wednesday = datetime(2026, 5, 27, 15, 30, tzinfo=dt_timezone.utc)
    week_start, week_end = calendar_week_bounds(wednesday)
    assert week_start.weekday() == 0
    assert week_start == datetime(2026, 5, 25, 0, 0, tzinfo=dt_timezone.utc)
    assert week_end == week_start + timedelta(days=7)


def test_weekly_merge_limit_reached_at_five():
    assert not weekly_merge_limit_reached(4)
    assert weekly_merge_limit_reached(5)
    assert weekly_merge_limit_reached(6)


def test_weekly_merge_limit_message_mentions_limit():
    message = weekly_merge_limit_message(limit=MERGE_WEEKLY_LIMIT)
    assert str(MERGE_WEEKLY_LIMIT) in message
    assert "Monday" in message


def test_merge_special_blocked_message_mentions_special_name():
    message = merge_special_blocked_message("FCDex Merge")
    assert "FCDex Merge" in message
    assert "cannot be merged" in message


def _load_merge_logic_for_validation_tests():
    """Load merge_logic with lightweight stubs so validate_merge_pair can be tested."""
    bd_models = ModuleType("bd_models")
    bd_models_models = ModuleType("bd_models.models")
    bd_models_models.Ball = object
    bd_models_models.BallInstance = object
    bd_models_models.Player = object
    bd_models_models.Special = object
    bd_models_models.balls = {}
    bd_models_models.specials = {}
    bd_models.models = bd_models_models

    settings_mod = ModuleType("settings")
    settings_models = ModuleType("settings.models")
    settings_models.settings = SimpleNamespace(
        plural_collectible_name="clubballs",
        max_attack_bonus=10,
        max_health_bonus=10,
    )
    settings_mod.models = settings_models

    discord_mod = ModuleType("discord")
    discord_mod.File = object

    fcdex_models = sys.modules.get("fcdex_3_0.models")
    if fcdex_models is None:
        fcdex_models = ModuleType("fcdex_3_0.models")

    merge_log_manager = MagicMock()
    merge_log_filter = MagicMock()
    merge_log_filter.acount = AsyncMock(return_value=0)
    merge_log_filter.aexists = AsyncMock(return_value=False)
    merge_log_manager.filter.return_value = merge_log_filter
    fcdex_models.MergeLog = SimpleNamespace(objects=merge_log_manager)

    special_manager = MagicMock()
    special_manager.filter.return_value.afirst = AsyncMock(return_value=None)
    bd_models_models.Special = SimpleNamespace(objects=special_manager)

    stubs = {
        "bd_models": bd_models,
        "bd_models.models": bd_models_models,
        "settings": settings_mod,
        "settings.models": settings_models,
        "discord": discord_mod,
        "fcdex_3_0.models": fcdex_models,
        "fcdex_3_0.fcdex_ext.bd_helpers": ModuleType("fcdex_3_0.fcdex_ext.bd_helpers"),
        "fcdex_3_0.fcdex_ext.services": ModuleType("fcdex_3_0.fcdex_ext.services"),
    }
    stubs["fcdex_3_0.fcdex_ext.bd_helpers"].format_instance = AsyncMock(return_value="label")
    stubs["fcdex_3_0.fcdex_ext.services"].increment_stat = AsyncMock()

    saved: dict[str, object] = {}
    for name, module in stubs.items():
        saved[name] = sys.modules.get(name)
        sys.modules[name] = module

    path = ROOT / "fcdex_3_0" / "fcdex_ext" / "merge_logic.py"
    spec = importlib.util.spec_from_file_location("fcdex_merge_logic_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name, previous in saved.items():
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous

    return module, merge_log_manager


def _make_instance(*, pk: int, player_id: int, special_id: int | None = None) -> SimpleNamespace:
    instance = SimpleNamespace(
        pk=pk,
        player_id=player_id,
        deleted=False,
        special_id=special_id,
        ball_id=pk,
    )
    instance.is_locked = AsyncMock(return_value=False)
    return instance


def test_validate_merge_pair_blocks_merge_special():
    merge_logic, _ = _load_merge_logic_for_validation_tests()
    player = SimpleNamespace(pk=1)
    merge_special = SimpleNamespace(pk=42, name="FCDex Merge", emoji="✨")
    first = _make_instance(pk=1, player_id=1, special_id=42)
    second = _make_instance(pk=2, player_id=1)

    merge_logic.get_merge_special = AsyncMock(return_value=merge_special)

    with pytest.raises(merge_logic.MergeValidationError) as exc:
        asyncio.run(merge_logic.validate_merge_pair(player, first, second))

    assert "FCDex Merge" in exc.value.message
    assert "cannot be merged" in exc.value.message


def test_validate_merge_pair_allows_fifth_weekly_merge():
    merge_logic, merge_log_manager = _load_merge_logic_for_validation_tests()
    player = SimpleNamespace(pk=1)
    first = _make_instance(pk=1, player_id=1)
    second = _make_instance(pk=2, player_id=1)
    merge_special = SimpleNamespace(pk=42, name="FCDex Merge", emoji="✨")

    merge_logic.get_merge_special = AsyncMock(return_value=merge_special)
    merge_log_manager.filter.return_value.acount = AsyncMock(return_value=4)

    asyncio.run(merge_logic.validate_merge_pair(player, first, second))


def test_validate_merge_pair_blocks_sixth_weekly_merge():
    merge_logic, merge_log_manager = _load_merge_logic_for_validation_tests()
    player = SimpleNamespace(pk=1)
    first = _make_instance(pk=1, player_id=1)
    second = _make_instance(pk=2, player_id=1)
    merge_special = SimpleNamespace(pk=42, name="FCDex Merge", emoji="✨")

    merge_logic.get_merge_special = AsyncMock(return_value=merge_special)
    merge_log_manager.filter.return_value.acount = AsyncMock(return_value=5)

    with pytest.raises(merge_logic.MergeValidationError) as exc:
        asyncio.run(merge_logic.validate_merge_pair(player, first, second))

    assert str(MERGE_WEEKLY_LIMIT) in exc.value.message
    assert "weekly merge limit" in exc.value.message


def test_validate_merge_pair_blocks_already_merged_instance():
    merge_logic, merge_log_manager = _load_merge_logic_for_validation_tests()
    player = SimpleNamespace(pk=1)
    first = _make_instance(pk=1, player_id=1)
    second = _make_instance(pk=2, player_id=1)
    merge_special = SimpleNamespace(pk=42, name="FCDex Merge", emoji="✨")

    merge_logic.get_merge_special = AsyncMock(return_value=merge_special)
    merge_log_manager.filter.return_value.acount = AsyncMock(return_value=0)
    merge_log_manager.filter.return_value.aexists = AsyncMock(return_value=True)

    with pytest.raises(merge_logic.MergeValidationError) as exc:
        asyncio.run(merge_logic.validate_merge_pair(player, first, second))

    assert "already used in a merge" in exc.value.message
