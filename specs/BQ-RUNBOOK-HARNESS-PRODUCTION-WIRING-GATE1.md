# BQ-RUNBOOK-HARNESS-PRODUCTION-WIRING Gate 1

**Title:** Runbook harness production wiring - MP dispatch + external-scenario-set mode

**Status:** Gate 1 design spec - R1 authoring

**Parent:** `build:bq-runbook-standard`

**Blocks:** `BQ-RUNBOOK-STANDARD` Gate 3 Chunk 2 B1 and B2.

## 1. BQ Identity + Parent Dependency

`BQ-RUNBOOK-HARNESS-PRODUCTION-WIRING` closes the production-readiness gap left by Chunk 1's harness scaffold: the CLI path exists, but it does not yet wire the live Koskadeux MP dispatch callable, and it cannot yet consume G4 hidden evaluation sets that are external to a runbook's own §I scenario table.

The parent dependency is `build:bq-runbook-standard`. This BQ blocks `BQ-RUNBOOK-STANDARD` Gate 3 Chunk 2 B1 because the self-assertion harness requires real MP dispatch, and blocks B2 because G4 hidden evaluation requires external-scenario-set mode.

Source references for the gap:

- Chunk 1 Gate 2 explicitly scoped the harness to exact design and acceptance criteria, including scoring, §I mirror validation, CI structure, and the upstream dependency, while Gate 3 was limited to implementing the chunk's approved surface. See `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:1325`, `:1329`, `:1330`, `:1332`, and `:1335`.
- The R1 -> R2 findings show that the MP dispatch interface was corrected to the real Koskadeux shape and the Codex CLI tool-restriction limitation was documented as an upstream dependency. See `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:1405` and `:1411`.
- The current CLI still contains a stub that raises `NotImplementedError`, which makes the harness scaffold-only at the production dispatch boundary. See `runbook_tools/cli.py:132` and `:133`.

## 2. Problem Statement

There are two distinct gaps.

First, `runbook-harness` cannot perform live MP dispatch from the CLI. The CLI defines `council_request_stub` at `runbook_tools/cli.py:132`, and that stub raises `NotImplementedError("council_request_fn not wired — Chunk 1 harness is scaffold-only")` at `runbook_tools/cli.py:133`. The runner already defines the dispatch shape around `council_request_fn`, including `agent="mp"`, prompt task, allowed tools, and 180 second timeout at `runbook_tools/harness/runner.py:28`, `:32`, `:33`, `:34`, `:35`, `:38`, and `:40`, but the CLI does not supply the production callable.

Second, Chunk 2 G4 requires a hidden evaluation set authored and reconciled outside the runbook's §I self-assertion set. Chunk 2 §5.4 states that the normal Chunk 1 harness treats the runbook's own §I as authoritative and enforces a §I-to-YAML mirror, which is incompatible with hidden externally authored evaluation sets; it names `--external-scenario-set <path>` as the systemic resolution at `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-2.md:222`. The hidden set artifact is a Living State answer-key body with a `scenarios` array, materialized to temporary YAML files, then invoked through `runbook-harness --runbook aim-node.md --external-scenario-set <temp_dir> --mode conformant --session <g4-scoring-session>` per `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-2.md:231`.

This BQ closes both gaps without changing the scoring model, the §I authority model in normal mode, or the Council dispatch contract.

## 3. Scope + Non-Goals

In scope:

- Replace the CLI `NotImplementedError` dispatch stub with a production `council_request_fn` that calls Koskadeux `council_request` through the D1 contract.
- Preserve the runner-level scenario dispatch contract: harness CLI -> `council_request_fn` -> `council_request(agent="mp", task=<prompt>, allowed_tools=["Read", "Grep", "Glob", "LS"])` -> Codex CLI -> response normalization -> scoring -> result writer.
- Add `--external-scenario-set <path>` to allow a directory or single YAML file to be authoritative for scenarios instead of the runbook's own §I mirror.
- Add optional `--external-scenarios-from-state <entity-key>` to read a Living State entity body containing `scenarios`, materialize those scenario objects to temporary YAML files, and invoke the same external-mode loader path.
- Enforce external-set validation: per-scenario JSON Schema validation, set count, type distribution, and weight-sum constraints.
- Preserve normal-mode behavior, including §I-to-YAML mirror checking.

