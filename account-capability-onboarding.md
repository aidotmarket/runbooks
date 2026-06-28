# Account Capability & Onboarding Runbook

> Covers the capability model that gates buying and selling on ai.market: how a user becomes a seller, what "provisioning" vs "active" means, the readiness signals that move a seller to active, the `require_capability` guard, and the 403 `CapabilityRequiredError` contract. Backing code verified against `aidotmarket/ai-market-backend` @ `2f20ea3f87dd7c8afe09a2aed46a48b77dd969c3` (deployed main, S1049 Gate-4).

---

## §A. Header

- **system_name:** Account Capability & Onboarding (ai.market backend)
- **purpose_sentence:** Authorize who can buy and who can sell on ai.market by resolving per-user buyer/seller capabilities from persisted status plus live readiness signals, and gate seller endpoints accordingly.
- **owner_agent:** Vulcan / Mars (ai.market backend peers)
- **escalation_contact:** Max
- **lifecycle_ref:** see §J (authoritative for refresh tracking)
- **authoritative_scope:** This runbook is the source of truth for the capability model (buyer default-on, seller additive), the provisioning→active readiness rules, the `require_capability` / `assert_user_capability` guard, and the 403 `CapabilityRequiredError` body. It is NOT the source of truth for sign-up/login (see `auth-signup-flow.md`), 2FA setup (see `two-factor-auth.md`), or Stripe Connect onboarding mechanics (see `infisical-secrets.md` for Stripe keys).
- **linter_version:** 1.0.0

### M1 — Dependencies & Credentials / Source-of-Truth

| Dependency | What it provides | Where the credential lives | Owning service |
|---|---|---|---|
| ai.market Postgres | `user_capabilities` table (persisted status) + `users.stripe_payouts_enabled` durable column (the authoritative payouts-live signal) | `DATABASE_URL` — Infisical `ai-market-backend`/prod, set in Railway env | ai.market backend |
| Stripe Connect | Payouts eligibility that drives the `stripe_payouts_live` readiness step | `STRIPE_*` keys — Infisical `ai-market-backend`/prod (see `infisical-secrets.md`) | Payments |
| 2FA / TOTP | `totp_enabled` readiness step | 2FA/TOTP encryption key in backend env (see `two-factor-auth.md`) | Auth |

There is no separate cache credential. The Redis readiness cache was removed (S1049); the durable Postgres column is the only source of truth for `stripe_payouts_live` in both the async and sync read paths.

---

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Buyer capability default-on (every active user can buy) | SHIPPED | `app/services/capability_resolver.py:CapabilityResolver._resolve_capability` (buyer branch returns active) | Resolver unit tests, S1044 slice-1 regression set (35 green) | S1049 |
| Seller capability additive + gated (not_requested → provisioning → active) | SHIPPED | `app/models/capability.py:CapabilityName,CapabilityStatus,UserCapability`; `app/schemas/capability.py:CapabilityStatusValue` | Resolver unit tests, S1044 slice-1 | S1049 |
| Seller readiness computation (4 steps) | SHIPPED | `app/services/capability_resolver.py:compute_seller_missing_steps` | Unit tests on the pure helper, S1044 slice-1 | S1049 |
| Effective-status derivation (persisted + missing steps) | SHIPPED | `app/services/capability_resolver.py:compute_effective_seller_status` | Unit tests on the pure helper, S1044 slice-1 | S1049 |
| `require_capability` / `assert_user_capability` guard | SHIPPED | `app/api/deps.py:require_capability`, `app/api/deps.py:assert_user_capability` | Endpoint guard tests, S1044 slice-1 (incl. Gate-3 docstring-guard regression) | S1049 |
| 403 `CapabilityRequiredError` body contract | SHIPPED | `app/schemas/capability.py:CapabilityRequiredError`; raised in `app/api/deps.py:assert_user_capability` | Endpoint guard tests, S1044 slice-1 | S1049 |
| Durable payouts-live signal (single source, sync + async parity) | SHIPPED | `app/services/capability_resolver.py:_read_durable_stripe_signal`; sync mirror `app/api/v1/endpoints/stripe.py:_require_seller_capability_sync` | Resolver unit tests; sync/async parity (M4, S1049) | S1049 |
| Redis readiness cache | DEPRECATED | removed S1049; durable `users.stripe_payouts_enabled` is authoritative | n/a (removed) | S1049 |
| `user_capabilities` table + status enums migration | SHIPPED | Alembic head `20260627_001` (prod `alembic_version`) | Gate-4 prod verification, S1049 | S1049 |

