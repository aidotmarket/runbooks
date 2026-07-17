from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml

from runbook_tools.catalog.generator import generate_catalog
from runbook_tools.cli import (
    catalog_check_cmd,
    catalog_select_cmd,
    harness_cmd,
    lint_cmd,
)


SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"


def _metadata(runbook_id: str) -> dict:
    return {
        "runbook_id": runbook_id,
        "domain": "test-domain",
        "status": "ACTIVE",
        "authoritative_for": [{"topic": f"{runbook_id}-topic", "section": "Overview"}],
        "aliases": [],
        "error_signatures": [],
        "supersedes": [],
        "superseded_by": [],
        "owner": "test-owner",
        "last_verified_at": "2026-07-17",
    }


def _write_readme(root: Path) -> None:
    (root / "README.md").write_text(
        "# Fixture\n\n## Adoption status\n\n"
        "| System | Runbook | Status |\n|---|---|---|\n| None | — | NOT_STARTED |\n\n"
        "## Status values\n\nFixture.\n"
    )


def _write_member(root: Path, runbook_id: str) -> Path:
    path = root / "runbooks" / f"{runbook_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        + yaml.safe_dump(_metadata(runbook_id), sort_keys=False)
        + f"---\n\n# {runbook_id}\n\n## Overview\n\nFixture.\n"
    )
    return path


def _generated_repo(root: Path, count: int) -> list[Path]:
    _write_readme(root)
    members = [_write_member(root, f"member-{index}") for index in range(count)]
    generate_catalog(root)
    return members


@pytest.mark.parametrize("mode", ["lint-selection", "harness-selection"])
def test_zero_catalog_selection_modes_emit_sentinel_and_exit_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    _generated_repo(tmp_path, 0)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(catalog_select_cmd, ["--mode", mode])

    assert result.exit_code == 1
    assert result.output.strip() == "ZERO_TARGETS_SELECTED"


def test_default_lint_and_harness_zero_targets_fail_nonvacuously(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _generated_repo(tmp_path, 0)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    lint_result = runner.invoke(
        lint_cmd, ["--mode", "strict", "--schemas-dir", str(SCHEMAS_DIR)]
    )
    harness_result = runner.invoke(harness_cmd, ["--mode", "conformant"])

    assert lint_result.exit_code == 1
    assert harness_result.exit_code == 1
    assert "ZERO_TARGETS_SELECTED" in lint_result.output
    assert "ZERO_TARGETS_SELECTED" in harness_result.output


@pytest.mark.parametrize("catalog_state", ["missing", "invalid"])
def test_missing_or_invalid_catalog_fails_before_lint_and_harness_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, catalog_state: str
) -> None:
    _write_readme(tmp_path)
    if catalog_state == "invalid":
        (tmp_path / "CATALOG.json").write_text("not-json\n")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    lint_result = runner.invoke(
        lint_cmd, ["--mode", "strict", "--schemas-dir", str(SCHEMAS_DIR)]
    )
    harness_result = runner.invoke(harness_cmd, ["--mode", "conformant"])

    assert lint_result.exit_code == 1
    assert harness_result.exit_code == 1
    assert "catalog selection failed" in lint_result.output
    assert "catalog selection failed" in harness_result.output
    assert "ZERO_TARGETS_SELECTED" not in lint_result.output + harness_result.output


def test_strict_lint_selects_logs_and_attempts_all_five_active_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    members = _generated_repo(tmp_path, 5)
    attempted: list[Path] = []

    def tracking_check(sections, context):
        attempted.append(context.readme_path)
        return []

    monkeypatch.setattr("runbook_tools.cli.ALL_CHECKS", [tracking_check])
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        lint_cmd, ["--mode", "strict", "--schemas-dir", str(SCHEMAS_DIR)]
    )

    assert result.exit_code == 0
    assert "SELECTED_TARGET_COUNT=5" in result.output
    assert result.output.count("SELECTED_TARGET_PATH=") == 5
    assert set(attempted) == {path.resolve() for path in members}


def test_conformant_harness_selects_logs_and_attempts_all_five_active_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    members = _generated_repo(tmp_path, 5)
    attempted: list[Path] = []

    def recording_loop(**kwargs):
        attempted.extend(kwargs["runbook_paths"])
        return 0

    monkeypatch.setattr("runbook_tools.cli._run_harness_loop", recording_loop)
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(harness_cmd, ["--mode", "conformant", "--session", "TEST"])

    assert result.exit_code == 0
    assert "SELECTED_TARGET_COUNT=5" in result.output
    assert result.output.count("SELECTED_TARGET_PATH=") == 5
    assert set(attempted) == {path.resolve() for path in members}


def test_selected_harness_target_configuration_failure_is_not_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _generated_repo(tmp_path, 1)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(harness_cmd, ["--mode", "conformant", "--session", "TEST"])

    assert result.exit_code == 1
    assert "SELECTED_TARGET_COUNT=1" in result.output
    assert "missing a valid §I acceptance payload" in result.output


def test_catalog_check_cli_exits_one_on_generated_catalog_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _generated_repo(tmp_path, 1)
    catalog = tmp_path / "CATALOG.json"
    catalog.write_text(catalog.read_text().replace('"schema_version": 1', '"schema_version": 2'))
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(catalog_check_cmd)

    assert result.exit_code == 1
    assert "catalog drift: CATALOG.json" in result.output
