---
system_name: build-queue-lifecycle
purpose_sentence: Lifecycle authority for ai.market build-queue items spanning the v2 endpoint surface, the centralized transition invariant validator, evidence-based completion, soft-freeze enforcement, the override token lifecycle, and the cleanup adjudication harness.
owner_agent: max
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Operator semantics for the v2 build-queue HTTP surface (list, detail, cancel, priority, reorder, affirm, complete), the centralized transition invariant validator that enforces evidence on status→completed across every mutation path, evidence-based completion via POST /complete (status→done), the soft-freeze enforcement layer, override token issuance / atomic CAS consumption / scoping / revocation, and the cleanup adjudication harness used to draft verdicts and issue cleanup_adjudication tokens.
linter_version: 1.0.0
---

# Build Queue Lifecycle

Operator runbook for the BQ lifecycle surface delivered under BQ-BUILD-QUEUE-LIFECYCLE-S544 Chunks 1, 1.5, 2, 3, 4. Covers the v2 build-queue HTTP surface (seven endpoints), the LS-side centralized transition invariant validator (`_validate_lifecycle_transition`) that enforces non-empty evidence on every transition into `completed`, evidence-based completion via POST `/api/v2/build-queue/{code}/complete` (transitions status to `done`), the soft-freeze enforcement layer with override-token bypass, the override token lifecycle (issuance, atomic CAS consumption, scoping, revocation), and the cleanup adjudication harness used to backfill missing `business_summary` values.

## §A. Header

