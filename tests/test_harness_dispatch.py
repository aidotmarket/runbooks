from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from runbook_tools.harness.dispatch import (
    DispatchResult,
    make_council_request_fn,
)
from runbook_tools.harness.prompts import (
    ALLOWED_TOOLS_PREAMBLE,
    READ_ONLY_PREAMBLE,
    build_harness_prompt,
)
from runbook_tools.harness.loader import Scenario


RUNBOOK_PATH = Path(__file__).parent / "fixtures" / "conformant.md"


def _scenario() -> Scenario:
    return Scenario(
        id="I-01",
        type="operate",
        refs=["E-01"],
        scenario_prose="Check the first action.",
        expected_answers=[{"kind": "tool_call", "tool": "x"}],
        weight=1.0,
        runbook=RUNBOOK_PATH,
    )


def _metadata() -> dict[str, Any]:
    return {
        "scenario_id": "I-01",
        "runbook_path": str(RUNBOOK_PATH.resolve()),
        "allowed_tools": ["Read", "Grep", "Glob", "LS"],
    }


def test_make_council_request_fn_returns_callable() -> None:
    dispatch_fn = make_council_request_fn(council_request=lambda **kwargs: "{}")

    assert callable(dispatch_fn)


def test_dispatch_happy_path_returns_json_verdict() -> None:
    payload = {"kind": "tool_call", "tool": "infisical secrets get", "arguments": {"env": "prod"}}
    dispatch_fn = make_council_request_fn(
        council_request=lambda **kwargs: json.dumps(payload)
    )

    result = dispatch_fn(build_harness_prompt(_scenario(), RUNBOOK_PATH), _metadata())

    assert isinstance(result, DispatchResult)
    assert result.status == "ok"
    assert result.response == payload


def test_dispatch_timeout_returns_status_timeout() -> None:
    def slow_request(**kwargs: Any) -> Any:
        time.sleep(0.5)
        return "{}"

    dispatch_fn = make_council_request_fn(timeout_s=0.05, council_request=slow_request)

    result = dispatch_fn("prompt", _metadata())

    assert result.status == "timeout"
    assert "0.05" in (result.error or "")


def test_dispatch_detects_write_capable_tool_usage_as_off_path() -> None:
    raw = {
        "response": json.dumps({"kind": "tool_call", "tool": "Read"}),
        "tool_use_trace": [
            {"tool": "Read", "arguments": {"path": str(RUNBOOK_PATH.resolve())}},
            {"tool": "Edit", "arguments": {"path": str(RUNBOOK_PATH.resolve())}},
        ],
    }
    dispatch_fn = make_council_request_fn(council_request=lambda **kwargs: raw)

    result = dispatch_fn("prompt", _metadata())

    assert result.status == "off_path_violation"
    assert "Edit" in (result.error or "")


def test_dispatch_malformed_json_returns_status_malformed() -> None:
    dispatch_fn = make_council_request_fn(council_request=lambda **kwargs: "not json")

    result = dispatch_fn("prompt", _metadata())

    assert result.status == "malformed"


def test_dispatch_malformed_when_parseable_but_schema_mismatch() -> None:
    dispatch_fn = make_council_request_fn(
        council_request=lambda **kwargs: json.dumps({"kind": "tool_call"})
    )

    result = dispatch_fn("prompt", _metadata())

    assert result.status == "malformed"


