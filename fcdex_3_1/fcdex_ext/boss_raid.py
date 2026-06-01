from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Literal

from bd_models.models import Ball, BallInstance, Player, Special
from fcdex_3_1.fcdex_ext.bd_helpers import instance_attack, instance_health

log = logging.getLogger("fcdex_3_1.boss.raid")

BossPhase = Literal["join", "pick", "resolve", "ended"]
MAX_ROUNDS = 3
DAMAGE_RNG = (200, 2_000)
BOSS_SPECIAL_NAME = "Boss"


@dataclass
class BossParticipant:
    discord_id: int
    total_damage: int = 0
    round_damage: int = 0
    selected_instance_id: int | None = None
    disqualified: bool = False


@dataclass
class BossRaid:
    guild_id: int  # scope key: guild id or DM channel id
    channel_id: int
    boss_ball_id: int
    max_hp: int
    current_hp: int
    reward_ball_id: int | None = None
    reward_server_id: int | None = None  # BallsDex server_id on grants; None in DMs
    phase: BossPhase = "join"
    round: int = 0
    is_attack_round: bool = True
    participants: dict[int, BossParticipant] = field(default_factory=dict)
    used_instance_ids: set[int] = field(default_factory=set)
    announcement_message_id: int | None = None
    last_round_log: str = ""

    @property
    def alive_participant_ids(self) -> list[int]:
        return [uid for uid, p in self.participants.items() if not p.disqualified]

    @property
    def reward_ball_id_effective(self) -> int:
        return self.reward_ball_id if self.reward_ball_id is not None else self.boss_ball_id

    @property
    def rounds_complete(self) -> bool:
        return self.round >= MAX_ROUNDS and self.phase == "resolve"


def _raids() -> dict[int, BossRaid]:
    from fcdex_3_1.fcdex_ext import boss_raid as mod

    return mod._ACTIVE_RAIDS


_ACTIVE_RAIDS: dict[int, BossRaid] = {}


def raid_scope_id(_guild_id: int | None, channel_id: int) -> int:
    """Raids are scoped to the channel (guild channel or DM) — always reliable."""
    return channel_id


def get_raid(scope_id: int | None) -> BossRaid | None:
    if scope_id is None:
        return None
    return _ACTIVE_RAIDS.get(scope_id)


async def ensure_boss_special() -> Special | None:
    return await Special.objects.filter(name__iexact=BOSS_SPECIAL_NAME).afirst()


def start_raid(
    *,
    scope_id: int,
    channel_id: int,
    boss_ball: Ball,
    hp: int,
    reward_ball: Ball | None = None,
    reward_server_id: int | None = None,
) -> BossRaid:
    if scope_id in _ACTIVE_RAIDS:
        raise ValueError("A boss raid is already active here.")
    raid = BossRaid(
        guild_id=scope_id,
        channel_id=channel_id,
        boss_ball_id=boss_ball.pk,
        max_hp=hp,
        current_hp=hp,
        reward_ball_id=reward_ball.pk if reward_ball is not None else None,
        reward_server_id=reward_server_id,
    )
    _ACTIVE_RAIDS[scope_id] = raid
    return raid


def end_raid(scope_id: int) -> BossRaid | None:
    return _ACTIVE_RAIDS.pop(scope_id, None)


def join_raid(raid: BossRaid, user_id: int) -> tuple[bool, str]:
    if raid.phase != "join":
        return False, "Registration is closed — wait for the next raid."
    if user_id in raid.participants:
        return False, "You already joined this raid."
    raid.participants[user_id] = BossParticipant(discord_id=user_id)
    return True, "You joined the boss raid!"


def can_start_round(raid: BossRaid) -> tuple[bool, str]:
    if raid.phase == "ended":
        return False, "This raid has ended."
    if raid.phase == "pick":
        return False, "Resolve the current round before starting another."
    if raid.rounds_complete:
        return False, "All 3 rounds complete — use **Conclude**."
    if raid.phase == "resolve" and raid.round >= MAX_ROUNDS:
        return False, "All 3 rounds complete — use **Conclude**."
    if raid.phase == "join" and raid.round == 0:
        return True, ""
    if raid.phase == "resolve" and raid.round < MAX_ROUNDS:
        return True, ""
    return False, "Cannot start a round right now."


def begin_round(raid: BossRaid, *, attack_phase: bool) -> tuple[bool, str]:
    ok, message = can_start_round(raid)
    if not ok:
        return False, message
    if raid.round >= MAX_ROUNDS:
        return False, "All 3 rounds complete — use **Conclude**."
    raid.round += 1
    raid.is_attack_round = attack_phase
    raid.phase = "pick"
    for participant in raid.participants.values():
        participant.round_damage = 0
        participant.selected_instance_id = None
    phase = "attack" if attack_phase else "defend"
    return (
        True,
        f"Round **{raid.round}/{MAX_ROUNDS}** — **{phase}** phase. Players: pick a clubball in `/fcdex boss`.",
    )


