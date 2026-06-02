from __future__ import annotations

from fcdex_3_1.fcdex_ext.achievement_admin_util import _TYPE_VALUES, normalize_achievement_type, parse_bool_field


def test_normalize_type_accepts_aliases() -> None:
    assert normalize_achievement_type("Battles Won") == "battles_won"
    assert normalize_achievement_type("tournament-win") == "tournament_win"


def test_parse_bool() -> None:
    assert parse_bool_field("yes") is True
    assert parse_bool_field("NO") is False
    assert parse_bool_field(None, default=True) is True
    assert parse_bool_field("", default=False) is False


def test_achievement_type_values_cover_admin_hints() -> None:
    expected = {"battles_won", "merges", "tournament_win", "tournament_participate", "balls_owned", "custom"}
    assert _TYPE_VALUES == expected
