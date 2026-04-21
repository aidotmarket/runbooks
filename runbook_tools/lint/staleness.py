from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import tempfile

from dateutil import parser as dateparser

from runbook_tools.lint import CheckContext
from runbook_tools.lint.forms import extract_b_rows, extract_j_payload
from runbook_tools.parser.sections import Section


@dataclass(slots=True)
class StalenessResult:
    is_stale: bool
    triggered_predicates: list[str]
    new_first_detected_at: str | None
    recommended_action: str
    prev_first: str | None


def evaluate_staleness(sections: list[Section], now: datetime, git_head: str) -> StalenessResult:
    section_map = {section.letter: section for section in sections}
    section_j = section_map.get("J")
    if section_j is None:
        raise ValueError("§J section is required for staleness evaluation")

    j = extract_j_payload(section_j)
    if j is None:
        raise ValueError("§J lifecycle payload is required for staleness evaluation")

    predicates: list[str] = []
    b_rows_unverified = compute_unverified_b_rows(sections)

    now_utc = _to_utc(now)
    commit_drift = j.get("last_refresh_commit") != git_head
    date_expired = (now_utc - _parse_datetime(j["last_refresh_date"])) > timedelta(days=60)
    if commit_drift and date_expired:
        predicates.append("commit_drift_60d")

    if (now_utc - _parse_datetime(j["last_harness_date"])) > timedelta(days=90):
        predicates.append("harness_90d")

    if b_rows_unverified:
        predicates.append("unverified_b_rows")

    is_stale = bool(predicates)
    prev_first = _normalize_iso_value(j.get("first_staleness_detected_at"))
    if is_stale and prev_first is None:
        return StalenessResult(True, predicates, now_utc.isoformat(), "SET", prev_first)
    if (not is_stale) and prev_first is not None:
        return StalenessResult(False, predicates, None, "CLEAR", prev_first)
    if is_stale and prev_first is not None:
        return StalenessResult(True, predicates, prev_first, "NONE", prev_first)
    return StalenessResult(False, predicates, prev_first, "NONE", prev_first)


def compute_unverified_b_rows(sections: list[Section]) -> list[int]:
    section_b = next((section for section in sections if section.letter == "B"), None)
    if section_b is None:
        return []

    unverified_rows: list[int] = []
    for index, row in enumerate(extract_b_rows(section_b), start=1):
        last_verified = row.get("Last Verified", "").strip()
        if last_verified in {"", "—"}:
            unverified_rows.append(index)
    return unverified_rows


def write_lifecycle_update(runbook_path: Path, new_first_detected_at: str | None) -> None:
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

    replacement_value = "null" if new_first_detected_at is None else f'"{new_first_detected_at}"'
    updated_block, replacements = re.subn(
        r"(^first_staleness_detected_at:\s*).*$",
        rf"\g<1>{replacement_value}",
        block_match.group(1),
        count=1,
        flags=re.MULTILINE,
    )
    if replacements != 1:
        raise ValueError("§J first_staleness_detected_at field not found")

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


def get_staleness_payload(sections: list[Section], ctx: CheckContext) -> dict[str, object]:
    cache_key = "staleness_payload"
    cached = ctx.form_cache.get(cache_key)
    if isinstance(cached, dict):
        return cached

    section_map = {section.letter: section for section in sections}
    payload = {
        "j": extract_j_payload(section_map["J"]) if "J" in section_map else None,
        "unverified_b_rows": compute_unverified_b_rows(sections),
    }
    ctx.form_cache[cache_key] = payload
    return payload


def _parse_datetime(value: str) -> datetime:
    if isinstance(value, datetime):
        return _to_utc(value)
    return _to_utc(dateparser.parse(value))


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_iso_value(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _to_utc(value).isoformat().replace("+00:00", "Z")
    return value
