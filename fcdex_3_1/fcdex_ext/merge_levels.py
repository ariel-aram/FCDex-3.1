from __future__ import annotations

from fcdex_3_1.fcdex_ext.merge_config import (
    DEFAULT_PERIOD_DAYS,
    DEFAULT_WEEKLY_CAP,
    INPUT_COUNT_TO_LEVEL,
    MAX_MERGE_LEVEL,
    MERGE_LEVELS,
    MergeLevelConfig,
)

__all__ = [
    "DEFAULT_PERIOD_DAYS",
    "DEFAULT_WEEKLY_CAP",
    "INPUT_COUNT_TO_LEVEL",
    "MAX_MERGE_LEVEL",
    "MERGE_LEVELS",
    "MergeLevelConfig",
    "detect_target_level",
    "format_level_table_row",
    "get_merge_level_config",
    "level_requires_ball_country",
    "resolve_merge_level_from_bonuses",
]


def get_merge_level_config(level: int) -> MergeLevelConfig:
    try:
        return MERGE_LEVELS[level]
    except KeyError as exc:
        raise ValueError(f"Invalid merge level: {level}") from exc


def detect_target_level(card_count: int) -> int | None:
    return INPUT_COUNT_TO_LEVEL.get(card_count)


def resolve_merge_level_from_bonuses(attack_bonus: int, health_bonus: int) -> int | None:
    for level in range(MAX_MERGE_LEVEL, 0, -1):
        cfg = MERGE_LEVELS[level]
        if attack_bonus == cfg.attack_bonus and health_bonus == cfg.health_bonus:
            return level
    return None


def format_level_table_row(level: int) -> str:
    cfg = MERGE_LEVELS[level]
    if cfg.requires_common_inputs:
        inputs = f"{cfg.input_count}× common"
    else:
        inputs = f"{cfg.input_count}× forge L{level - 1}"
    ball_note = f" · **{cfg.ball_country}** only" if cfg.ball_country else ""
    return f"**L{level}** · {inputs} → `+{cfg.attack_bonus}%` ATK / `+{cfg.health_bonus}%` HP{ball_note}"


def level_requires_ball_country(level: int) -> str | None:
    cfg = get_merge_level_config(level)
    return cfg.ball_country or None
