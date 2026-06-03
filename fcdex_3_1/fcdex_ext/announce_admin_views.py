from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

import discord
from discord.ui import ActionRow, Button, Container, Modal, Separator, TextDisplay, TextInput, button

from ballsdex.core.discord import LayoutView
from fcdex_3_1.fcdex_ext.broadcast_logic import (
    TOS_WARNING,
    count_dm_recipients,
    count_server_broadcast_targets,
    format_announce_message,
    run_dm_broadcast,
    run_server_broadcast,
    validate_broadcast_message,
)
from fcdex_3_1.fcdex_ext.views import AdminHubBackRow, truncate_text

if TYPE_CHECKING:
    from discord import Interaction

log = logging.getLogger("fcdex_3_1.announce.admin")

BroadcastKind = Literal["dm", "server"]


def _require_panel_owner(interaction: Interaction, owner_id: int) -> bool:
    if interaction.user.id != owner_id:
        return False
    return True


async def _deny_panel_owner(interaction: Interaction) -> None:
    await interaction.response.send_message("This panel is not yours.", ephemeral=True)


def _require_manage_guild(interaction: Interaction) -> bool:
    if interaction.guild is None:
        return True
    if not isinstance(interaction.user, discord.Member):
        return False
    return bool(interaction.user.guild_permissions.manage_guild)


async def _deny_manage_guild(interaction: Interaction) -> None:
    await interaction.response.send_message("You need **Manage Server** to use announcements.", ephemeral=True)


class AnnounceContentModal(Modal):
    title_field = TextInput(label="Title", max_length=256, placeholder="FCDex update")
    body_field = TextInput(
        label="Message", style=discord.TextStyle.paragraph, max_length=3500, placeholder="What players should know…"
    )

    def __init__(self, owner_id: int, kind: BroadcastKind):
        super().__init__(title="DM broadcast to players" if kind == "dm" else "Server broadcast")
        self.owner_id = owner_id
        self.kind = kind

    async def on_submit(self, interaction: Interaction) -> None:
        if not _require_panel_owner(interaction, self.owner_id):
            await _deny_panel_owner(interaction)
            return
        if not _require_manage_guild(interaction):
            await _deny_manage_guild(interaction)
            return
        title = self.title_field.value.strip()
        body = self.body_field.value.strip()
        if not body and not title:
            await interaction.response.send_message("Message cannot be empty.", ephemeral=True)
            return
        content = format_announce_message(title=title, body=body)
        ok, validated = validate_broadcast_message(content)
        if not ok:
            await interaction.response.send_message(validated, ephemeral=True)
            return
        content = validated
        bot = interaction.client
        if self.kind == "dm":
            recipient_count = await count_dm_recipients()
        else:
            recipient_count = await count_server_broadcast_targets(bot)  # type: ignore[arg-type]
        layout = build_broadcast_confirm_layout(
            self.owner_id, kind=self.kind, content=content, recipient_count=recipient_count
        )
        await interaction.response.edit_message(view=layout)


class BroadcastConfirmControls(ActionRow):
    def __init__(self, owner_id: int, kind: BroadcastKind, content: str, recipient_count: int):
        super().__init__()
        self.owner_id = owner_id
        self.kind = kind
        self.content = content
        self.recipient_count = recipient_count

    @button(label="Send broadcast", style=discord.ButtonStyle.danger, emoji="📣")
    async def confirm(self, interaction: Interaction, button: Button):
        if not _require_panel_owner(interaction, self.owner_id):
            await _deny_panel_owner(interaction)
            return
        if not _require_manage_guild(interaction):
            await _deny_manage_guild(interaction)
            return
        if self.recipient_count <= 0:
            await interaction.response.send_message("Nothing to send — recipient count is zero.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await interaction.edit_original_response(
            view=build_broadcast_progress_layout(self.owner_id, self.kind, notice="Starting broadcast…")
        )
        await _execute_broadcast(interaction, self.owner_id, kind=self.kind, content=self.content)

    @button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: Button):
        if not _require_panel_owner(interaction, self.owner_id):
            await _deny_panel_owner(interaction)
            return
        layout = build_announce_admin_layout(self.owner_id, notice="Broadcast cancelled.")
        await interaction.response.edit_message(view=layout)


def build_broadcast_confirm_layout(
    owner_id: int, *, kind: BroadcastKind, content: str, recipient_count: int
) -> LayoutView:
    layout = LayoutView(timeout=600)
    container = Container()
    kind_label = "DM" if kind == "dm" else "server"
    preview = truncate_text(content, 1200)
    body = (
        f"# Confirm {kind_label} broadcast\n"
        f"-# Recipients: **{recipient_count:,}** · review before sending.\n"
        f"{TOS_WARNING}\n\n"
        f"### Preview\n{preview}"
    )
    if kind == "dm":
        body += "\n\n-# Sends one DM per player with at least one clubball. Throttled ~1s between messages."
    else:
        body += (
            "\n\n-# Posts to each server's spawn channel (if set), else announcement / system / first writable channel."
        )
    container.add_item(TextDisplay(truncate_text(body)))
    container.add_item(Separator())
    container.add_item(BroadcastConfirmControls(owner_id, kind, content, recipient_count))
    container.add_item(AdminHubBackRow(owner_id))
    layout.add_item(container)
    return layout


