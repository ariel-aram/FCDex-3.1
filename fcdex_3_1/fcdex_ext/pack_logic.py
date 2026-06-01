from __future__ import annotations

import random
from datetime import timedelta

from django.utils import timezone

from bd_models.models import Ball, BallInstance, Player, balls
from fcdex_3_1.models import PackClaim, PackType

PACK_COOLDOWNS = {
    PackType.DAILY: timedelta(hours=24),
    PackType.WEEKLY: timedelta(days=7),
    PackType.MASCOT: timedelta(days=7),
}

PACK_REWARDS = {
    PackType.DAILY: {"coins_min": 250, "coins_max": 750, "balls": 1},
    PackType.WEEKLY: {"coins_min": 1_000, "coins_max": 2_500, "balls": 2},
    PackType.MASCOT: {"coins_min": 500, "coins_max": 1_500, "balls": 1},
}


async def last_pack_claim(player: Player, pack_type: str) -> PackClaim | None:
    return await PackClaim.objects.filter(player=player, pack_type=pack_type).order_by("-claimed_at").afirst()


def cooldown_remaining(last: PackClaim | None, pack_type: str) -> timedelta | None:
    if last is None:
        return None
    delta = PACK_COOLDOWNS[PackType(pack_type)]
    ready_at = last.claimed_at + delta
    now = timezone.now()
    if now >= ready_at:
        return None
    return ready_at - now


def _spawnable_balls() -> list[Ball]:
    cached = list(balls.values()) if balls else []
    return [b for b in cached if b.enabled]


async def grant_pack(player: Player, pack_type: str, *, guild_id: int | None) -> tuple[bool, str]:
    pack_enum = PackType(pack_type)
    last = await last_pack_claim(player, pack_type)
    if remaining := cooldown_remaining(last, pack_type):
        hours = int(remaining.total_seconds() // 3600)
        mins = int((remaining.total_seconds() % 3600) // 60)
        return False, f"**{pack_enum.label}** is on cooldown — try again in **{hours}h {mins}m**."

    rewards = PACK_REWARDS[pack_enum]
    coins = random.randint(rewards["coins_min"], rewards["coins_max"])
    if coins:
        await player.add_money(coins)

    pool = _spawnable_balls()
    if not pool and Ball.objects.exists():
        pool = [b async for b in Ball.objects.filter(enabled=True)]
    granted: list[str] = []
    for _ in range(rewards["balls"]):
        if not pool:
            break
        ball = random.choice(pool)
        await BallInstance.objects.acreate(ball=ball, player=player, attack_bonus=0, health_bonus=0, server_id=guild_id)
        granted.append(ball.country)

    await PackClaim.objects.acreate(player=player, pack_type=pack_type)
    if pack_type == PackType.DAILY:
        from fcdex_3_1.fcdex_ext.quest_logic import bump_quest

        await bump_quest(player, "pack_daily")
    ball_text = ", ".join(granted) if granted else "no clubball (dex cache empty)"
    return True, f"Opened **{pack_enum.label}**! **+{coins:,}** coins · {ball_text}"
