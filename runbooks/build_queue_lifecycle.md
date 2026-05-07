---
system_name: build-queue-lifecycle
purpose_sentence: Lifecycle authority for ai.market build-queue items spanning the dashboard binary view, work-type taxonomy, mark-done verification per work type, automatic stage transitions, and the pre-cutover backfill rerun procedure.
owner_agent: max
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Operator semantics for the build-queue dashboard (active vs done), the work_type enum (production_code / spec_or_decision / runbook_or_doc / strategic_thread plus work_type_pending_triage), mark-done evidence rules per work_type, automatic transitions filed → in_progress → gate_4_passed, the explicit gate_4_passed → live completion gate, and the manual pre-cutover backfill rerun procedure.
linter_version: 1.0.0
---

# Build Queue Lifecycle

Operator runbook for the BQ lifecycle surface delivered under BQ-BUILD-QUEUE-LIFECYCLE-S544. Covers the dashboard's binary (active vs done) view, the four-value work_type taxonomy with `work_type_pending_triage`, mark-done verification rules per work_type, the automatic transition machinery (filed → in_progress → gate_4_passed), the explicit gate_4_passed → live completion gate, and the pre-cutover backfill rerun procedure.

## §A. Header

The YAML frontmatter above is authoritative for §A. Display values mirror §J; on drift, §J wins and the linter flags the header.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Dashboard binary view (active vs done) hides per-stage detail | SHIPPED | `ops-ai-market/src/components/build-queue/BuildQueuePanel.tsx:BuildQueuePanel` | `ops-ai-market/src/components/build-queue/__tests__` | 2026-05-07 |
| Stage detail drill-in panel (filed / in_progress / gate_4_passed / live) | SHIPPED | `ops-ai-market/src/components/build-queue/ItemDetail.tsx` | manual smoke pre-release | 2026-05-07 |
| Work-type taxonomy enum (production_code, spec_or_decision, runbook_or_doc, strategic_thread) plus work_type_pending_triage | SHIPPED | `ai-market-backend/app/schemas/bq_lifecycle.py:BuildQueueDetail` | `ai-market-backend/tests` | 2026-05-07 |
| Mark-done verification per work_type (deploy receipt, signed-off spec, lint+harness, Max-only for strategic_thread) | PARTIAL | `ai-market-backend/app/api/v2/endpoints/build_queue.py:complete_item` | `ai-market-backend/tests` | 2026-05-07 |
| Automatic transition filed → in_progress on first gate-1 spec write | SHIPPED | `ai-market-backend/app/api/v1/endpoints/bq_lifecycle.py:transition` | `ai-market-backend/tests` | 2026-05-07 |
| Automatic transition in_progress → gate_4_passed on all four gates approved | SHIPPED | `ai-market-backend/app/api/v1/endpoints/bq_lifecycle.py:transition` | `ai-market-backend/tests` | 2026-05-07 |
| Explicit gate_4_passed → live via POST `/api/v2/build-queue/{code}/complete` (Max token required) | SHIPPED | `ai-market-backend/app/api/v2/endpoints/build_queue.py:complete_item` | `ai-market-backend/tests` | 2026-05-07 |
| Pre-cutover backfill rerun (work_type + business_summary draft / review / Max sign-off) | SHIPPED | `koskadeux-mcp/tools/cleanup_adjudication.py:apply_max_signoff` | manual operator dry-run | 2026-05-07 |
| Legacy gate-string coercer for pre-typed entities | SHIPPED | `ai-market-backend/app/schemas/bq_lifecycle.py:BuildQueueDetail._coerce_legacy_gate_string` | `ai-market-backend/tests` | 2026-05-07 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Dashboard UI | `ops-ai-market/src/components/build-queue/BuildQueuePanel.tsx:BuildQueuePanel` | client filter state, fetched build entity list | v2 build-queue API, ItemDetail drill-in panel | Default view collapses internal stages into active vs done. Stage detail surfaces only via the ItemDetail drill-in. No multi-pill widget in the default view. |
| Lifecycle Detail Endpoint v1 | `ai-market-backend/app/api/v1/endpoints/bq_lifecycle.py:entity_to_build_queue_detail` | Living State `state:build:*` entities (read), `BuildQueueDetail` schema (serialise) | dashboard list + detail fetch, gate transition handlers | Maps a Living State build entity to the typed `BuildQueueDetail` shape consumed by the dashboard. The legacy gate-string coercer normalises pre-typed entities so a single bad row does not 500 the whole list response. |
| Build Queue Endpoints v2 | `ai-market-backend/app/api/v2/endpoints/build_queue.py:list_items` | Living State `state:build:*` entities (via lifecycle service) | dashboard, internal API key gate, rate limiter | Provides list, detail, reorder, affirm, priority, cancel, and complete operations. The complete operation is the explicit gate_4_passed → live transition; it requires a Max-issued token and an evidence package. |
| Detail Schema | `ai-market-backend/app/schemas/bq_lifecycle.py:BuildQueueDetail` | Pydantic schema (no persistence; runtime validation) | v1 and v2 endpoints | Contains the `_coerce_legacy_gate_string` field validator that wraps a legacy free-form gate status string into `{"status": <s>, "legacy_format": True}` so the dashboard renders the entity. The `legacy_format` marker is the cleanup signal tracked under BQ-LS-LEGACY-GATE-STRING-CLEANUP-S577. |
| Cleanup Adjudication Tool | `koskadeux-mcp/tools/cleanup_adjudication.py:apply_max_signoff` | adjudication tokens, draft verdict manifests | Max-token issuer, allAI state read, council review dispatch | Operator-facing harness for the pre-cutover backfill rerun. Drafts verdicts, reviews the manifest, and applies Max sign-off to issue a cleanup-adjudication token that gates Chunk 3 enforcement. |
| State Request Handler | `koskadeux-mcp/tools/state.py:_handle_state_request` | dispatched to per-action handlers (`_handle_state_bq_complete`, `_handle_state_bq_update`, `_handle_state_bq_bulk_update`) | Railway backend Living State HTTP API | Single entry point for BQ writes from operator tooling. All BQ priority, status, and completion writes flow through this handler — no direct Living State patches for priority bypass it. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| max | Mark BQ done (gate_4_passed → live) | `state_request -> bq_complete` | Max-issued completion token | COMPLETE |
| max | Apply backfill sign-off | `koskadeux:cleanup_adjudication.apply_max_signoff` | Max status_complete_override token | COMPLETE |
| cc | Draft work_type and business_summary backfill verdicts | `koskadeux:cleanup_adjudication.draft_verdicts` | internal API read | COMPLETE |
| vulcan | Update BQ priority or status (non-completion) | `state_request -> bq_update` | internal API write | COMPLETE |
| mp | Inspect BQ detail and gate evidence | `koskadeux:state_request -> bq_status` | internal API read | COMPLETE |
| ag | Run pre-cutover dry-run on draft manifest | `koskadeux:cleanup_adjudication.dispatch_council_review` | service-account read | PARTIAL — dry-run dispatch is stubbed pending Chunk 4 council wiring |
| sysadmin | Replay backfill on missing legacy entity | `koskadeux:cleanup_adjudication.draft_verdicts` then `apply_max_signoff` | internal API write + Max token | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: Operator opens the build-queue dashboard to triage active items and act on a stuck BQ.
  pre_conditions:
    - dashboard_session_authenticated
    - backend_reachable
  tool_or_endpoint: GET /api/v2/build-queue?show_completed=false&show_cancelled=false
  argument_sourcing:
    show_completed: literal false (binary view collapses done items by default)
    show_cancelled: literal false
  idempotency: IDEMPOTENT
  expected_success:
    shape: BuildQueueListResponse with active items only; completed_count and cancelled_count surfaced as counters
    verification: Dashboard renders active list with no per-stage pill widget; counters match completed_count and cancelled_count
  expected_failures:
    - signature: 429 rate_limit_exceeded
      cause: read rate limit exceeded for this actor
    - signature: 500 with malformed gate field
      cause: a build entity has a legacy free-form gate string that escaped the coercer
  next_step_success: Drill in via ItemDetail on the stuck BQ to see stage detail and act on it
  next_step_failure: Escalate to §F-01 if items appear stuck, or §F-03 if the list response 500s
