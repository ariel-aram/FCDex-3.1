from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ui import ActionRow, Button, Container, Separator, TextDisplay, button

from ballsdex.core.discord import LayoutView
from fcdex_3_0.fcdex_ext.leaderboard_logic import (
    LeaderboardMetric,
    LeaderboardScope,
    fetch_leaderboard,
    fetch_viewer_placement,
    format_leaderboard_body,
    format_viewer_footer,
    normalize_metric_for_scope,
    page_count,
    slice_page,
)
from fcdex_3_0.fcdex_ext.views import truncate_text

if TYPE_CHECKING:
    from discord import Interaction

log = logging.getLogger("fcdex_3_0.leaderboard.views")


class LeaderboardScopeRow(ActionRow):
    def __init__(
        self,
        owner_id: int,
        *,
        scope: LeaderboardScope,
        metric: LeaderboardMetric,
        page: int,
        top: int,
        guild_id: int | None,
        guild_name: str | None,
    ):
        super().__init__()
        self.owner_id = owner_id
        self.scope = scope
        self.metric = metric
        self.page = page
        self.top = top
        self.guild_id = guild_id
        self.guild_name = guild_name

    @button(label="This server", style=discord.ButtonStyle.primary, emoji="🏠")
    async def server_scope(self, interaction: Interaction, button: Button):
        await self._switch(interaction, LeaderboardScope.SERVER)

    @button(label="Global", style=discord.ButtonStyle.secondary, emoji="🌍")
    async def global_scope(self, interaction: Interaction, button: Button):
        await self._switch(interaction, LeaderboardScope.GLOBAL)

    async def _switch(self, interaction: Interaction, scope: LeaderboardScope) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This leaderboard is private to you.", ephemeral=True)
            return
        if scope == LeaderboardScope.SERVER and self.guild_id is None:
            await interaction.response.send_message("Server rankings require a guild context.", ephemeral=True)
            return
        layout = await build_leaderboard_layout(
            self.owner_id,
            scope=scope,
            metric=self.metric,
            page=0,
            top=self.top,
            guild_id=self.guild_id,
            guild_name=self.guild_name,
        )
        await interaction.response.edit_message(view=layout)


class LeaderboardPageRow(ActionRow):
    def __init__(
        self,
        owner_id: int,
        *,
        scope: LeaderboardScope,
        metric: LeaderboardMetric,
        page: int,
        top: int,
        guild_id: int | None,
        guild_name: str | None,
    ):
        super().__init__()
        self.owner_id = owner_id
        self.scope = scope
        self.metric = metric
        self.page = page
        self.top = top
        self.guild_id = guild_id
        self.guild_name = guild_name
        self.page_count = page_count(top)

    @button(label="Prev", style=discord.ButtonStyle.secondary, emoji="◀")
    async def prev_page(self, interaction: Interaction, button: Button):
        if self.page <= 0:
            await interaction.response.send_message("Already on the first page.", ephemeral=True)
            return
        await self._go(interaction, self.page - 1)

    @button(label="Next", style=discord.ButtonStyle.secondary, emoji="▶")
    async def next_page(self, interaction: Interaction, button: Button):
        if self.page >= self.page_count - 1:
            await interaction.response.send_message("Already on the last page.", ephemeral=True)
            return
        await self._go(interaction, self.page + 1)

    async def _go(self, interaction: Interaction, page: int) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This leaderboard is private to you.", ephemeral=True)
            return
        layout = await build_leaderboard_layout(
            self.owner_id,
            scope=self.scope,
            metric=self.metric,
            page=max(0, page),
            top=self.top,
            guild_id=self.guild_id,
            guild_name=self.guild_name,
        )
        await interaction.response.edit_message(view=layout)


async def build_leaderboard_layout(
    owner_id: int,
    *,
    scope: LeaderboardScope,
    metric: LeaderboardMetric,
    page: int = 0,
    top: int = 10,
    guild_id: int | None = None,
    guild_name: str | None = None,
) -> LayoutView:
    metric, _ = normalize_metric_for_scope(metric, scope)
    entries = await fetch_leaderboard(scope=scope, metric=metric, guild_id=guild_id, limit=top)
    pages = page_count(top)
    page = max(0, min(page, pages - 1))
    page_entries = slice_page(entries, page)

    rank, score = await fetch_viewer_placement(owner_id, scope=scope, metric=metric, guild_id=guild_id)
    body = format_leaderboard_body(
        page_entries,
        scope=scope,
        metric=metric,
        page=page,
        total=top,
        guild_name=guild_name,
    )
    viewer_line = format_viewer_footer(rank, score, metric)

    layout = LayoutView(timeout=300)
    container = Container()
    container.add_item(TextDisplay(truncate_text(body)))
    container.add_item(Separator())
    container.add_item(TextDisplay(truncate_text(f"-# {viewer_line}")))

    if guild_id is not None:
        container.add_item(Separator())
        container.add_item(
            LeaderboardScopeRow(
                owner_id,
                scope=scope,
                metric=metric,
                page=page,
                top=top,
                guild_id=guild_id,
                guild_name=guild_name,
            )
        )

    if pages > 1:
        container.add_item(Separator())
        container.add_item(
            LeaderboardPageRow(
                owner_id,
                scope=scope,
                metric=metric,
                page=page,
                top=top,
                guild_id=guild_id,
                guild_name=guild_name,
            )
        )

    layout.add_item(container)
    return layout
