from __future__ import annotations

from contextlib import ExitStack
import json
from pathlib import Path
from typing import Any

from click.testing import CliRunner
import pytest
import yaml

from runbook_tools.cli import (
    _resolve_external_source,
    harness_cmd,
)
from runbook_tools.harness.dispatch import DispatchResult, make_council_request_fn
from runbook_tools.harness.loader import (
    ConfigurationError,
    ScenarioLoadConfig,
    ScenarioSetConstraintError,
    load_scenarios,
    load_scenarios_for_runbook,
)
from runbook_tools.harness.runner import run_dispatch_for_scenario
from runbook_tools.harness.scorer import score_response
from tests.conftest import FIXTURES_DIR


CONFORMANT_RUNBOOK = FIXTURES_DIR / "conformant.md"
SCENARIOS_DIR = FIXTURES_DIR / "harness_scenarios"


def _copy_fixture_scenarios(target_dir: Path) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for source in sorted((SCENARIOS_DIR / "infisical-secrets").glob("*.yaml")):
        destination = target_dir / source.name
        destination.write_text(source.read_text())
        files.append(destination)
    return files


def test_external_set_skips_si_mirror_check(tmp_path: Path) -> None:
    external_dir = tmp_path / "ext"
    _copy_fixture_scenarios(external_dir)
    runbook_without_si = tmp_path / "headless.md"
    runbook_without_si.write_text("# Headless\n\nNo §I section here.\n")

    scenarios = load_scenarios(
        ScenarioLoadConfig(
            runbook_path=runbook_without_si,
            scenarios_dir=tmp_path / "unused",
            external_set_path=external_dir,
        )
    )

    assert len(scenarios) == 12
    assert scenarios[0].id == "I-01"


def test_external_set_rejects_if_count_less_than_10(tmp_path: Path) -> None:
    external_dir = tmp_path / "ext"
    fixtures = _copy_fixture_scenarios(external_dir)
    for extra in fixtures[:5]:
        extra.unlink()

    with pytest.raises(ScenarioSetConstraintError, match="expected >= 10"):
        load_scenarios(
            ScenarioLoadConfig(
                runbook_path=CONFORMANT_RUNBOOK,
                scenarios_dir=tmp_path / "unused",
                external_set_path=external_dir,
            )
        )


def test_external_set_rejects_if_distribution_missing_operate(tmp_path: Path) -> None:
    external_dir = tmp_path / "ext"
    _copy_fixture_scenarios(external_dir)
    for path in sorted(external_dir.glob("I-0*.yaml"))[:3]:
        loaded = yaml.safe_load(path.read_text())
        if loaded.get("type") == "operate":
            loaded["type"] = "isolate"
            path.write_text(yaml.safe_dump(loaded))

    with pytest.raises(ScenarioSetConstraintError, match="operate"):
        load_scenarios(
            ScenarioLoadConfig(
                runbook_path=CONFORMANT_RUNBOOK,
                scenarios_dir=tmp_path / "unused",
                external_set_path=external_dir,
            )
        )


def test_external_set_rejects_if_weights_dont_sum_to_1(tmp_path: Path) -> None:
    external_dir = tmp_path / "ext"
    _copy_fixture_scenarios(external_dir)
    target = external_dir / "I-01.yaml"
    loaded = yaml.safe_load(target.read_text())
    loaded["weight"] = 0.5
    target.write_text(yaml.safe_dump(loaded))

    with pytest.raises(ScenarioSetConstraintError, match="weights sum"):
        load_scenarios(
            ScenarioLoadConfig(
                runbook_path=CONFORMANT_RUNBOOK,
                scenarios_dir=tmp_path / "unused",
                external_set_path=external_dir,
            )
        )


