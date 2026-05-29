from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class BattleBall:
    instance_id: int
    name: str
    owner: str
    health: int
    attack: int
    emoji: str = ""
    dead: bool = False


@dataclass
class BattleInstance:
    p1_balls: list[BattleBall] = field(default_factory=list)
    p2_balls: list[BattleBall] = field(default_factory=list)
    winner: str = ""
    turns: int = 0


def get_damage(ball: BattleBall) -> int:
    return max(1, int(ball.attack * random.uniform(0.8, 1.2)))


def attack(current_ball: BattleBall, enemy_balls: list[BattleBall]) -> str:
    alive_balls = [ball for ball in enemy_balls if not ball.dead]
    if not alive_balls:
        return f"{current_ball.owner}'s {current_ball.name} has no targets left."
    enemy = random.choice(alive_balls)
    attack_dealt = get_damage(current_ball)
    enemy.health -= attack_dealt
    if enemy.health <= 0:
        enemy.health = 0
        enemy.dead = True
        return (
            f"{current_ball.owner}'s {current_ball.name} has eliminated "
            f"{enemy.owner}'s {enemy.name}!"
        )
    return (
        f"{current_ball.owner}'s {current_ball.name} dealt {attack_dealt} damage to "
        f"{enemy.owner}'s {enemy.name} ({enemy.health} HP left)."
    )


def random_miss() -> bool:
    return random.randint(0, 100) <= 30


def gen_battle(battle: BattleInstance) -> Iterator[str]:
    turn = 0

    if all(ball.attack <= 0 for ball in battle.p1_balls + battle.p2_balls):
        yield "Everyone stared at each other — nobody wins."
        return

    while any(not ball.dead for ball in battle.p1_balls) and any(not ball.dead for ball in battle.p2_balls):
        alive_p1 = [ball for ball in battle.p1_balls if not ball.dead]
        alive_p2 = [ball for ball in battle.p2_balls if not ball.dead]

        for p1_ball, p2_ball in zip(alive_p1, alive_p2):
            if not p1_ball.dead:
                turn += 1
                if random_miss():
                    yield f"Turn {turn}: {p1_ball.owner}'s {p1_ball.name} missed!"
                else:
                    yield f"Turn {turn}: {attack(p1_ball, battle.p2_balls)}"
                if all(ball.dead for ball in battle.p2_balls):
                    break

            if not p2_ball.dead:
                turn += 1
                if random_miss():
                    yield f"Turn {turn}: {p2_ball.owner}'s {p2_ball.name} missed!"
                else:
                    yield f"Turn {turn}: {attack(p2_ball, battle.p1_balls)}"
                if all(ball.dead for ball in battle.p1_balls):
                    break

    if all(ball.dead for ball in battle.p1_balls):
        battle.winner = battle.p2_balls[0].owner if battle.p2_balls else ""
    elif all(ball.dead for ball in battle.p2_balls):
        battle.winner = battle.p1_balls[0].owner if battle.p1_balls else ""

    battle.turns = turn
