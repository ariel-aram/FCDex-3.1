from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import discord
from discord.ui import ActionRow, Button, Container, Separator, TextDisplay, button

from ballsdex.core.discord import LayoutView
from bd_models.models import Ball, BallInstance, Player
from fcdex_3_1.fcdex_ext.bd_helpers import get_ball
from fcdex_3_1.fcdex_ext.merge_levels import (
    MAX_MERGE_LEVEL,
    format_level_table_row,
    format_merge_input_requirement,
    get_merge_level_config,
    get_merge_level_emoji,
)
from fcdex_3_1.fcdex_ext.merge_logic import (
    MergeValidationError,
    execute_merge,
    instance_already_used_in_merge,
    preview_merge_stats,
    validate_merge_batch,
)
from fcdex_3_1.fcdex_ext.merge_quota import (
    format_quota_status_block,
    get_merge_quota_settings,
    get_merge_quota_snapshot,
)
from fcdex_3_1.fcdex_ext.merge_special import MERGE_SPECIAL_NAME, get_merge_special
from fcdex_3_1.fcdex_ext.views import truncate_text

if TYPE_CHECKING:
    from discord import Interaction

    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("fcdex_3_1.merge.views")


@dataclass(slots=True)
class MergeClubballSummary:
    ball: Ball
    buckets: dict[int, list[BallInstance]]

    @property
    def counts(self) -> dict[int, int]:
        return {level: len(instances) for level, instances in self.buckets.items()}


def _empty_buckets() -> dict[int, list[BallInstance]]:
    return {level: [] for level in range(0, MAX_MERGE_LEVEL + 1)}


def _highest_owned_level(counts: dict[int, int]) -> int:
    return max((level for level in range(1, MAX_MERGE_LEVEL + 1) if counts.get(level, 0) > 0), default=0)


def _open_level(counts: dict[int, int]) -> int:
    return min(MAX_MERGE_LEVEL, _highest_owned_level(counts) + 1)


def _progress_count(counts: dict[int, int], level: int) -> int:
    return counts.get(0 if level == 1 else level - 1, 0)


def _current_target_level(counts: dict[int, int]) -> int | None:
    open_level = _open_level(counts)
    candidate: int | None = None
    for level in range(1, open_level + 1):
        cfg = get_merge_level_config(level)
        if _progress_count(counts, level) >= cfg.input_count:
            candidate = level
    return candidate


def _input_label(level: int) -> str:
    if level == 1:
        return "common copies"
    return f"{get_merge_level_emoji(level - 1)} L{level - 1} copies"


def _target_instances(summary: MergeClubballSummary, target_level: int) -> list[BallInstance]:
    source_level = 0 if target_level == 1 else target_level - 1
    cfg = get_merge_level_config(target_level)
    return list(summary.buckets[source_level][: cfg.input_count])


def _option_description(summary: MergeClubballSummary) -> str:
    counts = summary.counts
    target_level = _current_target_level(counts)
    open_level = _open_level(counts)
    if target_level is not None:
        cfg = get_merge_level_config(target_level)
        progress = _progress_count(counts, target_level)
        return (
            f"Ready: {get_merge_level_emoji(target_level)} L{target_level} "
            f"({min(progress, cfg.input_count)}/{cfg.input_count})"
        )[:100]
    cfg = get_merge_level_config(open_level)
    progress = _progress_count(counts, open_level)
    return (
        f"Next: {get_merge_level_emoji(open_level)} L{open_level} ({min(progress, cfg.input_count)}/{cfg.input_count})"
    )[:100]


def _format_ladder_row(level: int, counts: dict[int, int]) -> str:
    emoji = get_merge_level_emoji(level)
    cfg = get_merge_level_config(level)
    open_level = _open_level(counts)
    progress = _progress_count(counts, level)
    owned_count = counts.get(level, 0)
    current_target = _current_target_level(counts)

    if level > open_level:
        return f"🔒 {emoji} **L{level}** · locked until you forge {get_merge_level_emoji(level - 1)} **L{level - 1}**"

    if level == current_target:
        return (
            f"➡️ {emoji} **L{level}** · own `{owned_count}` · "
            f"progress `{min(progress, cfg.input_count)}/{cfg.input_count}` · **ready now**"
        )

    marker = "✅" if owned_count else "▫️"
    return (
        f"{marker} {emoji} **L{level}** · own `{owned_count}` · needs **{cfg.input_count}× {_input_label(level)}** · "
        f"progress `{min(progress, cfg.input_count)}/{cfg.input_count}`"
    )


def _selectable(summary: MergeClubballSummary) -> bool:
    counts = summary.counts
    return sum(counts.get(level, 0) for level in range(0, MAX_MERGE_LEVEL)) > 0


