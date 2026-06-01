from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile
from django.utils import timezone

from bd_models.models import Special, specials
from fcdex_3_1.fcdex_ext.merge_assets import MERGE_BACKGROUND_FILENAME, read_merge_card

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("fcdex_3_1.merge.special")

MERGE_SPECIAL_NAME = "FCDex Merge"
MERGE_SPECIAL_EMOJI = "✨"
MERGE_SPECIAL_CATCH = "Forged in the FCDex merge — two clubballs became one masterpiece."


def _save_background_sync(special: Special, payload: bytes) -> None:
    special.background.save(MERGE_BACKGROUND_FILENAME, ContentFile(payload), save=True)


def _has_background_file(special: Special) -> bool:
    return bool(special.background and special.background.name)


async def _save_background(special: Special, payload: bytes) -> None:
    await sync_to_async(_save_background_sync)(special, payload)


async def ensure_merge_special() -> Special:
    """Create or repair the merge special and register it in the in-memory cache."""
    payload = read_merge_card()
    special = await Special.objects.filter(name=MERGE_SPECIAL_NAME).afirst()

    if special is None:
        special = await Special.objects.acreate(
            name=MERGE_SPECIAL_NAME,
            catch_phrase=MERGE_SPECIAL_CATCH,
            emoji=MERGE_SPECIAL_EMOJI,
            rarity=0,
            tradeable=True,
            hidden=True,
            start_date=timezone.now(),
        )
        await _save_background(special, payload)
        special = await Special.objects.aget(pk=special.pk)
        log.info("Created merge special %s (pk=%s).", MERGE_SPECIAL_NAME, special.pk)
    elif not await sync_to_async(_has_background_file)(special):
        await _save_background(special, payload)
        special = await Special.objects.aget(pk=special.pk)
        log.info("Repaired missing background for merge special pk=%s.", special.pk)

    specials[special.pk] = special
    return special


async def get_merge_special() -> Special:
    cached = next((s for s in specials.values() if s.name == MERGE_SPECIAL_NAME), None)
    if cached is not None:
        return cached
    return await ensure_merge_special()


async def bootstrap_merge_special(bot: BallsDexBot | None = None) -> Special:
    special = await ensure_merge_special()
    if bot is not None and hasattr(bot, "load_cache"):
        await bot.load_cache()
    return special
