from __future__ import annotations

from discord import PartialEmoji

from fcdex_3_1.fcdex_ext.achievement_admin_util import (
    _TYPE_VALUES,
    _select_emoji,
    normalize_achievement_type,
    parse_bool_field,
)


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


def test_select_emoji_rejects_plain_text() -> None:
    assert _select_emoji("Boss") is None
    assert _select_emoji("  ") is None
    assert _select_emoji(None) is None


def test_select_emoji_accepts_unicode_and_custom() -> None:
    assert _select_emoji("\U0001f3c6") == "\U0001f3c6"
    pe = _select_emoji("<:trophy:123456789012345678>")
    assert isinstance(pe, PartialEmoji)
    assert pe.name == "trophy"
    assert pe.id == 123456789012345678
    assert pe.animated is False
    animated = _select_emoji("<a:spin:987654321098765432>")
    assert isinstance(animated, PartialEmoji)
    assert animated.animated is True
