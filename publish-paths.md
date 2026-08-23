# Publish Paths Runbook

How a dataset becomes a marketplace listing. There is exactly one publish route; everything else is management or has been removed.

## §A. Header

- **Owns:** the single canonical publish path and the rules that keep it single.
- **Status:** current as of the wizard removal (S1077). Website publish wizards deleted; their five tables dropped in production.
- **Source of truth:** `config:publish-paths-consolidation-tracker` (program state); this runbook (operating model); `account-capability-onboarding.md` (the active-seller gate). When reality and this runbook disagree, fix the runbook in the same change.

### M1 — Dependencies & Credentials / Source-of-Truth
- **Canonical endpoint:** `POST /api/v1/vz/publish` → `vz_publish_service.create_or_update_listing` (ai-market-backend). Ed25519 trust-token signed; enforces the active-seller capability gate, with the create-only provisioning exception described below.
- **Listings store:** the `listings` table (Postgres). Same table for every product; no per-product listing store.
- **Gate dependency:** `assert_user_capability(user, db, 'seller', 'active')` — see `account-capability-onboarding.md`.

## §B. Capability Matrix

| Actor | Can create/publish a listing? | How |
|-------|------|-----|
| AIM Data (customer install) | Yes | Signs an EdDSA JWT and proxies to `POST /api/v1/vz/publish` |
| vectorAIz | Yes | Calls `POST /api/v1/vz/publish` directly |
| Agent / programmatic (REST `/actions/execute`, `/mcp tools/call`, Trust Channel) | Yes, gated | Reaches `aim.listing.*` only through the ActionExecutorService chokepoint, which enforces the same active-seller gate |
| The website (ai.market dashboard) | No | Manage only: see-my-listings, preview, unpublish, delete |

## §C. Architecture & Interactions

One write path, one gate. Both customer products (AIM Data, vectorAIz) publish through `POST /api/v1/vz/publish`, which is the only place a new listing is created or a listing is set to published, and it always runs the active-seller check first. A signed VZ request denied only because its seller is explicitly `provisioning` with reason `readiness_gap` may create one fresh `(seller_id, vz_raw_listing_id)` listing; a transaction-scoped advisory lock serializes concurrent attempts. If that listing already exists, the original 403 is returned before mutation or publish side effects. Purchase, payout, settlement, update, republish, and every other active-seller control remain blocked until the seller is active. The agent/programmatic surfaces do not have their own publish code; they pass through the ActionExecutorService chokepoint, which carries the same gate and has no provisioning exception. The website never creates or publishes — it reads and manages listings that already exist on the canonical `listings` table through `listings.py` (`GET /listings/mine`, `GET /listings/{id}/preview`, `POST /listings/{id}/unpublish`, `DELETE /listings/{id}`). Unpublish is a retraction: it delists and de-indexes, and does not fire publish-effect hooks (no translation outbox, no search submission).

**S3-connection publish authority (serial ownership chain).** When the listing is backed by a customer S3 connection, the gate additionally runs `app/services/vz_publish_service.py::_validate_s3_connection_publish_authority` (origin/main line ~598). Authorization anchors, in order: the Ed25519-signed publish JWT resolves `(seller_id, install_id)`; the `vz_installs` row must match both ids, be active, and not revoked; `install.serial_id` must be non-NULL, else 403 "install serial linkage required" — FAIL-CLOSED, metric `vz_publish_publish_rejected_unbound_install_total`; the serial must be activated and unexpired; `serials.user_id` is checked last — a non-NULL mismatch is a 409, and NULL is tolerated only as a legacy branch that fires `vz_publish_serial_user_id_stale_total`. The binding is created at registration: `register_install` atomically binds serial→install (partial unique index `ux_vz_installs_serial_id_bound`) and sets `serials.user_id = seller_id` in the same guarded UPDATE (commit a878c7b8, migration `bq_vz_serial_link_s1133`). Prod verified 2026-07-10 (T-2026-000182, S1169): zero serial-linked installs with NULL `serials.user_id`; never-registered activated serials are unreachable on the publish path. If the stale metric ever fires, that legacy branch is the suspect — it is dead code in prod today and a candidate to tighten to fail-closed.

## §D. Agent Capability Map
- **allAI** generates and classifies the listing metadata that is sent to the canonical endpoint. It does not itself publish.
- **No agent has a private publish path.** Any agent publish flows through the gated chokepoint above.

