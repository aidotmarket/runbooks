---
title: Council
owner: vulcan
last_verified: '2026-09-01'
aliases:
- Council dispatch
- review transport
- glm-codex-transport
- deepseek-codex-transport
- glm-profile-isolation
error_signatures:
- Error occurred during tool execution
- Not logged in
- OAuth session expired and could not be refreshed
- is not set; source the credential first
- no response written after
- required reviewer missing from the live tool schema
---

# Council

## Overview

This runbook is maintained by Vulcan. Neither instance is senior to the other.

## Capabilities

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Reviewer trigger | SHIPPED | `tools/agents.py` | Returns status=submitted with the two file paths immediately; exact-bytes tests | 2026-08-17 |
| Directory exchange | SHIPPED | `scripts/council_dir.py` | One write path for MCP and CLI; detached worker per request; unit tests green at S1568 | 2026-08-17 |
| Member launcher | SHIPPED | `scripts/council_dir.py:start` | Detached lifetime proven with the real 43KB S1567 R7 package: Kimi 2765s, GLM (minimal Codex transport) ~510s, both response files retained (S1568) | 2026-08-17 |
| DeepSeek reviewer seat | REGISTERED (EXPLICIT-NAME SHADOW ONLY) | `deepseek_codex_transport.py`, `config/deepseek_codex/` | Transport, config, environment-isolation, explicit-name directory routing, roster/audit visibility, and candidate-versus-three-voter-base non-authority tests | 2026-09-01 |
| MP build dispatch | SHIPPED | `tools/agents.py:_handle_dispatch_mp_build` | Live remote no-op dispatch plus existing minimal-bridge tests | 2026-08-26 |
| Council Hall | DEPRECATED | — | Absent from live tool registration | 2026-08-12 |
| Reviewer wrappers and verdict persistence | DEPRECATED | — | Absence and routing tests | 2026-08-12 |

## Architecture & interactions

There is one Council reviewer path.

1. Select `cc`, `kimi`, `glm`, or `deepseek`.
2. Place one request file under `/Users/max/council/<member>/` and detach the member worker into its own session (`council_dir.py start <member> <request>` under the hood). The worker's lifetime is independent of any HTTP request: the ~120s gateway lifetime that killed real 39.5KB CC/Kimi reviews (Mars, S1557) cannot reach it. Launcher stdout goes to `launcher-<stamp>.md.log` beside the request.
3. Return `status=submitted` with the request path and response path immediately.
4. Completion is the response file existing at the returned path. There is no polling API, queue, ledger, or per-member submission lock; concurrent requests simply create distinct timestamped files, each with its own worker. Failure diagnosis is the launcher log.

`council_request` is only the public trigger. If `review_package_path` is supplied, its bytes become the original request bytes. Otherwise the encoded `task` text becomes the original request bytes. Before the one request writer stores a request, the shared bytes helper prepends the standard `REVIEW_PROTOCOL`; the original bytes remain the exact suffix. `mode=review` and `mode=open_response` use this same path. A request file may be supplied without `task` or `mode`.

The standard preamble is the complete review contract approved in S1557. It requires exact artifact identity, environment truth, ground truth and boundaries, honest builder verification including failures and untrusted signals, prior-round delta, and three to six risk questions in the request body. It tells the reviewer to verify load-bearing claims, read whatever is necessary, return a verdict even when its turn budget expires, name incomplete coverage, produce SHA-bound evidenced findings, and answer the standing SIMPLER and BETTER questions. Do not shorten or hand-edit the prefix at dispatch time; its exact bytes are locked by the focused test.

The manual equivalent is:

    scripts/council_dir.py ask <cc|kimi|glm|deepseek|all> <request_file>
    scripts/council_dir.py run <cc|kimi|glm|deepseek|all>
    scripts/council_dir.py ask deepseek <request_file>
    scripts/council_dir.py run deepseek

`ask all` and `run all` mean the three required reviewers, processed in the
existing directory order: GLM, CC, then Kimi. They never include DeepSeek. Use
`ask deepseek` or `run deepseek` explicitly.

