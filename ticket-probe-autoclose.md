---
system_name: ticket-probe-autoclose
purpose_sentence: "Support tickets auto-close on the production symptom, not the delivery path: each ticket carries a machine still-broken probe, and a reconciler auto-resolves it (with evidence) once the probe reports not-broken twice, while an unreachable probe alarms and never closes."
owner_agent: vulcan
escalation_contact: max@ai.market
lifecycle_ref: §J
authoritative_scope: "The ticket-probe feature (BQ-TWO-TRACK-TICKET-PROBE-AUTOCLOSE-S1126, slice 1) — the probe schema/validation and probe-state columns on support_ticket, the probe runner, the ticket-probe reconciler with its deploy + heartbeat triggers, daily probe-rot canary, and unreachable alarms, plus the steady-state enablement (feature flag, launcher, launchd plist). Explicitly OUT of scope: the creation-time classification gate, the classification sweep, and the session-close intersection guard (later slices), and the separate git-branch BQ reconciler (tools/lifecycle/handler.py + eligibility.py), which this feature must never reuse or alter."
linter_version: 1.0.0
---

# Ticket-Probe Auto-Close (Two-Track Enforcement, Slice 1)

## §A. Header

YAML frontmatter above is authoritative for the §A header fields. This feature decouples ticket closure from the delivery mechanism (git branches / build gates) and couples it to the production symptom. A ticket carries a `probe` describing the condition that means STILL BROKEN; when production says the problem is gone (probe returns not_broken twice in a row), the ticket auto-resolves with the probe output as evidence — however the fix shipped. "Probe cannot reach its surface" (unreachable, including timeout and probe-rot) ALARMS and never closes. Backend surfaces live in `ai-market-backend`; runner + reconciler + scheduling live in `koskadeux-mcp`. The whole feature is gated by `TICKET_PROBE_RECONCILER_ENABLED` and does nothing when off. It is a no-op until a ticket is given a probe: reconcile only ever touches open tickets whose `probe IS NOT NULL`.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Probe schema + additive probe-state columns on support_ticket | SHIPPED | `alembic/versions/20260705_001_bq_ttpa_s1126_c1_probe_columns.py` | `tests/test_bq_ttpa_s1126_c1.py` | 2026-07-05 |
| Probe canary/rot columns + internal patch-field contract | SHIPPED | `alembic/versions/20260705_002_bq_ttpa_s1126_c1b_probe_canary_rot.py` | `tests/test_bq_ttpa_s1126_c1.py` | 2026-07-05 |
| Probe validation, all 5 kinds aligned to runner | SHIPPED | `app/schemas/support_ticket.py` | `tests/test_bq_ttpa_s1126_c1.py` | 2026-07-05 |
| P0/P1(critical/high)-requires-probe guard + counter-reset-on-reopen | SHIPPED | `app/api/v1/endpoints/support.py` | `tests/test_bq_ttpa_s1126_c1.py` | 2026-07-05 |
| Probe runner: per-kind classification + 30s timeout + read-only + allowlist-at-exec | SHIPPED | `tools/ticket_probe_runner.py` | `tests/unit/test_ticket_probe_runner.py` | 2026-07-05 |
| Reconciler auto-close: 2x not_broken -> resolved + evidence; unreachable never closes | SHIPPED | `tools/lifecycle/ticket_probe_reconciler.py` | `tests/unit/test_ticket_probe_reconciler.py` | 2026-07-05 |
| Concurrency: global pg advisory lock (skip-if-running) + 5-min per-ticket cooldown | SHIPPED | `tools/lifecycle/ticket_probe_reconciler.py` | `tests/unit/test_ticket_probe_reconciler.py` | 2026-07-05 |
| Daily canary probe-rot -> unreachable + alarm, blocks auto-close | SHIPPED | `tools/lifecycle/ticket_probe_reconciler.py` | `tests/unit/test_ticket_probe_reconciler.py` | 2026-07-05 |
| Unreachable alarm (peer bus + Event Ledger) with per-ticket 1h dedup | SHIPPED | `tools/lifecycle/ticket_probe_reconciler.py` | `tests/unit/test_ticket_probe_reconciler.py` | 2026-07-05 |
| Triggers: post-deploy hook + hourly launchd heartbeat, behind flag | SHIPPED | `kd_scheduler.py` | `tests/unit/test_ticket_probe_reconciler.py` | 2026-07-05 |
| Steady-state enabled on Titan-1 (flag in .env; launchd loaded; lock DSN via Infisical launcher) | SHIPPED | `scripts/launch_ticket_probe_reconciler.sh` | — | 2026-07-05 |
| http probes require backend TICKET_PROBE_HTTP_ALLOWLIST (Railway env) or create 422s | PARTIAL | `app/schemas/support_ticket.py` | `tests/test_bq_ttpa_s1126_c1.py` | 2026-07-05 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Backend probe schema + guards | ai-market-backend app/api/v1/endpoints/support.py (create/patch) | Railway Postgres support_ticket | probe runner (reads probe), reconciler (patches probe-state) | patch_ticket is internal-only (403 unless principal.is_internal); model_dump(exclude_none=True) -> only declared fields persist, so probe-state fields must be declared on TicketPatchRequest |
| Probe runner | koskadeux-mcp tools/ticket_probe_runner.py run_ticket_probe(probe) | none (pure function) | reconciler | Returns broken/not_broken/unreachable; per-probe 30s hard timeout -> unreachable+probe_timeout; read-only (SELECT-only via mcp_sql_validator); http allowlist re-checked at execution |
| Ticket-probe reconciler | koskadeux-mcp tools/lifecycle/ticket_probe_reconciler.py reconcile_ticket_probes() | Railway Postgres (via backend PATCH); pg advisory lock DB | runner, backend API, peer bus, Event Ledger | Sits ALONGSIDE the git-branch BQ reconciler and must not reuse/alter it. Full no-op when flag off |
| Scheduler CLI | koskadeux-mcp kd_scheduler.py --ticket-probe-reconcile | none | reconciler | One-shot heartbeat run; loads .env (override=False) |
| Deploy hook | koskadeux-mcp kd_deploy.py run_ticket_probe_reconciler_after_deploy() | none | reconciler | Fires after a successful prod deploy+restart; try/except, flag-gated |
| launchd heartbeat | launch_agents/com.koskadeux.ticket-probe-reconciler.plist -> scripts/launch_ticket_probe_reconciler.sh | Infisical (AUTHOR_DISPATCH_DATABASE_URL for lock) | scheduler CLI | Hourly (StartInterval 3600) + RunAtLoad; launcher Infisical-fetches the lock DSN (launchd has no shell env) |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| vulcan | Author/attach a probe to a ticket | backend PATCH /api/v1/support/tickets/{ref} (internal) | internal (INTERNAL_API_KEY) | COMPLETE |
| vulcan | Run a manual reconcile pass | koskadeux-mcp kd_scheduler.py --ticket-probe-reconcile | internal + lock DSN | COMPLETE |
| vulcan | Enable/disable steady-state | .env TICKET_PROBE_RECONCILER_ENABLED + launchctl bootout/bootstrap | Titan-1 shell | COMPLETE |
| mars | Same operations (equal authority) | as above | as above | COMPLETE |
| sysadmin | Respond to an unreachable/probe-rot alarm | peer bus alert -> this runbook §F/§G | operational | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: A P0/P1 (critical/high) ticket is created or an existing ticket should auto-close on a production symptom
  pre_conditions:
    - ticket exists and is open (status not in resolved/closed)
    - a machine-checkable "still broken" condition exists for the ticket
  tool_or_endpoint: 'PATCH /api/v1/support/tickets/{public_ref} (internal) with body containing the probe object'
  argument_sourcing:
    probe: 'kind in {http,db_query,log_grep,flag_state,config_key}; target; assert_broken (http {status:int, body_match?:str}; db_query {rows_gt:int|rows_eq:int} SELECT-only; log_grep {match:str}; flag_state/config_key {equals|value})'
  idempotency: IDEMPOTENT
  expected_success:
    shape: 200 with the ticket JSON including the stored probe
    verification: GET the ticket and confirm probe is present and probe_last_state is null until first reconcile
  expected_failures:
    - signature: 422 http probe target host is not in TICKET_PROBE_HTTP_ALLOWLIST
      cause: backend Railway env TICKET_PROBE_HTTP_ALLOWLIST does not include the target host (see §G-01)
    - signature: 422 P0/P1 support tickets require a valid machine probe
      cause: creating/patching a critical/high ticket without a valid probe
  next_step_success: Reconciler will pick up the ticket on the next deploy or hourly heartbeat
  next_step_failure: Fix the probe shape or the backend allowlist, then re-PATCH
