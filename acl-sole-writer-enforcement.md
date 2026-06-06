---
system_name: acl-sole-writer-enforcement
purpose_sentence: Per-field sole-writer access control for Living State writes — the WS9 reform subsystem that observes unauthorized writes in WARN mode and, once operator-flipped, rejects them with a 403 so only the canonical writer role may mutate each governed field.
owner_agent: vulcan
escalation_contact: Max
lifecycle_ref: §J
authoritative_scope: koskadeux-mcp tools/acl_enforce/ (identity, lookup, gate, audit, orchestrate), the field_acl table, and the acl_* event_ledger rows. Does NOT cover the state_request write-path hook (WS9 Chunk 6, not yet shipped) or the field_acl row seed migration (WS6, separate workstream).
linter_version: 1.0.0
---

# ACL Sole-Writer Enforcement (WS9)

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Writer-role identity resolution | SHIPPED | `tools/acl_enforce/identity.py:resolve_writer_role` | `tests/acl_enforce/test_identity.py` | 2026-06-06 |
| Key/path ACL lookup (specificity exact>prefix>glob>NULL) | SHIPPED | `tools/acl_enforce/lookup.py:FieldAclCache.lookup` | `tests/acl_enforce/test_lookup.py` | 2026-06-06 |
| Runtime gate (WARN log / ENFORCE 403) | SHIPPED | `tools/acl_enforce/gate.py:enforce_field_acl` | `tests/acl_enforce/test_gate.py` | 2026-06-06 |
| Phase A dry-run write inventory | SHIPPED | `tools/acl_enforce/audit.py:collect_phase_a_audit` | `tests/acl_enforce/test_audit.py` | 2026-06-06 |
| Phase C flip-readiness SLO | SHIPPED | `tools/acl_enforce/audit.py:evaluate_phase_c_slo` | `tests/acl_enforce/test_audit.py` | 2026-06-06 |
| Phase B WARN-start | SHIPPED | `tools/acl_enforce/orchestrate.py:start_phase_b_warn` | `tests/acl_enforce/test_orchestrate.py` | 2026-06-06 |
| Phase D enforce-flip (warn->enforce) | PARTIAL | `tools/acl_enforce/orchestrate.py:execute_phase_d_flip` | `tests/acl_enforce/test_orchestrate.py` | 2026-06-06 |
| Phase E single-row rollback (enforce->warn) | SHIPPED | `tools/acl_enforce/orchestrate.py:rollback_phase_e_row` | `tests/acl_enforce/test_orchestrate.py` | 2026-06-06 |
| Live write-path enforcement hook (state_request put/patch) | PLANNED | — | none | — |

