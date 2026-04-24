# BQ-RUNBOOK-HARNESS-PRODUCTION-WIRING Gate 2

**Title:** Runbook harness production wiring - implementation spec

**Status:** Gate 2 authoring

**Parent:** `build:bq-runbook-standard`

**Blocks:** `build:bq-runbook-standard` Gate 3 Chunk 2 B1 and B2.

**Gate 1 source:** `specs/BQ-RUNBOOK-HARNESS-PRODUCTION-WIRING-GATE1.md` at commit `5a53249`, approved.

**Living State source:** `build:bq-runbook-harness-production-wiring` version 6, read on 2026-04-24.

## 1. Gate 2 scope

This Gate 2 spec elevates all six Gate 1 deliverables into a concrete implementation plan for Gate 3.

Deliverables:

- D1: Wire `council_request_fn` to Koskadeux MP dispatch.
- D2: Add `--external-scenario-set` and `--external-scenarios-from-state` CLI flags.
- D3: Add loader external-mode branching that bypasses the normal §I mirror-check.
- D4: Source external answer keys from YAML files or Living State `body.scenarios`.
- D5: Audit CI so external mode is not run in a PR-blocking lane.
- D6: Add dispatch and external-mode tests.

The implementation is a single Gate 3 chunk. MP R3 passed `chunking_buildability`; this scope is coherent as one unit because the dispatch callable, loader branch, CLI authority selection, answer-key materialization, and tests are tightly coupled around one harness entrypoint.

Normal mode remains §I-authoritative. External mode is an explicit alternate input source for hidden or reconciled evaluation sets; it does not redesign §I authority, scoring, or the Chunk 1 §6.3 dispatch contract.

Line-number verification note: every Python `file.py:N` citation in this spec was verified during authoring with `nl -ba FILE | sed -n 'Np'` or an equivalent bounded `nl -ba` read. The parent dispatch-contract source requested as frozen commit `365c198` resolves in that commit to `specs/BQ-RUNBOOK-STANDARD.md`, not the later split `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md`; the R2 dispatch lines are verified in the current approved split Chunk 1 file at lines 942-946 and are quoted below without changing the contract.

## 2. Target file inventory

Gate 3 will touch these files:

| File | Deliverable | Expected delta |
|---|---|---:|
| `runbook_tools/cli.py` | D1 replaces the `NotImplementedError` stub at `runbook_tools/cli.py:132`; D2 adds `--external-scenario-set` and `--external-scenarios-from-state` flags | +70 / -3 |
| `runbook_tools/harness/dispatch.py` | D1 new dispatch adapter: build Koskadeux callable, enforce 180s guard if adapter owns async path, normalize statuses, detect off-path tool usage, classify malformed JSON | +130 / -0 |
| `runbook_tools/harness/loader.py` | D3 external-mode branch that bypasses the normal §I mirror-check while keeping schema and set constraints | +80 / -5 |
| `runbook_tools/harness/prompts.py` | D1 version-controlled prompt preamble carrying read-only review semantics and tool restrictions | +35 / -5 |
| `runbook_tools/harness/runner.py` | D1 integrate dispatch callable and surface timeout, off-path, and malformed-response statuses if not fully contained in `dispatch.py` | +45 / -2 |
| `schemas/scenario.schema.json` | D3 external scenarios validate against the same schema; expected unchanged unless a clarifying description is needed | +0 / -0 |
| `tests/test_harness_dispatch.py` | D6 new dispatch tests | +120 / -0 |
| `tests/test_harness_external_mode.py` | D6 new external-mode tests | +130 / -0 |
| `.github/workflows/runbook-harness.yml` | D5 audit only; confirm nightly normal path and no PR-blocking external mode | +0 / -0 |

Production estimate: about +400 / -10 LOC.

Test estimate: about +200 LOC.

Total Gate 3 delta: about +600 LOC.

## 3. D1 implementation spec - wire `council_request_fn` to Koskadeux

### 3.1 Function signature

Create `runbook_tools/harness/dispatch.py` with this public factory:

```python
def make_council_request_fn(*, timeout_s: float = 180.0) -> Callable[[str, dict], DispatchResult]:
    ...
```

The returned callable must be suitable for injection into the existing harness runner.

The callable accepts:

- `prompt: str` - the complete harness prompt for one scenario.
- `metadata: dict` - optional structured context from the runner, including scenario id, runbook path, and allowed tools.

