---
system_name: publish-paths
purpose_sentence: This runbook defines the canonical marketplace listing publication path, its seller-capability rules, and its safe retraction behavior.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Signed VZ listing creation and update, programmatic publication, website listing management, seller capability enforcement, and unpublish behavior.
linter_version: 1.0.0
---

# Publish Paths Runbook

How a dataset becomes a marketplace listing. There is exactly one product publish route; everything else is management or a separately gated programmatic surface.

## §A. Header

The YAML frontmatter defines the current conformance header. This document remains a grandfathered discovery runbook; the header does not promote it to action authority.

- **Source of truth:** `POST /api/v1/vz/publish`, `vz_publish_service.create_or_update_listing`, the seller capability service, and the deployed behavior verified by the current ticket.
- **Listings store:** the PostgreSQL `listings` table. Products do not own separate marketplace listing stores.
- **Related seller readiness:** `account-capability-onboarding.md`.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Signed VZ listing create | SHIPPED | `app/routers/vz_publish.py` | VZ publish route and protected seller-provisioning gate | 2026-08-23 |
| Active-seller listing update | SHIPPED | `app/services/vz_publish_service.py` | VZ publish and seller setup gate suites | 2026-08-23 |
| Provisioning seller fresh-create exception | SHIPPED | `app/services/vz_publish_service.py` | Exact-shape, unchanged-existing-listing, and PostgreSQL concurrency tests | 2026-08-23 |
| Programmatic listing actions | SHIPPED | `app/services/action_executor_service.py` | ActionExecutor active-seller chokepoint tests | 2026-08-23 |
| Website listing management | SHIPPED | `app/routers/listings.py` | Ownership and unpublish coverage | 2026-08-23 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Canonical product publish route | `POST /api/v1/vz/publish` | VZ installs, users, capabilities, listings, Redis replay state | AIM Data and vectorAIz | Ed25519 signed and fail-closed for trust, replay, identity, and seller capability. |
| Canonical listing writer | `vz_publish_service.create_or_update_listing` | PostgreSQL listings and publish-effect records | Notification, version, translation, and search hooks | Creates or updates for active sellers; serializes and limits provisioning sellers to one fresh seller/source create. |
| Programmatic action chokepoint | `ActionExecutorService` | Canonical listing state | REST actions, MCP tools, and Trust Channel | Remains active-seller only; it has no provisioning exception. |
| Website management | `app/routers/listings.py` | Canonical listing state | Marketplace dashboard | Reads, previews, unpublishes, or deletes owned listings; it does not create or publish. |

Both AIM Data and vectorAIz publish through `POST /api/v1/vz/publish`. The route always runs the active-seller check first. A signed VZ request denied only because its seller is explicitly `provisioning` with reason `readiness_gap` may create one fresh `(seller_id, vz_raw_listing_id)` listing. A transaction-scoped advisory lock serializes concurrent attempts. If that listing already exists, the original 403 is returned before mutation or publish side effects. Purchase, payout, settlement, update, republish, and every other active-seller control remain blocked until the seller is active.

When a listing is backed by a customer S3 connection, `_validate_s3_connection_publish_authority` additionally binds the signed `(seller_id, install_id)` to an active, unrevoked `vz_installs` row and its activated serial. A missing serial linkage fails closed. The serial owner is checked against the seller; legacy nullable ownership is observable and is not a substitute for the signed install binding.

Unpublish is retraction-only: it delists and de-indexes. It must not fire translation, search-submission, or other publish-effect hooks.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| AIM Data or vectorAIz install | Create or update through the canonical route | Signed VZ publish client | Install Ed25519 identity and seller session | COMPLETE |
| Programmatic marketplace client | Execute listing actions | ActionExecutorService chokepoint | Existing action or MCP authorization plus active seller | COMPLETE |
| Website seller | Manage an owned existing listing | Marketplace dashboard listing controls | Authenticated seller ownership | COMPLETE |
| Authorized operator | Retract an exact synthetic verification listing | Existing listing unpublish service | Approved secret-backed operator mechanism | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: A customer product publishes a newly reviewed dataset to the marketplace.
  pre_conditions: [signed_vz_install, authenticated_seller, redis_available, reviewed_metadata]
  tool_or_endpoint: POST /api/v1/vz/publish
  argument_sourcing: {seller_id: derive from the signed token subject, install_id: derive from the signed token issuer, source_id: derive from vz_raw_listing_id, metadata: derive from the reviewed customer listing form}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: seller_id plus vz_raw_listing_id
  expected_success: {shape: HTTP 201 with listing_id and marketplace_url, verification: open the exact listing through the isolated customer browser and compare the seller and source identity}
  expected_failures: [{signature: capability_required, cause: the seller is not active and the request is not the exact permitted provisioning fresh-create case}, {signature: security_services_offline, cause: Redis replay or rate-limit enforcement is unavailable}, {signature: install_authority_denied, cause: token, install, serial, seller, or source authority does not match}]
  next_step_success: If onboarding is required, complete 2FA and Stripe setup before purchase, payout, update, or republish.
  next_step_failure: Use §F and do not bypass signing, replay, install, capability, or browser identity controls.
