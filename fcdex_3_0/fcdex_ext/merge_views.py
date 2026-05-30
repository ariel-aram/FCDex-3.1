from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord.ui import ActionRow, Button, Container, Separator, TextDisplay, button

from ballsdex.core.discord import LayoutView
from bd_models.models import BallInstance, Player
from fcdex_3_0.fcdex_ext.bd_helpers import format_instance
from fcdex_3_0.fcdex_ext.merge_logic import MergeValidationError, execute_merge, validate_merge_pair
from fcdex_3_0.fcdex_ext.merge_special import MERGE_SPECIAL_NAME, get_merge_special
from fcdex_3_0.fcdex_ext.views import truncate_text

if TYPE_CHECKING:
    from discord import Interaction

    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("fcdex_3_0.merge.views")


class MergeConfirmRow(ActionRow):
    def __init__(self, owner_id: int, first_id: int, second_id: int):
        super().__init__()
        self.owner_id = owner_id
        self.first_id = first_id
        self.second_id = second_id

    @button(label="Forge merge", style=discord.ButtonStyle.success, emoji="✨")
    async def confirm_button(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This forge is private to you.", ephemeral=True)
            return
        bot = cast("BallsDexBot", interaction.client)
        await interaction.response.defer()
        player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
        first = await BallInstance.objects.aget(pk=self.first_id)
        second = await BallInstance.objects.aget(pk=self.second_id)
        try:
            await validate_merge_pair(player, first, second)
            _, summary, card_file = await execute_merge(
                player, first, second, guild_id=interaction.guild_id, bot=bot
            )
        except MergeValidationError as exc:
            layout = await build_merge_confirm_view(
                bot, self.owner_id, self.first_id, self.second_id, notice=f"❌ {exc.message}"
            )
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
    bot: BallsDexBot,
    owner_id: int,
    first_id: int,
    second_id: int,
    *,
    notice: str = "",
) -> LayoutView:
    first = await BallInstance.objects.aget(pk=first_id)
    second = await BallInstance.objects.aget(pk=second_id)
    first_label = await format_instance(first)
    second_label = await format_instance(second)
    special = await get_merge_special()
    emoji = special.emoji or "✨"

    header = "# ✨ Merge forge"
    if notice:
        header = f"{notice}\n\n{header}"
    body = (
        f"**{first_label}** + **{second_label}**\n"
        f"→ **{emoji} {MERGE_SPECIAL_NAME}** forged card\n"
        f"-# Both cards will be consumed if you forge."
    )

    layout = LayoutView(timeout=300)
    container = Container()
    container.add_item(TextDisplay(truncate_text(f"{header}\n-# {body}")))
    container.add_item(Separator())
    container.add_item(MergeConfirmRow(owner_id, first_id, second_id))
    layout.add_item(container)
    return layout


async def build_merge_done_view(bot: BallsDexBot, owner_id: int, *, notice: str) -> LayoutView:
    layout = LayoutView(timeout=120)
    container = Container()
    container.add_item(TextDisplay(truncate_text(f"{notice}\n\n-# Run `/merge` again to forge another pair.")))
    layout.add_item(container)
    return layout
