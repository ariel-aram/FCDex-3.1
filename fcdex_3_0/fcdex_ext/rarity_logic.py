from __future__ import annotations

from bd_models.models import Ball, balls
from fcdex_3_0.fcdex_ext.rarity_data import (
    CATEGORY_LABELS,
    RarityCategory,
    RarityEntry,
    entries_for_category,
    entries_for_tier,
    obtainable_tiers,
    resolve_entry,
)


def resolve_ball(ball: Ball) -> RarityEntry | None:
    return resolve_entry(ball.country)


def format_entry_line(entry: RarityEntry, *, ball: Ball | None = None) -> str:
    category = CATEGORY_LABELS[entry.category]
    weight = f" · `{entry.weight_display}`" if entry.weight is not None else ""
    status = "✅ spawn" if entry.obtainable else "🚫 not spawnable"
    dex = ""
    if ball is not None:
        dex = f" · dex `{ball.rarity}`" if ball.rarity else ""
    return f"**T{entry.tier}** · {entry.name}{weight}\n-# {category} · {status}{dex}"


def build_obtainable_overview(*, tiers_per_page: int = 8) -> list[str]:
    pages: list[str] = []
    tiers = obtainable_tiers()
    for start in range(0, len(tiers), tiers_per_page):
        chunk = tiers[start : start + tiers_per_page]
        sections: list[str] = []
        for tier in chunk:
            rows = entries_for_tier(tier)
            names = ", ".join(row.name for row in rows)
            sections.append(f"**T{tier}** ({len(rows)}) · {names}")
        pages.append("### ⚽ Official obtainable list\n" + "\n\n".join(sections))
    return pages or ["### ⚽ Official obtainable list\n*No entries configured.*"]


def build_category_overview(category: RarityCategory) -> str:
    rows = sorted(entries_for_category(category), key=lambda entry: (entry.tier, entry.name))
    if not rows:
        return f"### {CATEGORY_LABELS[category]}\n*No entries.*"
    lines: list[str] = []
    current_tier: int | None = None
    for row in rows:
        if row.tier != current_tier:
            current_tier = row.tier
            lines.append(f"\n**Tier {current_tier}**")
        weight = f" · `{row.weight_display}`" if row.weight is not None else ""
        lines.append(f"• {row.name}{weight}")
    return f"### {CATEGORY_LABELS[category]}\n" + "\n".join(lines).strip()


def count_catalog() -> dict[str, int]:
    counts: dict[str, int] = {}
    for category in RarityCategory:
        counts[category.value] = len(entries_for_category(category))
    return counts


def enabled_balls_missing_from_sheet() -> list[str]:
    missing: list[str] = []
    for ball in balls.values():
        if ball.enabled and resolve_ball(ball) is None:
            missing.append(ball.country)
    return sorted(missing)
