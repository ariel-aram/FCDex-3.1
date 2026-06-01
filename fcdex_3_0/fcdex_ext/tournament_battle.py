from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from ballsdex.core.discord import LayoutView
from bd_models.models import Player
from fcdex_3_0.fcdex_ext.battle_cog import ActiveBattle, _active_battles, fetch_battle
from fcdex_3_0.fcdex_ext.views import BattleLayoutView
from fcdex_3_0.models import Tournament, TournamentMatch

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("fcdex_3_0.tournament.battle")


async def resolve_guild_member(guild: discord.Guild, discord_id: int) -> discord.Member | None:
    """Return a Member in this guild; fetch from API when not in the gateway cache."""
    cached = guild.get_member(discord_id)
    if cached is not None:
        return cached
    try:
        return await guild.fetch_member(discord_id)
    except discord.NotFound:
        return None
    except discord.HTTPException as exc:
        log.warning("Could not fetch member %s in guild %s: %s", discord_id, guild.id, exc)
        return None


async def find_open_match_between(tournament_id: int, player_a_id: int, player_b_id: int) -> TournamentMatch | None:
    pair = {player_a_id, player_b_id}
    async for match in (
        TournamentMatch.objects.filter(tournament_id=tournament_id, completed=False)
        .select_related("player1", "player2")
        .order_by("pk")
    ):
        if match.player2_id is None:
            continue
        if {match.player1_id, match.player2_id} == pair:
            return match
    return None


async def start_tournament_match_battle(
    interaction: discord.Interaction, bot: BallsDexBot, match: TournamentMatch, initiator: discord.Member
) -> tuple[bool, str | LayoutView]:
    if not isinstance(interaction.guild, discord.Guild):
        return False, "Battles can only be started in a server."
    if match.completed:
        return False, "This tournament match is already finished."
    if match.player2_id is None:
        return False, "This match has no opponent yet."

    player, _ = await Player.objects.aget_or_create(discord_id=initiator.id)
    if match.verified_winner_id:
        if match.verified_winner_id == player.pk:
            return False, ("You already won this match in battle — open `/tournament match` and tap **Claim rewards**.")
        return False, "This match already has a verified winner — wait for them to claim rewards."

    if player.pk not in (match.player1_id, match.player2_id):
        return False, "You aren't a participant in this tournament match."

    opponent_player_id = match.player2_id if player.pk == match.player1_id else match.player1_id
    opponent_player = await Player.objects.aget(pk=opponent_player_id)
    opponent_member = await resolve_guild_member(interaction.guild, opponent_player.discord_id)
    if opponent_member is None:
        return False, "Your opponent must be in this server to start a battle."

    if opponent_member.bot:
        return False, "You can't battle bots."
    if fetch_battle(initiator) or fetch_battle(opponent_member):
        return False, "One of you is already in a match."

    battle = ActiveBattle(interaction, initiator, opponent_member, bot, tournament_match_id=match.pk)
    _active_battles.append(battle)
    tournament = await Tournament.objects.aget(pk=match.tournament_id)
    layout = BattleLayoutView(
        battle,
        banner=(
            f"🏟️ **{tournament.name}** · match **#{match.pk}**\n"
            f"{initiator.mention} vs {opponent_member.mention} — lock in when ready!"
        ),
    )
    return True, layout
