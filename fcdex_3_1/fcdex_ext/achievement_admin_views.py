from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ui import ActionRow, Button, Container, Modal, Separator, TextDisplay, TextInput, button

from ballsdex.core.discord import LayoutView
from fcdex_3_1.fcdex_ext.achievement_admin_util import (
    _TYPE_LABELS,
    _TYPE_VALUES,
    normalize_achievement_type,
    parse_bool_field,
)
from fcdex_3_1.fcdex_ext.bd_resolve import resolve_ball_input
from fcdex_3_1.fcdex_ext.interaction_context import AdminContext, admin_context
from fcdex_3_1.fcdex_ext.views import AdminHubBackRow, truncate_text
from fcdex_3_1.models import Achievement

if TYPE_CHECKING:
    from discord import Interaction

log = logging.getLogger("fcdex_3_1.achievement.admin")

_normalize_type = normalize_achievement_type
_parse_bool = parse_bool_field


class CreateAchievementModal(Modal, title="New achievement"):
    name = TextInput(label="Name", max_length=64)
    description = TextInput(label="Description", style=discord.TextStyle.paragraph, max_length=500)
    achievement_type = TextInput(
        label="Type",
        placeholder="battles_won · merges · tournament_win · balls_owned · custom",
        max_length=32,
        default="battles_won",
    )
    required_count = TextInput(label="Required count", placeholder="1", max_length=8, default="1")
    reward_money = TextInput(label="Coin reward", placeholder="0", max_length=16, default="0")
    emoji = TextInput(label="Emoji", required=False, max_length=32, default="🏆")
    reward_ball = TextInput(
        label="Reward clubball (optional)", required=False, placeholder="PK or country name", max_length=128
    )
    hidden = TextInput(label="Hidden? (yes/no)", required=False, max_length=8, default="no")

    def __init__(self, owner_id: int):
        super().__init__()
        self.owner_id = owner_id

    async def on_submit(self, interaction: Interaction) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This panel is not yours.", ephemeral=True)
            return
        ach_type = _normalize_type(self.achievement_type.value)
        if ach_type not in _TYPE_VALUES:
            await interaction.response.send_message(
                f"Type must be one of: {', '.join(sorted(_TYPE_VALUES))}.", ephemeral=True
            )
            return
        try:
            required = int(self.required_count.value.strip())
            reward = int(self.reward_money.value.strip().replace(",", ""))
            if required < 1 or reward < 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "Required count must be ≥ 1 and reward must be ≥ 0.", ephemeral=True
            )
            return
        name = self.name.value.strip()
        if not name:
            await interaction.response.send_message("Name is required.", ephemeral=True)
            return
        if await Achievement.objects.filter(name__iexact=name).aexists():
            await interaction.response.send_message(f"Achievement **{name}** already exists.", ephemeral=True)
            return
        reward_ball_id: int | None = None
        raw_ball = (self.reward_ball.value or "").strip()
        if raw_ball:
            ball = await resolve_ball_input(raw_ball)
            if ball is None:
                await interaction.response.send_message("Reward clubball not found in the dex.", ephemeral=True)
                return
            reward_ball_id = ball.pk
        achievement = await Achievement.objects.acreate(
            name=name,
            description=self.description.value.strip(),
            emoji=(self.emoji.value or "🏆")[:32],
            achievement_type=ach_type,
            required_count=required,
            reward_money=reward,
            reward_ball_id=reward_ball_id,
            hidden=_parse_bool(self.hidden.value),
        )
        ctx = admin_context(interaction)
        layout = await build_achievement_admin_layout(
            self.owner_id, ctx, notice=f"Created **{achievement.name}** (`#{achievement.pk}`)."
        )
        await interaction.response.edit_message(view=layout)