async def submit_card(raid: BossRaid, user_id: int, instance: BallInstance) -> tuple[bool, str]:
    if raid.phase != "pick":
        return False, "You cannot select a clubball right now."
    participant = raid.participants.get(user_id)
    if participant is None or participant.disqualified:
        return False, "You are not in this raid (or were disqualified). Join during registration first."
    if instance.pk in raid.used_instance_ids:
        return False, "That clubball was already used in this raid."
    if participant.selected_instance_id is not None:
        return False, "You already locked a clubball this round."
    participant.selected_instance_id = instance.pk
    return True, f"Locked **#{instance.pk}** for round **{raid.round}/{MAX_ROUNDS}**."


async def resolve_round(raid: BossRaid) -> str:
    if raid.phase != "pick":
        return "Nothing to resolve — start a round first."
    lines: list[str] = [f"### Round **{raid.round}/{MAX_ROUNDS}** results"]
    if raid.is_attack_round:
        total = 0
        for participant in raid.participants.values():
            if participant.disqualified or participant.selected_instance_id is None:
                continue
            try:
                inst = await BallInstance.objects.select_related("ball").aget(pk=participant.selected_instance_id)
            except BallInstance.DoesNotExist:
                continue
            ball = inst.ball
            power = instance_attack(inst, ball) + instance_health(inst, ball)
            dmg = max(1, int(power * random.uniform(0.85, 1.15)))
            participant.round_damage = dmg
            participant.total_damage += dmg
            total += dmg
            raid.used_instance_ids.add(inst.pk)
            lines.append(f"<@{participant.discord_id}> dealt **{dmg:,}** with {ball.country}")
        raid.current_hp = max(0, raid.current_hp - total)
        lines.append(f"\nBoss HP: **{raid.current_hp:,}** / **{raid.max_hp:,}**")
    else:
        boss_hit = random.randint(*DAMAGE_RNG)
        lines.append(f"Boss retaliates for **{boss_hit:,}** (flavour — raid is damage-race).")
    raid.phase = "resolve"
    if raid.rounds_complete:
        lines.append("\n-# All **3** rounds are done — admins: **Conclude** to award the winner.")
    raid.last_round_log = "\n".join(lines)
    return raid.last_round_log


def standings(raid: BossRaid) -> str:
    rows = sorted(raid.participants.values(), key=lambda p: p.total_damage, reverse=True)
    if not rows:
        return "*No participants yet — players must join during registration.*"
    return "\n".join(
        f"{'🚫' if p.disqualified else '▸'} <@{p.discord_id}> — **{p.total_damage:,}** total damage" for p in rows
    )


async def conclude_raid(raid: BossRaid, *, grant_reward: bool) -> tuple[str, int | None]:
    raid.phase = "ended"
    winner_id: int | None = None
    if raid.participants:
        winner = max(raid.participants.values(), key=lambda p: p.total_damage)
        if winner.total_damage > 0 and not winner.disqualified:
            winner_id = winner.discord_id

    lines = [f"### Raid concluded\n{standings(raid)}"]
    if winner_id and grant_reward:
        special = await ensure_boss_special()
        player = await Player.objects.filter(discord_id=winner_id).afirst()
        reward_ball = await Ball.objects.aget(pk=raid.reward_ball_id_effective)
        if player and special:
            await BallInstance.objects.acreate(
                ball=reward_ball,
                player=player,
                special=special,
                attack_bonus=0,
                health_bonus=0,
                server_id=raid.reward_server_id,
            )
            lines.append(f"\n🏆 <@{winner_id}> received **{reward_ball.country}** ({special.name})!")
        elif player:
            await BallInstance.objects.acreate(
                ball=reward_ball,
                player=player,
                attack_bonus=0,
                health_bonus=0,
                server_id=raid.reward_server_id,
            )
            lines.append(f"\n🏆 <@{winner_id}> received **{reward_ball.country}**!")
        else:
            lines.append(f"\n🏆 Top damage: <@{winner_id}> (no player record).")
    elif winner_id:
        lines.append(f"\n🏆 Top damage: <@{winner_id}> (no reward).")
    else:
        lines.append("\nNo winner recorded.")

    end_raid(raid.guild_id)
    return "\n".join(lines), winner_id


def disqualify(raid: BossRaid, user_id: int) -> tuple[bool, str]:
    participant = raid.participants.get(user_id)
    if participant is None:
        return False, "That user is not in the raid."
    participant.disqualified = True
    return True, f"<@{user_id}> was disqualified."