def _find_summary(summaries: list[MergeClubballSummary], ball_id: int | None) -> MergeClubballSummary | None:
    if ball_id is None:
        return None
    return next((summary for summary in summaries if summary.ball.pk == ball_id), None)


async def _instance_level_for_summary(instance: BallInstance, merge_special_id: int) -> int | None:
    if instance.special_id != merge_special_id:
        return 0
    cfg = next(
        (
            level
            for level in range(1, MAX_MERGE_LEVEL + 1)
            if instance.attack_bonus == get_merge_level_config(level).attack_bonus
            and instance.health_bonus == get_merge_level_config(level).health_bonus
        ),
        None,
    )
    return cfg


async def _load_merge_summaries(player: Player) -> list[MergeClubballSummary]:
    merge_special = await get_merge_special()
    grouped: dict[int, dict[int, list[BallInstance]]] = {}

    async for instance in (
        BallInstance.objects.filter(player=player, deleted=False).select_related("special").order_by("pk")
    ):
        if await instance.is_locked():
            continue
        if await instance_already_used_in_merge(instance.pk):
            continue
        level = await _instance_level_for_summary(instance, merge_special.pk)
        if level is None:
            continue
        grouped.setdefault(instance.ball_id, _empty_buckets())[level].append(instance)

    summaries: list[MergeClubballSummary] = []
    for buckets in grouped.values():
        first_instance = next((instances[0] for instances in buckets.values() if instances), None)
        if first_instance is None:
            continue
        ball = await get_ball(first_instance)
        summaries.append(MergeClubballSummary(ball=ball, buckets=buckets))

    summaries.sort(key=lambda item: item.ball.country.lower())
    return summaries


class MergeClubballSelect(discord.ui.Select):
    def __init__(self, owner_id: int, summaries: list[MergeClubballSummary], *, selected_ball_id: int | None):
        self.owner_id = owner_id
        options = [
            discord.SelectOption(
                label=summary.ball.country[:100],
                value=str(summary.ball.pk),
                description=_option_description(summary),
                emoji=get_merge_level_emoji(_open_level(summary.counts)),
                default=summary.ball.pk == selected_ball_id,
            )
            for summary in summaries[:25]
            if _selectable(summary)
        ]
        super().__init__(
            placeholder="Select the clubball you want to forge…", options=options, min_values=1, max_values=1
        )

    async def callback(self, interaction: Interaction) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This forge is private to you.", ephemeral=True)
            return
        bot = cast("BallsDexBot", interaction.client)
        layout = await build_merge_picker_view(bot, self.owner_id, selected_ball_id=int(self.values[0]))
        await interaction.response.edit_message(view=layout)