The callable returns a `DispatchResult` object. Gate 3 may implement this as a dataclass in `dispatch.py` or reuse an existing local result type if one exists by then.

Minimum `DispatchResult` fields:

- `status: Literal["ok", "timeout", "off_path_violation", "malformed", "dispatch_failure"]`
- `response: dict | None`
- `raw_response: Any | None`
- `tool_use_trace: list[dict[str, Any]]`
- `error: str | None`

The callable must be synchronous from the runner's perspective. If Koskadeux dispatch is asynchronous, the adapter owns the event loop bridge and wraps it in the same 180 second wall-clock guard.

### 3.2 Dispatch contract

The dispatch contract is the Chunk 1 §6.3 R2 shape:

```python
result = council_request(
    agent="mp",
    task=build_scenario_prompt(scenario, runbook_path),
    allowed_tools=["Read", "Grep", "Glob", "LS"],
)
```

Gate 3 must call:

```python
council_request(agent="mp", task=<prompt>, allowed_tools=["Read", "Grep", "Glob", "LS"])
```

There is no `mode` parameter. The system prompt carries review semantics.

The current runner already submits a callable with `agent="mp"`, `task=prompt`, and `allowed_tools=["Read", "Grep", "Glob", "LS"]` at `runbook_tools/harness/runner.py:32`, `runbook_tools/harness/runner.py:33`, `runbook_tools/harness/runner.py:34`, and `runbook_tools/harness/runner.py:35`. Gate 3 may either preserve that runner call shape and make `make_council_request_fn()` return a compatible callable, or tighten the runner around the new `Callable[[str, dict], DispatchResult]` signature. In either case, the actual Koskadeux invocation must remain exactly as above.

### 3.3 Prompt builder

Move prompt construction into `runbook_tools/harness/prompts.py`:

```python
def build_harness_prompt(scenario, runbook_path) -> str:
    ...
```

The returned string must include:

- System preamble: `READ-ONLY harness review. DO NOT modify files, commit, or push.`
- Tool restriction preamble: `Allowed tools: Read, Grep, Glob, LS. Using any other tool is an error.`
- Scenario context and runbook citations from loader output.
- Required JSON output schema for a parseable verdict.

The current prompt restriction surface is in `runbook_tools/harness/prompts.py:1`, `runbook_tools/harness/prompts.py:2`, and `runbook_tools/harness/prompts.py:3`, and it already ends with the one-object JSON instruction at `runbook_tools/harness/prompts.py:20`. Gate 3 must preserve those semantics while adding the explicit read-only and allowed-tools preambles.

The preamble is version-controlled. Upgrading it after Gate 3 counts as a Chunk 1 §6.3 change and is not part of Chunk 2 scope.

### 3.4 Timeout, off-path detection, and malformed JSON

Timeout:

- Enforce a 180 second wall-clock timeout per scenario.
- Use `asyncio.wait_for`, `future.result(timeout=timeout_s)`, or an equivalent wall-clock guard.
- Return `DispatchResult(status="timeout")`.
- Do not abort the whole run on one scenario timeout.

The current runner timeout guard is at `runbook_tools/harness/runner.py:38` and returns a scenario timeout at `runbook_tools/harness/runner.py:40`. Gate 3 may keep that behavior in the runner or centralize it in the dispatch adapter, but the outcome must be the same.

Off-path detection:

- Parse response metadata and tool-use traces for tool names outside `{Read, Grep, Glob, LS}`.
- Treat write-capable markers as violations, including `Edit`, `Write`, `MultiEdit`, `Bash`, `apply_patch`, `git commit`, `git push`, `rm`, and shell redirection to files.
- Retain existing path-based detection that flags tool events whose resolved path differs from the allowed runbook path.
- Return or surface `DispatchResult(status="off_path_violation")`.

Existing path-based trace scanning begins at `runbook_tools/harness/runner.py:62`, resolves the allowed path at `runbook_tools/harness/runner.py:66`, and returns true for a mismatched path at `runbook_tools/harness/runner.py:73`.

Malformed JSON:

- If the MP response is not valid JSON, return `DispatchResult(status="malformed")`.
- If JSON parses but does not match the harness output schema, return `DispatchResult(status="malformed")`.
- Preserve raw response content for result debugging.

