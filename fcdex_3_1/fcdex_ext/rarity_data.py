"""Dex rarity helpers — live BallsDex Ball data, not manual tier sheets."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bd_models.models import Ball

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


class RarityCategory(StrEnum):
    SPAWNABLE = "spawnable"
    UNSPAWNABLE = "unspawnable"


CATEGORY_LABELS: dict[RarityCategory, str] = {
    RarityCategory.SPAWNABLE: "✅ Spawnable",
    RarityCategory.UNSPAWNABLE: "🚫 Unspawnable",
}


@dataclass(frozen=True, slots=True)
class RarityBallInfo:
    ball_id: int
    name: str
    rarity: float
    enabled: bool
    attack: int
    health: int

    @classmethod
    def from_ball(cls, ball: Ball) -> RarityBallInfo:
        return cls(
            ball_id=ball.pk,
            name=ball.country,
            rarity=ball.rarity,
            enabled=ball.enabled,
            attack=ball.attack,
            health=ball.health,
        )

    @property
    def category(self) -> RarityCategory:
        return RarityCategory.SPAWNABLE if self.enabled else RarityCategory.UNSPAWNABLE

    @property
    def rarity_display(self) -> str:
        return format_rarity_value(self.rarity)


def format_rarity_value(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def normalize_rarity_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return _NORMALIZE_RE.sub(" ", text).strip()
