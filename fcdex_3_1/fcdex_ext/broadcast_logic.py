from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from bd_models.models import Player
from fcdex_3_1.fcdex_ext.leaderboard_logic import EXCLUDE_IDS

import discord

log = logging.getLogger("fcdex_3_1.broadcast")

DISCORD_MESSAGE_MAX = 2000
DM_BATCH_SIZE = 5
DM_BATCH_DELAY_SECONDS = 1.0
DM_PROGRESS_EVERY = 25
SERVER_GUILD_DELAY_SECONDS = 0.75
SERVER_PROGRESS_EVERY = 10


def validate_broadcast_message(message: str) -> tuple[bool, str]:
    """Return (ok, cleaned message or error text)."""
    text = message.strip()
    if not text:
        return False, "Message cannot be empty."
    if len(text) > DISCORD_MESSAGE_MAX:
        return False, f"Message is too long ({len(text)} characters). Maximum is {DISCORD_MESSAGE_MAX}."
    return True, text


def preview_broadcast_message(message: str, *, max_len: int = 500) -> str:
    if len(message) <= max_len:
        return message
    return message[: max_len - 1] + "…"


def _recipient_queryset():
    qs = Player.objects.filter(balls__deleted=False).distinct()
    if EXCLUDE_IDS:
        qs = qs.exclude(discord_id__in=EXCLUDE_IDS)
    return qs


async def count_dm_recipients() -> int:
    return await _recipient_queryset().acount()


async def iter_dm_recipient_ids() -> AsyncIterator[int]:
    qs = _recipient_queryset().values_list("discord_id", flat=True).order_by("discord_id")
    async for discord_id in qs.aiterator(chunk_size=500):
        yield int(discord_id)


def pick_guild_announce_channel(
    guild: discord.Guild,
    bot_member: discord.Member,
    *,
    raid_channel_id: int | None = None,
) -> discord.TextChannel | discord.Thread | None:
    """Pick a channel the bot can post server-wide announcements in."""
    perms = bot_member.guild_permissions

    def can_send(channel: discord.abc.GuildChannel | None) -> bool:
        if channel is None or not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return False
        return channel.permissions_for(bot_member).send_messages

    if raid_channel_id is not None:
        raid_ch = guild.get_channel(raid_channel_id)
        if can_send(raid_ch):
            return raid_ch  # type: ignore[return-value]

    system = guild.system_channel
    if can_send(system):
        return system

    news = [
        ch
        for ch in guild.text_channels
        if ch.is_news() and ch.permissions_for(bot_member).send_messages and perms.send_messages
    ]
    if news:
        return sorted(news, key=lambda c: c.position)[0]

    for ch in sorted(guild.text_channels, key=lambda c: c.position):
        if ch.permissions_for(bot_member).send_messages:
            return ch
    return None


def raid_channel_id_for_guild(guild_id: int) -> int | None:
    from fcdex_3_1.fcdex_ext.boss_raid import get_raid

    raid = get_raid(guild_id)
    return raid.channel_id if raid is not None else None


async def sleep_dm_batch(batch_index: int) -> None:
    if batch_index > 0 and batch_index % DM_BATCH_SIZE == 0:
        await asyncio.sleep(DM_BATCH_DELAY_SECONDS)