- id: E-02
  trigger: An active seller manages an existing listing from the marketplace website.
  pre_conditions: [seller_authenticated, listing_owned_by_seller]
  tool_or_endpoint: GET preview, POST unpublish, or DELETE through app/routers/listings.py
  argument_sourcing: {listing_id: derive from the seller-owned listing selected in the dashboard}
  idempotency: IDEMPOTENT
  expected_success: {shape: owned listing is read or retracted as requested, verification: confirm ownership enforcement and public listing state after the operation}
  expected_failures: [{signature: listing_not_found, cause: the listing is absent or not owned by the current seller}, {signature: active_seller_required, cause: the selected management operation requires active seller status}]
  next_step_success: Confirm the resulting public and dashboard state.
  next_step_failure: Stop and verify identity, ownership, and capability state before retrying.
- id: E-03
  trigger: An authorized operator retracts a synthetic listing created for live verification.
  pre_conditions: [exact_synthetic_listing_recorded, approved_operator_path_available]
  tool_or_endpoint: Existing listing unpublish service
  argument_sourcing: {listing_id: use the exact id returned by E-01, seller_id: verify against the recorded synthetic account}
  idempotency: IDEMPOTENT
  expected_success: {shape: status is unpublished and the listing is absent from public discovery, verification: confirm the exact identity through operator state and the isolated customer browser}
  expected_failures: [{signature: listing_identity_mismatch, cause: the target cannot be proven to be the recorded synthetic listing}, {signature: deindex_pending, cause: retraction succeeded but public discovery has not converged}]
  next_step_success: Retain create and retraction evidence with the ticket.
  next_step_failure: Fail closed without deletion or access-control bypass and preserve a recoverable identity record.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | A provisioning seller cannot create a fresh listing. | The denial is not the exact readiness gap, the seller/source already exists, Redis is unavailable, S3 authority failed, or production is stale. | Compare the typed response, seller capability, seller/source existence, replay health, install authority, and deployed SHA without retrieving secret values. | G-01 | CONFIRMED |
| F-02 | A provisioning seller updates, republishes, or creates the same seller/source twice. | The exact route matcher, advisory lock, or existing-listing denial was bypassed. | Exercise concurrent fresh creates and a real-service existing-listing request; require one create, one original 403, one row, and no existing-listing mutation or side effects. | G-02 | CONFIRMED |
| F-03 | A non-VZ programmatic path publishes for a non-active seller. | A new path bypasses the ActionExecutorService chokepoint or weakens its active-seller check. | Trace the request to its canonical writer and confirm the chokepoint runs before any published-state write. | G-03 | CONFIRMED |
| F-04 | Unpublish fires publish effects or leaves the listing publicly discoverable. | The retraction path calls publish hooks, de-indexing failed, or the wrong listing identity was targeted. | Verify the exact listing id and owner, inspect hook behavior, and compare canonical status with public and isolated-browser state. | G-04 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Canonical product publish route
  root_cause: A signed-publish prerequisite failed or production does not contain the reviewed exact fresh-create exception.
  repair_entry_point: app/routers/vz_publish.py and the exact deployment receipt
  change_pattern: Restore only the exact provisioning readiness_gap fresh-create path while retaining all trust, replay, install, seller/source, and capability checks.
  rollback_procedure: Revert through the protected workflow so provisioning publication returns to active-only behavior.
  integrity_check: Focused route, service, concurrency, protected-gate, deployment, and isolated-customer proofs pass.
