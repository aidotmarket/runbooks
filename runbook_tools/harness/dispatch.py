from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from functools import partial
import json
import os
import time
from typing import Any, Callable, Literal
from urllib.parse import urlparse

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

DEFAULT_SCENARIO_TIMEOUT_S = 600.0
COUNCIL_POLL_INTERVAL_S = 10.0
DEFAULT_KOSKADEUX_API_CALL_URL = "http://localhost:8765/api/call"
_PENDING_DISPATCH_STATUSES = frozenset(
    {"dispatched", "running", "queued", "pending", "in_progress"}
)
_COUNCIL_RESPONSE_KEYS = (
    "response",
    "result",
    "output",
    "text",
    "result_text",
    "structured_payload",
    "legacy_payload",
)
_FAILED_DISPATCH_STATUSES = frozenset(
    {"failed", "error", "timeout", "cancelled", "canceled", "not_found"}
)


class _CouncilDispatchError(RuntimeError):
    """The external council endpoint reported an unsuccessful dispatch."""


@dataclass(slots=True)
class DispatchResult:
    status: DispatchStatus
    response: dict[str, Any] | None = None
    raw_response: Any | None = None
    tool_use_trace: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


def make_council_request_fn(
    *,
    timeout_s: float | None = None,
    council_request: Callable[..., Any] | None = None,
) -> Callable[[str, dict[str, Any]], DispatchResult]:
    timeout_s = scenario_timeout_s(timeout_s)
    request = (
        council_request
        if council_request is not None
        else partial(_default_council_request, timeout_s=timeout_s)
    )

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

        try:
            payload, trace = _normalize_council_response(raw)
        except _CouncilDispatchError as exc:
            return DispatchResult(
                status="dispatch_failure",
                raw_response=raw,
                error=str(exc),
            )
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


def scenario_timeout_s(explicit_timeout_s: float | None = None) -> float:
    if explicit_timeout_s is not None:
        return explicit_timeout_s

    configured = os.environ.get("HARNESS_SCENARIO_TIMEOUT_S")
    if configured is None:
        return DEFAULT_SCENARIO_TIMEOUT_S
    try:
        timeout_s = float(configured)
    except ValueError:
        return DEFAULT_SCENARIO_TIMEOUT_S
    return timeout_s if timeout_s > 0 else DEFAULT_SCENARIO_TIMEOUT_S


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


def _default_council_request(
    *,
    agent: str,
    task: str,
    allowed_tools: list[str],
    timeout_s: float,
) -> Any:
    url = _council_api_call_url()
    token = os.environ.get("KOSKADEUX_MCP_TOKEN")

    deadline = time.monotonic() + timeout_s
    raw = _post_council_request(
        url,
        token,
        {
            "name": "council_request",
            "arguments": {"agent": agent, "task": task, "allowed_tools": allowed_tools},
        },
    )
    receipt = _parsed_council_payload(raw)
    if _is_completed_response(receipt):
        return _completed_council_result(raw, receipt)
    if not _is_dispatch_receipt(receipt):
        return raw

    task_id = str(receipt["task_id"])
    while True:
        remaining_s = deadline - time.monotonic()
        if remaining_s <= 0:
            raise FuturesTimeoutError()
        time.sleep(min(COUNCIL_POLL_INTERVAL_S, remaining_s))

        polled_raw = _post_council_request(
            url,
            token,
            {
                "name": "council_request",
                "arguments": {"action": "check_build", "task_id": task_id},
            },
        )
        polled = _parsed_council_payload(polled_raw)
        if polled is None:
            raise _CouncilDispatchError("check_build returned a malformed response")

        status = str(polled.get("status", "")).strip().lower()
        if status == "completed":
            return _completed_council_result(polled_raw, polled)
        if status in _PENDING_DISPATCH_STATUSES:
            continue
        if status in _FAILED_DISPATCH_STATUSES:
            error = polled.get("error") or polled.get("message") or f"task {task_id} {status}"
            raise _CouncilDispatchError(str(error))
        raise _CouncilDispatchError(
            f"check_build returned unexpected status {status!r} for task {task_id}"
        )


def _council_api_call_url() -> str:
    configured = os.environ.get("KOSKADEUX_MCP_URL")
    url = (configured or DEFAULT_KOSKADEUX_API_CALL_URL).strip()
    parsed = urlparse(url)
    host = (parsed.hostname or "").rstrip(".").lower()
    path = parsed.path.rstrip("/")
    if (
        parsed.scheme not in {"http", "https"}
        or not host
        or host == "mcp.ai.market"
        or path != "/api/call"
    ):
        raise RuntimeError(
            "KOSKADEUX_MCP_URL must target the koskadeux_server REST route; "
            f"set it to {DEFAULT_KOSKADEUX_API_CALL_URL}. MCP streamable-HTTP "
            "roots such as https://mcp.ai.market are not supported by the "
            "harness fallback."
        )
    return url


def _post_council_request(url: str, token: str | None, body: dict[str, Any]) -> Any:
    import urllib.request

    encoded_body = json.dumps(body).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=encoded_body, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _parsed_council_payload(raw: Any) -> dict[str, Any] | None:
    payload, _ = _normalize_council_response(raw)
    candidates = list(_iter_json_objects(payload))
    for candidate in candidates:
        if candidate.get("task_id") and candidate.get("status"):
            return candidate
    return candidates[0] if candidates else None


def _is_dispatch_receipt(payload: dict[str, Any] | None) -> bool:
    if payload is None or not payload.get("task_id"):
        return False
    status = str(payload.get("status", "")).strip().lower()
    return status in _PENDING_DISPATCH_STATUSES


def _is_completed_response(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    status = str(payload.get("status", "")).strip().lower()
    return status == "completed" or payload.get("cache_hit") is True


def _completed_council_result(raw: Any, payload: dict[str, Any]) -> dict[str, Any]:
    answer = _extract_structured_answer(payload)
    task_id = str(payload.get("task_id") or "unknown")
    if answer is None:
        raise _CouncilDispatchError(
            f"completed task {task_id} did not contain a structured harness answer"
        )
    _, inner_trace = _normalize_council_response(payload)
    _, outer_trace = _normalize_council_response(raw)
    completed: dict[str, Any] = {"success": True, "result": answer}
    trace = [*outer_trace, *inner_trace]
    if trace:
        completed["tool_use_trace"] = trace
    return completed


def _normalize_council_response(raw: Any) -> tuple[Any, list[dict[str, Any]]]:
    trace: list[dict[str, Any]] = []
    payload: Any = raw

    if isinstance(raw, dict):
        if "success" in raw:
            if not raw.get("success"):
                raise _CouncilDispatchError(
                    str(raw.get("error") or "council_request dispatch failed")
                )
            payload = raw.get("result")
        else:
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
    return next(_iter_json_objects(payload), None)


def _iter_json_objects(payload: Any):
    if isinstance(payload, dict):
        yield payload
        return
    if payload is None:
        return

    text = str(payload).strip()
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        parsed = None
    if isinstance(parsed, dict):
        yield parsed
        return

    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            candidate, _ = decoder.raw_decode(text[index:])
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(candidate, dict):
            yield candidate


def _extract_structured_answer(value: Any, *, depth: int = 0) -> dict[str, Any] | None:
    if depth > 10:
        return None

    for candidate in _iter_json_objects(value):
        if _matches_output_schema(candidate):
            return candidate
        for key in _COUNCIL_RESPONSE_KEYS:
            if key not in candidate:
                continue
            answer = _extract_structured_answer(candidate[key], depth=depth + 1)
            if answer is not None:
                return answer
    return None


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
