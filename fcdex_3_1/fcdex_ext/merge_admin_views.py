from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ui import ActionRow, Button, Container, Modal, Separator, TextDisplay, TextInput, button

from ballsdex.core.discord import LayoutView
from fcdex_3_1.fcdex_ext.bd_resolve import resolve_player_input
from fcdex_3_1.fcdex_ext.interaction_context import AdminContext, admin_context
from fcdex_3_1.fcdex_ext.merge_quota import (
    format_quota_status_block,
    get_merge_quota_settings,
    get_merge_quota_snapshot,
    get_player_merge_quota_row,
)
from fcdex_3_1.fcdex_ext.views import AdminHubBackRow, truncate_text
from fcdex_3_1.models import PlayerMergeQuota

if TYPE_CHECKING:
    from discord import Interaction

log = logging.getLogger("fcdex_3_1.merge.admin")


class EditGlobalQuotaModal(Modal, title="Global merge quota"):
    weekly_cap = TextInput(label="Weekly cap (base)", placeholder="5", max_length=6)
    period_days = TextInput(label="Period days (7 = Mon reset)", placeholder="7", max_length=4)

    def __init__(self, owner_id: int, *, weekly_cap: int, period_days: int):
        super().__init__()
        self.owner_id = owner_id
        self.weekly_cap.default = str(weekly_cap)
        self.period_days.default = str(period_days)

    async def on_submit(self, interaction: Interaction) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This panel is not yours.", ephemeral=True)
            return
        try:
            cap = int(self.weekly_cap.value.strip())
            period = int(self.period_days.value.strip())
            if cap < 1 or period < 1 or period > 365:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "Cap and period must be positive integers (period ≤ 365).", ephemeral=True
            )
            return
        settings = await get_merge_quota_settings()
        settings.weekly_cap = cap
        settings.period_days = period
        await settings.asave(update_fields=("weekly_cap", "period_days"))
        ctx = admin_context(interaction)
        layout = await build_merge_admin_layout(
            self.owner_id, ctx, notice=f"Global quota set to **{cap}** merges per **{period}** day(s)."
        )
        await interaction.response.edit_message(view=layout)


class GrantPremiumQuotaModal(Modal, title="Grant premium merge quota"):
    player = TextInput(label="Player", placeholder="Discord ID, @mention, or username in this server", max_length=128)
    bonus = TextInput(label="Premium bonus merges", placeholder="3", max_length=6, default="1")

    def __init__(self, owner_id: int):
        super().__init__()
        self.owner_id = owner_id

    async def on_submit(self, interaction: Interaction) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This panel is not yours.", ephemeral=True)
            return
        try:
            bonus = int(self.bonus.value.strip())
            if bonus < 0 or bonus > 999:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("Bonus must be 0–999.", ephemeral=True)
            return
        resolved = await resolve_player_input(self.player.value, guild=interaction.guild)
        if resolved is None:
            await interaction.response.send_message(
                "Player not found. Use their numeric **Discord ID** or a name visible in this server.", ephemeral=True
            )
            return
        await PlayerMergeQuota.objects.aupdate_or_create(player=resolved, defaults={"premium_bonus": bonus})
        ctx = admin_context(interaction)
        layout = await build_merge_admin_layout(
            self.owner_id,
            ctx,
            notice=f"Premium quota **+{bonus}** for <@{resolved.discord_id}> (player `#{resolved.pk}`).",
        )
        await interaction.response.edit_message(view=layout)


class SetPlayerCapOverrideModal(Modal, title="Player merge cap override"):
    player = TextInput(label="Player", placeholder="Discord ID, @mention, or username", max_length=128)
    cap_override = TextInput(
        label="Personal cap (empty = clear)", required=False, placeholder="Leave empty to remove override", max_length=6
    )

    def __init__(self, owner_id: int):
        super().__init__()
        self.owner_id = owner_id

    async def on_submit(self, interaction: Interaction) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This panel is not yours.", ephemeral=True)
            return
        resolved = await resolve_player_input(self.player.value, guild=interaction.guild)
        if resolved is None:
            await interaction.response.send_message("Player not found.", ephemeral=True)
            return
        raw_cap = (self.cap_override.value or "").strip()
        cap_value: int | None
        if not raw_cap:
            cap_value = None
        else:
            try:
                cap_value = int(raw_cap)
                if cap_value < 1:
                    raise ValueError
            except ValueError:
                await interaction.response.send_message("Cap override must be a positive integer.", ephemeral=True)
                return
        row, _ = await PlayerMergeQuota.objects.aupdate_or_create(player=resolved, defaults={})
        row.cap_override = cap_value
        await row.asave(update_fields=("cap_override",))
        cap_text = f"**{cap_value}**" if cap_value is not None else "*cleared (uses global + premium)*"
        ctx = admin_context(interaction)
        layout = await build_merge_admin_layout(
            self.owner_id, ctx, notice=f"Cap override {cap_text} for <@{resolved.discord_id}>."
        )
        await interaction.response.edit_message(view=layout)


