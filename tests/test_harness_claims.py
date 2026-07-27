from __future__ import annotations

import json
from pathlib import Path

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

    assert len(findings) == 1
    assert findings[0].severity == "FAIL"
    assert findings[0].message == (
        "§J claims a measured pass rate but no harness result exists for demo"
    )

    runbook_path.write_text(
        runbook_path.read_text().replace(
            "last_harness_pass_rate: 1.0",
            f"last_harness_pass_rate: {PENDING_HARNESS_TOOLING}",
            1,
        )
    )
    assert _run_check_21(runbook_path) == []


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
        "§J claims a measured pass rate but no harness result exists for demo"
    )

    runbook_path.write_text(
        runbook_path.read_text().replace(
            "last_harness_pass_rate: 1.0",
            f"last_harness_pass_rate: {PENDING_HARNESS_TOOLING}",
            1,
        )
    )
    assert _run_check_21(runbook_path) == []


def test_check_21_measured_result_must_match_score_and_utc_date(
    tmp_path: Path,
) -> None:
    runbook_path = _write_runbook(tmp_path)
    result_path = _write_result(
        tmp_path,
        runbook_path.stem,
        result="PASS",
        score=1.0,
        run_started_at="2026-04-20T23:30:00-02:00",
    )

    date_findings = _run_check_21(runbook_path)

    assert len(date_findings) == 1
    assert "claimed '2026-04-20T02:00:00Z'" in date_findings[0].message
    assert "measured '2026-04-20T23:30:00-02:00'" in date_findings[0].message

    payload = json.loads(result_path.read_text())
    payload["aggregate_score"] = 0.25
    payload["run_started_at"] = "2026-04-20T01:00:00Z"
    result_path.write_text(json.dumps(payload))

    score_findings = _run_check_21(runbook_path)

    assert len(score_findings) == 1
    assert "claimed 1.0" in score_findings[0].message
    assert "measured 0.25" in score_findings[0].message


def test_update_lifecycle_rewrites_measured_harness_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runbook_path = _write_runbook(tmp_path, stem="measured")
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
            "--update-lifecycle",
            "--schemas-dir",
            str(SCHEMAS_DIR),
        ],
    )

    assert result.exit_code == 0
    updated = runbook_path.read_text()
    assert "last_harness_pass_rate: 0.375" in updated
    assert "last_harness_date: 2026-07-18T08:36:20.840312Z" in updated


def test_update_lifecycle_rewrites_no_result_as_pending_and_null(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runbook_path = _write_runbook(tmp_path, stem="never-harnessed")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("runbook_tools.cli.ALL_CHECKS", [])

    result = CliRunner().invoke(
        lint_cmd,
        [
            str(runbook_path),
            "--update-lifecycle",
            "--schemas-dir",
            str(SCHEMAS_DIR),
        ],
    )

    assert result.exit_code == 0
    updated = runbook_path.read_text()
    assert f"last_harness_pass_rate: {PENDING_HARNESS_TOOLING}" in updated
    assert "last_harness_date: null" in updated


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
