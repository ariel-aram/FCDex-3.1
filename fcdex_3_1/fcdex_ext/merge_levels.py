from __future__ import annotations

from dataclasses import dataclass

MAX_MERGE_LEVEL = 7


@dataclass(frozen=True, slots=True)
class MergeLevelConfig:
    level: int
    input_count: int
    attack_bonus: int
    health_bonus: int
    requires_common_inputs: bool


MERGE_LEVELS: dict[int, MergeLevelConfig] = {
    1: MergeLevelConfig(level=1, input_count=10, attack_bonus=15, health_bonus=15, requires_common_inputs=True),
    2: MergeLevelConfig(level=2, input_count=8, attack_bonus=35, health_bonus=35, requires_common_inputs=False),
    3: MergeLevelConfig(level=3, input_count=6, attack_bonus=60, health_bonus=60, requires_common_inputs=False),
    4: MergeLevelConfig(level=4, input_count=5, attack_bonus=90, health_bonus=90, requires_common_inputs=False),
    5: MergeLevelConfig(level=5, input_count=4, attack_bonus=125, health_bonus=125, requires_common_inputs=False),
    6: MergeLevelConfig(level=6, input_count=3, attack_bonus=165, health_bonus=165, requires_common_inputs=False),
    7: MergeLevelConfig(level=7, input_count=2, attack_bonus=210, health_bonus=210, requires_common_inputs=False),
}

INPUT_COUNT_TO_LEVEL: dict[int, int] = {cfg.input_count: level for level, cfg in MERGE_LEVELS.items()}


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
    inputs = f"{cfg.input_count}× common" if cfg.requires_common_inputs else f"{cfg.input_count}× forge L{level - 1}"
    return f"**L{level}** · {inputs} → `+{cfg.attack_bonus}%` ATK / `+{cfg.health_bonus}%` HP"
