from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from runbook_tools.cli import lint_cmd
from runbook_tools.lint import CheckContext
from runbook_tools.lint.checks import check_21_harness_claim_matches_result
from runbook_tools.lint.staleness import PENDING_HARNESS_TOOLING
from runbook_tools.parser.sections import extract_sections, extract_yaml_frontmatter
from tests.conftest import FIXTURES_DIR, SCHEMAS_DIR


def test_check_21_no_result_requires_pending_tooling(tmp_path: Path) -> None:
    runbook_path = _write_runbook(tmp_path)

    findings = _run_check_21(runbook_path)

    assert len(findings) == 2
    assert all(finding.severity == "FAIL" for finding in findings)
    assert any(
        finding.message
        == "§J claims a measured pass rate but no harness result exists for demo"
        for finding in findings
    )
    assert any("last_harness_date must be null" in finding.message for finding in findings)

    runbook_path.write_text(
        runbook_path.read_text().replace(
            "last_harness_pass_rate: 1.0",
            f"last_harness_pass_rate: {PENDING_HARNESS_TOOLING}",
            1,
        )
    )
    pending_with_unsupported_date = _run_check_21(runbook_path)
    assert len(pending_with_unsupported_date) == 1
    assert "last_harness_date must be null" in pending_with_unsupported_date[0].message

    runbook_path.write_text(
        runbook_path.read_text().replace(
            "last_harness_date: 2026-04-20T02:00:00Z",
            "last_harness_date: null",
            1,
        )
    )
    assert _run_check_21(runbook_path) == []


def test_check_21_never_harnessed_runbook_may_omit_claim_pair(tmp_path: Path) -> None:
    runbook_path = _write_runbook(tmp_path, stem="never-harnessed")
    _remove_harness_claim_pair(runbook_path)

    assert _run_check_21(runbook_path) == []

    _write_result(
        tmp_path,
        runbook_path.stem,
        result="PASS",
        score=1.0,
        run_started_at="2026-04-20T02:00:00Z",
    )
    findings = _run_check_21(runbook_path)
    assert len(findings) == 1
    assert "must retain the harness claim pair" in findings[0].message


def test_check_21_infrastructure_failure_requires_pending_tooling(
    tmp_path: Path,
) -> None:
    runbook_path = _write_runbook(tmp_path)
    _write_result(
        tmp_path,
        runbook_path.stem,
        result="INFRASTRUCTURE_FAILURE",
        score=0.0,
        run_started_at="2026-04-20T02:00:00Z",
    )

    findings = _run_check_21(runbook_path)

    assert len(findings) == 1
    assert findings[0].message == (
        "§J claims a measured pass rate but newest harness result for demo "
        "is an infrastructure failure"
    )

    runbook_path.write_text(
        runbook_path.read_text().replace(
            "last_harness_pass_rate: 1.0",
            f"last_harness_pass_rate: {PENDING_HARNESS_TOOLING}",
            1,
        )
    )
    assert _run_check_21(runbook_path) == []

    runbook_path.write_text(
        runbook_path.read_text().replace(
            "last_harness_date: 2026-04-20T02:00:00Z",
            "last_harness_date: 2026-04-20T03:00:00Z",
            1,
        )
    )
    date_findings = _run_check_21(runbook_path)
    assert len(date_findings) == 1
    assert "last_harness_date" in date_findings[0].message


def test_check_21_measured_result_must_match_score_and_exact_instant(
    tmp_path: Path,
) -> None:
    runbook_path = _write_runbook(tmp_path)
    result_path = _write_result(
        tmp_path,
        runbook_path.stem,
        result="PASS",
        score=1.0,
        run_started_at="2026-04-20T03:00:00Z",
    )

    date_findings = _run_check_21(runbook_path)

    assert len(date_findings) == 1
    assert "claimed '2026-04-20T02:00:00Z'" in date_findings[0].message
    assert "measured '2026-04-20T03:00:00Z'" in date_findings[0].message

    payload = json.loads(result_path.read_text())
    payload["run_started_at"] = "2026-04-19T22:00:00-04:00"
    result_path.write_text(json.dumps(payload))

    assert _run_check_21(runbook_path) == []

    payload["aggregate_score"] = 0.25
    result_path.write_text(json.dumps(payload))

    score_findings = _run_check_21(runbook_path)

    assert len(score_findings) == 1
    assert "claimed 1.0" in score_findings[0].message
    assert "measured 0.25" in score_findings[0].message