The YAML frontmatter above is authoritative for §A. Display values mirror §J; on drift, §J wins and the linter flags the header.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| v2 build-queue endpoint surface (list, detail, cancel, priority, reorder, affirm, complete) | SHIPPED | `ai-market-backend/app/api/v2/endpoints/build_queue.py` | `ai-market-backend/tests` | 2026-05-07 |
| Dashboard list view with active/completed/cancelled counters and item drill-in | SHIPPED | `ops-ai-market/src/components/build-queue/BuildQueuePanel.tsx:BuildQueuePanel` | `ops-ai-market/src/components/build-queue/__tests__` | 2026-05-07 |
| Modal-based mark-complete with evidence_summary + evidence_refs and If-Match header | SHIPPED | `ops-ai-market/src/components/build-queue/BuildQueuePanel.tsx` | manual smoke pre-release | 2026-05-07 |
| Centralized transition invariant validator — `_validate_lifecycle_transition` enforces evidence on every mutation path for status→completed | SHIPPED | `ai-market-backend/app/services/bq_lifecycle_service.py:_validate_lifecycle_transition` | `ai-market-backend/tests` | 2026-05-07 |
| Mark-done verification (evidence-based with cleanup_adjudication_token override on the LS validator) | SHIPPED | `ai-market-backend/app/api/v2/endpoints/build_queue.py:complete_item` | `ai-market-backend/tests` | 2026-05-07 |
| Soft-freeze enforcement with override-token bypass | SHIPPED | `koskadeux-mcp/tools/soft_freeze.py:evaluate_freeze` | `tests` (koskadeux-mcp) | 2026-05-07 |
| Override token lifecycle: issuance, atomic CAS consumption, scoping, revocation | SHIPPED | `koskadeux-mcp/tools/token_lifecycle.py` | `tests` (koskadeux-mcp) | 2026-05-07 |
| Cleanup adjudication harness — draft_verdicts, dispatch_council_review, apply_max_signoff | SHIPPED | `koskadeux-mcp/tools/cleanup_adjudication.py:apply_max_signoff` | manual operator dry-run | 2026-05-07 |
| Legacy gate-string coercer for pre-typed entities | SHIPPED | `ai-market-backend/app/schemas/bq_lifecycle.py:BuildQueueDetail._coerce_legacy_gate_string` | `ai-market-backend/tests` | 2026-05-07 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Dashboard UI | `ops-ai-market/src/components/build-queue/BuildQueuePanel.tsx:BuildQueuePanel` | client filter state, fetched build entity list | v2 build-queue API, modal mark-complete dialog | Renders the list with per-row gate pipeline (`<GatePipeline entity={entity} />`); `updated_at` drives the 30s refresh signal. Mark-complete is a modal dialog that POSTs to /complete with `If-Match` carrying the current `version_stamp`. |
| Build Queue Endpoints v2 | `ai-market-backend/app/api/v2/endpoints/build_queue.py` | Living State `state:build:*` entities (via lifecycle service) | dashboard, internal API key gate, rate limiter | Provides list, detail, cancel, priority, reorder, affirm, and complete operations. The proxy carries metadata (event_payload or auto-derive, evidence, expected_version, actor, cleanup_adjudication_token) to LS; LS is the enforcement layer. The proxy returns 422 verbatim from the LS validator. |
| Lifecycle Service | `ai-market-backend/app/services/bq_lifecycle_service.py:BuildQueueLifecycleService` | Living State entities (read+write via atomic CAS) | v2 endpoints, validators, event ledger writer | Hosts the centralized transition invariant validator (`_validate_lifecycle_transition`) that runs on every mutation path before commit. Inspects pre/post `body.status`; transitions into `completed` require non-empty evidence (`evidence_summary`, `evidence_refs`, `actor`) unless an override_token is supplied. |
| Detail Schema | `ai-market-backend/app/schemas/bq_lifecycle.py:BuildQueueDetail` | Pydantic schema (no persistence; runtime validation) | v2 endpoints, dashboard | Status literal closed at: `planned`, `in_progress`, `completed`, `failed`, `blocked`, `cut`, `approved`, `done`. The `_coerce_legacy_gate_string` field validator (lines 63–81) wraps a legacy free-form gate status string into `{"status": <s>, "legacy_format": True}` so the dashboard renders the entity. |
| Cleanup Adjudication Tool | `koskadeux-mcp/tools/cleanup_adjudication.py:apply_max_signoff` | adjudication tokens, draft verdict manifests | Max-token issuer, allAI state read, council review dispatch | Operator-facing harness. `draft_verdicts` enumerates build entities; `dispatch_council_review` is stubbed pending Chunk 4 council wiring; `apply_max_signoff` validates a `status_complete_override` Max-token and issues a `cleanup_adjudication_token` scoped to the `adjudication_id`. |
| Token Lifecycle | `koskadeux-mcp/tools/token_lifecycle.py` | `config:build-queue-tokens` LS entity | cleanup_adjudication, soft_freeze, LS validator | Issues `max_urgent_override`, `cleanup_adjudication_token`, and `freeze_lift_operation` tokens. `validate_token_authorization` checks kind/state/scope. Tokens have a `state` field (`active`/`used`/`revoked`); the protected operation flips the state via single-transaction CAS. |
| Soft-Freeze Layer | `koskadeux-mcp/tools/soft_freeze.py:evaluate_freeze` | `config:build-queue-freeze` LS entity (5s TTL cache) | LS mutation handlers, override-token validator | Blocks status_change, priority_change, reorder, cancel, defer, complete, bq_create, bq_update, bq_bulk_update, patch_status, put_status, status_complete_override when `is_freeze_active()`. Allows reads and `affirm`. Override tokens bypass and are logged. |
| State Request Handler | `koskadeux-mcp/tools/state.py:_handle_state_request` | dispatched to per-action handlers | Railway backend Living State HTTP API | Single entry point for BQ writes from operator tooling. All BQ priority, status, and completion writes flow through this handler — no direct LS patches for priority bypass it. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| max | Mark BQ done with evidence | POST `/api/v2/build-queue/{code}/complete` | internal API key + evidence body + If-Match | COMPLETE |
| max | Issue an override token | `koskadeux:token_lifecycle.issue_max_urgent_override` | Max-only credential | COMPLETE |
| max | Apply cleanup adjudication sign-off | `koskadeux:cleanup_adjudication.apply_max_signoff` | Max status_complete_override token | COMPLETE |
| cc | Draft cleanup adjudication verdicts | `koskadeux:cleanup_adjudication.draft_verdicts` | internal API read | COMPLETE |
| vulcan | Update BQ priority or status (non-completion) | `state_request -> bq_update` | internal API write | COMPLETE |
| mp | Inspect BQ detail | `koskadeux:state_request -> bq_status` | internal API read | COMPLETE |
| ag | Run pre-cutover dry-run on draft manifest | `koskadeux:cleanup_adjudication.dispatch_council_review` | service-account read | PARTIAL — dispatch is stubbed pending council-review wiring |
| sysadmin | Reissue cleanup adjudication on a missing entity | `koskadeux:cleanup_adjudication.draft_verdicts` then `apply_max_signoff` | internal API write + Max token | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: Operator opens the build-queue dashboard to triage active items and act on a stuck BQ.
  pre_conditions:
    - dashboard_session_authenticated
    - backend_reachable
  tool_or_endpoint: GET /api/v2/build-queue
  argument_sourcing:
    show_completed: literal false (default filter; completed items reachable via toggle)
    show_cancelled: literal false
  idempotency: IDEMPOTENT
  expected_success:
    shape: BuildQueueListResponse with items list plus completed_count and cancelled_count counters
    verification: Dashboard renders the list with per-row gate pipeline; counters match completed_count and cancelled_count; updated_at indicators advance on the 30s poll
  expected_failures:
    - signature: 429 rate_limit_exceeded
      cause: read rate limit exceeded for this actor
    - signature: 500 with malformed gate field
      cause: a build entity has a legacy free-form gate string that escaped the coercer
  next_step_success: Drill in via the row's detail panel to see gate detail and act on it
  next_step_failure: Escalate to §F-01 if items appear stuck, or §F-03 if the list response 500s