- id: E-02
  trigger: Operator wants an immediate reconcile pass (verification or expedite)
  pre_conditions:
    - TICKET_PROBE_RECONCILER_ENABLED=true in the run environment
    - advisory-lock DSN available (AUTHOR_DISPATCH_DATABASE_URL or DATABASE_URL)
  tool_or_endpoint: koskadeux-mcp/venv/bin/python kd_scheduler.py --ticket-probe-reconcile (or launchctl kickstart -k gui/$(id -u)/com.koskadeux.ticket-probe-reconciler)
  argument_sourcing:
    env: 'flag + TICKET_PROBE_DATABASE_URL from .env; lock DSN from Infisical via scripts/launch_ticket_probe_reconciler.sh'
  idempotency: IDEMPOTENT
  expected_success:
    shape: 'JSON stats {enabled:true, lock_acquired:true, tickets_seen, resolved, alarms, errors:[]}'
    verification: exit 0; stats printed; /var/tmp/koskadeux/ticket_probe_reconciler.log updated
  expected_failures:
    - signature: '{enabled:false}'
      cause: flag not set in the run environment (see §F F1)
    - signature: '{lock_acquired:false}'
      cause: another run holds the lock, OR the lock DSN is missing/unreachable (see §F F2)
  next_step_success: not_broken x2 auto-resolves the ticket; unreachable alarms
  next_step_failure: See §F to isolate, §G to repair