The current malformed parse path catches JSON parse failures at `runbook_tools/harness/runner.py:44`, `runbook_tools/harness/runner.py:45`, and `runbook_tools/harness/runner.py:46`. Gate 3 must extend this from "parseable JSON" to "parseable JSON matching schema."

### 3.5 Replace the CLI stub

`runbook_tools/cli.py` currently defines `council_request_stub` at `runbook_tools/cli.py:132`, and the stub raises the scaffold-only `NotImplementedError` at `runbook_tools/cli.py:133`.

Gate 3 must replace that stub with:

```python
dispatch_fn = make_council_request_fn()
```

Then pass `dispatch_fn` into the runner for every scenario.

Acceptance evidence must include the verified line where the stub was removed and the verified line where `make_council_request_fn()` is constructed.

## 4. D2 implementation spec - CLI flags

### 4.1 `--external-scenario-set <path>`

Add a Click option to `runbook-harness`:

```text
--external-scenario-set <path>
```

Behavior:

- Accept a single YAML file.
- Accept a directory containing YAML files.
- Resolve the path before loader invocation.
- Require the path to exist.
- Treat external scenarios as authoritative.
- Bypass normal-mode §I mirror authority only when this flag is present.

Absence of this flag keeps current normal mode.

### 4.2 `--external-scenarios-from-state <entity-key>`

Add a second Click option:

```text
--external-scenarios-from-state <entity-key>
```

Behavior:

- Read the named Living State entity.
- Require `body.scenarios` to exist and be an array.
- Materialize every scenario object to a temporary YAML file in `tempfile.TemporaryDirectory()`.
- Pass that temporary directory to the loader exactly as if `--external-scenario-set <tempdir>` had been supplied.
- Clean up the temp directory after validation, run completion, or dispatch failure.

Gate 3 must inject or wrap the state reader so tests can mock it without requiring a live MCP call.

### 4.3 Error handling

Usage errors must exit with code 2:

- Both external flags passed.
- External path does not exist.
- External path is neither a YAML file nor a directory.
- Living State entity not found.
- Living State entity lacks `body.scenarios`.
- `body.scenarios` is not an array.
- Materialized state scenario fails schema validation.

Diagnostics must name the failing flag and input. Examples:

- `--external-scenario-set path does not exist: <path>`
- `--external-scenario-set must be a YAML file or directory: <path>`
- `--external-scenario-set and --external-scenarios-from-state are mutually exclusive`
- `state entity <key> body.scenarios is required for --external-scenarios-from-state`

### 4.4 Usage table

| Use case | Command |
|---|---|
| Normal self-assertion run | `runbook-harness --runbook aim-node.md --mode conformant --session SELF-ASSERT-001` |
| External directory run | `runbook-harness --runbook aim-node.md --external-scenario-set /tmp/g4-scenarios --mode conformant --session G4-001` |
| External single YAML run | `runbook-harness --runbook aim-node.md --external-scenario-set /tmp/I-01.yaml --mode conformant --session G4-001` |
| Living State sourced run | `runbook-harness --runbook aim-node.md --external-scenarios-from-state state:bq-runbook-standard:g4:aim-node:answer-key --mode conformant --session G4-001` |

## 5. D3 implementation spec - loader external-mode branch

### 5.1 Entry point

Gate 3 should introduce a loader config object:

```python
@dataclass(slots=True)
class ScenarioLoadConfig:
    runbook_path: Path
    scenarios_dir: Path
    external_set_path: Path | None = None
```

Then expose:

```python
def load_scenarios(config: ScenarioLoadConfig) -> list[Scenario]:
    ...
```

`load_scenarios_for_runbook(runbook_path, scenarios_dir)` may remain as a compatibility wrapper that calls `load_scenarios()` with `external_set_path=None`.

If `external_set_path` is set:

- Skip the §I extraction and mirror-check.
- Load scenarios from the external file or directory.
- Validate each scenario against `schemas/scenario.schema.json`.
- Enforce set constraints.
- Return the same `Scenario` objects used by normal mode.

The current normal loader reads §I and builds expected metadata at `runbook_tools/harness/loader.py:33` through `runbook_tools/harness/loader.py:51`. It reads YAML files at `runbook_tools/harness/loader.py:58`, validates schema at `runbook_tools/harness/loader.py:62`, and enters the mirror-check at `runbook_tools/harness/loader.py:68`. External mode branches before that mirror-check.

### 5.2 Constraint enforcement

