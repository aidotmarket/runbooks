# Account Capability & Onboarding Runbook

> Covers the capability model that gates buying and selling on ai.market: how a user becomes a seller, what "provisioning" vs "active" means, the readiness signals that move a seller to active, the `require_capability` guard, the 403 `CapabilityRequiredError` contract, the self-serve buyer→seller request endpoint, the read-capabilities endpoint, and the capability-aware dashboard. Backing code verified against `aidotmarket/ai-market-backend` deployed main `839eef35` (slice-2 ship, S1054) and `aidotmarket/ai-market-frontend` deployed main `4932ecd` (capability-aware dashboard + floating setup bar, S1054).

---

## §A. Header

- **system_name:** Account Capability & Onboarding (ai.market backend + dashboard)
- **purpose_sentence:** Authorize who can buy and who can sell on ai.market by resolving per-user buyer/seller capabilities from persisted status plus live readiness signals, let a buyer self-serve request the seller capability, expose that state over HTTP, gate seller endpoints accordingly, and route the dashboard to the user's next setup step instead of erroring.
- **owner_agent:** Vulcan / Mars (ai.market backend peers)
- **escalation_contact:** Max
- **lifecycle_ref:** see §J (authoritative for refresh tracking)
- **authoritative_scope:** This runbook is the source of truth for the capability model (buyer default-on, seller additive), the provisioning→active readiness rules, the `require_capability` / `assert_user_capability` guard, the 403 `CapabilityRequiredError` body, the `GET /api/v1/auth/capabilities` read contract, the `POST /api/v1/auth/capabilities/seller/request` self-serve request contract, and the `next_action` field. It describes the capability-aware dashboard + floating setup bar (`ai-market-frontend`) as a downstream CONSUMER of these contracts, not as their source of truth. It is NOT the source of truth for sign-up/login (see `auth-signup-flow.md`) or 2FA setup (see `two-factor-auth.md`). It IS the home of the Stripe Connect ACTIVATION CHAIN procedure (E-06) — the click → hosted onboarding → return-sync → webhook → durable-write path that flips a seller active — added S1097 after both legs of that chain failed for the first live seller with no runbook owning them (Stripe keys themselves: `infisical-secrets.md`; session/cookie behavior on the Stripe round-trip: `browser-session-auth.md`).
- **linter_version:** 1.0.0

### M1 — Dependencies & Credentials / Source-of-Truth

