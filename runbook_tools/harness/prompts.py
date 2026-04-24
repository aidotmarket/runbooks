from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runbook_tools.harness.loader import Scenario


PROMPT_PREAMBLE_VERSION = "1"

READ_ONLY_PREAMBLE = (
    "READ-ONLY harness review. DO NOT modify files, commit, or push."
)

ALLOWED_TOOLS_PREAMBLE = (
    "Allowed tools: Read, Grep, Glob, LS. Using any other tool is an error."
)

ALLOWED_TOOLS: tuple[str, ...] = ("Read", "Grep", "Glob", "LS")


SYSTEM_PROMPT = """You are evaluating a runbook for stateless-agent legibility. For this evaluation you
must use ONLY the Read, Grep, Glob, and LS tools, and you must restrict file access
to the single file <runbook_path>. Do not open or search other files. You have no
prior context about this system beyond what is in the runbook.

Given the scenario below, produce your first action.

Your first action is either:
  (a) a tool call - specify the tool name and argument key-value pairs
  (b) a human instruction - specify the verb, object, and target
  (c) a classification verdict (only for §H Evolve scenarios): SAFE, REVIEW, or BREAKING

Output ONLY a JSON object matching this schema:
  {"kind": "tool_call", "tool": "...", "arguments": {...}}
  OR
  {"kind": "human_action", "verb": "...", "object": "...", "target": "..."}
  OR
  {"kind": "classification", "verdict": "SAFE|REVIEW|BREAKING"}

No prose. No markdown fences. One JSON object.
"""


def build_harness_prompt(scenario: "Scenario", runbook_path: Path) -> str:
    refs = ", ".join(scenario.refs)
    body = SYSTEM_PROMPT.replace("<runbook_path>", str(runbook_path.resolve())).rstrip()
    return (
        f"{READ_ONLY_PREAMBLE}\n"
        f"{ALLOWED_TOOLS_PREAMBLE}\n\n"
        f"{body}\n\n"
        f"Scenario refs: {refs}\n"
        f"Scenario type: {scenario.type}\n"
        f"Scenario:\n{scenario.scenario_prose.strip()}\n"
        "Return the first action as exactly one JSON object."
    )
