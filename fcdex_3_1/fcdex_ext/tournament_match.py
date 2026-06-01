from __future__ import annotations

from django.utils import timezone

from bd_models.models import Player
from fcdex_3_1.fcdex_ext.tournament_bets import resolve_bets_for_match
from fcdex_3_1.fcdex_ext.tournament_loot import grant_match_loot, load_match_prizes
from fcdex_3_1.models import (
    Tournament,
    TournamentGroup,
    TournamentMatch,
    TournamentRegistration,
    TournamentRound,
    TournamentStatus,
)


async def _player_group(tournament: Tournament, player: Player) -> str | None:
    try:
        reg = await TournamentRegistration.objects.aget(tournament=tournament, player=player)
    except TournamentRegistration.DoesNotExist:
        return None
    return reg.group


async def list_pending_matches(tournament: Tournament, player: Player) -> list[TournamentMatch]:
    """Incomplete matches this player is in (group stage scoped to their registration group)."""
    group = await _player_group(tournament, player)
    matches: list[TournamentMatch] = []
    qs = TournamentMatch.objects.filter(tournament=tournament, completed=False).select_related("player1", "player2")
    if tournament.status == TournamentStatus.GROUP_STAGE and group is not None:
        qs = qs.filter(round=TournamentRound.GROUP, group=group)
    async for match in qs.order_by("round", "created_at"):
        if match.player1_id == player.pk or match.player2_id == player.pk:
            matches.append(match)
    return matches


async def list_open_group_matches_in_group(tournament: Tournament, group: str) -> list[TournamentMatch]:
    return [
        m
        async for m in TournamentMatch.objects.filter(
            tournament=tournament, round=TournamentRound.GROUP, group=group, completed=False
        )
        .select_related("player1", "player2")
        .order_by("pk")
    ]


async def record_battle_verification(match_id: int, winner: Player) -> tuple[bool, str]:
    match = await TournamentMatch.objects.select_related("player1", "player2").aget(pk=match_id)
    if match.completed:
        return False, "This tournament match is already completed."
    if winner.pk not in (match.player1_id, match.player2_id):
        return False, "Battle winner is not a participant in this tournament match."

    updated = await TournamentMatch.objects.filter(pk=match_id, completed=False).aupdate(
        verified_winner_id=winner.pk, verified_at=timezone.now()
    )
    if not updated:
        return False, "This tournament match is already completed."
    return True, "Battle result verified."


async def apply_verified_battle_result(match_id: int, winner: Player, *, guild_id: int | None) -> tuple[bool, str]:
    match = await TournamentMatch.objects.aget(pk=match_id)
    if match.completed:
        return False, "This tournament match is already completed."
    tournament = await Tournament.objects.aget(pk=match.tournament_id)
    ok, message = await record_battle_verification(match_id, winner)
    if not ok:
        return False, message
    match = await TournamentMatch.objects.aget(pk=match_id)
    claimed, claim_message = await claim_match_victory(tournament, match, winner, guild_id=guild_id)
    if claimed:
        return True, claim_message
    return False, claim_message


async def claim_match_victory(
    tournament: Tournament, match: TournamentMatch, winner: Player, *, guild_id: int | None = None
) -> tuple[bool, str]:
    if winner.pk not in (match.player1_id, match.player2_id):
        return False, "You aren't a participant in this match."
    if match.player2_id is None:
        return False, "This match has no opponent yet."

    fresh = await TournamentMatch.objects.aget(pk=match.pk)
    if fresh.completed:
        return False, "This match is already completed."
    if fresh.verified_winner_id is None:
        return False, (
            "No verified battle result yet — use **Start battle** in this hub, win the match, then claim your rewards."
        )
    if fresh.verified_winner_id != winner.pk:
        return False, "Only the verified battle winner can claim this match."

    score1, score2 = (1, 0) if winner.pk == match.player1_id else (0, 1)
    locked = await TournamentMatch.objects.filter(pk=match.pk, completed=False, verified_winner_id=winner.pk).aupdate(
        winner_id=winner.pk, completed=True, score1=score1, score2=score2
    )
    if not locked:
        return False, "This match is already completed."

    match = await TournamentMatch.objects.aget(pk=match.pk)

    reward_text = ""
    if not match.reward_claimed:
        prize_pool = await load_match_prizes(match)
        loot_text = await grant_match_loot(match, winner, guild_id=guild_id)
        reward_text = f" · {loot_text}"
        if not prize_pool and tournament.match_win_reward:
            await winner.add_money(tournament.match_win_reward)
            reward_text += f" · **+{tournament.match_win_reward:,}** coins"
        await TournamentMatch.objects.filter(pk=match.pk, reward_claimed=False).aupdate(reward_claimed=True)

    try:
        registration = await TournamentRegistration.objects.aget(tournament=tournament, player=winner)
        registration.score += 3
        if tournament.semifinal_cutoff and registration.score < tournament.semifinal_cutoff:
            registration.semifinal_eligible = False
        await registration.asave(update_fields=("score", "semifinal_eligible"))
    except TournamentRegistration.DoesNotExist:
        # Verified winner without a registration row — record match only, no bracket points.
        pass

    bet_lines = await resolve_bets_for_match(match, winner)
    bet_text = f"\n-# Bets settled: {', '.join(bet_lines)}" if bet_lines else ""

    opponent = match.player2 if winner.pk == match.player1_id else match.player1
    try:
        group_part = f" · **{TournamentGroup(match.group).label}**" if match.group else ""
    except ValueError:
        group_part = ""
    opponent_mention = f"<@{opponent.discord_id}>" if opponent else "your opponent"
    return True, (
        f"🏆 Match **#{match.pk}** recorded{group_part}! "
        f"You beat {opponent_mention} · **+3** tournament pts{reward_text}{bet_text}"
    )
