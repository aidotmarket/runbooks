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

    result = runner.invoke(
        new_cmd,
        ["BAD", "--owner", "sysadmin", "--domain", "infrastructure"],
    )

    assert result.exit_code == 2
    assert "invalid system_name" in result.output


def test_new_cmd_refuses_overwrite(tmp_path: Path) -> None:
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("runbooks").mkdir()
        Path("runbooks/infisical-secrets.md").write_text("already here")
        result = runner.invoke(
            new_cmd,
            [
                "infisical-secrets",
                "--owner",
                "sysadmin",
                "--domain",
                "infrastructure",
            ],
        )

    assert result.exit_code == 1
    assert "refusing to overwrite" in result.output


def test_new_cmd_creates_explicit_draft_inside_runbooks(tmp_path: Path) -> None:
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            new_cmd,
            [
                "infisical-secrets",
                "--owner",
                "sysadmin",
                "--domain",
                "infrastructure",
            ],
        )
        created = Path("runbooks/infisical-secrets.md")
        assert result.exit_code == 0
        assert created.is_file()
        assert not Path("infisical-secrets.md").exists()
        content = created.read_text()
        assert "runbook_id: infisical-secrets" in content
        assert "status: DRAFT" in content
        assert "owner: sysadmin" in content


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


def test_lint_missing_schemas_dir_returns_usage_error(tmp_path: Path) -> None:
    runner = CliRunner()
    fixture = tmp_path / "bad.md"
    fixture.write_text("## §A. Header\n")

    result = runner.invoke(lint_cmd, [str(fixture), "--schemas-dir", str(tmp_path / "missing-schemas")])

    assert result.exit_code == 2


def test_lint_missing_readme_returns_usage_error(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(lint_cmd, ["--readme", str(tmp_path / "README.md")])

    assert result.exit_code == 2


def test_lint_internal_error_returns_exit_3(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    fixture = tmp_path / "bad.md"
    fixture.write_text("## §A. Header\n")

    def exploding_check(sections, ctx):
        del sections, ctx
        raise RuntimeError("boom")

    monkeypatch.setattr("runbook_tools.cli.ALL_CHECKS", [exploding_check])

    result = runner.invoke(lint_cmd, [str(fixture), "--schemas-dir", str(Path.cwd() / "schemas")])

    assert result.exit_code == 3
    assert "internal error in exploding_check" in result.output
    assert f"while linting {fixture.resolve()}: boom" in result.output


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
        "    scenario: demo scenario deliberately has no expected answer\n"
        "    weight: 1.0\n"
        "```\n"
    )

    result = runner.invoke(harness_cmd, ["--runbook", str(runbook)])

    assert result.exit_code == 1
    assert "§I failed acceptance schema validation" in result.output


def test_harness_cmd_skips_empty_i_without_creating_failure_artifact(
    tmp_path: Path,
) -> None:
    runbook = tmp_path / "empty.md"
    runbook.write_text(
        """---
system_name: empty
---

## §I. Acceptance Criteria

```yaml acceptance
scenario_set: []
```
"""
    )

    result = CliRunner().invoke(harness_cmd, ["--runbook", str(runbook)])

    assert result.exit_code == 0
    assert "SKIP_NO_EVIDENCE_BACKED_SCENARIOS" in result.output
    assert not (Path.cwd() / "harness" / "results" / "empty").exists()
