---
runbook_id: council
domain: council-operations
status: ACTIVE
authoritative_for:
  - topic: council-operations
    section: §C. Architecture & Interactions
  - topic: council-dispatch-failure
    section: §F. Isolate
  - topic: council-roster-and-schema-drift
    section: §F. Isolate
aliases: []
error_signatures:
  - signature: no response written after
    section: §F. Isolate
  - signature: is not set; source the credential first
    section: §F. Isolate
  - signature: Not logged in
    section: §F. Isolate
  - signature: required reviewer missing from the live tool schema
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: vulcan
last_verified_at: 2026-08-12
system_name: council
purpose_sentence: CC, Kimi, and GLM exchange one request file for one response file; MP remains the separate mandatory builder.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: |
  The complete active Council reviewer transport. council_request is a thin
  public trigger over scripts/council_dir.py. MP build dispatch is separate.
linter_version: 1.0.0
---

# Council

## §A. Header

The frontmatter is authoritative. This runbook is maintained by Vulcan. Neither instance is senior to the other.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Reviewer trigger | SHIPPED | `tools/agents.py:_handle_council_member` | Focused routing tests for CC, Kimi, and GLM | 2026-08-12 |
| Directory exchange | SHIPPED | `scripts/council_dir.py:ask_member` | Exact request bytes and raw response text tested | 2026-08-12 |
| Member launcher | SHIPPED | `scripts/council_dir.py:start` | End-to-end response file from each CLI | 2026-08-12 |
| MP build dispatch | SHIPPED | `tools/agents.py:_handle_call_mp` | Existing MP build tests; unchanged by S1527 | 2026-08-12 |
| Council Hall | DEPRECATED | — | Absent from live tool registration | 2026-08-12 |
| Reviewer wrappers and verdict persistence | DEPRECATED | — | Absence and routing tests | 2026-08-12 |

## §C. Architecture & Interactions

There is one Council reviewer path.

1. Select `cc`, `kimi`, or `glm`.
2. Place one request file under `/Users/max/council/<member>/`.
3. Start that member's CLI with one sentence: read the named request file and write the named response file in the same directory.
4. Return the response file text unchanged.

`council_request` is only the public trigger. If `review_package_path` is supplied, its bytes are copied unchanged into the member directory. Otherwise the `task` text becomes the request file. `mode=review` and `mode=open_response` use this same path. A request file may be supplied without `task` or `mode`.

The manual equivalent is:

    scripts/council_dir.py ask <cc|kimi|glm|all> <request_file>
    scripts/council_dir.py run <cc|kimi|glm|all>

The response is `response-<stamp>.md` beside `request-<stamp>.md`. That file is the durable Council verdict record; there is no second persistence or push step. File names include microseconds so two requests to one member cannot overwrite each other.

The launcher does not assemble a review prompt, pin a checkout, select files, validate a schema, set reviewer budgets, parse a verdict, retry, create a session, normalize terminal output, persist a verdict, push a branch, or select another transport. Do not add any of those behaviors.

The member may read any local file it chooses. The existing macOS sandbox confines member writes to its own Council directory plus CLI housekeeping paths. That fence does not inspect, reject, alter, or discard a response.

Credentials are launcher inputs only:

- CC uses the machine's Claude Code login and must run without `--bare`.
- GLM uses `GLM_z_AI_API_KEY` from the launched MCP environment.
- Kimi uses `MOONSHOT_API_KEY` from the launched MCP environment.

MP is not a reviewer. `council_request agent=mp mode=build|author` continues through the existing MP build system. Reviewer simplification must not change MP routing, worktrees, verification, or publication.

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Reviewer Trigger | `tools/agents.py:_handle_council_member` | none | Directory Exchange | Copies or writes one request and returns one response. |
| Directory Exchange | `scripts/council_dir.py:ask_member` | `/Users/max/council/<member>/` | Member Launcher | No parsing, persistence, or alternate transport. |
| Member Launcher | `scripts/council_dir.py:start` | request and response files | CC, Kimi, GLM CLIs | One-sentence pickup instruction. |
| Launch Environment | `scripts/launch_mcp_server.sh` | process environment | GLM and Kimi credentials | Credential values are never written to request files. |
| MP Build Dispatch | `tools/agents.py:_handle_call_mp` | existing MP task stores | Codex CLI | Separate and unchanged. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| CC | Council review | Directory exchange | Own Council directory | COMPLETE |
| Kimi | Council review | Directory exchange | Own Council directory | COMPLETE |
| GLM | Council review | Directory exchange | Own Council directory | COMPLETE |
| MP | Mandatory build; never a voter | Separate MP build path | Explicit build/author workspace | COMPLETE |
| Vulcan and Mars | Trigger work; never vote | `council_request` | Governed operational scope | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: An existing request file must be sent to one Council reviewer.
  pre_conditions: [member_is_cc_kimi_or_glm, request_file_is_readable]
  tool_or_endpoint: council_request(agent=<member>, review_package_path=<request_file>)
  argument_sourcing:
    agent: cc, kimi, or glm
    review_package_path: the exact file to copy into the member directory
  idempotency: NOT_IDEMPOTENT
  expected_success: {shape: success plus request_file, response_file, and raw response text, verification: both returned paths exist and the response equals the response file contents}
  expected_failures:
    - {signature: no response written after, cause: the CLI exited without creating the named response file}
    - {signature: is not set; source the credential first, cause: the GLM or Kimi credential is absent}
  next_step_success: Use the returned response unchanged.
  next_step_failure: Inspect the CLI output shown by the launcher; do not switch transports or add parsing or retries.
