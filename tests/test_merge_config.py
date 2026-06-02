from __future__ import annotations

from fcdex_3_1.fcdex_ext.merge_config import MAX_MERGE_LEVEL, MERGE_LEVELS, load_merge_cards_config


def test_merge_cards_toml_loads_seven_levels():
    levels, weekly_cap, period_days = load_merge_cards_config()
    assert len(levels) == MAX_MERGE_LEVEL
    assert all(level in levels for level in range(1, MAX_MERGE_LEVEL + 1))
    assert weekly_cap >= 1
    assert period_days >= 1


def test_merge_level_input_counts_match_tiers():
    assert [MERGE_LEVELS[level].input_count for level in range(1, 8)] == [10, 8, 6, 5, 4, 3, 2]
