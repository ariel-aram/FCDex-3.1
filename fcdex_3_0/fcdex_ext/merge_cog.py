from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ballsdex.core.utils.transformers import BallInstanceTransform
from bd_models.models import Player
from fcdex_3_0.fcdex_ext.merge_logic import MergeValidationError, validate_merge_batch
from fcdex_3_0.fcdex_ext.merge_views import build_merge_confirm_view

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("fcdex_3_0.merge")


def _collect_merge_cards(
    card1: BallInstanceTransform,
    card2: BallInstanceTransform | None = None,
    card3: BallInstanceTransform | None = None,
    card4: BallInstanceTransform | None = None,
    card5: BallInstanceTransform | None = None,
    card6: BallInstanceTransform | None = None,
    card7: BallInstanceTransform | None = None,
    card8: BallInstanceTransform | None = None,
    card9: BallInstanceTransform | None = None,
    card10: BallInstanceTransform | None = None,
) -> list[BallInstanceTransform]:
    return [
        card for card in (card1, card2, card3, card4, card5, card6, card7, card8, card9, card10) if card is not None
    ]


class MergeCog(commands.Cog):
    """Forge matching clubballs through seven merge tiers."""

    def __init__(self, bot: BallsDexBot):
        self.bot = bot

    @app_commands.command(
        name="merge",
        description="Sacrifice matching clubballs to forge a tiered FCDex merge card (2–10 inputs by level)",
    )
    @app_commands.describe(
        card1="First clubball (required)",
        card2="Second clubball",
        card3="Third clubball",
        card4="Fourth clubball",
        card5="Fifth clubball",
        card6="Sixth clubball",
        card7="Seventh clubball",
        card8="Eighth clubball",
        card9="Ninth clubball",
        card10="Tenth clubball",
    )
    async def merge(
        self,
        interaction: discord.Interaction,
        card1: BallInstanceTransform,
        card2: BallInstanceTransform | None = None,
        card3: BallInstanceTransform | None = None,
        card4: BallInstanceTransform | None = None,
        card5: BallInstanceTransform | None = None,
        card6: BallInstanceTransform | None = None,
        card7: BallInstanceTransform | None = None,
        card8: BallInstanceTransform | None = None,
        card9: BallInstanceTransform | None = None,
        card10: BallInstanceTransform | None = None,
    ):
        cards = _collect_merge_cards(card1, card2, card3, card4, card5, card6, card7, card8, card9, card10)
        player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
        try:
            await validate_merge_batch(player, cards)
        except MergeValidationError as exc:
            await interaction.response.send_message(exc.message, ephemeral=True)
            return

        instance_ids = [card.pk for card in cards]
        layout = await build_merge_confirm_view(self.bot, interaction.user.id, instance_ids)
        await interaction.response.send_message(view=layout)  # pyright: ignore[reportArgumentType]