def test_refresh_harness_metadata_rewrites_measured_harness_fields_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runbook_path = _write_runbook(tmp_path, stem="measured")
    retained_clock = "2026-05-01T03:04:05Z"
    runbook_path.write_text(
        runbook_path.read_text().replace(
            "first_staleness_detected_at: null",
            f"first_staleness_detected_at: {retained_clock}",
            1,
        )
    )
    _write_result(
        tmp_path,
        runbook_path.stem,
        result="FAIL",
        score=0.375,
        run_started_at="2026-07-18T08:36:20.840312Z",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("runbook_tools.cli.ALL_CHECKS", [])

    result = CliRunner().invoke(
        lint_cmd,
        [
            str(runbook_path),
            "--refresh-harness-metadata",
            "--schemas-dir",
            str(SCHEMAS_DIR),
        ],
    )

    assert result.exit_code == 0
    updated = runbook_path.read_text()
    assert "last_harness_pass_rate: 0.375" in updated
    assert "last_harness_date: 2026-07-18T08:36:20.840312Z" in updated
    assert f"first_staleness_detected_at: {retained_clock}" in updated


def test_refresh_harness_metadata_rewrites_no_result_as_pending_and_null(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runbook_path = _write_runbook(tmp_path, stem="never-harnessed")
    _remove_harness_claim_pair(runbook_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("runbook_tools.cli.ALL_CHECKS", [])

    result = CliRunner().invoke(
        lint_cmd,
        [
            str(runbook_path),
            "--refresh-harness-metadata",
            "--schemas-dir",
            str(SCHEMAS_DIR),
        ],
    )

    assert result.exit_code == 0
    updated = runbook_path.read_text()
    assert f"last_harness_pass_rate: {PENDING_HARNESS_TOOLING}" in updated
    assert "last_harness_date: null" in updated
    assert "first_staleness_detected_at: null" in updated


@pytest.mark.parametrize("retired_flag", ["--update-lifecycle", "--update-staleness"])
def test_retired_file_clock_write_flags_are_rejected_without_writes(
    tmp_path: Path,
    monkeypatch,
    retired_flag: str,
) -> None:
    runbook_path = _write_runbook(tmp_path, stem="retired-clock-writer")
    before = runbook_path.read_text()
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        lint_cmd,
        [
            str(runbook_path),
            retired_flag,
            "--schemas-dir",
            str(SCHEMAS_DIR),
        ],
    )

    assert result.exit_code == 2
    assert runbook_path.read_text() == before


def _write_runbook(tmp_path: Path, *, stem: str = "demo") -> Path:
    (tmp_path / "CATALOG.json").write_text("{}\n")
    runbook_path = tmp_path / "runbooks" / f"{stem}.md"
    runbook_path.parent.mkdir(parents=True, exist_ok=True)
    runbook_path.write_text((FIXTURES_DIR / "conformant.md").read_text())
    return runbook_path


def _write_result(
    repo_root: Path,
    stem: str,
    *,
    result: str,
    score: float,
    run_started_at: str,
) -> Path:
    result_path = (
        repo_root
        / "harness"
        / "results"
        / stem
        / "S-TEST-2026-07-18.json"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(
            {
                "result": result,
                "aggregate_score": score,
                "pass_threshold": 0.8,
                "run_started_at": run_started_at,
                "run_finished_at": run_started_at,
                "runbook": f"{stem}.md",
                "linter_version": "1.0.0",
                "scenarios": [],
            }
        )
    )
    return result_path


def _remove_harness_claim_pair(runbook_path: Path) -> None:
    runbook_path.write_text(
        runbook_path.read_text()
        .replace("last_harness_pass_rate: 1.0\n", "", 1)
        .replace("last_harness_date: 2026-04-20T02:00:00Z\n", "", 1)
    )


def _run_check_21(runbook_path: Path):
    markdown = runbook_path.read_text()
    return check_21_harness_claim_matches_result(
        extract_sections(markdown),
        CheckContext(
            schemas_dir=SCHEMAS_DIR,
            readme_path=runbook_path,
            mode="strict",
            frontmatter=extract_yaml_frontmatter(markdown),
        ),
    )