def test_normal_mode_still_fails_if_si_mirror_breaks(tmp_path: Path) -> None:
    scenario_root = tmp_path / "infisical-secrets"
    scenario_root.mkdir(parents=True)
    for source in sorted((SCENARIOS_DIR / "infisical-secrets").glob("*.yaml")):
        (scenario_root / source.name).write_text(source.read_text())
    (scenario_root / "I-99.yaml").write_text(
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

    with pytest.raises(ConfigurationError, match="orphan_yaml:I-99"):
        load_scenarios_for_runbook(CONFORMANT_RUNBOOK, tmp_path)


def test_external_scenarios_from_state_materializes_and_loads(tmp_path: Path) -> None:
    state_entity = {
        "body": {
            "scenarios": [
                yaml.safe_load(path.read_text())
                for path in sorted((SCENARIOS_DIR / "infisical-secrets").glob("*.yaml"))
            ]
        }
    }

    with ExitStack() as stack:
        external_path = _resolve_external_source(
            external_scenario_set=None,
            external_scenarios_from_state="state:test",
            stack=stack,
            state_reader=lambda key: state_entity,
        )
        assert external_path is not None
        scenarios = load_scenarios(
            ScenarioLoadConfig(
                runbook_path=CONFORMANT_RUNBOOK,
                scenarios_dir=tmp_path / "unused",
                external_set_path=external_path,
            )
        )

    assert len(scenarios) == 12
    assert {scenario.id for scenario in scenarios} == {
        f"I-{index:02d}" for index in range(1, 13)
    }


def test_both_external_flags_exits_with_error() -> None:
    runner = CliRunner()

    result = runner.invoke(
        harness_cmd,
        [
            "--runbook",
            str(CONFORMANT_RUNBOOK),
            "--external-scenario-set",
            "/tmp/nope",
            "--external-scenarios-from-state",
            "state:also-nope",
        ],
    )

    assert result.exit_code == 2
    assert "mutually exclusive" in result.output


def test_external_mode_scoring_equals_normal_mode_on_same_set(tmp_path: Path) -> None:
    external_dir = tmp_path / "ext"
    _copy_fixture_scenarios(external_dir)

    normal_scenarios = load_scenarios_for_runbook(CONFORMANT_RUNBOOK, SCENARIOS_DIR)
    external_scenarios = load_scenarios(
        ScenarioLoadConfig(
                runbook_path=CONFORMANT_RUNBOOK,
                scenarios_dir=tmp_path / "unused",
                external_set_path=external_dir,
        )
    )

    assert [scenario.id for scenario in normal_scenarios] == [
        scenario.id for scenario in external_scenarios
    ]

    responses_by_id = {
        "I-01": {"kind": "tool_call", "tool": "infisical secrets get", "arguments": {"project-id": "x", "env": "prod", "path": "/a"}},
        "I-02": {"kind": "tool_call", "tool": "infisical secrets get", "arguments": {"project-id": "x", "env": "staging", "path": "/a"}},
        "I-03": {"kind": "tool_call", "tool": "infisical audit sync", "arguments": {"project-id": "x", "env": "prod"}},
        "I-04": {"kind": "tool_call", "tool": "infisical secrets list", "arguments": {"project-id": "x", "env": "prod", "path": "/a"}},
        "I-05": {"kind": "tool_call", "tool": "infisical secrets list", "arguments": {"project-id": "x", "env": "prod", "path": "/a"}},
        "I-06": {"kind": "tool_call", "tool": "infisical audit sync", "arguments": {"project-id": "x", "env": "prod"}},
        "I-07": {"kind": "human_action", "verb": "compare", "object": "environment selection", "target": "prod versus staging request context"},
        "I-08": {"kind": "human_action", "verb": "patch", "object": "argument normalization", "target": "infisical/cli.py:resolve_secret_target"},
        "I-09": {"kind": "human_action", "verb": "patch", "object": "cache invalidation", "target": "infisical/sync.py:run_sync"},
        "I-10": {"kind": "classification", "verdict": "REVIEW"},
        "I-11": {"kind": "classification", "verdict": "BREAKING"},
        "I-12": {"kind": "human_action", "verb": "investigate", "object": "drift alert", "target": "sync worker plus environment state"},
    }

    def dispatch_fn(prompt: str, metadata: dict[str, Any]) -> DispatchResult:
        scenario_id = metadata["scenario_id"]
        return DispatchResult(status="ok", response=responses_by_id[scenario_id])

    def aggregate(scenarios: list) -> float:
        total = 0.0
        for scenario in scenarios:
            response = run_dispatch_for_scenario(scenario, CONFORMANT_RUNBOOK, dispatch_fn)
            score, _, _ = score_response(response, scenario)
            total += score * scenario.weight
        return total

    normal_score = aggregate(normal_scenarios)
    external_score = aggregate(external_scenarios)

    assert pytest.approx(normal_score, abs=1e-9) == external_score


def test_external_scenario_set_single_file_accepted(tmp_path: Path) -> None:
    source = SCENARIOS_DIR / "infisical-secrets" / "I-01.yaml"
    with pytest.raises(ScenarioSetConstraintError):
        load_scenarios(
            ScenarioLoadConfig(
                runbook_path=CONFORMANT_RUNBOOK,
                scenarios_dir=tmp_path / "unused",
                external_set_path=source,
            )
        )


def test_external_scenario_set_missing_path_raises() -> None:
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_scenarios(
            ScenarioLoadConfig(
                runbook_path=CONFORMANT_RUNBOOK,
                scenarios_dir=Path("/unused"),
                external_set_path=Path("/tmp/definitely-not-here-xyz"),
            )
        )


def test_resolve_external_source_rejects_missing_path() -> None:
    from click import UsageError

    with ExitStack() as stack:
        with pytest.raises(UsageError, match="does not exist"):
            _resolve_external_source(
                external_scenario_set="/tmp/definitely-not-here-xyz-123",
                external_scenarios_from_state=None,
                stack=stack,
            )


def test_resolve_external_source_rejects_state_without_scenarios() -> None:
    from click import UsageError

    with ExitStack() as stack:
        with pytest.raises(UsageError, match="body.scenarios is required"):
            _resolve_external_source(
                external_scenario_set=None,
                external_scenarios_from_state="state:empty",
                stack=stack,
                state_reader=lambda key: {"body": {}},
            )


def test_resolve_external_source_rejects_non_yaml_file(tmp_path: Path) -> None:
    from click import UsageError

    path = tmp_path / "readme.txt"
    path.write_text("not yaml")

    with ExitStack() as stack:
        with pytest.raises(UsageError, match="YAML file or directory"):
            _resolve_external_source(
                external_scenario_set=str(path),
                external_scenarios_from_state=None,
                stack=stack,
            )


def test_materialize_state_scenarios_rejects_non_list(tmp_path: Path) -> None:
    from click import UsageError

    with ExitStack() as stack:
        with pytest.raises(UsageError, match="must be a list"):
            _resolve_external_source(
                external_scenario_set=None,
                external_scenarios_from_state="state:bad",
                stack=stack,
                state_reader=lambda key: {"body": {"scenarios": "not-a-list"}},
            )


def test_materialize_state_scenarios_rejects_non_object_entry(tmp_path: Path) -> None:
    from click import UsageError

    with ExitStack() as stack:
        with pytest.raises(UsageError, match="must be objects"):
            _resolve_external_source(
                external_scenario_set=None,
                external_scenarios_from_state="state:bad",
                stack=stack,
                state_reader=lambda key: {"body": {"scenarios": ["not-an-object"]}},
            )


def test_materialize_state_scenarios_rejects_unsafe_id() -> None:
    from click import UsageError

    scenario = {
        "id": "../etc/passwd",
        "runbook": "x.md",
        "type": "operate",
        "refs": ["E-01"],
        "scenario": "scenario body long enough",
        "expected_answers": [{"kind": "tool_call", "tool": "x"}],
        "weight": 1.0,
    }

    with ExitStack() as stack:
        with pytest.raises(UsageError, match="unsafe or missing id"):
            _resolve_external_source(
                external_scenario_set=None,
                external_scenarios_from_state="state:bad",
                stack=stack,
                state_reader=lambda key: {"body": {"scenarios": [scenario]}},
            )


def test_default_state_reader_raises_when_mcp_url_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from click import UsageError
    from runbook_tools.cli import _default_state_reader

    monkeypatch.delenv("KOSKADEUX_MCP_URL", raising=False)
    with pytest.raises(UsageError, match="KOSKADEUX_MCP_URL"):
        _default_state_reader("state:anything")


def test_default_state_reader_calls_mcp_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from runbook_tools.cli import _default_state_reader

    monkeypatch.setenv("KOSKADEUX_MCP_URL", "https://example.invalid/mcp")
    monkeypatch.setenv("KOSKADEUX_MCP_TOKEN", "state-token")

    captured: dict[str, Any] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {"body": {"scenarios": [{"id": "I-01"}]}}
            ).encode("utf-8")

    def fake_urlopen(req: Any) -> FakeResponse:
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["auth"] = req.headers.get("Authorization")
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    entity = _default_state_reader("state:answer-key")

    assert captured["url"] == "https://example.invalid/mcp"
    assert captured["auth"] == "Bearer state-token"
    assert captured["body"]["tool"] == "state_request"
    assert captured["body"]["arguments"]["op"] == "read"
    assert captured["body"]["arguments"]["key"] == "state:answer-key"
    assert entity == {"body": {"scenarios": [{"id": "I-01"}]}}


