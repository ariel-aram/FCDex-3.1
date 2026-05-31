from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast

from fcdex_3_0.fcdex_ext.rarity_data import RarityCategory, format_rarity_value, normalize_rarity_name

ROOT = Path(__file__).resolve().parents[1]


class _RarityLogicTestModule:
    """Typing stub for dynamically loaded rarity_logic used in tests."""

    balls: dict[int, SimpleNamespace]
    balls_for_category: Any
    balls_at_rarity: Any
    distinct_rarity_values: Any
    resolve_ball_by_name: Any
    build_spawnable_overview: Any
    count_catalog: Any
    format_ball_line: Any
    fetch_all_balls: Any


def _ball(**kwargs) -> SimpleNamespace:
    defaults = {
        "pk": 1,
        "country": "Test Club",
        "rarity": 10.0,
        "enabled": True,
        "attack": 100,
        "health": 80,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _load_rarity_logic() -> tuple[_RarityLogicTestModule, dict[str, object | None]]:
    bd_models = ModuleType("bd_models")
    bd_models_models = ModuleType("bd_models.models")
    bd_models_models.Ball = object
    bd_models_models.balls = {}
    bd_models.models = bd_models_models

    saved: dict[str, object | None] = {
        name: sys.modules.get(name)
        for name in ("bd_models", "bd_models.models", "fcdex_3_0.fcdex_ext.rarity_logic")
    }
    sys.modules["bd_models"] = bd_models
    sys.modules["bd_models.models"] = bd_models_models
    sys.modules.pop("fcdex_3_0.fcdex_ext.rarity_logic", None)

    path = ROOT / "fcdex_3_0" / "fcdex_ext" / "rarity_logic.py"
    spec = importlib.util.spec_from_file_location("fcdex_rarity_logic_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name, previous in saved.items():
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous

    return cast(_RarityLogicTestModule, module), saved


def _restore_modules(saved: dict[str, object | None]) -> None:
    for name, module in saved.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module


def test_format_rarity_value_strips_trailing_zeros():
    assert format_rarity_value(0.001) == "0.001"
    assert format_rarity_value(10.0) == "10"
    assert format_rarity_value(0.05) == "0.05"


def test_normalize_matches_punctuation():
    assert normalize_rarity_name("FC Barcelona") == normalize_rarity_name("fc barcelona")


def test_rarity_logic_grouping_and_lookup():
    logic, saved = _load_rarity_logic()
    try:
        rows = logic.balls_for_category(
            [_ball(country="A", enabled=True), _ball(pk=2, country="B", enabled=False)],
            RarityCategory.SPAWNABLE,
        )
        assert [row.name for row in rows] == ["A"]

        pool = [_ball(country="Rare", rarity=0.001), _ball(pk=2, country="Common", rarity=10)]
        rows = logic.balls_at_rarity(pool, 0.001)
        assert [row.name for row in rows] == ["Rare"]

        values = logic.distinct_rarity_values(
            [_ball(rarity=10), _ball(pk=2, rarity=0.001), _ball(pk=3, enabled=False, rarity=1)]
        )
        assert values == [0.001, 10.0]

        pool = [_ball(pk=1, country="Shadow", enabled=False), _ball(pk=2, country="Shadow", enabled=True)]
        assert logic.resolve_ball_by_name(pool, "shadow").pk == 2

        pages = logic.build_spawnable_overview([_ball(country="A", rarity=1), _ball(pk=2, country="B", rarity=1)])
        assert "r:1" in pages[0]
        assert "A" in pages[0] and "B" in pages[0]

        counts = logic.count_catalog([_ball(enabled=True), _ball(pk=2, enabled=False)])
        assert counts == {"spawnable": 1, "unspawnable": 1}

        line = logic.format_ball_line(_ball(country="Pele", rarity=0.001, attack=120, health=90))
        assert "r:0.001" in line
        assert "Pele" in line
        assert "120" in line and "90" in line
    finally:
        _restore_modules(saved)


def test_fetch_all_balls_uses_cache():
    logic, saved = _load_rarity_logic()
    try:
        logic.balls = {1: _ball(pk=1, country="Cached")}
        result = asyncio.run(logic.fetch_all_balls())
        assert len(result) == 1
        assert result[0].country == "Cached"
    finally:
        _restore_modules(saved)
