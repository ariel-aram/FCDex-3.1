from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fcdex_3_1.fcdex_ext.bd_resolve import (
    PLAYER_NOT_FOUND_MESSAGE,
    _member_matches_token,
    _member_name_keys,
    _normalize_token,
    _parse_username_discriminator,
    resolve_player_input,
)


@pytest.mark.parametrize(("raw", "expected"), [("42", "42"), ("#42", "42"), ("  #99 ", "99"), ("Brazil", "Brazil")])
def test_normalize_token(raw: str, expected: str) -> None:
    assert _normalize_token(raw) == expected


@pytest.mark.parametrize(
    ("raw", "name", "disc"),
    [("alice", "alice", None), ("@bob", "bob", None), ("user#1234", "user", "1234"), ("User#0", "User", "0")],
)
def test_parse_username_discriminator(raw: str, name: str, disc: str | None) -> None:
    assert _parse_username_discriminator(raw) == (name, disc)


def test_member_name_keys_includes_nick_and_global() -> None:
    member = SimpleNamespace(name="Alpha", display_name="Beta", global_name="Gamma", nick="Delta", discriminator="0")
    keys = _member_name_keys(member)  # type: ignore[arg-type]
    assert keys == {"alpha", "beta", "gamma", "delta"}


def test_member_matches_token_by_display_name() -> None:
    member = SimpleNamespace(name="other", display_name="Visible", global_name=None, nick=None, discriminator="0")
    assert _member_matches_token(member, "visible", None)  # type: ignore[arg-type]


def test_member_matches_token_legacy_discriminator() -> None:
    member = SimpleNamespace(name="legacy", display_name="legacy", global_name=None, nick=None, discriminator="4242")
    assert _member_matches_token(member, "legacy", "4242")  # type: ignore[arg-type]
    assert not _member_matches_token(member, "legacy", "0001")  # type: ignore[arg-type]


def test_player_not_found_message_documents_formats() -> None:
    assert "@" in PLAYER_NOT_FOUND_MESSAGE
    assert "Discord" in PLAYER_NOT_FOUND_MESSAGE


def test_resolve_player_input_by_discord_id() -> None:
    player = SimpleNamespace(pk=7, discord_id=9001)
    with patch("fcdex_3_1.fcdex_ext.bd_resolve.Player") as player_model:
        player_model.objects.filter.return_value.afirst = AsyncMock(return_value=player)
        resolved = asyncio.run(resolve_player_input("9001"))
    assert resolved is player


def test_resolve_player_input_by_mention() -> None:
    player = SimpleNamespace(pk=3, discord_id=555)
    with patch("fcdex_3_1.fcdex_ext.bd_resolve.Player") as player_model:
        player_model.objects.filter.return_value.afirst = AsyncMock(return_value=player)
        resolved = asyncio.run(resolve_player_input("<@555>"))
    assert resolved is player


def test_resolve_player_input_by_guild_username() -> None:
    player = SimpleNamespace(pk=2, discord_id=42)
    member = SimpleNamespace(
        id=42, name="tester", display_name="tester", global_name=None, nick=None, discriminator="0"
    )
    guild = MagicMock()
    guild.members = [member]
    guild.query_members = AsyncMock(return_value=[])
    with patch("fcdex_3_1.fcdex_ext.bd_resolve.Player") as player_model:
        player_model.objects.filter.return_value.afirst = AsyncMock(return_value=player)
        resolved = asyncio.run(resolve_player_input("@tester", guild=guild))
    assert resolved is player
    guild.query_members.assert_not_called()


def test_resolve_player_input_queries_guild_when_not_cached() -> None:
    player = SimpleNamespace(pk=2, discord_id=99)
    member = SimpleNamespace(
        id=99, name="hidden", display_name="hidden", global_name=None, nick=None, discriminator="0"
    )
    guild = MagicMock()
    guild.members = []
    guild.query_members = AsyncMock(return_value=[member])
    with patch("fcdex_3_1.fcdex_ext.bd_resolve.Player") as player_model:
        player_model.objects.filter.return_value.afirst = AsyncMock(return_value=player)
        resolved = asyncio.run(resolve_player_input("hidden", guild=guild))
    assert resolved is player
    guild.query_members.assert_awaited_once()
