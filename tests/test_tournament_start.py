from __future__ import annotations

import itertools

import pytest


def _group_stage_match_count(player_count: int) -> int:
    if player_count < 2:
        return 0
    return len(list(itertools.combinations(range(player_count), 2)))


def test_four_players_in_one_group_create_six_matches():
    assert _group_stage_match_count(4) == 6


def test_two_players_per_group_create_one_match_each():
    assert _group_stage_match_count(2) == 1
    assert _group_stage_match_count(2) + _group_stage_match_count(2) == 2


@pytest.mark.parametrize(("legacy_players", "main_players", "expected_matches"), [(4, 0, 6), (2, 2, 2), (3, 1, 3)])
def test_group_stage_match_plan_for_four_registrations(legacy_players, main_players, expected_matches):
    total = _group_stage_match_count(legacy_players) + _group_stage_match_count(main_players)
    assert legacy_players + main_players == 4
    assert total == expected_matches