class EditAchievementModal(Modal, title="Edit achievement"):
    name = TextInput(label="Name", max_length=64)
    description = TextInput(label="Description", style=discord.TextStyle.paragraph, max_length=500)
    achievement_type = TextInput(label="Type", max_length=32)
    required_count = TextInput(label="Required count", max_length=8)
    reward_money = TextInput(label="Coin reward", max_length=16)
    emoji = TextInput(label="Emoji", max_length=32)
    reward_ball = TextInput(
        label="Reward clubball", required=False, placeholder="PK, country, or leave empty to clear", max_length=128
    )
    hidden = TextInput(label="Hidden? (yes/no)", required=False, max_length=8)
    enabled = TextInput(label="Enabled? (yes/no)", required=False, max_length=8)

    def __init__(self, owner_id: int, achievement: Achievement):
        super().__init__()
        self.owner_id = owner_id
        self.achievement_id = achievement.pk
        self.name.default = achievement.name
        self.description.default = achievement.description
        self.achievement_type.default = achievement.achievement_type
        self.required_count.default = str(achievement.required_count)
        self.reward_money.default = str(achievement.reward_money)
        self.emoji.default = achievement.emoji
        self.hidden.default = "yes" if achievement.hidden else "no"
        self.enabled.default = "yes" if achievement.enabled else "no"
        if achievement.reward_ball_id:
            self.reward_ball.default = str(achievement.reward_ball_id)

    async def on_submit(self, interaction: Interaction) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This panel is not yours.", ephemeral=True)
            return
        ach_type = _normalize_type(self.achievement_type.value)
        if ach_type not in _TYPE_VALUES:
            await interaction.response.send_message(
                f"Type must be one of: {', '.join(sorted(_TYPE_VALUES))}.", ephemeral=True
            )
            return
        try:
            required = int(self.required_count.value.strip())
            reward = int(self.reward_money.value.strip().replace(",", ""))
            if required < 1 or reward < 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "Required count must be ≥ 1 and reward must be ≥ 0.", ephemeral=True
            )
            return
        name = self.name.value.strip()
        if not name:
            await interaction.response.send_message("Name is required.", ephemeral=True)
            return
        achievement = await Achievement.objects.aget(pk=self.achievement_id)
        if name.lower() != achievement.name.lower() and await Achievement.objects.filter(name__iexact=name).aexists():
            await interaction.response.send_message(f"Achievement **{name}** already exists.", ephemeral=True)
            return
        raw_ball = (self.reward_ball.value or "").strip()
        reward_ball_id: int | None = None
        if raw_ball:
            ball = await resolve_ball_input(raw_ball)
            if ball is None:
                await interaction.response.send_message("Reward clubball not found in the dex.", ephemeral=True)
                return
            reward_ball_id = ball.pk
        achievement.name = name
        achievement.description = self.description.value.strip()
        achievement.emoji = (self.emoji.value or "🏆")[:32]
        achievement.achievement_type = ach_type
        achievement.required_count = required
        achievement.reward_money = reward
        achievement.reward_ball_id = reward_ball_id
        achievement.hidden = _parse_bool(self.hidden.value, default=achievement.hidden)
        achievement.enabled = _parse_bool(self.enabled.value, default=achievement.enabled)
        await achievement.asave()
        ctx = admin_context(interaction)
        layout = await build_achievement_admin_layout(self.owner_id, ctx, notice=f"Updated **{achievement.name}**.")
        await interaction.response.edit_message(view=layout)


