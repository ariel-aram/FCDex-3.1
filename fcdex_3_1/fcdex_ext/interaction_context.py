from __future__ import annotations

from dataclasses import dataclass

import discord


@dataclass(frozen=True, slots=True)
class AdminContext:
    """Resolved Discord location for admin panels and boss raids."""

    guild_id: int | None
    channel_id: int
    scope_id: int
    reward_server_id: int | None

    @classmethod
    def from_interaction(cls, interaction: discord.Interaction) -> AdminContext:
        guild_id = interaction.guild_id
        channel_id = interaction.channel_id
        return cls(
            guild_id=guild_id,
            channel_id=channel_id,
            scope_id=channel_id,
            reward_server_id=guild_id,
        )


def admin_context(interaction: discord.Interaction) -> AdminContext:
    return AdminContext.from_interaction(interaction)
