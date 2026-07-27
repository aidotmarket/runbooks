---
runbook_id: policy-kernel-enforcement
domain: council-operations
status: ACTIVE
authoritative_for:
  - topic: policy-kernel-enforcement
    section: §C. Architecture & Interactions
aliases: []
error_signatures:
  - signature: policy_kernel_not_evaluable
    section: §F. Isolate
  - signature: policy_kernel_enforcement_setting_invalid
    section: §F. Isolate
  - signature: policy_kernel_preflight_indeterminate
    section: §F. Isolate
  - signature: dispatch_terminal_state_missing_after_restart
    section: §F. Isolate
  - signature: deployed_sha_stale
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: vulcan
last_verified_at: 2026-07-27
system_name: policy-kernel-enforcement
purpose_sentence: Operate, diagnose, and safely roll back the live Policy Kernel enforcement path on the Council compliance gate.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: |
  The Council compliance gate Policy Kernel enforcement switch, readiness preflight, refusal alert, restart safety, break-glass continuity, and rollback. This runbook does not change the legacy parity adapter, break_glass, or author-dispatch behavior.

  Cross-runbook reference convention: same-file references use bare IDs such as `F-01` or `G-01`; cross-file references use `<file-stem>:<id>`.
linter_version: 1.0.0
---

# Policy Kernel Enforcement Gate

## §A. Header

The YAML frontmatter above defines the §A header.

### Live activation record

As of 2026-07-27, enforcement is **ON**, `main` is `6b03e99e`, and the handler was restarted at `09:56:32`. The committed switch default remains the literal string `off`.

This is a live, load-bearing gate. A restart can destroy in-flight dispatches, and an invalid switch value causes a full gate outage. Follow the restart guard in E-01 before every kickstart.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Explicit `off`/`on` enforcement switch | SHIPPED | `council_compliance_gate.py:read_council_gate_policy_kernel_enforcement` | Default, exact values, and invalid-value fail-closed tests | 2026-07-27 |
| Policy Kernel authoritative decision path | SHIPPED | `council_compliance_gate.py:CouncilComplianceGate._record_hard_floor_parity` | Kernel allow/refuse, multi-observation, and `not_evaluable` tests | 2026-07-27 |
| Legacy-path parity recording during enforcement | SHIPPED | `council_compliance_gate.py:_record_hard_floor_parity` | Parity and disagreement-warning tests | 2026-07-27 |
| Legacy-allow refusal alert and process counter | SHIPPED | `council_compliance_gate.py:COUNCIL_GATE_POLICY_KERNEL_LEGACY_ALLOW_REFUSAL_MARKER` | Marker payload and counter-increment test | 2026-07-27 |
| Enablement readiness preflight | SHIPPED | `council_compliance_gate.py:council_gate_policy_kernel_preflight` | Ready, not-ready, pagination, database, and indeterminate tests | 2026-07-27 |
| Exact off/on/off rollback | SHIPPED | `tests/test_council_gate_kernel_enforcement.py:test_off_on_off_restores_the_exact_original_outcome` | Exact original outcome restored by off/on/off test | 2026-07-27 |
| Existing `break_glass` short-circuit | SHIPPED | `council_compliance_gate.py:CouncilComplianceGate.check` | Four tests: three bypass cases and one control | 2026-07-27 |

## §C. Architecture & Interactions

The switch `COUNCIL_GATE_POLICY_KERNEL_ENFORCEMENT` is read by `read_council_gate_policy_kernel_enforcement` in `/Users/max/koskadeux-mcp/council_compliance_gate.py`. Its committed default is exactly `off`. Only exact `off` and `on` values are accepted; any other value raises, and the compliance gate converts that configuration error into a refusal. A typo is therefore a full Council-gate outage.

The live value is stored in `/Users/max/koskadeux-mcp/.env`. Changing the file does not change the running handler: the value takes effect only after `com.koskadeux.mcp` restarts.