---

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| CapabilityModel | `app/models/capability.py:UserCapability` | `user_capabilities` table (user_id, capability, status); enums `CapabilityName`, `CapabilityStatus` | `app/schemas/capability.py` (API shapes) | Persisted seller status lives here. Absence of a seller row is projected from `users.role` (`seller`→active, else not_requested). |
| CapabilityResolver | `app/services/capability_resolver.py:CapabilityResolver.resolve` | reads `user_capabilities` + `users` columns | guard (`deps.py`), seller/listings endpoints | Returns `CapabilitySetResponse(buyer, seller)`. Buyer always active. Seller effective status = persisted + missing steps. |
| ReadinessSignals | `app/services/capability_resolver.py:compute_seller_missing_steps` | reads `users.display_name`/`first_name`/`last_name`/`company_name`/`totp_enabled`/`stripe_payouts_enabled` | CapabilityResolver | Four steps: `profile_name`, `company_name`, `totp_enabled`, `stripe_payouts_live`. Any present step is dropped from `missing_steps`. |
| StripeDurableSync | `app/services/capability_resolver.py:_read_durable_stripe_signal` | reads durable `users.stripe_payouts_enabled` (string `"true"`) | Stripe Connect / Stripe sync endpoints that WRITE the column | Read failure or `None` → `StripeReadiness(live=False, unavailable=True)`, logged `severity=high`, reason `durable_signal_unavailable`. |
| CapabilityGuard | `app/api/deps.py:require_capability` | none (delegates to resolver) | every guarded seller endpoint | FastAPI dependency factory. `require_capability(name, required_status=active)` → `assert_user_capability`. Depends on `get_user_or_internal_key`. On fail raises 403 with `CapabilityRequiredError`. |

Data flow: a guarded request resolves the caller's `User`, `CapabilityResolver.resolve` reads the persisted seller row (or projects from role), computes `missing_steps` from the four readiness signals, derives effective status, and the guard compares effective status against the endpoint's `required_status`. A `provisioning` requirement is also satisfied by `active` (active is strictly stronger).

The capability guard sits ALONGSIDE older, narrower guards that still exist: role-based `get_current_seller` (`deps.py`), Stripe-KYC `get_kyc_verified_seller` (`deps.py`), and the `_enforce_onboarding` flag check (`onboarding_completed` → 403 with `onboarding_url`). The capability guard is the authoritative gate for buyer/seller marketplace actions; the others are legacy or orthogonal (KYC, first-run onboarding).

---

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Operator / support (human) | Read a user's resolved capabilities | `CapabilityResolver.resolve(user_id)` via backend shell or the capabilities API | Internal key or admin JWT | COMPLETE |
| allAI / internal service | Call a guarded endpoint on behalf of a service flow | `get_user_or_internal_key` (X-Internal-API-Key) → synthetic admin user | Internal key | PARTIAL — internal-key caller resolves as role `admin`, so seller readiness is `not_requested`; use a real user JWT when seller readiness matters. Notes: do not rely on the internal key to satisfy a seller `active` gate. |
| Vulcan / Mars | Inspect prod readiness signals | Railway-derived `DATABASE_PUBLIC_URL` read of `users.stripe_payouts_enabled` + `user_capabilities` | Prod DB read (account token) | COMPLETE |

---

## §E. Operate — Serving Customers

### E-01 — New user wants to buy
- **id:** E-01
- **trigger:** A freshly registered, active user attempts a buyer action.
- **pre_conditions:** `user_authenticated`, `user.status == active`.
- **tool_or_endpoint:** any buyer endpoint guarded by `require_capability(CapabilityName.buyer)` (default active).
- **argument_sourcing:** `user`: resolved by `get_user_or_internal_key` from the Bearer token.
- **idempotency:** IDEMPOTENT (read of capability state).
- **expected_success:** buyer effective status is `active`; request proceeds.
- **expected_failures:** 401 if not authenticated (not a capability failure).
- **next_step_success:** serve the buyer action.
- **next_step_failure:** if 401, re-authenticate; capability is never the blocker for buying.