**PARTIAL note (Phase D enforce-flip):** code-complete and unit-tested but never executed against production; gated on (a) explicit Max direction, (b) the live write-path hook landing (Chunk 6, see PLANNED row), and (c) resolution of the precedence defect in §F-05. Operative mode for the whole subsystem today is WARN-only, and no live interception exists until the Chunk 6 hook ships.

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Identity resolver | tools/acl_enforce/identity.py:resolve_writer_role | none (pure function) | gate, audit | Maps updated_by + session context to WriterIdentity(role, role_class, session match); 13 seed roles + 4 identity tokens. |
| ACL lookup cache | tools/acl_enforce/lookup.py:FieldAclCache.lookup | field_acl | gate, audit | Resolves (entity_kind, key, path) to a FieldAclRow with two-axis specificity ordering exact>prefix>glob>NULL. |
| Runtime gate | tools/acl_enforce/gate.py:enforce_field_acl | field_acl; event_ledger | (future) tools/state.py state_request | WARN: emit acl_warn_violation and allow. ENFORCE: emit acl_enforce_violation and raise 403 sole_writer_mismatch. |
| Audit / SLO | tools/acl_enforce/audit.py:collect_phase_a_audit / evaluate_phase_c_slo | event_ledger; field_acl | orchestrate | Phase A dry-run replay of past writes; Phase C reads concrete acl_warn_violation payload path via lookup._match_path (NOT a literal path_pattern). |
| Cutover orchestrator | tools/acl_enforce/orchestrate.py:start_phase_b_warn / execute_phase_d_flip / rollback_phase_e_row | field_acl; event_ledger | audit | Phase B/D/E. Phase D locks rows, rejects already-enforced, RE-VALIDATES the Phase C SLO inside the flip transaction, then updates enforce_mode in one atomic txn. |
| field_acl (state store) | — | Postgres (Living State DB; reach via DATABASE_PUBLIC_URL from Titan-1) | — | Columns include enforce_mode IN ('warn','enforce'), sole_writer_role, sole_writer_session_match, key_pattern/key_pattern_type, path_pattern/path_type. |
| event_ledger (state store) | — | Postgres event_ledger | — | Emits acl_warn_started, acl_audit_done, acl_flip_ready, acl_flip_blocked, acl_flip_done, acl_row_rollback, acl_warn_violation, acl_enforce_violation (all event_type <=32 chars). |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| vulcan / mars (orchestrating instance) | run WARN-start, readiness check, flip, rollback, audit | shell_request to Titan-1: direct invocation of tools/acl_enforce/orchestrate.py + audit.py functions with a live DB connection (no dedicated CLI/MCP wrapper yet) | Titan-1 shell + DATABASE_PUBLIC_URL | PARTIAL — first-class CLI/MCP tool wrapper is a tracked §H REVIEW item; operated today via direct library calls on Titan-1 |
| state_request (runtime path) | enforce on put/patch pre-persistence | gate.py:enforce_field_acl (future hook) | Living State write path | PLANNED |
| reconciliation_job / lifecycle / drain / claim handlers | governed writers subject to the gate | state_request | per field_acl sole_writer_role row | PLANNED |
| Max | direct the enforce-flip (Phase D) | operator instruction relayed to the orchestrating instance | final authority | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: Operator begins WARN observation on a clean field_acl (no enforce rows yet)
  pre_conditions:
    - field_acl contains zero rows with enforce_mode='enforce'
  tool_or_endpoint: tools/acl_enforce/orchestrate.py:start_phase_b_warn(conn)
  argument_sourcing:
    conn: open against the Living State DB via DATABASE_PUBLIC_URL (Infisical-sourced) from Titan-1
  idempotency: IDEMPOTENT
  expected_success:
    shape: returns None; one acl_warn_started event in event_ledger with enforce_rows=0
    verification: SELECT count(*) FROM event_ledger WHERE event_type='acl_warn_started' ORDER BY occurred_at DESC LIMIT 1
  expected_failures:
    - signature: ValueError "field_acl already contains enforce rows"
      cause: a prior flip already moved one or more rows to enforce; system is not in pure-WARN
  next_step_success: leave the gate in WARN and accumulate acl_warn_violation events over the observation window
  next_step_failure: see §F-04; roll back the erroneous enforce rows (§G-01) if the flip was unintended
- id: E-02
  trigger: Before any flip, confirm the candidate rows are flip-ready
  pre_conditions:
    - a candidate list of (entity_kind, path_pattern, path_type) rows exists in field_acl
    - a WARN observation window has accumulated events
  tool_or_endpoint: tools/acl_enforce/audit.py:evaluate_phase_c_slo(conn, eligible_rows)
  argument_sourcing:
    conn: Living State DB via DATABASE_PUBLIC_URL
    eligible_rows: SELECT (entity_kind, path_pattern, path_type) FROM field_acl WHERE enforce_mode='warn' for the candidate set
  idempotency: IDEMPOTENT
  expected_success:
    shape: "SloVerdict(ready: bool, blocked_reasons: list, global_violation_rate: float, per_row: dict)"
    verification: verdict.ready is True AND verdict.blocked_reasons is empty
  expected_failures:
    - signature: verdict.ready is False with non-empty blocked_reasons
      cause: warn_violation_count / unknown_writer_count / missing_session_match_count nonzero on a row, or global rate over threshold
  next_step_success: proceed to E-03 (flip) only with explicit Max direction
  next_step_failure: see §F-01; remediate offending writers then re-run (§G-02)
