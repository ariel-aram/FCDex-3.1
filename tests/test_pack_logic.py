from __future__ import annotations

import sys
from datetime import timedelta
from types import ModuleType, SimpleNamespace

# pack_logic imports discord at module load; stub it so pure helpers are testable without discord.py.
if "discord" not in sys.modules:
    discord_stub = ModuleType("discord")

    class _File:
        def __init__(self, fp, filename: str | None = None) -> None:
            self.fp = fp
            self.filename = filename

    discord_stub.File = _File
    sys.modules["discord"] = discord_stub

from django.utils import timezone

from fcdex_3_1.fcdex_ext.pack_assets import pack_art_path
from fcdex_3_1.fcdex_ext.pack_logic import (
    EXCLUSIVE_REWARDS,
    PACK_REWARDS,
    PackRewardLine,
    PackType,
    collection_card_file,
    cooldown_remaining,
    format_pack_open_message,
    roll_pack_stat_bonuses,
)
from fcdex_3_1.models import PackType as ModelPackType


def test_format_pack_open_message_with_stat_rolls():
    lines = [
        PackRewardLine("Alpha", 5, -2, "Shiny"),
        PackRewardLine("Beta", -3, 8, None),
    ]
    text = format_pack_open_message("Daily Pack", 293, lines)
    assert "**+293** coins" in text
    assert "**2** clubball(s)" in text
    assert "**Alpha**" in text and "`+5%` ATK" in text
    assert "**Shiny**" in text


def test_format_pack_open_message_no_balls():
    text = format_pack_open_message("Daily Pack", 500, [])
    assert "no clubballs (dex cache empty)" in text


def test_collection_card_file_missing():
    ball = SimpleNamespace(collection_card=None)
    assert collection_card_file(ball) is None  # type: ignore[arg-type]


def test_collection_card_file_returns_file(tmp_path):
    card_path = tmp_path / "card.png"
    card_path.write_bytes(b"png")
    ball = SimpleNamespace(collection_card=SimpleNamespace(name="card.png", path=str(card_path)))
    file = collection_card_file(ball, index=2)  # type: ignore[arg-type]
    assert file is not None
    assert file.filename == "pack-card-2.png"


def test_cooldown_remaining_none_when_never_claimed():
    assert cooldown_remaining(None, PackType.DAILY) is None


def test_cooldown_exclusive_has_no_player_cooldown():
    last = SimpleNamespace(claimed_at=timezone.now())
    assert cooldown_remaining(last, PackType.EXCLUSIVE) is None


def test_pack_reward_counts():
    assert PACK_REWARDS[PackType.DAILY]["balls"] == 3
    assert PACK_REWARDS[PackType.WEEKLY]["balls"] == 5
    assert EXCLUSIVE_REWARDS["balls"] == 5


def test_exclusive_stat_rolls_are_high():
    atk, hp = roll_pack_stat_bonuses(PackType.EXCLUSIVE)
    assert atk >= 1
    assert hp >= 1


def test_pack_art_files_exist():
    for pack_type in (ModelPackType.DAILY, ModelPackType.WEEKLY, ModelPackType.EXCLUSIVE):
        assert pack_art_path(pack_type).is_file()


def test_cooldown_remaining_after_recent_claim():
    last = SimpleNamespace(claimed_at=timezone.now())
    remaining = cooldown_remaining(last, PackType.DAILY)
    assert remaining is not None
    assert remaining > timedelta(hours=23)
