from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Literal

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, button

from fcdex_3_1.fcdex_ext.broadcast_logic import (
    DISCORD_MESSAGE_MAX,
    DM_PROGRESS_EVERY,
    SERVER_GUILD_DELAY_SECONDS,
    SERVER_PROGRESS_EVERY,
    count_dm_recipients,
    iter_dm_recipient_ids,
    pick_guild_announce_channel,
    preview_broadcast_message,
    raid_channel_id_for_guild,
    sleep_dm_batch,
    validate_broadcast_message,
)

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("fcdex_3_1.broadcast.cog")

BroadcastKind = Literal["dm", "server"]


def broadcast_admin_check():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is not None:
            return bool(interaction.user.guild_permissions.manage_guild)
        return await interaction.client.is_owner(interaction.user)

    return app_commands.check(predicate)


class BroadcastConfirmView(View):
    def __init__(
        self,
        *,
        owner_id: int,
        kind: BroadcastKind,
        message: str,
        recipient_label: str,
    ):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.kind = kind
        self.message = message
        self.recipient_label = recipient_label
        self._started = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This confirmation is not yours.", ephemeral=True)
            return False
        return True

    @button(label="Confirm broadcast", style=discord.ButtonStyle.danger, emoji="📣")
    async def confirm(self, interaction: discord.Interaction, button: Button) -> None:
        if self._started:
            await interaction.response.send_message("Broadcast already started.", ephemeral=True)
            return
        self._started = True
        for child in self.children:
            child.disabled = True  # type: ignore[union-attr]
        await interaction.response.defer(ephemeral=True)
        await interaction.edit_original_response(
            content="Broadcast started…", embed=None, view=self
        )
        bot: BallsDexBot = interaction.client  # type: ignore[assignment]
        if self.kind == "dm":
            await _run_dm_broadcast(interaction, bot, self.message)
        else:
            await _run_server_broadcast(interaction, bot, self.message)

    @button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: Button) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore[union-attr]
        await interaction.response.edit_message(
            content="Broadcast cancelled.", embed=None, view=self
        )


async def _edit_status(interaction: discord.Interaction, text: str) -> None:
    try:
        await interaction.edit_original_response(content=text)
    except discord.HTTPException:
        log.debug("Could not edit broadcast status message", exc_info=True)


async def _run_dm_broadcast(interaction: discord.Interaction, bot: BallsDexBot, message: str) -> None:
    total = await count_dm_recipients()
    sent = 0
    dm_closed = 0
    other_fail = 0
    processed = 0

    await _edit_status(interaction, f"Starting DM broadcast to **{total:,}** players…")

    async for discord_id in iter_dm_recipient_ids():
        processed += 1
        try:
            user = await bot.fetch_user(discord_id)
            await user.send(message)
            sent += 1
        except discord.Forbidden:
            dm_closed += 1
        except discord.HTTPException as exc:
            other_fail += 1
            log.warning("DM broadcast failed for %s: %s", discord_id, exc)
        except Exception:
            other_fail += 1
            log.exception("DM broadcast failed for %s", discord_id)

        if processed % DM_PROGRESS_EVERY == 0 or processed == total:
            await _edit_status(
                interaction,
                f"DM broadcast… **{sent:,}** sent · **{processed:,}/{total:,}** processed",
            )
        await sleep_dm_batch(processed)

    summary = (
        f"**DM broadcast complete**\n"
        f"- Sent: **{sent:,}**\n"
        f"- DMs closed / blocked: **{dm_closed:,}**\n"
        f"- Other failures: **{other_fail:,}**\n"
        f"- Total targeted: **{total:,}**"
    )
    await _edit_status(interaction, summary)


