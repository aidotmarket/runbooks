---
runbook_id: build-queue-reconciliation
domain: build-queue
status: ACTIVE
authoritative_for:
  - topic: build-queue-reconciliation
    section: §C. Architecture & Interactions
aliases: []
error_signatures:
  - signature: unsupported_target_repo
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: vulcan
last_verified_at: 2026-07-17
system_name: build-queue-reconciliation
purpose_sentence: Build Queue reconciliation keeps Living State, Build Queue status, and git evidence aligned before more build work is dispatched.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Reconciliation classifications, safe-patch invariants, dispatch and event triggers, audited bypass handling, bypass review, and poller cursor operations.
linter_version: 1.0.0
---

# Build Queue Reconciliation

## §A. Header

The YAML frontmatter above is the summary header. §J is authoritative for refresh and harness state.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Evidence classification and `cleanly_extends` evaluation | SHIPPED | `koskadeux-mcp:kd_reconcile_bq` | Strict lint and conformant scenario harness | 2026-07-17 |
| Trigger A pre-dispatch reconciliation | SHIPPED | `koskadeux-mcp:council_request` | Strict lint and conformant scenario harness | 2026-07-17 |
| Trigger B session-open advisory report | SHIPPED | `koskadeux-mcp:kd_session_open` | Strict lint and conformant scenario harness | 2026-07-17 |
| Trigger C manual reconciliation | SHIPPED | `koskadeux-mcp:kd_reconcile_bq` | Strict lint and conformant scenario harness | 2026-07-17 |
| Trigger D event-driven reconciliation | SHIPPED | `koskadeux-mcp:koskadeux_server.py` | Startup log signature checks and conformant scenario harness | 2026-07-17 |
| Weekly bypass-rate report | SHIPPED | `koskadeux-mcp/scripts/bypass_audit_report.py` | Manual report checklist and scheduled-job log signature | 2026-07-17 |
| Target-repository backfill | SHIPPED | `koskadeux-mcp/scripts/backfill_target_repos.py` | Dry-run-before-apply procedure | 2026-07-17 |

## §C. Architecture & Interactions

The reconciler core reads one BQ entity from Living State, fetches Build Queue status, fetches git evidence for every `body.target_repos` repository, reads the gate chunk plan from the local spec, and classifies drift.

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Reconciler Core | `kd_reconcile_bq` | `build:bq-*` Living State entities | Build Queue status, target-repository git logs, local gate spec | Produces a classification and evaluates whether evidence cleanly extends the recorded chunk plan. |
| Pre-dispatch Gate | `council_request(mode=build)` | BQ entity and reconciliation audit events | Reconciler Core, build dispatcher | Trigger A blocks risky dispatch until drift is patched, rejected, or bypassed with an audit justification. |
| Session-open Advisory | `kd_session_open` | In-progress BQ entities | Reconciler Core, session opening | Trigger B reports drift read-only and never mutates Living State or emits reconciliation events. |
| Event Pollers | `koskadeux_server.py:BackgroundScheduler` | `infra:build-queue-poller-cursor`, `infra:git-push-poller-cursor` | Build completion callbacks, Build Queue transitions, git pushes | Trigger D reacts to new evidence and patches only after successful audit emission on the safe path. |
| Bypass Audit | `scripts/bypass_audit_report.py:main` | `ls_drift_bypassed` events | Living State event listing, weekly handoff | Produces the rolling seven-day report manually or every Monday at 09:00 UTC. |
| Target Repo Backfill | `scripts/backfill_target_repos.py:main` | `body.target_repos` on BQ entities | Repository ownership evidence | Runs dry first, then applies only after ownership and target repositories are verified. |

### Classification reference