- id: E-02
  trigger: A BQ has shipped and the operator must mark it done with evidence.
  pre_conditions:
    - bq_in_terminal_ready_state
    - evidence_summary_drafted
    - evidence_refs_collected
    - current_version_stamp_known
  tool_or_endpoint: POST /api/v2/build-queue/{code}/complete
  argument_sourcing:
    code: from dashboard row or detail panel
    evidence_summary: composed by operator from the supporting artifacts
    evidence_refs: list of URLs (e.g., Railway deploy URL plus smoke run URL, or merged PR URL)
    If-Match: version_stamp from current detail fetch
    actor: derived from the internal API key context on the proxy
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(code + version_stamp)
  expected_success:
    shape: BuildQueueWriteResponse with detail.status == 'done' and version_stamp incremented
    verification: Re-fetch GET /api/v2/build-queue/{code} and confirm status 'done' and updated_at advanced
  expected_failures:
    - signature: 409 version_conflict
      cause: stale If-Match version_stamp; the entity was mutated between fetch and complete
    - signature: 422 completion_evidence_required
      cause: LS-side centralized transition validator rejected the transition because evidence_summary, evidence_refs, or actor was missing or empty (only fires when the resulting status is `completed`, not on direct `done` writes — see expected_failures below)
    - signature: 422 with field_errors from BuildQueueCompleteRequest
      cause: evidence_summary not a string or evidence_refs not a list
    - signature: 503 soft_freeze_active
      cause: soft-freeze is on and the caller did not supply a valid override token
  next_step_success: Confirm the dashboard now shows the BQ in the completed counter and not in the active list
  next_step_failure: Escalate to §F-04 if completion repeatedly fails despite valid evidence
- id: E-03
  trigger: Operator runs the cleanup adjudication harness to issue a cleanup_adjudication_token for a backfill scope before flipping enforcement.
  pre_conditions:
    - max_token_available
    - adjudication_id_known_or_to_be_issued
    - chunk_3_enforcement_state_known
  tool_or_endpoint: koskadeux:cleanup_adjudication.draft_verdicts then apply_max_signoff
  argument_sourcing:
    scope_filter: optional substring filter (e.g., 'BQ-CRM' to scope to one tree)
    adjudication_id: caller-chosen identifier reused for sign-off (or fresh per run)
    max_token: Max-issued status_complete_override token (max_urgent_override kind)
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: adjudication_id
  expected_success:
    shape: apply_max_signoff returns ok=true with cleanup_adjudication_token; draft_verdicts returns a verdict list per scope
    verification: Re-run draft_verdicts with the same scope and confirm the orphan list is empty before flipping the enforcement flag
  expected_failures:
    - signature: ok=false with reason 'token_not_found' / 'token_expired' / 'token_scope_mismatch' / 'token_kind_action_unauthorized'
      cause: Max token is missing, expired, wrong scope, or wrong kind for the status_complete_override action
    - signature: orphan list non-empty after sign-off
      cause: a fresh BQ was created during the run and slipped past the manifest snapshot
    - signature: backend unreachable
      cause: Railway backend down or wrong RAILWAY_BACKEND_URL
  next_step_success: Archive the adjudication manifest (Chunk 4 cleanup pre-flight) and record the cleanup_adjudication_token in the cutover ledger
  next_step_failure: Escalate to §F-02 if a specific entity is missing business_summary or to §F-05 if the token validation rejects the operator credential
