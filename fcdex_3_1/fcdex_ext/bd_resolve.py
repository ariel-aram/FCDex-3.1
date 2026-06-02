from __future__ import annotations

import re

import discord

from bd_models.models import Ball, BallInstance, Player

_MENTION_RE = re.compile(r"^<@!?(\d+)>$")
_USER_DISCRIMINATOR_RE = re.compile(r"^(.+)#(\d{1,4})$")

PLAYER_NOT_FOUND_MESSAGE = "Player not found — use @mention, server username, or numeric Discord user ID."


def _normalize_token(value: str) -> str:
    return value.strip().lstrip("#")


def _parse_username_discriminator(value: str) -> tuple[str, str | None]:
    """Return (username, discriminator) with discriminator None if not a legacy tag."""
    text = value.strip().lstrip("@")
    match = _USER_DISCRIMINATOR_RE.match(text)
    if match:
        return match.group(1), match.group(2)
    return text, None


def _member_name_keys(member: discord.Member) -> set[str]:
    names = {member.name.lower(), member.display_name.lower()}
    if member.global_name:
        names.add(member.global_name.lower())
    nick = getattr(member, "nick", None)
    if nick:
        names.add(nick.lower())
    return names


def _member_matches_token(member: discord.Member, name_lower: str, discriminator: str | None) -> bool:
    if discriminator is not None:
        if member.name.lower() != name_lower:
            return False
        member_disc = member.discriminator
        if member_disc == "0" and discriminator == "0":
            return True
        return member_disc == discriminator
    return name_lower in _member_name_keys(member)


async def _player_for_discord_id(discord_id: int) -> Player | None:
    return await Player.objects.filter(discord_id=discord_id).afirst()


async def _resolve_guild_member(guild: discord.Guild, raw: str) -> discord.Member | None:
    search = raw.strip().lstrip("@")
    if not search:
        return None
    name_part, disc_part = _parse_username_discriminator(search)
    name_lower = name_part.lower()

    for member in guild.members:
        if _member_matches_token(member, name_lower, disc_part):
            return member

    query = name_part if disc_part is not None else search
    if not query:
        return None
    try:
        members = await guild.query_members(query=query, limit=15)
    except (discord.HTTPException, discord.Forbidden, AttributeError):
        members = []
    for member in members:
        if _member_matches_token(member, name_lower, disc_part):
            return member
    return None


async def resolve_ball_input(value: str) -> Ball | None:
    """Resolve a dex Ball by primary key or country name (case-insensitive)."""
    raw = value.strip()
    if not raw:
        return None
    token = _normalize_token(raw)
    if token.isdigit():
        ball = await Ball.objects.filter(pk=int(token)).afirst()
        if ball is not None:
            return ball
    ball = await Ball.objects.filter(country__iexact=raw).afirst()
    if ball is None and token != raw:
        ball = await Ball.objects.filter(country__iexact=token).afirst()
    return ball


async def resolve_ball_for_lookup(value: str) -> Ball | None:
    """Resolve Ball by PK, BallInstance PK, or country name."""
    raw = value.strip()
    if not raw:
        return None
    token = _normalize_token(raw)
    if token.isdigit():
        pk = int(token)
        ball = await Ball.objects.filter(pk=pk).afirst()
        if ball is not None:
            return ball
        inst = await BallInstance.objects.filter(pk=pk, deleted=False).select_related("ball").afirst()
        if inst is not None:
            return inst.ball
    return await resolve_ball_input(value)


async def resolve_ball_instance_input(value: str, player: Player) -> BallInstance | None:
    """Resolve a player's BallInstance by instance PK, Ball PK, or country name."""
    raw = value.strip()
    if not raw:
        return None
    token = _normalize_token(raw)
    if token.isdigit():
        pk = int(token)
        inst = await BallInstance.objects.filter(pk=pk, player=player, deleted=False).select_related("ball").afirst()
        if inst is not None:
            return inst
        ball = await Ball.objects.filter(pk=pk).afirst()
        if ball is not None:
            return (
                await BallInstance.objects.filter(ball=ball, player=player, deleted=False)
                .select_related("ball")
                .order_by("-pk")
                .afirst()
            )
    ball = await resolve_ball_input(value)
    if ball is None:
        return None
    return (
        await BallInstance.objects.filter(ball=ball, player=player, deleted=False)
        .select_related("ball")
        .order_by("-pk")
        .afirst()
    )


async def resolve_player_input(value: str, *, guild: discord.Guild | None = None) -> Player | None:
    """Resolve a Player by Discord ID, player PK, @mention, or guild display/name."""
    raw = value.strip()
    if not raw:
        return None

    mention = _MENTION_RE.match(raw)
    token = mention.group(1) if mention else raw.lstrip("@").lstrip("#")

    if token.isdigit():
        discord_id = int(token)
        player = await _player_for_discord_id(discord_id)
        if player is not None:
            return player
        if len(token) < 17:
            player = await Player.objects.filter(pk=discord_id).afirst()
            if player is not None:
                return player
        if guild is not None and mention is not None:
            member = guild.get_member(discord_id)
            if member is None:
                try:
                    member = await guild.fetch_member(discord_id)
                except (discord.HTTPException, discord.NotFound):
                    member = None
            if member is not None:
                return await _player_for_discord_id(member.id)

    if guild is not None:
        member = await _resolve_guild_member(guild, raw)
        if member is not None:
            return await _player_for_discord_id(member.id)

    return None
