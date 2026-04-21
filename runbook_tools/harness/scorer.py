from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from runbook_tools.harness.loader import Scenario
from runbook_tools.harness.runner import Response, has_off_path_tool_use


CANONICAL_VERBS = {
    "run": ["execute", "invoke", "trigger"],
    "restart": ["reboot", "bounce", "cycle"],
    "read": ["fetch", "get", "retrieve", "look up"],
    "write": ["set", "update", "create", "push", "upload"],
    "delete": ["remove", "destroy", "clear"],
    "rotate": [],
    "escalate": ["page", "alert", "notify"],
    "verify": ["check", "confirm", "validate"],
    "search": ["grep", "find", "locate"],
}


def score_response(response: Response, scenario: Scenario) -> tuple[float, int | None, str]:
    if has_off_path_tool_use(response, scenario.runbook if isinstance(scenario.runbook, Path) else Path(scenario.runbook)):
        return 0.0, None, "off_path_tool_use"

    best_score = 0.0
    best_index: int | None = None
    best_reason = "no_match"
    for index, expected in enumerate(scenario.expected_answers):
        score, reason = _score_against_one(response, expected)
        if score > best_score:
            best_score = score
            best_index = index
            best_reason = reason
        if best_score >= 1.0:
            break
    return best_score, best_index, best_reason


def _score_against_one(response: Response, expected: dict[str, Any]) -> tuple[float, str]:
    expected_kind = expected.get("kind")
    if response.kind != expected_kind:
        return 0.0, "kind_mismatch"
    if expected_kind == "tool_call":
        return score_tool_call(response, expected)
    if expected_kind == "human_action":
        return score_human_action(response, expected)
    if expected_kind == "classification":
        return score_classification(response, expected)
    return 0.0, "unknown_expected_kind"


def score_tool_call(response: Response, expected: dict[str, Any]) -> tuple[float, str]:
    expected_tool = _normalize_tool(str(expected.get("tool", "")))
    response_tool = _normalize_tool(response.tool or "")
    if expected_tool != response_tool:
        return 0.0, "tool_mismatch"

    expected_keys = {str(key) for key in expected.get("argument_keys", [])}
    response_keys = set(response.arguments.keys())
    if expected_keys != response_keys:
        return 0.5, "arg_keyset_mismatch"

    expected_values = expected.get("argument_values") or {}
    for key, wanted in expected_values.items():
        if not _match_argument_value(response.arguments.get(key), wanted):
            return 0.5, "partial_value_match"
    return 1.0, "exact_match"


def score_human_action(response: Response, expected: dict[str, Any]) -> tuple[float, str]:
    response_verb = canonicalize_verb(response.verb or "")
    expected_verb = canonicalize_verb(str(expected.get("verb", "")))
    if response_verb != expected_verb:
        return 0.0, "verb_mismatch"

    response_object = _normalize_noun_phrase(response.object or "")
    expected_object = _normalize_noun_phrase(str(expected.get("object", "")))
    if response_object != expected_object:
        return 0.0, "object_mismatch"

    response_target = _normalize_noun_phrase(response.target or "")
    expected_target = _normalize_noun_phrase(str(expected.get("target", "")))
    if response_target != expected_target:
        return 0.5, "target_mismatch"
    return 1.0, "exact_match"


def canonicalize_verb(verb: str) -> str:
    lowered = verb.strip().lower()
    for canonical, synonyms in CANONICAL_VERBS.items():
        if lowered == canonical or lowered in synonyms:
            return canonical
    return lowered


def score_classification(response: Response, expected: dict[str, Any]) -> tuple[float, str]:
    expected_verdict = str(expected.get("verdict", expected.get("label", "")))
    response_verdict = str(response.verdict or response.label or "")
    if response_verdict == expected_verdict:
        return 1.0, "exact_match"
    return 0.0, "verdict_mismatch"


def _normalize_tool(tool: str) -> str:
    return tool.strip().lower()


def _match_argument_value(actual: Any, expected: Any) -> bool:
    actual_text = "" if actual is None else str(actual).strip()
    if isinstance(expected, str):
        stripped = expected.strip()
        if len(stripped) >= 2 and stripped.startswith("/") and stripped.endswith("/"):
            return re.search(stripped[1:-1], actual_text) is not None
        return actual_text == stripped
    if isinstance(expected, dict) and "any_of" in expected:
        return any(_match_argument_value(actual, option) for option in expected["any_of"])
    return actual == expected


def _normalize_noun_phrase(text: str) -> str:
    lowered = text.strip().lower()
    return re.sub(r"^(the|a|an)\s+", "", lowered)