CLI `ask` calls the same `submit_member` function as the MCP trigger, returns after submission, and preserves file/stdin bytes exactly. A busy member is rejected before a second request file is written; `ask all` continues submitting the free members and exits nonzero if any member was busy or failed. CLI `run` only starts already-placed files under the same member lock and does not prepend again. A file placed directly in a member directory likewise remains operator-authored and receives no automatic prefix.

For a controlled baseline experiment, a non-empty `KD_COUNCIL_NO_PROTOCOL` suppresses the prefix at the request writer. The exact original bytes are then stored unchanged, and the writer emits exactly one visible stderr/log marker naming `KD_COUNCIL_NO_PROTOCOL` for each suppressed write. The marker never includes request content.

The response is `response-<stamp>.md` beside `request-<stamp>.md`. That file is the durable Council verdict record; there is no second persistence or push step. File names include microseconds so two requests to one member cannot overwrite each other.

A reviewer may return `REJECT` with no build mandates when its conclusion is to stop the proposed work. The response file and its explanation remain the complete verdict; the operator must not invent a mandate to satisfy a response shape. The directory transport does not schema-validate or discard that response.

The launcher does not pin a checkout, select files, retry, create a session, persist a verdict, push a branch, or select another transport. CC and Kimi receive the one-sentence pickup instruction. GLM and DeepSeek use the same parameterized Codex transport: each receives the complete request over stdin and Codex writes the one response file via `-o`. GLM keeps its dedicated `CODEX_HOME` and `HOME` under `/Users/max/koskadeux-state/agents/glm/`; DeepSeek has separate homes at `/Users/max/koskadeux-state/agents/deepseek/codex-home` and `/Users/max/koskadeux-state/agents/deepseek`. Their checked templates are `config/glm_codex/` and `config/deepseek_codex/`. Nothing in the Codex launcher parses output, size-limits it, byte-compares the response, audits directory permissions, or deletes a response (S1568). Each template supplies a `:read-only` permission profile, denies `/Users/max/.codex`, and excludes its provider credential from the child shell environment. The external contract remains one request file in and one response file out in the same member directory for all four registered reviewers, with response-file existence as the sole success criterion. Do not add another broker, queue, daemon, filesystem service, schema wrapper, or alternate launcher.

DeepSeek is registered, audited, displayed, and dispatchable by explicit name for
Phase-1 shadow evaluation. It is outside the required-reviewer set and has no
authority: its absence, failure, model mismatch, verdict, or mandates cannot
change gate consensus, gate status, run status, `blocking_revisions`, build
completion authorization, empty-range override acknowledgement, spec approval,
`ask all`/`run all` expansion, or shared health. Its own configured state remains
visible as `service_health.deepseek.configured`, but it is excluded from
`health_summary`. Single-voter gate submission rejects DeepSeek before either the
atomic backend call or the local fallback.

Empty-range override acknowledgement is actor-authorized. `vulcan`, `mars`,
`venus`, `mercury`, `jupiter`, `saturn`, and `mp` may acknowledge with no declared
role or with `ack_role=peer`; CC, Kimi, and GLM may acknowledge with no declared
role or with `ack_role=council`. A payload role never grants authority by itself:
DeepSeek, an unknown actor, or an authorized actor claiming the other class is
rejected. This actor/role binding closes a pre-existing weakness in the base
implementation; it is not merely a DeepSeek roster filter. The final candidate
contains no automatic promotion path for a registered reviewer. Giving DeepSeek
authority is outside Phase 1 and requires a separate decision and code change.

CC and Kimi may read local files and may write only inside their own Council member directory plus CLI housekeeping paths. GLM and DeepSeek receive the self-contained request over stdin and may use read-only shell commands to inspect the pinned checkout; Codex writes the named response file. No fence inspects, alters, or discards an accepted response.

There is no admission control (Max, S1568: nothing that can check and block work). No member lock, no busy refusal, no waiting list, broker, retry, or daemon. The only lock anywhere is CC's profile lock, which exists to stop two Claude Code processes racing one OAuth token refresh — the mechanism that historically destroyed Max's own login — and never refuses a review; it serializes CC launches. The response file is the complete durable status record across client disconnects.

### Production measurement checkpoint

Use the existing request and response files; do not add request-path telemetry. Score the first 20 ordinary production reviews after this protocol deploys, excluding `KD_COUNCIL_NO_PROTOCOL` experiments and byte-identical retries. Record, by reviewer and in aggregate:

- usable verdict returned and elapsed time;
- non-approving verdict rate;
- numbered findings carrying exact repo@SHA and file:line evidence;
- explicit uncovered-area or fully-covered statement;
- concrete SIMPLER and BETTER answers, including supported `none found` answers.

Compare the cohort with the S1539/S1544 baseline and record a keep, tune, or rollback recommendation on `build:bq-council-review-request-standard-s1539`. Stop the cohort and investigate after two consecutive missing verdicts or evidence that the standard is suppressing a material finding. This checkpoint evaluates the prompt; it does not parse, reject, or alter live Council responses.

Credentials are launcher inputs only:

- CC uses the dedicated isolated CC profile from F-03/G-03, never Max's personal Claude profile,
  and must run without `--bare`.
- GLM uses `GLM_z_AI_API_KEY` from the launched MCP environment and a dedicated `CODEX_HOME` at `/Users/max/koskadeux-state/agents/glm/codex-home`; no credential is stored there.
- Kimi uses `MOONSHOT_API_KEY` from the launched MCP environment.
- DeepSeek uses `DEEPSEEK_API_KEY` from Infisical project `0943f641-faee-4324-b337-0d50c276e4a9`, environment `prod`, path `/`, and dedicated homes under `/Users/max/koskadeux-state/agents/deepseek/`; no credential is stored there.

Kimi retained-session finalization uses `kimi --session <id> --prompt <text>`
under the same member sandbox and a five-step reserve. Do not add `--auto` to
that prompt-mode command: Kimi CLI 0.32.0 rejects `--auto` plus `--prompt`
before it resolves the retained session. S1632 recovered the original 55-step
review without resending its package, then merged the one-token repair as
`koskadeux-mcp` PR 196 (`cbc27315868d14e9d5efb61bf53890a0174dc62a`).

The public agent/build surface has two names: `council_request` for review and
`dispatch_mp_build` for builds. Build status and listing remain actions on
`council_request`: `action=check_build` and `action=list_builds`. The former
public aliases `call_mp`, `call_claude_code`, `dispatch_build`, `check_build`,
and `list_builds` are retired and raw calls are refused as unknown before any
handler or build side effect.

MP is not a reviewer. The private `council_request agent=mp mode=build|author`
path continues through the same minimal MP build system for existing callers;
it is not a second advertised build tool. Registered raw state and shell
compatibility names are unchanged by this agent/build route reduction.

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Reviewer Trigger | `tools/agents.py:_handle_council_member` and `_handle_check_council_member` | none | Directory Exchange | Submit returns `request_id` immediately; `check_review` returns running/completed/failed/not_found and unchanged completed text. |
| Directory Exchange | `scripts/council_dir.py:submit_member` | `/Users/max/council/<member>/` and one fixed `.member.lock` | Member Launcher | One lock-before-write path for MCP and CLI; exact original-byte suffix; no queue, retry, or alternate transport. |
| Member Launcher | `scripts/council_dir.py:start` | request and response files | CC, Kimi, GLM, DeepSeek CLIs | File-in/file-out. GLM and DeepSeek use the shared parameterized Codex transport with provider-specific homes and config. |
| Launch Environment | `scripts/launch_mcp_server.sh` | process environment | GLM, Kimi, and DeepSeek credentials | Credential values are never written to request files. |
| MP Build Dispatch | `dispatch_mp_build` → `tools/agents.py:_handle_dispatch_mp_build` | existing MP task stores | Minimal bridge and Codex CLI | The separately advertised build route. |

## Agent capabilities

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| CC | Council review | Directory exchange | Own Council directory | COMPLETE |
| Kimi | Council review | Directory exchange | Own Council directory | COMPLETE |
| GLM | Council review | Directory exchange | Own Council directory | COMPLETE |
| DeepSeek | Council shadow review; not a required voter | Shared parameterized Codex transport and directory exchange | Dedicated `HOME`/`CODEX_HOME`; Infisical-injected DeepSeek key | REGISTERED |
| MP | Mandatory build; never a voter | Separate MP build path | Explicit build/author workspace | COMPLETE |
| Vulcan and Mars | Trigger work; never vote | `council_request`, `dispatch_mp_build` | Governed operational scope | COMPLETE |