### E-02 — User checks seller readiness
- **id:** E-02
- **trigger:** A user wants to know what they need to do to sell.
- **pre_conditions:** `user_authenticated`.
- **tool_or_endpoint:** `CapabilityResolver.resolve(user_id)` (exposed through the capabilities API surface).
- **argument_sourcing:** `user_id`: the authenticated user's id from the JWT `sub`.
- **idempotency:** IDEMPOTENT.
- **expected_success:** returns `seller` readiness with `effective_status=provisioning` (or `not_requested`) and a `missing_steps` list drawn from `profile_name`, `company_name`, `totp_enabled`, `stripe_payouts_live`.
- **expected_failures:** none beyond auth; an unreadable durable column yields `reason=durable_signal_unavailable` (see §F-03).
- **next_step_success:** surface the missing steps to the customer in plain language (see Customer-facing copy below).
- **next_step_failure:** if `durable_signal_unavailable`, follow §G-02.

### E-03 — Seller completes Stripe payouts and goes active
- **id:** E-03
- **trigger:** Seller finishes Stripe Connect; payouts become live.
- **pre_conditions:** profile name set, company name set, 2FA on, Stripe payouts eligible.
- **tool_or_endpoint:** the Stripe sync / Connect endpoint that writes `users.stripe_payouts_enabled = "true"`, then `require_capability(CapabilityName.seller, CapabilityStatus.active)` on a seller action.
- **argument_sourcing:** durable signal: written by the Stripe sync path; read by `_read_durable_stripe_signal`.
- **idempotency:** IDEMPOTENT_WITH_KEY (durable write keyed by `user_id`; re-running is safe).
- **expected_success:** `missing_steps` empties, effective seller status flips to `active`, seller actions (create listing, etc.) succeed.
- **expected_failures:** if the durable write did not land, status stays `provisioning` with `missing_steps=[stripe_payouts_live]` (see §F-02).
- **next_step_success:** seller can list/sell.
- **next_step_failure:** §G-01 to resync the durable signal.

### E-04 — Operator resolves a specific user's capabilities
- **id:** E-04
- **trigger:** Support needs to know why a seller is blocked.
- **pre_conditions:** operator has internal key or admin JWT.
- **tool_or_endpoint:** `CapabilityResolver.resolve(user_id)`.
- **argument_sourcing:** `user_id`: from the support ticket / CRM.
- **idempotency:** IDEMPOTENT.
- **expected_success:** returns persisted status, effective status, missing steps, and reason.
- **expected_failures:** `LookupError` if the user id does not exist.
- **next_step_success:** map `missing_steps`/`reason` to §F.
- **next_step_failure:** confirm the user id.

### Customer-facing copy (seller readiness, Max voice)
- `profile_name`: "Add your name so buyers know who they are dealing with."
- `company_name`: "Add your company name. Buyers want to know who is behind the data."
- `totp_enabled`: "Turn on two-factor login. We need this on before you can sell."
- `stripe_payouts_live`: "Connect Stripe so we can pay you. Once payouts are live you can start selling."
- active / all-clear: "You are all set to sell. Go ahead and list your data."

---

## §F. Isolate — Diagnosing Deviations

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Seller gets 403 on a state-changing seller action; body shows `missing_steps` | Seller is genuinely still provisioning (a readiness step is incomplete) | Read the 403 `CapabilityRequiredError` body; `effective_status=provisioning` and `missing_steps` names the incomplete step(s) | | CONFIRMED |
| F-02 | `missing_steps=[stripe_payouts_live]` though the seller finished Stripe onboarding | Durable `users.stripe_payouts_enabled` not written/synced after payouts went live | Read `users.stripe_payouts_enabled` for the user; if not `"true"`, the durable write lagged | §G-01 | CONFIRMED |
| F-03 | `reason=durable_signal_unavailable` on seller readiness | The durable column read raised or returned `None`; resolver returns `live=False, unavailable=True` | Check backend logs for `capability_readiness_durable_signal_unavailable ... severity=high`; inspect the column value/type | §G-02 | CONFIRMED |
| F-04 | A seller passes the async resolve but fails the sync Stripe-path gate (or vice versa) | Sync and async readiness derivations drifted apart | Confirm `stripe.py:_require_seller_capability_sync` calls the shared `compute_*` helpers | §G-03 | HYPOTHESIZED |
| F-05 | 403 on a provisioning-level read endpoint (e.g., discovery readiness) | User never requested seller; persisted status `not_requested` | Resolve the user; `persisted_status=not_requested` | | CONFIRMED |