- id: E-02
  trigger: Production_code BQ has shipped and the operator must mark it done with deploy evidence.
  pre_conditions:
    - bq_status_is_gate_4_passed
    - work_type_is_production_code
    - deploy_receipt_available
    - smoke_tests_passing
  tool_or_endpoint: POST /api/v2/build-queue/{code}/complete
  argument_sourcing:
    code: from dashboard ItemDetail header
    evidence_summary: composed by operator from deploy receipt and smoke test summary
    evidence_refs: list of URLs (Railway deploy URL plus smoke run URL)
    X-Max-Token: Max-issued completion token
    If-Match: version_stamp from current detail fetch
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(code + version_stamp)
  expected_success:
    shape: BuildQueueWriteResponse with detail.status == 'live' and version_stamp incremented
    verification: Re-fetch GET /api/v2/build-queue/{code} and confirm status 'live' and updated_at advanced
  expected_failures:
    - signature: 401 missing or invalid Max token
      cause: completion attempt lacks an Max-issued token in X-Max-Token
    - signature: 409 version_conflict
      cause: stale If-Match version_stamp
    - signature: 422 missing evidence_refs
      cause: production_code completion requires non-empty evidence_refs list
  next_step_success: Confirm the binary view now shows the BQ in the done counter and not in the active list
  next_step_failure: Escalate to §F-04 if completion repeatedly fails despite valid evidence