## How to operate

```yaml operate
- id: E-01
  trigger: An existing request file must be sent to one Council reviewer.
  pre_conditions: [member_is_cc_kimi_glm_or_deepseek, request_file_is_readable]
  tool_or_endpoint: council_request(agent=<member>, review_package_path=<request_file>)
  argument_sourcing:
    agent: cc, kimi, glm, or deepseek
    review_package_path: the exact file to copy into the member directory
  idempotency: NOT_IDEMPOTENT
  expected_success: {shape: status submitted plus request_id, request path, and response path, verification: the request path exists and the call returns without waiting for the response path}
  expected_failures:
    - {signature: status busy plus active_request_id, cause: that member already has one active request; no new request file is written}
  next_step_success: Poll the returned request_id with E-04 until completed or failed.
  next_step_failure: Poll the active_request_id; do not switch transports, add parsing, or re-dispatch.
- id: E-02
  trigger: Plain task text must be sent to one Council reviewer.
  pre_conditions: [member_is_cc_kimi_glm_or_deepseek, task_text_is_present]
  tool_or_endpoint: council_request(agent=<member>, task=<text>)
  argument_sourcing:
    agent: cc, kimi, glm, or deepseek
    task: exact text to write to the request file
  idempotency: NOT_IDEMPOTENT
  expected_success: {shape: status submitted plus request_id, request path, and response path, verification: the request file contains the task and the call does not require the response file to exist}
  expected_failures:
    - {signature: status busy plus active_request_id, cause: that member already has one active request; no new request file is written}
  next_step_success: Poll the returned request_id with E-04 until completed or failed.
  next_step_failure: Poll the active_request_id; apply When it breaks without modifying or re-dispatching the request.
- id: E-03
  trigger: A request file must be sent to all three required reviewers without the MCP surface.
  pre_conditions: [required_member_credentials_available, request_file_is_readable]
  tool_or_endpoint: scripts/council_dir.py ask all <request_file>
  argument_sourcing:
    request_file: one plain file; the same bytes are copied once to CC, Kimi, and GLM only; use ask deepseek explicitly for a separate shadow review
  idempotency: NOT_IDEMPOTENT
  expected_success: {shape: exactly three submitted request paths without waiting for responses, verification: one printed request path exists in each required member directory and none is created for DeepSeek}
  expected_failures:
    - {signature: member unavailable, cause: that member credential or CLI is unavailable}
    - {signature: member_busy plus active request, cause: that member already has one active request; no new request file is written}
  next_step_success: Derive each request_id from its printed path and poll it with E-04.
  next_step_failure: Poll a busy member's active request; a failed member does not prevent the other members from submitting.
- id: E-04
  trigger: A submitted Council review must be checked without creating or retrying a request.
  pre_conditions: [member_is_cc_kimi_glm_or_deepseek, request_id_was_returned_by_submit_or_busy]
  tool_or_endpoint: council_request(action=check_review, agent=<member>, request_id=<request_id>)
  argument_sourcing:
    agent: the member that owns the returned request_id
    request_id: the exact request filename returned by submitted or active_request_id returned by busy
  idempotency: IDEMPOTENT
  expected_success: {shape: status running, completed, failed, or not_found, verification: completed alone includes the retained response text unchanged; polling creates no request file and never retries}
  expected_failures:
    - {signature: status failed, cause: the retained request has no response and its member lock is no longer held for that request}
    - {signature: status not_found, cause: no retained request exists for that member and request_id}
  next_step_success: If running, poll the same request_id again; if completed, use the returned response unchanged.
  next_step_failure: Inspect the retained paths and provider evidence; any retry is an explicit new operator decision.
- id: E-05
  trigger: An approved implementation needs the mandatory MP builder.
  pre_conditions: [approved_build_scope, clean_dedicated_worktree, active_session]
  tool_or_endpoint: dispatch_mp_build(task=<build_task>, repo=<org/repo>, expected_branch=<build/branch>, caller_instance=<peer>, ref_entity=<work_ref>)
  argument_sourcing:
    task: approved build scope
    repo: canonical configured repository identity
    expected_branch: exact disposable or delivery build branch
    caller_instance: vulcan or mars
    ref_entity: active BQ, support ticket, or bounded work reference
  idempotency: NOT_IDEMPOTENT
  expected_success: {shape: queued receipt with task_id and expected_branch, verification: poll the task_id with council_request(action=check_build) and follow the MP build runbook}
  expected_failures:
    - {signature: MP build failure, cause: follow the separate MP build runbook}
  next_step_success: Verify the MP artifact independently.
  next_step_failure: Follow MP build recovery; do not route MP through the reviewer directory.
```

