from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from fcdex_3_1.fcdex_ext.shop_views import build_shop_layout

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


class ShopCog(commands.GroupCog, group_name="shop", group_description="Buy clubball bundles with coins"):
    """Coin shop for configured bundles."""

    def __init__(self, bot: BallsDexBot):
        self.bot = bot

    @app_commands.command(name="browse", description="Browse bundles and purchase with coins")
    async def browse(self, interaction: discord.Interaction):
        layout = await build_shop_layout(interaction.user.id)
        await interaction.response.send_message(view=layout)  # pyright: ignore[reportArgumentType]