- id: E-02
  trigger: Plain task text must be sent to one Council reviewer.
  pre_conditions: [member_is_cc_kimi_or_glm, task_text_is_present]
  tool_or_endpoint: council_request(agent=<member>, task=<text>)
  argument_sourcing:
    agent: cc, kimi, or glm
    task: exact text to write to the request file
  idempotency: NOT_IDEMPOTENT
  expected_success: {shape: success plus request_file, response_file, and raw response text, verification: request file contains task exactly and response file exists}
  expected_failures:
    - {signature: no response written after, cause: the CLI did not create the named response file}
  next_step_success: Use the returned response unchanged.
  next_step_failure: Apply §F without modifying the request.
- id: E-03
  trigger: A request file must be sent to all three reviewers without the MCP surface.
  pre_conditions: [all_member_credentials_available, request_file_is_readable]
  tool_or_endpoint: scripts/council_dir.py ask all <request_file>
  argument_sourcing:
    request_file: one plain file; the same bytes are copied once per member
  idempotency: NOT_IDEMPOTENT
  expected_success: {shape: one response path per member, verification: each path exists in that member's directory}
  expected_failures:
    - {signature: member unavailable, cause: that member credential or CLI is unavailable}
  next_step_success: Read the three response files unchanged.
  next_step_failure: A failed member does not prevent the other members from running; inspect only that member's launcher output.
- id: E-04
  trigger: An approved implementation needs the mandatory MP builder.
  pre_conditions: [approved_build_scope, clean_dedicated_worktree, active_session]
  tool_or_endpoint: council_request(agent=mp, mode=build, task=<build_task>, cwd=<repo>, caller_instance=<peer>, session_id=<session>)
  argument_sourcing:
    task: approved build scope
    cwd: exact build checkout
    caller_instance: vulcan or mars
    session_id: active session
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: build scope plus target checkout plus session
  expected_success: {shape: MP task receipt and build result, verification: follow the MP build runbook}
  expected_failures:
    - {signature: MP build failure, cause: follow the separate MP build runbook}
  next_step_success: Verify the MP artifact independently.
  next_step_failure: Follow MP build recovery; do not route MP through the reviewer directory.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `no response written after` | CLI failure or member did not write the named file | Read the launcher's bounded output and check the exact response path | G-01 | CONFIRMED |
| F-02 | `GLM_z_AI_API_KEY is not set` or `MOONSHOT_API_KEY is not set` | Credential was not injected into the MCP process | Check presence and approved source without printing the value | G-02 | CONFIRMED |
| F-03 | CC says `Not logged in` | CC was started with `--bare` or the machine login is absent | Compare plain `claude -p` with `claude --bare -p` | G-03 | CONFIRMED |
| F-04 | Response appears under an old wrapper task, Hall database, verdict branch, or `/var/tmp/koskadeux/verdicts` | Retired transport is still deployed or running | Inspect live tool list, process list, deployed SHA, and returned request/response paths | G-04 | CONFIRMED |
| F-05 | A required reviewer is missing from the live tool schema, or the deployed roster and the recorded roster disagree | Roster or model policy changed in Living State without a matching deployment, or a stale client schema is being read as truth | Compare the live callable `council_request` agent enum and the required-member constants in the deployed code against Living State `infra:council-comms` and the model registry, then against the deployed SHA | G-05 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Member Launcher
  root_cause: The selected CLI did not create the named response file.
  repair_entry_point: scripts/council_dir.py:start
  change_pattern: Fix only the CLI invocation or member instruction needed to make it write the response file.
  rollback_procedure: Restore the last launcher that produced a response file.
  integrity_check: The original request remains unchanged and one response file is returned.
- id: G-02
  symptom_ref: F-02
  component_ref: Launch Environment
  root_cause: The required provider credential is absent.
  repair_entry_point: scripts/launch_mcp_server.sh
  change_pattern: Restore the existing approved credential injection, restart, and retry the same file.
  rollback_procedure: Stop if the approved source is unavailable; never store a replacement secret in code or a request file.
  integrity_check: Credential presence is true and its value is never printed.
- id: G-03
  symptom_ref: F-03
  component_ref: Member Launcher
  root_cause: The --bare flag hid the machine's Claude Code login.
  repair_entry_point: scripts/council_dir.py:_claude_command
  change_pattern: Keep bare=false for CC.
  rollback_procedure: Restore the last CC command that used the machine login.
  integrity_check: CC writes the response file without an Anthropic API key.
- id: G-04
  symptom_ref: F-04
  component_ref: Reviewer Trigger
  root_cause: Retired reviewer machinery is still registered, deployed, or running.
  repair_entry_point: koskadeux_server.py and the running service definition
  change_pattern: Remove the alternate registration or process and restart at the reviewed SHA.
  rollback_procedure: Roll back the whole deployment only if the directory trigger itself cannot run.
  integrity_check: council_request is the only reviewer tool and returns paths under /Users/max/council/<member>/.
- id: G-05
  symptom_ref: F-05
  component_ref: Reviewer Trigger
  root_cause: The reviewer roster or a member model drifted between Living State and the deployed schema.
  repair_entry_point: Living State infra:council-comms plus the deployed reviewer registration
  change_pattern: Treat Living State infra:council-comms and the model registry as the only roster truth; reconcile the live callable schema and the required-member constants to it, and never substitute a member or reduce quorum to route around the gap.
  rollback_procedure: Block the gate and keep the recorded roster; do not edit prose to match a stale client.
  integrity_check: The live agent enum, the recorded roster, and the deployed SHA all name the same members.
```

## §H. Evolve

### §H.1 Invariants

- `council_request` is the only public Council reviewer trigger.
- CC, Kimi, and GLM all use `scripts/council_dir.py`.
- One request file produces one response file in the same member directory.
- Responses are returned unchanged.
- MP build dispatch remains separate.

### §H.2 BREAKING predicates

- Adding another Council reviewer transport, Hall, wrapper, parser, retry layer, persistence step, or pre-dispatch reviewer gate is BREAKING.
- Routing MP through the reviewer directory is BREAKING.

### §H.3 REVIEW predicates

- Changing a member CLI command, model, credential source, or directory location requires review and an end-to-end file exchange.

### §H.4 SAFE predicates

- Correcting prose or tests to match the deployed one-file contract is SAFE.

### §H.5 Boundary definitions

#### module

The reviewer module is `tools/agents.py:_handle_council_member` plus `scripts/council_dir.py`.

#### public contract

The public contract is `council_request` returning request path, response path, and unchanged response text.

#### runtime dependency

A runtime dependency is the selected member CLI, its existing credential, and the writable member directory.

#### config default

The only reviewer defaults are the member CLI commands and `/Users/max/council` root defined in `scripts/council_dir.py`.

### §H.6 Adjudication

Max resolves any request to add behavior between the request file and response file.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01, §H.1]
    scenario: An existing request file is sent to Kimi through council_request.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, review_package_path]
        argument_values: {agent: kimi}
    weight: 0.25
  - id: I-02
    type: operate
    refs: [E-02, §H.1]
    scenario: The same task text is sent separately to CC, Kimi, and GLM.
    expected_answers:
      - kind: human_action
        verb: verify
        object: all three reviewers use the same directory handler
        target: tools/agents.py
    weight: 0.25
  - id: I-03
    type: isolate
    refs: [F-04, G-04]
    scenario: Inspect the live tool list after deployment.
    expected_answers:
      - kind: human_action
        verb: inspect
        object: live tool list
        target: council_request present and council_hall absent
    weight: 0.25
  - id: I-04
    type: operate
    refs: [E-04, §H.1]
    scenario: Dispatch an MP build after the reviewer simplification.
    expected_answers:
      - kind: classification
        label: MP path unchanged
    weight: 0.25
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1527
last_refresh_commit: d393224d95c35a45d83a2347d1fcedc99f67895e
last_refresh_date: 2026-08-12T14:00:00Z
owner_agent: vulcan
refresh_triggers:
  - council_request reviewer routing changes
  - a Council member CLI command changes
  - the Council directory or credential source changes
scheduled_cadence: 90d
last_harness_pass_rate: 0.16666666666666666
last_harness_date: 2026-07-18T08:36:20.840312Z
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1527 / 2026-08-12T14:00:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