---

## §G. Repair — Fixing Problems

### G-01 — Resync the durable payouts signal
- **id:** G-01
- **symptom_ref:** F-02
- **component_ref:** StripeDurableSync
- **root_cause:** `users.stripe_payouts_enabled` was not updated to `"true"` after the seller's payouts became eligible, so the resolver still counts `stripe_payouts_live` as missing.
- **repair_entry_point:** `app/api/v1/endpoints/stripe.py` (the Stripe sync / Connect-status endpoints that write the durable column) and the Stripe webhook path that mirrors payouts state onto the user.
- **change_pattern:** Re-run the durable write for the affected user so the column reflects live payouts; confirm the write path fires on the payouts-eligible Stripe event.
- **rollback_procedure:** The durable column is the source of truth; revert by setting it back to its prior value. No cache to invalidate (cache removed S1049).
- **integrity_check:** Re-resolve the user; `missing_steps` no longer contains `stripe_payouts_live` and effective seller status is `active`.

### G-02 — Restore the durable readiness signal
- **id:** G-02
- **symptom_ref:** F-03
- **component_ref:** ReadinessSignals
- **root_cause:** The durable `users.stripe_payouts_enabled` column is unreadable (attribute/read error) or `None`, so `_read_durable_stripe_signal` reports `unavailable=True`.
- **repair_entry_point:** `app/services/capability_resolver.py:_read_durable_stripe_signal` and the `users` model column definition / backfill migration.
- **change_pattern:** Ensure the column exists and is populated (`"true"`/`"false"`) for affected users; backfill if a migration left it null.
- **rollback_procedure:** Backfill writes are value updates on the column; revert by restoring prior values from backup if needed.
- **integrity_check:** Resolve the user; `reason` is no longer `durable_signal_unavailable`; the high-severity log line stops firing.

### G-03 — Keep sync and async readiness in lockstep
- **id:** G-03
- **symptom_ref:** F-04
- **component_ref:** CapabilityResolver
- **root_cause:** The sync seller gate and the async resolver derive readiness independently and have diverged.
- **repair_entry_point:** `app/services/capability_resolver.py:compute_seller_missing_steps` + `compute_effective_seller_status` (the shared helpers), consumed by both `CapabilityResolver` and `app/api/v1/endpoints/stripe.py:_require_seller_capability_sync`.
- **change_pattern:** Route both paths through the shared `compute_*` helpers so precedence cannot drift (the M4 design from S1049); do not reintroduce a parallel readiness derivation.
- **rollback_procedure:** Revert to the prior commit; both paths already shipped on `2f20ea3f` calling the shared helpers.
- **integrity_check:** A user who is `active` under the async resolver is also `active` under the sync gate, and vice versa, across all four readiness steps.

---

## §H. Evolve — Extending the System

### §H.1 Invariants
- **Buyer is default-on.** Every active user can buy; the buyer branch must not be gated behind readiness steps.
- **Seller is additive and gated.** A seller endpoint that requires `active` must never be served to a user whose effective seller status is below the required status.
- **One source of truth for payouts-live.** `users.stripe_payouts_enabled` is the sole authority for `stripe_payouts_live` in BOTH the sync and async paths. No cache may become the source of truth; the two paths must share the `compute_*` helpers.
- **403 body is a public contract.** The `CapabilityRequiredError` field set (`capability`, `persisted_status`, `effective_status`, `missing_steps`, `reason`) is consumed by the frontend; changing it is BREAKING.
- **Non-custodial.** Capability state is metadata only; no customer data flows through this layer.
- **module** = immediate subdir of `app/` (e.g. `app/api/`, `app/services/`, `app/models/`, `app/schemas/`). **public contract** includes the served API schemas (incl. `CapabilityRequiredError`). **config default** = values in the canonical backend config. **runtime dependency** = `pyproject.toml [project.dependencies]`.

