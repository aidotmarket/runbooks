from __future__ import annotations

from datetime import datetime, timedelta, timezone

from runbook_tools.lint.staleness import evaluate_staleness
from runbook_tools.parser.sections import extract_sections
from tests.conftest import FIXTURES_DIR


def test_evaluate_staleness_not_stale() -> None:
    is_stale, triggered_predicates, new_first_detected_at, recommended_action = evaluate_staleness(
        _sections("conformant.md"),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert is_stale is False
    assert triggered_predicates == []
    assert new_first_detected_at is None
    assert recommended_action == "NONE"


def test_evaluate_staleness_commit_drift_and_date_expired() -> None:
    is_stale, triggered_predicates, _, _ = evaluate_staleness(
        _sections("stale_commit_drift.md"),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert is_stale is True
    assert triggered_predicates == ["commit_drift_60d"]


def test_full_head_matches_the_same_stored_short_commit() -> None:
    is_stale, triggered_predicates, _, _ = evaluate_staleness(
        _sections("conformant.md"),
        datetime(2026, 6, 21, tzinfo=timezone.utc),
        "ea70326000000000000000000000000000000000",
    )

    assert is_stale is False
    assert triggered_predicates == []


def test_evaluate_staleness_ignores_retired_harness_age() -> None:
    is_stale, triggered_predicates, _, recommended_action = evaluate_staleness(
        _sections("stale_harness_old.md"),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert is_stale is False
    assert triggered_predicates == []
    assert recommended_action == "NONE"


def test_evaluate_staleness_null_harness_date_is_not_a_staleness_signal() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text().replace(
        "last_harness_date: 2026-04-20T02:00:00Z",
        "last_harness_date: null",
        1,
    )
    for original in ("2026-04-20", "2026-04-19", "2026-04-18"):
        markdown = markdown.replace(f"| {original} |", "| 2027-04-20 |", 1)

    is_stale, triggered_predicates, _, _ = evaluate_staleness(
        extract_sections(markdown),
        datetime(2027, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert is_stale is False
    assert triggered_predicates == []


def test_evaluate_staleness_null_refresh_date_does_not_trigger_commit_drift() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text().replace(
        "last_refresh_date: 2026-04-21T17:30:00Z",
        "last_refresh_date: null",
        1,
    )
    for original in ("2026-04-20", "2026-04-19", "2026-04-18"):
        markdown = markdown.replace(f"| {original} |", "| 2027-04-20 |", 1)

    is_stale, triggered_predicates, _, _ = evaluate_staleness(
        extract_sections(markdown),
        datetime(2027, 4, 21, tzinfo=timezone.utc),
        "different-head",
    )

    assert is_stale is False
    assert triggered_predicates == []


def test_evaluate_staleness_unverified_b_rows() -> None:
    _, triggered_predicates, _, _ = evaluate_staleness(
        _sections("stale_unverified_b.md"),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert triggered_predicates == ["unverified_b_rows"]


def test_evaluate_staleness_treats_91_but_not_90_days_as_unverified() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()
    for original in ("2026-04-20", "2026-04-19", "2026-04-18"):
        markdown = markdown.replace(f"| {original} |", "| 2026-04-20 |", 1)

    at_90 = evaluate_staleness(
        extract_sections(markdown),
        datetime(2026, 7, 19, 23, 59, tzinfo=timezone.utc),
        "ea70326",
    )
    at_91 = evaluate_staleness(
        extract_sections(markdown),
        datetime(2026, 7, 20, tzinfo=timezone.utc),
        "ea70326",
    )

    assert at_90[0] is False
    assert at_90[1] == []
    assert at_91[0] is True
    assert at_91[1] == ["unverified_b_rows"]
    assert at_91[3] == "NONE"


def test_last_verified_age_uses_utc_day_across_extreme_caller_timezones() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text()
    for original in ("2026-04-20", "2026-04-19", "2026-04-18"):
        markdown = markdown.replace(f"| {original} |", "| 2026-04-20 |", 1)
    sections = extract_sections(markdown)

    local_next_day_but_utc_day_90 = evaluate_staleness(
        sections,
        datetime(2026, 7, 20, 0, 30, tzinfo=timezone(timedelta(hours=14))),
        "ea70326",
    )
    local_day_90_but_utc_day_91 = evaluate_staleness(
        sections,
        datetime(2026, 7, 19, 23, 30, tzinfo=timezone(timedelta(hours=-10))),
        "ea70326",
    )

    assert local_next_day_but_utc_day_90[1] == []
    assert local_day_90_but_utc_day_91[1] == ["unverified_b_rows"]


def test_evaluate_staleness_multiple_authoritative_predicates_ignore_harness_age() -> None:
    markdown = (
        FIXTURES_DIR / "stale_commit_drift.md"
    ).read_text().replace("last_harness_date: 2026-04-20T02:00:00Z", "last_harness_date: 2026-01-01T02:00:00Z")
    markdown = markdown.replace("| Automated secret rotation UI | PLANNED | — | — | 2026-04-18 |", "| Automated secret rotation UI | PLANNED | — | — |  |")

    _, triggered_predicates, _, _ = evaluate_staleness(
        extract_sections(markdown),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert triggered_predicates == ["commit_drift_60d", "unverified_b_rows"]


def test_file_owned_first_seen_clock_never_changes_staleness_result() -> None:
    base = (FIXTURES_DIR / "stale_commit_drift.md").read_text()
    without_clock = evaluate_staleness(
        extract_sections(base),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )
    with_reset_clock = evaluate_staleness(
        extract_sections(
            base.replace(
                "first_staleness_detected_at: null",
                "first_staleness_detected_at: 2026-04-21T00:00:00Z",
            )
        ),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert without_clock == with_reset_clock
    assert without_clock == (True, ["commit_drift_60d"], None, "NONE")


def test_evaluate_staleness_commit_drift_boundary_at_60_days_is_not_stale() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text().replace(
        "last_refresh_commit: ea70326",
        "last_refresh_commit: old-commit",
        1,
    )
    markdown = markdown.replace(
        "last_refresh_date: 2026-04-20T00:00:00Z",
        "last_refresh_date: 2026-02-20T00:00:00Z",
        1,
    )

    is_stale, triggered_predicates, _, _ = evaluate_staleness(
        extract_sections(markdown),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert is_stale is False
    assert triggered_predicates == []


def test_evaluate_staleness_harness_boundary_at_90_days_is_not_stale() -> None:
    markdown = (FIXTURES_DIR / "conformant.md").read_text().replace(
        "last_harness_date: 2026-04-20T02:00:00Z",
        "last_harness_date: 2026-01-21T00:00:00Z",
        1,
    )

    is_stale, triggered_predicates, _, _ = evaluate_staleness(
        extract_sections(markdown),
        datetime(2026, 4, 21, tzinfo=timezone.utc),
        "ea70326",
    )

    assert is_stale is False
    assert triggered_predicates == []


def _sections(fixture_name: str):
    return extract_sections((FIXTURES_DIR / fixture_name).read_text())