## When it breaks

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `no response written after` | CLI failure or member did not write the named file | Read the launcher's bounded output and check the exact response path | G-01 | CONFIRMED |
| F-02 | `GLM_z_AI_API_KEY is not set`, `MOONSHOT_API_KEY is not set`, or `DEEPSEEK_API_KEY is not set` | Credential was not injected into the MCP process | Check presence and approved source without printing the value | G-02 | CONFIRMED |
| F-03 | CC returns `auth_unavailable`, `cc_busy`, or `Not logged in` | The dedicated CC profile is absent, its OAuth login is unusable, or another CC review holds the profile lock | Run `cc_profile.status()` and require `isolated=true` and `credential_usable=true`; for `cc_busy`, confirm the existing lock holder is still running | G-03 | CONFIRMED |
| F-04 | Response appears under an old wrapper task, Hall database, verdict branch, or `/var/tmp/koskadeux/verdicts` | Retired transport is still deployed or running | Inspect live tool list, process list, deployed SHA, and returned request/response paths | G-04 | CONFIRMED |
| F-05 | A required reviewer is missing from the live tool schema, or the deployed roster and the recorded roster disagree | Roster or model policy changed in Living State without a matching deployment, or a stale client schema is being read as truth | Compare the live callable `council_request` agent enum and the required-member constants in the deployed code against Living State `infra:council-comms` and the model registry, then against the deployed SHA | G-05 | CONFIRMED |
| F-06 | Reviewer dispatch does not return `submitted` promptly, a second same-member dispatch creates another request, or `check_review` disagrees with the retained files | The pre-S1557 synchronous handler is still deployed, the member lock path drifted, the detached worker did not retain the lock, or the caller is using a stale tool schema without `check_review` | Require main, checkout, and deployed marker at `31c843b6`; require the live `council_request` action enum to contain `check_review`; submit one bounded canary, confirm immediate `request_id`, running then completed, unchanged response, and a concurrent dispatch returning busy with no new request file | G-06 | CONFIRMED |
| F-07 | Max's Claude login changes after GLM, GLM returns `glm_*`, or GLM does not produce the matching response file | The retired Claude-based GLM route reappeared, the dedicated Codex home drifted, the provider/JSONL lifecycle failed, the response differs from the attested final message, or the request is not UTF-8 | Verify main, checkout, and deployed marker first. Run the 90-second low-effort transport canary before a full max-effort review. Across both runs confirm `~/.claude/session-env`, `~/.codex/auth.json` mtime, and the login watcher are unchanged; confirm zero auth files/symlinks under the dedicated GLM home | G-07 | CONFIRMED |

## Repair

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
    codex exec using the dedicated GLM CODEX_HOME, and the launcher writes Codex's attested final
    message to the matching response file.
    The model shell tool is disabled, runs are serialized, malformed JSONL and any command or file
    change fail closed, and the accepted response must byte-match Codex's attested final message.
    R11 SHA 9c8d6a5c7e26ff0078e97cd7dfb0e3b96c199b56 retained schema enforcement and deleted a usable
    Markdown-fenced response; it was immediately forward-rolled back to 041f7d78. R13 removed that
    schema-only layer instead of adding fence parsing. Exact reviewed SHA
    c96cea2fcbbc0fb6b53d19f39becfc5b0cba734c was main and deployed for the S1566 proof on
    2026-08-16. Its 90-second low-effort
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
    main, checkout, and deployed marker equal the current reviewed deployment SHA, presently
    31c843b6b24779a5250cf406e5d1975e7b4f3177; health is OK; a request file produces its matching
    response file; session-env count, personal Codex auth mtime, and watcher bytes are unchanged;
    the dedicated GLM home has zero credential files and symlinks. The earlier c96cea2f proof SHA is
    retained history, not the current deployment target.