### Change-class examples
- *Add a fifth required readiness step (e.g., a verified bank account):* **BREAKING** — it adds a required gate that can newly fail existing `active` sellers and changes the `missing_steps` value set (an authz-boundary + public-contract change).
- *Change a read endpoint from `provisioning` to `active`:* **BREAKING** — changes scope semantics for existing callers (provisioning sellers lose access they had).
- *Add a new seller-only feature endpoint guarded by `require_capability(seller, active)`:* **REVIEW** — a new feature on an existing public surface, no contract change.
- *Reword a `missing_steps` customer-facing copy string:* **SAFE** — copy change within existing semantics (the step key is unchanged).

---

## §I. Acceptance Criteria (scenario set)

**Weighting:** equal-weight default (1/N, N = 11). No unequal weights declared.

1. (E) New active user with no seller row attempts to buy. Expected first action: confirm buyer effective status is `active` and serve the request. [E-01]
2. (E) User asks "what do I need to do to sell?" Expected first action: call `CapabilityResolver.resolve(user_id)` and return `missing_steps`. [E-02]
3. (E) Seller just finished Stripe; verify they can now list. Expected first action: read `users.stripe_payouts_enabled` and re-resolve; confirm `active`. [E-03]
4. (F) Seller reports 403 creating a listing. Expected first action: read the 403 `CapabilityRequiredError` body and inspect `missing_steps`. [F-01]
5. (F) `missing_steps=[stripe_payouts_live]` though Stripe is done. Expected first action: read `users.stripe_payouts_enabled` for the user. [F-02]
6. (F) Readiness shows `reason=durable_signal_unavailable`. Expected first action: check backend logs for `capability_readiness_durable_signal_unavailable severity=high` and inspect the column. [F-03]
7. (G) Durable signal stale after payouts live. Expected first action: re-run the durable write via the Stripe sync/Connect endpoint for the user (entry `app/api/v1/endpoints/stripe.py`). [G-01]
8. (G) Durable column unreadable/None. Expected first action: inspect/backfill `users.stripe_payouts_enabled` at `_read_durable_stripe_signal`. [G-02]
9. (H) Propose adding a required "verified bank account" readiness step. Expected verdict: **BREAKING**. [§H]
10. (H) Propose adding a new seller-only analytics endpoint guarded `require_capability(seller, active)`. Expected verdict: **REVIEW**. [§H]
11. (Ambiguous) Seller is blocked and reason is empty/unclear. Acceptable first actions: (a) `CapabilityResolver.resolve(user_id)` to read persisted+effective status, OR (b) read `users.stripe_payouts_enabled`, OR (c) read the 403 body if one was returned. Any of these scores correct.

Pass threshold: weighted score ≥ 0.80.

---

## §J. Lifecycle

- **last_refresh_session:** S1051
- **last_refresh_commit:** 2f20ea3f87dd7c8afe09a2aed46a48b77dd969c3
- **last_refresh_date:** 2026-06-28
- **owner_agent:** Vulcan / Mars (ai.market backend peers)
- **refresh_triggers:** capability/onboarding BQ completion, Gate approval on the onboarding redesign, any incident touching seller readiness, scheduled cadence
- **scheduled_cadence:** 90 days
- **last_harness_pass_rate:** not_yet_run (first authoring; harness run queued)
- **last_harness_date:** null (first authoring; harness run queued)
- **first_staleness_detected_at:** null

---

## §K. Conformance

- **linter_version:** 1.0.0
- **last_lint_run:** S1051, 2026-06-28
- **last_lint_result:** PENDING — first CI run after merge; author validated §A–§K presence/order, agent forms, and §F↔§G cross-references by hand
- **trace_matrix_path:** n/a (greenfield, not a retrofit)
- **word_count_delta:** n/a (greenfield, not a retrofit)

### §K.0 — Linter version compatibility
- **linter_version:** 1.0.0 (matches `runbook-tools` package version; reconcile with `runbook-lint --version` on first CI run)