| Dependency | What it provides | Where the credential lives | Owning service |
|---|---|---|---|
| ai.market Postgres | `user_capabilities` table (persisted status) + `users.stripe_payouts_enabled` durable column (the authoritative payouts-live signal) | `DATABASE_URL` — Infisical `ai-market-backend`/prod, set in Railway env | ai.market backend |
| Stripe Connect | Payouts eligibility that drives the `stripe_payouts_live` readiness step | `STRIPE_*` keys — Infisical `ai-market-backend`/prod (see `infisical-secrets.md`) | Payments |
| 2FA / TOTP | `totp_enabled` readiness step | 2FA/TOTP encryption key in backend env (see `two-factor-auth.md`) | Auth |
| ai-market-frontend | Capability-aware dashboard routing + floating setup progress bar that consume `GET /api/v1/auth/capabilities` | n/a (browser; calls the backend with the user's session JWT) | ai.market frontend |

There is no separate cache credential. The Redis readiness cache was removed (S1049); the durable Postgres column is the only source of truth for `stripe_payouts_live` in both the async and sync read paths.

---

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Buyer capability default-on (every active user can buy) | SHIPPED | `app/services/capability_resolver.py:CapabilityResolver._resolve_capability` (buyer branch returns active) | Resolver unit tests, S1044 slice-1 regression set (35 green) | S1054 |
| Seller capability additive + gated (not_requested → provisioning → active) | SHIPPED | `app/models/capability.py:CapabilityName,CapabilityStatus,UserCapability`; `app/schemas/capability.py:CapabilityStatusValue` | Resolver unit tests, S1044 slice-1 | S1054 |
| Seller readiness computation (4 steps) | SHIPPED | `app/services/capability_resolver.py:compute_seller_missing_steps` | Unit tests on the pure helper, S1044 slice-1 | S1054 |
| Effective-status derivation (persisted + missing steps); provisioning→active fall-through reachable | SHIPPED | `app/services/capability_resolver.py:compute_effective_seller_status` (§2.0.1 fix S1054: provisioning early-return removed, so a persisted-provisioning seller with all 4 steps done now flips to active; `not_requested`/`suspended` remain hard floors; fail-closed preserved) | Unit tests on the pure helper; slice-2 build tests (29 green, real Postgres) | S1054 |
| `require_capability` / `assert_user_capability` guard | SHIPPED | `app/api/deps.py:require_capability`, `app/api/deps.py:assert_user_capability` | Endpoint guard tests, S1044 slice-1 (incl. Gate-3 docstring-guard regression) | S1054 |
| 403 `CapabilityRequiredError` body contract | SHIPPED | `app/schemas/capability.py:CapabilityRequiredError`; raised in `app/api/deps.py:assert_user_capability` | Endpoint guard tests, S1044 slice-1 | S1054 |
| Active-seller publish gate on the canonical publish path (`POST /api/v1/vz/publish`) | SHIPPED | `app/routers/vz_publish.py:publish_listing` — after `validate_publish_jwt` returns `(seller_id, install_id)` and before `create_or_update_listing`, loads the seller via `db.get(User, seller_id)` (403 fail-closed if missing) then `assert_user_capability(seller, db, "seller", "active")`; gate precedes the upsert so it covers create AND update | `tests/test_vz_publish.py:TestPublishActiveSellerCapabilityGate` (9 tests; full vz_publish suite 62 green, real Postgres); Gate-2 + Gate-3 unanimous (AG security + DeepSeek + GLM), S1060 | S1060 |
| `GET /api/v1/auth/capabilities` (read resolved buyer+seller capabilities + `next_action`) | SHIPPED | `app/api/v1/endpoints/auth.py` (capabilities read route); response `app/schemas/capability.py:CapabilitySetResponse` + `next_action` | Slice-2 build tests (29 green, real Postgres); Gate-3 PASS S1054 | S1054 |
| `POST /api/v1/auth/capabilities/seller/request` (self-serve buyer→seller request; idempotent `not_requested`→`provisioning`; grants no privilege) | SHIPPED | `app/api/v1/endpoints/auth.py` (seller request route, async auth dep, never promotes to `active`, `suspended`→409, IntegrityError→rollback) | Slice-2 build tests (29 green, real Postgres); Gate-3 PASS S1054 | S1054 |
| `next_action` field on the readiness response | SHIPPED | `app/schemas/capability.py` (additive `next_action`); populated by the resolver from the first outstanding step | Slice-2 build tests | S1054 |
| Capability-aware dashboard routing (admits provisioning sellers; no buyer-bounce; Start-selling CTA for `not_requested`) | SHIPPED | `ai-market-frontend` `app/dashboard/layout.tsx`, `app/dashboard/page.tsx`, `app/dashboard/settings/page.tsx`, `api/capabilities.ts` | vitest 9 files/30 tests; frontend Gate-3 PASS S1054; prod `ai.market/dashboard` 200 | S1054 |
| Floating seller setup progress bar (persistent, N-of-4, deep-links each step, `next_action` CTA) | SHIPPED | `ai-market-frontend` `components/onboarding/SellerSetupProgressBar.tsx` (visible only when seller `effective_status==='provisioning'`; refetch on mount/focus) | vitest; frontend Gate-3 PASS S1054 | S1054 |
| Durable payouts-live signal (single source, sync + async parity) | SHIPPED | `app/services/capability_resolver.py:_read_durable_stripe_signal`; sync mirror `app/api/v1/endpoints/stripe.py:_require_seller_capability_sync` | Resolver unit tests; sync/async parity (M4, S1049) | S1054 |
| Redis readiness cache | DEPRECATED | removed S1049; durable `users.stripe_payouts_enabled` is authoritative | n/a (removed) | S1049 |
| `user_capabilities` table + status enums migration | SHIPPED | Alembic head `20260627_001` (prod `alembic_version`) | Gate-4 prod verification, S1049/S1054 | S1054 |

---

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| CapabilityModel | `app/models/capability.py:UserCapability` | `user_capabilities` table (user_id, capability, status); enums `CapabilityName`, `CapabilityStatus` | `app/schemas/capability.py` (API shapes) | Persisted seller status lives here. Absence of a seller row is projected from `users.role` (`seller`→active, else not_requested). |
| CapabilityResolver | `app/services/capability_resolver.py:CapabilityResolver.resolve` | reads `user_capabilities` + `users` columns | guard (`deps.py`), capabilities API, seller/listings endpoints | Returns `CapabilitySetResponse(buyer, seller)` plus `next_action`. Buyer always active. Seller effective status = persisted + missing steps; §2.0.1 fix makes the all-steps-done provisioning→active fall-through reachable. |
| ReadinessSignals | `app/services/capability_resolver.py:compute_seller_missing_steps` | reads `users.display_name`/`first_name`/`last_name`/`company_name`/`totp_enabled`/`stripe_payouts_enabled` | CapabilityResolver | Four steps: `profile_name`, `company_name`, `totp_enabled`, `stripe_payouts_live`. Any present step is dropped from `missing_steps`. `next_action` is the first outstanding step. |
| CapabilitiesReadEndpoint | `app/api/v1/endpoints/auth.py` → `GET /api/v1/auth/capabilities` | none (delegates to resolver) | CapabilityResolver; frontend dashboard/bar | Auth-gated (401 unauthenticated, verified in prod). Returns the resolved buyer+seller capabilities, seller `missing_steps`, and `next_action`. Read-only. |
| SellerRequestEndpoint | `app/api/v1/endpoints/auth.py` → `POST /api/v1/auth/capabilities/seller/request` | writes `user_capabilities` seller row | CapabilityResolver; frontend Start-selling CTA | Async auth dep (async `User` + `get_async_db`, access-type JWT, `status==active`, no `user_id` selector, no internal-key). Idempotent: `not_requested`→`provisioning`; re-request on an existing row is a no-op. NEVER promotes to `active` (privilege still requires readiness + the guard). `suspended`→409. `IntegrityError`→rollback. |
| CapabilityGuard | `app/api/deps.py:require_capability` | none (delegates to resolver) | every guarded seller endpoint | FastAPI dependency factory. `require_capability(name, required_status=active)` → `assert_user_capability`. Depends on `get_user_or_internal_key`. On fail raises 403 with `CapabilityRequiredError`. |
| StripeDurableSync | `app/services/capability_resolver.py:_read_durable_stripe_signal` | reads durable `users.stripe_payouts_enabled` (string `"true"`) | Stripe Connect / Stripe sync endpoints that WRITE the column | Read failure or `None` → `StripeReadiness(live=False, unavailable=True)`, logged `severity=high`, reason `durable_signal_unavailable`. |
| DashboardRouting (frontend, consumer) | `ai-market-frontend` `app/dashboard/layout.tsx` + `app/dashboard/page.tsx` | none (calls `GET /api/v1/auth/capabilities`) | CapabilitiesReadEndpoint | Routes by `effective_status` (with `user.role` fallback until the call resolves): admits provisioning sellers (no buyer-bounce off `/dashboard`), gates seller stats/listings to `sellerIsActive`, shows a Start-selling CTA for `not_requested` buyers. |
| SellerSetupProgressBar (frontend, consumer) | `ai-market-frontend` `components/onboarding/SellerSetupProgressBar.tsx` | none (calls `GET /api/v1/auth/capabilities`) | CapabilitiesReadEndpoint | Persistent floating bar, visible only while seller `effective_status==='provisioning'`. Shows N-of-4 progress, per-step done/to-do, deep-links each step to its setup surface, surfaces the `next_action` CTA, refetches on mount/focus. |

Data flow (guard): a guarded request resolves the caller's `User`, `CapabilityResolver.resolve` reads the persisted seller row (or projects from role), computes `missing_steps` from the four readiness signals, derives effective status, and the guard compares effective status against the endpoint's `required_status`. A `provisioning` requirement is also satisfied by `active` (active is strictly stronger).

Data flow (self-serve upgrade): the dashboard Start-selling CTA calls `POST /api/v1/auth/capabilities/seller/request`, which writes/affirms a `provisioning` seller row (no privilege granted). The floating bar then reads `GET /api/v1/auth/capabilities`, shows the outstanding steps, and deep-links each. When the durable signals flip all four steps green, the resolver's effective status becomes `active` and the seller guard starts admitting the user.

The capability guard sits ALONGSIDE older, narrower guards that still exist: role-based `get_current_seller` (`deps.py`), Stripe-KYC `get_kyc_verified_seller` (`deps.py`), and the `_enforce_onboarding` flag check (`onboarding_completed` → 403 with `onboarding_url`). The capability guard is the authoritative gate for buyer/seller marketplace actions; the others are legacy or orthogonal (KYC, first-run onboarding).

---

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Operator / support (human) | Read a user's resolved capabilities | `CapabilityResolver.resolve(user_id)` via backend shell, or `GET /api/v1/auth/capabilities` as that user | Internal key or admin JWT (shell); user JWT (endpoint) | COMPLETE |
| Buyer (end user) | Self-serve request the seller capability | `POST /api/v1/auth/capabilities/seller/request` (via the dashboard Start-selling CTA) | User access-type JWT, `status==active` | COMPLETE |
| End user (buyer or provisioning seller) | Read own capabilities + next setup step | `GET /api/v1/auth/capabilities` | User access-type JWT | COMPLETE |
| allAI / internal service | Call a guarded endpoint on behalf of a service flow | `get_user_or_internal_key` (X-Internal-API-Key) → synthetic admin user | Internal key | PARTIAL — internal-key caller resolves as role `admin`, so seller readiness is `not_requested`; the seller-request endpoint rejects the internal key (no `user_id` selector); use a real user JWT when seller readiness or self-serve request matters. Notes: do not rely on the internal key to satisfy a seller `active` gate. |
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
- **tool_or_endpoint:** `GET /api/v1/auth/capabilities` (delegates to `CapabilityResolver.resolve`).
- **argument_sourcing:** `user_id`: the authenticated user's id from the JWT `sub`.
- **idempotency:** IDEMPOTENT.
- **expected_success:** returns `seller` readiness with `effective_status=provisioning` (or `not_requested`), a `missing_steps` list drawn from `profile_name`, `company_name`, `totp_enabled`, `stripe_payouts_live`, and a `next_action` naming the first outstanding step.
- **expected_failures:** 401 if not authenticated; an unreadable durable column yields `reason=durable_signal_unavailable` (see §F-03).
- **next_step_success:** surface the missing steps to the customer in plain language (see Customer-facing copy below); the floating bar deep-links each.
- **next_step_failure:** if `durable_signal_unavailable`, follow §G-02.

### E-03 — Seller completes Stripe payouts and goes active
- **id:** E-03
- **trigger:** Seller finishes Stripe Connect; payouts become live.
- **pre_conditions:** profile name set, company name set, 2FA on, Stripe payouts eligible.
- **tool_or_endpoint:** the Stripe sync / Connect endpoint that writes `users.stripe_payouts_enabled = "true"`, then `require_capability(CapabilityName.seller, CapabilityStatus.active)` on a seller action.
- **argument_sourcing:** durable signal: written by the Stripe sync path; read by `_read_durable_stripe_signal`.
- **idempotency:** IDEMPOTENT_WITH_KEY (durable write keyed by `user_id`; re-running is safe).
- **expected_success:** `missing_steps` empties, effective seller status flips to `active` (§2.0.1 fall-through), seller actions (create listing, etc.) succeed.
- **expected_failures:** if the durable write did not land, status stays `provisioning` with `missing_steps=[stripe_payouts_live]` (see §F-02).
- **next_step_success:** seller can list/sell; the floating bar disappears (no longer provisioning).
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

### E-05 — Buyer self-serve requests the seller capability
- **id:** E-05
- **trigger:** A buyer taps Start-selling on the dashboard to begin selling.
- **pre_conditions:** `user_authenticated`, `user.status == active`, seller capability `not_requested` (or already `provisioning`).
- **tool_or_endpoint:** `POST /api/v1/auth/capabilities/seller/request`.
- **argument_sourcing:** `user`: resolved by the async auth dep from the access-type JWT (no body selector; the endpoint never targets another user_id).
- **idempotency:** IDEMPOTENT (`not_requested`→`provisioning`; re-request on an existing provisioning/active row is a safe no-op).
- **expected_success:** seller row is `provisioning`; response reflects provisioning + `missing_steps` + `next_action`; NO privilege is granted (still gated until readiness completes).
- **expected_failures:** 401 if unauthenticated; 409 if the seller capability is `suspended` (policy enforcement — see §F-06); rollback with no row change on `IntegrityError`.
- **next_step_success:** the dashboard shows the floating setup bar; user works the four steps.
- **next_step_failure:** on 409 suspended, do NOT auto-clear — route per §F-06 (escalation, not a code repair).

### E-06 — Stripe Connect activation chain (click → active)
- **id:** E-06
- **trigger:** A provisioning seller clicks Connect Stripe (dashboard card, floating bar, or stripe-return retry).
- **pre_conditions:** `user_authenticated`, seller `provisioning`, 2FA complete (endpoint enforces 403 otherwise).
- **chain (each link verified live S1097):**
  1. Frontend calls `POST /connect/onboarding`; backend reuses `users.stripe_account_id` or creates a Standard account, returns `{onboarding_url, account_id, type}`. Frontend parsing is centralized in `api/connect.ts` (`onboarding_url` with legacy `url` fallback, `connect.stripe.com/` prefix guard) — the S468/S1097 field-mismatch bug lives here if it ever regresses.
  2. Browser goes to Stripe-hosted onboarding; seller completes; Stripe returns the browser to `/dashboard/stripe-return`.
  3. **Return leg:** stripe-return polls `GET /connect/status`, which fetches the live account from Stripe and writes the durable columns (`users.stripe_payouts_enabled/stripe_details_submitted/stripe_onboarding_complete`) plus the `party_identity` bridge. Requires the session to survive the cross-site round-trip (auth `hydrated` gate, S1097; cookie contract in `browser-session-auth.md`).
  4. **Webhook leg (independent of the browser):** Stripe delivers `account.updated` / `capability.updated` / `account.application.deauthorized` for CONNECTED accounts ONLY to a **Connect-enabled** webhook endpoint. Live endpoint: `we_1TojkMRucxd97j0A9bMsZv1f` → `https://api.ai.market/api/v1/webhooks/stripe`, created S1097 (the original endpoint was account-level, so seller events were silently undeliverable). Its signing secret sits in the `STRIPE_WEBHOOK_SECRET_PREVIOUS` slot; the handler verifies against both secrets (`webhooks.py` two-secret try).
  5. Either leg flips the durable signal; the resolver's all-steps-done fall-through makes the seller `active`; the publish gate opens.
- **idempotency:** IDEMPOTENT end-to-end (account reuse; durable writes keyed by user; either leg may fire first or twice).
- **expected_failures:** login bounce on return (fixed S1097, `hydrated` gate — see BQ-FE-STRIPE-RETURN-LOGIN-BOUNCE-S1097); webhook silently undelivered (check the endpoint is Connect-enabled: `GET /v1/webhook_endpoints`, the connect flag, NOT just the event list — the S1097 lesson).
- **operator resync (no user JWT needed):** when Stripe says done but the platform disagrees (F-02), read ground truth from Stripe (`GET /v1/accounts/{acct}` → `details_submitted`/`payouts_enabled`), then mirror it: `UPDATE users SET stripe_payouts_enabled='true', stripe_details_submitted='true', stripe_onboarding_complete='complete' WHERE id=…` and patch the `party_identity` metadata (`onboarding_status`,`payouts_enabled`,`details_submitted`). Always read Stripe FIRST; never set the column ahead of provider truth. Used live for the first seller, S1097.

### Customer-facing copy (seller readiness, Max voice)
- `profile_name`: "Add your name so buyers know who they are dealing with."
- `company_name`: "Add your company name. Buyers want to know who is behind the data."
- `totp_enabled`: "Turn on two-factor login. We need this on before you can sell."
- `stripe_payouts_live`: "Connect Stripe so we can pay you. Once payouts are live you can start selling."
- active / all-clear: "You are all set to sell. Go ahead and list your data."
- start-selling CTA (not_requested buyer): "Want to sell your data? Start here — we will walk you through it."

---

## §F. Isolate — Diagnosing Deviations

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Seller gets 403 on a state-changing seller action; body shows `missing_steps` | Seller is genuinely still provisioning (a readiness step is incomplete) | Read the 403 `CapabilityRequiredError` body; `effective_status=provisioning` and `missing_steps` names the incomplete step(s) | | CONFIRMED |
| F-02 | `missing_steps=[stripe_payouts_live]` though the seller finished Stripe onboarding | Durable `users.stripe_payouts_enabled` not written/synced after payouts went live | Read `users.stripe_payouts_enabled` for the user; if not `"true"`, the durable write lagged | §G-01 | CONFIRMED |
| F-03 | `reason=durable_signal_unavailable` on seller readiness | The durable column read raised or returned `None`; resolver returns `live=False, unavailable=True` | Check backend logs for `capability_readiness_durable_signal_unavailable ... severity=high`; inspect the column value/type | §G-02 | CONFIRMED |
| F-04 | A seller passes the async resolve but fails the sync Stripe-path gate (or vice versa) | Sync and async readiness derivations drifted apart | Confirm `stripe.py:_require_seller_capability_sync` calls the shared `compute_*` helpers | §G-03 | HYPOTHESIZED |
| F-05 | 403 on a provisioning-level read endpoint (e.g., discovery readiness) | User never requested seller; persisted status `not_requested` | Resolve the user; `persisted_status=not_requested` | | CONFIRMED |
| F-06 | `POST .../seller/request` returns 409 | Seller capability is `suspended` (policy enforcement), so a self-serve request is refused by design | Resolve the user; `persisted_status=suspended` and a `reason`/suspension timestamp is set. This is expected behavior, not a bug — clearing suspension is a policy action (Max / Council), never an automatic repair | | CONFIRMED |
| F-07 | All four steps look done but seller stays `provisioning` | (pre-S1054) the provisioning early-return short-circuited the active fall-through | Confirm deployed `compute_effective_seller_status` includes the §2.0.1 fix (no early provisioning return before the `missing_steps==[]`→active check); on current main this is fixed | §G-03 | CONFIRMED |

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
- **symptom_ref:** F-04, F-07
- **component_ref:** CapabilityResolver
- **root_cause:** The sync seller gate and the async resolver derive readiness independently and have diverged, or an effective-status derivation short-circuits the active fall-through (the pre-S1054 provisioning early-return).
- **repair_entry_point:** `app/services/capability_resolver.py:compute_seller_missing_steps` + `compute_effective_seller_status` (the shared helpers), consumed by both `CapabilityResolver` and `app/api/v1/endpoints/stripe.py:_require_seller_capability_sync`.
- **change_pattern:** Route both paths through the shared `compute_*` helpers so precedence cannot drift (the M4 design from S1049); keep the §2.0.1 fix in place so a fully-ready provisioning seller flips to active; do not reintroduce a parallel readiness derivation or an early provisioning return.
- **rollback_procedure:** Revert to the prior commit; both paths ship calling the shared helpers, and the §2.0.1 fix is on deployed main `839eef35`.
- **integrity_check:** A user who is `active` under the async resolver is also `active` under the sync gate, and vice versa, across all four readiness steps; a provisioning seller with all four steps done resolves to `active`.

---

## §H. Evolve — Extending the System

### §H.1 Invariants
- **Buyer is default-on.** Every active user can buy; the buyer branch must not be gated behind readiness steps.
- **Seller is additive and gated.** A seller endpoint that requires `active` must never be served to a user whose effective seller status is below the required status.
- **Publishing requires an active seller, on the canonical path only.** A listing reaches the marketplace through one entry point, `POST /api/v1/vz/publish` (shared by vectorAIz and AIM Data). It asserts `active` seller capability after trust-token validation and before any listing create/update, taking identity only from the verified install binding (`vz_installs.seller_id`), never the request body. This is what enforces `no_anonymous_uploads` on the live publish path. Other/legacy publish surfaces are being REMOVED (not separately gated) under the publish-paths consolidation (`BQ-PUBLISH-PATHS-CONSOLIDATION-S1060`); `aim.py /nodes/{id}/tools/publish` is AIM-node tool registration, not a dataset publish, and is out of scope.
- **Self-serve request grants no privilege.** `POST .../seller/request` may only move `not_requested`→`provisioning`. It must NEVER promote to `active`; activation is earned by readiness and enforced by the guard. `suspended` is a hard floor the request endpoint must refuse (409), never auto-clear.
- **One source of truth for payouts-live.** `users.stripe_payouts_enabled` is the sole authority for `stripe_payouts_live` in BOTH the sync and async paths. No cache may become the source of truth; the two paths must share the `compute_*` helpers.
- **403 body is a public contract.** The `CapabilityRequiredError` field set (`capability`, `persisted_status`, `effective_status`, `missing_steps`, `reason`) is consumed by the frontend; changing it is BREAKING.
- **Read contract is a public contract.** `GET /api/v1/auth/capabilities` (`buyer`/`seller` status, `missing_steps`, `next_action`) is consumed by the dashboard and the floating bar; removing or renaming a field is BREAKING.
- **Dashboard routes, never errors.** The capability-aware dashboard must route an unfinished user to their next step (provisioning sellers admitted, `not_requested` buyers shown the CTA); it must not hard-error on mid-setup state.
- **Non-custodial.** Capability state is metadata only; no customer data flows through this layer.
- **module** = immediate subdir of `app/` (e.g. `app/api/`, `app/services/`, `app/models/`, `app/schemas/`). **public contract** includes the served API schemas (`CapabilityRequiredError`, `CapabilitySetResponse` + `next_action`). **config default** = values in the canonical backend config. **runtime dependency** = `pyproject.toml [project.dependencies]`.

### Change-class examples
- *Add a fifth required readiness step (e.g., a verified bank account):* **BREAKING** — it adds a required gate that can newly fail existing `active` sellers and changes the `missing_steps` value set (an authz-boundary + public-contract change).
- *Change a read endpoint from `provisioning` to `active`:* **BREAKING** — changes scope semantics for existing callers (provisioning sellers lose access they had).
- *Let `POST .../seller/request` promote straight to `active`:* **BREAKING** — violates the self-serve-grants-no-privilege invariant; an authz-boundary change.
- *Add a `next_action` value or reword a `missing_steps` customer-facing copy string:* **SAFE** — additive/copy change within existing semantics (the step key set is unchanged).
- *Add a new seller-only feature endpoint guarded by `require_capability(seller, active)`:* **REVIEW** — a new feature on an existing public surface, no contract change.

---

## §I. Acceptance Criteria (scenario set)

**Weighting:** equal-weight default (1/N, N = 14). No unequal weights declared.

1. (E) New active user with no seller row attempts to buy. Expected first action: confirm buyer effective status is `active` and serve the request. [E-01]
2. (E) User asks "what do I need to do to sell?" Expected first action: call `GET /api/v1/auth/capabilities` (resolver) and return `missing_steps` + `next_action`. [E-02]
3. (E) Seller just finished Stripe; verify they can now list. Expected first action: read `users.stripe_payouts_enabled` and re-resolve; confirm `active`. [E-03]
4. (E) Buyer taps Start-selling. Expected first action: `POST /api/v1/auth/capabilities/seller/request`; confirm `not_requested`→`provisioning` and that NO privilege was granted. [E-05]
5. (E) Buyer taps Start-selling twice. Expected first action: confirm the second request is a safe no-op (idempotent), status stays `provisioning`. [E-05]
6. (F) Seller reports 403 creating a listing. Expected first action: read the 403 `CapabilityRequiredError` body and inspect `missing_steps`. [F-01]
7. (F) `missing_steps=[stripe_payouts_live]` though Stripe is done. Expected first action: read `users.stripe_payouts_enabled` for the user. [F-02]
8. (F) Readiness shows `reason=durable_signal_unavailable`. Expected first action: check backend logs for `capability_readiness_durable_signal_unavailable severity=high` and inspect the column. [F-03]
9. (F) `POST .../seller/request` returns 409. Expected first action: resolve the user, confirm `persisted_status=suspended`, and treat as policy (escalate; do not auto-clear). [F-06]
10. (F) All four steps done but seller stays provisioning. Expected first action: confirm deployed `compute_effective_seller_status` carries the §2.0.1 fix (no early provisioning return). [F-07]
11. (G) Durable signal stale after payouts live. Expected first action: re-run the durable write via the Stripe sync/Connect endpoint for the user (entry `app/api/v1/endpoints/stripe.py`). [G-01]
12. (G) Durable column unreadable/None. Expected first action: inspect/backfill `users.stripe_payouts_enabled` at `_read_durable_stripe_signal`. [G-02]
13. (H) Propose letting `POST .../seller/request` promote straight to `active`. Expected verdict: **BREAKING**. [§H]
14. (Ambiguous) Seller is blocked and reason is empty/unclear. Acceptable first actions: (a) `GET /api/v1/auth/capabilities` / `CapabilityResolver.resolve(user_id)` to read persisted+effective status, OR (b) read `users.stripe_payouts_enabled`, OR (c) read the 403 body if one was returned. Any of these scores correct.

Pass threshold: weighted score ≥ 0.80.

---

## §J. Lifecycle

- **last_refresh_session:** S1097
- **last_refresh_commit:** 8ac99a03 (backend deployed main) / 41a75d3 (frontend deployed main, hydration-gate fix)
- **last_refresh_date:** 2026-07-02
- **owner_agent:** Vulcan / Mars (ai.market backend peers)
- **refresh_triggers:** capability/onboarding BQ completion, Gate approval on the onboarding redesign, any incident touching seller readiness, scheduled cadence
- **scheduled_cadence:** 90 days
- **last_harness_pass_rate:** not_yet_run (harness run still queued from first authoring)
- **last_harness_date:** null (harness run queued)
- **first_staleness_detected_at:** null
- **refresh_log:**
  - S1051 (2026-06-28): first authoring — slice-1 capability model, guard, 403 contract, readiness signals.
  - S1097 (2026-07-02): first-seller incident refresh — added E-06 (Stripe Connect activation chain) after BOTH activation legs failed live for seller #1: the return-leg sync was killed by a login bounce (pristine-store guard race, fixed with the auth `hydrated` gate, frontend 41a75d3) and the webhook leg was undeliverable because the Stripe endpoint was never Connect-enabled (fixed: `we_1TojkMRucxd97j0A9bMsZv1f` + second-secret slot, backend env deploy 12:29Z). Documented the operator resync procedure (used live). Lesson recorded: verifying a webhook means verifying the CONNECT flag, not just existence + event list.
  - S1054 (2026-06-29): slice-2 refresh — added `GET /api/v1/auth/capabilities`, `POST /api/v1/auth/capabilities/seller/request`, `next_action`, capability-aware dashboard + floating setup bar (frontend consumers), and the §2.0.1 provisioning→active fall-through fix. Slice-2 shipped to prod 2026-06-28 (backend `839eef35`, frontend `4932ecd`).

---

## §K. Conformance

- **linter_version:** 1.0.0
- **last_lint_run:** S1054, 2026-06-29
- **last_lint_result:** PENDING — CI run on next merge; author validated §A–§K presence/order, agent forms, §F↔§G cross-references (F-02→G-01, F-03→G-02, F-04/F-07→G-03), and acceptance-scenario↔procedure references by hand
- **trace_matrix_path:** n/a (greenfield, not a retrofit)
- **word_count_delta:** slice-2 additions (two endpoints, next_action, dashboard/bar consumers, §2.0.1 fix) over the S1051 baseline
- **§K.0 — Linter version compatibility**
  - **linter_version:** 1.0.0 (matches `runbook-tools` package version; reconcile with `runbook-lint --version` on first CI run)