- id: E-03
  trigger: Operator runs the pre-cutover backfill rerun before flipping Chunk 3 enforcement on for missing work_type or business_summary.
  pre_conditions:
    - max_token_available
    - cleanup_adjudication_id_known_or_to_be_issued
    - chunk_3_enforcement_flag_currently_off
  tool_or_endpoint: koskadeux:cleanup_adjudication.draft_verdicts then dispatch_council_review then apply_max_signoff
  argument_sourcing:
    scope_filter: optional substring filter from the operator (e.g., 'BQ-CRM' to scope to one tree)
    adjudication_id: returned from draft_verdicts manifest write (or supplied by operator for rerun on prior id)
    max_token: Max-issued status_complete_override token
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: adjudication_id
  expected_success:
    shape: apply_max_signoff returns ok=true with cleanup_adjudication_token; draft_verdicts manifest enumerates entities lacking work_type or business_summary
    verification: Re-run draft_verdicts with the same scope and confirm the orphan list is empty before flipping the Chunk 3 enforcement flag
  expected_failures:
    - signature: ok=false with reason 'invalid_token' or 'wrong_scope'
      cause: Max token is missing, expired, or not scoped to status_complete_override
    - signature: orphan list non-empty after sign-off
      cause: a fresh BQ was created during the run and slipped past the manifest snapshot
    - signature: backend unreachable
      cause: Railway backend down or wrong RAILWAY_BACKEND_URL
  next_step_success: Flip the Chunk 3 enforcement flag and record the cleanup-adjudication-token in the cutover ledger
  next_step_failure: Escalate to §F-02 if a specific entity is missing work_type or to §F-05 if the token validation rejects the operator credential
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | A BQ has not advanced past in_progress past the stale threshold and dashboard shows it in active | gate review pending on a council reviewer; spec write blocked; work_type misclassified so transitions skipped | Read the BQ detail via GET /api/v2/build-queue/{code} and inspect gate1..gate4 status plus updated_at; cross-check council review queue | | CONFIRMED |
| F-02 | Work_type is missing on a legacy entity and the triage flag is set | entity predates the work_type taxonomy rollout; backfill never ran for this scope; work_type field stripped during a previous patch | Inspect the entity body via state_request bq_status and confirm work_type_pending_triage is true; cross-check the backfill manifest for an entry under this code | §G-02 | CONFIRMED |
| F-03 | Dashboard 500s when listing build-queue entities and a single entity has a malformed gate field | a legacy entity stored gate1 or gate2 as a free-form status string instead of a dict; the legacy_format coercer is bypassed (e.g., direct schema use without the validator) | Reproduce locally by fetching the offending entity directly and validating against BuildQueueDetail; confirm the coercer fires and produces a legacy_format=true wrapper | §G-01 | CONFIRMED |
| F-04 | Production_code completion call rejects with 422 despite operator supplying evidence | evidence_refs empty or whitespace; evidence_summary too short; deploy receipt URL malformed; X-Max-Token scope wrong | Re-issue the call with explicit evidence_refs list and confirm summary length; if still rejected, validate the Max token scope against status_complete_override | | HYPOTHESIZED |
| F-05 | Backfill apply_max_signoff returns ok=false with reason invalid_token or wrong_scope | Max token expired; token issued for a different action; operator pasted the wrong token into the runner | Re-fetch a fresh Max token scoped to status_complete_override and rerun apply_max_signoff with the same adjudication_id | | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-03
  component_ref: Detail Schema
  root_cause: 'A subset of pre-typed Living State build entities have gate1 or gate2 stored as free-form status strings; the BuildQueueDetail schema rejected str-where-dict-expected, 500ing the entire list response under any caller that did not pass through the coercer.'
  repair_entry_point: ai-market-backend/app/schemas/bq_lifecycle.py:BuildQueueDetail._coerce_legacy_gate_string
  change_pattern: 'Coerce legacy gate string values to a dict shape (status field plus legacy_format=true marker) via the field_validator so downstream consumers always see a dict; cleanup tracked via the legacy_format marker for migration removal.'
  rollback_procedure: 'Revert the field_validator to a no-op and reintroduce the strict dict-only schema; expect the offending entity to surface as a 500 again until a forward migration normalises the entity body.'
  integrity_check: 'Re-run the dashboard list fetch end-to-end and confirm the response is 200; grep the response for legacy_format=true to enumerate entities still requiring forward migration under BQ-LS-LEGACY-GATE-STRING-CLEANUP-S577.'
