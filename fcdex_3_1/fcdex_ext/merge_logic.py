from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import discord
from django.db.models import Q

from bd_models.models import Ball, BallInstance, Player, Special, balls
from fcdex_3_0.fcdex_ext.bd_helpers import format_instance, get_ball, instance_attack, instance_health
from fcdex_3_0.fcdex_ext.merge_levels import (
    MAX_MERGE_LEVEL,
    detect_target_level,
    get_merge_level_config,
    resolve_merge_level_from_bonuses,
)
from fcdex_3_0.fcdex_ext.merge_limits import (
    MERGE_WEEKLY_LIMIT,
    calendar_week_bounds,
    merge_special_blocked_message,
    weekly_merge_limit_message,
    weekly_merge_limit_reached,
)
from fcdex_3_0.fcdex_ext.merge_special import MERGE_SPECIAL_NAME, get_merge_special
from fcdex_3_0.fcdex_ext.services import increment_stat
from fcdex_3_0.models import MergeLog
from settings.models import settings

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


class MergeValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def count_player_merges_this_week(player: Player) -> int:
    week_start, week_end = calendar_week_bounds()
    return await MergeLog.objects.filter(player=player, created_at__gte=week_start, created_at__lt=week_end).acount()


async def instance_has_merge_special(instance: BallInstance) -> bool:
    merge_special = await get_merge_special()
    if instance.special_id == merge_special.pk:
        return True
    if instance.special_id:
        special = await Special.objects.filter(pk=instance.special_id).afirst()
        if special is not None and special.name == MERGE_SPECIAL_NAME:
            return True
    return False


async def get_instance_merge_level(instance: BallInstance) -> int | None:
    if not await instance_has_merge_special(instance):
        return 0
    return resolve_merge_level_from_bonuses(instance.attack_bonus, instance.health_bonus)


async def is_common_ball(ball: Ball) -> bool:
    enabled = [entry for entry in balls.values() if entry.enabled]
    if not enabled:
        enabled = [ball async for ball in Ball.objects.filter(enabled=True)]
    if not enabled:
        return False
    min_rarity = min(entry.rarity for entry in enabled)
    return ball.rarity == min_rarity


async def instance_already_used_in_merge(instance_id: int) -> bool:
    if await MergeLog.objects.filter(
        Q(source_ball1_id=instance_id) | Q(source_ball2_id=instance_id) | Q(result_ball_id=instance_id)
    ).aexists():
        return True
    return await MergeLog.objects.filter(source_ids__contains=instance_id).aexists()


def _duplicate_instance_ids(instances: list[BallInstance]) -> set[int]:
    seen: set[int] = set()
    duplicates: set[int] = set()
    for instance in instances:
        if instance.pk in seen:
            duplicates.add(instance.pk)
        seen.add(instance.pk)
    return duplicates