- id: E-03
  trigger: Max directs flipping a verified-ready row set from WARN to ENFORCE
  pre_conditions:
    - E-02 returned ready=True for exactly this row set
    - explicit Max direction recorded
    - the §F-05 precedence defect has been resolved (gate before broad enforce)
  tool_or_endpoint: tools/acl_enforce/orchestrate.py:execute_phase_d_flip(conn, eligible_rows, operator)
  argument_sourcing:
    conn: Living State DB via DATABASE_PUBLIC_URL
    eligible_rows: the verified-ready set from E-02
    operator: the human operator identity directing the flip
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: FlipResult(rows_flipped, flipped_at, flipped_by, event_id); one acl_flip_done event
    verification: SELECT enforce_mode FROM field_acl for each row returns 'enforce'
  expected_failures:
    - signature: StateRequestError 409 acl_phase_c_slo_not_ready
      cause: the in-transaction SLO re-validation failed between E-02 and the flip
    - signature: StateRequestError 409 field_acl_row_already_enforced
      cause: one or more target rows were already enforce
    - signature: StateRequestError 404 field_acl_row_not_found
      cause: a target (entity_kind, path_pattern, path_type) tuple does not exist in field_acl
  next_step_success: monitor acl_enforce_violation events; roll back any row that misbehaves via §G-01
  next_step_failure: see §F-01 / §F-02 / §F-03 by signature
- id: E-04
  trigger: Operator wants a dry-run inventory of recent writes vs current ACL rows (no mutation)
  pre_conditions:
    - event_ledger contains recent state-write events
  tool_or_endpoint: tools/acl_enforce/audit.py:collect_phase_a_audit(conn, window_days=14)
  argument_sourcing:
    conn: Living State DB via DATABASE_PUBLIC_URL
  idempotency: IDEMPOTENT
  expected_success:
    shape: AuditReport(covered_writer_match, covered_writer_mismatch, uncovered, total_writes, window_start, window_end)
    verification: acl_audit_done event present with matching total_writes
  expected_failures:
    - signature: empty report (total_writes=0)
      cause: no state-write events in window, or window too narrow
  next_step_success: use mismatch/uncovered counts to decide which rows are candidates for E-02
  next_step_failure: widen window_days and re-run
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Flip raises 409 acl_phase_c_slo_not_ready | WARN window not clean for the row set; SloVerdict.ready=False | Re-run evaluate_phase_c_slo(conn, rows) and read blocked_reasons + per_row counters | §G-02 | CONFIRMED |
| F-02 | Flip raises 409 field_acl_row_already_enforced | One or more target rows already at enforce_mode='enforce' | SELECT enforce_mode FROM field_acl WHERE (entity_kind,path_pattern,path_type) IN (...) | §G-01 | CONFIRMED |
| F-03 | Flip or rollback raises 404 field_acl_row_not_found | Row key tuple mismatch, or row absent (seed not applied) | SELECT * FROM field_acl matching the tuple; compare against WS6 seed | §G-03 | CONFIRMED |
| F-04 | start_phase_b_warn raises ValueError "field_acl already contains enforce rows" | System is not in pure-WARN; a flip already happened | SELECT count(*) FROM field_acl WHERE enforce_mode='enforce' | §G-01 | CONFIRMED |
| F-05 | Phase A advisory and runtime gate disagree on which row applies | Phase A classifies on most-specific row (acl_rows[0]); gate.py defensive-ANDs across all matching specificity levels | Compare collect_phase_a_audit classification vs gate.py enforce_field_acl matching for the same (entity_kind,key,path) | | HYPOTHESIZED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-02
  component_ref: Cutover orchestrator
  root_cause: A row was flipped to enforce in error, or WARN observation must resume on an enforce row
  repair_entry_point: tools/acl_enforce/orchestrate.py:rollback_phase_e_row(conn, entity_kind, path_pattern, path_type, reason, operator)
  change_pattern: Call rollback with a non-empty reason and operator; it sets enforce_mode='warn' for exactly one row and emits acl_row_rollback with operator+reason audit
  rollback_procedure: This IS the rollback path; if the row is already warn it raises 404 (rows_updated != 1) — no further action
  integrity_check: SELECT enforce_mode FROM field_acl for the row returns 'warn'; acl_row_rollback event present with the operator and reason