- id: G-02
  symptom_ref: F-02
  component_ref: Cleanup Adjudication Tool
  root_cause: 'A legacy build entity exists without work_type or business_summary because it predates the taxonomy rollout or had its body stripped during a prior patch; the dashboard surfaces the work_type_pending_triage flag and Chunk 3 enforcement would block the entity if flipped on.'
  repair_entry_point: koskadeux-mcp/tools/cleanup_adjudication.py:apply_max_signoff
  change_pattern: 'Run draft_verdicts scoped to the affected code or scope_filter, review the manifest for the missing entity, then call apply_max_signoff with a Max status_complete_override token to issue a cleanup-adjudication-token; the token is the audit anchor for the rerun.'
  rollback_procedure: 'Cleanup writes are append-only via the adjudication token; rollback is to ignore the token and re-issue a fresh adjudication if the verdicts are wrong; no destructive rollback is required because the token does not mutate the entity body until Chunk 3 enforcement applies it.'
  integrity_check: 'Re-run draft_verdicts with the same scope_filter and confirm the orphan list is empty; spot-check three entities via state_request bq_status and confirm work_type and business_summary are populated and work_type_pending_triage is false.'
```

## §H. Evolve

### §H.1 Invariants

- Auto-promotion past gate_4_passed is forbidden. The gate_4_passed → live transition is only ever via POST `/api/v2/build-queue/{code}/complete` carrying a Max-issued token plus an evidence package. The transition handler MUST NOT promote on its own.
- Strategic_thread items never auto-complete. Mark-done for a strategic_thread requires an explicit Max-only action with a written reason; no system path auto-flips a strategic_thread to live.
- All BQ writes flow through `state_request`. Operator tooling MUST NOT patch Living State priority, status, or work_type fields directly; the path is `state_request -> bq_update` (and `bq_complete` for the explicit completion gate).
- The dashboard default view is binary (active vs done). The default list view MUST NOT surface a multi-pill widget for internal stages; per-stage detail is exposed only via the ItemDetail drill-in panel.
- The work_type enum is closed at four values: production_code, spec_or_decision, runbook_or_doc, strategic_thread. The pre-classification flag is `work_type_pending_triage` (boolean). Adding or removing an enum value is a §H.2 BREAKING change.
- Mark-done evidence rules are work-type-specific. Production_code requires a deploy receipt URL plus smoke test pass; spec_or_decision requires a signed-off spec doc commit; runbook_or_doc requires a lint-passing and harness-passing runbook merged; strategic_thread requires Max-only sign-off with reason.

### §H.2 BREAKING predicates

- Adding, removing, or renaming a value in the work_type enum.
- Removing the `work_type_pending_triage` field or repurposing its semantics.
- Changing the auto-promotion stage policy so that gate_4_passed → live can fire without an explicit Max-token call.
- Removing or renaming any of the v2 endpoints (list, detail, reorder, affirm, priority, cancel, complete) without a backwards-compatible shim.
- Changing the schema of the BuildQueueDetail gate fields in a way that breaks the legacy_format coercer's output shape.

### §H.3 REVIEW predicates

- Adding a new mark-done evidence rule for an existing work_type (e.g., requiring a security-review URL alongside the deploy receipt for production_code).
- Adding a new dashboard filter or counter on top of the binary view that does not introduce a multi-pill widget.
- Changing the rate limits on the v2 endpoints.
- Adding a new operator-callable action on the cleanup_adjudication tool surface.
- Refactoring the lifecycle service into a different module while preserving the v1 and v2 endpoint signatures.

### §H.4 SAFE predicates

- Bug fixes inside `BuildQueueDetail._coerce_legacy_gate_string` that preserve the output shape `{"status": <s>, "legacy_format": True}`.
- Adding logging or metrics around an existing endpoint without changing the response shape.
- Documentation-only updates to this runbook.
- Test additions for any §B feature row.
- Internal renames inside `_handle_state_bq_complete` or `_handle_state_bq_update` that preserve the public skill_tool surface.

### §H.5 Boundary definitions

#### module

A module under this runbook is an immediate subdirectory of a system source root involved in the BQ lifecycle: `ai-market-backend/app/api/`, `ai-market-backend/app/schemas/`, `ai-market-backend/app/services/`, `koskadeux-mcp/tools/`, and `ops-ai-market/src/components/build-queue/`. Cross-module refactors are §H.3 REVIEW unless they also tip a §H.2 predicate.

#### public contract

Public contract for this runbook is the v1 and v2 build-queue HTTP surface (paths, methods, request and response shapes), the `state_request` skill operations exposed by koskadeux-mcp (`bq_complete`, `bq_update`, `bq_bulk_update`, `bq_status`), and the `cleanup_adjudication` tool function signatures (`draft_verdicts`, `dispatch_council_review`, `apply_max_signoff`).

#### runtime dependency

Runtime dependencies for this runbook are the Railway backend Living State HTTP API (read and write), the Max-token issuer for completion and cleanup-adjudication tokens, and the `INTERNAL_API_KEY` environment variable consumed by both the v2 endpoints and the cleanup_adjudication client. Test fixtures, in-process stubs, and dev-only environment overrides are not runtime dependencies.

#### config default

Config defaults under this runbook are: `RAILWAY_BACKEND_URL` falling back to the production URL inside `cleanup_adjudication.py`, the v2 endpoint rate limits (READ_LIMIT=600/min, WRITE_LIMIT=60/min, WINDOW_SECONDS=60), and the dashboard default filters (`show_completed=false`, `show_cancelled=false`). Changing any of these defaults is §H.3 REVIEW.

### §H.6 Adjudication

When a proposed change touches more than one boundary class, classify at the highest-risk class and document the rationale in the change record. Disputes between agents on classification escalate to Max; the ruling is added back to §H.1 Invariants as a per-system clarification so the next reviewer inherits the precedent.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: Operator opens the dashboard and needs the first action to view active build-queue items in the binary view.
    expected_answers:
      - kind: tool_call
        tool: GET /api/v2/build-queue
        argument_keys: [show_completed, show_cancelled]
    weight: 0.08333333333333333
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: A production_code BQ has shipped with a deploy receipt and smoke tests passing; the operator must mark it done.
    expected_answers:
      - kind: tool_call
        tool: POST /api/v2/build-queue/{code}/complete
        argument_keys: [evidence_summary, evidence_refs]
    weight: 0.08333333333333333
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: Pre-cutover, the operator must rerun the work_type and business_summary backfill before flipping Chunk 3 enforcement.
    expected_answers:
      - kind: tool_call
        tool: koskadeux:cleanup_adjudication.draft_verdicts
        argument_keys: [scope_filter]
    weight: 0.08333333333333333
  - id: I-04
    type: operate
    refs: [E-01]
    scenario: From the binary view, the operator wants stage detail for a single stuck BQ before deciding whether to escalate.
    expected_answers:
      - kind: tool_call
        tool: GET /api/v2/build-queue/{code}
        argument_keys: [code]
    weight: 0.08333333333333333
  - id: I-05
    type: isolate
    refs: [F-01]
    scenario: A BQ has been in_progress past the stale threshold; the responder must verify what is blocking advancement before acting.
    expected_answers:
      - kind: tool_call
        tool: GET /api/v2/build-queue/{code}
        argument_keys: [code]
    weight: 0.08333333333333333
  - id: I-06
    type: isolate
    refs: [F-02]
    scenario: A legacy entity surfaces with work_type_pending_triage true; the responder must confirm the missing fields before queueing a backfill.
    expected_answers:
      - kind: tool_call
        tool: koskadeux:state_request
        argument_keys: [op, key]
    weight: 0.08333333333333333
  - id: I-07
    type: isolate
    refs: [F-03]
    scenario: The dashboard list endpoint 500s and the responder must determine whether a single legacy gate-string entity is the cause.
    expected_answers:
      - kind: human_action
        verb: validate
        object: BuildQueueDetail schema against the offending entity body
        target: ai-market-backend/app/schemas/bq_lifecycle.py
    weight: 0.08333333333333333
  - id: I-08
    type: repair
    refs: [G-01]
    scenario: A repair is required for the malformed gate-string class of entities that 500 the list endpoint.
    expected_answers:
      - kind: human_action
        verb: patch
        object: legacy gate-string coercer
        target: ai-market-backend/app/schemas/bq_lifecycle.py:BuildQueueDetail._coerce_legacy_gate_string
    weight: 0.08333333333333333
  - id: I-09
    type: repair
    refs: [G-02]
    scenario: A specific BQ is missing work_type and the operator must reissue the backfill scoped to that code.
    expected_answers:
      - kind: tool_call
        tool: koskadeux:cleanup_adjudication.apply_max_signoff
        argument_keys: [adjudication_id, max_token]
    weight: 0.08333333333333333
  - id: I-10
    type: evolve
    refs: ["§H"]
    scenario: A proposal adds a fifth value to the work_type enum (e.g., infrastructure_change) and needs classification against the evolve predicates.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-11
    type: evolve
    refs: ["§H"]
    scenario: A proposal changes the auto-promotion policy so gate_4_passed → live can fire without an explicit Max-token call when all gates are CLEAN.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-12
    type: ambiguous
    refs: [E-02, F-04, "§H"]
    scenario: A production_code completion attempt repeatedly 422s; possible causes include empty evidence_refs, a wrong-scope Max token, or a work_type misclassification that should not be production_code.
    expected_answers:
      - kind: human_action
        verb: investigate
        object: completion 422 cause
        target: evidence_refs payload, X-Max-Token scope, and work_type field on the entity
    weight: 0.08333333333333333
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S544
last_refresh_commit: 1dde2b9
last_refresh_date: 2026-05-07T12:00:00Z
owner_agent: max
refresh_triggers:
  - bq_completion
  - gate_approval
  - incident
  - chunk_3_enforcement_flip
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-05-07T12:00:00Z
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S544 / 2026-05-07T12:00:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