With enforcement `on`, the Policy Kernel is the authoritative decision path on the Council-gate surface. The legacy adapter still executes so parity continues to be recorded. Kernel statuses `satisfied` and `not_applicable` allow; `not_evaluable` never allows and fails closed. This tightens accepted request shapes. The measured example is an omitted `target_gate`: the legacy path defaulted it to Gate 1 and proceeded, while the kernel records the fact as unavailable and refuses.

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Enforcement Switch | `read_council_gate_policy_kernel_enforcement` | `/Users/max/koskadeux-mcp/.env` | `CouncilComplianceGate` | Committed default `off`; only `off` and `on` are valid; restart required. |
| Council Compliance Gate | `CouncilComplianceGate.check` | Request arguments and Living State gate facts | Legacy adapter, Policy Kernel, `break_glass` | `break_glass` is checked before every enforcement point. |
| Policy Kernel Decision | `_record_hard_floor_parity` -> `evaluate_council_gate_hard_floor` | Typed policy-fact envelope | Council Compliance Gate | Authoritative when enforcement is `on`; `not_evaluable` refuses. |
| Legacy Parity Adapter | `compare_council_gate_parity` | Structured parity log event | Policy Kernel Decision | Continues to run with enforcement on; it is not the authoritative decision path. |
| Refusal Alert | `COUNCIL_GATE_KERNEL_ENFORCEMENT_REFUSED_LEGACY_ALLOW` | `/tmp/koskadeux_mcp.log`; process-lifetime counter | Incident monitoring | Warning includes predicate, kernel status, and count since process start. |
| Readiness Preflight | `council_gate_policy_kernel_preflight` | Read-only live build inventory | Living State HTTP or database scan | Scans only the known sentinel-lease divergence. |
| Dispatch Task Store | `/var/tmp/koskadeux/cc_tasks` | `<task>.meta.json`, `<task>.done`, result files | Council and build worker threads | A record blocks restart when it is LIVE, or INDETERMINATE and not yet resolved by the reaper. |
| Handler LaunchAgent | `com.koskadeux.mcp` | Running process and `/tmp/koskadeux_mcp.log` | `/Users/max/koskadeux-mcp` checkout | Kickstart kills worker threads and every in-flight Council/build dispatch. |
| Emergency Lever | `break_glass` | Existing break-glass sentinel and audit path | First statement in `CouncilComplianceGate.check` | Still works with enforcement on. `emergency_authority` is not this lever. |

### Ground truth for deployed code

`/var/tmp/koskadeux/deployed_sha` is stale and does not update on a manual kickstart. Never use it as deployment ground truth. Bind a deployment claim to both:

1. the handler process start time; and
2. the checkout SHA that was present at that time.

Before a planned restart, record `git -C /Users/max/koskadeux-mcp rev-parse HEAD`. After restart, capture the new handler PID and process start time. If this evidence was not captured contemporaneously, compare the process start time with the checkout reflog; do not substitute `deployed_sha`.

### Restart destroys in-flight dispatches

Restarting `com.koskadeux.mcp` kills the dispatching process and all of its worker threads. In-flight Council and build dispatches do not write a terminal state, and recovery is unavailable. Four dispatches were destroyed this way on 2026-07-27.

Before any restart, run the liveness check:

```bash
python3 /Users/max/koskadeux-mcp/scripts/check_dispatch_liveness.py
```

It classifies every task record as LIVE, TERMINAL or INDETERMINATE and exits non-zero when a restart is unsafe. Never restart while any record is LIVE. An INDETERMINATE record is also a stop condition, but unlike the old procedure it is answerable: the reaper in `claude_code_client.reap_abandoned_tasks` writes terminal state for records whose owner process is provably gone, and ages out records carrying no owner identity after 24 hours. Run the reaper, then run the check again.