External mode must enforce the same scenario-set constraints as §I:

- Count must be at least 10.
- Type distribution must include at least 3 `operate`.
- Type distribution must include at least 3 `isolate`.
- Type distribution must include at least 2 `repair`.
- Type distribution must include at least 2 `evolve`.
- Type distribution must include at least 1 `ambiguous`.
- Weights must sum to `1.0 +/- 0.001`.

Add:

```python
class ScenarioSetConstraintError(ConfigurationError):
    ...
```

Each violation raises `ScenarioSetConstraintError` with a specific reason. Example messages:

- `external scenario set has 8 scenarios; expected >= 10`
- `external scenario set has 1 operate scenarios; expected >= 3`
- `external scenario weights sum to 0.997; expected 1.0 +/- 0.001`

The schema already requires `id`, `runbook`, `type`, `refs`, `scenario`, `expected_answers`, and `weight` at `schemas/scenario.schema.json:5` through `schemas/scenario.schema.json:13`. It already constrains scenario types at `schemas/scenario.schema.json:24` through `schemas/scenario.schema.json:32`, requires at least one expected answer at `schemas/scenario.schema.json:45` through `schemas/scenario.schema.json:47`, and bounds weight at `schemas/scenario.schema.json:90` through `schemas/scenario.schema.json:93`.

### 5.3 Normal mirror-check unchanged

Normal mode must continue to perform the §I-to-YAML mirror-check.

Regression coverage must prove normal mode still fails if:

- A §I scenario id is missing from YAML.
- A YAML id is orphaned from §I.
- A type differs.
- Refs differ.
- Weight differs.
- Runbook name differs.

Existing mismatch construction starts with missing and orphan ids at `runbook_tools/harness/loader.py:72` and `runbook_tools/harness/loader.py:73`, checks type at `runbook_tools/harness/loader.py:80`, refs at `runbook_tools/harness/loader.py:82`, weight at `runbook_tools/harness/loader.py:84`, and runbook name at `runbook_tools/harness/loader.py:87`.

## 6. D4 implementation spec - external answer-key sourcing

External YAML format mirrors the per-file YAMLs used in normal mode. Each scenario file carries:

- `id`
- `runbook`
- `type`
- `refs`
- `scenario`
- `expected_answers`
- `weight`
- optional `notes`

`expected_answers` uses the same shape as normal mode. No separate answer-key file is introduced.

Living State entity format:

```json
{
  "scenarios": [
    {
      "runbook": "aim-node.md",
      "id": "I-01",
      "type": "operate",
      "refs": ["§B"],
      "scenario": "A stateless operator needs to perform the first safe action.",
      "expected_answers": [{"kind": "tool_call", "tool": "Read"}],
      "weight": 0.1
    }
  ]
}
```

Materialization rules:

- Preserve every scenario object exactly, except for YAML serialization order.
- Name files deterministically, preferably `<id>.yaml`.
- Reject duplicate ids before writing files.
- Reject ids that would produce unsafe filenames.
- Use the external-mode loader after materialization, so schema validation and set constraints are identical to file-path external mode.

## 7. D5 implementation spec - CI workflow

Audit `.github/workflows/runbook-harness.yml`.

Current finding:

- The workflow is schedule and manual-dispatch only at `.github/workflows/runbook-harness.yml:2` through `.github/workflows/runbook-harness.yml:5`.
- It installs the package at `.github/workflows/runbook-harness.yml:16`.
- It runs `runbook-lint --mode strict --update-lifecycle` at `.github/workflows/runbook-harness.yml:18`.
- It runs normal harness mode at `.github/workflows/runbook-harness.yml:23`.
- It does not pass `--external-scenario-set`.
- It does not pass `--external-scenarios-from-state`.
- It has no pull-request trigger.

Gate 3 should leave the workflow unchanged if these facts remain true. If later edits add a PR trigger before Gate 3 lands, Gate 3 must confirm that no PR-blocking workflow invokes external mode.

External mode is for ad-hoc G4-style falsifiability runs. It must not become a PR-blocking lane in this BQ.

## 8. D6 implementation spec - test plan

### 8.1 `tests/test_harness_dispatch.py`

Add eight tests:

