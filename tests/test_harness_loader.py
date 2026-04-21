from pathlib import Path

import pytest

from tests.conftest import FIXTURES_DIR
from runbook_tools.harness.loader import ConfigurationError, load_scenarios_for_runbook


SCENARIOS_DIR = FIXTURES_DIR / "harness_scenarios"


def test_load_scenarios_conformant() -> None:
    scenarios = load_scenarios_for_runbook(FIXTURES_DIR / "conformant.md", SCENARIOS_DIR)

    assert len(scenarios) == 12
    assert scenarios[0].id == "I-01"
    assert scenarios[-1].id == "I-12"


def test_load_scenarios_orphan_yaml(tmp_path: Path) -> None:
    scenario_root = tmp_path / "infisical-secrets"
    scenario_root.mkdir(parents=True)
    for source in sorted((SCENARIOS_DIR / "infisical-secrets").glob("*.yaml")):
        (scenario_root / source.name).write_text(source.read_text())
    (scenario_root / "I-99.yaml").write_text(
        (
            "id: I-99\n"
            "runbook: infisical-secrets.md\n"
            "type: operate\n"
            "refs: [E-01]\n"
            "scenario: |\n"
            "  Orphan scenario.\n"
            "expected_answers:\n"
            "  - kind: tool_call\n"
            "    tool: infisical secrets get\n"
            "    argument_keys: [project-id, env, path]\n"
            "weight: 0.08333333333333333\n"
        )
    )

    with pytest.raises(ConfigurationError, match="orphan_yaml:I-99"):
        load_scenarios_for_runbook(FIXTURES_DIR / "conformant.md", tmp_path)


def test_load_scenarios_missing_yaml(tmp_path: Path) -> None:
    scenario_root = tmp_path / "infisical-secrets"
    scenario_root.mkdir(parents=True)
    for source in sorted((SCENARIOS_DIR / "infisical-secrets").glob("*.yaml")):
        if source.name == "I-12.yaml":
            continue
        (scenario_root / source.name).write_text(source.read_text())

    with pytest.raises(ConfigurationError, match="missing_yaml:I-12"):
        load_scenarios_for_runbook(FIXTURES_DIR / "conformant.md", tmp_path)


def test_load_scenarios_weight_mismatch(tmp_path: Path) -> None:
    scenario_root = tmp_path / "infisical-secrets"
    scenario_root.mkdir(parents=True)
    for source in sorted((SCENARIOS_DIR / "infisical-secrets").glob("*.yaml")):
        content = source.read_text()
        if source.name == "I-01.yaml":
            content = content.replace("weight: 0.08333333333333333", "weight: 0.2")
        (scenario_root / source.name).write_text(content)

    with pytest.raises(ConfigurationError, match="weight:I-01"):
        load_scenarios_for_runbook(FIXTURES_DIR / "conformant.md", tmp_path)

