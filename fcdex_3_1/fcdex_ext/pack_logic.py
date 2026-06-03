from __future__ import annotations

import logging
import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

import discord
from django.utils import timezone

from bd_models.models import Ball, BallInstance, Player, balls
from fcdex_3_1.models import PackClaim, PackType

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("fcdex_3_1.pack")

PACK_COOLDOWNS = {
    PackType.DAILY: timedelta(hours=24),
    PackType.WEEKLY: timedelta(days=7),
    PackType.MASCOT: timedelta(days=7),
}

PACK_REWARDS = {
    PackType.DAILY: {"coins_min": 250, "coins_max": 750, "balls": 3},
    PackType.WEEKLY: {"coins_min": 1_000, "coins_max": 2_500, "balls": 5},
    PackType.MASCOT: {"coins_min": 500, "coins_max": 1_500, "balls": 3},
}


@dataclass(frozen=True)
class PackOpenSuccess:
    message: str
    instances: tuple[BallInstance, ...]
    balls: tuple[Ball, ...]


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


def format_pack_open_message(pack_label: str, coins: int, ball_names: list[str]) -> str:
    if not ball_names:
        ball_text = "no clubballs (dex cache empty)"
    elif len(ball_names) == 1:
        ball_text = ball_names[0]
    else:
        ball_text = ", ".join(f"**{name}**" for name in ball_names)
    return f"**+{coins:,}** coins\n**{len(ball_names)}** clubball(s): {ball_text}"


def collection_card_file(ball: Ball, *, index: int = 1) -> discord.File | None:
    card = ball.collection_card
    if not card:
        return None
    ext = card.name.rsplit(".", 1)[-1]
    return discord.File(str(card.path), filename=f"pack-card-{index}.{ext}")


async def render_pack_card_file(
    instance: BallInstance, ball: Ball, *, bot: BallsDexBot, index: int = 1
) -> discord.File | None:
    try:
        with ThreadPoolExecutor() as pool:
            buffer = await bot.loop.run_in_executor(pool, instance.draw_card)
        return discord.File(buffer, f"pack-card-{index}.webp")
    except Exception:
        log.debug("draw_card failed for pack reward, falling back to collection_card", exc_info=True)
        return collection_card_file(ball, index=index)


async def grant_pack(player: Player, pack_type: str, *, guild_id: int | None) -> tuple[bool, str | PackOpenSuccess]:
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
    granted_balls: list[Ball] = []
    granted_instances: list[BallInstance] = []
    for _ in range(rewards["balls"]):
        if not pool:
            break
        ball = random.choice(pool)
        instance = await BallInstance.objects.acreate(
            ball=ball, player=player, attack_bonus=0, health_bonus=0, server_id=guild_id
        )
        granted_balls.append(ball)
        granted_instances.append(instance)

    await PackClaim.objects.acreate(player=player, pack_type=pack_type)
    if pack_type == PackType.DAILY:
        from fcdex_3_1.fcdex_ext.quest_logic import bump_quest

        await bump_quest(player, "pack_daily")
    message = format_pack_open_message(pack_enum.label, coins, [b.country for b in granted_balls])
    return True, PackOpenSuccess(message=message, instances=tuple(granted_instances), balls=tuple(granted_balls))
