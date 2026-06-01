from __future__ import annotations

from fcdex_3_0.fcdex_ext.battle_engine import BattleBall, BattleInstance, gen_battle

DEFAULT_BOSS_HP = 8_000
DEFAULT_BOSS_ATTACK = 120


def run_boss_battle(team: list[BattleBall], *, boss_name: str = "Raid Boss") -> tuple[BattleInstance, list[str]]:
    boss = BattleBall(instance_id=0, name=boss_name, owner="Boss", health=DEFAULT_BOSS_HP, attack=DEFAULT_BOSS_ATTACK)
    instance = BattleInstance(p1_balls=list(team), p2_balls=[boss])
    log = list(gen_battle(instance))
    return instance, log
