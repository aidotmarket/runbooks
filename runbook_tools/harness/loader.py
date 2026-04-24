from __future__ import annotations

from dataclasses import dataclass, field
from difflib import unified_diff
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import yaml

from runbook_tools.lint.forms import extract_i_payload
from runbook_tools.parser.sections import extract_sections, extract_yaml_frontmatter


SCENARIO_SCHEMA_PATH = Path(__file__).parent.parent.parent / "schemas" / "scenario.schema.json"

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
    scenarios_dir: Path
    external_set_path: Path | None = None


class ConfigurationError(RuntimeError):
    def __init__(self, message: str, *, diff: str | None = None) -> None:
        super().__init__(message if not diff else f"{message}\n{diff}")
        self.diff = diff


class ScenarioSetConstraintError(ConfigurationError):
    pass


def _scenario_validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCENARIO_SCHEMA_PATH.read_text()))


def load_scenarios(config: ScenarioLoadConfig) -> list[Scenario]:
    if config.external_set_path is not None:
        return _load_external_scenarios(config.runbook_path, config.external_set_path)
    return _load_authoritative_scenarios(config.runbook_path, config.scenarios_dir)


def load_scenarios_for_runbook(runbook_path: Path, scenarios_dir: Path) -> list[Scenario]:
    return load_scenarios(
        ScenarioLoadConfig(runbook_path=runbook_path, scenarios_dir=scenarios_dir)
    )


def _load_authoritative_scenarios(runbook_path: Path, scenarios_dir: Path) -> list[Scenario]:
    markdown = runbook_path.read_text()
    sections = extract_sections(markdown)
    section_i = next((section for section in sections if section.letter == "I"), None)
    payload = extract_i_payload(section_i) if section_i is not None else None
    if not isinstance(payload, dict):
        raise ConfigurationError(f"{runbook_path.name} is missing a valid §I acceptance payload")

    frontmatter = extract_yaml_frontmatter(markdown) or {}
    system_name = str(frontmatter.get("system_name") or runbook_path.stem)
    expected_runbook_name = f"{system_name}.md"
    expected_meta = {
        str(item["id"]): {
            "type": item["type"],
            "refs": list(item["refs"]),
            "weight": float(item["weight"]),
        }
        for item in payload.get("scenario_set", [])
    }

    scenario_root = scenarios_dir / system_name
    yaml_paths = sorted(scenario_root.glob("*.yaml"))
    actual_payloads: dict[str, dict[str, Any]] = {}
    validator = _scenario_validator()

    for yaml_path in yaml_paths:
        loaded = yaml.safe_load(yaml_path.read_text())
        if not isinstance(loaded, dict):
            raise ConfigurationError(f"{yaml_path} did not parse to an object")
        errors = sorted(validator.iter_errors(loaded), key=lambda error: list(error.absolute_path))
        if errors:
            messages = ", ".join(error.message for error in errors)
            raise ConfigurationError(f"{yaml_path} failed scenario schema validation: {messages}")
        actual_payloads[str(loaded["id"])] = loaded

    mismatches: list[str] = []
    expected_ids = set(expected_meta)
    actual_ids = set(actual_payloads)

    missing_ids = sorted(expected_ids - actual_ids)
    orphan_ids = sorted(actual_ids - expected_ids)
    mismatches.extend(f"missing_yaml:{scenario_id}" for scenario_id in missing_ids)
    mismatches.extend(f"orphan_yaml:{scenario_id}" for scenario_id in orphan_ids)

    for scenario_id in sorted(expected_ids & actual_ids):
        expected = expected_meta[scenario_id]
        actual = actual_payloads[scenario_id]
        if actual.get("type") != expected["type"]:
            mismatches.append(f"type:{scenario_id}: expected {expected['type']!r}, got {actual.get('type')!r}")
        if list(actual.get("refs", [])) != expected["refs"]:
            mismatches.append(f"refs:{scenario_id}: expected {expected['refs']!r}, got {actual.get('refs')!r}")
        actual_weight = float(actual.get("weight", 0.0))
        if abs(actual_weight - expected["weight"]) > 1e-9:
            mismatches.append(f"weight:{scenario_id}: §I={expected['weight']!r}, yaml={actual_weight!r}")
        if actual.get("runbook") != expected_runbook_name:
            mismatches.append(f"runbook:{scenario_id}: expected {expected_runbook_name!r}, got {actual.get('runbook')!r}")

    if mismatches:
        expected_lines = [f"{scenario_id}: {expected_meta[scenario_id]}" for scenario_id in sorted(expected_ids)]
        actual_lines = [f"{scenario_id}: {actual_payloads[scenario_id]}" for scenario_id in sorted(actual_ids)]
        diff = "\n".join(
            unified_diff(
                expected_lines,
                actual_lines,
                fromfile=f"{runbook_path.name} §I",
                tofile=str(scenario_root),
                lineterm="",
            )
        )
        mismatch_text = "\n".join(mismatches)
        raise ConfigurationError(f"Scenario configuration drift for {runbook_path.name}\n{mismatch_text}", diff=diff or None)

    return [
        Scenario(
            id=scenario_id,
            type=str(actual_payloads[scenario_id]["type"]),
            refs=list(actual_payloads[scenario_id]["refs"]),
            scenario_prose=str(actual_payloads[scenario_id]["scenario"]),
            expected_answers=list(actual_payloads[scenario_id]["expected_answers"]),
            weight=float(actual_payloads[scenario_id]["weight"]),
            runbook=runbook_path,
        )
        for scenario_id in sorted(actual_ids)
    ]


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
        loaded = yaml.safe_load(yaml_path.read_text())
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