Non-goals:

- Do not change §I authority in normal mode. Normal mode remains §I authoritative and mirror-checked.
- Do not redesign harness scoring. Best-score semantics and off-path invalidation remain the Chunk 1 model.
- Do not wire Responses API fallback or infrastructure-level tool restriction. That belongs to `BQ-COUNCIL-ALLOWED-TOOLS-CODEX-CLI`, which Chunk 1 identifies as the upstream dependency at `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:967`.
- Do not add new Council members.
- Do not alter `BQ-RUNBOOK-STANDARD` specs as part of this BQ.

## 4. Architecture

### 4.1 Normal-Mode MP Dispatch Wiring

Sequence:

1. `runbook-harness` resolves target runbooks and scenario inputs.
2. In normal mode, the loader reads the runbook's §I metadata and validates that YAML files mirror that §I authority.
3. For each loaded scenario, the runner builds the scenario prompt using the version-controlled system prompt preamble.
4. The runner calls `council_request_fn(prompt, allowed_tools)` through the D1 adapter boundary. The adapter calls Koskadeux `council_request(agent="mp", task=<prompt>, allowed_tools=["Read", "Grep", "Glob", "LS"])`.
5. Koskadeux dispatches MP through the primary Codex CLI path and returns a response plus any available tool-use trace.
6. The runner normalizes the response, parses the expected JSON object, scans the trace for off-path tool use, and passes the result to the scorer.
7. The scorer returns the weighted score contribution and reason.
8. The writer persists the result JSON. The current writer derives the destination from runbook name, session id, and run date at `runbook_tools/harness/writer.py:8`, `:21`, `:22`, and `:23`.

Seams and contract boundaries:

- CLI seam: argument parsing, target resolution, external-mode selection, state-materialization option, and creation of the production `council_request_fn`.
- Dispatch seam: `council_request_fn(prompt: str, allowed_tools: list[str]) -> dict`.
- Runner seam: prompt construction, harness-side timeout, response normalization, malformed-response classification, and off-path trace scan.
- Scorer seam: maps normalized runner responses and exception classifications to scores and reasons.
- Writer seam: persists run-level result records without changing scoring semantics.

### 4.2 External-Scenario-Set Mode

External mode branches before the §I mirror-check. When `--external-scenario-set` is present, the loader treats the external YAML file or YAML directory as authoritative and does not compare those scenarios against the runbook's §I table.

Validation chain:

1. Each scenario object must validate against `schemas/scenario.schema.json`.
2. The external set must contain at least 10 scenarios.
3. The external set must satisfy type distribution: at least 3 `operate`, 3 `isolate`, 2 `repair`, 2 `evolve`, and 1 `ambiguous`.
4. The external set's weights must sum to `1.0 +/- 0.001`.

The branch is a loader contract boundary, not a new scoring path. After load and validation, external scenarios use the same dispatch, scoring, aggregation, and writer surfaces as normal scenarios.

## 5. D1 Contract Specification - Wire MP Dispatch

### 5.1 Callable Signature

The production adapter MUST expose this logical signature to the runner:

```python
def council_request_fn(prompt: str, allowed_tools: list[str]) -> dict: ...
```

The adapter maps those logical arguments to the Koskadeux invocation shape defined by Chunk 1 §6.3:

```python
council_request(
    agent="mp",
    task=prompt,
    allowed_tools=allowed_tools,
)
```

For this BQ, callers MUST pass `allowed_tools=["Read", "Grep", "Glob", "LS"]`. There is no `mode` parameter. Chunk 1 §6.3 explicitly defines `agent="mp"`, `task=build_scenario_prompt(...)`, and `allowed_tools=["Read", "Grep", "Glob", "LS"]` at `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:943`, `:944`, `:945`, and `:946`, and explicitly states that no `mode` parameter is part of the primary MP dispatch contract at `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:950`.