def test_dispatch_passes_allowed_tools_exactly_as_read_grep_glob_ls() -> None:
    captured: dict[str, Any] = {}

    def recorder(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return json.dumps({"kind": "classification", "verdict": "SAFE"})

    dispatch_fn = make_council_request_fn(council_request=recorder)

    result = dispatch_fn("prompt", _metadata())

    assert result.status == "ok"
    assert captured["allowed_tools"] == ["Read", "Grep", "Glob", "LS"]


def test_dispatch_prompt_includes_version_controlled_preamble() -> None:
    prompt = build_harness_prompt(_scenario(), RUNBOOK_PATH)

    assert prompt.startswith(READ_ONLY_PREAMBLE)
    assert ALLOWED_TOOLS_PREAMBLE in prompt
    assert "READ-ONLY" in prompt


def test_dispatch_contract_matches_parent_spec_dispatch_shape() -> None:
    captured: dict[str, Any] = {}

    def recorder(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return json.dumps({"kind": "classification", "verdict": "REVIEW"})

    prompt = build_harness_prompt(_scenario(), RUNBOOK_PATH)
    dispatch_fn = make_council_request_fn(council_request=recorder)

    dispatch_fn(prompt, _metadata())

    assert captured["agent"] == "mp"
    assert captured["task"] == prompt
    assert captured["allowed_tools"] == ["Read", "Grep", "Glob", "LS"]
    assert "mode" not in captured


def test_dispatch_failure_when_underlying_call_raises() -> None:
    def boom(**kwargs: Any) -> Any:
        raise RuntimeError("gateway unreachable")

    dispatch_fn = make_council_request_fn(council_request=boom)

    result = dispatch_fn("prompt", _metadata())

    assert result.status == "dispatch_failure"
    assert "gateway unreachable" in (result.error or "")


def test_dispatch_default_council_request_requires_mcp_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KOSKADEUX_MCP_URL", raising=False)
    dispatch_fn = make_council_request_fn()

    result = dispatch_fn("prompt", _metadata())

    assert result.status == "dispatch_failure"
    assert "KOSKADEUX_MCP_URL" in (result.error or "")


def test_dispatch_default_council_request_posts_to_configured_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KOSKADEUX_MCP_URL", "https://example.invalid/mcp")
    monkeypatch.setenv("KOSKADEUX_MCP_TOKEN", "token-xyz")

    captured: dict[str, Any] = {}

    class FakeResponse:
        def __init__(self, payload: str) -> None:
            self._payload = payload

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def read(self) -> bytes:
            return self._payload.encode("utf-8")

    def fake_urlopen(req: Any) -> FakeResponse:
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["auth"] = req.headers.get("Authorization")
        return FakeResponse(json.dumps({"response": {"kind": "classification", "verdict": "SAFE"}}))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    dispatch_fn = make_council_request_fn()
    result = dispatch_fn("prompt", _metadata())

    assert result.status == "ok"
    assert captured["url"] == "https://example.invalid/mcp"
    assert captured["auth"] == "Bearer token-xyz"
    assert captured["body"]["arguments"]["agent"] == "mp"


def test_dispatch_default_council_request_returns_text_when_not_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KOSKADEUX_MCP_URL", "https://example.invalid/mcp")
    monkeypatch.delenv("KOSKADEUX_MCP_TOKEN", raising=False)

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def read(self) -> bytes:
            return b"not-json-body"

    monkeypatch.setattr("urllib.request.urlopen", lambda req: FakeResponse())

    dispatch_fn = make_council_request_fn()
    result = dispatch_fn("prompt", _metadata())

    assert result.status == "malformed"


def test_dispatch_normalizes_response_from_output_text_attribute() -> None:
    class Obj:
        output_text = json.dumps({"kind": "classification", "verdict": "SAFE"})
        tool_use_trace = [{"tool": "Read", "arguments": {"path": str(RUNBOOK_PATH.resolve())}}]

    dispatch_fn = make_council_request_fn(council_request=lambda **kwargs: Obj())

    result = dispatch_fn("prompt", _metadata())

    assert result.status == "ok"
    assert result.response == {"kind": "classification", "verdict": "SAFE"}


def test_dispatch_normalizes_response_from_text_attribute() -> None:
    class Obj:
        text = json.dumps({"kind": "tool_call", "tool": "Read"})

    dispatch_fn = make_council_request_fn(council_request=lambda **kwargs: Obj())

    result = dispatch_fn("prompt", _metadata())

    assert result.status == "ok"


def test_dispatch_detects_non_allowed_tool_as_off_path() -> None:
    raw = {
        "response": json.dumps({"kind": "tool_call", "tool": "Read"}),
        "tool_use_trace": [{"tool": "WebFetch", "arguments": {}}],
    }
    dispatch_fn = make_council_request_fn(council_request=lambda **kwargs: raw)

    result = dispatch_fn("prompt", _metadata())

    assert result.status == "off_path_violation"
    assert "WebFetch" in (result.error or "")


def test_dispatch_detects_shell_redirection_as_off_path() -> None:
    raw = {
        "response": json.dumps({"kind": "tool_call", "tool": "Read"}),
        "tool_use_trace": [
            {"tool": "Read", "arguments": {"path": str(RUNBOOK_PATH.resolve()), "command": "echo hi > /tmp/out"}}
        ],
    }
    dispatch_fn = make_council_request_fn(council_request=lambda **kwargs: raw)

    result = dispatch_fn("prompt", _metadata())

    assert result.status == "off_path_violation"
    assert "redirection" in (result.error or "")


def test_dispatch_detects_off_path_file_event() -> None:
    raw = {
        "response": json.dumps({"kind": "tool_call", "tool": "Read"}),
        "tool_use_trace": [{"tool": "Read", "arguments": {"path": "/etc/passwd"}}],
    }
    dispatch_fn = make_council_request_fn(council_request=lambda **kwargs: raw)

    result = dispatch_fn("prompt", _metadata())

    assert result.status == "off_path_violation"
    assert "/etc/passwd" in (result.error or "")


def test_dispatch_classification_label_accepted_as_verdict() -> None:
    dispatch_fn = make_council_request_fn(
        council_request=lambda **kwargs: json.dumps({"kind": "classification", "label": "REVIEW"})
    )

    result = dispatch_fn("prompt", _metadata())

    assert result.status == "ok"


def test_dispatch_malformed_for_unknown_kind() -> None:
    dispatch_fn = make_council_request_fn(
        council_request=lambda **kwargs: json.dumps({"kind": "exotic"})
    )

    result = dispatch_fn("prompt", _metadata())

    assert result.status == "malformed"


def test_dispatch_human_action_requires_all_fields() -> None:
    dispatch_fn_ok = make_council_request_fn(
        council_request=lambda **kwargs: json.dumps(
            {"kind": "human_action", "verb": "check", "object": "status", "target": "server"}
        )
    )
    dispatch_fn_bad = make_council_request_fn(
        council_request=lambda **kwargs: json.dumps({"kind": "human_action", "verb": "check"})
    )

    assert dispatch_fn_ok("prompt", _metadata()).status == "ok"
    assert dispatch_fn_bad("prompt", _metadata()).status == "malformed"


def test_run_dispatch_for_scenario_timeout_maps_to_response() -> None:
    from runbook_tools.harness.runner import run_dispatch_for_scenario

    def timeout_dispatch(prompt: str, metadata: dict[str, Any]) -> DispatchResult:
        return DispatchResult(status="timeout", error="slow")

    response = run_dispatch_for_scenario(_scenario(), RUNBOOK_PATH, timeout_dispatch)

    assert response.kind == "SCENARIO_TIMEOUT"
    assert response.error == "slow"


def test_run_dispatch_for_scenario_off_path_maps_to_response() -> None:
    from runbook_tools.harness.runner import run_dispatch_for_scenario

    def off_path_dispatch(prompt: str, metadata: dict[str, Any]) -> DispatchResult:
        return DispatchResult(
            status="off_path_violation",
            error="Edit used",
            tool_use_trace=[{"tool": "Edit"}],
        )

    response = run_dispatch_for_scenario(_scenario(), RUNBOOK_PATH, off_path_dispatch)

    assert response.kind == "OFF_PATH_VIOLATION"
    assert response.tool_use_trace == [{"tool": "Edit"}]


def test_run_dispatch_for_scenario_malformed_maps_to_response() -> None:
    from runbook_tools.harness.runner import run_dispatch_for_scenario

    def malformed_dispatch(prompt: str, metadata: dict[str, Any]) -> DispatchResult:
        return DispatchResult(status="malformed", error="bad json")

    response = run_dispatch_for_scenario(_scenario(), RUNBOOK_PATH, malformed_dispatch)

    assert response.kind == "INVALID_RESPONSE"


def test_run_dispatch_for_scenario_dispatch_failure_maps_to_response() -> None:
    from runbook_tools.harness.runner import run_dispatch_for_scenario

    def failing_dispatch(prompt: str, metadata: dict[str, Any]) -> DispatchResult:
        return DispatchResult(status="dispatch_failure", error="boom")

    response = run_dispatch_for_scenario(_scenario(), RUNBOOK_PATH, failing_dispatch)

    assert response.kind == "INFRASTRUCTURE_FAILURE"
    assert "boom" in (response.error or "")


def test_run_dispatch_for_scenario_ok_maps_full_payload() -> None:
    from runbook_tools.harness.runner import run_dispatch_for_scenario

    def ok_dispatch(prompt: str, metadata: dict[str, Any]) -> DispatchResult:
        return DispatchResult(
            status="ok",
            response={
                "kind": "human_action",
                "verb": "restart",
                "object": "service",
                "target": "worker",
            },
        )

    response = run_dispatch_for_scenario(_scenario(), RUNBOOK_PATH, ok_dispatch)

    assert response.kind == "human_action"
    assert response.verb == "restart"
    assert response.target == "worker"


def test_dispatch_handles_list_paths_in_trace() -> None:
    raw = {
        "response": json.dumps({"kind": "tool_call", "tool": "Read"}),
        "tool_use_trace": [
            {
                "tool": "Read",
                "arguments": {
                    "paths": [str(RUNBOOK_PATH.resolve()), "/tmp/something-else"],
                },
            }
        ],
    }
    dispatch_fn = make_council_request_fn(council_request=lambda **kwargs: raw)

    result = dispatch_fn("prompt", _metadata())

    assert result.status == "off_path_violation"
