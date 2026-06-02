from __future__ import annotations

import re
import unicodedata

from discord import PartialEmoji

_CUSTOM_EMOJI_RE = re.compile(r"^<(?P<animated>a)?:(?P<name>[a-zA-Z0-9_]+):(?P<id>\d+)>$")

_TYPE_VALUES = frozenset({"battles_won", "merges", "tournament_win", "tournament_participate", "balls_owned", "custom"})

_TYPE_LABELS = {
    "battles_won": "Battles Won",
    "merges": "Merges Completed",
    "tournament_win": "Tournament Wins",
    "tournament_participate": "Tournament Participation",
    "balls_owned": "Clubballs Owned",
    "custom": "Custom (manual)",
}


def normalize_achievement_type(raw: str) -> str:
    return raw.strip().lower().replace("-", "_").replace(" ", "_")


def parse_bool_field(raw: str | None, *, default: bool = False) -> bool:
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "y", "on")


def _is_unicode_emoji(text: str) -> bool:
    """True when *text* is a single Discord-valid Unicode emoji (not plain words)."""
    if not text or len(text) > 32:
        return False
    compact = "".join(ch for ch in text if not ch.isspace())
    if not compact:
        return False
    if compact.isascii() and compact.isalnum():
        return False
    has_emoji = False
    for ch in text:
        code = ord(ch)
        if ch in "\u200d\u20e3\ufe0f":
            continue
        if unicodedata.category(ch) in ("Mn", "Me"):
            continue
        if 0x1F1E6 <= code <= 0x1F1FF:
            has_emoji = True
            continue
        if 0x1F300 <= code <= 0x1FAFF or 0x2600 <= code <= 0x27BF or 0x2300 <= code <= 0x23FF:
            has_emoji = True
            continue
        if unicodedata.category(ch) == "So" and code > 0xFFFF:
            has_emoji = True
            continue
        if "0" <= ch <= "9" and "\u20e3" in text:
            has_emoji = True
            continue
        return False
    return has_emoji


def _select_emoji(raw: str | None) -> str | PartialEmoji | None:
    """Return a value safe for discord.SelectOption(emoji=...), or None to omit."""
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    match = _CUSTOM_EMOJI_RE.match(text)
    if match:
        return PartialEmoji(
            name=match.group("name"), id=int(match.group("id")), animated=match.group("animated") is not None
        )
    if _is_unicode_emoji(text):
        return text
    return None