### 5.2 Return Shape

The callable returns a dictionary compatible with the runner's normalization seam:

```python
{
    "response": "<json-object string or dict>",
    "tool_use_trace": [
        {"tool": "Read", "arguments": {"path": "/absolute/runbook.md"}}
    ],
    "dispatch_id": "<optional provider/session id>",
    "raw": "<optional raw provider payload>"
}
```

Required keys:

- `response`: JSON object or JSON string matching the prompt output schema.

Optional keys:

- `tool_use_trace`: list of tool-call events used by post-hoc off-path detection.
- `dispatch_id`: provider or session identifier for audit correlation.
- `raw`: raw provider payload for result debugging.

### 5.3 Exceptions and Scorer Effects

The D1 adapter and runner boundary defines four error classes:

- `Timeout`: harness-side wall-clock guard exceeded for one scenario.
- `OffPath`: MP tool-use trace accessed a file outside the target runbook path.
- `MalformedResponse`: MP response could not be parsed as the required JSON object or lacked the required shape.
- `DispatchFailure`: Koskadeux dispatch failed before a scenario response could be obtained.

Scorer and CLI handling:

- `Timeout` -> scenario score `0.0`, reason `timeout`, continue to next scenario.
- `OffPath` -> scenario score `0.0`, reason `tool_violation`, continue to next scenario.
- `MalformedResponse` -> scenario score `0.0`, reason `parse_error`, continue to next scenario.
- `DispatchFailure` -> abort the run with exit code `3`; do not retry inside the harness.

Timeout contract: the harness enforces a stricter 180 second wall-clock guard per scenario. Chunk 1 §6.3 requires 180 seconds at the harness runner level and records scenario timeout while continuing at `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:952`. The runner already uses `future.result(timeout=180)` and returns a timeout response with `180s` in the error at `runbook_tools/harness/runner.py:38` and `:40`. Codex CLI may have its own longer dispatch timeout, but the harness boundary is 180 seconds.

### 5.4 Tool Restriction

Tool restriction remains prompt-based on the Codex CLI primary path. Chunk 1 §6.3 states that `allowed_tools` is enforced on the Responses API fallback path at `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:956`, ignored on the Codex CLI primary path at `:958`, and therefore relies on the system prompt as the primary restriction mechanism at `:960`.

The version-controlled restriction surface is `runbook_tools/harness/prompts.py`: it instructs MP to use only Read, Grep, Glob, and LS at `runbook_tools/harness/prompts.py:1` and `:2`, and to restrict access to the single runbook path at `runbook_tools/harness/prompts.py:3`. Post-hoc off-path detection remains in the runner. Chunk 1 requires off-path tool calls to invalidate a scenario at `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:964` and runner trace scanning currently returns true when a resolved path differs from the allowed runbook path at `runbook_tools/harness/runner.py:62`, `:66`, `:73`, and `:74`.

Infrastructure-level enforcement of `allowed_tools` on Codex CLI is out of scope for this BQ and remains tracked in `BQ-COUNCIL-ALLOWED-TOOLS-CODEX-CLI`.

## 6. D2/D3 External-Scenario-Set Mode

### 6.1 CLI Surface

Add:

```text
--external-scenario-set <path>
```

`<path>` may be either:

- a directory containing one or more YAML scenario files, or
- a single YAML scenario file.

This flag is mutually exclusive with normal §I mirror mode. In practical CLI behavior, absence of the flag means normal mode; presence of the flag means external mode and bypasses §I mirror comparison.

### 6.2 Loader Branching

The divergence point is before the normal mirror-check. The current loader builds `actual_payloads` from YAML files at `runbook_tools/harness/loader.py:55`, constructs the schema validator at `runbook_tools/harness/loader.py:56`, iterates YAML files at `:58`, schema-validates each loaded scenario at `:62` through `:65`, then compares actual payloads with expected §I metadata beginning at `runbook_tools/harness/loader.py:68`.