- id: E-03
  trigger: Turn the feature on or off for steady state
  pre_conditions:
    - on Titan-1 with launchctl access
  tool_or_endpoint: 'edit .env TICKET_PROBE_RECONCILER_ENABLED (true|false); launchctl bootstrap|bootout gui/$(id -u) ~/Library/LaunchAgents/com.koskadeux.ticket-probe-reconciler.plist'
  argument_sourcing:
    flag: .env TICKET_PROBE_RECONCILER_ENABLED
  idempotency: IDEMPOTENT
  expected_success:
    shape: launchctl list shows com.koskadeux.ticket-probe-reconciler with exit 0 (enabled) / absent (disabled)
    verification: kickstart a run and confirm stats.enabled matches intent
  expected_failures:
    - signature: job runs but stats.enabled=false
      cause: flag still false in .env or a stale process env
  next_step_success: Steady state matches intent
  next_step_failure: Recheck .env and reload the job
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Reconcile stats show enabled:false (does nothing) | flag not set in the run env (launchd has no shell env; launcher not used) | Run the launcher directly; check stats.enabled | G-01 | CONFIRMED |
| F-02 | Reconcile stats show lock_acquired:false every run | advisory-lock DSN missing/unreachable, or a stuck concurrent run | Confirm launcher Infisical fetch (stderr present:yes); check for another instance | G-02 | CONFIRMED |
| F-03 | Ticket create/patch 422 on an http probe | backend Railway TICKET_PROBE_HTTP_ALLOWLIST missing the target host | Reproduce the PATCH; read the 422 detail | G-03 | CONFIRMED |
| F-04 | db_query probe always classifies unreachable | TICKET_PROBE_DATABASE_URL/DATABASE_URL not set for the runner, or the SELECT errors | Run the probe SQL against the readonly DSN; check runner env | G-04 | HYPOTHESIZED |
| F-05 | Auto-close never fires despite not_broken | probe-state fields not persisting, <2 consecutive not_broken, or cooldown collapsing runs | GET the ticket; confirm probe_consecutive_not_broken increments across runs | G-05 | HYPOTHESIZED |
| F-06 | Alarm storm for one ticket | dedup window not applied, or many genuinely-unreachable tickets | Inspect Event Ledger support_ticket_probe_unreachable per ticket per hour | G-06 | HYPOTHESIZED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-03
  component_ref: Backend probe schema + guards
  root_cause: http probe host not on the backend allowlist
  repair_entry_point: ai-market-backend Railway env TICKET_PROBE_HTTP_ALLOWLIST
  change_pattern: Add the target host (comma-separated) to TICKET_PROBE_HTTP_ALLOWLIST on the ai-market-backend Railway service, redeploy, then re-verify the PATCH. db_query probes need no allowlist.
  rollback_procedure: Remove the host from the env and redeploy
  integrity_check: PATCH the probe again and confirm 200; the runner re-checks the allowlist at execution too
