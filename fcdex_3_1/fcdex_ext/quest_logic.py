from __future__ import annotations

from django.utils import timezone

from bd_models.models import Player
from fcdex_3_0.models import PlayerQuestProgress

DAILY_QUESTS = (
    ("pack_daily", "Open your daily pack", 1, 500),
    ("battle_play", "Play a battle", 1, 300),
    ("merge_once", "Complete a merge", 1, 400),
)


async def ensure_daily_quests(player: Player) -> list[PlayerQuestProgress]:
    today = timezone.localdate()
    rows: list[PlayerQuestProgress] = []
    for key, _label, target, _coins in DAILY_QUESTS:
        row, _ = await PlayerQuestProgress.objects.aget_or_create(
            player=player, quest_key=key, day=today, defaults={"target": target, "progress": 0}
        )
        rows.append(row)
    return rows


async def bump_quest(player: Player, quest_key: str, amount: int = 1) -> None:
    today = timezone.localdate()
    try:
        row = await PlayerQuestProgress.objects.aget(player=player, quest_key=quest_key, day=today)
    except PlayerQuestProgress.DoesNotExist:
        return
    if row.claimed_at:
        return
    row.progress = min(row.target, row.progress + amount)
    if row.progress >= row.target and not row.completed_at:
        row.completed_at = timezone.now()
    await row.asave(update_fields=("progress", "completed_at"))


async def claim_quest(player: Player, quest_key: str) -> tuple[bool, str]:
    today = timezone.localdate()
    try:
        row = await PlayerQuestProgress.objects.aget(player=player, quest_key=quest_key, day=today)
    except PlayerQuestProgress.DoesNotExist:
        return False, "Quest not found for today."

    if not row.completed_at:
        return False, f"Quest not complete ({row.progress}/{row.target})."
    if row.claimed_at:
        return False, "Already claimed today."

    reward = next((coins for k, _, _, coins in DAILY_QUESTS if k == quest_key), 0)
    if reward:
        await player.add_money(reward)
    row.claimed_at = timezone.now()
    await row.asave(update_fields=("claimed_at",))
    label = next((lbl for k, lbl, _, _ in DAILY_QUESTS if k == quest_key), quest_key)
    return True, f"Claimed **{label}** — **+{reward:,}** coins!"
