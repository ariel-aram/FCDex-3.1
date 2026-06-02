from __future__ import annotations

import re

import discord

from bd_models.models import Ball, BallInstance, Player

_MENTION_RE = re.compile(r"^<@!?(\d+)>$")


def _normalize_token(value: str) -> str:
    return value.strip().lstrip("#")


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
        player = await Player.objects.filter(discord_id=discord_id).afirst()
        if player is not None:
            return player
        if len(token) < 17:
            return await Player.objects.filter(pk=discord_id).afirst()

    if guild is not None:
        lowered = raw.lower().lstrip("@")
        for member in guild.members:
            names = {member.name.lower(), member.display_name.lower()}
            if member.global_name:
                names.add(member.global_name.lower())
            if lowered in names:
                return await Player.objects.filter(discord_id=member.id).afirst()

    return None