- id: G-02
  symptom_ref: F-01
  component_ref: Scheduler CLI
  root_cause: flag not present in the run environment
  repair_entry_point: koskadeux-mcp .env and scripts/launch_ticket_probe_reconciler.sh
  change_pattern: Ensure TICKET_PROBE_RECONCILER_ENABLED=true in .env; ensure the plist runs the launcher. Reload the job (bootout then bootstrap).
  rollback_procedure: Set TICKET_PROBE_RECONCILER_ENABLED=false (feature becomes a full no-op)
  integrity_check: launchctl kickstart -k and confirm stats.enabled=true
- id: G-03
  symptom_ref: F-02
  component_ref: Ticket-probe reconciler
  root_cause: lock DSN missing/unreachable or a stuck concurrent holder
  repair_entry_point: scripts/launch_ticket_probe_reconciler.sh Infisical fetch of AUTHOR_DISPATCH_DATABASE_URL
  change_pattern: Confirm the sysadmin JWT is fresh (infisical_auth_refresh.sh) and the secret fetch returns non-empty. The lock is pg_try_advisory_lock (session-scoped) and releases on process exit; kill a stuck run if needed.
  rollback_procedure: none needed; lock auto-releases on process exit
  integrity_check: Re-run; stats.lock_acquired=true
- id: G-04
  symptom_ref: F-04
  component_ref: Probe runner
  root_cause: probe-execution DB URL missing or the SELECT errors
  repair_entry_point: koskadeux-mcp .env TICKET_PROBE_DATABASE_URL and the probe target SQL
  change_pattern: Ensure TICKET_PROBE_DATABASE_URL resolves to a reachable readonly prod DSN; validate the probe SQL is SELECT-only and returns the expected rows.
  rollback_procedure: Revert the probe target; unreachable never auto-closes so no data harm
  integrity_check: Manual reconcile; ticket probe_last_state becomes broken/not_broken (not unreachable)
- id: G-05
  symptom_ref: F-05
  component_ref: Ticket-probe reconciler
  root_cause: probe-state fields not persisting, or anti-flap/cooldown collapsing runs
  repair_entry_point: ai-market-backend app/schemas/support_ticket.py TicketPatchRequest; reconciler counter logic
  change_pattern: Confirm the probe-state fields are declared on TicketPatchRequest (added S1128 C1b). Confirm two runs at least 5 min apart (cooldown).
  rollback_procedure: none (read/verify path)
  integrity_check: probe_consecutive_not_broken reaches 2 -> status=resolved + resolution_source=probe + evidence message
- id: G-06
  symptom_ref: F-06
  component_ref: Ticket-probe reconciler
  root_cause: dedup not applied, or many genuine unreachables
  repair_entry_point: koskadeux-mcp tools/lifecycle/ticket_probe_reconciler.py alarm dedup
  change_pattern: Confirm the per-ticket 1h dedup key logic; if many tickets are genuinely unreachable, treat as a real incident (surface/probe outage), not a bug.
  rollback_procedure: Disable the feature (flag false) to silence while investigating
  integrity_check: At most one alarm per ticket per 1h window in the Event Ledger
