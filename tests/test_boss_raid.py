from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from fcdex_3_1.fcdex_ext import boss_raid
from fcdex_3_1.fcdex_ext.boss_raid import MAX_ROUNDS, BossParticipant, BossRaid, can_start_round


def _make_raid(**kwargs) -> BossRaid:
    defaults = dict(scope_id=1, channel_id=2, boss_ball_id=10, max_hp=1000, current_hp=1000)
    defaults.update(kwargs)
    return BossRaid(**defaults)


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
    raid = _make_raid(phase="pick", round=1, is_attack_round=True, current_hp=5000)
    raid.participants[42] = BossParticipant(discord_id=42, selected_instance_id=7)

    ball = MagicMock()
    ball.country = "Testland"
    ball.attack = 50
    ball.health = 50

    inst = MagicMock()
    inst.pk = 7
    inst.ball = ball

    mock_qs = MagicMock()
    mock_qs.aget = AsyncMock(return_value=inst)
    mock_objects = MagicMock()
    mock_objects.select_related.return_value = mock_qs

    with patch.object(boss_raid.BallInstance, "objects", mock_objects):
        log = asyncio.run(boss_raid.resolve_round(raid))

    assert raid.current_hp < 5000
    assert raid.participants[42].total_damage > 0
    assert "dealt" in log.lower()
    assert raid.phase == "resolve"


def test_resolve_round_boss_defeated_message():
    raid = _make_raid(phase="pick", round=1, current_hp=50)
    raid.participants[42] = BossParticipant(discord_id=42, selected_instance_id=7)

    ball = MagicMock()
    ball.country = "Testland"
    ball.attack = 50
    ball.health = 50

    inst = MagicMock()
    inst.pk = 7
    inst.ball = ball

    mock_qs = MagicMock()
    mock_qs.aget = AsyncMock(return_value=inst)
    mock_objects = MagicMock()
    mock_objects.select_related.return_value = mock_qs

    with patch.object(boss_raid.BallInstance, "objects", mock_objects):
        log = asyncio.run(boss_raid.resolve_round(raid))

    assert raid.current_hp == 0
    assert "defeated" in log.lower()
    assert raid.phase == "resolve"


def test_resolve_round_reports_missing_picks():
    raid = _make_raid(phase="pick", round=1, is_attack_round=True, current_hp=5000)
    raid.participants[42] = BossParticipant(discord_id=42)

    log = asyncio.run(boss_raid.resolve_round(raid))

    assert raid.current_hp == 5000
    assert "did not lock" in log.lower()
