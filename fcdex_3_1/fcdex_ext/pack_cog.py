from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bd_models.models import Player
from fcdex_3_1.fcdex_ext.pack_logic import PackOpenSuccess, grant_pack
from fcdex_3_1.fcdex_ext.pack_views import build_pack_open_layout

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


class PackCog(commands.GroupCog, group_name="pack"):
    """Daily, weekly, and exclusive reward packs."""

    def __init__(self, bot: BallsDexBot):
        self.bot = bot

    async def _open(self, interaction: discord.Interaction, pack_type: str) -> None:
        player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
        guild_id = interaction.guild_id if interaction.guild else None
        ok, result = await grant_pack(player, pack_type, guild_id=guild_id)
        if not ok:
            await interaction.response.send_message(result, ephemeral=True)
            return

        success: PackOpenSuccess = result  # type: ignore[assignment]
        layout, pack_files = build_pack_open_layout(pack_type=pack_type, body=success.message)
        if pack_files:
            await interaction.response.send_message(view=layout, files=pack_files)  # pyright: ignore[reportArgumentType]
        else:
            await interaction.response.send_message(view=layout)  # pyright: ignore[reportArgumentType]

    @app_commands.command(name="daily", description="Open your daily pack — 3 clubballs (24h cooldown)")
    async def daily(self, interaction: discord.Interaction):
        await self._open(interaction, "daily")

    @app_commands.command(name="weekly", description="Open your weekly pack — 5 clubballs (7d cooldown)")
    async def weekly(self, interaction: discord.Interaction):
        await self._open(interaction, "weekly")

    @app_commands.command(name="mascot", description="Open your exclusive pack — 3 clubballs (7d cooldown)")
    async def mascot(self, interaction: discord.Interaction):
        await self._open(interaction, "mascot")

    @app_commands.command(name="exclusive", description="Open your exclusive pack — 3 clubballs (7d cooldown)")
    async def exclusive(self, interaction: discord.Interaction):
        await self._open(interaction, "mascot")