The earlier version of this procedure told operators to stop on any `.meta.json` without a matching `.done`. That check was unsatisfiable and was therefore routinely bypassed with private ad-hoc checks. On 2026-07-27 it reported 135 blocking records, 134 of which carried no owner identity at all and so could never be resolved by waiting. It was replaced under T-2026-000437.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Council operator | Run preflight, inspect configuration, inventory tasks, monitor warnings | Shell, Python preflight, log inspection | Read checkout/task state; controlled `.env` and LaunchAgent change | COMPLETE |
| Incident responder | Roll back enforcement or invoke existing break-glass procedure | `.env`, `launchctl`, `break_glass` | Emergency gate operations under existing authorization | COMPLETE |
| Council caller | Supply complete request facts including explicit `target_gate` | Council dispatch surface | Request submission only | COMPLETE |
| Policy Kernel | Evaluate Council hard-floor predicates | `evaluate_council_gate_hard_floor` | Deterministic decision only | COMPLETE |
| Legacy parity adapter | Record comparison against the legacy outcome | `compare_council_gate_parity` | Telemetry only while enforcement is on | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: Any operator is about to restart `com.koskadeux.mcp`, including for enablement or rollback.
  pre_conditions:
    - "`/var/tmp/koskadeux/cc_tasks` is readable"
    - the intended checkout SHA is known
    - no restart command has been issued
  tool_or_endpoint: Run `python3 /Users/max/koskadeux-mcp/scripts/check_dispatch_liveness.py`. It exits 0 when `safe_to_restart` is true. On a non-zero exit, run the reaper once and run the check again. Record the checkout SHA and kickstart only on a zero exit, or under an explicit named waiver from Max.
  argument_sourcing:
    task directory: "default `/var/tmp/koskadeux/cc_tasks`; override with `--tasks-dir`"
    intended SHA: "`git -C /Users/max/koskadeux-mcp rev-parse HEAD`"
    launch label: "literal `gui/$(id -u)/com.koskadeux.mcp`"
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: "`safe_to_restart` true with `live_count` zero, recorded checkout SHA, new handler PID and start time, and a healthy handler."
    verification: Confirm the check exits 0; after kickstart compare the new process start time with the recorded checkout SHA.
  expected_failures:
    - signature: dispatch_in_flight
      cause: "`live_count` is above zero. A dispatch is provably running and restarting would destroy it."
    - signature: dispatch_indeterminate
      cause: Records remain INDETERMINATE after a reaper run, because owner identity is missing and the 24 hour age-out has not yet expired.
    - signature: task_inventory_unreadable
      cause: The operator cannot read the dispatch directory.
  next_step_success: Proceed to E-02 for enablement or E-04 for rollback.
  next_step_failure: On `dispatch_in_flight`, stop and wait for the dispatch to finish. On `dispatch_indeterminate`, either wait for the age-out or obtain an explicit waiver from Max naming the specific records, and record the restart as proceeding under waiver and not as a passing check. Never clear a record by hand to turn the check green.
- id: E-02
  trigger: An authorized operator is preparing to enable Policy Kernel enforcement.
  pre_conditions:
    - E-01 restart guard can be satisfied
    - the live build inventory is readable
    - "`/Users/max/koskadeux-mcp/.env` is backed up"
  tool_or_endpoint: Run `council_gate_policy_kernel_preflight`, require `status=ready`, set `COUNCIL_GATE_POLICY_KERNEL_ENFORCEMENT=on` in `.env`, then use E-01 to restart.
  argument_sourcing:
    environment file: "literal `/Users/max/koskadeux-mcp/.env`"
    preflight: "`council_compliance_gate.council_gate_policy_kernel_preflight`"
    accepted setting: "literal `on`"
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: Preflight reports `ready`; restarted handler reads `on`; refusal-marker monitoring is active.
    verification: Confirm the exact `.env` line, bind the new process start time to the checkout SHA, and follow `/tmp/koskadeux_mcp.log` for the refusal marker.
  expected_failures:
    - signature: policy_kernel_preflight_indeterminate
      cause: Inventory completeness, dependency health, clock, or a sentinel lease could not be evaluated.
    - signature: policy_kernel_preflight_not_ready
      cause: The known sentinel-lease scan found a currently allowed decision that enforcement would change.
  next_step_success: Continue with E-03 monitoring.
  next_step_failure: Treat `indeterminate` and `not_ready` as not ready; do not enable.
