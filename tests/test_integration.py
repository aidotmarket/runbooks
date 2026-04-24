from pathlib import Path

from click.testing import CliRunner

from tests.conftest import FIXTURES_DIR, SCHEMAS_DIR
from runbook_tools.cli import harness_cmd, lint_cmd, new_cmd


def test_lint_conformant_runbook_passes() -> None:
    runner = CliRunner()

    result = runner.invoke(
        lint_cmd,
        [str(FIXTURES_DIR / "conformant.md"), "--schemas-dir", str(SCHEMAS_DIR)],
    )

    assert result.exit_code == 0
    assert "FAIL" not in result.output


def test_lint_missing_section_fails() -> None:
    runner = CliRunner()

    result = runner.invoke(
        lint_cmd,
        [str(FIXTURES_DIR / "missing_section_g.md"), "--schemas-dir", str(SCHEMAS_DIR)],
    )

    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_new_cmd_creates_file(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(new_cmd, ["infisical-secrets", "--dry-run"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "infisical-secrets" in result.output


def test_harness_cmd_reports_dispatch_failure_when_unconfigured(monkeypatch) -> None:
    monkeypatch.delenv("KOSKADEUX_MCP_URL", raising=False)
    monkeypatch.delenv("KOSKADEUX_MCP_TOKEN", raising=False)
    runner = CliRunner()

    result = runner.invoke(
        harness_cmd,
        ["--runbook", str(FIXTURES_DIR / "conformant.md")],
    )

    assert result.exit_code != 0
    assert "KOSKADEUX_MCP_URL is not set" in result.output


def test_harness_cmd_rejects_both_external_flags() -> None:
    runner = CliRunner()

    result = runner.invoke(
        harness_cmd,
        [
            "--runbook",
            str(FIXTURES_DIR / "conformant.md"),
            "--external-scenario-set",
            "/tmp/not-used",
            "--external-scenarios-from-state",
            "state:missing",
        ],
    )

    assert result.exit_code == 2
    assert "mutually exclusive" in result.output