| Classification | Meaning | Example scenario | Operator action |
|---|---|---|---|
| `HIGH_CONFIDENCE_GIT_AHEAD` | Git contains completed chunk evidence that cleanly extends Living State. This is the only class eligible for automatic safe patching. | Living State says the next action is Chunk 2A, and all target repositories contain Chunk 2A commits with no revert evidence. | Use `auto_reconcile=true` or let Trigger D apply the safe patch. |
| `ADVISORY_GIT_AHEAD` | Git appears ahead, but confidence is insufficient for automatic mutation. | One target repository has the chunk commit, but another declared repository has no matching commit. | Inspect repositories and Build Queue history; do not auto-patch. |
| `ADVISORY_BUILD_QUEUE_AHEAD` | Build Queue appears ahead of Living State, but git evidence is not sufficient for automatic mutation. | Build Queue marks a chunk complete, but git evidence is missing or incomplete. | Verify builder output and commits; patch manually only after evidence is clear. |
| `AMBIGUOUS` | Evidence conflicts or a dependency failed. | Git fetch fails, Build Queue is unreachable, or evidence includes a revert. | Treat as degraded evidence; resolve the failure or inspect manually. |
| `LS_AHEAD_SUSPECTED` | Living State records progress that git or Build Queue evidence does not confirm. | Living State lists Chunk 3 built while git and Build Queue only support Chunk 2. | Audit recent Living State writes before dispatching dependent work. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan | Inspect or reconcile one BQ and review bypass rates | `kd_reconcile_bq`, `scripts/bypass_audit_report.py` | Living State read; mutation only on an explicitly safe or verified path | COMPLETE |
| Council dispatcher | Run Trigger A before build dispatch | `council_request(mode=build)` | Build dispatch and audited reconciliation arguments | COMPLETE |
| Session opener | Report Trigger B drift | `kd_session_open` | Read-only across in-progress BQs | COMPLETE |
| Event scheduler | Run Trigger D after new evidence | `koskadeux_server.py` pollers and callbacks | Poller cursors, reconciliation audit events, safe Living State patch | COMPLETE |
| Max | Adjudicate unsupported ownership or an intentional unsafe bypass request | Human escalation | Final operational decision | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: A build dispatch with a BQ code reaches the Trigger A reconciliation gate.
  pre_conditions: [BQ_entity_exists, body_target_repos_are_declared, gate_spec_is_readable, build_dispatch_context_is_available]
  tool_or_endpoint: council_request(mode=build, bq_code=<code>, auto_reconcile=<bool>, bypass_reconcile=<bool>, reconcile_justification=<text>)
  argument_sourcing:
    bq_code: read from the requested Build Queue entity
    auto_reconcile: set true only for HIGH_CONFIDENCE_GIT_AHEAD with cleanly_extends=true
    bypass_reconcile: set true only for an intentional human decision to proceed without patching Living State
    reconcile_justification: obtain the concrete evidence or outage reason from the human authorizing the bypass
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: BQ code plus observed Living State version plus proposed next chunk
  expected_success: {shape: dispatch proceeds after no drift, an appended safe patch plus ls_drift_reconciled event, or an ls_drift_bypassed audit event, verification: Compare the BQ entity, classification, target-repository evidence, emitted event, and dispatch result}
  expected_failures:
    - {signature: unsupported_target_repo, cause: body.target_repos is missing or outside the supported aidotmarket scope}
    - {signature: unsafe_or_advisory_drift, cause: classification or cleanly_extends result does not permit automatic mutation}
  next_step_success: Continue the requested build dispatch and retain its reconciliation evidence.
  next_step_failure: Reject dispatch until the matching §F diagnosis is repaired or Max authorizes a specific audited bypass.
- id: E-02
  trigger: A session opens and needs a read-only drift report across in-progress BQs.
  pre_conditions: [session_is_opening, in_progress_BQs_can_be_listed]
  tool_or_endpoint: kd_session_open
  argument_sourcing: {}
  idempotency: IDEMPOTENT
  expected_success: {shape: advisory reconciliation report for in-progress BQs, verification: Confirm the report contains classifications and no Living State mutation or reconciliation event}
  expected_failures:
    - {signature: degraded_evidence, cause: Build Queue, git, or gate-plan evidence could not be read}
  next_step_success: Use the advisory report to choose which BQ needs inspection before dispatch.
  next_step_failure: Treat affected BQs as AMBIGUOUS and repair the unavailable evidence source.
- id: E-03
  trigger: An operator requests on-demand inspection or correction for one BQ.
  pre_conditions: [BQ_entity_exists, target_repo_evidence_can_be_fetched, gate_spec_path_is_known]
  tool_or_endpoint: kd_reconcile_bq(bq_code=<code>, auto_reconcile=<bool>)
  argument_sourcing:
    bq_code: read from the operator request or Build Queue entity
    auto_reconcile: set true only after the report shows HIGH_CONFIDENCE_GIT_AHEAD and cleanly_extends=true
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: BQ code plus observed Living State version plus proposed next chunk
  expected_success: {shape: one reconciliation report and optional safe Living State append, verification: Confirm existing chunks remain unchanged, all target repositories support the next chunk, and gate status is unchanged}
  expected_failures:
    - {signature: advisory_or_ambiguous_classification, cause: evidence does not meet the safe-patch invariant}
    - {signature: chunk_plan_unavailable, cause: gate spec or chunk sequence cannot be resolved}
  next_step_success: Record the report and continue only from the reconciled or already-consistent state.
  next_step_failure: Follow the matching §F/§G entry and rerun after evidence is repaired.