- id: G-02
  symptom_ref: F-01
  component_ref: Audit / SLO
  root_cause: One or more eligible rows have nonzero warn_violation_count, unknown_writer_count, or missing_session_match_count, or the global violation rate exceeds threshold
  repair_entry_point: tools/acl_enforce/audit.py:evaluate_phase_c_slo(conn, eligible_rows)
  change_pattern: Read SloVerdict.per_row to find the offending rows; correct the misbehaving writer (fix updated_by/role mapping in identity.py seed, or fix the writer's session-match) so it stops emitting acl_warn_violation; let a fresh WARN window accumulate; re-evaluate
  rollback_procedure: none required (read-only diagnostic); do not flip until verdict.ready=True
  integrity_check: evaluate_phase_c_slo returns ready=True with empty blocked_reasons for the row set
- id: G-03
  symptom_ref: F-03
  component_ref: ACL lookup cache
  root_cause: Target (entity_kind, path_pattern, path_type) tuple is absent from field_acl, or the WS6 seed has not populated it
  repair_entry_point: tools/acl_enforce/lookup.py:FieldAclCache.lookup
  change_pattern: Reconcile the row against the WS6 field_acl seed; correct the tuple passed to the flip/rollback call to match an existing row; if the row should exist but does not, escalate to the WS6 seed owner
  rollback_procedure: none (no write attempted once the tuple is corrected)
  integrity_check: lookup returns a FieldAclRow for the (entity_kind, key, path); the subsequent flip/rollback no longer 404s
```

## §H. Evolve

### §H.1 Invariants

- enforce_mode is the closed set {'warn','enforce'} only; adding a third mode re-architects Phase D and the SLO contract.
- field_acl is the single authority for per-field write authorization in the single-source-of-truth reform.
- The enforce-flip (Phase D) is operator-directed by Max and never automatic; no module-level flip executes at import.
- execute_phase_d_flip re-validates the Phase C SLO INSIDE the flip transaction (TOCTOU safety) and locks target rows (FOR UPDATE on Postgres); this atomicity must not be removed.
- ai.market non-custodial invariant is unaffected: this governs internal Living State write authorization, never customer data.
- All DB access is via DATABASE_PUBLIC_URL with credentials from Infisical; no secrets committed.

### §H.2 BREAKING predicates

- Adds, removes, or renames a field_acl column in the published DDL contract.
- Changes the enforce_mode allowed value set.
- Changes the resolve_writer_role return contract (WriterIdentity shape) or the SloVerdict shape.
- Removes the in-transaction SLO re-validation or row locking in execute_phase_d_flip.

### §H.3 REVIEW predicates

- Adds a new sole_writer_role to the seed or a new identity token to resolve_writer_role.
- Changes the specificity ordering semantics (exact>prefix>glob>NULL) in lookup.
- Adds a new acl_* event_type (must stay within the 32-char event_type cap).
- Wires enforce_field_acl into a new call site, e.g. the state_request put/patch hook (WS9 Chunk 6 is itself a REVIEW-class change).
- Adds a first-class CLI/MCP tool wrapper for the cutover functions (closes the §D tool-gap).

### §H.4 SAFE predicates

- Adds a new §E operate scenario, §F symptom, or test without touching the gate/flip logic.
- Tightens a blocked_reason or audit message string.
- Adds a read-only diagnostic query over event_ledger or field_acl.

### §H.5 Boundary definitions

#### module

tools/acl_enforce/ — an immediate subdirectory of the koskadeux-mcp source root, comprising identity.py, lookup.py, gate.py, audit.py, orchestrate.py.

#### public contract

The field_acl DDL, the enforce_mode enum, resolve_writer_role/WriterIdentity, SloVerdict, the 403 sole_writer_mismatch error, the StateRequestError 404/409 codes raised by the orchestrator, and the acl_* event_type names.

#### runtime dependency

The koskadeux-mcp pyproject runtime dependencies; WS9 adds no new runtime dependency (Postgres via the existing driver, sqlite via stdlib for tests).

#### config default

None specific to this subsystem; the DB target is supplied at runtime via the DATABASE_PUBLIC_URL environment variable, which is not a config default.

### §H.6 Adjudication

If two agents classify the same change differently, the more restrictive classification wins. Disputes unresolvable under the predicates escalate to Max; the ruling is appended here as a per-system clarification.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs:
      - E-01
    scenario: Operator wants to begin WARN observation and field_acl currently has no enforce rows. Which call starts the WARN phase and what does it need?
    expected_answers:
      - kind: tool_call
        tool: tools/acl_enforce/orchestrate.py:start_phase_b_warn
        argument_keys:
          - conn
    weight: 0.09090909090909091
  - id: I-02
    type: operate
    refs:
      - E-02
    scenario: Before flipping a set of rows to enforce, the operator must confirm they are flip-ready. Which call evaluates readiness and over what inputs?
    expected_answers:
      - kind: tool_call
        tool: tools/acl_enforce/audit.py:evaluate_phase_c_slo
        argument_keys:
          - conn
          - eligible_rows
    weight: 0.09090909090909091
  - id: I-03
    type: operate
    refs:
      - E-03
    scenario: Max has directed flipping a verified-ready row set from warn to enforce. Which call performs the atomic flip and what does it require?
    expected_answers:
      - kind: tool_call
        tool: tools/acl_enforce/orchestrate.py:execute_phase_d_flip
        argument_keys:
          - conn
          - eligible_rows
          - operator
    weight: 0.09090909090909091
  - id: I-04
    type: isolate
    refs:
      - F-01
    scenario: A flip attempt returns 409 acl_phase_c_slo_not_ready. How do you diagnose why it is not ready?
    expected_answers:
      - kind: tool_call
        tool: tools/acl_enforce/audit.py:evaluate_phase_c_slo
        argument_keys:
          - conn
          - eligible_rows
    weight: 0.09090909090909091
  - id: I-05
    type: isolate
    refs:
      - F-02
    scenario: A flip attempt returns 409 field_acl_row_already_enforced. How do you confirm which rows are already enforced?
    expected_answers:
      - kind: tool_call
        tool: field_acl
        argument_keys:
          - enforce_mode
    weight: 0.09090909090909091
  - id: I-06
    type: isolate
    refs:
      - F-03
    scenario: A flip or rollback returns 404 field_acl_row_not_found. How do you verify the target row tuple?
    expected_answers:
      - kind: tool_call
        tool: field_acl
        argument_keys:
          - entity_kind
          - path_pattern
          - path_type
    weight: 0.09090909090909091
  - id: I-07
    type: repair
    refs:
      - G-01
      - F-02
    scenario: A row was flipped to enforce in error and must be reverted to warn with an audit trail. Which call performs the rollback and what does it need?
    expected_answers:
      - kind: tool_call
        tool: tools/acl_enforce/orchestrate.py:rollback_phase_e_row
        argument_keys:
          - conn
          - entity_kind
          - path_pattern
          - path_type
          - reason
          - operator
    weight: 0.09090909090909091
  - id: I-08
    type: repair
    refs:
      - G-02
      - F-01
    scenario: The SLO is not ready and you must remediate the offending writers then confirm readiness. Which call re-checks readiness after remediation?
    expected_answers:
      - kind: tool_call
        tool: tools/acl_enforce/audit.py:evaluate_phase_c_slo
        argument_keys:
          - conn
          - eligible_rows
    weight: 0.09090909090909091
  - id: I-09
    type: ambiguous
    refs:
      - E-03
    scenario: An operator says "turn on ACL enforcement" but gives no specific row set, no Phase C readiness result, and no recorded Max direction. What should the agent do?
    expected_answers:
      - kind: human_action
        tool: ask
        argument_keys:
          - eligible_rows
          - slo_verdict
          - max_direction
    weight: 0.09090909090909091
  - id: I-10
    type: evolve
    refs:
      - H.3
    scenario: Propose adding a new sole_writer_role to the field_acl seed and the identity resolver. Classify the change.
    expected_answers:
      - kind: classification
        tool: review
        argument_keys:
          - REVIEW
    weight: 0.09090909090909091
  - id: I-11
    type: evolve
    refs:
      - H.2
    scenario: Propose adding a third enforce_mode value 'soft' alongside warn and enforce. Classify the change.
    expected_answers:
      - kind: classification
        tool: breaking
        argument_keys:
          - BREAKING
    weight: 0.09090909090909091
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S784
last_refresh_commit: 2deca00f
last_refresh_date: "2026-06-06"
owner_agent: vulcan
refresh_triggers:
  - WS9 Chunk 6 (state_request enforce hook) ships — add live write-path rows to §B and a wiring scenario to §E
  - Any change to the field_acl DDL or the enforce_mode value set
  - Before any production enforce-flip (Phase D execution)
  - Resolution of the §F-05 precedence defect
scheduled_cadence: 90d
last_harness_pass_rate: null
last_harness_date: "2026-06-06"
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S784 / 2026-06-06T09:48:00Z
last_lint_result: PASS
trace_matrix_path: harness/acl-sole-writer-enforcement.trace.yaml
word_count_delta: initial
```
