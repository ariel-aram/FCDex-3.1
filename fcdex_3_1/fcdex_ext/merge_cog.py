from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from fcdex_3_1.fcdex_ext.merge_views import build_merge_picker_view

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("fcdex_3_1.merge")

class MergeCog(commands.Cog):
    """Forge matching clubballs through seven merge tiers."""

    def __init__(self, bot: BallsDexBot):
        self.bot = bot

    @app_commands.command(name="merge", description="Pick one clubball and forge it through the FCDex merge ladder")
    async def merge(self, interaction: discord.Interaction):
        layout = await build_merge_picker_view(self.bot, interaction.user.id)
        await interaction.response.send_message(view=layout, ephemeral=True)  # pyright: ignore[reportArgumentType]