1. `test_make_council_request_fn_returns_callable`
2. `test_dispatch_happy_path_returns_json_verdict`
3. `test_dispatch_timeout_returns_status_timeout`
4. `test_dispatch_detects_write_capable_tool_usage_as_off_path`
5. `test_dispatch_malformed_json_returns_status_malformed`
6. `test_dispatch_passes_allowed_tools_exactly_as_read_grep_glob_ls`
7. `test_dispatch_prompt_includes_version_controlled_preamble`
8. `test_dispatch_contract_matches_parent_spec_dispatch_shape`

Mock Koskadeux dispatch. Do not require live MCP credentials in unit tests.

The contract test must assert:

- `agent == "mp"`
- `task == <prompt>`
- `allowed_tools == ["Read", "Grep", "Glob", "LS"]`
- no `mode` keyword is sent

### 8.2 `tests/test_harness_external_mode.py`

Add eight tests:

1. `test_external_set_skips_si_mirror_check`
2. `test_external_set_rejects_if_count_less_than_10`
3. `test_external_set_rejects_if_distribution_missing_operate`
4. `test_external_set_rejects_if_weights_dont_sum_to_1`
5. `test_normal_mode_still_fails_if_si_mirror_breaks`
6. `test_external_scenarios_from_state_materializes_and_loads`
7. `test_both_external_flags_exits_with_error`
8. `test_external_mode_scoring_equals_normal_mode_on_same_set`

Use generated temporary runbooks and YAML files. Keep fixtures small but schema-valid. For parity, use the same scenario objects in normal mode and external mode, and assert aggregate score equality.

### 8.3 Coverage target

Gate 3 must report at least 90% coverage on new and modified harness files:

- `runbook_tools/cli.py`
- `runbook_tools/harness/dispatch.py`
- `runbook_tools/harness/loader.py`
- `runbook_tools/harness/prompts.py`
- `runbook_tools/harness/runner.py`

### 8.4 Regression

All existing harness tests must remain green.

Run at minimum:

```text
pytest tests/test_harness*.py
```

If the repo has a configured coverage command, use that command and report the modified-file coverage numbers.

## 9. Acceptance criteria for Gate 3

AC1: The `NotImplementedError` stub currently at `runbook_tools/cli.py:132` is replaced with a `make_council_request_fn()` callable, and the replacement line is verified.

AC2: `--external-scenario-set` and `--external-scenarios-from-state` exist and are mutually exclusive.

AC3: External-mode loader skips the §I mirror-check, validates against `schemas/scenario.schema.json`, and enforces set constraints.

AC4: External answer-key sourcing works for both file-path inputs and Living State entity inputs.

AC5: CI workflow audit is documented; PR-blocking lanes, if any, stay on normal path only.

AC6: Sixteen new tests are present: eight dispatch tests and eight external-mode tests. They are green, and coverage is at least 90% on modified harness files.

AC7: Regression tests confirm normal mode still performs the §I mirror-check and existing harness behavior is unbroken.

AC8: Dispatch contract exactly matches Chunk 1 §6.3 R2: `council_request(agent="mp", task=<prompt>, allowed_tools=["Read", "Grep", "Glob", "LS"])`, with no `mode` parameter.

AC9: Tool restriction via version-controlled prompt preamble, post-hoc off-path detection, and the 180 second timeout are all present.

AC10: External-mode scoring parity with normal mode is verified by a cross-mode parity test on the same scenario set.

## 10. Open questions

1. Source granularity: Gate 1 carried file vs directory vs Living State as an open question. This Gate 2 spec resolves it by requiring all three surfaces: a single YAML file, a directory of YAML files, and Living State `body.scenarios` materialized through the external path.

2. Distinct result filename for external-mode runs: unresolved. Gate 3 may keep the current writer naming if it records enough run metadata to distinguish external mode. If result ambiguity remains, add a minimal external-mode marker in the result payload before changing filename conventions.

## 11. Non-goals

- Extending MP dispatch to AG, XAI, or CC. That belongs to `BQ-COUNCIL-ALLOWED-TOOLS-CODEX-CLI` or a separate Council dispatch BQ.
- Redesigning §I authority. Parent §I stays unchanged.
- Modifying the Chunk 1 §6.3 dispatch contract.
- Changing scoring semantics.
- Adding new scenario types.
- Wiring Responses API fallback.
- Infrastructure-enforced `allowed_tools` on the Codex CLI primary path.
- Modifying `runbook_tools/*`, `schemas/*`, or `tests/*` during Gate 2 authoring.

