from __future__ import annotations

from fcdex_3_1.fcdex_ext.quest_logic import DAILY_QUESTS, QuestSpec, _fallback_specs, _spec_from_row


def test_fallback_specs_match_daily_quests():
    specs = _fallback_specs()
    assert len(specs) == len(DAILY_QUESTS)
    for spec, row in zip(specs, DAILY_QUESTS, strict=True):
        key, label, target, coins, hook = row
        assert spec == QuestSpec(
            quest_key=key, label=label, target=target, reward_coins=coins, hook_key=hook
        )


def test_spec_from_row_fields():
    class _Row:
        quest_key = "battle_play"
        label = "Play a battle"
        target = 2
        reward_coins = 100
        hook_key = "battle_play"

    spec = _spec_from_row(_Row())
    assert spec.quest_key == "battle_play"
    assert spec.target == 2
    assert spec.reward_coins == 100
