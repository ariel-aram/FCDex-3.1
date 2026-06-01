from __future__ import annotations

from fcdex_3_1.fcdex_ext.battle_engine import BattleBall, BattleInstance, gen_battle


def run_full_roster_battle(p1: list[BattleBall], p2: list[BattleBall]) -> tuple[BattleInstance, list[str]]:
    instance = BattleInstance(p1_balls=list(p1), p2_balls=list(p2))
    log = list(gen_battle(instance))
    return instance, log


def summarize_battle(instance: BattleInstance, log: list[str], *, skip_commentary: bool) -> str:
    winner = instance.winner or "Draw"
    if skip_commentary:
        return f"**Battle All complete** · Winner: **{winner}** · Turns: **{instance.turns}**"
    tail = "\n".join(log[-8:]) if log else ""
    return f"**Battle All complete** · Winner: **{winner}** · Turns: **{instance.turns}**\n\n{tail}"
