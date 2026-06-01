from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ballsdex.core.utils.transformers import BallEnabledTransform, BallInstanceTransform
from bd_models.models import Ball, BallInstance, Player, balls
from fcdex_3_0.fcdex_ext.boss_logic import DEFAULT_BOSS_HP, run_boss_battle
from fcdex_3_0.fcdex_ext.leaderboard_logic import (
    LeaderboardMetric,
    LeaderboardScope,
    normalize_metric_for_scope,
    resolve_scope,
)
from fcdex_3_0.fcdex_ext.leaderboard_views import build_leaderboard_layout
from fcdex_3_0.fcdex_ext.quest_logic import DAILY_QUESTS, claim_quest, ensure_daily_quests
from fcdex_3_0.fcdex_ext.rarity_views import (
    CATEGORY_MODES,
    build_ball_rarity_layout,
    build_rarity_menu,
    build_rarity_value_layout,
)
from fcdex_3_0.fcdex_ext.regime_data import REGIMES, regime_by_key
from fcdex_3_0.fcdex_ext.shiny_logic import ShinyError, convert_to_shiny
from fcdex_3_0.fcdex_ext.views import build_panel_layout, truncate_text

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


class FcdexCog(commands.GroupCog, group_name="fcdex"):
    """FCDex 3.1 feature directory."""

    def __init__(self, bot: BallsDexBot):
        self.bot = bot

    @app_commands.command(name="menu", description="FCDex 3.1 hub — packs, craft, battles, tournaments, and more")
    async def menu(self, interaction: discord.Interaction):
        layout = build_panel_layout(
            title="FCDex 3.1",
            subtitle="Official extra · Components v2",
            sections=[
                "### 📦 Packs\n`/pack daily` · `/pack weekly` · `/pack mascot`",
                "### 🧪 Craft (SBC)\n`/craft menu` · `/craft complete name:<SBC>`",
                "### ⚔️ Battles\n"
                "`/battle challenge` — lineup panel\n"
                "`/battle random` — instant random 5v5\n"
                "`/battle all` — every clubball you own · `skip_commentary:true`",
                "### 🏟️ Tournaments\n`/tournament view` · `/tournament start` · `/tournament match` · `/tournament bet`",
                "### ✨ Merge · 🏅 Achievements · 📊 Rarity · 🏆 Leaderboard",
                "### 📋 List regime\n`/fcdex list regime:<name>` — browse clubballs by regime",
                "### 👑 Boss · ✨ Shiny · 📜 Quests\n"
                "`/fcdex boss` · `/fcdex shiny` · `/fcdex quests` · `/fcdex quest claim`",
                "### 🛡️ Admin\n`/fcdex owners clubball:<card>` — who owns a rare card (Manage Server)",
            ],
            footer="-# Configure SBCs, achievements & tournaments in admin · FCDex 3.1",
        )
        await interaction.response.send_message(view=layout)  # pyright: ignore[reportArgumentType]

    @app_commands.command(name="list", description="List clubballs in a football regime")
    @app_commands.describe(regime="Regime key or name (e.g. ucl, Premier League)")
    @app_commands.choices(
        regime=[app_commands.Choice(name=r.label, value=r.key) for r in REGIMES]
        + [app_commands.Choice(name="All regimes", value="all")]
    )
    async def list_regime(self, interaction: discord.Interaction, regime: app_commands.Choice[str]):
        if regime.value == "all":
            lines = [f"**{r.label}** (`{r.key}`) — {r.description}" for r in REGIMES]
            body = "\n".join(lines) + "\n\n-# Use `/fcdex list regime:<key>` for clubballs in one regime."
            await interaction.response.send_message(truncate_text(body), ephemeral=True)
            return

        entry = regime_by_key(regime.value)
        if entry is None:
            await interaction.response.send_message("Unknown regime.", ephemeral=True)
            return

        cached = {b.country.lower(): b for b in balls.values()} if balls else {}
        if not cached:
            async for b in Ball.objects.all():
                cached[b.country.lower()] = b

        found: list[str] = []
        missing: list[str] = []
        for name in entry.ball_names:
            ball = cached.get(name.lower())
            if ball:
                found.append(f"{ball.country} · spawn `{ball.rarity}` · {'✅' if ball.enabled else '🚫'}")
            else:
                missing.append(name)

        body = f"### {entry.label}\n{entry.description}\n\n" + (
            "\n".join(found) if found else "*No matches in dex cache.*"
        )
        if missing:
            body += "\n\n-# Not in cache: " + ", ".join(missing)
        await interaction.response.send_message(truncate_text(body), ephemeral=True)

    @app_commands.command(name="owners", description="List players who own a clubball (admin)")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(clubball="Clubball to look up (e.g. rare event cards)")
    async def owners(self, interaction: discord.Interaction, clubball: BallEnabledTransform):
        count = await BallInstance.objects.filter(ball_id=clubball.pk, deleted=False).acount()
        if count == 0:
            await interaction.response.send_message(f"Nobody owns **{clubball.country}** right now.", ephemeral=True)
            return

        lines: list[str] = []
        async for inst in (
            BallInstance.objects.filter(ball_id=clubball.pk, deleted=False)
            .select_related("player")
            .order_by("-pk")[:25]
        ):
            lines.append(f"• <@{inst.player.discord_id}> · card `#{inst.pk}`")

        extra = f"\n-# Showing 25/{count} owners." if count > 25 else ""
        await interaction.response.send_message(
            truncate_text(f"### Owners of **{clubball.country}** ({count})\n" + "\n".join(lines) + extra),
            ephemeral=True,
        )

    @app_commands.command(name="boss", description="Fight the raid boss with your strongest 5 clubballs")
    async def boss(self, interaction: discord.Interaction):
        from fcdex_3_0.fcdex_ext.battle_cog import ball_instance_to_battle_ball

        player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
        instances = [x async for x in BallInstance.objects.filter(player=player, deleted=False)]
        if not instances:
            await interaction.response.send_message("You need clubballs to fight the boss.", ephemeral=True)
            return

        from fcdex_3_0.fcdex_ext.bd_helpers import instance_attack, instance_health

        ranked: list[tuple[int, BallInstance]] = []
        for inst in instances:
            ball = await Ball.objects.aget(pk=inst.ball_id)
            ranked.append((instance_attack(inst, ball) + instance_health(inst, ball), inst))
        ranked.sort(key=lambda x: x[0], reverse=True)
        top = [inst for _, inst in ranked[:5]]
        team = [
            await ball_instance_to_battle_ball(inst, interaction.user.display_name, self.bot)  # type: ignore[arg-type]
            for inst in top
        ]
        instance, log = run_boss_battle(team)
        won = instance.winner and instance.winner != "Boss"
        summary = (
            f"**Raid boss** ({DEFAULT_BOSS_HP:,} HP)\n"
            f"{'🏆 You won!' if won else '💀 Boss wins.'} · Turns: **{instance.turns}**"
        )
        if not won:
            tail = "\n".join(log[-5:])
            summary += f"\n\n{tail}"
        await interaction.response.send_message(truncate_text(summary))

    @app_commands.command(name="shiny", description="Convert 2 copies into one shiny (+25% ATK/HP)")
    @app_commands.describe(clubball="A copy of the clubball you want to make shiny")
    async def shiny(self, interaction: discord.Interaction, clubball: BallInstanceTransform):
        player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
        guild_id = interaction.guild_id if interaction.guild else None
        try:
            message = await convert_to_shiny(player, clubball, guild_id=guild_id)
        except ShinyError as exc:
            await interaction.response.send_message(exc.message, ephemeral=True)
            return
        await interaction.response.send_message(message)

    @app_commands.command(name="quests", description="Daily quest progress")
    async def quests(self, interaction: discord.Interaction):
        player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
        rows = await ensure_daily_quests(player)
        labels = {k: lbl for k, lbl, _, _ in DAILY_QUESTS}
        lines: list[str] = []
        for row in rows:
            status = "✅ claimed" if row.claimed_at else ("🎁 ready" if row.completed_at else "⏳")
            lines.append(f"{status} **{labels.get(row.quest_key, row.quest_key)}** · `{row.progress}/{row.target}`")
        layout = build_panel_layout(
            title="FCDex 3.1 · Daily quests",
            subtitle="Resets at midnight (server time)",
            sections=["\n".join(lines), "-# `/fcdex quest claim:<key>` when complete"],
        )
        await interaction.response.send_message(view=layout)  # pyright: ignore[reportArgumentType]

    @app_commands.command(name="quest", description="Claim a completed daily quest")
    @app_commands.describe(key="Quest key from `/fcdex quests`")
    @app_commands.choices(key=[app_commands.Choice(name=label, value=key) for key, label, _, _ in DAILY_QUESTS])
    async def quest_claim(self, interaction: discord.Interaction, key: app_commands.Choice[str]):
        player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
        await ensure_daily_quests(player)
        ok, message = await claim_quest(player, key.value)
        await interaction.response.send_message(message, ephemeral=not ok)

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
