from __future__ import annotations

import json
import re
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from dateutil import parser as dateparser

from runbook_tools.lint import CheckContext
from runbook_tools.lint.forms import (
    classify_last_verified,
    extract_b_rows,
    extract_j_payload,
)
from runbook_tools.parser.sections import Section

StalenessResult = tuple[bool, list[str], str | None, str]
PENDING_HARNESS_TOOLING = "PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)"
_UNSET = object()


def evaluate_staleness(sections: list[Section], now: datetime, git_head: str) -> StalenessResult:
    section_map = {section.letter: section for section in sections}
    section_j = section_map.get("J")
    if section_j is None:
        raise ValueError("§J section is required for staleness evaluation")

    j = extract_j_payload(section_j)
    if j is None:
        raise ValueError("§J lifecycle payload is required for staleness evaluation")

    predicates: list[str] = []
    b_rows_unverified = compute_unverified_b_rows(sections, now)

    now_utc = _to_utc(now)
    commit_drift = not _same_commit_ref(j.get("last_refresh_commit"), git_head)
    try:
        last_refresh_at = _parse_datetime(j.get("last_refresh_date"))
    except (TypeError, ValueError, OverflowError):
        # Form validation owns the deterministic FAIL. Staleness must not turn
        # malformed lifecycle input into an internal-error exit.
        last_refresh_at = None
    date_expired = (
        last_refresh_at is not None
        and (now_utc - last_refresh_at) > timedelta(days=60)
    )
    if commit_drift and date_expired:
        predicates.append("commit_drift_60d")

    if b_rows_unverified:
        predicates.append("unverified_b_rows")

    is_stale = bool(predicates)
    # File-owned first-seen clocks are legacy provenance only. They cannot
    # grant freshness or reset escalation; canonical server state owns age.
    return is_stale, predicates, None, "NONE"


def compute_unverified_b_rows(
    sections: list[Section],
    now: datetime | None = None,
) -> list[int]:
    section_b = next((section for section in sections if section.letter == "B"), None)
    if section_b is None:
        return []

    unverified_rows: list[int] = []
    for index, row in enumerate(extract_b_rows(section_b), start=1):
        last_verified = row.get("Last Verified", "").strip()
        state, _ = classify_last_verified(last_verified, now)
        if state in {"unverified", "expired"}:
            unverified_rows.append(index)
    return unverified_rows


def write_lifecycle_update(
    runbook_path: Path,
    *,
    last_harness_pass_rate: float | str | object = _UNSET,
    last_harness_date: str | None | object = _UNSET,
) -> None:
    content = runbook_path.read_text()
    section_match = re.search(
        r"(^##\s+§J\..*?)(?=^##\s+§[A-K]\.|\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    if section_match is None:
        raise ValueError("§J section not found")

    section_text = section_match.group(1)
    block_match = re.search(
        r"(^```yaml\s+lifecycle\s*\n.*?^```[ \t]*$)",
        section_text,
        re.MULTILINE | re.DOTALL,
    )
    if block_match is None:
        raise ValueError("§J lifecycle yaml block not found")

    updated_block = block_match.group(1)
    if last_harness_pass_rate is not _UNSET:
        updated_block = _upsert_lifecycle_field(
            updated_block,
            "last_harness_pass_rate",
            str(last_harness_pass_rate),
        )
    if last_harness_date is not _UNSET:
        replacement_value = (
            "null" if last_harness_date is None else str(last_harness_date)
        )
        updated_block = _upsert_lifecycle_field(
            updated_block,
            "last_harness_date",
            replacement_value,
        )

    updated_section = section_text.replace(block_match.group(1), updated_block, 1)
    updated_content = content[: section_match.start(1)] + updated_section + content[section_match.end(1) :]

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=str(runbook_path.parent),
    ) as tmp:
        tmp.write(updated_content)
        temp_path = Path(tmp.name)
    temp_path.replace(runbook_path)


def newest_harness_result(
    runbook_path: Path,
) -> tuple[Path, dict[str, Any]] | None:
    repo_root = _find_repo_root(runbook_path)
    if repo_root is None:
        return None

    results_dir = repo_root / "harness" / "results" / runbook_path.stem
    candidates: list[tuple[Path, dict[str, Any]]] = []
    for result_path in results_dir.glob("*.json"):
        payload = json.loads(result_path.read_text())
        if not isinstance(payload, dict):
            raise TypeError(f"harness result is not a JSON object: {result_path}")
        candidates.append((result_path, payload))

    if not candidates:
        return None
    return max(candidates, key=_harness_result_sort_key)


def harness_lifecycle_values(runbook_path: Path) -> tuple[float | str, str | None]:
    newest = newest_harness_result(runbook_path)
    if newest is None:
        return PENDING_HARNESS_TOOLING, None

    _, payload = newest
    run_started_at = payload.get("run_started_at")
    harness_date = str(run_started_at) if run_started_at else None
    if payload.get("result") == "INFRASTRUCTURE_FAILURE":
        return PENDING_HARNESS_TOOLING, harness_date
    if payload.get("result") not in {"PASS", "FAIL"}:
        raise ValueError(f"unsupported harness result value: {payload.get('result')!r}")
    return float(payload["aggregate_score"]), harness_date


def get_staleness_payload(sections: list[Section], ctx: CheckContext) -> dict[str, object]:
    cache_key = "staleness_payload"
    cached = ctx.form_cache.get(cache_key)
    if isinstance(cached, dict):
        return cached

    section_map = {section.letter: section for section in sections}
    payload = {
        "j": extract_j_payload(section_map["J"]) if "J" in section_map else None,
        "unverified_b_rows": compute_unverified_b_rows(sections, ctx.now),
    }
    ctx.form_cache[cache_key] = payload
    return payload


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _to_utc(value)
    return _to_utc(dateparser.parse(value))


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_iso_value(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _to_utc(value).isoformat().replace("+00:00", "Z")
    return value


def _same_commit_ref(stored: object, current: str) -> bool:
    if not isinstance(stored, str):
        return False
    stored_value = stored.strip().casefold()
    current_value = current.strip().casefold()
    if not re.fullmatch(r"[0-9a-f]{7,40}", stored_value):
        return False
    if not re.fullmatch(r"[0-9a-f]{7,40}", current_value):
        return False
    return stored_value.startswith(current_value) or current_value.startswith(stored_value)


def _upsert_lifecycle_field(block: str, field: str, value: str) -> str:
    updated_block, replacements = re.subn(
        rf"(^{re.escape(field)}:\s*).*$",
        rf"\g<1>{value}",
        block,
        count=1,
        flags=re.MULTILINE,
    )
    if replacements == 1:
        return updated_block
    closing_fence = re.search(r"^```[ \t]*$", block, re.MULTILINE)
    if closing_fence is None:
        raise ValueError("§J lifecycle YAML block closing fence not found")
    prefix = block[: closing_fence.start()]
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    return prefix + f"{field}: {value}\n" + block[closing_fence.start() :]


def _find_repo_root(runbook_path: Path) -> Path | None:
    start = runbook_path.resolve().parent
    for candidate in (start, *start.parents):
        if (candidate / "CATALOG.json").is_file():
            return candidate
    return None


def _harness_result_sort_key(
    candidate: tuple[Path, dict[str, Any]],
) -> tuple[bool, datetime, str]:
    result_path, payload = candidate
    try:
        run_started_at = _parse_datetime(payload.get("run_started_at"))
    except (TypeError, ValueError, OverflowError):
        run_started_at = None
    return (
        run_started_at is not None,
        run_started_at or datetime.min.replace(tzinfo=UTC),
        result_path.name,
    )