class LookupPlayerQuotaModal(Modal, title="View player merge quota"):
    player = TextInput(label="Player", placeholder="Discord ID, @mention, or username", max_length=128)

    def __init__(self, owner_id: int):
        super().__init__()
        self.owner_id = owner_id

    async def on_submit(self, interaction: Interaction) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This panel is not yours.", ephemeral=True)
            return
        resolved = await resolve_player_input(self.player.value, guild=interaction.guild)
        if resolved is None:
            await interaction.response.send_message("Player not found.", ephemeral=True)
            return
        settings = await get_merge_quota_settings()
        snapshot = await get_merge_quota_snapshot(resolved)
        override = await get_player_merge_quota_row(resolved)
        extra = ""
        if override is not None:
            extra = (
                f"\n-# DB override: premium **+{override.premium_bonus}** · "
                f"cap override **{override.cap_override if override.cap_override is not None else '—'}**"
            )
        notice = (
            f"<@{resolved.discord_id}> · player `#{resolved.pk}`\n"
            f"{format_quota_status_block(snapshot, settings_period_days=settings.period_days)}"
            f"{extra}"
        )
        ctx = admin_context(interaction)
        layout = await build_merge_admin_layout(self.owner_id, ctx, notice=notice)
        await interaction.response.edit_message(view=layout)


class MergeAdminControls(ActionRow):
    def __init__(self, owner_id: int, *, weekly_cap: int, period_days: int):
        super().__init__()
        self.owner_id = owner_id
        self.weekly_cap = weekly_cap
        self.period_days = period_days

    @button(label="Global quota", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def global_quota(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(
            EditGlobalQuotaModal(self.owner_id, weekly_cap=self.weekly_cap, period_days=self.period_days)
        )

    @button(label="Premium bonus", style=discord.ButtonStyle.success, emoji="⭐")
    async def premium(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(GrantPremiumQuotaModal(self.owner_id))

    @button(label="Lookup player", style=discord.ButtonStyle.secondary, emoji="🔍")
    async def lookup(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(LookupPlayerQuotaModal(self.owner_id))

    @button(label="Cap override", style=discord.ButtonStyle.secondary, emoji="🎯")
    async def cap_override(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(SetPlayerCapOverrideModal(self.owner_id))

    @button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh(self, interaction: Interaction, button: Button):
        ctx = admin_context(interaction)
        layout = await build_merge_admin_layout(self.owner_id, ctx)
        await interaction.response.edit_message(view=layout)


async def build_merge_admin_layout(owner_id: int, ctx: AdminContext, *, notice: str = "") -> LayoutView:
    settings = await get_merge_quota_settings()
    overrides = [row async for row in PlayerMergeQuota.objects.select_related("player").order_by("-pk")[:15]]
    lines: list[str] = []
    for row in overrides:
        player = row.player
        parts = [f"premium **+{row.premium_bonus}**"]
        if row.cap_override is not None:
            parts.append(f"cap **{row.cap_override}**")
        lines.append(f"• <@{player.discord_id}> · `#{player.pk}` · {', '.join(parts)}")
    override_body = "\n".join(lines) if lines else "*No per-player overrides yet.*"
    period_hint = (
        "calendar week (Monday reset)" if settings.period_days == 7 else f"rolling **{settings.period_days}** days"
    )
    body = (
        f"**Global** · cap **{settings.weekly_cap}** per {period_hint}\n"
        f"-# Premium bonus stacks on global cap unless a personal cap override is set.\n\n"
        f"**Recent overrides**\n{override_body}"
    )
    if notice:
        body = f"**{notice}**\n\n{body}"

    layout = LayoutView(timeout=600)
    container = Container()
    container.add_item(
        TextDisplay(
            truncate_text(
                "# ✨ Merge admin\n"
                "-# Seven forge tiers (levels 1–7) · `/merge` · config in `merge_cards.toml`.\n"
                "-# Set the **global cap**, grant **premium bonus** merges, or **lookup / override** a player."
            )
        )
    )
    container.add_item(Separator())
    container.add_item(TextDisplay(truncate_text(body)))
    container.add_item(Separator())
    container.add_item(MergeAdminControls(owner_id, weekly_cap=settings.weekly_cap, period_days=settings.period_days))
    container.add_item(Separator())
    container.add_item(AdminHubBackRow(owner_id))
    layout.add_item(container)
    return layout