External mode reuses the per-file schema validation behavior but does not execute the §I comparison block that checks missing IDs, orphan IDs, type mismatches, refs, weights, and runbook name at `runbook_tools/harness/loader.py:72`, `:73`, `:80`, `:82`, `:84`, and `:87`.

### 6.3 Validation Chain

Each external scenario MUST validate against `schemas/scenario.schema.json`. The schema requires `id`, `runbook`, `type`, `refs`, `scenario`, `expected_answers`, and `weight` at `schemas/scenario.schema.json:5` through `:13`. It defines the allowed `type` enum at `schemas/scenario.schema.json:24` through `:32`, requires at least one expected answer at `schemas/scenario.schema.json:45` through `:48`, and bounds `weight` between 0.0 and 1.0 at `schemas/scenario.schema.json:90` through `:94`.

Set-level validation MUST then enforce:

- `count >= 10`
- type distribution: `operate >= 3`, `isolate >= 3`, `repair >= 2`, `evolve >= 2`, `ambiguous >= 1`
- `abs(sum(weights) - 1.0) <= 0.001`

Chunk 2 §5.4 applies the same hidden-set floor, distribution, and weight-sum constraints at `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-2.md:243`.

### 6.4 Rejection Contract

Any external-mode validation failure is a usage error:

- CLI exit code: `2`
- Exception class: `UsageError` or equivalent Click usage error
- Diagnostic: specific and actionable, naming the failing file or set-level constraint.

Examples:

- `external scenario set has 8 scenarios; expected >= 10`
- `external scenario set has 1 repair scenarios; expected >= 2`
- `external scenario weights sum to 0.93; expected 1.0 +/- 0.001`
- `<path> failed scenario schema validation: 'runbook' is a required property`

## 7. D4 Answer-Key Sourcing

External scenario YAMLs carry `expected_answers` directly, using the same shape as normal scenario YAML. Chunk 2 §5.4 requires each hidden scenario object to be a full `schemas/scenario.schema.json` conformant object, including `runbook: aim-node.md`, `id`, `type`, `refs`, scenario prose, `expected_answers`, and `weight` at `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-2.md:231`.

Add optional:

```text
--external-scenarios-from-state <entity-key>
```

Behavior:

1. Read the named Living State entity.
2. Require `entity.body.scenarios` to exist and be an array.
3. Create a `tempfile.TemporaryDirectory()` using the platform default temp root.
4. Materialize each scenario object to one YAML file in that temp directory.
5. Invoke the same external-mode path as `--external-scenario-set <temp_dir>`.
6. Clean up the temporary directory when the run exits, including validation failures and dispatch failures.

Failure mode:

- If the entity body lacks `scenarios`, or `scenarios` is not an array, reject as usage error with exit code `2` and diagnostic `state entity <key> body.scenarios is required for --external-scenarios-from-state`.

This option exists for G4 ad-hoc scoring convenience. It does not create a second loader authority model; it only materializes state-backed scenarios into the external-mode YAML path.

## 8. D5 CI Workflow

External mode is not invoked from the PR-blocking workflow and is not added to the nightly workflow by this BQ.

`.github/workflows/runbook-harness.yml` stays on the §I-authoritative normal path. The current workflow runs on schedule and manual dispatch at `.github/workflows/runbook-harness.yml:2` through `:5`, installs the package at `:16`, updates lifecycle state through `runbook-lint --mode strict --update-lifecycle` at `:17` and `:18`, and runs normal harness mode with `runbook-harness --mode conformant --session "CI-$(date -u +%Y%m%d)"` at `:19` through `:23`.

G4 hidden-eval-set runs are ad-hoc dispatches documented by this spec and by the parent BQ's Gate 3 process, not workflow changes.

## 9. D6 Test Plan

Gate 3 MUST include tests for the following acceptance-level cases. Test file paths are target locations; exact function names may adjust to the repo's test naming style.