- id: E-04
  trigger: Build completion, a Build Queue transition, or a git push supplies new reconciliation evidence.
  pre_conditions: [event_payload_is_available, poller_or_callback_is_running, BQ_entity_can_be_resolved]
  tool_or_endpoint: Trigger D build completion callback or Build Queue/git push poller
  argument_sourcing:
    event payload: read from the callback or the poller result
    BQ entity: resolve from the event payload and Living State
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: event identity plus BQ code plus observed Living State version
  expected_success: {shape: audit event followed by a safe patch, or an advisory report with no patch, verification: Confirm audit emission preceded any mutation and cursor advancement reflects processed evidence}
  expected_failures:
    - {signature: audit_emission_failed, cause: the required reconciliation audit event could not be persisted}
    - {signature: poller_dependency_outage, cause: Build Queue or GitHub evidence is unavailable or rate-limited}
  next_step_success: Leave the BQ aligned or advisory-only and allow the poller to continue.
  next_step_failure: Do not patch; preserve the cursor and repair the event or dependency failure.
- id: E-05
  trigger: The weekly rolling seven-day bypass-rate review is due.
  pre_conditions: [koskadeux_mcp_checkout_exists, Living_State_events_are_queryable]
  tool_or_endpoint: python3 scripts/bypass_audit_report.py --days 7
  argument_sourcing: {}
  idempotency: IDEMPOTENT
  expected_success: {shape: markdown table of BQ, session, bypass count, caller, and justifications, verification: Confirm the report covers a UTC window beginning seven days before execution}
  expected_failures:
    - {signature: report_query_failed, cause: ls_drift_bypassed events could not be listed}
  next_step_success: Review repeated BQ/session pairs and open a follow-up BQ if one failure mode clusters.
  next_step_failure: Restore Living State event access and rerun without changing reconciliation state.
