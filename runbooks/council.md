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
  - signature: "Error occurred during tool execution"
    section: §F. Isolate
  - signature: "OAuth session expired and could not be refreshed"
    section: §F. Isolate
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
last_verified_at: 2026-08-16
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
| Reviewer trigger | SHIPPED | `tools/agents.py` | Immediate submit, busy/no-second-file, running/completed/failed polling, and exact-response tests | 2026-08-16 |
| Directory exchange | SHIPPED | `scripts/council_dir.py` | MCP and CLI share one lock-before-write path; 98 focused tests and deployed submit/poll canary at `31c843b6` | 2026-08-16 |
| Member launcher | SHIPPED | `scripts/council_dir.py:start` | 137 focused tests; deployed low-effort canary and full max-effort GLM review both retained matching responses at `c96cea2f`; see G-07 | 2026-08-16 |
| MP build dispatch | SHIPPED | `tools/agents.py:_handle_call_mp` | Existing MP build tests; unchanged by S1527 | 2026-08-12 |
| Council Hall | DEPRECATED | — | Absent from live tool registration | 2026-08-12 |
| Reviewer wrappers and verdict persistence | DEPRECATED | — | Absence and routing tests | 2026-08-12 |

## §C. Architecture & Interactions

There is one Council reviewer path.

1. Select `cc`, `kimi`, or `glm`.
2. Acquire that member's fixed OS lock, place one request file under `/Users/max/council/<member>/`, and start the detached member worker.
3. Return `status=submitted`, `request_id`, request path, and response path immediately; do not wait for the provider.
4. Poll `council_request(action=check_review, agent=<member>, request_id=<request_id>)`. `running` means that exact request owns the lock; `completed` returns the response text unchanged; `failed` means the worker exited without the response; `not_found` means the request file does not exist.

`council_request` is only the public trigger. If `review_package_path` is supplied, its bytes become the original request bytes. Otherwise the encoded `task` text becomes the original request bytes. Before the one request writer stores a request, the shared bytes helper prepends the standard `REVIEW_PROTOCOL`; the original bytes remain the exact suffix. `mode=review` and `mode=open_response` use this same path. A request file may be supplied without `task` or `mode`.

The standard preamble is the complete review contract approved in S1557. It requires exact artifact identity, environment truth, ground truth and boundaries, honest builder verification including failures and untrusted signals, prior-round delta, and three to six risk questions in the request body. It tells the reviewer to verify load-bearing claims, read whatever is necessary, return a verdict even when its turn budget expires, name incomplete coverage, produce SHA-bound evidenced findings, and answer the standing SIMPLER and BETTER questions. Do not shorten or hand-edit the prefix at dispatch time; its exact bytes are locked by the focused test.

The manual equivalent is:

    scripts/council_dir.py ask <cc|kimi|glm|all> <request_file>
    scripts/council_dir.py run <cc|kimi|glm|all>

CLI `ask` calls the same `submit_member` function as the MCP trigger, returns after submission, and preserves file/stdin bytes exactly. A busy member is rejected before a second request file is written; `ask all` continues submitting the free members and exits nonzero if any member was busy or failed. CLI `run` only starts already-placed files under the same member lock and does not prepend again. A file placed directly in a member directory likewise remains operator-authored and receives no automatic prefix.

For a controlled baseline experiment, a non-empty `KD_COUNCIL_NO_PROTOCOL` suppresses the prefix at the request writer. The exact original bytes are then stored unchanged, and the writer emits exactly one visible stderr/log marker naming `KD_COUNCIL_NO_PROTOCOL` for each suppressed write. The marker never includes request content.

The response is `response-<stamp>.md` beside `request-<stamp>.md`. That file is the durable Council verdict record; there is no second persistence or push step. File names include microseconds so two requests to one member cannot overwrite each other.

The launcher does not pin a checkout, select files, retry, create a session, persist a verdict, push a branch, or select another transport. CC and Kimi receive the one-sentence pickup instruction. GLM has no text-file-reading tool, so the launcher reads the same request file as UTF-8 and sends its complete contents over stdin; the launcher writes Codex's exact final UTF-8 message to the matching response file. The external contract remains one request file in and one response file out in the same member directory. Do not add another broker, queue, daemon, filesystem service, schema wrapper, or alternate launcher.

CC and Kimi may read local files and may write only inside their own Council member directory plus CLI housekeeping paths. GLM receives the self-contained request file only; exact review packages therefore carry their own sources and diff. The GLM sandbox is read-only and the launcher writes its named response file. The fence does not inspect, alter, or discard an accepted response.

Admission control is deliberately smaller than a queue. Each member has one fixed `.member.lock`; the submitter acquires it before writing the request and hands the same locked descriptor to the detached worker. A second submission returns `status=busy` with the active `request_id` and creates no file. There is no waiting list, broker, retry, or daemon. The response file and the lock state are the complete durable status record across client disconnects.

### Production measurement checkpoint

Use the existing request and response files; do not add request-path telemetry. Score the first 20 ordinary production reviews after this protocol deploys, excluding `KD_COUNCIL_NO_PROTOCOL` experiments and byte-identical retries. Record, by reviewer and in aggregate:

- usable verdict returned and elapsed time;
- non-approving verdict rate;
- numbered findings carrying exact repo@SHA and file:line evidence;
- explicit uncovered-area or fully-covered statement;
- concrete SIMPLER and BETTER answers, including supported `none found` answers.

Compare the cohort with the S1539/S1544 baseline and record a keep, tune, or rollback recommendation on `build:bq-council-review-request-standard-s1539`. Stop the cohort and investigate after two consecutive missing verdicts or evidence that the standard is suppressing a material finding. This checkpoint evaluates the prompt; it does not parse, reject, or alter live Council responses.

Credentials are launcher inputs only:

- CC uses the machine's Claude Code login and must run without `--bare`.
- GLM uses `GLM_z_AI_API_KEY` from the launched MCP environment and a dedicated `CODEX_HOME` at `/Users/max/koskadeux-state/agents/glm/codex-home`; no credential is stored there.
- Kimi uses `MOONSHOT_API_KEY` from the launched MCP environment.

MP is not a reviewer. `council_request agent=mp mode=build|author` continues through the existing MP build system. Reviewer simplification must not change MP routing, worktrees, verification, or publication.

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Reviewer Trigger | `tools/agents.py:_handle_council_member` and `_handle_check_council_member` | none | Directory Exchange | Submit returns `request_id` immediately; `check_review` returns running/completed/failed/not_found and unchanged completed text. |
| Directory Exchange | `scripts/council_dir.py:submit_member` | `/Users/max/council/<member>/` and one fixed `.member.lock` | Member Launcher | One lock-before-write path for MCP and CLI; exact original-byte suffix; no queue, retry, or alternate transport. |
| Member Launcher | `scripts/council_dir.py:start` | request and response files | CC, Kimi, GLM CLIs | File-in/file-out. GLM request bytes are carried over stdin because its shell tool is disabled. |
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
| F-03 | CC returns `auth_unavailable`, `cc_busy`, or `Not logged in` | The dedicated CC profile is absent, its OAuth login is unusable, or another CC review holds the profile lock | Run `cc_profile.status()` and require `isolated=true` and `credential_usable=true`; for `cc_busy`, confirm the existing lock holder is still running | G-03 | CONFIRMED |
| F-04 | Response appears under an old wrapper task, Hall database, verdict branch, or `/var/tmp/koskadeux/verdicts` | Retired transport is still deployed or running | Inspect live tool list, process list, deployed SHA, and returned request/response paths | G-04 | CONFIRMED |
| F-05 | A required reviewer is missing from the live tool schema, or the deployed roster and the recorded roster disagree | Roster or model policy changed in Living State without a matching deployment, or a stale client schema is being read as truth | Compare the live callable `council_request` agent enum and the required-member constants in the deployed code against Living State `infra:council-comms` and the model registry, then against the deployed SHA | G-05 | CONFIRMED |
| F-06 | Reviewer dispatch does not return `submitted` promptly, a second same-member dispatch creates another request, or `check_review` disagrees with the retained files | The pre-S1557 synchronous handler is still deployed, the member lock path drifted, the detached worker did not retain the lock, or the caller is using a stale tool schema without `check_review` | Require main, checkout, and deployed marker at `31c843b6`; require the live `council_request` action enum to contain `check_review`; submit one bounded canary, confirm immediate `request_id`, running then completed, unchanged response, and a concurrent dispatch returning busy with no new request file | G-06 | CONFIRMED |
| F-07 | Max's Claude login changes after GLM, GLM returns `glm_*`, or GLM does not produce the matching response file | The retired Claude-based GLM route reappeared, the dedicated Codex home drifted, the provider/JSONL lifecycle failed, the response differs from the attested final message, or the request is not UTF-8 | Verify main, checkout, and deployed marker first. Run the 90-second low-effort transport canary before a full max-effort review. Across both runs confirm `~/.claude/session-env`, `~/.codex/auth.json` mtime, and the login watcher are unchanged; confirm zero auth files/symlinks under the dedicated GLM home | G-07 | CONFIRMED |

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
  root_cause: The dedicated CC profile is missing, logged out, or currently locked by another review.
  repair_entry_point: cc_profile.py and scripts/setup_cc_profile.sh
  change_pattern: Run scripts/setup_cc_profile.sh as Max when the profile is missing or logged out; wait for the live lock holder when status is cc_busy.
  rollback_procedure: Stop if the dedicated profile cannot be restored; never route CC through Max's personal Claude profile or inject an Anthropic API key.
  integrity_check: cc_profile.status reports isolated=true and credential_usable=true, then CC writes the response file.
- id: G-04
  symptom_ref: F-04
  component_ref: Reviewer Trigger
  root_cause: Retired reviewer machinery is still registered, deployed, or running.
  repair_entry_point: koskadeux_server.py and the running service definition
  change_pattern: Remove the alternate registration or process and restart at the reviewed SHA.
  rollback_procedure: Roll back the whole deployment only if the directory trigger itself cannot run.
  integrity_check: council_request is the only reviewer tool and returns paths under /Users/max/council/<member>/.
