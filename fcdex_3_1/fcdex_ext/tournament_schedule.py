from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from fcdex_3_0.models import Tournament, TournamentStatus

_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
)


def parse_optional_datetime(raw: str | None) -> datetime | None:
    if not raw or not raw.strip():
        return None

    value = raw.strip()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = None
        for fmt in _DATETIME_FORMATS:
            try:
                parsed = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            raise ValueError(
                "Unrecognized date format. Use `YYYY-MM-DD`, `YYYY-MM-DD HH:MM`, or ISO-8601 (server timezone)."
            )

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def format_datetime(dt: datetime | None) -> str:
    if dt is None:
        return "Not set"
    return f"<t:{int(dt.timestamp())}:F>"


def format_for_input(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M")


def parse_status(raw: str | None) -> str | None:
    if not raw or not raw.strip():
        return None
    value = raw.strip().lower().replace(" ", "_")
    valid = {choice for choice, _ in TournamentStatus.choices}
    if value not in valid:
        raise ValueError(f"Invalid status. Use one of: {', '.join(sorted(valid))}")
    return value


def schedule_summary_lines(tournament: Tournament) -> list[str]:
    lines: list[str] = []
    if tournament.scheduled_start_at:
        lines.append(f"**Scheduled start:** {format_datetime(tournament.scheduled_start_at)}")
    if tournament.scheduled_end_at:
        lines.append(f"**Scheduled end:** {format_datetime(tournament.scheduled_end_at)}")
    if tournament.started_at:
        lines.append(f"**Started (actual):** {format_datetime(tournament.started_at)}")
    if tournament.ended_at:
        lines.append(f"**Ended (actual):** {format_datetime(tournament.ended_at)}")
    return lines


def is_past_scheduled_end(tournament: Tournament) -> bool:
    return bool(tournament.scheduled_end_at and timezone.now() > tournament.scheduled_end_at)


def registration_is_open(tournament: Tournament) -> bool:
    """Open while status is registration and before scheduled end — not closed by scheduled start."""
    if tournament.status != TournamentStatus.REGISTRATION:
        return False
    if is_past_scheduled_end(tournament):
        return False
    return True


def registration_closed_reason(tournament: Tournament) -> str | None:
    if tournament.status != TournamentStatus.REGISTRATION:
        return "Registration is closed — the host has started the tournament."
    if is_past_scheduled_end(tournament):
        return "This tournament has passed its scheduled end date."
    return None


def registration_status_label(tournament: Tournament) -> str:
    if not registration_is_open(tournament):
        return registration_closed_reason(tournament) or "🔴 Registration closed"
    if tournament.scheduled_start_at and timezone.now() >= tournament.scheduled_start_at:
        return (
            "🟢 Registration open · scheduled start passed — use `/tournament start` "
            "or **Start group stage** in `/tournament view` / `/tournament match`"
        )
    return "🟢 Registration open"


def past_end_reason(tournament: Tournament) -> str | None:
    if is_past_scheduled_end(tournament):
        return f"This tournament ended on {format_datetime(tournament.scheduled_end_at)}."
    return None


def start_blocked_reason(tournament: Tournament) -> str | None:
    if reason := past_end_reason(tournament):
        return reason
    if tournament.scheduled_start_at and timezone.now() < tournament.scheduled_start_at:
        return f"This tournament is scheduled to start on {format_datetime(tournament.scheduled_start_at)}."
    return None
