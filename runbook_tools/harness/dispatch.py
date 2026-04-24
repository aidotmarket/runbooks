from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
import json
import os
from typing import Any, Callable, Literal

from runbook_tools.harness.prompts import ALLOWED_TOOLS


DispatchStatus = Literal[
    "ok",
    "timeout",
    "off_path_violation",
    "malformed",
    "dispatch_failure",
]


WRITE_CAPABLE_TOOLS: frozenset[str] = frozenset(
    {
        "Edit",
        "Write",
        "MultiEdit",
        "Bash",
        "apply_patch",
        "git commit",
        "git push",
        "rm",
    }
)


@dataclass(slots=True)
class DispatchResult:
    status: DispatchStatus
    response: dict[str, Any] | None = None
    raw_response: Any | None = None
    tool_use_trace: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


def make_council_request_fn(
    *,
    timeout_s: float = 180.0,
    council_request: Callable[..., Any] | None = None,
) -> Callable[[str, dict[str, Any]], DispatchResult]:
    request = council_request if council_request is not None else _default_council_request

    def dispatch(prompt: str, metadata: dict[str, Any] | None = None) -> DispatchResult:
        metadata = metadata or {}
        try:
            raw = _call_with_timeout(request, prompt, timeout_s)
        except FuturesTimeoutError:
            return DispatchResult(
                status="timeout",
                error=f"council_request exceeded {timeout_s:g}s wall-clock guard",
            )
        except Exception as exc:  # noqa: BLE001
            return DispatchResult(
                status="dispatch_failure",
                error=f"{type(exc).__name__}: {exc}",
            )

        payload, trace = _normalize_council_response(raw)
        violation = _detect_off_path(trace, metadata)
        if violation is not None:
            return DispatchResult(
                status="off_path_violation",
                raw_response=raw,
                tool_use_trace=trace,
                error=violation,
            )

        parsed = _parse_json_payload(payload)
        if parsed is None or not _matches_output_schema(parsed):
            return DispatchResult(
                status="malformed",
                raw_response=raw,
                tool_use_trace=trace,
                error="response is not a JSON object matching the harness output schema",
            )

        return DispatchResult(
            status="ok",
            response=parsed,
            raw_response=raw,
            tool_use_trace=trace,
        )

    return dispatch


def _call_with_timeout(
    request: Callable[..., Any],
    prompt: str,
    timeout_s: float,
) -> Any:
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(
            request,
            agent="mp",
            task=prompt,
            allowed_tools=list(ALLOWED_TOOLS),
        )
        return future.result(timeout=timeout_s)
    finally:
        # wait=False avoids the default __exit__ behavior that blocks until the
        # worker finishes — a stuck request would otherwise pin the caller past
        # timeout_s. cancel_futures drops queued work, and the leaked worker
        # thread dies with the process.
        executor.shutdown(wait=False, cancel_futures=True)


def _default_council_request(*, agent: str, task: str, allowed_tools: list[str]) -> Any:
    url = os.environ.get("KOSKADEUX_MCP_URL")
    token = os.environ.get("KOSKADEUX_MCP_TOKEN")
    if not url:
        raise RuntimeError(
            "KOSKADEUX_MCP_URL is not set; inject council_request for tests or configure the env var"
        )

    import urllib.request

    body = json.dumps(
        {
            "tool": "council_request",
            "arguments": {"agent": agent, "task": task, "allowed_tools": allowed_tools},
        }
    ).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _normalize_council_response(raw: Any) -> tuple[Any, list[dict[str, Any]]]:
    trace: list[dict[str, Any]] = []
    payload: Any = raw

    if isinstance(raw, dict):
        payload = raw.get("response", raw.get("output", raw.get("text", raw)))
        candidate = raw.get("tool_use_trace")
        if isinstance(candidate, list):
            trace = [event for event in candidate if isinstance(event, dict)]
    elif hasattr(raw, "output_text"):
        payload = getattr(raw, "output_text")
        candidate = getattr(raw, "tool_use_trace", None)
        if isinstance(candidate, list):
            trace = [event for event in candidate if isinstance(event, dict)]
    elif hasattr(raw, "text"):
        payload = getattr(raw, "text")
        candidate = getattr(raw, "tool_use_trace", None)
        if isinstance(candidate, list):
            trace = [event for event in candidate if isinstance(event, dict)]

    return payload, trace


def _detect_off_path(
    trace: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> str | None:
    allowed_path = metadata.get("runbook_path")
    allowed_resolved = None
    if allowed_path is not None:
        from pathlib import Path as _Path

        try:
            allowed_resolved = _Path(str(allowed_path)).expanduser().resolve()
        except OSError:
            allowed_resolved = None

    for event in trace:
        tool_name = str(event.get("tool", ""))
        if tool_name in WRITE_CAPABLE_TOOLS:
            return f"write-capable tool used: {tool_name}"
        if tool_name and tool_name not in ALLOWED_TOOLS:
            return f"non-allowed tool used: {tool_name}"

        arguments = event.get("arguments")
        if isinstance(arguments, dict):
            command = str(arguments.get("command", ""))
            if command:
                stripped = command.strip()
                if any(marker in stripped for marker in (" > ", " >> ", "git commit", "git push")):
                    return f"write-capable shell redirection detected: {command!r}"

        if allowed_resolved is None:
            continue
        for candidate in _iter_event_paths(event):
            from pathlib import Path as _Path

            try:
                resolved = _Path(candidate).expanduser().resolve()
            except OSError:
                continue
            if resolved != allowed_resolved:
                return f"off-path tool event: {candidate}"
    return None


def _iter_event_paths(value: Any) -> list[str]:
    if isinstance(value, dict):
        collected: list[str] = []
        for key, child in value.items():
            if key in {"path", "file", "filepath"} and isinstance(child, str):
                collected.append(child)
            elif key in {"paths", "files"} and isinstance(child, list):
                collected.extend(str(item) for item in child if isinstance(item, str))
            else:
                collected.extend(_iter_event_paths(child))
        return collected
    if isinstance(value, list):
        collected = []
        for item in value:
            collected.extend(_iter_event_paths(item))
        return collected
    return []


def _parse_json_payload(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        return payload
    if payload is None:
        return None
    try:
        parsed = json.loads(str(payload))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _matches_output_schema(parsed: dict[str, Any]) -> bool:
    kind = parsed.get("kind")
    if kind == "tool_call":
        return isinstance(parsed.get("tool"), str)
    if kind == "human_action":
        return all(isinstance(parsed.get(field), str) for field in ("verb", "object", "target"))
    if kind == "classification":
        verdict = parsed.get("verdict") or parsed.get("label")
        return isinstance(verdict, str) and verdict in {"SAFE", "REVIEW", "BREAKING"}
    return False