async def _run_server_broadcast(interaction: discord.Interaction, bot: BallsDexBot, message: str) -> None:
    guilds = list(bot.guilds)
    total = len(guilds)
    posted = 0
    skipped = 0
    failed = 0

    await _edit_status(interaction, f"Starting server broadcast across **{total:,}** servers…")

    for index, guild in enumerate(guilds, start=1):
        member = guild.me
        if member is None:
            skipped += 1
            continue
        channel = pick_guild_announce_channel(
            guild, member, raid_channel_id=raid_channel_id_for_guild(guild.id)
        )
        if channel is None:
            skipped += 1
            continue
        try:
            await channel.send(message)
            posted += 1
        except discord.Forbidden:
            skipped += 1
            log.warning("Server broadcast: no permission in %s (#%s)", guild.id, channel.id)
        except discord.HTTPException as exc:
            failed += 1
            log.warning("Server broadcast failed in %s: %s", guild.id, exc)
        except Exception:
            failed += 1
            log.exception("Server broadcast failed in guild %s", guild.id)

        if index % SERVER_PROGRESS_EVERY == 0 or index == total:
            await _edit_status(
                interaction,
                f"Server broadcast… **{posted:,}** posted · **{index:,}/{total:,}** servers",
            )
        if index < total:
            await asyncio.sleep(SERVER_GUILD_DELAY_SECONDS)

    summary = (
        f"**Server broadcast complete**\n"
        f"- Posted: **{posted:,}**\n"
        f"- Skipped (no channel / permission): **{skipped:,}**\n"
        f"- Failed: **{failed:,}**\n"
        f"- Guilds: **{total:,}**"
    )
    await _edit_status(interaction, summary)


async def _prompt_broadcast(
    interaction: discord.Interaction,
    *,
    kind: BroadcastKind,
    message: str,
) -> None:
    ok, result = validate_broadcast_message(message)
    if not ok:
        await interaction.response.send_message(result, ephemeral=True)
        return

    cleaned = result
    if kind == "dm":
        count = await count_dm_recipients()
        recipient_label = f"**{count:,}** players with at least one clubball (non-deleted)"
        title = "DM broadcast"
        warning = (
            "This will DM every eligible player. Rate-limited batches reduce 429 risk; "
            "large sends may take several minutes."
        )
    else:
        count = len(interaction.client.guilds)
        recipient_label = f"**{count:,}** servers (one message per server)"
        title = "Server broadcast"
        warning = "This posts your message publicly in each target server channel."

    embed = discord.Embed(
        title=f"Confirm · {title}",
        description=(
            f"{recipient_label}\n\n"
            f"**Preview**\n{preview_broadcast_message(cleaned)}\n\n"
            f"-# {warning}"
        ),
        color=discord.Color.orange(),
    )
    view = BroadcastConfirmView(
        owner_id=interaction.user.id,
        kind=kind,
        message=cleaned,
        recipient_label=recipient_label,
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class BroadcastCog(commands.GroupCog, group_name="broadcast"):
    """Mass announcements — admin-only with confirmation."""

    def __init__(self, bot: BallsDexBot):
        self.bot = bot

    @app_commands.command(
        name="dm",
        description="DM every player who has caught at least one clubball (admin · confirmation required)",
    )
    @app_commands.describe(message=f"Announcement text (max {DISCORD_MESSAGE_MAX} characters)")
    @broadcast_admin_check()
    async def dm(self, interaction: discord.Interaction, message: str):
        await _prompt_broadcast(interaction, kind="dm", message=message)

    @app_commands.command(
        name="dm_announcement",
        description="Alias for /broadcast dm — DM players with at least one clubball",
    )
    @app_commands.describe(message=f"Announcement text (max {DISCORD_MESSAGE_MAX} characters)")
    @broadcast_admin_check()
    async def dm_announcement(self, interaction: discord.Interaction, message: str):
        await _prompt_broadcast(interaction, kind="dm", message=message)

    @app_commands.command(
        name="server",
        description="Post an announcement in every server the bot is in (admin · confirmation required)",
    )
    @app_commands.describe(message=f"Announcement text (max {DISCORD_MESSAGE_MAX} characters)")
    @broadcast_admin_check()
    async def server(self, interaction: discord.Interaction, message: str):
        await _prompt_broadcast(interaction, kind="server", message=message)

    @app_commands.command(
        name="server_announcement",
        description="Alias for /broadcast server — announce in all guilds",
    )
    @app_commands.describe(message=f"Announcement text (max {DISCORD_MESSAGE_MAX} characters)")
    @broadcast_admin_check()
    async def server_announcement(self, interaction: discord.Interaction, message: str):
        await _prompt_broadcast(interaction, kind="server", message=message)