- id: G-06
  symptom_ref: F-06
  component_ref: Member Launcher
  root_cause: Before S1557, council_request waited synchronously for the provider and could outlive the client timeout; independent dispatches could also overlap one member. The deployed path submits once, returns immediately, and holds one per-member OS lock for the worker lifetime.
  repair_entry_point: tools/agents.py:_handle_council_member and _handle_check_council_member; scripts/council_dir.py:submit_member and member_request_status
  change_pattern: Verify the exact deployed SHA and live schema first. If busy, poll the returned active request_id; do not re-dispatch. If failed, inspect the exact retained request/response paths and provider failure, then make any retry an explicit new operator decision. Never bypass or weaken the member lock.
  rollback_procedure: Forward-roll protected main on a named rollback branch to tree 7ef8d2e0570b8e086e6ac2b67b8955510b7d7871 (commit c96cea2fcbbc0fb6b53d19f39becfc5b0cba734c), restart, verify health, and keep Council review dispatch closed because that tree restores the known synchronous timeout behavior.
  integrity_check: Main, checkout, and deployed marker equal 31c843b6b24779a5250cf406e5d1975e7b4f3177; live schema includes check_review; submit returns request_id immediately; poll reaches completed with unchanged text; a concurrent same-member submit returns busy without creating a request file.
- id: G-07
  symptom_ref: F-07
  component_ref: Member Launcher
  root_cause: >-
    Before S1566, GLM ran through the Claude binary with no isolated Claude profile and wrote into
    Max's personal ~/.claude state. --bare did not isolate it. The deployed S1566 route removes
    Claude from GLM completely: one UTF-8 request file is read by council_dir, sent over stdin to
    codex exec using the dedicated GLM CODEX_HOME, and Codex writes the matching response file.
    The model shell tool is disabled, runs are serialized, malformed JSONL and any command or file
    change fail closed, and the accepted response must byte-match Codex's attested final message.
    R11 SHA 9c8d6a5c7e26ff0078e97cd7dfb0e3b96c199b56 retained schema enforcement and deleted a usable
    Markdown-fenced response; it was immediately forward-rolled back to 041f7d78. R13 removed that
    schema-only layer instead of adding fence parsing. Exact reviewed SHA
    c96cea2fcbbc0fb6b53d19f39becfc5b0cba734c is now main and deployed. Its 90-second low-effort
    transport canary passed in 50.758 seconds with eight JSONL events, one agent message, zero file
    changes, and a retained response. A separate full max-effort production review then retained
    response-20260816-225423-290186.md with APPROVE_WITH_NITS and no blocking finding. Across both
    deployed proofs ~/.claude/session-env stayed at 859 entries, ~/.codex/auth.json mtime stayed
    1786520858, the login-watcher stayed 2801918 bytes, and the dedicated GLM home contained zero
    auth.json files and zero symlinks.
  repair_entry_point: scripts/council_dir.py:start and glm_codex_transport.py
  change_pattern: >-
    Keep the one-file contract, dedicated CODEX_HOME, direct codex exec path, plain exact response,
    JSONL attestation, process lock, and child cleanup. After any GLM transport deployment, first run
    a 90-second low-reasoning canary through the same transport entry point; only after it passes run
    one full max-reasoning review. Never print or store GLM_z_AI_API_KEY. Do not add a broker, queue,
    daemon, filesystem service, response schema, Claude fallback, second launcher, or shell capability.
  rollback_procedure: >-
    If the canary, full review, health, isolation, or exact-SHA check fails, forward-roll main with a
    named rollback branch whose tree is 041f7d78dbcbb47518748bc0e7e7c4d160bd1c33, restart, verify
    health and restored behavior, and keep GLM/full Council closed. Never restore the retired
    Claude-based GLM route. The prior named example is rollback/s1566-r11-live-proof-failure.
  integrity_check: >-
    main, checkout, and deployed marker equal the reviewed SHA; health is OK; a request file produces
    its matching response file; session-env count, personal Codex auth mtime, and watcher bytes are
    unchanged; the dedicated GLM home has zero credential files and symlinks.
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
- One member runs at most one request; busy creates no request file.
- Dispatch returns a durable request ID immediately and polling never retries.
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

The reviewer module is `tools/agents.py:_handle_council_member` plus `scripts/council_dir.py`; GLM's launcher implementation is `glm_codex_transport.py`.

#### public contract

The public contract is `council_request` returning `status=submitted`, `request_id`, request path, and response path immediately; `action=check_review` returns running/completed/failed/not_found and includes unchanged response text only when completed.

#### runtime dependency

A runtime dependency is the selected member CLI, its existing credential, and the writable member directory.

#### config default

The reviewer defaults are the member CLI commands and `/Users/max/council` root in `scripts/council_dir.py`, plus GLM's dedicated `/Users/max/koskadeux-state/agents/glm/codex-home` and its checked config template.

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
last_refresh_session: S1557
last_refresh_commit: 31c843b6b24779a5250cf406e5d1975e7b4f3177
last_refresh_date: 2026-08-16T22:35:00Z
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