| Test name | Verifies | Target file |
|---|---|---|
| `test_harness_cli_wires_mp_dispatch_happy_path` | CLI replaces the stub with a real callable and calls Koskadeux with `agent="mp"`, `task=<prompt>`, and `allowed_tools=["Read", "Grep", "Glob", "LS"]` | `tests/test_harness_cli.py` |
| `test_dispatch_timeout_scores_zero` | A per-scenario timeout at 180s becomes score `0.0` with reason `timeout` and the run continues | `tests/test_harness_runner.py` |
| `test_off_path_tool_use_scores_zero` | Post-hoc tool-use trace scan detects access outside the target runbook and maps to reason `tool_violation` | `tests/test_harness_runner.py` |
| `test_malformed_response_scores_zero` | Non-JSON or wrong-shape MP response maps to score `0.0` with reason `parse_error` | `tests/test_harness_runner.py` |
| `test_external_loader_accepts_without_i_mirror` | External mode accepts schema-valid external scenarios without requiring §I mirror agreement | `tests/test_harness_loader.py` |
| `test_external_loader_rejects_set_constraints` | External mode rejects count, distribution, and weight-sum failures with usage diagnostics | `tests/test_harness_loader.py` |
| `test_normal_loader_still_requires_i_mirror` | Normal mode still fails when the §I-to-YAML mirror breaks | `tests/test_harness_loader.py` |
| `test_external_and_normal_scoring_parity` | Same scenario set produces the same aggregate scoring in normal and external modes | `tests/test_harness_integration.py` |
| `test_external_scenarios_from_state_happy_path` | State entity with `body.scenarios` materializes to temp YAML and runs external mode | `tests/test_harness_cli.py` |
| `test_external_scenarios_from_state_missing_scenarios` | State entity without `body.scenarios` exits as usage error code `2` | `tests/test_harness_cli.py` |
| `test_external_flags_mutually_exclusive_with_default_authority` | CLI rejects conflicting or ambiguous authority selection and keeps default normal mode when no external flag is present | `tests/test_harness_cli.py` |

Coverage target: Gate 3 MUST maintain at least 90% coverage on touched modules. Chunk 1 Gate 3 used 90% coverage on `runbook_tools/` as a boundary at `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:1345`; this BQ applies that threshold to modified harness and CLI modules.

## 10. Acceptance Criteria

- **AC1:** The `runbook_tools/cli.py:132`/`:133` `NotImplementedError` stub is replaced with a real production callable.
- **AC2:** D1 dispatch matches Chunk 1 §6.3 exactly: no `mode` parameter, `agent="mp"`, `task=<prompt>`, `allowed_tools=["Read", "Grep", "Glob", "LS"]`, harness-side 180s timeout.
- **AC3:** Error-path exceptions are present and documented: `Timeout`, `OffPath`, `MalformedResponse`, and `DispatchFailure`, with scorer/CLI behavior matching §5.3.
- **AC4:** `--external-scenario-set <path>` exists, supports directory or single file, and is mutually exclusive with normal §I mirror authority.
- **AC5:** External scenarios validate against `schemas/scenario.schema.json`, including required `runbook`.
- **AC6:** External set-level constraints are enforced: count, type distribution, and weight sum.
- **AC7:** `--external-scenarios-from-state <entity-key>` exists, reads `body.scenarios`, materializes temp YAML files, invokes external mode, and cleans up temp files.
- **AC8:** `.github/workflows/runbook-harness.yml` remains on the normal §I-authoritative path and does not invoke external mode.
- **AC9:** Gate 3 reports at least 90% coverage on touched modules.
- **AC10:** All test cases listed in §9 are green.

## 11. Open Questions

1. Result file naming convention for external-mode runs: should they use the current `<session>-<date>.json` writer shape, an `external-<date>.json` prefix, or another convention?
2. Source granularity for external scenarios: keep all three surfaces - single YAML file, directory of YAMLs, and Living State entity body - or narrow before Gate 3?
3. Should temp-file materialization have a debugging opt-out such as `--keep-temp`, or should cleanup be unconditional for the first implementation?

