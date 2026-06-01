from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bd_models.models import Player
from fcdex_3_0.fcdex_ext.pack_logic import grant_pack

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


class PackCog(commands.GroupCog, group_name="pack"):
    """Mascot, daily, and weekly reward packs."""

    def __init__(self, bot: BallsDexBot):
        self.bot = bot

    async def _open(self, interaction: discord.Interaction, pack_type: str) -> None:
        player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
        guild_id = interaction.guild_id if interaction.guild else None
        ok, message = await grant_pack(player, pack_type, guild_id=guild_id)
        await interaction.response.send_message(message, ephemeral=not ok)

    @app_commands.command(name="daily", description="Open your daily pack (24h cooldown)")
    async def daily(self, interaction: discord.Interaction):
        await self._open(interaction, "daily")

    @app_commands.command(name="weekly", description="Open your weekly pack (7d cooldown)")
    async def weekly(self, interaction: discord.Interaction):
        await self._open(interaction, "weekly")

    @app_commands.command(name="mascot", description="Open your mascot pack (7d cooldown)")
    async def mascot(self, interaction: discord.Interaction):
        await self._open(interaction, "mascot")