```

## §H. Evolve

### §H.1 Invariants

- Flag off (`TICKET_PROBE_RECONCILER_ENABLED` unset/false) is a FULL no-op: no fetch, no probe, no PATCH, no alarm, no lock.
- `resolved` is terminal for auto-close: the reconciler never advances a ticket to `closed`; an operator owns resolved->closed.
- `unreachable` (including probe_timeout and probe_rot) NEVER closes a ticket and NEVER resets the not-broken counter; it alarms.
- Probes are read-only: db_query is SELECT-only (mcp_sql_validator); no probe kind performs a write.
- Only open tickets with `probe IS NOT NULL` are ever evaluated; the git-branch BQ reconciler is never reused or altered.
- Backend probe validation MUST match the runner's assert_broken contract for every kind (drift here silently breaks a probe kind end-to-end).
- The support-ticket PATCH path stays internal-only (403 for non-internal principals).

### §H.2 BREAKING predicates

- Removing or renaming any probe-state column (probe, probe_last_state, probe_last_checked_at, probe_consecutive_not_broken, resolution_source, probe_last_canary_at, probe_rot).
- Changing the runner's return values (broken/not_broken/unreachable) or the assert_broken shape for any kind without matching the backend validator.
- Making the patch path externally reachable, or letting external callers set resolved_at/resolution_source/status.

### §H.3 REVIEW predicates

- Changing the auto-close threshold (2x not_broken), the 5-min cooldown, the 30s probe timeout, the daily canary cadence, or the 1h alarm dedup window.
- Adding a new probe kind (must be added to BOTH backend validation and the runner in the same change).
- Changing the advisory-lock key or DSN source.

### §H.4 SAFE predicates

- Adding a host to TICKET_PROBE_HTTP_ALLOWLIST.
- Attaching/removing a probe on an individual ticket.
- Editing log/observability strings that carry no secret.

### §H.5 Boundary definitions

#### module

koskadeux-mcp tools/lifecycle/ticket_probe_reconciler.py (reconciler), tools/ticket_probe_runner.py (runner); ai-market-backend app/schemas/support_ticket.py + app/api/v1/endpoints/support.py (probe contract).

#### public contract

Backend: TicketProbe (kind/target/assert_broken) validation; TicketPatchRequest probe-state fields; internal-only patch. Runner: run_ticket_probe(probe) -> broken|not_broken|unreachable. Reconciler: reconcile_ticket_probes() stats.

#### runtime dependency

Railway Postgres (support_ticket via backend), the advisory-lock DB (AUTHOR_DISPATCH_DATABASE_URL via Infisical), a readonly probe DB (TICKET_PROBE_DATABASE_URL), peer bus + Event Ledger, launchd on Titan-1.

#### config default

TICKET_PROBE_RECONCILER_ENABLED default false. On Titan-1 it is set true in koskadeux-mcp .env (S1128). TICKET_PROBE_HTTP_ALLOWLIST is unset by default (http probes require it on the backend).

### §H.6 Adjudication

Owner agent vulcan adjudicates evolution. BREAKING changes require a spec + Council Gate-3 (reviewer!=builder) before merge and a Gate-4 controlled enable. REVIEW changes require a single-reviewer pass. SAFE changes may proceed directly and be noted here in the same session.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs:
      - E-01
    scenario: Attach a valid db_query probe to an open ticket.
    expected_answers:
      - kind: tool_call
        tool: patch_ticket
        argument_keys:
          - public_ref
          - probe
    weight: 0.1
  - id: I-02
    type: operate
    refs:
      - E-02
    scenario: Run a manual reconcile pass with the flag on.
    expected_answers:
      - kind: tool_call
        tool: reconcile_ticket_probes
        argument_keys:
          - reason
    weight: 0.1
  - id: I-03
    type: operate
    refs:
      - E-03
    scenario: Enable steady-state on Titan-1 via the flag and launchd job.
    expected_answers:
      - kind: human_action
        tool: launchctl
        argument_keys:
          - bootstrap
    weight: 0.1
  - id: I-04
    type: isolate
    refs:
      - F-01
    scenario: Reconcile reports enabled false and does nothing.
    expected_answers:
      - kind: tool_call
        tool: reconcile_ticket_probes
        argument_keys:
          - enabled
    weight: 0.1
  - id: I-05
    type: isolate
    refs:
      - F-02
    scenario: Reconcile reports lock_acquired false every run.
    expected_answers:
      - kind: tool_call
        tool: reconcile_ticket_probes
        argument_keys:
          - lock_acquired
    weight: 0.1
  - id: I-06
    type: isolate
    refs:
      - F-06
    scenario: A ticket whose probe is unreachable alarms without closing.
    expected_answers:
      - kind: tool_call
        tool: emit_unreachable_alarm
        argument_keys:
          - ticket_ref
          - probe_last_state
    weight: 0.1
  - id: I-07
    type: repair
    refs:
      - G-01
    scenario: An http probe 422s at create because the backend allowlist lacks the host.
    expected_answers:
      - kind: human_action
        tool: railway_env_set
        argument_keys:
          - TICKET_PROBE_HTTP_ALLOWLIST
    weight: 0.1
  - id: I-08
    type: repair
    refs:
      - G-05
    scenario: Auto-close is not firing; verify probe-state persistence and cooldown.
    expected_answers:
      - kind: tool_call
        tool: patch_ticket
        argument_keys:
          - probe_consecutive_not_broken
    weight: 0.1
  - id: I-09
    type: evolve
    refs:
      - E-01
    scenario: A probe of each of the five kinds passes create-validation shaped as the runner consumes it.
    expected_answers:
      - kind: classification
        tool: TicketProbe.validate_probe
        argument_keys:
          - kind
          - assert_broken
    weight: 0.1
  - id: I-10
    type: evolve
    refs:
      - F-05
    scenario: Adding a new probe kind requires matching backend validation and the runner in one change.
    expected_answers:
      - kind: classification
        tool: TicketProbe.validate_probe
        argument_keys:
          - kind
    weight: 0.05
  - id: I-11
    type: ambiguous
    refs:
      - F-05
    scenario: Ticket sits open with a probe but no state change; unclear if not-broken-once, cooldown, or unreachable.
    expected_answers:
      - kind: tool_call
        tool: reconcile_ticket_probes
        argument_keys:
          - tickets_evaluated
    weight: 0.05
```

