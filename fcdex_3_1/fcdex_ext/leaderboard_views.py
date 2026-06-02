from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ui import ActionRow, Button, Container, Section, Separator, TextDisplay, Thumbnail, button

from ballsdex.core.discord import LayoutView
from fcdex_3_1.fcdex_ext.leaderboard_logic import (
    LeaderboardMetric,
    LeaderboardProfile,
    LeaderboardScope,
    default_profile,
    fetch_leaderboard,
    fetch_viewer_placement,
    format_entry_line,
    format_leaderboard_header,
    format_leaderboard_page_footer,
    format_viewer_footer,
    normalize_metric_for_scope,
    page_count,
    resolve_leaderboard_display_name,
    slice_page,
)
from fcdex_3_1.fcdex_ext.views import truncate_text

if TYPE_CHECKING:
    from discord import Interaction

log = logging.getLogger("fcdex_3_1.leaderboard.views")


def profile_from_user(user: discord.User | discord.Member) -> LeaderboardProfile:
    return LeaderboardProfile(
        display_name=resolve_leaderboard_display_name(username=user.name), avatar_url=str(user.display_avatar.url)
    )


async def resolve_leaderboard_profiles(
    client: discord.Client, discord_ids: list[int], *, guild: discord.Guild | None = None
) -> dict[int, LeaderboardProfile]:
    """Resolve Discord usernames and avatars without mention strings."""
    unique_ids = list(dict.fromkeys(discord_ids))
    profiles: dict[int, LeaderboardProfile] = {}
    to_fetch: list[int] = []

    for discord_id in unique_ids:
        user: discord.User | discord.Member | None = None
        if guild is not None:
            user = guild.get_member(discord_id)
        if user is None:
            user = client.get_user(discord_id)
        if user is not None:
            profiles[discord_id] = profile_from_user(user)
        else:
            to_fetch.append(discord_id)

    for discord_id in to_fetch:
        try:
            user = await client.fetch_user(discord_id)
            profiles[discord_id] = profile_from_user(user)
        except discord.NotFound:
            profiles[discord_id] = default_profile(discord_id)
        except discord.HTTPException:
            log.warning("Failed to fetch Discord user %s for leaderboard", discord_id, exc_info=True)
            profiles[discord_id] = default_profile(discord_id)

    return profiles


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
            interaction.client,
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
            interaction.client,
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
    client: discord.Client,
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
    header = format_leaderboard_header(scope=scope, metric=metric, total=top, guild_name=guild_name)
    viewer_line = format_viewer_footer(rank, score, metric)

    guild = client.get_guild(guild_id) if guild_id is not None else None
    profiles = await resolve_leaderboard_profiles(client, [entry.discord_id for entry in page_entries], guild=guild)

    layout = LayoutView(timeout=300)
    container = Container()
    container.add_item(TextDisplay(truncate_text(header)))

    if not page_entries:
        container.add_item(TextDisplay("*No ranked players yet.*"))
    else:
        for entry in page_entries:
            profile = profiles[entry.discord_id]
            line = format_entry_line(entry, metric, display_name=profile.display_name)
            container.add_item(Section(TextDisplay(truncate_text(line)), accessory=Thumbnail(profile.avatar_url)))
        container.add_item(TextDisplay(truncate_text(format_leaderboard_page_footer(page, top))))

    container.add_item(Separator())
    container.add_item(TextDisplay(truncate_text(f"-# {viewer_line}")))

    if guild_id is not None:
        container.add_item(Separator())
        container.add_item(
            LeaderboardScopeRow(
                owner_id, scope=scope, metric=metric, page=page, top=top, guild_id=guild_id, guild_name=guild_name
            )
        )

    if pages > 1:
        container.add_item(Separator())
        container.add_item(
            LeaderboardPageRow(
                owner_id, scope=scope, metric=metric, page=page, top=top, guild_id=guild_id, guild_name=guild_name
            )
        )

    layout.add_item(container)
    return layout