- id: E-03
  trigger: Enforcement has just been enabled or an incident responder is evaluating newly refused requests.
  pre_conditions:
    - handler has restarted with the intended checkout
    - "`/tmp/koskadeux_mcp.log` is readable"
  tool_or_endpoint: Follow `/tmp/koskadeux_mcp.log` for `COUNCIL_GATE_KERNEL_ENFORCEMENT_REFUSED_LEGACY_ALLOW`.
  argument_sourcing:
    log path: "literal `/tmp/koskadeux_mcp.log`"
    marker: "literal `COUNCIL_GATE_KERNEL_ENFORCEMENT_REFUSED_LEGACY_ALLOW`"
    fields: "`predicate`, `kernel_status`, and `count_since_process_start`"
  idempotency: IDEMPOTENT
  expected_success:
    shape: Every kernel refusal of a legacy allow is visible at warning level with predicate, status, and process-lifetime count.
    verification: Correlate marker timestamps and fields with the refused request shape; remember the count resets on process restart.
  expected_failures:
    - signature: policy_kernel_new_refusal
      cause: Enforcement refused a request the legacy path would have allowed.
  next_step_success: Correct an incomplete request shape when safe, or keep enforcement on when the refusal is intended.
  next_step_failure: Use F-01/G-01; roll back if the live impact requires immediate restoration.
- id: E-04
  trigger: Enforcement must be rolled back because of live impact or an invalid switch value.
  pre_conditions:
    - E-01 restart guard is satisfied
    - rollback choice is either exact `off` or the known backup
  tool_or_endpoint: Set `COUNCIL_GATE_POLICY_KERNEL_ENFORCEMENT=off` in `/Users/max/koskadeux-mcp/.env`, or restore `/Users/max/koskadeux-mcp/.env.s1364.bak`, then run `launchctl kickstart -k gui/$(id -u)/com.koskadeux.mcp`.
  argument_sourcing:
    accepted setting: "literal `off`"
    backup: "literal `/Users/max/koskadeux-mcp/.env.s1364.bak`"
    launch label: "literal `gui/$(id -u)/com.koskadeux.mcp`"
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: A new handler process runs with enforcement off and the original legacy outcome is restored.
    verification: Bind the new process start time to the checkout SHA and exercise the previously divergent request; the off/on/off test proves exact original-outcome restoration.
  expected_failures:
    - signature: policy_kernel_enforcement_setting_invalid
      cause: The restored or edited value is not exact `off` or `on`.
    - signature: dispatch_terminal_state_missing_after_restart
      cause: The restart occurred while a dispatch lacked `.done`.
  next_step_success: Keep monitoring the handler and preserve incident evidence.
  next_step_failure: Use F-02 or F-04; do not perform repeated restarts until the task inventory is clear.
- id: E-05
  trigger: An authorized emergency requires bypassing the Council compliance gate while enforcement remains on.
  pre_conditions:
    - emergency use is authorized under the existing break-glass procedure
    - the responder understands that `emergency_authority` is inert
  tool_or_endpoint: Use the existing `break_glass` lever; its short-circuit is the first statement in `CouncilComplianceGate.check`.
  argument_sourcing:
    lever: existing `break_glass` procedure and sentinel
    non-lever: "`emergency_authority.py`, which has zero non-test call sites"
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: "`CouncilComplianceGate.check` returns allow before any enforcement point is reached."
    verification: Confirm the break-glass audit evidence and that the kernel/legacy decision path was not evaluated for the bypassed call.
  expected_failures:
    - signature: wrong_emergency_lever
      cause: The responder attempted to use the inert `emergency_authority` module.
  next_step_success: Complete the bounded emergency action and follow the existing break-glass cleanup/audit procedure.
  next_step_failure: Escalate to Max; do not weaken the enforcement code.
