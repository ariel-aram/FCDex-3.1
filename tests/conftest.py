from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import django
from django.conf import settings

ROOT = Path(__file__).resolve().parents[1]


class _TournamentStatus:
    REGISTRATION = "registration"
    GROUP_STAGE = "group_stage"
    SEMIFINALS = "semifinals"
    FINALS = "finals"
    COMPLETED = "completed"


_models_stub = ModuleType("fcdex_3_0.models")
_models_stub.Tournament = object  # type: ignore[misc, assignment]
_models_stub.TournamentStatus = _TournamentStatus
sys.modules.setdefault("fcdex_3_0.models", _models_stub)

if not settings.configured:
    settings.configure(SECRET_KEY="test", USE_TZ=True, TIME_ZONE="UTC", INSTALLED_APPS=[])
    django.setup()

_schedule_path = ROOT / "fcdex_3_0" / "fcdex_ext" / "tournament_schedule.py"
_spec = importlib.util.spec_from_file_location("fcdex_tournament_schedule_test", _schedule_path)
assert _spec and _spec.loader
schedule = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(schedule)

TournamentStatus = _TournamentStatus


def make_tournament(**kwargs) -> SimpleNamespace:
    defaults: dict = {"status": TournamentStatus.REGISTRATION, "scheduled_start_at": None, "scheduled_end_at": None}
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)
