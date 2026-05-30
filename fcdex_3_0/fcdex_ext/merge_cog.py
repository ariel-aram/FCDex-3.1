from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ballsdex.core.utils.transformers import BallInstanceTransform
from bd_models.models import Player
from fcdex_3_0.fcdex_ext.merge_logic import MergeValidationError, validate_merge_pair
from fcdex_3_0.fcdex_ext.merge_views import build_merge_confirm_view

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("fcdex_3_0.merge")


class MergeCog(commands.Cog):
    """Forge two clubballs into one FCDex merge special card."""

    def __init__(self, bot: BallsDexBot):
        self.bot = bot

    @app_commands.command(
        name="merge",
        description="Sacrifice two clubballs to forge one FCDex merge special card",
    )
    async def merge(
        self,
        interaction: discord.Interaction,
        first: BallInstanceTransform,
        second: BallInstanceTransform,
    ):
        player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
        try:
            await validate_merge_pair(player, first, second)
        except MergeValidationError as exc:
            await interaction.response.send_message(exc.message, ephemeral=True)
            return

        layout = await build_merge_confirm_view(
            self.bot, interaction.user.id, first.pk, second.pk
        )
        await interaction.response.send_message(view=layout)  # pyright: ignore[reportArgumentType]