```

### Preflight command

Run from the Koskadeux checkout:

```bash
cd /Users/max/koskadeux-mcp
venv/bin/python - <<'PY'
import json
from dotenv import load_dotenv
from council_compliance_gate import council_gate_policy_kernel_preflight

load_dotenv()
print(json.dumps(council_gate_policy_kernel_preflight(), indent=2, sort_keys=True))
PY
```

Interpretation:

- `status=ready`: the complete scan found no current divergence in the one known class it checks.
- `status=not_ready`: enabling would change a currently allowed decision in the known sentinel-lease class.
- `status=indeterminate`: the scan could not establish an answer; the result includes `reason`.

Treat both `not_ready` and `indeterminate` as not ready. A `ready` result is narrow: the preflight scans only the known sentinel-lease divergence. It does not prove that another request shape will not newly refuse.

### Mandatory pre-restart liveness check

```bash
python3 /Users/max/koskadeux-mcp/scripts/check_dispatch_liveness.py
```

Exit 0 means safe to restart. Exit 1 means not safe, and the JSON it prints names every blocking record with a reason.

If the check refuses, run the reaper once and check again:

```bash
python3 -c "import sys, json; sys.path.insert(0, '/Users/max/koskadeux-mcp'); import claude_code_client as c; print(json.dumps(c.reap_abandoned_tasks()['counts']))"
```

The reaper writes terminal state only for records it can prove are finished, and it distinguishes an observed successful result from an assumed failure. It never clears a record it cannot establish, so it is safe to run and safe to repeat. Do not clear records by hand, and do not assume a missing worker recovery path exists.

### Post-restart evidence

```bash
git -C /Users/max/koskadeux-mcp rev-parse HEAD
launchctl list | awk '$3 == "com.koskadeux.mcp" {print $1}'
ps -p <PID> -o lstart=
curl -sS http://127.0.0.1:8765/health
```

Record the SHA before kickstart and the PID/start time after kickstart. Do not read `/var/tmp/koskadeux/deployed_sha` as proof.

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | A dispatch is refused that previously passed. | Enforcement is on and the kernel returned `violated` or `not_evaluable` where legacy allowed; a newly required request fact such as `target_gate` may be absent. | Search `/tmp/koskadeux_mcp.log` for `COUNCIL_GATE_KERNEL_ENFORCEMENT_REFUSED_LEGACY_ALLOW`; inspect its predicate and kernel status, then compare the request shape. | G-01 | CONFIRMED |
| F-02 | The Council gate refuses everything after a configuration change. | `COUNCIL_GATE_POLICY_KERNEL_ENFORCEMENT` contains a value other than exact `off` or `on`; the reader raises and the gate fails closed. | Read only the exact `.env` assignment and inspect the refusal for `policy_kernel_enforcement_setting_invalid` and `must be exactly 'off' or 'on'`. | G-02 | CONFIRMED |
| F-03 | Preflight returns `status=indeterminate`. | Inventory completeness, HTTP/database access, timezone-aware clock, payload shape, or a sentinel lease could not be established. | Read the returned `reason`, `entities_examined`, and `gate_records_examined`; do not infer readiness from partial rows. | G-03 | CONFIRMED |
| F-04 | A dispatch remains `running` or has no terminal state after handler restart. | The restart killed its worker thread before `.done` and terminal metadata were written; recovery is unavailable. | Find the task's `.meta.json`, confirm the matching `.done` is absent, correlate its dispatch time with the handler restart, and inspect the target branch for any completed output. | G-04 | CONFIRMED |
| F-05 | `/var/tmp/koskadeux/deployed_sha` disagrees with observed handler behavior or the checkout. | The marker is stale because manual kickstart does not update it. | Ignore the marker; compare handler process start time with the checkout SHA recorded at that time or reconstruct from the checkout reflog. | G-05 | CONFIRMED |
| F-06 | The refusal marker count drops or restarts from one. | `count_since_process_start` is process-lifetime state and the handler restarted. | Compare the log timestamp with the current handler process start time. | G-06 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Policy Kernel Decision
  root_cause: The authoritative kernel refused a legacy allow because a predicate was violated or required facts were not evaluable.
  repair_entry_point: Refused request payload plus `COUNCIL_GATE_KERNEL_ENFORCEMENT_REFUSED_LEGACY_ALLOW` warning.
  change_pattern: Supply the missing explicit request fact when that matches the caller contract; for immediate broad restoration use E-04 rollback, and for an authorized bounded emergency use E-05 break_glass.
  rollback_procedure: Remove only an incorrect caller-side payload change; do not make `not_evaluable` allow.
  integrity_check: Repeat the exact request shape and confirm the intended kernel decision; if rolled back, confirm the exact original legacy outcome.
- id: G-02
  symptom_ref: F-02
  component_ref: Enforcement Switch
  root_cause: The switch value is invalid, so the gate fails closed instead of selecting a decision path.
  repair_entry_point: "`/Users/max/koskadeux-mcp/.env`."
  change_pattern: After satisfying E-01, set the value to exact `off` for rollback or exact `on` for continued enforcement, then kickstart once.
  rollback_procedure: Restore `/Users/max/koskadeux-mcp/.env.s1364.bak` and kickstart only after E-01 passes.
  integrity_check: Confirm the exact assignment, new handler PID/start time, checkout SHA at restart, health response, and absence of configuration-invalid refusals.
- id: G-03
  symptom_ref: F-03
  component_ref: Readiness Preflight
  root_cause: The preflight cannot prove a complete and evaluable scan.
  repair_entry_point: "`council_gate_policy_kernel_preflight` result `reason`."
  change_pattern: Repair the named clock, inventory-completeness, HTTP, database, or sentinel-record problem and rerun the full scan.
  rollback_procedure: Leave enforcement off while the result is indeterminate; no configuration change is required.
  integrity_check: Require an explicit `status=ready`; remember that ready covers only the known sentinel-lease divergence.
- id: G-04
  symptom_ref: F-04
  component_ref: Dispatch Task Store
  root_cause: Handler restart killed the worker before it wrote `.done` or a terminal task state.
  repair_entry_point: "`/var/tmp/koskadeux/cc_tasks/<task_id>.meta.json` and the target repository branch."
  change_pattern: Preserve the orphaned task evidence, verify whether any commit or output landed, then create a replacement dispatch only when duplicate work is excluded.
  rollback_procedure: There is no worker recovery. Supersede the terminal-less task record; do not fabricate a completion marker.
  integrity_check: Confirm exactly one replacement result or existing landed artifact is accepted and tied to the reviewed commit.
- id: G-05
  symptom_ref: F-05
  component_ref: Handler LaunchAgent
  root_cause: Manual kickstart changed the running process without updating `deployed_sha`.
  repair_entry_point: Handler process start time plus `/Users/max/koskadeux-mcp` checkout history.
  change_pattern: Reconstruct or record the SHA present at process start and use that pair as deployment evidence.
  rollback_procedure: Discard any deployment conclusion based only on `deployed_sha`; do not rewrite the marker to manufacture history.
  integrity_check: The process start time and checkout-at-that-time identify one SHA; health and behavior are consistent with it.
- id: G-06
  symptom_ref: F-06
  component_ref: Refusal Alert
  root_cause: The refusal counter resets when the handler process restarts.
  repair_entry_point: "`/tmp/koskadeux_mcp.log` and handler process start time."
  change_pattern: Segment alert counts by handler lifetime and retain timestamps with each observation.
  rollback_procedure: Do not rewrite or aggregate the in-process counter as if it were durable state.
  integrity_check: Every reported count is associated with one process start time.
```

