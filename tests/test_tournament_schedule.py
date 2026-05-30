from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from tests.conftest import TournamentStatus, make_tournament, schedule


def test_registration_open_before_scheduled_start():
    now = timezone.now()
    tournament = make_tournament(scheduled_start_at=now + timedelta(hours=2), scheduled_end_at=now + timedelta(days=1))
    assert schedule.registration_is_open(tournament)
    assert schedule.registration_closed_reason(tournament) is None
    assert schedule.registration_status_label(tournament) == "🟢 Registration open"


def test_registration_stays_open_after_scheduled_start():
    now = timezone.now()
    tournament = make_tournament(scheduled_start_at=now - timedelta(hours=1), scheduled_end_at=now + timedelta(days=1))
    assert schedule.registration_is_open(tournament)
    assert schedule.registration_closed_reason(tournament) is None
    assert "scheduled start passed" in schedule.registration_status_label(tournament)


def test_registration_closed_after_scheduled_end():
    now = timezone.now()
    tournament = make_tournament(scheduled_end_at=now - timedelta(minutes=1))
    assert not schedule.registration_is_open(tournament)
    assert schedule.registration_closed_reason(tournament) == "This tournament has passed its scheduled end date."


def test_registration_closed_after_host_starts():
    tournament = make_tournament(status=TournamentStatus.GROUP_STAGE)
    assert not schedule.registration_is_open(tournament)
    reason = schedule.registration_closed_reason(tournament)
    assert reason == "Registration is closed — the host has started the tournament."


def test_start_blocked_before_scheduled_start():
    now = timezone.now()
    tournament = make_tournament(scheduled_start_at=now + timedelta(hours=3))
    assert schedule.start_blocked_reason(tournament) is not None


def test_start_allowed_after_scheduled_start():
    now = timezone.now()
    tournament = make_tournament(
        status=TournamentStatus.REGISTRATION,
        scheduled_start_at=now - timedelta(minutes=5),
        scheduled_end_at=now + timedelta(days=1),
    )
    assert schedule.start_blocked_reason(tournament) is None
