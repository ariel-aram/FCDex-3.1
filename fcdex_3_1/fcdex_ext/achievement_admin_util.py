from __future__ import annotations

_TYPE_VALUES = frozenset(
    {
        "battles_won",
        "merges",
        "tournament_win",
        "tournament_participate",
        "balls_owned",
        "custom",
    }
)

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