## §H. Evolve

### §H.1 Invariants

- Only exact `off` and `on` switch values are valid; invalid configuration fails closed.
- When enforcement is on, `not_evaluable` never allows.
- The kernel is authoritative while the legacy adapter continues parity recording.
- `break_glass` remains the first short-circuit in `CouncilComplianceGate.check`.
- A handler restart is forbidden while any task metadata lacks its matching `.done`.
- Deployment proof binds handler start time to checkout state and never relies on `deployed_sha`.

### §H.2 BREAKING predicates

- Allowing a kernel `not_evaluable` status is BREAKING.
- Moving the `break_glass` check behind any enforcement point is BREAKING.
- Accepting switch values beyond exact `off` and `on`, or making invalid values fall open, is BREAKING.
- Restarting the handler without protecting in-flight dispatches is BREAKING.
- Changing the enforcement decision from kernel-authoritative back to a mixed or implicit path is BREAKING.

### §H.3 REVIEW predicates

- Changing the committed switch default is REVIEW.
- Expanding preflight beyond the known sentinel-lease divergence is REVIEW.
- Changing the Policy Kernel fact envelope or a predicate's status mapping is REVIEW.
- Changing the refusal marker fields, level, or process-counter semantics is REVIEW.
- Adding durable dispatch recovery across handler restart is REVIEW.

