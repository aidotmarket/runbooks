from pathlib import Path

import pytest

from runbook_tools.cli import _default_scenarios_dir
from runbook_tools.harness.loader import ConfigurationError, load_scenarios_for_runbook
from tests.conftest import FIXTURES_DIR

SCENARIOS_DIR = FIXTURES_DIR / "harness_scenarios"


def test_load_scenarios_conformant() -> None:
    scenarios = load_scenarios_for_runbook(FIXTURES_DIR / "conformant.md")

    assert len(scenarios) == 12
    assert scenarios[0].id == "I-01"
    assert scenarios[0].scenario_prose == (
        "Support needs the first action for a missing production frontend secret."
    )
    assert scenarios[0].expected_answers == [
        {
            "kind": "tool_call",
            "tool": "infisical secrets get",
            "argument_keys": ["project-id", "env", "path"],
        }
    ]
    assert scenarios[-1].id == "I-12"


def test_load_scenarios_derives_equal_diagnostic_weight_when_i_omits_it(
    tmp_path: Path,
) -> None:
    runbook = tmp_path / "minimal.md"
    runbook.write_text(
        """---
system_name: minimal
---

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: A real operator condition requires the documented first action.
    expected_answers:
      - kind: human_action
        verb: inspect
        object: current evidence
        target: E-01
```
"""
    )
    scenarios = load_scenarios_for_runbook(runbook, tmp_path / "scenarios")

    assert len(scenarios) == 1
    assert scenarios[0].weight == 1.0


def test_incomplete_legacy_weights_fail_as_ambiguous_diagnostic_configuration(
    tmp_path: Path,
) -> None:
    runbook = tmp_path / "partial-weights.md"
    runbook.write_text(
        """## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: The first evidence-backed example retains a legacy diagnostic weight.
    expected_answers:
      - kind: classification
        label: FIRST
    weight: 0.9
  - id: I-02
    type: isolate
    refs: [F-01]
    scenario: The second evidence-backed example has no legacy diagnostic weight.
    expected_answers:
      - kind: classification
        label: SECOND
```
"""
    )

    with pytest.raises(ConfigurationError, match="present on every §I example"):
        load_scenarios_for_runbook(runbook)


def test_load_scenarios_returns_empty_for_empty_i_without_fixture_directory(
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

    assert load_scenarios_for_runbook(runbook, tmp_path / "scenarios") == []


def test_normal_mode_ignores_conflicting_fixture_yaml(tmp_path: Path) -> None:
    scenario_root = tmp_path / "infisical-secrets"
    scenario_root.mkdir(parents=True)
    (scenario_root / "I-01.yaml").write_text(
        """id: I-01
runbook: infisical-secrets.md
type: ambiguous
refs: [obsolete:AG]
scenario: Dispatch the retired AG and MP behavior from the stale fixture.
expected_answers:
  - kind: classification
    label: USE_RETIRED_DEEPSEEK
weight: 1.0
"""
    )

    scenarios = load_scenarios_for_runbook(
        FIXTURES_DIR / "conformant.md", tmp_path
    )

    assert len(scenarios) == 12
    assert scenarios[0].type == "operate"
    assert scenarios[0].refs == ["E-01"]
    assert "retired" not in scenarios[0].scenario_prose
    assert scenarios[0].expected_answers[0]["tool"] == "infisical secrets get"


def test_load_scenarios_rejects_malformed_inline_schema(tmp_path: Path) -> None:
    runbook = tmp_path / "malformed.md"
    runbook.write_text(
        """## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: This scenario deliberately lacks its expected answer payload.
```
"""
    )

    with pytest.raises(ConfigurationError, match="schema validation"):
        load_scenarios_for_runbook(runbook)


def test_load_scenarios_rejects_malformed_inline_yaml(tmp_path: Path) -> None:
    runbook = tmp_path / "malformed-yaml.md"
    runbook.write_text(
        """## §I. Acceptance Criteria

```yaml acceptance
scenario_set: []
scenario_set: []
```
"""
    )

    with pytest.raises(ConfigurationError, match="missing or malformed"):
        load_scenarios_for_runbook(runbook)


def test_load_scenarios_rejects_duplicate_inline_ids(tmp_path: Path) -> None:
    runbook = tmp_path / "duplicate.md"
    runbook.write_text(
        """## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: The first sufficiently detailed acceptance scenario for the harness.
    expected_answers:
      - kind: classification
        label: CURRENT
  - id: I-01
    type: isolate
    refs: [F-01]
    scenario: The second sufficiently detailed acceptance scenario for the harness.
    expected_answers:
      - kind: classification
        label: DUPLICATE
```
"""
    )

    with pytest.raises(ConfigurationError, match="duplicate scenario id: I-01"):
        load_scenarios_for_runbook(runbook)


def test_default_scenarios_dir_never_falls_back_to_tests(tmp_path: Path) -> None:
    stale_fixture = tmp_path / "tests" / "fixtures" / "harness_scenarios"
    stale_fixture.mkdir(parents=True)
    (stale_fixture / "obsolete.yaml").write_text("obsolete: true\n")

    resolved = _default_scenarios_dir(tmp_path)

    assert resolved == tmp_path / "harness" / "scenarios"
    assert "tests" not in resolved.relative_to(tmp_path).parts