### §I.1 Weight Justification

Core paths carry 0.1; two secondary guards carry 0.05. Per-scenario:

- I-01 (0.1): attach a probe — entry point for the whole feature.
- I-02 (0.1): manual reconcile — the core operate loop.
- I-03 (0.1): enable steady-state — the production on-switch.
- I-04 (0.1): flag-off no-op — the primary safety invariant.
- I-05 (0.1): lock-acquire failure — the main degraded mode.
- I-06 (0.1): unreachable alarms without closing — the core safety behavior.
- I-07 (0.1): http-allowlist 422 repair — the most common operator fix.
- I-08 (0.1): auto-close not firing — the core persistence path.
- I-09 (0.1): five-kind contract — the cross-chunk correctness guard.
- I-10 (0.05): new-kind discipline — important but secondary to the core paths.
- I-11 (0.05): ambiguous no-movement — a triage aid, secondary to deterministic paths.

Weights sum to 1.0.

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1128
last_refresh_commit: 57e18568
last_refresh_date: "2026-07-05"
owner_agent: vulcan
refresh_triggers:
  - change to the probe schema, probe-state columns, or the assert_broken contract for any kind
  - change to the reconciler close rule, cooldown, timeout, canary cadence, or alarm dedup
  - change to the enablement mechanism (flag, launcher, plist) or the advisory-lock DSN source
  - adding a new probe kind
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: "2026-07-05T00:00:00Z"
first_staleness_detected_at: null
```

## §K. Conformance

Slice 1 scope only. Later slices (creation-time classification gate, classification sweep, session-close intersection guard) are explicitly out of scope and will extend this runbook when built. Two carried non-blocking notes: the SELECT-only validator is deliberately conservative (may reject exotic-but-legitimate SQL), and the runner's http client timeout is fixed at 30s independent of a configurable per-probe timeout (inert at the default).

```yaml conformance
linter_version: 1.0.0
last_lint_run: "S1128 / 2026-07-05T21:40:00Z"
last_lint_result: PASS
trace_matrix_path: specs/BQ-TWO-TRACK-TICKET-PROBE-AUTOCLOSE-S1126-GATE2.md
word_count_delta: null
```
