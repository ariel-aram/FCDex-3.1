from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import django
from django.conf import settings

ROOT = Path(__file__).resolve().parents[1]

if not settings.configured:
    settings.configure(SECRET_KEY="test", USE_TZ=True, TIME_ZONE="UTC", INSTALLED_APPS=[])
    django.setup()


def _load_bracket():
    models_stub = ModuleType("fcdex_3_1.models")
    models_stub.TournamentGroup = SimpleNamespace(
        LEGACY=SimpleNamespace(value="legacy"), MAIN=SimpleNamespace(value="main")
    )
    models_stub.TournamentRound = SimpleNamespace(SEMIFINAL="semifinal", FINAL="final")
    models_stub.TournamentMatch = object
    models_stub.Tournament = object
    models_stub.TournamentRegistration = object
    models_stub.TournamentStatus = object
    bd_models = ModuleType("bd_models")
    bd_models_models = ModuleType("bd_models.models")
    bd_models_models.Player = object
    bd_models.models = bd_models_models
    sys.modules["bd_models"] = bd_models
    sys.modules["bd_models.models"] = bd_models_models
    sys.modules.pop("fcdex_3_1.fcdex_ext.tournament_bracket", None)
    sys.modules["fcdex_3_1.models"] = models_stub

    path = ROOT / "fcdex_3_1" / "fcdex_ext" / "tournament_bracket.py"
    spec = importlib.util.spec_from_file_location("fcdex_tournament_bracket_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_create_final_pairing_legacy_vs_main() -> None:
    bracket = _load_bracket()
    legacy_player = SimpleNamespace(pk=1, discord_id=101)
    main_player = SimpleNamespace(pk=2, discord_id=202)
    tournament = SimpleNamespace(pk=9)

    semi_filter = MagicMock()
    semi_filter.select_related.return_value = semi_filter
    semi_filter.afirst = AsyncMock(
        side_effect=[SimpleNamespace(winner=legacy_player), SimpleNamespace(winner=main_player)]
    )

    final_filter = MagicMock()
    final_filter.aexists = AsyncMock(return_value=False)

    acreate = AsyncMock()

    def match_objects_filter(**kwargs):
        if kwargs.get("round") == bracket.TournamentRound.FINAL:
            return final_filter
        return semi_filter

    bracket.TournamentMatch = SimpleNamespace(objects=SimpleNamespace(filter=match_objects_filter, acreate=acreate))

    ok = asyncio.run(bracket.create_final_pairing(tournament))
    assert ok is True
    acreate.assert_awaited_once()
    kwargs = acreate.await_args.kwargs
    assert kwargs["player1"] is legacy_player
    assert kwargs["player2"] is main_player