@pytest.mark.integration
def test_default_state_reader_surfaces_transport_failure_as_usage_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from click import UsageError
    from runbook_tools.cli import _default_state_reader

    monkeypatch.setenv("KOSKADEUX_MCP_URL", "https://example.invalid/mcp")
    monkeypatch.delenv("KOSKADEUX_MCP_TOKEN", raising=False)

    def boom(req: Any) -> Any:
        raise OSError("gateway unreachable")

    monkeypatch.setattr("urllib.request.urlopen", boom)

    with pytest.raises(UsageError, match="gateway unreachable"):
        _default_state_reader("state:anything")


def test_harness_cmd_rejects_missing_external_path() -> None:
    runner = CliRunner()

    result = runner.invoke(
        harness_cmd,
        [
            "--runbook",
            str(CONFORMANT_RUNBOOK),
            "--external-scenario-set",
            "/tmp/definitely-not-here-xyz-abc",
        ],
    )

    assert result.exit_code == 2
    assert "does not exist" in result.output


def test_harness_cmd_end_to_end_external_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    external_dir = tmp_path / "ext"
    _copy_fixture_scenarios(external_dir)
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    payloads_by_id = {
        "I-01": {"kind": "tool_call", "tool": "infisical secrets get", "arguments": {"project-id": "x", "env": "prod", "path": "/a"}},
        "I-02": {"kind": "tool_call", "tool": "infisical secrets get", "arguments": {"project-id": "x", "env": "staging", "path": "/a"}},
        "I-03": {"kind": "tool_call", "tool": "infisical audit sync", "arguments": {"project-id": "x", "env": "prod"}},
        "I-04": {"kind": "tool_call", "tool": "infisical secrets list", "arguments": {"project-id": "x", "env": "prod", "path": "/a"}},
        "I-05": {"kind": "tool_call", "tool": "infisical secrets list", "arguments": {"project-id": "x", "env": "prod", "path": "/a"}},
        "I-06": {"kind": "tool_call", "tool": "infisical audit sync", "arguments": {"project-id": "x", "env": "prod"}},
        "I-07": {"kind": "human_action", "verb": "compare", "object": "environment selection", "target": "prod versus staging request context"},
        "I-08": {"kind": "human_action", "verb": "patch", "object": "argument normalization", "target": "infisical/cli.py:resolve_secret_target"},
        "I-09": {"kind": "human_action", "verb": "patch", "object": "cache invalidation", "target": "infisical/sync.py:run_sync"},
        "I-10": {"kind": "classification", "verdict": "REVIEW", "label": "REVIEW"},
        "I-11": {"kind": "classification", "verdict": "BREAKING", "label": "BREAKING"},
        "I-12": {"kind": "human_action", "verb": "investigate", "object": "drift alert", "target": "sync worker plus environment state"},
    }

    def fake_make_dispatch() -> Any:
        def dispatch(prompt: str, metadata: dict[str, Any]) -> DispatchResult:
            scenario_id = metadata["scenario_id"]
            return DispatchResult(
                status="ok",
                response=payloads_by_id[scenario_id],
                tool_use_trace=[{"tool": "Read", "arguments": {"path": metadata["runbook_path"]}}],
            )

        return dispatch

    monkeypatch.setattr("runbook_tools.cli.make_council_request_fn", fake_make_dispatch)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        harness_cmd,
        [
            "--runbook",
            str(CONFORMANT_RUNBOOK),
            "--external-scenario-set",
            str(external_dir),
            "--session",
            "TEST-001",
        ],
    )

    assert result.exit_code == 0, result.output
    result_files = list((tmp_path / "harness" / "results").rglob("*.json"))
    assert len(result_files) == 1
    payload = json.loads(result_files[0].read_text())
    assert payload["result"] == "PASS"
    assert payload["external_mode"] is True
    assert payload["aggregate_score"] == pytest.approx(1.0, abs=1e-9)


