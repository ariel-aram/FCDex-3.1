from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from fcdex_3_1.fcdex_ext.tournament_match import _opponent_for_winner


def test_opponent_for_winner_when_player1_wins():
    match = MagicMock()
    match.player1_id = 10
    match.player2_id = 20
    winner = MagicMock()
    winner.pk = 10
    opponent = MagicMock()

    async def run() -> None:
        with patch("fcdex_3_1.fcdex_ext.tournament_match.Player") as player_model:
            player_model.objects.aget = AsyncMock(return_value=opponent)
            result = await _opponent_for_winner(match, winner)
        assert result is opponent
        player_model.objects.aget.assert_awaited_once_with(pk=20)

    asyncio.run(run())


def test_opponent_for_winner_when_player2_wins():
    match = MagicMock()
    match.player1_id = 10
    match.player2_id = 20
    winner = MagicMock()
    winner.pk = 20
    opponent = MagicMock()

    async def run() -> None:
        with patch("fcdex_3_1.fcdex_ext.tournament_match.Player") as player_model:
            player_model.objects.aget = AsyncMock(return_value=opponent)
            result = await _opponent_for_winner(match, winner)
        assert result is opponent
        player_model.objects.aget.assert_awaited_once_with(pk=10)

    asyncio.run(run())


def test_opponent_for_winner_missing_opponent_id():
    match = MagicMock()
    match.player1_id = 10
    match.player2_id = None
    winner = MagicMock()
    winner.pk = 10

    async def run() -> None:
        with patch("fcdex_3_1.fcdex_ext.tournament_match.Player") as player_model:
            player_model.objects.aget = AsyncMock()
            result = await _opponent_for_winner(match, winner)
        assert result is None
        player_model.objects.aget.assert_not_called()

    asyncio.run(run())
