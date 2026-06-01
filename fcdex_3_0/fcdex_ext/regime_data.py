from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegimeEntry:
    key: str
    label: str
    description: str
    ball_names: tuple[str, ...]


# Official regime groupings — match by clubball country name (case-insensitive).
REGIMES: tuple[RegimeEntry, ...] = (
    RegimeEntry(
        "ucl",
        "UEFA · Champions League",
        "European elite clubs",
        ("Paris Saint-Germain", "Real Madrid", "Bayern Munich", "Manchester City"),
    ),
    RegimeEntry(
        "premier",
        "Premier League",
        "English top flight",
        ("Arsenal", "Chelsea", "Liverpool", "Manchester United", "Manchester City", "Tottenham Hotspur"),
    ),
    RegimeEntry("la_liga", "La Liga", "Spanish top flight", ("Barcelona", "Real Madrid", "Atlético Madrid")),
    RegimeEntry("serie_a", "Serie A", "Italian top flight", ("AC Milan", "Inter Milan", "Juventus", "Napoli", "Roma")),
    RegimeEntry(
        "national",
        "National teams",
        "International sides",
        ("France", "Brazil", "Argentina", "Germany", "England", "Spain", "Portugal"),
    ),
)


def regime_by_key(key: str) -> RegimeEntry | None:
    lowered = key.strip().lower().replace(" ", "_")
    for entry in REGIMES:
        if entry.key == lowered or entry.label.lower() == key.strip().lower():
            return entry
    return None