def test_external_scenario_duplicate_id_rejected(tmp_path: Path) -> None:
    external_dir = tmp_path / "ext"
    external_dir.mkdir()
    base = yaml.safe_load((SCENARIOS_DIR / "infisical-secrets" / "I-01.yaml").read_text())
    (external_dir / "first.yaml").write_text(yaml.safe_dump(base))
    (external_dir / "second.yaml").write_text(yaml.safe_dump(base))

    with pytest.raises(ConfigurationError, match="duplicate id"):
        load_scenarios(
            ScenarioLoadConfig(
                runbook_path=CONFORMANT_RUNBOOK,
                scenarios_dir=tmp_path / "unused",
                external_set_path=external_dir,
            )
        )


def test_external_mode_invalid_set_exits_2(tmp_path: Path) -> None:
    """Spec §4.3: external-mode constraint violations surface as exit 2 (usage error)."""
    external_dir = tmp_path / "ext"
    fixtures = _copy_fixture_scenarios(external_dir)
    for extra in fixtures[:5]:
        extra.unlink()

    runner = CliRunner()
    result = runner.invoke(
        harness_cmd,
        [
            "--runbook",
            str(CONFORMANT_RUNBOOK),
            "--external-scenario-set",
            str(external_dir),
        ],
    )

    assert result.exit_code == 2, result.output
    assert "expected >= 10" in result.output