- id: G-05
  symptom_ref: F-05
  component_ref: Reviewer Trigger
  root_cause: The reviewer roster or a member model drifted between Living State and the deployed schema.
  repair_entry_point: Living State infra:council-comms plus the deployed reviewer registration
  change_pattern: Treat Living State infra:council-comms and the model registry as the only roster truth; reconcile the live callable schema and the required-member constants to it, and never substitute a member or reduce quorum to route around the gap.
  rollback_procedure: Block the gate and keep the recorded roster; do not edit prose to match a stale client.
  integrity_check: The live agent enum, the recorded roster, and the deployed SHA all name the same members.
```

## Changes and maintenance

### H.1 Invariants

- `council_request` is the only public Council reviewer trigger.
- `dispatch_mp_build` is the only separately advertised public build trigger.
- Build checking and listing are `council_request` actions, not separate tools.
- CC, Kimi, GLM, and DeepSeek all use `scripts/council_dir.py`.
- DeepSeek is registered for explicit-name shadow dispatch but affects no consensus, mandate, completion, override, spec-approval, all-reviewer expansion, or shared-health decision; gate-voter submission rejects it before forwarding and override roles are bound to authorized actor identities.
- One request file produces one response file in the same member directory.
- Responses are returned unchanged.
- One member runs at most one request; busy creates no request file.
- Dispatch returns a durable request ID immediately and polling never retries.
- MP build dispatch remains separate from reviewer transport.

### H.2 BREAKING predicates

- Adding another Council reviewer transport, Hall, wrapper, parser, retry layer, persistence step, or pre-dispatch reviewer gate is BREAKING.
- Routing MP through the reviewer directory is BREAKING.

### H.3 REVIEW predicates

- Changing a member CLI command, model, credential source, or directory location requires review and an end-to-end file exchange.

### H.4 SAFE predicates

- Correcting prose or tests to match the deployed one-file contract is SAFE.

### H.5 Boundary definitions

#### module

The reviewer module is `tools/agents.py:_handle_council_member` plus `scripts/council_dir.py`; GLM and DeepSeek use the parameterized path in `codex_reviewer_transport.py` through their provider wrappers.

#### public contract

The public contract is `council_request` returning `status=submitted`, `request_id`, request path, and response path immediately; `action=check_review` returns running/completed/failed/not_found and includes unchanged response text only when completed.

#### runtime dependency

A runtime dependency is the selected member CLI, its existing credential, and the writable member directory.

#### config default

The reviewer defaults are the member CLI commands and `/Users/max/council` root in `scripts/council_dir.py`, plus the dedicated GLM and DeepSeek homes and their checked config templates under `config/glm_codex/` and `config/deepseek_codex/`.

### H.6 Adjudication

Max resolves any request to add behavior between the request file and response file.

## Acceptance criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01, H.1]
    scenario: An existing request file is sent to Kimi through council_request.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, review_package_path]
        argument_values: {agent: kimi}
    weight: 0.25
  - id: I-02
    type: operate
    refs: [E-02, H.1]
    scenario: The same task text is sent separately to CC, Kimi, GLM, and DeepSeek.
    expected_answers:
      - kind: human_action
        verb: verify
        object: all four registered reviewers use the same directory handler
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
        target: council_request and dispatch_mp_build each present once; call_mp, call_claude_code, dispatch_build, check_build, and list_builds absent
    weight: 0.25
  - id: I-04
    type: operate
    refs: [E-05, H.1]
    scenario: Dispatch an MP build after the reviewer simplification.
    expected_answers:
      - kind: tool_call
        tool: dispatch_mp_build
        argument_keys: [task, repo, expected_branch, caller_instance, ref_entity]
    weight: 0.25
```

## Maintenance

```yaml lifecycle
last_refresh_session: S1605
last_refresh_commit: 75be0caab2efb6aa8af4c20566b3ec4365ea930d
last_refresh_date: 2026-08-26T09:16:22Z
owner_agent: vulcan
refresh_triggers:
  - council_request reviewer routing changes
  - a Council member CLI command changes
  - the Council directory or credential source changes
scheduled_cadence: 90d
first_staleness_detected_at: null
```
