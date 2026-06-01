from __future__ import annotations

from fcdex_3_1.fcdex_ext import boss_raid
from fcdex_3_1.fcdex_ext.boss_raid import MAX_ROUNDS, BossRaid, can_start_round


def _make_raid(**kwargs) -> BossRaid:
    defaults = dict(guild_id=1, channel_id=2, boss_ball_id=10, max_hp=1000, current_hp=1000)
    defaults.update(kwargs)
    return BossRaid(**defaults)


def test_join_only_during_registration():
    raid = _make_raid(phase="pick")
    ok, _ = boss_raid.join_raid(raid, 99)
    assert not ok
    raid.phase = "join"
    ok, msg = boss_raid.join_raid(raid, 99)
    assert ok
    assert "joined" in msg.lower()
    assert 99 in raid.participants


def test_max_three_rounds():
    raid = _make_raid(phase="join")
    boss_raid.join_raid(raid, 1)
    for expected_round in (1, 2, 3):
        ok, _ = boss_raid.begin_round(raid, attack_phase=True)
        assert ok
        assert raid.round == expected_round
        assert raid.phase == "pick"
        raid.phase = "resolve"
    ok, msg = boss_raid.begin_round(raid, attack_phase=True)
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