```

## §F. Isolate

This section covers fault isolation for the build-queue lifecycle surface. Cleanup adjudication runs are archived as part of the Chunk 4 pre-flight (per BQ-BUILD-QUEUE-LIFECYCLE-S544 Gate 2 v6 AC4.0 / AC4.7 and AC5.2); the manifest produced by `cleanup_adjudication.draft_verdicts` is the audit anchor referenced for any retroactive isolation work involving missing `business_summary` values.

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | A BQ has not advanced past in_progress past the stale threshold and dashboard shows it in active | gate review pending on a council reviewer; spec write blocked; soft-freeze active | Read the BQ detail via GET /api/v2/build-queue/{code} and inspect gate1..gate4 status plus updated_at; check `is_freeze_active()` via `state_request -> get config:build-queue-freeze` | | CONFIRMED |
| F-02 | A legacy entity surfaces without business_summary and Chunk 3 enforcement would block writes | entity predates business_summary requirement; previous patch stripped the field | Inspect the entity body via state_request bq_status and confirm business_summary is empty or missing; cross-check the most recent Chunk 4 cleanup adjudication manifest for an entry under this code | §G-02 | CONFIRMED |
| F-03 | Dashboard 500s when listing build-queue entities and a single entity has a malformed gate field | a legacy entity stored gate1 or gate2 as a free-form status string instead of a dict; the legacy_format coercer is bypassed (e.g., direct schema use without the field_validator) | Reproduce locally by fetching the offending entity directly and validating against BuildQueueDetail; confirm the coercer fires and produces a legacy_format=true wrapper | §G-01 | CONFIRMED |
| F-04 | Completion call repeatedly rejects with 422 despite operator supplying evidence | evidence_summary empty or missing; evidence_refs empty list; actor missing on the LS-side validator path; cleanup_adjudication_token wrong scope | Re-issue the call with explicit non-empty evidence_summary and at least one evidence_ref; re-fetch the version_stamp; if invoking via `bq_update` with an override token, validate the token's `kind=cleanup_adjudication_token` and `scope=<adjudication_id>` | | CONFIRMED |
| F-05 | apply_max_signoff returns ok=false with reason token_not_found / token_expired / token_scope_mismatch | Max token expired; token issued for a different action; operator pasted the wrong token; token already revoked or consumed | Re-issue a fresh max_urgent_override scoped to status_complete_override and rerun apply_max_signoff with the same adjudication_id; check `config:build-queue-tokens` for the token's state field | | CONFIRMED |
| F-06 | Mutation rejected with 503 soft_freeze_active | soft-freeze flag is on and the caller supplied no override token (or an invalid one) | Read `config:build-queue-freeze` body and confirm `active=true`; if the operation is genuinely urgent, request a `freeze_lift_operation` token from Max | | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-03
  component_ref: Detail Schema
  root_cause: 'A subset of pre-typed Living State build entities have gate1 or gate2 stored as free-form status strings; the BuildQueueDetail schema rejected str-where-dict-expected, 500ing the entire list response under any caller that did not pass through the field_validator.'
  repair_entry_point: ai-market-backend/app/schemas/bq_lifecycle.py:BuildQueueDetail._coerce_legacy_gate_string
  change_pattern: 'Coerce legacy gate string values to a dict shape (status field plus legacy_format=true marker) via the field_validator at lines 63–81 so downstream consumers always see a dict; cleanup tracked via the legacy_format marker for migration removal.'
  rollback_procedure: 'Revert the field_validator to a no-op and reintroduce the strict dict-only schema; expect the offending entity to surface as a 500 again until a forward migration normalises the entity body.'
  integrity_check: 'Re-run the dashboard list fetch end-to-end and confirm the response is 200; grep the response for legacy_format=true to enumerate entities still requiring forward migration under BQ-LS-LEGACY-GATE-STRING-CLEANUP.'
- id: G-02
  symptom_ref: F-02
  component_ref: Cleanup Adjudication Tool
  root_cause: 'A legacy build entity exists without business_summary because it predates the field requirement or had its body stripped during a prior patch; Chunk 3 enforcement would block bq_update on this entity until the field is populated.'
  repair_entry_point: koskadeux-mcp/tools/cleanup_adjudication.py:apply_max_signoff
  change_pattern: 'Run draft_verdicts scoped to the affected code or scope_filter, review the manifest for the missing entity, then call apply_max_signoff with a Max status_complete_override token to issue a cleanup_adjudication_token; the token is the audit anchor and is consumed atomically when the bq_update path applies it.'
  rollback_procedure: 'Tokens are append-only in `config:build-queue-tokens`; rollback is to revoke the token via revoke_token(token_id, reason) before it is consumed. After consumption, the entity body update is the rollback target — revert via a fresh bq_update with the prior body.'
  integrity_check: 'Re-run draft_verdicts with the same scope_filter and confirm the orphan list is empty; spot-check three entities via state_request bq_status and confirm business_summary is populated.'
```

