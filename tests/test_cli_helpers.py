from pathlib import Path

import pytest
from click.testing import CliRunner

from runbook_tools.cli import _parse_readme_status_rows, harness_cmd, lint_cmd, new_cmd


def test_lint_version_flag() -> None:
    runner = CliRunner()

    result = runner.invoke(lint_cmd, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == "1.0.0"


def test_new_cmd_invalid_name() -> None:
    runner = CliRunner()

    result = runner.invoke(new_cmd, ["BAD"])

    assert result.exit_code == 2
    assert "invalid system_name" in result.output


def test_new_cmd_refuses_overwrite(tmp_path: Path) -> None:
    runner = CliRunner()
    existing = tmp_path / "infisical-secrets.md"
    existing.write_text("already here")

    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("infisical-secrets.md").write_text("already here")
        result = runner.invoke(new_cmd, ["infisical-secrets"])

    assert result.exit_code == 1
    assert "refusing to overwrite" in result.output


def test_parse_readme_status_rows_accepts_markdown_links(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "# x\n\n"
        "| System | Runbook | Status | Gate | Linter | Harness | Owner |\n"
        "|---|---|---|---|---|---|---|\n"
        "| Infisical | [infisical-secrets.md](infisical-secrets.md) | CONFORMANT | gate4 | PASS | 1.0 | sysadmin |\n"
    )

    rows = _parse_readme_status_rows(readme)

    assert rows[0]["status"] == "CONFORMANT"
    assert rows[0]["path"] == (tmp_path / "infisical-secrets.md").resolve()


def test_parse_readme_status_rows_rejects_unknown_status(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "| System | Runbook | Status | Gate | Linter | Harness | Owner |\n"
        "|---|---|---|---|---|---|---|\n"
        "| Infisical | infisical-secrets.md | UNKNOWN_STATUS | gate4 | PASS | 1.0 | sysadmin |\n"
    )

    with pytest.raises(Exception, match="unknown README status value"):
        _parse_readme_status_rows(readme)


def test_lint_json_output(tmp_path: Path) -> None:
    runner = CliRunner()
    fixture = tmp_path / "bad.md"
    fixture.write_text("## §A. Header\n")

    result = runner.invoke(lint_cmd, [str(fixture), "--format", "json", "--schemas-dir", str(Path.cwd() / "schemas")])

    assert result.exit_code == 1
    assert result.output.strip().startswith("[")


def test_harness_cmd_configuration_error(tmp_path: Path) -> None:
    runner = CliRunner()
    runbook = tmp_path / "demo.md"
    runbook.write_text(
        "---\n"
        "system_name: demo-system\n"
        "purpose_sentence: A sufficiently long purpose sentence for testing.\n"
        "owner_agent: max\n"
        "escalation_contact: max\n"
        "lifecycle_ref: §J\n"
        "authoritative_scope: A test scope that is long enough.\n"
        "linter_version: 1.0.0\n"
        "---\n\n"
        "# Demo\n\n"
        "## §I. Acceptance Criteria\n\n"
        "```yaml acceptance\n"
        "scenario_set:\n"
        "  - id: I-01\n"
        "    type: operate\n"
        "    refs: [E-01]\n"
        "    scenario: demo scenario\n"
        "    expected_answers:\n"
        "      - kind: tool_call\n"
        "        tool: demo\n"
        "        argument_keys: [x]\n"
        "    weight: 1.0\n"
        "```\n"
    )

    result = runner.invoke(harness_cmd, ["--runbook", str(runbook)])

    assert result.exit_code == 1
    assert "Scenario configuration drift" in result.output or "missing_yaml:I-01" in result.output
