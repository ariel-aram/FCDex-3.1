from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bd_models.models import Player
from fcdex_3_1.fcdex_ext.pack_logic import PackOpenSuccess, grant_pack, render_pack_card_file
from fcdex_3_1.fcdex_ext.views import build_panel_layout

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


class PackCog(commands.GroupCog, group_name="pack"):
    """Mascot, daily, and weekly reward packs."""

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
        layout = build_panel_layout(title="FCDex 3.1 · Pack opened", sections=[success.message])
        attachments: list[discord.File] = []
        if success.instances and success.balls:
            card = await render_pack_card_file(success.instances[0], success.balls[0], bot=self.bot, index=1)
            if card:
                attachments.append(card)

        send_kwargs: dict = {"view": layout}
        if attachments:
            send_kwargs["attachments"] = attachments
        await interaction.response.send_message(**send_kwargs)  # pyright: ignore[reportArgumentType]

    @app_commands.command(name="daily", description="Open your daily pack (24h cooldown)")
    async def daily(self, interaction: discord.Interaction):
        await self._open(interaction, "daily")

    @app_commands.command(name="weekly", description="Open your weekly pack (7d cooldown)")
    async def weekly(self, interaction: discord.Interaction):
        await self._open(interaction, "weekly")

    @app_commands.command(name="mascot", description="Open your mascot pack (7d cooldown)")
    async def mascot(self, interaction: discord.Interaction):
        await self._open(interaction, "mascot")
