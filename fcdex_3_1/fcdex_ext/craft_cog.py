from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bd_models.models import Player
from fcdex_3_1.fcdex_ext.craft_logic import CraftError, complete_sbc
from fcdex_3_1.fcdex_ext.views import build_panel_layout
from fcdex_3_1.models import SBCRecipe

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


class CraftCog(commands.GroupCog, group_name="craft"):
    """SBC crafting — complete squad-building challenges without tickets."""

    def __init__(self, bot: BallsDexBot):
        self.bot = bot

    @app_commands.command(name="menu", description="List active SBC recipes")
    async def menu(self, interaction: discord.Interaction):
        lines: list[str] = []
        async for recipe in SBCRecipe.objects.filter(enabled=True).select_related("required_ball", "reward_ball"):
            req = recipe.required_ball.country
            rew = recipe.reward_ball.country
            lines.append(
                f"**{recipe.name}** — **{recipe.required_count}×** {req} → **{rew}**"
                + (f" · **+{recipe.reward_money:,}** coins" if recipe.reward_money else "")
            )
        body = "\n".join(lines) if lines else "*No SBC recipes yet — add them in the admin panel under FCDex 3.1.*"
        layout = build_panel_layout(
            title="FCDex 3.1 · Craft",
            subtitle="Squad Building Challenges",
            sections=[body, "-# Use `/craft complete name:<SBC>` to submit cards"],
        )
        await interaction.response.send_message(view=layout)  # pyright: ignore[reportArgumentType]

    @app_commands.command(name="complete", description="Submit clubballs for an SBC by recipe name")
    @app_commands.describe(name="SBC recipe name (see `/craft menu`)")
    async def complete(self, interaction: discord.Interaction, name: str):
        try:
            recipe = await SBCRecipe.objects.select_related("required_ball", "reward_ball").aget(
                name__iexact=name.strip(), enabled=True
            )
        except SBCRecipe.DoesNotExist:
            await interaction.response.send_message(f"No active SBC named **{name}**.", ephemeral=True)
            return

        player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
        guild_id = interaction.guild_id if interaction.guild else None
        try:
            message = await complete_sbc(player, recipe, guild_id=guild_id)
        except CraftError as exc:
            await interaction.response.send_message(exc.message, ephemeral=True)
            return
        layout = build_panel_layout(title="FCDex 3.1 · SBC complete", sections=[message])
        await interaction.response.send_message(view=layout)  # pyright: ignore[reportArgumentType]
