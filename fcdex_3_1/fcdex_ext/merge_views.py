from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import app_commands
from discord.ui import ActionRow, Button, Container, Separator, TextDisplay, button
from django.db.models import Q

from ballsdex.core.discord import LayoutView
from ballsdex.core.utils.transformers import BallInstanceTransformer
from bd_models.models import BallInstance, Player
from fcdex_3_1.fcdex_ext.bd_helpers import format_instance, get_ball
from fcdex_3_1.fcdex_ext.merge_levels import (
    MAX_MERGE_LEVEL,
    format_level_table_row,
    get_merge_level_config,
    get_merge_level_emoji,
)
from fcdex_3_1.fcdex_ext.merge_logic import (
    MergeValidationError,
    execute_merge,
    get_instance_merge_level,
    preview_merge_stats,
    validate_merge_batch,
)
from fcdex_3_1.fcdex_ext.merge_quota import (
    format_quota_status_block,
    get_merge_quota_settings,
    get_merge_quota_snapshot,
)
from fcdex_3_1.fcdex_ext.merge_special import MERGE_SPECIAL_NAME, get_merge_special
from fcdex_3_1.fcdex_ext.views import truncate_text

if TYPE_CHECKING:
    from discord import Interaction

    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("fcdex_3_1.merge.views")


class MergeBallInstanceTransformer(BallInstanceTransformer):
    """Card picker for /merge — hides max-tier (L7) forge results."""

    def get_queryset(self):
        max_cfg = get_merge_level_config(MAX_MERGE_LEVEL)
        return (
            super()
            .get_queryset()
            .filter(deleted=False)
            .exclude(
                Q(special__name=MERGE_SPECIAL_NAME)
                & Q(attack_bonus=max_cfg.attack_bonus)
                & Q(health_bonus=max_cfg.health_bonus)
            )
        )

    async def get_options(self, interaction: discord.Interaction, value: str) -> list[app_commands.Choice[int]]:
        choices = await super().get_options(interaction, value)
        if not choices:
            return choices

        pks = [int(choice.value, 16) for choice in choices]
        instances = {
            instance.pk: instance
            async for instance in BallInstance.objects.filter(pk__in=pks).select_related("special")
        }

        enriched: list[app_commands.Choice[int]] = []
        for choice in choices:
            instance = instances.get(int(choice.value, 16))
            if instance is None:
                enriched.append(choice)
                continue
            merge_level = await get_instance_merge_level(instance)
            if merge_level:
                prefix = f"{get_merge_level_emoji(merge_level)} "
                name = f"{prefix}{choice.name}"[:100]
                enriched.append(app_commands.Choice(name=name, value=choice.value))
            else:
                enriched.append(choice)
        return enriched


MergeBallInstanceTransform = app_commands.Transform[BallInstance, MergeBallInstanceTransformer]


class MergeConfirmRow(ActionRow):
    def __init__(self, owner_id: int, instance_ids: list[int]):
        super().__init__()
        self.owner_id = owner_id
        self.instance_ids = instance_ids

    @button(label="Forge merge", style=discord.ButtonStyle.success, emoji="✨")
    async def confirm_button(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This forge is private to you.", ephemeral=True)
            return
        bot = cast("BallsDexBot", interaction.client)
        await interaction.response.defer()
        player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
        instances = [
            instance
            async for instance in BallInstance.objects.select_related("special").filter(pk__in=self.instance_ids)
        ]
        instances.sort(key=lambda item: self.instance_ids.index(item.pk))
        try:
            await validate_merge_batch(player, instances)
            _, summary, card_file, _ = await execute_merge(player, instances, guild_id=interaction.guild_id, bot=bot)
        except MergeValidationError as exc:
            layout = await build_merge_confirm_view(bot, self.owner_id, self.instance_ids, notice=f"❌ {exc.message}")
            await interaction.edit_original_response(view=layout)
            return

        layout = await build_merge_done_view(bot, self.owner_id, notice=summary)
        await interaction.edit_original_response(view=layout, attachments=[card_file])

    @button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This forge is private to you.", ephemeral=True)
            return
        layout = LayoutView(timeout=120)
        container = Container()
        container.add_item(TextDisplay("Merge cancelled — nothing was consumed."))
        layout.add_item(container)
        await interaction.response.edit_message(view=layout)


async def build_merge_confirm_view(
    bot: BallsDexBot, owner_id: int, instance_ids: list[int], *, notice: str = ""
) -> LayoutView:
    player = await Player.objects.aget(discord_id=owner_id)
    instances = [instance async for instance in BallInstance.objects.filter(pk__in=instance_ids)]
    instances.sort(key=lambda item: instance_ids.index(item.pk))
    labels = [await format_instance(instance) for instance in instances]
    ball = await get_ball(instances[0])
    special = await get_merge_special()
    quota_settings = await get_merge_quota_settings()
    quota_snapshot = await get_merge_quota_snapshot(player)
    quota_block = format_quota_status_block(quota_snapshot, settings_period_days=quota_settings.period_days)

    try:
        target_level = await validate_merge_batch(player, instances)
        cfg = get_merge_level_config(target_level)
        level_emoji = get_merge_level_emoji(target_level)
        base_attack, base_health, final_attack, final_health = preview_merge_stats(ball, target_level)
        level_line = (
            f"{level_emoji} **Forge L{target_level}** · `{len(instances)}` inputs → "
            f"**{special.emoji or level_emoji} {MERGE_SPECIAL_NAME}** `{ball.country}`\n"
            f"Stats: **{base_attack}**/{base_health} → **{final_attack}** ATK · **{final_health}** HP "
            f"(`+{cfg.attack_bonus}%` / `+{cfg.health_bonus}%`)"
        )
    except MergeValidationError as exc:
        level_line = f"❌ {exc.message}"

    header = "# ✨ Merge forge"
    if notice:
        header = f"{notice}\n\n{header}"

    card_list = "\n".join(f"• `{label}`" for label in labels)
    tier_guide = " · ".join(format_level_table_row(level) for level in range(1, MAX_MERGE_LEVEL + 1))
    body = (
        f"{level_line}\n\n"
        f"**Inputs ({len(instances)})**\n{card_list}\n\n"
        f"{quota_block}\n\n"
        f"-# Same **clubball** only (not just country) · L1 needs **common** copies · "
        f"forge **L1→L2→…→L7** · {get_merge_level_emoji(MAX_MERGE_LEVEL)} **L{MAX_MERGE_LEVEL}** can't merge again.\n"
        f"-# Tier guide: {tier_guide}"
    )

    layout = LayoutView(timeout=300)
    container = Container()
    container.add_item(TextDisplay(truncate_text(f"{header}\n\n{body}")))
    container.add_item(Separator())
    container.add_item(MergeConfirmRow(owner_id, instance_ids))
    layout.add_item(container)
    return layout


async def build_merge_done_view(bot: BallsDexBot, owner_id: int, *, notice: str) -> LayoutView:
    layout = LayoutView(timeout=120)
    container = Container()
    container.add_item(TextDisplay(truncate_text(f"{notice}\n\n-# Run `/merge` again to forge another batch.")))
    layout.add_item(container)
    return layout