## §H. Evolve

### §H.1 Invariants

- The centralized transition invariant validator (`_validate_lifecycle_transition` at `ai-market-backend/app/services/bq_lifecycle_service.py:460`) MUST run on every mutation path before commit. Status transitions into `completed` require a non-empty evidence object (`evidence_summary`, `evidence_refs`, `actor`) unless a valid override token is supplied via the override_token parameter. Direct LS writes cannot bypass.
- All BQ writes flow through `state_request`. Operator tooling MUST NOT patch Living State priority, status, or body fields directly; the path is `state_request -> bq_update` (and the v2 /complete endpoint for the explicit completion gate).
- The lifecycle status enum is closed at the values declared in `_LIFECYCLE_STATUS_VALUES` (`planned`, `in_progress`, `completed`, `failed`, `blocked`, `cut`, `approved`, `done`). Adding or removing a value is a §H.2 BREAKING change.
- The v2 endpoint surface is closed at seven endpoints (list, detail, cancel, priority, reorder, affirm, complete). Removing or renaming any is a §H.2 BREAKING change.
- Token lifecycle invariants:
  - **Issuance.** Tokens are issued by `koskadeux-mcp/tools/token_lifecycle.py`. `issue_max_urgent_override(scope, expires_in_seconds=3600)` issues a Max-only override (default 1-hour time-box). `issue_cleanup_adjudication_token(adjudication_id)` is invoked from `apply_max_signoff` after Max-token validation. `issue_freeze_lift_operation_token` issues the freeze-lift token.
  - **Atomic CAS consumption.** `verify_and_consume_token` (descriptor at `TokenCasDescriptor(token_id, action_kind, expected_state='active', target_state='used')`) performs a single-transaction state CAS from `active` to `used`. Concurrent callers race on this CAS — exactly one wins; the protected operation runs only on success.
  - **Scoping.** Each token kind has a scope field. `cleanup_adjudication_token` scope is the `adjudication_id`. `freeze_lift_operation` scope is the literal `freeze_lift`. `max_urgent_override` scope can be `*` (any) or a specific action target. Scope is validated via `_scope_matches` against the AUTHORIZATION_RULES table at `token_lifecycle.py:14`.
  - **Revocation.** `revoke_token(token_id, reason)` flips state to `revoked` and records `revoked_reason` and `revoked_at`. Revocation does not affect already-`used` tokens (the protected mutation already happened).
- The soft-freeze enforcement layer (`koskadeux-mcp/tools/soft_freeze.py:evaluate_freeze`) blocks the action kinds in `BLOCKED_ACTION_KINDS` when `is_freeze_active()` returns true; allows reads and `affirm`; and treats a valid override token as a bypass with mandatory consumption.

### §H.2 BREAKING predicates

- Adding, removing, or renaming a value in `_LIFECYCLE_STATUS_VALUES`.
- Removing or renaming any of the seven v2 endpoints (list, detail, cancel, priority, reorder, affirm, complete) without a backwards-compatible shim.
- Changing `_validate_lifecycle_transition` so that status→completed can succeed without an evidence object AND without a valid override token.
- Removing or repurposing the `cleanup_adjudication_token` override path on the LS validator.
- Changing the token state machine (`active` → `used` → `revoked`) so concurrent callers can both consume the same token.
- Changing the `BuildQueueCompleteRequest` schema to drop `evidence_summary` or `evidence_refs`.
- Changing the schema of the BuildQueueDetail gate fields in a way that breaks the legacy_format coercer's output shape `{"status": <s>, "legacy_format": True}`.

### §H.3 REVIEW predicates

- Adding a new evidence rule (e.g., requiring a security-review URL alongside the deploy receipt) on top of the existing evidence_summary + evidence_refs requirement.
- Adding a new dashboard filter or counter on top of the current list view.
- Changing the rate limits on the v2 endpoints.
- Adding a new operator-callable action on the cleanup_adjudication tool surface.
- Adding a new token kind to the AUTHORIZATION_RULES table.
- Refactoring the lifecycle service into a different module while preserving the v2 endpoint signatures and the validator's enforced invariants.

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

