from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from fcdex_3_1.fcdex_ext import boss_raid
from fcdex_3_1.fcdex_ext.boss_raid import (
    MAX_ROUNDS,
    BossParticipant,
    BossRaid,
    can_start_round,
    format_public_raid_results,
    pick_raid_winner_id,
    top_damage_tie_ids,
)


def _make_raid(**kwargs) -> BossRaid:
    defaults = dict(scope_id=1, channel_id=2, boss_ball_id=10, max_hp=1000, current_hp=1000)
    defaults.update(kwargs)
    return BossRaid(**defaults)


def _make_card(*, pk: int = 7, attack: int = 50, health: int = 50):
    ball = MagicMock()
    ball.country = "Testland"
    ball.attack = attack
    ball.health = health
    inst = MagicMock()
    inst.pk = pk
    inst.ball = ball
    return inst, ball


def _make_boss_ball(*, attack: int = 10, health: int = 10):
    boss = MagicMock()
    boss.attack = attack
    boss.health = health
    return boss


def _resolve_with_mocks(raid: BossRaid, *, inst, boss_ball):
    inst_qs = MagicMock()
    inst_qs.aget = AsyncMock(return_value=inst)
    inst_objects = MagicMock()
    inst_objects.select_related.return_value = inst_qs
    ball_objects = MagicMock()
    ball_objects.aget = AsyncMock(return_value=boss_ball)
    with (
        patch.object(boss_raid.BallInstance, "objects", inst_objects),
        patch.object(boss_raid.Ball, "objects", ball_objects),
    ):
        return asyncio.run(boss_raid.resolve_round(raid))


def test_join_during_join_and_pick_not_after_resolve():
    raid = _make_raid(phase="pick")
    ok, _ = boss_raid.join_raid(raid, 100)
    assert ok
    raid.phase = "resolve"
    ok, _ = boss_raid.join_raid(raid, 101)
    assert not ok
    raid = _make_raid(phase="join")
    ok, msg = boss_raid.join_raid(raid, 99)
    assert ok
    assert "joined" in msg.lower()
    assert 99 in raid.participants


def test_max_three_rounds():
    raid = _make_raid(phase="join")
    boss_raid.join_raid(raid, 1)
    for expected_round in (1, 2, 3):
        ok, _ = boss_raid.begin_round(raid)
        assert ok
        assert raid.round == expected_round
        assert raid.phase == "pick"
        raid.phase = "resolve"
    ok, msg = boss_raid.begin_round(raid)
    assert not ok
    assert "3 rounds" in msg.lower() or "conclude" in msg.lower()
    assert raid.round == MAX_ROUNDS


def test_cannot_start_round_during_pick():
    raid = _make_raid(phase="pick", round=1)
    ok, msg = can_start_round(raid)
    assert not ok
    assert "resolve" in msg.lower()


def test_can_start_after_resolve_not_after_three():
    raid = _make_raid(phase="resolve", round=2)
    ok, _ = can_start_round(raid)
    assert ok
    raid.round = MAX_ROUNDS
    ok, msg = can_start_round(raid)
    assert not ok
    assert "conclude" in msg.lower()


def test_reward_ball_defaults_to_boss():
    raid = _make_raid(boss_ball_id=7)
    assert raid.reward_ball_id_effective == 7
    raid.reward_ball_id = 42
    assert raid.reward_ball_id_effective == 42


def test_resolve_round_deals_damage_on_attack_round():
    raid = _make_raid(phase="pick", round=1, current_hp=5000)
    raid.participants[42] = BossParticipant(discord_id=42, selected_instance_id=7)
    inst, _ = _make_card()
    log = _resolve_with_mocks(raid, inst=inst, boss_ball=_make_boss_ball())

    assert raid.current_hp < 5000
    assert raid.participants[42].total_damage > 0
    assert "dealt" in log.lower()
    assert "boss hit" in log.lower() or "boss countered" in log.lower()
    assert raid.phase == "resolve"


def test_resolve_round_boss_defeated_message():
    raid = _make_raid(phase="pick", round=1, current_hp=50)
    raid.participants[42] = BossParticipant(discord_id=42, selected_instance_id=7)
    inst, _ = _make_card()
    log = _resolve_with_mocks(raid, inst=inst, boss_ball=_make_boss_ball())

    assert raid.current_hp == 0
    assert "defeated" in log.lower()
    assert raid.phase == "resolve"


def test_boss_counter_knocks_out_weak_card():
    raid = _make_raid(phase="pick", round=1, current_hp=5000)
    raid.participants[42] = BossParticipant(discord_id=42, selected_instance_id=7)
    inst, _ = _make_card(attack=5, health=5)

    with patch.object(boss_raid, "_boss_strike", return_value=999):
        log = _resolve_with_mocks(raid, inst=inst, boss_ball=_make_boss_ball(attack=500, health=500))

    assert raid.participants[42].disqualified
    assert "knocked out" in log.lower()


def test_boss_counter_survives_strong_card():
    raid = _make_raid(phase="pick", round=1, current_hp=5000)
    raid.participants[42] = BossParticipant(discord_id=42, selected_instance_id=7)
    inst, _ = _make_card(attack=200, health=200)

    with patch.object(boss_raid, "_boss_strike", return_value=50):
        log = _resolve_with_mocks(raid, inst=inst, boss_ball=_make_boss_ball())

    assert not raid.participants[42].disqualified
    assert "survives" in log.lower()
    assert raid.participants[42].round_boss_damage == 50


def test_pick_winner_skips_disqualified_top_damager():
    raid = _make_raid()
    raid.participants[1] = BossParticipant(discord_id=1, total_damage=500, disqualified=True)
    raid.participants[2] = BossParticipant(discord_id=2, total_damage=100)
    assert pick_raid_winner_id(raid) == 2


def test_pick_winner_none_when_no_damage():
    raid = _make_raid()
    raid.participants[1] = BossParticipant(discord_id=1, total_damage=0)
    assert pick_raid_winner_id(raid) is None


def test_top_damage_tie_ids():
    raid = _make_raid()
    raid.participants[1] = BossParticipant(discord_id=1, total_damage=100)
    raid.participants[2] = BossParticipant(discord_id=2, total_damage=100)
    assert top_damage_tie_ids(raid) == [1, 2]


def test_format_public_raid_results_defeated_and_reward():
    raid = _make_raid(current_hp=0)
    raid.participants[42] = BossParticipant(discord_id=42, total_damage=999)
    text = format_public_raid_results(
        raid, boss_country="Test Boss", winner_id=42, reward_line="🎁 <@42> received **Prize** (Boss)!"
    )
    assert "Test Boss" in text
    assert "defeated" in text.lower()
    assert "<@42>" in text
    assert "Prize" in text


def test_format_public_raid_results_no_participants():
    raid = _make_raid(current_hp=500)
    text = format_public_raid_results(raid, boss_country="Lonely Boss", winner_id=None, reward_line=None)
    assert "survived" in text.lower()
    assert "no one joined" in text.lower()


def test_resolve_round_reports_missing_picks():
    raid = _make_raid(phase="pick", round=1, current_hp=5000)
    raid.participants[42] = BossParticipant(discord_id=42)
    boss_ball = _make_boss_ball()
    ball_objects = MagicMock()
    ball_objects.aget = AsyncMock(return_value=boss_ball)
    with patch.object(boss_raid.Ball, "objects", ball_objects):
        log = asyncio.run(boss_raid.resolve_round(raid))

    assert raid.current_hp == 5000
    assert "did not lock" in log.lower()
