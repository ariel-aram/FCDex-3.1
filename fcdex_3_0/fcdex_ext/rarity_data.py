"""Official FCDex rarity tables (March–May 2026).

Unlike generic dex extras that derive tiers from spawn weights, FCDex uses fixed
official tier lists per category. Lower tier = rarer.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


class RarityCategory(StrEnum):
    OBTAINABLE = "obtainable"
    ICON = "icon"
    GOAT_ICON = "goat_icon"
    PRIME = "prime"
    EVENT = "event"
    EXCLUSIVE = "exclusive"
    EID = "eid"
    UNOBTAINABLE = "unobtainable"


CATEGORY_LABELS: dict[RarityCategory, str] = {
    RarityCategory.OBTAINABLE: "⚽ Obtainable",
    RarityCategory.ICON: "🌟 Icon",
    RarityCategory.GOAT_ICON: "👑 GOAT · Icon",
    RarityCategory.PRIME: "🏆 Prime clubs",
    RarityCategory.EVENT: "🎉 Event customs",
    RarityCategory.EXCLUSIVE: "💎 Exclusive",
    RarityCategory.EID: "🌙 Eid customs",
    RarityCategory.UNOBTAINABLE: "🚫 Unobtainable",
}


@dataclass(frozen=True, slots=True)
class RarityEntry:
    name: str
    tier: int
    category: RarityCategory
    weight: float | None = None
    obtainable: bool = True

    @property
    def weight_display(self) -> str:
        if self.weight is not None:
            return f"{self.weight:.4f}".rstrip("0").rstrip(".")
        return "—"


def _entries(
    category: RarityCategory, rows: list[tuple[int, str, float | None]], *, obtainable: bool
) -> list[RarityEntry]:
    return [
        RarityEntry(name=name, tier=tier, category=category, weight=weight, obtainable=obtainable)
        for tier, name, weight in rows
    ]


# fmt: off
_OBTAINABLE_ROWS: list[tuple[int, str, float | None]] = [
    (1, "Team Shaolin", None), (1, "Team Hurakan", None),
    (2, "Manchester United (2008)", None), (2, "Barcelona (2009)", None), (2, "Real Madrid (2017)", None),
    (5, "AC Milan (2003)", None),
    (6, "Chelsea (2012)", None),
    (6, "Inter Milan (2010)", None),
    (6, "Arsenal (2003)", None),
    (6, "Juventus (2017)", None),
    (10, "Santos (1963/2012)", None), (10, "Paris Saint Germain (2025)", None),
    (10, "Manchester City (2023)", None), (10, "Bayern Munich (2020)", None),
    (14, "Napoli (1988/2023)", None),
    (15, "Legendary Brazil", None), (15, "Leicester City (2016)", None), (15, "MSN Barcelona", None),
    (15, "Los Galácticos", None),
    (19, "Ferguson's United", None),
    (20, "Invincible Arsenal", None), (20, "Rossoneri", None),
    (22, "Mx7di", None), (22, "Shadow", None), (22, "AYAN", None),
    (25, "EL Bicho", None), (25, "Klopp's Liverpool", None),
    (27, "2020's Bayern Munich", None),
    (28, "AJAY", None), (28, "Farmer", None), (28, "Messi10", None), (28, "Vegito", None), (28, "Rampage", None),
    (33, "AFC Richmond", None), (33, "Qatar Football association", None),
    (35, "Real Madrid CF", None), (35, "FC Barcelona", None), (35, "Germany National Football Team", None),
    (35, "Brazil National Football Team", None), (35, "France National Football Team", None),
    (35, "England National Football Team", None), (35, "Argentina National Football Team", None),
    (42, "Brighton FC", None), (42, "San Marino National Football Team", None),
    (44, "Paris Saint-Germain FC", None), (44, "Manchester City FC", None), (44, "Liverpool FC", None),
    (47, "Arsenal FC", None), (47, "FC Bayern Munich", None),
    (49, "Spain National Football Team", None),
    (50, "Netherlands National Football Team", None), (50, "Portugal National Football Team", None),
    (52, "Belgium National Football Team", None),
    (53, "Chelsea FC", None),
    (54, "Japan National Football Team", None),
    (55, "Tottenham Hotspur FC", None), (55, "AC Milan", None),
    (57, "Juventus FC", None), (57, "AFC Ajax", None),
    (59, "Manchester United FC", None),
    (60, "Borussia Dortmund", None),
    (61, "Atletico Madrid", None), (61, "Sevilla FC", None),
    (63, "Newcastle United FC", None), (63, "AS Roma", None),
    (65, "SSC Napoli", None),
    (66, "Inter Milan", None),
    (67, "Al Nassr FC", None),
    (68, "Al Hilal SFC", None),
    (69, "SL Benfica", None),
    (70, "Real Sociedad", None),
    (70, "FK Austria Wien", None),
    (70, "SK Rapid Wien", None),
    (70, "Rayo Vallecano", None),
    (73, "Olympique Lyonnais", None),
    (74, "Rangers FC", None), (74, "Everton FC", None),
    (76, "Como 1907", None),
    (77, "Wrexham AFC", None),
    (78, "Inter Miami CF", None),
    (79, "New York City FC", None), (79, "FC Dallas", None), (79, "LA Galaxy", None),
    (82, "India National Football Team", None),
    (83, "APOEL FC", None), (83, "Wolverhampton Wanderers FC", None),
    (85, "Motherwell FC", None),
    (86, "Oldham Athletic AFC", None), (86, "Sport Club Corinthians Paulista", None),
    (88, "Fortuna Düsseldorf", None), (88, "Hannover 96", None), (88, "FC Köln", None),
    (91, "Wiener Sport Club", None), (91, "Sheffield FC", None), (91, "Coventry City FC", None),
    (91, "FC Saarbrücken", None), (91, "FC Hansa Rostock", None), (91, "Liechtenstein National Football Team", None),
    (91, "Crewe Alexandra FC", None), (91, "Southampton FC", None), (91, "Derry City FC", None),
]

_ICON_ROWS: list[tuple[int, str, float | None]] = [
    (1, "Pele", 0.001), (2, "Diego Maradona", 0.005), (2, "Franz Beckenbauer", 0.005),
    (3, "Ronaldo Nazario", 0.006), (3, "Zinedine Zidane", 0.006), (3, "Ronaldinho", 0.006),
    (3, "Johan Cruyff", 0.006), (3, "Paolo Maldini", 0.006), (3, "Michel Platini", 0.006),
    (3, "Alfredo di stefano", 0.006), (3, "Gianluigi Buffon", 0.006), (3, "Ferenc Puskas", 0.006),
    (4, "Fabio Cannavaro", 0.007), (4, "Ricardo Kaka", 0.007),
]

_GOAT_ROWS: list[tuple[int, str, float | None]] = [
    (1, "Lionel Messi", None), (1, "Cristiano Ronaldo", None),
]

_PRIME_ROWS: list[tuple[int, str, float | None]] = [
    (2, "Real Madrid (2017)", None), (2, "Barcelona (2017)", None), (2, "Manchester United (2008)", None),
    (3, "AC Milan (2003)", None),
    (4, "Arsenal (2003)", None),
    (4, "Inter Milan (2010)", None),
    (4, "Juventus (2017)", None),
    (4, "Chelsea (2012)", None),
    (5, "Paris Saint Germain (2025)", None), (5, "Bayern Munich (2020)", None), (5, "Santos (1963/2012)", None),
    (5, "Manchester City (2023)", None), (5, "Liverpool (2019)", None), (5, "Napoli (1988/2023)", None),
    (7, "Leicester City (2016)", None),
]

_EVENT_ROWS: list[tuple[int, str, float | None]] = [
    (8, "Mx7Di", None), (9, "Shadow", None), (9, "Ayan", None), (9, "Mx7Di & Levente & Stellanor", None),
    (12, "Vegito", None), (12, "Earthiopia", None), (12, "Messi10", None), (12, "Farmer", None),
    (12, "Ajay", None), (12, "Anti", None), (12, "Shazaam & Vegito", None), (12, "Burl", None), (12, "Rampage", None),
]

_EID_ROWS: list[tuple[int, str, float | None]] = [
    (8, "Ash & Mx7Di", 0.05), (8, "Nash X", 0.05), (8, "Levente", 0.05), (8, "Evixcinity", 0.05),
]

_EXCLUSIVE_ROWS: list[tuple[int, str, float | None]] = [
    (1, "Michael Jackson", None), (2, "Kanye West", None), (7, "Khabib", None), (7, "IShowSpeed", None),
    (9, "Karim Benzema (Eid)", None),
]

_UNOBTAINABLE_ROWS: list[tuple[int, str, float | None]] = [
    (1, "Michael Jackson", 0.001), (1, "Reichking", 0.001),
    (2, "Kanye West", 0.005),
    (7, "Khabib", 0.01),
    (8, "Karim Benzema (Eid)", 0.05), (8, "Levente (EidCustom)", 0.05),
    (8, "Ash & Mx7Di (EidCustom)", 0.05), (8, "Nash X (EidCustom)", 0.05), (8, "Evixcinity (EidCustom)", 0.05),
]
# fmt: on

FCDEX_RARITY_ENTRIES: list[RarityEntry] = [
    *_entries(RarityCategory.OBTAINABLE, _OBTAINABLE_ROWS, obtainable=True),
    *_entries(RarityCategory.ICON, _ICON_ROWS, obtainable=False),
    *_entries(RarityCategory.GOAT_ICON, _GOAT_ROWS, obtainable=False),
    *_entries(RarityCategory.PRIME, _PRIME_ROWS, obtainable=False),
    *_entries(RarityCategory.EVENT, _EVENT_ROWS, obtainable=False),
    *_entries(RarityCategory.EID, _EID_ROWS, obtainable=False),
    *_entries(RarityCategory.EXCLUSIVE, _EXCLUSIVE_ROWS, obtainable=False),
    *_entries(RarityCategory.UNOBTAINABLE, _UNOBTAINABLE_ROWS, obtainable=False),
]

# Lookup priority when a name appears in multiple lists (most specific wins).
_CATEGORY_PRIORITY: tuple[RarityCategory, ...] = (
    RarityCategory.GOAT_ICON,
    RarityCategory.ICON,
    RarityCategory.EXCLUSIVE,
    RarityCategory.EID,
    RarityCategory.EVENT,
    RarityCategory.PRIME,
    RarityCategory.UNOBTAINABLE,
    RarityCategory.OBTAINABLE,
)


def normalize_rarity_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return _NORMALIZE_RE.sub(" ", text).strip()


def _build_lookup() -> dict[str, list[RarityEntry]]:
    table: dict[str, list[RarityEntry]] = defaultdict(list)
    for entry in FCDEX_RARITY_ENTRIES:
        table[normalize_rarity_name(entry.name)].append(entry)
    return table


_LOOKUP = _build_lookup()


def resolve_entry(name: str) -> RarityEntry | None:
    matches = _LOOKUP.get(normalize_rarity_name(name))
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    priority = {category: index for index, category in enumerate(_CATEGORY_PRIORITY)}
    return min(matches, key=lambda entry: priority.get(entry.category, 99))


def entries_for_category(category: RarityCategory) -> list[RarityEntry]:
    return [entry for entry in FCDEX_RARITY_ENTRIES if entry.category == category]


def entries_for_tier(tier: int, *, category: RarityCategory = RarityCategory.OBTAINABLE) -> list[RarityEntry]:
    return [entry for entry in entries_for_category(category) if entry.tier == tier]


def obtainable_tiers() -> list[int]:
    tiers = {entry.tier for entry in entries_for_category(RarityCategory.OBTAINABLE)}
    return sorted(tiers)
