from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ballsdex.core.utils.transformers import BallEnabledTransform
from fcdex_3_0.fcdex_ext.leaderboard_logic import (
    LeaderboardMetric,
    LeaderboardScope,
    normalize_metric_for_scope,
    resolve_scope,
)
from fcdex_3_0.fcdex_ext.leaderboard_views import build_leaderboard_layout
from fcdex_3_0.fcdex_ext.rarity_views import (
    CATEGORY_MODES,
    build_ball_rarity_layout,
    build_rarity_menu,
    build_rarity_value_layout,
)
from fcdex_3_0.fcdex_ext.views import build_panel_layout

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


class FcdexCog(commands.GroupCog, group_name="fcdex"):
    """FCDex 3.0 feature directory."""

    def __init__(self, bot: BallsDexBot):
        self.bot = bot

    @app_commands.command(name="menu", description="FCDex 3.0 hub — battles, tournaments, merge forge, achievements")
    async def menu(self, interaction: discord.Interaction):
        layout = build_panel_layout(
            title="FCDex 3.0",
            subtitle="Official extra · Components v2 hubs",
            sections=[
                "### ⚔️ Battles\n`/battle challenge` — challenge a player\n`/battle card` — manage your battle lineup",
                "### 🏟️ Tournaments\n"
                "`/tournament view` — hub, join, standings, bracket\n"
                "`/tournament match` — battles, bounties, verified wins\n"
                "`/tournament bet` — wager on match outcomes\n"
                "`/tournament manage` — admin panel (Manage Server)",
                "### ✨ Merge\n"
                "`/merge` — 7-tier forge · same clubball only · L1=10 commons → L7=2 cards "
                "(5/week · max tier can't merge again)",
                "### 🏅 Achievements\n`/achievement menu` — catalog, progress, claim rewards",
                "### 📊 Rarity\n`/fcdex rarity` — live dex spawn weights · lookup · spawnable lists",
                "### 🏆 Leaderboard\n"
                "`/fcdex leaderboard` — server clubball rankings (default in guild) · toggle **Global** for worldwide stats",
            ],
            footer="-# Configure achievements & tournaments in the admin panel under FCDex 3.0",
        )
        await interaction.response.send_message(view=layout)  # pyright: ignore[reportArgumentType]

    @app_commands.command(name="rarity", description="Live BallsDex spawn weights, rarity lookup, and clubball browse")
    @app_commands.describe(
        clubball="Look up one clubball's dex spawn weight",
        rarity="Show spawnable clubballs at this spawn weight (lower = rarer)",
        category="Browse spawnable or unspawnable clubballs",
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="Spawnable", value="spawnable"),
            app_commands.Choice(name="Unspawnable", value="unspawnable"),
        ]
    )
    async def rarity(
        self,
        interaction: discord.Interaction,
        clubball: BallEnabledTransform | None = None,
        rarity: float | None = None,
        category: app_commands.Choice[str] | None = None,
    ):
        if clubball is not None and rarity is not None:
            await interaction.response.send_message("Pick either **clubball** or **rarity**, not both.", ephemeral=True)
            return
        if clubball is not None:
            layout = await build_ball_rarity_layout(clubball)
            await interaction.response.send_message(view=layout)  # pyright: ignore[reportArgumentType]
            return
        if rarity is not None:
            layout = await build_rarity_value_layout(rarity)
            await interaction.response.send_message(view=layout)  # pyright: ignore[reportArgumentType]
            return
        mode = category.value if category else "overview"
        if mode not in CATEGORY_MODES and mode != "overview":
            await interaction.response.send_message("Unknown rarity category.", ephemeral=True)
            return
        layout = await build_rarity_menu(interaction.user.id, mode=mode)
        await interaction.response.send_message(view=layout)  # pyright: ignore[reportArgumentType]

    @app_commands.command(name="leaderboard", description="Rank players by clubballs or FCDex stats")
    @app_commands.describe(
        scope="Server rankings (clubballs caught here) or global worldwide",
        sort="Metric to rank by",
        top="How many players to include",
    )
    @app_commands.choices(
        scope=[
            app_commands.Choice(name="This server", value="server"),
            app_commands.Choice(name="Global", value="global"),
        ],
        sort=[
            app_commands.Choice(name="Clubballs", value="clubballs"),
            app_commands.Choice(name="Battles won", value="battles_won"),
            app_commands.Choice(name="Merges", value="merges"),
            app_commands.Choice(name="Tournament wins", value="tournament_wins"),
        ],
        top=[app_commands.Choice(name="Top 10", value="10"), app_commands.Choice(name="Top 20", value="20")],
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        scope: app_commands.Choice[str] | None = None,
        sort: app_commands.Choice[str] | None = None,
        top: app_commands.Choice[str] | None = None,
    ):
        in_guild = interaction.guild is not None
        in_dm = interaction.guild is None
        requested_scope = LeaderboardScope(scope.value) if scope else None
        effective_scope, scope_notice = resolve_scope(requested_scope, in_guild=in_guild, in_dm=in_dm)

        metric = LeaderboardMetric(sort.value) if sort else LeaderboardMetric.CLUBBALLS
        metric, metric_notice = normalize_metric_for_scope(metric, effective_scope)
        limit = int(top.value) if top else 10

        notices = [msg for msg in (scope_notice, metric_notice) if msg]
        if notices:
            await interaction.response.send_message("\n".join(notices), ephemeral=True)

        guild_id = interaction.guild.id if interaction.guild else None
        guild_name = interaction.guild.name if interaction.guild else None
        layout = await build_leaderboard_layout(
            interaction.client,
            interaction.user.id,
            scope=effective_scope,
            metric=metric,
            page=0,
            top=limit,
            guild_id=guild_id,
            guild_name=guild_name,
        )
        if notices:
            await interaction.followup.send(view=layout)  # pyright: ignore[reportArgumentType]
        else:
            await interaction.response.send_message(view=layout)  # pyright: ignore[reportArgumentType]