```

### Bypass procedure

Use `auto_reconcile=true` when the reconciler reports `HIGH_CONFIDENCE_GIT_AHEAD`, `cleanly_extends=true`, and the proposed patch only appends the next chunk and advances `next_action`. The system applies the Living State patch, emits `ls_drift_reconciled`, and then proceeds.

Use `bypass_reconcile=true` only when a human intentionally wants to proceed without patching Living State. Include `reconcile_justification` with the concrete reason, such as "Build Queue outage; verified Chunk 2A commit in target repo manually." Bypasses emit `ls_drift_bypassed` with caller, session, classification, Living State state, and justification. Missing or vague justifications are review findings.

Do not use bypass to avoid a clean safe patch. Do not bypass unsupported target repositories until repository ownership is confirmed and `body.target_repos` is corrected.

### Weekly bypass-rate review checklist

Run the report over a rolling seven-day window:

```bash
cd /Users/max/koskadeux-mcp
python3 scripts/bypass_audit_report.py --days 7
```

The script queries:

```json
{
  "action": "list",
  "event_type": "ls_drift_bypassed",
  "updated_since": "<UTC timestamp for now minus 7 days>"
}
```

Paste this markdown table into the weekly session handoff:

```markdown
| BQ | Session | Bypass Count | Caller | Justifications |
|---|---|---|---|---|
```

Review steps:

1. Sort by highest bypass count.
2. For each repeated BQ/session pair, confirm each justification references concrete evidence or a known outage.
3. Confirm there is no pattern of bypassing clean `HIGH_CONFIDENCE_GIT_AHEAD` patches.
4. For unsupported or missing `target_repos`, run the backfill script in dry-run mode and patch Living State after verification:

   ```bash
   python3 scripts/backfill_target_repos.py
   python3 scripts/backfill_target_repos.py --apply
   ```

5. File a follow-up BQ if bypasses cluster around the same failure mode.

Scheduling option: the weekly report is registered in `koskadeux_server.py` through `BackgroundScheduler` as `build_queue_bypass_audit_report`. It runs Mondays at 09:00 UTC and writes the markdown table to the server log. For a manual-only deployment, keep using the command above.

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Reconciler reports `error_code=build_queue_unreachable`, Trigger B shows an outage flag, or the poller logs `poll skipped after API outage`. | Build Queue dependency is unavailable. | Check backend health and confirm whether git evidence remains independently readable. | §G-01 | CONFIRMED |
| F-02 | Reconciler reports `error_code=git_fetch_failed` or the git push poller logs `git push poll skipped`. | GitHub token, network, repository access, branch name, outage, or rate limit prevents evidence fetch. | Check token, connectivity, repository access, and branch; require `git fetch origin` to succeed. | §G-02 | CONFIRMED |
| F-03 | Reconciler reports `chunk_plan_unavailable`. | `gate{N}.spec_path` is wrong, the local spec is absent, or the chunk sequence is unreadable. | Resolve the BQ gate spec path and confirm its local `specs/` file contains the chunk plan. | §G-03 | CONFIRMED |
| F-04 | Reconciler reports `unsupported_target_repo`. | `body.target_repos` is missing or names a repository outside the supported `aidotmarket/*` scope. | Confirm repository ownership and compare the BQ target list with the repositories that contain chunk evidence. | §G-04 | CONFIRMED |
| F-05 | Classification is `AMBIGUOUS` or `LS_AHEAD_SUSPECTED`. | Evidence conflicts, includes a later revert, or Living State contains progress that git and Build Queue do not confirm. | Compare Living State chunks, Build Queue history, all target-repository commits, and revert evidence before dispatch. | §G-05 | CONFIRMED |
| F-06 | Trigger D has safe evidence but no patch occurs and audit emission failed. | The required audit event could not be written. | Inspect event persistence for `ls_drift_reconciled` and confirm no Living State mutation followed the failed emission. | §G-06 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Reconciler Core
  root_cause: Build Queue evidence is unavailable.
  repair_entry_point: Build Queue backend health and reconciliation retry
  change_pattern: Restore backend health and rerun reconciliation; do not auto-patch from unavailable Build Queue evidence, and bypass only with manually verified git evidence plus a specific justification.
  rollback_procedure: Stop the retry or bypass and leave Living State unchanged if independent evidence cannot be confirmed.
  integrity_check: Confirm Build Queue status is readable and the rerun classification is supported by both status and git evidence.
- id: G-02
  symptom_ref: F-02
  component_ref: Event Pollers
  root_cause: Git evidence could not be fetched from a declared target repository.
  repair_entry_point: git fetch origin
  change_pattern: Correct the GitHub token, network access, repository permission, or branch name, then rerun only after git fetch origin succeeds.
  rollback_procedure: Revert any credential or branch correction that does not restore the intended repository access and preserve the poller cursor.
  integrity_check: Confirm every declared target repository can be fetched and contributes evidence to the new classification.
- id: G-03
  symptom_ref: F-03
  component_ref: Reconciler Core
  root_cause: The configured gate spec path or local chunk plan is unavailable.
  repair_entry_point: gate{N}.spec_path and local specs file
  change_pattern: Correct the spec path or restore the referenced spec, then rerun reconciliation without patching until the chunk sequence is readable.
  rollback_procedure: Restore the prior gate spec reference if the correction points at a non-authoritative plan; keep Living State unchanged.
  integrity_check: Confirm the proposed chunk is exactly the next chunk in the resolved gate plan.
- id: G-04
  symptom_ref: F-04
  component_ref: Target Repo Backfill
  root_cause: The BQ target-repository list is missing, unsupported, or inconsistent with ownership evidence.
  repair_entry_point: scripts/backfill_target_repos.py:main
  change_pattern: Confirm ownership, run the backfill script in dry-run mode, then apply the verified body.target_repos correction and rerun reconciliation.
  rollback_procedure: Restore the prior BQ target list using its previous Living State version if the applied repository set is wrong.
  integrity_check: Confirm every corrected target repository is supported and contains or legitimately lacks the chunk evidence reported by the reconciler.
- id: G-05
  symptom_ref: F-05
  component_ref: Reconciler Core
  root_cause: Living State, Build Queue, and git do not form one safe monotonic extension.
  repair_entry_point: kd_reconcile_bq
  change_pattern: Resolve dependency failures or manually audit recent Living State writes, Build Queue history, commits, and reverts; patch only after evidence becomes clear.
  rollback_procedure: Do not apply or retain any patch that rewrites existing chunks, skips the next planned chunk, lacks evidence in a target repository, ignores a revert, or changes gate status.
  integrity_check: Re-evaluate all five cleanly_extends conditions and require HIGH_CONFIDENCE_GIT_AHEAD before automatic mutation.
- id: G-06
  symptom_ref: F-06
  component_ref: Event Pollers
  root_cause: Trigger D could not persist its audit event before the proposed patch.
  repair_entry_point: Living State reconciliation event emission
  change_pattern: Restore audit-event persistence and replay the event-driven reconciliation from the preserved cursor and source evidence.
  rollback_procedure: Leave the BQ unpatched and keep the cursor at the unprocessed event if audit persistence remains unavailable.
  integrity_check: Confirm the audit event is durable before the safe patch and that replay does not append the same chunk twice.
```

### Poller cursor operations and healthy signatures

| Poller | Cursor key |
|---|---|
| Build Queue transition poller | `infra:build-queue-poller-cursor` |
| Git push poller | `infra:git-push-poller-cursor` |

To inspect a cursor:

```json
{"action":"get","key":"infra:build-queue-poller-cursor"}
{"action":"get","key":"infra:git-push-poller-cursor"}
```

To reset a cursor, patch or put the cursor body with an empty position after confirming no in-flight events depend on it:

```json
{"action":"put","key":"infra:build-queue-poller-cursor","kind":"infra","summary":"Reset Build Queue poller cursor","body":{},"updated_by":"vulcan","source_ref":"build-queue-reconciliation-runbook","expected_version":<current_version>}
{"action":"put","key":"infra:git-push-poller-cursor","kind":"infra","summary":"Reset git push poller cursor","body":{"repos":{}},"updated_by":"vulcan","source_ref":"build-queue-reconciliation-runbook","expected_version":<current_version>}
```

Verify pollers are running from `koskadeux_server.py` startup logs:

| Component | Healthy or diagnostic log signature |
|---|---|
| Scheduler startup | `Trigger D pollers started` |
| Build Queue poller registration | `build_queue poller registered` |
| Git push poller registration | `git_push poller registered` |
| Bypass audit report registration | `bypass audit report job registered` |
| Build Queue outage | `build_queue poll skipped after API outage` |
| GitHub outage/rate limit | `git push poll skipped` or `git push poll rate-limited` |
| Weekly bypass report | `weekly ls_drift_bypassed report` |

## §H. Evolve

The change-class predicates are evaluated in order; the first matching class wins.

### §H.1 Invariants

- The proposed chunk must be the next chunk in the gate chunk plan.
- Existing Living State chunk entries must be preserved and never rewritten.
- Every declared `target_repos` repository must have evidence for the proposed chunk.
- No later revert or contradictory git evidence may invalidate the proposed chunk.
- A reconciliation patch must not mutate `gate{N}.status`.
- Trigger B remains read-only and cannot emit reconciliation events.
- Trigger D emits its audit event before any safe patch.

### §H.2 BREAKING predicates

- A change is BREAKING if it changes a public contract without a backwards-compatible shim.
- A change is BREAKING if it changes a data-model field type, removes a field, or adds a required field without a default.
- A change is BREAKING if it removes or weakens any §H.1 invariant.
- A change is BREAKING if it changes an authorization boundary or permits a new caller to mutate Living State.

### §H.3 REVIEW predicates

- After BREAKING predicates fail, a new reconciliation feature on an existing public surface requires REVIEW.
- A refactor that creates, deletes, or moves code across module boundaries requires REVIEW.
- A change to a canonical config default, including poll cadence or supported repository scope, requires REVIEW.
- A new runtime dependency requires REVIEW.

### §H.4 SAFE predicates

- A bug fix within existing reconciliation semantics is SAFE.
- A documentation update or test addition is SAFE.
- An internal refactor within one module that preserves public signatures and every §H.1 invariant is SAFE.

### §H.5 Boundary definitions

#### module

A module is an immediate subdirectory of the Koskadeux MCP source root. Scripts and tests are peer trees rather than product modules.

#### public contract

The public contract includes the MCP signatures for `council_request`, `kd_session_open`, and `kd_reconcile_bq`, the reconciliation classifications, emitted event shapes, and published CLI flags.

#### runtime dependency

A runtime dependency is an entry in the system's runtime dependency declaration; development, test, and optional-only dependencies are excluded.

#### config default

A config default is a value shipped in canonical Koskadeux configuration, including poll cadence and supported repository scope; environment overrides and test-only values are excluded.

### §H.6 Adjudication

If two agents classify a change differently, the more restrictive class wins. Max resolves any remaining dispute, especially one that would weaken a safe-patch invariant or expand mutation authority.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: A build dispatch finds high-confidence git-ahead drift that cleanly appends the next chunk.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [mode, bq_code, auto_reconcile]
        argument_values: {mode: build, auto_reconcile: true}
    weight: 0.08333333333333333
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: A session opener needs a read-only report of drift across in-progress Build Queue entities.
    expected_answers:
      - kind: tool_call
        tool: kd_session_open
        argument_keys: []
    weight: 0.08333333333333333
  - id: I-03
    type: operate
    refs: [E-05]
    scenario: The weekly operator needs the rolling seven-day audit of reconciliation bypasses.
    expected_answers:
      - kind: tool_call
        tool: python3 scripts/bypass_audit_report.py --days 7
        argument_keys: []
    weight: 0.08333333333333333
  - id: I-04
    type: isolate
    refs: [F-01, G-01]
    scenario: Reconciliation reports build_queue_unreachable before a proposed automatic patch.
    expected_answers:
      - kind: human_action
        verb: verify
        object: Build Queue backend health
        target: Build Queue dependency before reconciliation retry
    weight: 0.08333333333333333
  - id: I-05
    type: isolate
    refs: [F-02, G-02]
    scenario: The git push poller logs that its poll was skipped and repository evidence is missing.
    expected_answers:
      - kind: human_action
        verb: run
        object: git fetch origin
        target: every declared target repository
    weight: 0.08333333333333333
  - id: I-06
    type: isolate
    refs: [F-04, G-04]
    scenario: A BQ cannot reconcile because body.target_repos is missing or unsupported.
    expected_answers:
      - kind: human_action
        verb: confirm
        object: repository ownership
        target: body.target_repos before dry-run backfill
    weight: 0.08333333333333333
  - id: I-07
    type: repair
    refs: [G-03, F-03]
    scenario: The reconciler cannot read the chunk sequence because the gate spec path is wrong.
    expected_answers:
      - kind: human_action
        verb: correct
        object: gate spec path
        target: gate{N}.spec_path and local specs file
    weight: 0.08333333333333333
  - id: I-08
    type: repair
    refs: [G-06, F-06]
    scenario: Trigger D has safe evidence but audit event persistence failed before the patch.
    expected_answers:
      - kind: human_action
        verb: restore
        object: reconciliation audit-event persistence
        target: Living State before replaying Trigger D
    weight: 0.08333333333333333
  - id: I-09
    type: evolve
    refs: [§H]
    scenario: A proposal allows automatic reconciliation to rewrite an existing Living State chunk.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-10
    type: evolve
    refs: [§H]
    scenario: A proposal changes the default Build Queue poll cadence without changing public signatures.
    expected_answers:
      - kind: classification
        label: REVIEW
    weight: 0.08333333333333333
  - id: I-11
    type: ambiguous
    refs: [F-05, G-05]
    scenario: Living State says a later chunk is built while Build Queue and git support only an earlier chunk.
    expected_answers:
      - kind: human_action
        verb: audit
        object: recent Living State writes
        target: BQ chunks against Build Queue history, commits, and reverts
    weight: 0.08333333333333333
  - id: I-12
    type: ambiguous
    refs: [E-01, F-01, F-05]
    scenario: Build Queue is down but a human has manually verified git evidence and wants dispatch to continue.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [mode, bq_code, bypass_reconcile, reconcile_justification]
        argument_values: {mode: build, bypass_reconcile: true}
    weight: 0.08333333333333333
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1265
last_refresh_commit: 03cd4c0
last_refresh_date: 2026-07-17T20:00:00Z
owner_agent: vulcan
refresh_triggers:
  - reconciliation classification or cleanly_extends invariant changes
  - trigger, bypass, audit-event, or poller behavior changes
  - Build Queue or Living State incident
  - runbook-lint or runbook-harness schema changes
scheduled_cadence: 90d
last_harness_pass_rate: 1.0
last_harness_date: 2026-07-17T20:00:00Z
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1265 / 2026-07-17T20:00:00Z
last_lint_result: PASS
retrofit: false
trace_matrix_path: null
word_count_delta: null
```