class MergeActionRow(ActionRow):
    def __init__(self, owner_id: int, ball_id: int | None, *, can_forge: bool, target_level: int | None):
        super().__init__()
        self.owner_id = owner_id
        self.ball_id = ball_id
        if target_level is None:
            self.forge_button.label = "No forge available"
            self.forge_button.disabled = True
        else:
            self.forge_button.label = f"Forge {get_merge_level_emoji(target_level)} L{target_level}"
            self.forge_button.disabled = not can_forge

    @button(label="Forge next", style=discord.ButtonStyle.success, emoji="✨")
    async def forge_button(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This forge is private to you.", ephemeral=True)
            return
        if self.ball_id is None:
            await interaction.response.send_message("Pick a clubball first.", ephemeral=True)
            return

        bot = cast("BallsDexBot", interaction.client)
        await interaction.response.defer()
        loading_layout = await build_merge_picker_view(
            bot,
            self.owner_id,
            selected_ball_id=self.ball_id,
            notice="⏳ Forging your next tier…",
        )
        await interaction.edit_original_response(view=loading_layout, attachments=[])
        player, _ = await Player.objects.aget_or_create(discord_id=self.owner_id)
        summaries = await _load_merge_summaries(player)
        summary = _find_summary(summaries, self.ball_id)
        if summary is None:
            layout = await build_merge_picker_view(
                bot, self.owner_id, notice="❌ That clubball is no longer mergeable."
            )
            await interaction.edit_original_response(view=layout, attachments=[])
            return

        target_level = _current_target_level(summary.counts)
        if target_level is None:
            layout = await build_merge_picker_view(
                bot,
                self.owner_id,
                selected_ball_id=self.ball_id,
                notice="❌ You do not have enough copies for the next visible forge tier yet.",
            )
            await interaction.edit_original_response(view=layout, attachments=[])
            return

        instances = _target_instances(summary, target_level)
        try:
            await validate_merge_batch(player, instances)
            _, summary_text, _, _ = await execute_merge(player, instances, guild_id=interaction.guild_id, bot=bot)
        except MergeValidationError as exc:
            layout = await build_merge_picker_view(
                bot, self.owner_id, selected_ball_id=self.ball_id, notice=f"❌ {exc.message}"
            )
            await interaction.edit_original_response(view=layout, attachments=[])
            return
        except Exception:
            log.exception("Merge forge failed for user %s ball %s", self.owner_id, self.ball_id)
            layout = await build_merge_picker_view(
                bot,
                self.owner_id,
                selected_ball_id=self.ball_id,
                notice="❌ Forge failed unexpectedly. Try again, and check logs if it keeps happening.",
            )
            await interaction.edit_original_response(view=layout, attachments=[])
            return

        layout = await build_merge_picker_view(bot, self.owner_id, selected_ball_id=self.ball_id, notice=summary_text)
        try:
            await interaction.edit_original_response(view=layout, attachments=[])
        except discord.HTTPException:
            log.exception("Merge panel refresh failed after forge for user %s", self.owner_id)
            await interaction.followup.send(summary_text, ephemeral=True)

    @button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh_button(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This forge is private to you.", ephemeral=True)
            return
        bot = cast("BallsDexBot", interaction.client)
        layout = await build_merge_picker_view(bot, self.owner_id, selected_ball_id=self.ball_id)
        await interaction.response.edit_message(view=layout)


async def build_merge_picker_view(
    bot: BallsDexBot, owner_id: int, *, selected_ball_id: int | None = None, notice: str = ""
) -> LayoutView:
    player, _ = await Player.objects.aget_or_create(discord_id=owner_id)
    summaries = await _load_merge_summaries(player)
    selectable = [summary for summary in summaries if _selectable(summary)]
    selected = _find_summary(summaries, selected_ball_id) if selected_ball_id is not None else None

    quota_settings = await get_merge_quota_settings()
    quota_snapshot = await get_merge_quota_snapshot(player)
    quota_block = format_quota_status_block(quota_snapshot, settings_period_days=quota_settings.period_days)
    tier_guide = " · ".join(format_level_table_row(level) for level in range(1, MAX_MERGE_LEVEL + 1))

    header = "# ✨ Merge forge"
    if notice:
        header = f"{notice}\n\n{header}"

    if not summaries:
        body = (
            "You do not own any clubballs that can enter the forge yet.\n\n"
            f"{quota_block}\n\n"
            f"-# Tier guide: {tier_guide}"
        )
        target_level = None
    elif selected is None:
        body = (
            "Select **one clubball** below and the forge will show its whole ladder.\n\n"
            f"{quota_block}\n\n"
            "-# You no longer need to pick 10 separate cards in slash-command fields.\n"
            "-# Levels unlock one by one; higher tiers stay locked until you forge the previous tier.\n"
            f"-# Tier guide: {tier_guide}"
        )
        target_level = None
    else:
        counts = selected.counts
        open_level = _open_level(counts)
        target_level = _current_target_level(counts)
        special = await get_merge_special()

        if target_level is not None:
            base_attack, base_health, final_attack, final_health = preview_merge_stats(selected.ball, target_level)
            next_line = (
                f"{get_merge_level_emoji(target_level)} **Next forge:** L{target_level}\n"
                f"{format_merge_input_requirement(0 if target_level == 1 else target_level - 1, target_level)}\n"
                f"Result: **{special.emoji or get_merge_level_emoji(target_level)} {MERGE_SPECIAL_NAME}** "
                f"`{selected.ball.country}` · **{final_attack}** ATK / **{final_health}** HP "
                f"(`{base_attack}` / `{base_health}` base)"
            )
        else:
            next_line = (
                f"🔒 **Current lock:** you need more **{_input_label(open_level)}** to reach "
                f"{get_merge_level_emoji(open_level)} **L{open_level}**."
            )

        ladder = "\n".join(_format_ladder_row(level, counts) for level in range(1, MAX_MERGE_LEVEL + 1))
        body = (
            f"**Selected clubball:** **{selected.ball.country}**\n"
            f"{next_line}\n\n"
            f"{quota_block}\n\n"
            f"### Ladder\n{ladder}\n\n"
            "-# Forge uses your available copies automatically: same **clubball** only, "
            "common copies for **L1**, then same-tier forge copies for later levels.\n"
            f"-# {get_merge_level_emoji(MAX_MERGE_LEVEL)} **L{MAX_MERGE_LEVEL}** is the max tier "
            "and can’t be forged again."
        )

    layout = LayoutView(timeout=300)
    container = Container()
    container.add_item(TextDisplay(truncate_text(f"{header}\n\n{body}")))
    if selectable:
        container.add_item(Separator())
        row = ActionRow()
        row.add_item(MergeClubballSelect(owner_id, selectable, selected_ball_id=selected_ball_id))
        container.add_item(row)
    container.add_item(Separator())
    container.add_item(
        MergeActionRow(
            owner_id,
            selected_ball_id if selected is not None else None,
            can_forge=target_level is not None,
            target_level=target_level,
        )
    )
    layout.add_item(container)
    return layout
