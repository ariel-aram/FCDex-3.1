from __future__ import annotations

from bd_models.models import BallInstance, Player

# Shiny conversion: sacrifice 2 identical copies → 1 powered-up copy (+25% ATK/HP bonuses).
SHINY_ATTACK_BONUS = 25
SHINY_HEALTH_BONUS = 25


class ShinyError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def is_shiny_instance(instance: BallInstance) -> bool:
    return instance.attack_bonus >= SHINY_ATTACK_BONUS and instance.health_bonus >= SHINY_HEALTH_BONUS


async def convert_to_shiny(player: Player, template: BallInstance, *, guild_id: int | None) -> str:
    if template.deleted:
        raise ShinyError("That card is no longer available.")
    if template.player_id != player.pk:
        raise ShinyError("That card isn't yours.")
    if is_shiny_instance(template):
        raise ShinyError("That card is already shiny.")

    siblings = [
        inst
        async for inst in BallInstance.objects.filter(player=player, ball_id=template.ball_id, deleted=False).order_by(
            "pk"
        )
    ]
    plain = [i for i in siblings if not is_shiny_instance(i)]
    if len(plain) < 2:
        raise ShinyError("You need **2** copies of the same clubball (non-shiny) to convert.")

    to_consume = plain[:2]
    ids = [i.pk for i in to_consume]
    await BallInstance.objects.filter(pk__in=ids).aupdate(deleted=True)
    shiny = await BallInstance.objects.acreate(
        ball_id=template.ball_id,
        player=player,
        attack_bonus=SHINY_ATTACK_BONUS,
        health_bonus=SHINY_HEALTH_BONUS,
        server_id=guild_id,
    )
    return f"✨ Shiny conversion complete! Card **#{shiny.pk}** (+{SHINY_ATTACK_BONUS}% ATK / HP)."
