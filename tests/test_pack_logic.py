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
    PACK_REWARDS,
    PackType,
    collection_card_file,
    cooldown_remaining,
    format_pack_open_message,
)


def test_format_pack_open_message_single_ball():
    text = format_pack_open_message("Daily Pack", 293, ["Me Pica un Pulmon"])
    assert "**+293** coins" in text
    assert "**1** clubball(s)" in text
    assert "Me Pica un Pulmon" in text


def test_format_pack_open_message_multiple_balls():
    text = format_pack_open_message("Weekly Pack", 1500, ["Alpha", "Beta", "Gamma"])
    assert "**+1,500** coins" in text
    assert "**3** clubball(s)" in text
    assert "**Alpha**" in text and "**Beta**" in text


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


def test_pack_reward_counts_grant_multiple_collectibles():
    assert PACK_REWARDS[PackType.DAILY]["balls"] >= 2
    assert PACK_REWARDS[PackType.WEEKLY]["balls"] >= 2
    assert PACK_REWARDS[PackType.MASCOT]["balls"] >= 2


def test_pack_art_files_exist():
    for pack_type in (PackType.DAILY, PackType.WEEKLY, PackType.MASCOT):
        assert pack_art_path(pack_type).is_file()


def test_cooldown_remaining_after_recent_claim():
    last = SimpleNamespace(claimed_at=timezone.now())
    remaining = cooldown_remaining(last, PackType.DAILY.value)  # type: ignore[arg-type]
    assert remaining is not None
    assert remaining > timedelta(hours=23)
