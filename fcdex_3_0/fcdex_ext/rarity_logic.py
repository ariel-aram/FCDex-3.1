from __future__ import annotations

from collections import defaultdict

from bd_models.models import Ball, balls
from fcdex_3_0.fcdex_ext.rarity_data import (
    CATEGORY_LABELS,
    RarityBallInfo,
    RarityCategory,
    format_rarity_value,
    normalize_rarity_name,
)


async def fetch_all_balls() -> list[Ball]:
    if balls:
        return list(balls.values())
    return [ball async for ball in Ball.objects.all()]


def balls_for_category(all_balls: list[Ball], category: RarityCategory) -> list[RarityBallInfo]:
    spawnable = category == RarityCategory.SPAWNABLE
    rows = [RarityBallInfo.from_ball(ball) for ball in all_balls if ball.enabled == spawnable]
    return sorted(rows, key=lambda entry: (entry.rarity, entry.name.casefold()))


def balls_at_rarity(all_balls: list[Ball], rarity: float, *, spawnable_only: bool = True) -> list[RarityBallInfo]:
    target = format_rarity_value(rarity)
    rows: list[RarityBallInfo] = []
    for ball in all_balls:
        if spawnable_only and not ball.enabled:
            continue
        if format_rarity_value(ball.rarity) != target:
            continue
        rows.append(RarityBallInfo.from_ball(ball))
    return sorted(rows, key=lambda entry: entry.name.casefold())


def distinct_rarity_values(all_balls: list[Ball], *, spawnable_only: bool = True) -> list[float]:
    values: set[float] = set()
    for ball in all_balls:
        if spawnable_only and not ball.enabled:
            continue
        values.add(ball.rarity)
    return sorted(values)


def resolve_ball_by_name(all_balls: list[Ball], name: str) -> Ball | None:
    needle = normalize_rarity_name(name)
    if not needle:
        return None
    matches = [ball for ball in all_balls if normalize_rarity_name(ball.country) == needle]
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    enabled = [ball for ball in matches if ball.enabled]
    return enabled[0] if enabled else matches[0]


def format_ball_line(ball: Ball) -> str:
    info = RarityBallInfo.from_ball(ball)
    status = "✅ spawnable" if info.enabled else "🚫 not spawnable"
    category = CATEGORY_LABELS[info.category]
    return (
        f"**r:{info.rarity_display}** · {info.name}\n"
        f"-# {category} · {status} · `{info.attack}` ATK · `{info.health}` HP"
    )


def build_spawnable_overview(all_balls: list[Ball], *, values_per_page: int = 8) -> list[str]:
    pages: list[str] = []
    rarity_values = distinct_rarity_values(all_balls, spawnable_only=True)
    for start in range(0, len(rarity_values), values_per_page):
        chunk = rarity_values[start : start + values_per_page]
        sections: list[str] = []
        for value in chunk:
            rows = balls_at_rarity(all_balls, value, spawnable_only=True)
            names = ", ".join(row.name for row in rows)
            display = format_rarity_value(value)
            sections.append(f"**r:{display}** ({len(rows)}) · {names}")
        pages.append("### ✅ Spawnable clubballs\n" + "\n\n".join(sections))
    return pages or ["### ✅ Spawnable clubballs\n*No spawnable clubballs in the dex.*"]


def build_category_overview(all_balls: list[Ball], category: RarityCategory) -> str:
    rows = balls_for_category(all_balls, category)
    if not rows:
        return f"### {CATEGORY_LABELS[category]}\n*No clubballs in this group.*"
    lines: list[str] = []
    current_rarity: str | None = None
    for row in rows:
        rarity = row.rarity_display
        if rarity != current_rarity:
            current_rarity = rarity
            lines.append(f"\n**r:{rarity}**")
        lines.append(f"• {row.name} · `{row.attack}` ATK · `{row.health}` HP")
    return f"### {CATEGORY_LABELS[category]}\n" + "\n".join(lines).strip()


def count_catalog(all_balls: list[Ball]) -> dict[str, int]:
    return {
        RarityCategory.SPAWNABLE.value: len(balls_for_category(all_balls, RarityCategory.SPAWNABLE)),
        RarityCategory.UNSPAWNABLE.value: len(balls_for_category(all_balls, RarityCategory.UNSPAWNABLE)),
    }


def rarity_distribution(all_balls: list[Ball]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for ball in all_balls:
        if not ball.enabled:
            continue
        counts[format_rarity_value(ball.rarity)] += 1
    return dict(sorted(counts.items(), key=lambda item: float(item[0])))