async def validate_merge_batch(player: Player, instances: list[BallInstance]) -> int:
    if len(instances) < 2:
        raise MergeValidationError("Pick at least two clubballs to forge.")

    duplicates = _duplicate_instance_ids(instances)
    if duplicates:
        raise MergeValidationError("Each card can only be selected once.")

    target_level = detect_target_level(len(instances))
    if target_level is None:
        valid = ", ".join(str(get_merge_level_config(level).input_count) for level in range(1, MAX_MERGE_LEVEL + 1))
        raise MergeValidationError(
            f"This forge needs a valid card count for levels 1–{MAX_MERGE_LEVEL} "
            f"({valid} cards). You picked {len(instances)}."
        )

    cfg = get_merge_level_config(target_level)
    ball_ids = {instance.ball_id for instance in instances}
    if len(ball_ids) != 1:
        raise MergeValidationError("All inputs must be the same clubball type (same country).")

    required_input_level = target_level - 1
    merges_this_week = await count_player_merges_this_week(player)
    if weekly_merge_limit_reached(merges_this_week):
        raise MergeValidationError(weekly_merge_limit_message(limit=MERGE_WEEKLY_LIMIT))

    for instance in instances:
        if instance.player_id != player.pk:
            raise MergeValidationError(f"All {settings.plural_collectible_name} must belong to you.")
        if instance.deleted:
            raise MergeValidationError("One of these cards is no longer available.")
        if await instance_already_used_in_merge(instance.pk):
            raise MergeValidationError("One of these cards was already used in a merge.")
        if await instance.is_locked():
            raise MergeValidationError("One of these cards is locked for a trade.")

        input_level = await get_instance_merge_level(instance)
        if input_level is None:
            raise MergeValidationError(
                "One of these cards is a legacy merge result and can't be used in the 7-tier forge."
            )
        if input_level == MAX_MERGE_LEVEL:
            raise MergeValidationError(merge_special_blocked_message(MERGE_SPECIAL_NAME, max_level=MAX_MERGE_LEVEL))
        if input_level != required_input_level:
            if required_input_level == 0:
                raise MergeValidationError(
                    f"Forge **level {target_level}** needs {cfg.input_count} plain **common** copies "
                    "of the same clubball."
                )
            raise MergeValidationError(
                f"Forge **level {target_level}** needs {cfg.input_count} forge **level {required_input_level}** "
                "cards of the same clubball."
            )

        if required_input_level == 0:
            ball = await get_ball(instance)
            if not await is_common_ball(ball):
                raise MergeValidationError(
                    f"Forge **level 1** only accepts **common** clubballs ({cfg.input_count} matching copies)."
                )

    return target_level


async def consume_merge_inputs(instance_ids: list[int]) -> None:
    consumed = await BallInstance.objects.filter(pk__in=instance_ids, deleted=False).aupdate(deleted=True)
    if consumed != len(instance_ids):
        raise MergeValidationError("One of these cards is no longer available.")


def preview_merge_stats(ball: Ball, target_level: int) -> tuple[int, int, int, int]:
    cfg = get_merge_level_config(target_level)
    base_attack = ball.attack
    base_health = ball.health
    preview = BallInstance(attack_bonus=cfg.attack_bonus, health_bonus=cfg.health_bonus)
    preview.ball_id = ball.pk
    return (base_attack, base_health, instance_attack(preview, ball), instance_health(preview, ball))


async def execute_merge(
    player: Player, instances: list[BallInstance], *, guild_id: int | None, bot: BallsDexBot
) -> tuple[BallInstance, str, discord.File, int]:
    target_level = await validate_merge_batch(player, instances)
    cfg = get_merge_level_config(target_level)
    merge_special = await get_merge_special()
    result_ball = await get_ball(instances[0])

    instance_ids = [instance.pk for instance in instances]
    await consume_merge_inputs(instance_ids)
    for instance in instances:
        instance.deleted = True

    new_instance = await BallInstance.objects.acreate(
        ball=result_ball,
        player=player,
        special=merge_special,
        attack_bonus=cfg.attack_bonus,
        health_bonus=cfg.health_bonus,
        server_id=guild_id,
    )

    await MergeLog.objects.acreate(
        player=player,
        source_ball1=instances[0],
        source_ball2=instances[1] if len(instances) > 1 else None,
        result_ball=new_instance,
        merge_level=target_level,
        source_ids=instance_ids,
    )
    await increment_stat(player, "merges_completed")
    from fcdex_3_0.fcdex_ext.quest_logic import bump_quest

    await bump_quest(player, "merge_once")

    with ThreadPoolExecutor() as pool:
        buffer = await bot.loop.run_in_executor(pool, new_instance.draw_card)

    result_label = await format_instance(new_instance)
    _, _, final_attack, final_health = preview_merge_stats(result_ball, target_level)
    special_tag = merge_special.emoji or "✨"
    summary = (
        f"{special_tag} **{merge_special.name}** · forge **level {target_level}** complete!\n"
        f"You forged `{result_label}` — **`+{cfg.attack_bonus}%` ATK / `+{cfg.health_bonus}%` HP** "
        f"(≈ **{final_attack}** ATK · **{final_health}** HP)."
    )
    return new_instance, summary, discord.File(buffer, "card.webp"), target_level