## 12. Out of Scope

- Scorer algorithm changes.
- §I authority changes in normal mode.
- Chunk 1 §6.3 dispatch contract changes.
- Council roster changes.
- Responses API fallback wiring.
- Infrastructure-enforced `allowed_tools` on Codex CLI.
- New scenario types beyond `operate`, `isolate`, `repair`, `evolve`, and `ambiguous`.
- Changes to `BQ-RUNBOOK-STANDARD` specs.

## 13. Appendices

### Appendix A - Source Reference Table

All file references below were verified during authoring with `nl -ba` against commit `18c5e4a5b173adc48793f68ba4e842a66a0ca864`.

| Claim | Source |
|---|---|
| Chunk 1 Gate 2 delivered exact CLI shapes, scoring, §I mirror validation, CI structure, and upstream dependency identification | `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:1325`, `:1329`, `:1330`, `:1332`, `:1335` |
| Chunk 1 Gate 3 implementation boundary and coverage target | `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:1337`, `:1345` |
| R2 fixed the Koskadeux interface shape and documented Codex CLI limitation/upstream BQ | `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:1405`, `:1411` |
| Live MP dispatch invocation shape | `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:936`, `:943`, `:944`, `:945`, `:946`, `:947`, `:950` |
| Harness-side 180s timeout | `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:952`; `runbook_tools/harness/runner.py:38`, `:40` |
| Codex CLI primary path does not enforce `allowed_tools`; prompt and post-hoc detection are the mitigation | `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:956`, `:958`, `:960`, `:964`, `:965` |
| Upstream infrastructure BQ for Codex CLI allowed-tools enforcement | `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:967`, `:969` |
| Version-controlled prompt restriction | `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md:975`, `:978`, `:979`, `:980`, `:997`; `runbook_tools/harness/prompts.py:1`, `:2`, `:3`, `:20` |
| Current CLI stub and NotImplementedError | `runbook_tools/cli.py:132`, `:133` |
| Current runner dispatch shape | `runbook_tools/harness/runner.py:28`, `:32`, `:33`, `:34`, `:35` |
| Current runner malformed-response normalization | `runbook_tools/harness/runner.py:42`, `:44`, `:45`, `:46` |
| Current runner off-path trace scanning | `runbook_tools/harness/runner.py:62`, `:66`, `:73`, `:74` |
| Current writer result file behavior | `runbook_tools/harness/writer.py:8`, `:21`, `:22`, `:23` |
| Chunk 2 §5.4 requires external mode because hidden eval sets conflict with normal §I mirror authority | `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-2.md:220`, `:222` |
| Chunk 2 hidden answer-key artifact shape and temp-materialization invocation | `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-2.md:231` |
| Chunk 2 hidden set count, distribution, and weight constraints | `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-2.md:243` |
| Current normal loader validates YAML against schema then performs §I mirror comparison | `runbook_tools/harness/loader.py:55`, `:56`, `:58`, `:62`, `:63`, `:64`, `:65`, `:68`, `:72`, `:73`, `:80`, `:82`, `:84`, `:87` |
| Scenario schema required fields, type enum, expected-answer minimum, and weight bounds | `schemas/scenario.schema.json:5`, `:6`, `:7`, `:8`, `:9`, `:10`, `:11`, `:12`, `:13`, `:24`, `:26`, `:27`, `:28`, `:29`, `:30`, `:31`, `:32`, `:45`, `:47`, `:90`, `:92`, `:93` |
| Nightly workflow currently uses normal harness command and does not include external mode | `.github/workflows/runbook-harness.yml:1`, `:2`, `:3`, `:4`, `:5`, `:16`, `:17`, `:18`, `:19`, `:20`, `:21`, `:22`, `:23` |
| Living State entity v4 supplied D1-D6 deliverables and open questions | `build:bq-runbook-harness-production-wiring` version 4, read during authoring on 2026-04-24 |
