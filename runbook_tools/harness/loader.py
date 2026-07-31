from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from runbook_tools.lint.forms import extract_i_payload
from runbook_tools.parser.sections import extract_sections
from runbook_tools.strict_yaml import strict_yaml_load

SCENARIO_SCHEMA_PATH = Path(__file__).parent.parent.parent / "schemas" / "scenario.schema.json"
INLINE_SCENARIO_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent / "schemas" / "section_i_acceptance.schema.json"
)

REQUIRED_TYPE_COUNTS: dict[str, int] = {
    "operate": 3,
    "isolate": 3,
    "repair": 2,
    "evolve": 2,
    "ambiguous": 1,
}

MIN_SCENARIO_COUNT = 10
WEIGHT_SUM_TOLERANCE = 1e-3


@dataclass(slots=True)
class Scenario:
    id: str
    type: str
    refs: list[str]
    scenario_prose: str
    expected_answers: list[dict[str, Any]]
    weight: float
    runbook: Path


@dataclass(slots=True)
class ScenarioLoadConfig:
    runbook_path: Path
    # Retained as a compatibility-only input for older callers. Normal harness
    # runs never read duplicated scenario YAML; §I is the sole scenario source.
    scenarios_dir: Path | None = None
    external_set_path: Path | None = None


class ConfigurationError(RuntimeError):
    pass


class ScenarioSetConstraintError(ConfigurationError):
    pass


def _scenario_validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCENARIO_SCHEMA_PATH.read_text()))


def _inline_scenario_validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(INLINE_SCENARIO_SCHEMA_PATH.read_text()))


def load_scenarios(config: ScenarioLoadConfig) -> list[Scenario]:
    if config.external_set_path is not None:
        return _load_external_scenarios(config.runbook_path, config.external_set_path)
    return _load_inline_scenarios(config.runbook_path)


def load_scenarios_for_runbook(
    runbook_path: Path,
    scenarios_dir: Path | None = None,
) -> list[Scenario]:
    return load_scenarios(
        ScenarioLoadConfig(runbook_path=runbook_path, scenarios_dir=scenarios_dir)
    )


def _load_inline_scenarios(runbook_path: Path) -> list[Scenario]:
    markdown = runbook_path.read_text()
    section_i_matches = [
        section for section in extract_sections(markdown) if section.letter == "I"
    ]
    if len(section_i_matches) != 1:
        raise ConfigurationError(
            f"{runbook_path.name} must contain exactly one current §I acceptance section"
        )

    payload = extract_i_payload(section_i_matches[0])
    if not isinstance(payload, dict):
        raise ConfigurationError(
            f"{runbook_path.name} §I acceptance payload is missing or malformed"
        )

    errors = sorted(
        _inline_scenario_validator().iter_errors(payload),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        messages = ", ".join(error.message for error in errors)
        raise ConfigurationError(
            f"{runbook_path.name} §I failed acceptance schema validation: {messages}"
        )

    scenario_items = payload["scenario_set"]
    weight_presence = ["weight" in item for item in scenario_items]
    if any(weight_presence) and not all(weight_presence):
        raise ConfigurationError(
            f"{runbook_path.name} diagnostic weights must be present on every "
            "§I example or omitted from every example"
        )
    use_declared_weights = bool(scenario_items) and all(weight_presence)
    equal_diagnostic_weight = 1.0 / len(scenario_items) if scenario_items else 0.0
    seen_ids: set[str] = set()
    scenarios: list[Scenario] = []
    for item in scenario_items:
        scenario_id = item["id"]
        if scenario_id in seen_ids:
            raise ConfigurationError(
                f"{runbook_path.name} §I contains duplicate scenario id: {scenario_id}"
            )
        seen_ids.add(scenario_id)
        scenarios.append(
            Scenario(
                id=scenario_id,
                type=item["type"],
                refs=list(item["refs"]),
                scenario_prose=item["scenario"],
                expected_answers=deepcopy(item["expected_answers"]),
                weight=(
                    float(item["weight"])
                    if use_declared_weights
                    else equal_diagnostic_weight
                ),
                runbook=runbook_path,
            )
        )
    return scenarios


def _load_external_scenarios(runbook_path: Path, external_set_path: Path) -> list[Scenario]:
    if not external_set_path.exists():
        raise ConfigurationError(
            f"--external-scenario-set path does not exist: {external_set_path}"
        )

    if external_set_path.is_file():
        if external_set_path.suffix.lower() not in {".yaml", ".yml"}:
            raise ConfigurationError(
                f"--external-scenario-set must be a YAML file or directory: {external_set_path}"
            )
        yaml_paths = [external_set_path]
    elif external_set_path.is_dir():
        yaml_paths = sorted(
            p for p in external_set_path.iterdir()
            if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}
        )
        if not yaml_paths:
            raise ConfigurationError(
                f"--external-scenario-set directory contains no YAML files: {external_set_path}"
            )
    else:
        raise ConfigurationError(
            f"--external-scenario-set must be a YAML file or directory: {external_set_path}"
        )

    validator = _scenario_validator()
    scenarios: list[Scenario] = []
    seen_ids: set[str] = set()

    for yaml_path in yaml_paths:
        try:
            loaded = strict_yaml_load(yaml_path.read_text())
        except yaml.YAMLError as exc:
            raise ConfigurationError(f"{yaml_path} contains invalid YAML: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ConfigurationError(f"{yaml_path} did not parse to an object")
        errors = sorted(validator.iter_errors(loaded), key=lambda error: list(error.absolute_path))
        if errors:
            messages = ", ".join(error.message for error in errors)
            raise ConfigurationError(
                f"{yaml_path} failed scenario schema validation: {messages}"
            )
        scenario_id = str(loaded["id"])
        if scenario_id in seen_ids:
            raise ConfigurationError(
                f"external scenario set contains duplicate id: {scenario_id}"
            )
        seen_ids.add(scenario_id)
        scenarios.append(
            Scenario(
                id=scenario_id,
                type=str(loaded["type"]),
                refs=list(loaded["refs"]),
                scenario_prose=str(loaded["scenario"]),
                expected_answers=list(loaded["expected_answers"]),
                weight=float(loaded["weight"]),
                runbook=runbook_path,
            )
        )

    enforce_set_constraints(scenarios)
    scenarios.sort(key=lambda scenario: scenario.id)
    return scenarios


def enforce_set_constraints(scenarios: list[Scenario]) -> None:
    count = len(scenarios)
    if count < MIN_SCENARIO_COUNT:
        raise ScenarioSetConstraintError(
            f"external scenario set has {count} scenarios; expected >= {MIN_SCENARIO_COUNT}"
        )

    counts: dict[str, int] = {}
    for scenario in scenarios:
        counts[scenario.type] = counts.get(scenario.type, 0) + 1

    for scenario_type, minimum in REQUIRED_TYPE_COUNTS.items():
        actual = counts.get(scenario_type, 0)
        if actual < minimum:
            raise ScenarioSetConstraintError(
                f"external scenario set has {actual} {scenario_type} scenarios; expected >= {minimum}"
            )

    weight_sum = sum(scenario.weight for scenario in scenarios)
    if abs(weight_sum - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise ScenarioSetConstraintError(
            f"external scenario weights sum to {weight_sum:.3f}; expected 1.0 +/- {WEIGHT_SUM_TOLERANCE}"
        )
