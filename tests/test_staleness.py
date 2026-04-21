from __future__ import annotations

from datetime import datetime, timezone

from tests.conftest import FIXTURES_DIR
from runbook_tools.lint.staleness import evaluate_staleness, write_lifecycle_update
from runbook_tools.parser.sections import extract_sections


def test_evaluate_staleness_not_stale() -> None:
    result = evaluate_staleness(
        _sections("conformant.md"),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert result.is_stale is False
    assert result.triggered_predicates == []
    assert result.new_first_detected_at is None
    assert result.recommended_action == "NONE"
    assert result.prev_first is None


def test_evaluate_staleness_commit_drift_and_date_expired() -> None:
    result = evaluate_staleness(
        _sections("stale_commit_drift.md"),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert result.is_stale is True
    assert result.triggered_predicates == ["commit_drift_60d"]


def test_evaluate_staleness_harness_stale() -> None:
    result = evaluate_staleness(
        _sections("stale_harness_old.md"),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert result.triggered_predicates == ["harness_90d"]


def test_evaluate_staleness_unverified_b_rows() -> None:
    result = evaluate_staleness(
        _sections("stale_unverified_b.md"),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert result.triggered_predicates == ["unverified_b_rows"]


def test_evaluate_staleness_multiple_predicates() -> None:
    markdown = (
        FIXTURES_DIR / "stale_commit_drift.md"
    ).read_text().replace("last_harness_date: 2026-04-20T02:00:00Z", "last_harness_date: 2026-01-01T02:00:00Z")
    markdown = markdown.replace("| Automated secret rotation UI | PLANNED | — | — | 2026-04-18 |", "| Automated secret rotation UI | PLANNED | — | — |  |")

    result = evaluate_staleness(
        extract_sections(markdown),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert result.triggered_predicates == ["commit_drift_60d", "harness_90d", "unverified_b_rows"]


def test_emission_table_row_1_set() -> None:
    result = evaluate_staleness(
        _sections("stale_commit_drift.md"),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert result.recommended_action == "SET"
    assert result.prev_first is None


def test_emission_table_row_2_no_action() -> None:
    markdown = (FIXTURES_DIR / "stale_commit_drift.md").read_text().replace(
        "first_staleness_detected_at: null",
        "first_staleness_detected_at: 2026-04-11T00:00:00Z",
    )

    result = evaluate_staleness(
        extract_sections(markdown),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert result.recommended_action == "NONE"
    assert result.prev_first == "2026-04-11T00:00:00Z"


def test_emission_table_row_3_still_no_action() -> None:
    markdown = (FIXTURES_DIR / "stale_commit_drift.md").read_text().replace(
        "first_staleness_detected_at: null",
        "first_staleness_detected_at: 2026-03-07T00:00:00Z",
    )

    result = evaluate_staleness(
        extract_sections(markdown),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert result.recommended_action == "NONE"
    assert result.prev_first == "2026-03-07T00:00:00Z"


def test_emission_table_row_4_clean() -> None:
    result = evaluate_staleness(
        _sections("conformant.md"),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert result.recommended_action == "NONE"
    assert result.is_stale is False


def test_emission_table_row_5_clear() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text().replace(
        "first_staleness_detected_at: null",
        "first_staleness_detected_at: 2026-04-01T00:00:00Z",
    )

    result = evaluate_staleness(
        extract_sections(markdown),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert result.recommended_action == "CLEAR"
    assert result.new_first_detected_at is None


def test_write_lifecycle_update_sets_iso(tmp_path) -> None:
    runbook_path = tmp_path / "runbook.md"
    original = (FIXTURES_DIR / "conformant.md").read_text()
    runbook_path.write_text(original)

    write_lifecycle_update(runbook_path, "2026-04-21T00:00:00+00:00")

    updated = runbook_path.read_text()
    assert 'first_staleness_detected_at: "2026-04-21T00:00:00+00:00"' in updated
    assert "last_refresh_session: S487" in updated
    assert "last_harness_date: 2026-04-20T02:00:00Z" in updated


def test_write_lifecycle_update_sets_null(tmp_path) -> None:
    runbook_path = tmp_path / "runbook.md"
    original = (FIXTURES_DIR / "conformant.md").read_text().replace(
        "first_staleness_detected_at: null",
        "first_staleness_detected_at: 2026-04-01T00:00:00Z",
    )
    runbook_path.write_text(original)

    write_lifecycle_update(runbook_path, None)

    updated = runbook_path.read_text()
    assert "first_staleness_detected_at: null" in updated


def _sections(fixture_name: str):
    return extract_sections((FIXTURES_DIR / fixture_name).read_text())
