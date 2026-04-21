from concurrent.futures import TimeoutError as FuturesTimeoutError
import json
from pathlib import Path

import pytest

from runbook_tools.harness.loader import Scenario
from runbook_tools.harness.runner import Response, dispatch_for_scenario, has_off_path_tool_use
from runbook_tools.harness.writer import write_result


def _scenario() -> Scenario:
    return Scenario(
        id="I-01",
        type="operate",
        refs=["E-01"],
        scenario_prose="Check the first action.",
        expected_answers=[],
        weight=1.0,
        runbook=Path("tests/fixtures/conformant.md"),
    )


def test_dispatch_for_scenario_parses_string_json() -> None:
    response = dispatch_for_scenario(
        _scenario(),
        Path("tests/fixtures/conformant.md"),
        lambda **kwargs: json.dumps({"kind": "tool_call", "tool": "x", "arguments": {"env": "prod"}}),
    )

    assert response.kind == "tool_call"
    assert response.tool == "x"
    assert response.arguments == {"env": "prod"}


def test_dispatch_for_scenario_parses_dict_wrapper() -> None:
    response = dispatch_for_scenario(
        _scenario(),
        Path("tests/fixtures/conformant.md"),
        lambda **kwargs: {
            "response": {"kind": "classification", "verdict": "SAFE"},
            "tool_use_trace": [{"tool": "Read", "arguments": {"path": str(Path("tests/fixtures/conformant.md").resolve())}}],
        },
    )

    assert response.kind == "classification"
    assert response.verdict == "SAFE"
    assert response.tool_use_trace is not None


def test_dispatch_for_scenario_invalid_json() -> None:
    response = dispatch_for_scenario(
        _scenario(),
        Path("tests/fixtures/conformant.md"),
        lambda **kwargs: "not json",
    )

    assert response.kind == "INVALID_RESPONSE"
    assert "invalid JSON response" in (response.error or "")


def test_dispatch_for_scenario_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeFuture:
        def result(self, timeout):
            raise FuturesTimeoutError()

    class FakeExecutor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def submit(self, fn, **kwargs):
            return FakeFuture()

    monkeypatch.setattr("runbook_tools.harness.runner.ThreadPoolExecutor", lambda max_workers: FakeExecutor())

    response = dispatch_for_scenario(_scenario(), Path("tests/fixtures/conformant.md"), lambda **kwargs: None)

    assert response.kind == "SCENARIO_TIMEOUT"


def test_has_off_path_tool_use_false_when_same_runbook() -> None:
    runbook = Path("tests/fixtures/conformant.md").resolve()
    response = Response(kind="tool_call", tool_use_trace=[{"tool": "Read", "arguments": {"path": str(runbook)}}])

    assert has_off_path_tool_use(response, runbook) is False


def test_write_result_creates_file(tmp_path: Path) -> None:
    output = write_result(
        {
            "session_id": "S487",
            "runbook": "infisical-secrets.md",
            "run_started_at": "2026-04-22T02:00:00Z",
            "result": "PASS",
        },
        tmp_path,
    )

    assert output.exists()
    assert output.name == "S487-2026-04-22.json"
    assert json.loads(output.read_text())["result"] == "PASS"


def test_write_result_falls_back_for_bad_timestamp(tmp_path: Path) -> None:
    output = write_result(
        {
            "session_id": "S999",
            "runbook": "infisical-secrets.md",
            "run_started_at": "not-a-timestamp",
            "result": "FAIL",
        },
        tmp_path,
    )

    assert output.exists()
    assert output.name.startswith("S999-")

