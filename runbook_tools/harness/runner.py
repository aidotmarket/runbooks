from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from runbook_tools.harness.loader import Scenario
from runbook_tools.harness.prompts import SYSTEM_PROMPT


@dataclass(slots=True)
class Response:
    kind: str
    tool: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    verb: str | None = None
    object: str | None = None
    target: str | None = None
    verdict: str | None = None
    label: str | None = None
    error: str | None = None
    raw_response: Any = None
    tool_use_trace: list[dict[str, Any]] | None = None


def dispatch_for_scenario(scenario: Scenario, runbook_path: Path, council_request_fn) -> Response:
    prompt = _build_scenario_prompt(scenario, runbook_path)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            council_request_fn,
            agent="mp",
            task=prompt,
            allowed_tools=["Read", "Grep", "Glob", "LS"],
        )
        try:
            raw = future.result(timeout=180)
        except FuturesTimeoutError:
            return Response(kind="SCENARIO_TIMEOUT", error=f"scenario {scenario.id} exceeded 180s")

    payload, tool_use_trace = _normalize_council_response(raw)
    try:
        parsed = payload if isinstance(payload, dict) else json.loads(str(payload))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return Response(kind="INVALID_RESPONSE", error=f"invalid JSON response: {exc}", raw_response=raw, tool_use_trace=tool_use_trace)

    return Response(
        kind=str(parsed.get("kind", "INVALID_RESPONSE")),
        tool=parsed.get("tool"),
        arguments=dict(parsed.get("arguments", {}) or {}),
        verb=parsed.get("verb"),
        object=parsed.get("object"),
        target=parsed.get("target"),
        verdict=parsed.get("verdict"),
        label=parsed.get("label"),
        raw_response=raw,
        tool_use_trace=tool_use_trace,
    )


def has_off_path_tool_use(response: Response, runbook_path: Path) -> bool:
    if not response.tool_use_trace:
        return False

    allowed_path = runbook_path.resolve()
    for event in response.tool_use_trace:
        for candidate in _iter_paths(event):
            try:
                resolved = Path(candidate).expanduser().resolve()
            except OSError:
                continue
            if resolved != allowed_path:
                return True
    return False


def _build_scenario_prompt(scenario: Scenario, runbook_path: Path) -> str:
    refs = ", ".join(scenario.refs)
    return (
        SYSTEM_PROMPT.replace("<runbook_path>", str(runbook_path.resolve())).rstrip()
        + "\n\n"
        + f"Scenario refs: {refs}\n"
        + f"Scenario type: {scenario.type}\n"
        + f"Scenario:\n{scenario.scenario_prose.strip()}\n"
        + "Return the first action as exactly one JSON object."
    )


def _normalize_council_response(raw: Any) -> tuple[Any, list[dict[str, Any]] | None]:
    if isinstance(raw, dict):
        payload = raw.get("response", raw.get("output", raw.get("text", raw)))
        trace = raw.get("tool_use_trace")
        return payload, trace if isinstance(trace, list) else None
    if hasattr(raw, "output_text"):
        trace = getattr(raw, "tool_use_trace", None)
        return getattr(raw, "output_text"), trace if isinstance(trace, list) else None
    if hasattr(raw, "text"):
        trace = getattr(raw, "tool_use_trace", None)
        return getattr(raw, "text"), trace if isinstance(trace, list) else None
    return raw, None


def _iter_paths(value: Any) -> list[str]:
    if isinstance(value, dict):
        collected: list[str] = []
        for key, child in value.items():
            if key in {"path", "file", "filepath"} and isinstance(child, str):
                collected.append(child)
            elif key in {"paths", "files"} and isinstance(child, list):
                collected.extend(str(item) for item in child if isinstance(item, str))
            else:
                collected.extend(_iter_paths(child))
        return collected
    if isinstance(value, list):
        collected: list[str] = []
        for item in value:
            collected.extend(_iter_paths(item))
        return collected
    return []