### §H.4 SAFE predicates

- Clarifying incident commands is SAFE when switch, decision, alert, and restart semantics do not change.
- Adding a verified example of a refused incomplete request is SAFE.
- Correcting dates, paths, or source references is SAFE when grounded in current code and deployment evidence.

### §H.5 Boundary definitions

#### module

The module boundary is the Council compliance gate switch reader, kernel decision selection, legacy parity recording, readiness preflight, refusal warning, break-glass short-circuit, and handler restart interaction.

#### public contract

The public contract is exact `off`/`on` configuration, kernel-authoritative decisions when on, fail-closed `not_evaluable`, continued parity telemetry, warning fields, and exact rollback to the legacy outcome.

#### runtime dependency

A runtime dependency is `/Users/max/koskadeux-mcp/.env`, the `com.koskadeux.mcp` process, the checkout loaded at its start, Living State inventory for preflight, `/tmp/koskadeux_mcp.log`, or `/var/tmp/koskadeux/cc_tasks`.

#### config default

The config default is the literal string `off` in `COUNCIL_GATE_POLICY_KERNEL_ENFORCEMENT_DEFAULT`.

### §H.6 Adjudication

Use the more restrictive class when classifications differ. Max adjudicates changes to fail-closed behavior, break-glass ordering, live enablement, or restart safety.

