from pathlib import Path

from runbook_tools.harness.loader import Scenario
from runbook_tools.harness.runner import Response
from runbook_tools.harness.scorer import score_response, score_tool_call, score_human_action, score_classification


def test_tool_call_exact_match() -> None:
    response = Response(kind="tool_call", tool="infisical secrets get", arguments={"project-id": "p1", "env": "prod", "path": "x"})
    expected = {"kind": "tool_call", "tool": "infisical secrets get", "argument_keys": ["project-id", "env", "path"]}

    assert score_tool_call(response, expected) == (1.0, "exact_match")


def test_tool_call_partial_value() -> None:
    response = Response(kind="tool_call", tool="infisical secrets get", arguments={"project-id": "p1", "env": "staging", "path": "x"})
    expected = {
        "kind": "tool_call",
        "tool": "infisical secrets get",
        "argument_keys": ["project-id", "env", "path"],
        "argument_values": {"env": "prod"},
    }

    assert score_tool_call(response, expected) == (0.5, "partial_value_match")


def test_tool_call_argkey_mismatch() -> None:
    response = Response(kind="tool_call", tool="infisical secrets get", arguments={"env": "prod", "path": "x"})
    expected = {"kind": "tool_call", "tool": "infisical secrets get", "argument_keys": ["project-id", "env", "path"]}

    assert score_tool_call(response, expected) == (0.5, "arg_keyset_mismatch")


def test_tool_call_tool_mismatch() -> None:
    response = Response(kind="tool_call", tool="infisical audit sync", arguments={"project-id": "p1", "env": "prod"})
    expected = {"kind": "tool_call", "tool": "infisical secrets get", "argument_keys": ["project-id", "env", "path"]}

    assert score_tool_call(response, expected) == (0.0, "tool_mismatch")


def test_best_score_semantics() -> None:
    scenario = Scenario(
        id="I-01",
        type="operate",
        refs=["E-01"],
        scenario_prose="test",
        expected_answers=[
            {"kind": "tool_call", "tool": "infisical secrets get", "argument_keys": ["project-id", "env"]},
            {"kind": "tool_call", "tool": "infisical secrets get", "argument_keys": ["project-id", "env", "path"]},
        ],
        weight=1.0,
        runbook=Path("tests/fixtures/conformant.md"),
    )
    response = Response(kind="tool_call", tool="infisical secrets get", arguments={"project-id": "p1", "env": "prod", "path": "x"})

    assert score_response(response, scenario) == (1.0, 1, "exact_match")


def test_human_action_exact() -> None:
    response = Response(kind="human_action", verb="compare", object="environment selection", target="prod versus staging request context")
    expected = {"kind": "human_action", "verb": "compare", "object": "environment selection", "target": "prod versus staging request context"}

    assert score_human_action(response, expected) == (1.0, "exact_match")


def test_human_action_target_differs() -> None:
    response = Response(kind="human_action", verb="compare", object="environment selection", target="frontend request context")
    expected = {"kind": "human_action", "verb": "compare", "object": "environment selection", "target": "prod versus staging request context"}

    assert score_human_action(response, expected) == (0.5, "target_mismatch")


def test_canonical_verbs_restart_matches_reboot() -> None:
    response = Response(kind="human_action", verb="reboot", object="gateway", target="edge gateway")
    expected = {"kind": "human_action", "verb": "restart", "object": "gateway", "target": "edge gateway"}

    assert score_human_action(response, expected) == (1.0, "exact_match")


def test_classification_exact() -> None:
    response = Response(kind="classification", verdict="REVIEW")
    expected = {"kind": "classification", "label": "REVIEW"}

    assert score_classification(response, expected) == (1.0, "exact_match")


def test_classification_mismatch() -> None:
    response = Response(kind="classification", verdict="SAFE")
    expected = {"kind": "classification", "label": "REVIEW"}

    assert score_classification(response, expected) == (0.0, "verdict_mismatch")


def test_off_path_tool_use_zero_score() -> None:
    scenario = Scenario(
        id="I-01",
        type="operate",
        refs=["E-01"],
        scenario_prose="test",
        expected_answers=[{"kind": "tool_call", "tool": "infisical secrets get", "argument_keys": ["project-id", "env", "path"]}],
        weight=1.0,
        runbook=Path("tests/fixtures/conformant.md"),
    )
    response = Response(
        kind="tool_call",
        tool="infisical secrets get",
        arguments={"project-id": "p1", "env": "prod", "path": "x"},
        tool_use_trace=[{"tool": "Read", "arguments": {"path": "/tmp/not-the-runbook.md"}}],
    )

    assert score_response(response, scenario) == (0.0, None, "off_path_tool_use")