def build_broadcast_progress_layout(owner_id: int, kind: BroadcastKind, *, notice: str) -> LayoutView:
    layout = LayoutView(timeout=600)
    container = Container()
    label = "DM" if kind == "dm" else "Server"
    container.add_item(TextDisplay(truncate_text(f"# {label} broadcast in progress\n-# {notice}")))
    container.add_item(AdminHubBackRow(owner_id))
    layout.add_item(container)
    return layout


async def _update_announce_panel(interaction: Interaction, owner_id: int, *, notice: str) -> None:
    layout = build_announce_admin_layout(owner_id, notice=notice)
    try:
        if interaction.response.is_done():
            await interaction.edit_original_response(view=layout)
        else:
            await interaction.response.edit_message(view=layout)
    except discord.NotFound:
        try:
            await interaction.followup.send(notice, ephemeral=True)
        except discord.HTTPException:
            log.warning("Broadcast finished but panel message was gone for user %s", owner_id)
    except discord.HTTPException:
        log.exception("Could not refresh announce panel for user %s", owner_id)


async def _execute_broadcast(interaction: Interaction, owner_id: int, *, kind: BroadcastKind, content: str) -> None:
    bot = interaction.client
    try:
        if kind == "dm":
            tally, total = await run_dm_broadcast(bot, content)
            summary = tally.format_dm_summary(total=total)
        else:
            tally, guilds, skipped = await run_server_broadcast(bot, content)  # type: ignore[arg-type]
            summary = tally.format_server_summary(guilds=guilds, skipped=skipped)
        notice = f"{summary}\n\n-# You can start another broadcast from **Announce**."
        await _update_announce_panel(interaction, owner_id, notice=notice)
    except Exception:
        log.exception("Broadcast failed kind=%s", kind)
        await _update_announce_panel(interaction, owner_id, notice="❌ Broadcast failed — check bot logs.")


class AnnounceAdminControls(ActionRow):
    def __init__(self, owner_id: int):
        super().__init__()
        self.owner_id = owner_id

    @button(label="DM players", style=discord.ButtonStyle.primary, emoji="✉️")
    async def dm_broadcast(self, interaction: Interaction, button: Button):
        if not _require_panel_owner(interaction, self.owner_id):
            await _deny_panel_owner(interaction)
            return
        await interaction.response.send_modal(AnnounceContentModal(self.owner_id, "dm"))

    @button(label="Server broadcast", style=discord.ButtonStyle.primary, emoji="📢")
    async def server_broadcast(self, interaction: Interaction, button: Button):
        if not _require_panel_owner(interaction, self.owner_id):
            await _deny_panel_owner(interaction)
            return
        await interaction.response.send_modal(AnnounceContentModal(self.owner_id, "server"))

    @button(label="Preview DM count", style=discord.ButtonStyle.secondary, emoji="🔢")
    async def preview_dm_count(self, interaction: Interaction, button: Button):
        if not _require_panel_owner(interaction, self.owner_id):
            await _deny_panel_owner(interaction)
            return
        count = await count_dm_recipients()
        layout = build_announce_admin_layout(
            self.owner_id,
            notice=f"**DM dry-run:** **{count:,}** players with at least one clubball would receive a DM.",
        )
        await interaction.response.edit_message(view=layout)

    @button(label="Preview server count", style=discord.ButtonStyle.secondary, emoji="🔢")
    async def preview_server_count(self, interaction: Interaction, button: Button):
        if not _require_panel_owner(interaction, self.owner_id):
            await _deny_panel_owner(interaction)
            return
        count = await count_server_broadcast_targets(interaction.client)  # type: ignore[arg-type]
        layout = build_announce_admin_layout(
            self.owner_id, notice=f"**Server dry-run:** **{count:,}** servers have a writable announcement channel."
        )
        await interaction.response.edit_message(view=layout)


def build_announce_admin_layout(owner_id: int, *, notice: str = "") -> LayoutView:
    layout = LayoutView(timeout=600)
    container = Container()
    body = (
        "# 📣 Announcements\n"
        "-# Manage Server · mass updates for players and servers.\n"
        "-# **DM players** — every player with ≥1 clubball (not deleted).\n"
        "-# **Server broadcast** — every enabled/configured server + bot guilds.\n"
        f"{TOS_WARNING}"
    )
    if notice:
        body = f"{notice}\n\n{body}"
    container.add_item(TextDisplay(truncate_text(body)))
    container.add_item(Separator())
    container.add_item(AnnounceAdminControls(owner_id))
    container.add_item(AdminHubBackRow(owner_id))
    layout.add_item(container)
    return layout


class AdminHubAnnounceRow(ActionRow):
    def __init__(self, owner_id: int):
        super().__init__()
        self.owner_id = owner_id

    @button(label="Announce", style=discord.ButtonStyle.success, emoji="📣")
    async def announce(self, interaction: Interaction, button: Button):
        if not _require_manage_guild(interaction):
            await _deny_manage_guild(interaction)
            return
        layout = build_announce_admin_layout(self.owner_id)
        await interaction.response.edit_message(view=layout)