## §E. Operate — Serving Customers
- **E-01 — A customer publishes via AIM Data:** the install signs a token and proxies to `POST /api/v1/vz/publish`. An active seller may create or update. An explicitly provisioning seller may create only a fresh seller/source listing under the exact `readiness_gap` exception; an existing listing or any other denial remains blocked.
- **E-02 — A customer publishes via vectorAIz:** same endpoint, called directly.
- **E-03 — A seller manages an existing listing on the website:** preview, unpublish, or delete through `listings.py`. Ownership is enforced (a non-owner gets a 404).
- **E-04 — A seller wants to publish from the website:** there is no such action by design. Direct them to AIM Data or vectorAIz.

## §F. Isolate — Diagnosing Deviations
- **A listing was published without an active seller:** first determine whether it is the one permitted fresh signed-VZ create for an explicitly provisioning seller with the exact `readiness_gap` denial. Any update, repeat create for the same seller/source, other denial shape, or non-VZ path that succeeds is a gate bypass. The guarded exception lives across `vz_publish.publish_listing` and `vz_publish_service.create_or_update_listing`; the ActionExecutorService chokepoint remains active-only.
- **A new "publish" route appears:** it must route through the canonical endpoint or the gated chokepoint. A standalone publish route is a regression of this consolidation.
- **Unpublish triggered translation/search side-effects:** unpublish must be retraction-only; a publish-effect hook firing on unpublish is a defect.

## §G. Repair — Fixing Problems
- **G-01 — Close an ungated publish path:** route it through `vz_publish_service.create_or_update_listing`, or gate it with `assert_user_capability(..., 'seller', 'active')` at the chokepoint. Never add a second ungated writer.
- **G-02 — Roll back the wizard removal (if ever needed):** the drop migration `s1077_drop_publish_wizard_tables` has a downgrade that recreates the five tables (empty). Reversal is schema-level only; it does not restore data (there was none — pre-launch).

## §H. Evolve — Extending the System

### §H.1 Invariants
- One publish route. New products publish through `POST /api/v1/vz/publish`, never a new endpoint.
- One gate. Every publish-effect path enforces the active-seller capability check; only the canonical signed-VZ route may make the exact create-only provisioning exception above.
- The website never creates or publishes.
- Unpublish is retraction-only.

### Change-class examples
- **Add a new data product that lists to the marketplace:** point it at `POST /api/v1/vz/publish`. No new publish code.
- **Add an agent publish capability:** add it under `aim.listing.*` so it inherits the chokepoint gate by construction.

## §I. Acceptance Criteria (scenario set)
- A non-active seller is rejected on every publish path except that an explicitly provisioning seller with the exact signed-VZ `readiness_gap` denial may create one fresh seller/source listing.
- A provisioning seller cannot update or republish that listing, cannot create it twice under concurrency, and gains no purchase, payout, or settlement authority from the exception.
- The website exposes no create/publish action; manage actions enforce ownership.
- No live code outside the canonical writer / gated chokepoint sets a listing to published.
- Unpublish does not fire publish-effect hooks.

## §J. Lifecycle
- **Removed (S1077):** the two website publish wizards (`seller_wizard`, `publish_wizard`) — endpoints, services, model, schema, and their five tables (`publish_operations`, `publish_audit_log`, `hitl_tokens`, `pii_findings`, `replay_nonces`). Verified absent in production; alembic head `s1077_drop_publish_wizard_tables`.
- **Transient cutover note:** during consolidation an older `POST /api/v1/listings/` push and the website wizards coexisted with the canonical path. The website wizards are now gone. Two legacy server surfaces remain and are retired by separate, already-planned phases: `publish.py POST /listings/publish` (BQ-D2 safe-delete) and `listings.py POST /listings/` (active-seller gated today, retired as a product publish route by the AIM Data migration).

## §K. Conformance
- The single-path and single-gate invariants are enforced by tests in ai-market-backend (`test_publish_paths_phase3_rehome.py` and the vz/publish + chokepoint gate suites). Adding a publish-effect path without the gate should fail review.

## §L. Topic router & self-containment
Registered in `TOPIC-ROUTER.md`. For the gate mechanics and seller readiness, see `account-capability-onboarding.md`. For program state and history, see `config:publish-paths-consolidation-tracker`.
