from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from fcdex_3_1.fcdex_ext.merge_debug import merge_debug
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
        merge_debug("H5", "merge_cog.merge:entry", "slash merge opened", {"user_id": interaction.user.id})
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.HTTPException as exc:
            merge_debug(
                "H1",
                "merge_cog.merge:defer_failed",
                "slash defer failed",
                {"status": getattr(exc, "status", None), "code": getattr(exc, "code", None)},
            )
            try:
                await interaction.response.send_message(
                    "❌ Could not open the forge panel. Try again in a moment.", ephemeral=True
                )
            except discord.HTTPException:
                pass
            return
        try:
            layout = await build_merge_picker_view(self.bot, interaction.user.id)
            await interaction.edit_original_response(view=layout)  # pyright: ignore[reportArgumentType]
            merge_debug("H5", "merge_cog.merge:ok", "panel shown", {"user_id": interaction.user.id})
        except Exception as exc:
            merge_debug(
                "H5",
                "merge_cog.merge:failed",
                "open merge panel failed",
                {"error": type(exc).__name__, "msg": str(exc)[:240]},
            )
            log.exception("Failed to open merge panel for user %s", interaction.user.id)
            try:
                await interaction.edit_original_response(
                    content=f"❌ Could not open merge forge: **{type(exc).__name__}** — {str(exc)[:200]}"
                )
            except discord.HTTPException:
                try:
                    await interaction.followup.send(
                        f"❌ Could not open merge forge: **{type(exc).__name__}** — {str(exc)[:200]}",
                        ephemeral=True,
                    )
                except discord.HTTPException:
                    pass