## §I. Scenario Set

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01, §C]
    scenario: |
      An operator is preparing a handler restart. The task directory contains one `abc.meta.json` with no `abc.done`. The first action must protect the dispatch rather than reload the switch. Use E-01 and the restart stop condition.
    expected_answers:
      - kind: human_action
        verb: stop
        object: handler restart
        target: unmatched dispatch metadata must reach a terminal `.done` state
    weight: 0.08333333333333333
  - id: I-02
    type: operate
    refs: [E-02, E-03]
    scenario: |
      An authorized operator has a complete inventory and preflight returns `status=ready`. The task scan is empty and the `.env` backup exists. Select the enablement action and immediate monitoring signal.
    expected_answers:
      - kind: human_action
        verb: enable
        object: "`COUNCIL_GATE_POLICY_KERNEL_ENFORCEMENT=on`"
        target: restart under E-01 then monitor the legacy-allow refusal marker
    weight: 0.08333333333333333
  - id: I-03
    type: operate
    refs: [E-05, §C]
    scenario: |
      Enforcement is on and an authorized bounded emergency requires bypassing the compliance gate. Choose the actual live lever before any kernel predicate executes.
    expected_answers:
      - kind: human_action
        verb: invoke
        object: existing `break_glass`
        target: first statement of `CouncilComplianceGate.check`
    weight: 0.08333333333333333
  - id: I-04
    type: isolate
    refs: [F-01, G-01]
    scenario: |
      A request that passed yesterday now returns `policy_kernel_not_evaluable`. The warning names `target_gate_valid`, kernel status `not_evaluable`, and legacy allowed. Classify the symptom before changing code.
    expected_answers:
      - kind: human_action
        verb: classify
        object: enforcement refused a legacy allow because `target_gate` was omitted
        target: F-01 then G-01
    weight: 0.08333333333333333
  - id: I-05
    type: isolate
    refs: [F-02, G-02]
    scenario: |
      Every Council-gate request refuses immediately after the switch was edited to `enabled`. Identify the configuration failure and the accepted value set.
    expected_answers:
      - kind: human_action
        verb: classify
        object: invalid enforcement switch causing fail-closed gate outage
        target: exact `off` or `on` only, then G-02
    weight: 0.08333333333333333
  - id: I-06
    type: isolate
    refs: [F-04, G-04]
    scenario: |
      A build remains running with no terminal state after a 10:02 handler kickstart. Its metadata predates the restart and no matching `.done` exists. Identify what happened and whether worker recovery is available.
    expected_answers:
      - kind: human_action
        verb: classify
        object: dispatch destroyed by handler restart
        target: no worker recovery; preserve evidence and use G-04
    weight: 0.08333333333333333
  - id: I-07
    type: repair
    refs: [G-02, E-04]
    scenario: |
      A typo in the enforcement variable is causing a full gate outage. No dispatch is in flight. Choose the immediate restoration sequence without pushing code.
    expected_answers:
      - kind: human_action
        verb: restore
        object: exact `off` or `/Users/max/koskadeux-mcp/.env.s1364.bak`
        target: kickstart `com.koskadeux.mcp` once and verify process/SHA evidence
    weight: 0.08333333333333333
  - id: I-08
    type: repair
    refs: [G-03, E-02]
    scenario: |
      Preflight returns `indeterminate` because inventory completeness cannot be established. Choose the safe repair posture and the evidence required before enablement.
    expected_answers:
      - kind: human_action
        verb: hold
        object: enforcement enablement
        target: repair the named scan failure and require explicit `status=ready`
    weight: 0.08333333333333333
  - id: I-09
    type: evolve
    refs: [§H, F-01]
    scenario: |
      A proposal would let `not_evaluable` requests proceed to reduce incident refusals. Classify the change against the live enforcement invariants.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-10
    type: evolve
    refs: [§H, E-02]
    scenario: |
      A proposal expands preflight from the known sentinel-lease divergence to additional request-shape divergences without changing the live decision path. Classify the change.
    expected_answers:
      - kind: classification
        label: REVIEW
    weight: 0.08333333333333333
  - id: I-11
    type: ambiguous
    refs: [F-01, F-02, F-03]
    scenario: |
      Requests refuse after enablement, but the incident report does not include the marker, exact `.env` line, or preflight result. Triage without assuming whether this is an intended tightening, invalid config, or incomplete readiness scan.
    expected_answers:
      - kind: human_action
        verb: triage
        object: refusal marker, exact switch value, and preflight evidence
        target: distinguish F-01 from F-02 and F-03 before repair
    weight: 0.08333333333333333
  - id: I-12
    type: ambiguous
    refs: [F-05, G-05]
    scenario: |
      `deployed_sha` names an older commit, current checkout names a newer commit, and the handler started between them. Determine deployed code without treating either current file as automatic proof.
    expected_answers:
      - kind: human_action
        verb: reconstruct
        object: checkout SHA at handler process start time
        target: process start plus checkout history; ignore stale `deployed_sha`
    weight: 0.08333333333333333
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1364
last_refresh_commit: 6b03e99e
last_refresh_date: 2026-07-27T09:56:32+02:00
owner_agent: vulcan
refresh_triggers:
  - enforcement switch parsing or default changes
  - Policy Kernel Council predicate or fact-envelope changes
  - preflight coverage or result-shape changes
  - refusal marker payload or counter changes
  - break-glass ordering changes
  - handler restart or dispatch persistence changes
scheduled_cadence: 30d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-07-27T09:56:32+02:00
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1364 / 2026-07-27T08:30:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
