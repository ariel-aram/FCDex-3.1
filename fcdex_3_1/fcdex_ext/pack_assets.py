from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from fcdex_3_1.models import PackType

_PACK_ART: dict[str, str] = {
    PackType.DAILY: "daily-pack.png",
    PackType.WEEKLY: "weekly-pack.png",
    PackType.MASCOT: "exclusive-pack.png",
}


def pack_art_path(pack_type: str) -> Path:
    filename = _PACK_ART.get(pack_type, "daily-pack.png")
    return Path(str(files("fcdex_3_1").joinpath(f"media/{filename}")))