Public contract for this runbook is the v2 build-queue HTTP surface (paths, methods, request and response shapes), the `state_request` skill operations exposed by koskadeux-mcp (`bq_complete`, `bq_update`, `bq_bulk_update`, `bq_status`), the `cleanup_adjudication` tool function signatures (`draft_verdicts`, `dispatch_council_review`, `apply_max_signoff`), and the `token_lifecycle` tool function signatures (`issue_max_urgent_override`, `issue_cleanup_adjudication_token`, `issue_freeze_lift_operation_token`, `validate_token_authorization`, `revoke_token`).

#### runtime dependency

Runtime dependencies for this runbook are the Railway backend Living State HTTP API (read and write), the Max-token issuer for max_urgent_override tokens, and the `INTERNAL_API_KEY` environment variable consumed by the v2 endpoints, the cleanup_adjudication client, the token_lifecycle client, and the soft_freeze client. Test fixtures, in-process stubs, and dev-only environment overrides are not runtime dependencies.

#### config default

Config defaults under this runbook are: `RAILWAY_BACKEND_URL` falling back to the production URL inside `cleanup_adjudication.py`, `token_lifecycle.py`, and `soft_freeze.py`; the v2 endpoint rate limits (READ_LIMIT and WRITE_LIMIT); the soft-freeze cache TTL (`_CACHE_TTL_SECONDS=5.0`); the dashboard default filters (`show_completed=false`, `show_cancelled=false`); and the default token expiry (`expires_in_seconds=3600`). Changing any of these defaults is §H.3 REVIEW.

### §H.6 Adjudication

When a proposed change touches more than one boundary class, classify at the highest-risk class and document the rationale in the change record. Disputes between agents on classification escalate to Max; the ruling is added back to §H.1 Invariants as a per-system clarification so the next reviewer inherits the precedent.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: Operator opens the dashboard and needs the first action to view active build-queue items.
    expected_answers:
      - kind: tool_call
        tool: GET /api/v2/build-queue
        argument_keys: [show_completed, show_cancelled]
    weight: 0.08333333333333333
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: A BQ has shipped with evidence summary and supporting URLs ready; the operator must mark it done.
    expected_answers:
      - kind: tool_call
        tool: POST /api/v2/build-queue/{code}/complete
        argument_keys: [evidence_summary, evidence_refs]
    weight: 0.08333333333333333
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: Pre-cutover, the operator must run cleanup adjudication on a scope to issue a cleanup_adjudication_token before flipping enforcement.
    expected_answers:
      - kind: tool_call
        tool: koskadeux:cleanup_adjudication.draft_verdicts
        argument_keys: [scope_filter]
    weight: 0.08333333333333333
  - id: I-04
    type: operate
    refs: [E-01]
    scenario: From the list view, the operator wants gate detail for a single stuck BQ before deciding whether to escalate.
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
    refs: [F-06]
    scenario: A bq_update mutation fails with 503 soft_freeze_active and the responder must verify whether soft-freeze is genuinely on before requesting an override token.
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
    scenario: A specific BQ is missing business_summary and the operator must reissue the cleanup adjudication scoped to that code, then apply Max sign-off to obtain a cleanup_adjudication_token.
    expected_answers:
      - kind: tool_call
        tool: koskadeux:cleanup_adjudication.apply_max_signoff
        argument_keys: [adjudication_id, max_token]
    weight: 0.08333333333333333
  - id: I-10
    type: evolve
    refs: ["§H"]
    scenario: A proposal removes the cleanup_adjudication_token override path from `_validate_lifecycle_transition` so that status→completed always requires inline evidence; needs classification against the evolve predicates.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-11
    type: evolve
    refs: ["§H"]
    scenario: A proposal changes `_validate_lifecycle_transition` so that status→completed can succeed without an evidence object AND without an override token (i.e., evidence becomes optional).
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-12
    type: ambiguous
    refs: [E-02, F-04, "§H"]
    scenario: A completion call repeatedly 422s; possible causes include empty evidence_refs, a stale If-Match version_stamp, a wrong-scope cleanup_adjudication_token on an alternative bq_update path, or a soft-freeze active state masking the failure.
    expected_answers:
      - kind: human_action
        verb: investigate
        object: completion 422 cause
        target: evidence payload, If-Match version_stamp, override-token scope, and soft-freeze state
    weight: 0.08333333333333333
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S577
last_refresh_commit: 3e836bb
last_refresh_date: 2026-05-07T12:00:00Z
owner_agent: max
refresh_triggers:
  - bq_completion
  - gate_approval
  - incident
  - chunk_3_enforcement_flip
  - token_lifecycle_change
  - soft_freeze_state_change
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-05-07T12:00:00Z
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S577 / 2026-05-07T12:00:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