class AchievementAdminControls(ActionRow):
    def __init__(self, owner_id: int):
        super().__init__()
        self.owner_id = owner_id

    @button(label="New achievement", style=discord.ButtonStyle.success, emoji="➕")
    async def new_achievement(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(CreateAchievementModal(self.owner_id))

    @button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh(self, interaction: Interaction, button: Button):
        ctx = admin_context(interaction)
        layout = await build_achievement_admin_layout(self.owner_id, ctx)
        await interaction.response.edit_message(view=layout)


class AchievementToggleSelect(discord.ui.Select):
    def __init__(self, owner_id: int, achievements: list[Achievement]):
        self.owner_id = owner_id
        options = [
            discord.SelectOption(
                label=a.name[:100],
                value=str(a.pk),
                description=(
                    f"{'On' if a.enabled else 'Off'} · {_TYPE_LABELS.get(a.achievement_type, a.achievement_type)}"
                )[:100],
                emoji=a.emoji or None,
            )
            for a in achievements[:25]
        ]
        super().__init__(placeholder="Enable / disable…", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This panel is not yours.", ephemeral=True)
            return
        achievement = await Achievement.objects.aget(pk=int(self.values[0]))
        achievement.enabled = not achievement.enabled
        await achievement.asave(update_fields=("enabled",))
        state = "enabled" if achievement.enabled else "disabled"
        ctx = admin_context(interaction)
        layout = await build_achievement_admin_layout(
            self.owner_id, ctx, notice=f"**{achievement.name}** is now {state}."
        )
        await interaction.response.edit_message(view=layout)


class AchievementEditSelect(discord.ui.Select):
    def __init__(self, owner_id: int, achievements: list[Achievement]):
        self.owner_id = owner_id
        options = [
            discord.SelectOption(
                label=a.name[:100],
                value=str(a.pk),
                description=f"goal {a.required_count} · +{a.reward_money:,} coins"[:100],
                emoji=a.emoji or None,
            )
            for a in achievements[:25]
        ]
        super().__init__(placeholder="Edit achievement…", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This panel is not yours.", ephemeral=True)
            return
        achievement = await Achievement.objects.aget(pk=int(self.values[0]))
        await interaction.response.send_modal(EditAchievementModal(self.owner_id, achievement))


class AchievementDeleteSelect(discord.ui.Select):
    def __init__(self, owner_id: int, achievements: list[Achievement]):
        self.owner_id = owner_id
        options = [
            discord.SelectOption(
                label=a.name[:100], value=str(a.pk), description="Select to confirm delete"[:100], emoji=a.emoji or None
            )
            for a in achievements[:25]
        ]
        super().__init__(placeholder="Delete achievement…", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This panel is not yours.", ephemeral=True)
            return
        achievement = await Achievement.objects.aget(pk=int(self.values[0]))
        ctx = admin_context(interaction)
        layout = await build_achievement_admin_layout(
            self.owner_id,
            ctx,
            notice=f"⚠️ Delete **{achievement.name}**? This removes all player progress for it.",
            pending_delete_id=achievement.pk,
        )
        await interaction.response.edit_message(view=layout)


class DeleteConfirmRow(ActionRow):
    def __init__(self, owner_id: int, achievement_id: int, achievement_name: str):
        super().__init__()
        self.owner_id = owner_id
        self.achievement_id = achievement_id
        self.achievement_name = achievement_name

    @button(label="Confirm delete", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This panel is not yours.", ephemeral=True)
            return
        deleted, _ = await Achievement.objects.filter(pk=self.achievement_id).adelete()
        ctx = admin_context(interaction)
        notice = f"Deleted **{self.achievement_name}**." if deleted else "Achievement was already removed."
        layout = await build_achievement_admin_layout(self.owner_id, ctx, notice=notice)
        await interaction.response.edit_message(view=layout)

    @button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This panel is not yours.", ephemeral=True)
            return
        ctx = admin_context(interaction)
        layout = await build_achievement_admin_layout(self.owner_id, ctx)
        await interaction.response.edit_message(view=layout)


async def build_achievement_admin_layout(
    owner_id: int, ctx: AdminContext, *, notice: str = "", pending_delete_id: int | None = None
) -> LayoutView:
    achievements = [a async for a in Achievement.objects.select_related("reward_ball").order_by("name")[:50]]
    lines: list[str] = []
    for achievement in achievements:
        type_label = _TYPE_LABELS.get(achievement.achievement_type, achievement.achievement_type)
        reward_ball = achievement.reward_ball
        reward_parts: list[str] = []
        if achievement.reward_money:
            reward_parts.append(f"**+{achievement.reward_money:,}** coins")
        if reward_ball:
            reward_parts.append(f"**{reward_ball.country}** card")
        reward_text = " · ".join(reward_parts) if reward_parts else "*no reward*"
        flags = []
        if achievement.hidden:
            flags.append("hidden")
        if not achievement.enabled:
            flags.append("off")
        flag_text = f" · {', '.join(flags)}" if flags else ""
        lines.append(
            f"{achievement.emoji} **{achievement.name}** · `{type_label}` × **{achievement.required_count}**\n"
            f"-# {achievement.description[:120]}{'…' if len(achievement.description) > 120 else ''}\n"
            f"-# Reward: {reward_text} · `#{achievement.pk}`{flag_text}"
        )
    body = "\n\n".join(lines) if lines else "*No achievements — use **New achievement**.*"
    if notice:
        body = f"**{notice}**\n\n{body}"
    if len(achievements) == 50:
        body += "\n\n-# Showing first 50 achievements."

    layout = LayoutView(timeout=600)
    container = Container()
    container.add_item(
        TextDisplay(
            truncate_text(
                "# 🏅 Achievement admin\n"
                "-# Goals for `/achievement menu` — catalog, progress & claims.\n"
                "-# **Type** drives auto-progress (except **custom** — set progress in Django admin)."
            )
        )
    )
    container.add_item(Separator())
    container.add_item(TextDisplay(truncate_text(body)))
    container.add_item(Separator())
    container.add_item(AchievementAdminControls(owner_id))
    if achievements:
        toggle_row = ActionRow()
        toggle_row.add_item(AchievementToggleSelect(owner_id, achievements))
        container.add_item(toggle_row)
        edit_row = ActionRow()
        edit_row.add_item(AchievementEditSelect(owner_id, achievements))
        container.add_item(edit_row)
        delete_row = ActionRow()
        delete_row.add_item(AchievementDeleteSelect(owner_id, achievements))
        container.add_item(delete_row)
    if pending_delete_id is not None:
        pending = next((a for a in achievements if a.pk == pending_delete_id), None)
        if pending is None:
            pending = await Achievement.objects.filter(pk=pending_delete_id).afirst()
        if pending is not None:
            container.add_item(DeleteConfirmRow(owner_id, pending.pk, pending.name))
    container.add_item(Separator())
    container.add_item(AdminHubBackRow(owner_id))
    layout.add_item(container)
    return layout