- id: G-02
  symptom_ref: F-02
  component_ref: Canonical listing writer
  root_cause: Provisioning requests are not serialized or the existing seller/source check occurs after mutation or side effects.
  repair_entry_point: app/services/vz_publish_service.py create_or_update_listing
  change_pattern: Reinstate the transaction-scoped seller/source advisory lock and return the original denial immediately when the listing exists.
  rollback_procedure: Disable the provisioning exception through the protected workflow until the create-only invariant is restored.
  integrity_check: Two concurrent calls produce one row and one 403; an existing listing and all publish-effect mocks remain unchanged.
- id: G-03
  symptom_ref: F-03
  component_ref: Programmatic action chokepoint
  root_cause: A programmatic writer bypasses ActionExecutorService or its active-seller check.
  repair_entry_point: ActionExecutorService routing and the offending caller
  change_pattern: Route the caller through the existing active-seller chokepoint; do not copy the VZ-only provisioning exception.
  rollback_procedure: Disable or revert the new programmatic path until it uses the canonical chokepoint.
  integrity_check: Every programmatic publish-effect request for a non-active seller is denied before state change.
- id: G-04
  symptom_ref: F-04
  component_ref: Website management
  root_cause: Retraction invoked publish hooks, failed de-indexing, or targeted an unverified identity.
  repair_entry_point: app/routers/listings.py and the existing unpublish service
  change_pattern: Keep unpublish retraction-only and repeat only the approved reversible operation for an exactly verified listing identity.
  rollback_procedure: If identity or authorization cannot be proven, stop without mutation and preserve the recovery record.
  integrity_check: Canonical status is unpublished, publish hooks did not fire, and public discovery no longer returns the exact listing.
```

## §H. Evolve

### §H.1 Invariants

There is one signed product publish route. The provisioning exception is exact-denial, signed-VZ, fresh-create, and seller/source scoped. It grants no purchase, payout, settlement, update, republish, or programmatic authority. Website unpublish is retraction-only.

### §H.2 BREAKING predicates

Adding a product writer outside the canonical VZ route, removing trust or replay checks, widening the provisioning exception, bypassing the programmatic chokepoint, or firing publish hooks on unpublish is BREAKING.

### §H.3 REVIEW predicates

Review changes to VZ claims, install or serial binding, seller readiness semantics, seller/source identity, lock scope, status transitions, publish hooks, or website management authorization.

### §H.4 SAFE predicates

Examples and explanatory copy are safe when they do not change route identity, authorization, capability gates, state transitions, or publish and retraction side effects.

### §H.5 Boundary definitions

#### module

The VZ router owns request trust and seller-gate interpretation. The VZ publish service owns canonical listing writes and publish effects. ActionExecutorService owns programmatic gating. The listings router owns website management.

#### public contract

Products create listings through signed `POST /api/v1/vz/publish`; website customers manage owned listings through the existing listings endpoints.

#### runtime dependency

The route depends on PostgreSQL user, capability, install, serial, and listing state; Redis replay and rate limiting; and the deployed backend identity.

#### config default

No flag widens the provisioning exception. Missing trust, replay, install, durable readiness, ownership, or identity state fails closed.

### §H.6 Adjudication

Any new writer or broader seller exception requires separate frozen scope, security review, focused tests, protected merge, deployment proof, and customer verification.

## §I. Operational Examples

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: A signed VZ request from an explicitly provisioning seller targets a seller/source pair that does not exist.
    expected_answers:
      - kind: classification
        label: allow one guarded fresh create and retain every post-publish active-seller block
  - id: I-02
    type: isolate
    refs: [F-02, G-02]
    scenario: Two concurrent provisioning requests target the same fresh seller/source pair.
    expected_answers:
      - kind: classification
        label: serialize the requests so exactly one creates and the other receives the original readiness_gap denial
  - id: I-03
    type: operate
    refs: [E-03, G-04]
    scenario: Live verification created a synthetic listing that must be safely taken down.
    expected_answers:
      - kind: classification
        label: use the existing reversible unpublish path for the exact recorded identity and verify public absence
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1599
last_refresh_commit: deffba2d84de40d7bc3369e5dd31ef3cf7f1eedd
last_refresh_date: 2026-08-23T17:00:00Z
owner_agent: vulcan
refresh_triggers:
  - A product publish route, seller capability rule, seller/source identity, publish effect, or unpublish contract changes.
scheduled_cadence: 3m
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
retrofit: false
trace_matrix_path: null
word_count_delta: null
```

## Related

- `account-capability-onboarding.md` for seller readiness mechanics.
- `aim-data.md` for the customer-installed product journey.
- `config:publish-paths-consolidation-tracker` for historical consolidation state.
