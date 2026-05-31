from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ui import ActionRow, Button, Container, Separator, TextDisplay, button

from ballsdex.core.discord import LayoutView
from fcdex_3_0.fcdex_ext.rarity_data import RarityCategory
from fcdex_3_0.fcdex_ext.rarity_logic import (
    build_category_overview,
    build_obtainable_overview,
    count_catalog,
    entries_for_tier,
    format_entry_line,
    resolve_ball,
)
from fcdex_3_0.fcdex_ext.views import truncate_text

if TYPE_CHECKING:
    from discord import Interaction

    from bd_models.models import Ball

log = logging.getLogger("fcdex_3_0.rarity.views")

CATEGORY_MODES: dict[str, RarityCategory] = {
    "obtainable": RarityCategory.OBTAINABLE,
    "icons": RarityCategory.ICON,
    "goat": RarityCategory.GOAT_ICON,
    "prime": RarityCategory.PRIME,
    "events": RarityCategory.EVENT,
    "eid": RarityCategory.EID,
    "exclusive": RarityCategory.EXCLUSIVE,
    "unobtainable": RarityCategory.UNOBTAINABLE,
}


def _overview_body() -> str:
    counts = count_catalog()
    lines = [
        "Official FCDex rarity uses **fixed tiers** — lower tier = rarer.",
        "",
        f"⚽ Obtainable · **{counts['obtainable']}** clubballs",
        f"🌟 Icons · **{counts['icon']}** · 👑 GOAT · **{counts['goat_icon']}**",
        f"🏆 Prime · **{counts['prime']}** · 🎉 Events · **{counts['event']}**",
        f"🌙 Eid · **{counts['eid']}** · 💎 Exclusive · **{counts['exclusive']}**",
        f"🚫 Unobtainable · **{counts['unobtainable']}**",
        "",
        "-# Use **Category** tabs below · `/fcdex rarity clubball:<card>` for a lookup",
    ]
    return "\n".join(lines)


class RarityCategoryTabs(ActionRow):
    def __init__(self, owner_id: int, *, mode: str = "overview", page: int = 0):
        super().__init__()
        self.owner_id = owner_id
        self.mode = mode
        self.page = page

    @button(label="Overview", style=discord.ButtonStyle.primary, emoji="📋")
    async def overview_tab(self, interaction: Interaction, button: Button):
        await self._switch(interaction, "overview", 0)

    @button(label="Obtainable", style=discord.ButtonStyle.secondary, emoji="⚽")
    async def obtainable_tab(self, interaction: Interaction, button: Button):
        await self._switch(interaction, "obtainable", 0)

    @button(label="Icons", style=discord.ButtonStyle.secondary, emoji="🌟")
    async def icons_tab(self, interaction: Interaction, button: Button):
        await self._switch(interaction, "icons", 0)

    @button(label="Events", style=discord.ButtonStyle.secondary, emoji="🎉")
    async def events_tab(self, interaction: Interaction, button: Button):
        await self._switch(interaction, "events", 0)

    @button(label="Unobtainable", style=discord.ButtonStyle.secondary, emoji="🚫")
    async def unobtainable_tab(self, interaction: Interaction, button: Button):
        await self._switch(interaction, "unobtainable", 0)

    async def _switch(self, interaction: Interaction, mode: str, page: int) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This menu is private to you.", ephemeral=True)
            return
        layout = await build_rarity_menu(self.owner_id, mode=mode, page=page)
        await interaction.response.edit_message(view=layout)


class RarityPageRow(ActionRow):
    def __init__(self, owner_id: int, *, page: int, page_count: int):
        super().__init__()
        self.owner_id = owner_id
        self.page = page
        self.page_count = page_count

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
            await interaction.response.send_message("This menu is private to you.", ephemeral=True)
            return
        layout = await build_rarity_menu(self.owner_id, mode="obtainable", page=max(0, page))
        await interaction.response.edit_message(view=layout)


async def build_rarity_menu(owner_id: int, *, mode: str = "overview", page: int = 0) -> LayoutView:
    layout = LayoutView(timeout=300)
    container = Container()

    if mode == "overview":
        container.add_item(TextDisplay(truncate_text(f"# 📊 FCDex rarity\n\n{_overview_body()}")))
    elif mode == "obtainable":
        pages = build_obtainable_overview()
        page = max(0, min(page, len(pages) - 1))
        footer = f"\n\n-# Page **{page + 1}/{len(pages)}** · lower tier = rarer"
        container.add_item(TextDisplay(truncate_text(pages[page] + footer)))
        if len(pages) > 1:
            container.add_item(Separator())
            container.add_item(RarityPageRow(owner_id, page=page, page_count=len(pages)))
    elif mode in CATEGORY_MODES:
        body = build_category_overview(CATEGORY_MODES[mode])
        container.add_item(TextDisplay(truncate_text(body)))
    else:
        container.add_item(TextDisplay("Unknown rarity view."))

    container.add_item(Separator())
    container.add_item(RarityCategoryTabs(owner_id, mode=mode, page=page))
    layout.add_item(container)
    return layout


async def build_ball_rarity_layout(ball: Ball) -> LayoutView:
    entry = resolve_ball(ball)
    layout = LayoutView(timeout=120)
    container = Container()
    if entry is None:
        body = (
            f"# 🔍 {ball.country}\n"
            f"Not listed on the official FCDex rarity sheet.\n"
            f"-# Dex spawn weight: `{ball.rarity}`"
        )
    else:
        body = f"# 🔍 {ball.country}\n{format_entry_line(entry, ball=ball)}"
    container.add_item(TextDisplay(truncate_text(body)))
    layout.add_item(container)
    return layout


async def build_tier_layout(tier: int) -> LayoutView:
    rows = entries_for_tier(tier)
    layout = LayoutView(timeout=120)
    container = Container()
    if not rows:
        container.add_item(TextDisplay(f"# Tier {tier}\nNo obtainable clubballs at this tier."))
    else:
        lines = [format_entry_line(row) for row in rows]
        container.add_item(TextDisplay(truncate_text(f"# ⚽ Obtainable · Tier {tier}\n\n" + "\n\n".join(lines))))
    layout.add_item(container)
    return layout
