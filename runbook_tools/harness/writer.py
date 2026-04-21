from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path


def write_result(result_dict, output_dir) -> Path:
    runbook_name = str(result_dict.get("runbook", "runbook.md"))
    system_name = Path(runbook_name).stem
    session_id = str(result_dict.get("session_id", "session"))
    started_at = str(result_dict.get("run_started_at", ""))
    if started_at:
        try:
            run_date = datetime.fromisoformat(started_at.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            run_date = datetime.now(timezone.utc).date().isoformat()
    else:
        run_date = datetime.now(timezone.utc).date().isoformat()

    destination = Path(output_dir) / system_name / f"{session_id}-{run_date}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result_dict, indent=2, sort_keys=True) + "\n")
    return destination