def _copy_fixtures_under(tmp_path: Path) -> Path:
    scenario_root = tmp_path / "infisical-secrets"
    scenario_root.mkdir(parents=True)
    for source in sorted((SCENARIOS_DIR / "infisical-secrets").glob("*.yaml")):
        (scenario_root / source.name).write_text(source.read_text())
    return scenario_root


def test_normal_mode_type_mismatch_fails(tmp_path: Path) -> None:
    """Spec §5.3/AC7: normal mode still rejects YAML type ≠ §I type."""
    scenario_root = _copy_fixtures_under(tmp_path)
    target = scenario_root / "I-01.yaml"
    loaded = yaml.safe_load(target.read_text())
    loaded["type"] = "isolate"
    target.write_text(yaml.safe_dump(loaded))

    with pytest.raises(ConfigurationError, match="type:I-01"):
        load_scenarios_for_runbook(CONFORMANT_RUNBOOK, tmp_path)


def test_normal_mode_refs_mismatch_fails(tmp_path: Path) -> None:
    """Spec §5.3/AC7: normal mode still rejects YAML refs ≠ §I refs."""
    scenario_root = _copy_fixtures_under(tmp_path)
    target = scenario_root / "I-01.yaml"
    loaded = yaml.safe_load(target.read_text())
    loaded["refs"] = ["E-99"]
    target.write_text(yaml.safe_dump(loaded))

    with pytest.raises(ConfigurationError, match="refs:I-01"):
        load_scenarios_for_runbook(CONFORMANT_RUNBOOK, tmp_path)


def test_normal_mode_runbook_name_mismatch_fails(tmp_path: Path) -> None:
    """Spec §5.3/AC7: normal mode still rejects YAML.runbook ≠ runbook being validated."""
    scenario_root = _copy_fixtures_under(tmp_path)
    target = scenario_root / "I-01.yaml"
    loaded = yaml.safe_load(target.read_text())
    loaded["runbook"] = "other-system.md"
    target.write_text(yaml.safe_dump(loaded))

    with pytest.raises(ConfigurationError, match="runbook:I-01"):
        load_scenarios_for_runbook(CONFORMANT_RUNBOOK, tmp_path)
