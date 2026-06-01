from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ui import ActionRow, Button, Container, Modal, Separator, TextDisplay, TextInput, button

from ballsdex.core.discord import LayoutView
from bd_models.models import Ball
from fcdex_3_1.fcdex_ext.bd_resolve import resolve_ball_for_lookup
from fcdex_3_1.fcdex_ext.boss_views import build_boss_admin_layout
from fcdex_3_1.fcdex_ext.craft_admin_views import build_craft_admin_layout
from fcdex_3_1.fcdex_ext.shop_admin_views import build_shop_admin_layout
from fcdex_3_1.fcdex_ext.views import build_panel_layout, truncate_text

if TYPE_CHECKING:
    from discord import Interaction


class AdminHubControls(ActionRow):
    def __init__(self, owner_id: int, guild_id: int | None):
        super().__init__()
        self.owner_id = owner_id
        self.guild_id = guild_id

    @button(label="Shop", style=discord.ButtonStyle.primary, emoji="🛒")
    async def shop(self, interaction: Interaction, button: Button):
        layout = await build_shop_admin_layout(self.owner_id, self.guild_id)
        await interaction.response.edit_message(view=layout)

    @button(label="Craft", style=discord.ButtonStyle.primary, emoji="🧪")
    async def craft(self, interaction: Interaction, button: Button):
        layout = await build_craft_admin_layout(self.owner_id, self.guild_id)
        await interaction.response.edit_message(view=layout)

    @button(label="Boss", style=discord.ButtonStyle.danger, emoji="👑")
    async def boss(self, interaction: Interaction, button: Button):
        if self.guild_id is None:
            await interaction.response.send_message("Boss admin requires a server.", ephemeral=True)
            return
        layout = await build_boss_admin_layout(self.owner_id, self.guild_id)
        await interaction.response.edit_message(view=layout)

    @button(label="Owners", style=discord.ButtonStyle.secondary, emoji="🔍")
    async def owners(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(OwnersLookupModal(self.owner_id, self.guild_id))


class OwnersLookupModal(Modal, title="Clubball owners"):
    clubball = TextInput(label="Clubball", placeholder="Country name or PK (e.g. 42)", max_length=128)

    def __init__(self, owner_id: int, guild_id: int | None):
        super().__init__()
        self.owner_id = owner_id
        self.guild_id = guild_id

    async def on_submit(self, interaction: Interaction) -> None:
        ball = await resolve_ball_for_lookup(self.clubball.value)
        if ball is None:
            await interaction.response.send_message("Clubball not found.", ephemeral=True)
            return
        await open_owners_panel(interaction, ball)


def build_admin_hub_layout(owner_id: int, guild_id: int | None) -> LayoutView:
    layout = LayoutView(timeout=600)
    container = Container()
    container.add_item(
        TextDisplay(
            truncate_text(
                "# 🛡️ FCDex admin\n"
                "-# Manage Server · all panels are ephemeral.\n"
                "-# **Shop** — bundles & optional specials per item.\n"
                "-# **Craft** — SBC recipes without the web panel.\n"
                "-# **Boss** — guild raid (start rounds from Boss panel)."
            )
        )
    )
    container.add_item(Separator())
    container.add_item(AdminHubControls(owner_id, guild_id))
    layout.add_item(container)
    return layout


async def open_owners_panel(interaction: Interaction, clubball: Ball) -> None:
    from bd_models.models import BallInstance

    count = await BallInstance.objects.filter(ball_id=clubball.pk, deleted=False).acount()
    if count == 0:
        await interaction.response.send_message(f"Nobody owns **{clubball.country}** right now.", ephemeral=True)
        return
    lines: list[str] = []
    async for inst in (
        BallInstance.objects.filter(ball_id=clubball.pk, deleted=False).select_related("player").order_by("-pk")[:25]
    ):
        lines.append(f"• <@{inst.player.discord_id}> · card `#{inst.pk}`")
    extra = f"-# Showing 25/{count} owners." if count > 25 else ""
    layout = build_panel_layout(
        title=f"Owners of {clubball.country}",
        subtitle=f"{count} owner{'s' if count != 1 else ''}",
        sections=["\n".join(lines)],
        footer=extra,
    )
    await interaction.response.send_message(view=layout, ephemeral=True)  # pyright: ignore[reportArgumentType]
