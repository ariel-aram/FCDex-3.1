from __future__ import annotations

from bd_models.models import Player
from fcdex_3_1.models import (
    Tournament,
    TournamentGroup,
    TournamentMatch,
    TournamentRegistration,
    TournamentRound,
    TournamentStatus,
)


async def _top_finalists(tournament: Tournament, group: TournamentGroup) -> list[TournamentRegistration]:
    regs = [
        r
        async for r in TournamentRegistration.objects.filter(tournament=tournament, group=group.value, eliminated=False)
        .select_related("player")
        .order_by("-score", "player_id")
    ]
    return regs[:2]


async def create_semifinal_pairings(tournament: Tournament) -> int:
    """Create semifinal matches for groups that don't have one yet. Returns count created."""
    created = 0
    for group in TournamentGroup:
        if await TournamentMatch.objects.filter(
            tournament=tournament, round=TournamentRound.SEMIFINAL, group=group.value
        ).aexists():
            continue
        finalists = await _top_finalists(tournament, group)
        if len(finalists) < 2:
            continue
        await TournamentMatch.objects.acreate(
            tournament=tournament,
            round=TournamentRound.SEMIFINAL,
            group=group.value,
            player1=finalists[0].player,
            player2=finalists[1].player,
        )
        created += 1
    return created


async def semifinal_winner_for_group(tournament: Tournament, group: str) -> Player | None:
    match = (
        await TournamentMatch.objects.filter(
            tournament=tournament, round=TournamentRound.SEMIFINAL, group=group, completed=True
        )
        .select_related("winner")
        .afirst()
    )
    return match.winner if match else None


async def create_final_pairing(tournament: Tournament) -> bool:
    """Grand final is always Legacy semifinal winner vs Main semifinal winner."""
    if await TournamentMatch.objects.filter(tournament=tournament, round=TournamentRound.FINAL).aexists():
        return False
    legacy_winner = await semifinal_winner_for_group(tournament, TournamentGroup.LEGACY.value)
    main_winner = await semifinal_winner_for_group(tournament, TournamentGroup.MAIN.value)
    if legacy_winner is None or main_winner is None:
        return False
    await TournamentMatch.objects.acreate(
        tournament=tournament, round=TournamentRound.FINAL, player1=legacy_winner, player2=main_winner
    )
    return True


async def sync_bracket_for_status(tournament: Tournament) -> tuple[int, int]:
    """Repair missing bracket rows for the current tournament status. Returns (semis, final) created."""
    semis = 0
    final = 0
    if tournament.status in (TournamentStatus.SEMIFINALS, TournamentStatus.FINALS, TournamentStatus.COMPLETED):
        semis = await create_semifinal_pairings(tournament)
    if tournament.status in (TournamentStatus.FINALS, TournamentStatus.COMPLETED):
        if await create_final_pairing(tournament):
            final = 1
    return semis, final


async def explain_no_matches(tournament: Tournament, player: Player) -> str:
    try:
        reg = await TournamentRegistration.objects.aget(tournament=tournament, player=player)
    except TournamentRegistration.DoesNotExist:
        return (
            f"You aren't registered in **{tournament.name}**.\n"
            "-# Join with `/tournament view` first, then come back here."
        )

    status = tournament.status
    if reg.eliminated:
        return (
            f"You were **eliminated** in **{tournament.name}** ({reg.get_group_display()} · `{reg.score}` pts).\n"
            "-# Check **Standings** in `/tournament view` · you can still `/tournament bet` on others."
        )

    if status == TournamentStatus.REGISTRATION:
        from fcdex_3_1.fcdex_ext.tournament_host import registration_counts_by_group, tournament_start_eligibility

        eligible, blocker = await tournament_start_eligibility(tournament)
        counts = await registration_counts_by_group(tournament)
        legacy = counts.get(TournamentGroup.LEGACY.value, 0)
        main = counts.get(TournamentGroup.MAIN.value, 0)
        if eligible:
            host_hint = (
                "-# Someone with **Manage Server** can tap **Start group stage** below, "
                "use `/tournament start`, or `/tournament manage` → **Host**."
            )
        elif blocker:
            host_hint = f"-# {blocker}"
        else:
            host_hint = "-# Wait for the host to start the group stage."
        return (
            f"**{tournament.name}** hasn't started yet "
            f"(Legacy **{legacy}** · Main **{main}**).\n"
            f"{host_hint}\n"
            "-# Matches are round-robin within each group that has **≥2** players."
        )

    if status == TournamentStatus.GROUP_STAGE:
        from fcdex_3_1.fcdex_ext.tournament_match import list_open_group_matches_in_group

        remaining = await list_open_group_matches_in_group(tournament, reg.group)
        if remaining:
            open_lines = [
                f"**#{m.pk}** · <@{m.player1.discord_id}> **vs** <@{m.player2.discord_id}>"
                if m.player2
                else f"**#{m.pk}** · waiting for opponent"
                for m in remaining
            ]
            return (
                f"You're **caught up** for now (`{reg.score}` pts · {reg.get_group_display()}).\n\n"
                f"### Still open in {reg.get_group_display()}\n"
                + "\n".join(open_lines)
                + "\n\n-# These are other players' matches — use **Bracket** in `/tournament view` "
                "or `/tournament bet` with match **#** when it's your turn."
            )
        return (
            f"Your group stage is **done** (`{reg.score}` pts).\n"
            "-# Host: `/tournament manage` → **Host** → **Advance round** to create semifinals."
        )

    if status == TournamentStatus.SEMIFINALS:
        semi_count = await TournamentMatch.objects.filter(
            tournament=tournament, round=TournamentRound.SEMIFINAL
        ).acount()
        if semi_count == 0:
            return (
                "**Semifinals** are active but **no semifinal pairings exist** yet.\n"
                "-# Host: open `/tournament manage` → **Host** → **Sync bracket** "
                "(or **Advance round** if group stage just ended)."
            )
        my_semi = [
            m
            async for m in TournamentMatch.objects.filter(
                tournament=tournament, round=TournamentRound.SEMIFINAL
            ).select_related("player1", "player2")
            if m.player1_id == player.pk or m.player2_id == player.pk
        ]
        if not my_semi:
            return (
                f"You didn't make the **semifinal** cut (`{reg.score}` pts · {reg.get_group_display()}).\n"
                "-# Top **2** non-eliminated players per group advance · see **Standings** in `/tournament view`."
            )
        if all(m.completed for m in my_semi):
            return (
                "Your semifinal is **already complete**.\n"
                "-# Host advances to the grand final when **all** semifinals are done."
            )
        return "Semifinal pairing exists but isn't listed — host should run **Sync bracket** in `/tournament manage`."

    if status == TournamentStatus.FINALS:
        final = await TournamentMatch.objects.filter(tournament=tournament, round=TournamentRound.FINAL).afirst()
        if not final:
            return (
                "**Finals** are active but no grand-final match exists yet.\n"
                "-# Host: `/tournament manage` → **Host** → **Sync bracket** or **Advance round**."
            )
        if player.pk not in (final.player1_id, final.player2_id):
            return (
                f"You're not in the **grand final** (`{reg.score}` pts).\n"
                "-# Only the two semifinal winners battle here — you can `/tournament bet`."
            )
        if final.completed:
            return "**Grand final** is already complete.\n-# Host can **Advance round** to close the tournament."
        return "Grand final exists — try **Sync bracket** if this message persists."

    if status == TournamentStatus.COMPLETED:
        return f"**{tournament.name}** is over.\n-# See **Bracket** in `/tournament view` for results."

    return f"No pending matches in **{tournament.name}**."
