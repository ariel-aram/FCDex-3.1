from __future__ import annotations

import json
import logging
import time
from pathlib import Path

SESSION_ID = "9834ad"
_LOG = logging.getLogger("fcdex_3_1.merge.debug")


def _candidate_log_paths() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        Path.cwd() / "debug-9834ad.log",
        here.parents[2] / "debug-9834ad.log",
        here.parents[3] / "debug-9834ad.log",
    ]


def merge_debug(
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict | None = None,
    *,
    run_id: str = "pre-fix",
) -> None:
    # #region agent log
    payload = {
        "sessionId": SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    line = json.dumps(payload, default=str)
    _LOG.info("MERGE_DEBUG %s", line)
    for path in _candidate_log_paths():
        try:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
            return
        except OSError:
            continue
    # #endregion
