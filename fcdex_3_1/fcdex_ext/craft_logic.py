from __future__ import annotations

from bd_models.models import BallInstance, Player
from fcdex_3_0.models import SBCRecipe


class CraftError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def complete_sbc(player: Player, recipe: SBCRecipe, *, guild_id: int | None) -> str:
    owned = [
        inst
        async for inst in BallInstance.objects.filter(
            player=player, ball_id=recipe.required_ball_id, deleted=False
        ).order_by("pk")[: recipe.required_count]
    ]
    if len(owned) < recipe.required_count:
        ball = recipe.required_ball
        country = ball.country if hasattr(ball, "country") else f"ball #{recipe.required_ball_id}"
        raise CraftError(f"You need **{recipe.required_count}× {country}** (you have **{len(owned)}**).")

    ids = [inst.pk for inst in owned]
    updated = await BallInstance.objects.filter(pk__in=ids, player=player, deleted=False).aupdate(deleted=True)
    if updated != len(ids):
        raise CraftError("Some cards were already used — try again.")

    await BallInstance.objects.acreate(
        ball_id=recipe.reward_ball_id, player=player, attack_bonus=0, health_bonus=0, server_id=guild_id
    )
    if recipe.reward_money:
        await player.add_money(recipe.reward_money)

    reward = recipe.reward_ball
    reward_name = reward.country if hasattr(reward, "country") else f"ball #{recipe.reward_ball_id}"
    parts = [f"**{recipe.name}** complete! Received **{reward_name}**"]
    if recipe.reward_money:
        parts.append(f"**+{recipe.reward_money:,}** coins")
    return " · ".join(parts)
