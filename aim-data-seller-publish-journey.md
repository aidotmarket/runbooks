---
system_name: aim-data-seller-publish-journey
purpose_sentence: Operate, isolate, repair, and safely evolve the customer journey from a signed-in AIM Data install to a live ai.market listing.
owner_agent: mars
escalation_contact: Max for any action touching the money path or production customer accounts
lifecycle_ref: §J
authoritative_scope: The ordered AIM Data seller publish journey, its cross-repository handoffs, customer-visible readiness gates, verified failure signatures, and first-response procedures; broader product behavior, seller readiness policy, and the single publish-path architecture remain authoritative in their linked parent runbooks.
linter_version: 1.0.0
---

# AIM Data Seller Publish Journey

This runbook discharges the AIM Data seller-publish journey waivers, including S1216-D3, S1219-D1, and their predecessors. It starts after the customer has an AIM Data install and follows the customer-visible path through ai.market sign-in, install registration, local listing preparation, explicit disclosure confirmation, signed publish, and live-listing verification.

This runbook does not redefine the AIM Data product (`aim-data.md`), the one-route/one-gate publishing architecture (`publish-paths.md`), or seller readiness (`account-capability-onboarding.md`). Those runbooks remain authoritative for their respective scopes.

## §A. Header

The YAML frontmatter above is authoritative for the §A header fields. §J is authoritative for lifecycle metadata.

### M1 — Dependencies & Credentials / Source-of-Truth

| Dependency | Required state or credential | Source of truth | Journey use |
|---|---|---|---|
| AIM Data customer install | Running install with an ai.market-authenticated session; the access token is persisted by `app/services/serial_store.py:SerialStore.persist_ai_market_session` in local `serial.json` (mode 0600) | `aim-data.md`; AIM Data `app/routers/auth.py:aim_market_login` | Establishes the seller identity used for registration and publish. Do not copy tokens into job scripts or this runbook. |
| AIM Data device keys | Locally generated Ed25519 keypair; private key stays in the AIM Data keystore | AIM Data `app/core/crypto.py:DeviceCrypto`; `app/services/registration_service.py:ensure_vz_install_registered` | Public key registers the install; private key signs the short-lived publish JWT. |
| Install registration | `POST /api/v1/vz/register` with the authenticated user's bearer token and `{public_key_b64, serial?, serial_install_token?}` | ai-market-backend `app/routers/vz_publish.py:register_install` | Registration is the act of becoming a seller: it provisions a non-admin caller to seller role, marks onboarding complete, registers `vz_installs`, and returns HTTP 201 with `install_id`. The route is `/api/v1/vz/register`, never `/register-install`. |
| Seller readiness | Effective seller capability `active`: profile name, company name, TOTP enabled, and durable Stripe payouts-live signal | `account-capability-onboarding.md`; ai-market-backend `app/services/capability_resolver.py:CapabilityResolver.resolve` | Registration provisions seller identity but does not bypass readiness. Publish fails 403 until all readiness steps pass. Anything involving payouts or a production customer account escalates to Max. |
| Local listing preparation | Dataset is `preview_ready`; privacy review is complete; listing metadata has title and description; seller accepts metadata; disclosure decision is confirmed | AIM Data `frontend/src/pages/DatasetDetail.tsx:ListingPreparation`; `app/routers/datasets.py:generate_listing_metadata` | Unlocks Step 3 and the Publish action. This is local draft state, not a second ai.market listing store. |
| Canonical publish route | Signed EdDSA JWT and canonical payload sent to `POST /api/v1/vz/publish` | `publish-paths.md`; ai-market-backend `app/routers/vz_publish.py:publish_listing` | The only route that creates or updates the live marketplace listing; it enforces the active-seller gate before writing. The website has no create/publish action. |
| Canonical listing record | `listings` row keyed for this flow by `(seller_id, source_dataset_id=vz_raw_listing_id)` | `publish-paths.md`; ai-market-backend `app/services/vz_publish_service.py:create_or_update_listing` | Stores the published listing and returns `listing_id` plus `marketplace_url`. |
| Browser verification | kd-browser runner at `127.0.0.1:8790`, driven by checked job scripts; both operating instances invoke jobs through `shell_request` | `e2e-browser-runner.md` operating pattern; the journey job script under the operator's browser-job workspace | Verifies the real customer sequence in Chrome. Never put credentials in the script; use the approved authenticated profile. Max approval is required for a production customer account or money-path mutation. |

Verified source baselines for this edition: AIM Data `origin/main` `2430bb9`; ai-market-backend `main` `dfd926ec`; runbooks `main` `5f968f1`.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| ai.market sign-in pre-warms AIM Data install registration | SHIPPED | `aim-data/app/routers/auth.py:aim_market_login` | `aim-data/tests/test_auth_integration.py`; `aim-data/tests/test_vz_publish_proxy.py`; S1219/S1220 | 2026-07-14 |
| `/api/v1/vz/register` provisions an authenticated buyer-role caller to seller and returns 201 | SHIPPED | `ai-market-backend/app/routers/vz_publish.py:register_install` | `ai-market-backend/tests/integration/test_vz_register_role_promotion.py:test_register_install_promotes_buyer_on_real_userrole_column`; T-2026-000256 live buyer-role HTTP 201 | 2026-07-14 |
| Local privacy and listing-metadata preparation | SHIPPED | `aim-data/frontend/src/pages/DatasetDetail.tsx:ListingPreparation` | `aim-data/frontend/src/pages/DatasetDetail.test.tsx`; S1219 real Chrome, build a13d9a4 | 2026-07-14 |
| Accept-all metadata unlocks Step 3 without requiring a nonexistent draft listing id | SHIPPED | `aim-data/frontend/src/pages/DatasetDetail.tsx:handleAcceptAllMetadata` | `aim-data/frontend/src/pages/DatasetDetail.test.tsx:enables metadata acceptance without a draft listing id`; T-2026-000251, AIM Data 2430bb9 | 2026-07-14 |
| AI-training disclosure confirmation gates the Publish action | SHIPPED | `aim-data/frontend/src/pages/DatasetDetail.tsx:ListingPreparation` | `aim-data/tests/test_s804_disclosure_dataset_detail.py`; DOM id `ai-training-disclosure-confirmation`; S1219 real Chrome | 2026-07-14 |
| AIM Data signs and proxies the publish payload | SHIPPED | `aim-data/app/routers/marketplace_publish.py:publish_via_signed_proxy` | `aim-data/tests/test_vz_publish_proxy.py`; `aim-data/tests/test_dataset_publish_signed_proxy.py`; S1219 | 2026-07-14 |
| Canonical receiver enforces active seller and creates/updates the listing | SHIPPED | `ai-market-backend/app/routers/vz_publish.py:publish_listing` | `ai-market-backend/tests/test_vz_publish.py:TestPublishCapabilityGate`; S1219/S1220 | 2026-07-14 |
| Browser journey reaches Accept all, Step 3, disclosure confirmation, and Publish | SHIPPED | `aim-data/frontend/src/pages/DatasetDetail.tsx:ListingPreparation` | kd-browser job via `127.0.0.1:8790` using the `shell_request` job-script pattern; S1219 real Chrome against build a13d9a4 | 2026-07-14 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| AIM Data ai.market session | `aim-data/app/routers/auth.py:aim_market_login` | Local user/session data; `serial.json.ai_market_access_token`; `serial.json.ai_market_seller_id` | ai.market `POST /api/v1/auth/login`, `GET /api/v1/auth/me`; install registration client | On successful login (including 2FA completion), persists the ai.market session and attempts install registration. Registration failure is logged and retried at publish. |
| AIM Data install registration client | `aim-data/app/services/registration_service.py:ensure_vz_install_registered` | `serial.json.vz_install_id`; `serial.json.vz_install_token`; local Ed25519 public key | ai.market `POST /api/v1/vz/register` | Returns a cached install id when present; otherwise sends the public key under the seller bearer token and persists the returned id. It never sends the private key. |
| ai.market registration receiver | `ai-market-backend/app/routers/vz_publish.py:register_install` | `users`; `vz_installs`; optional `serials` binding | AIM Data registration client; `vz_publish_service.register_install` | Promotes a non-seller/non-admin caller using explicit `userrole` casts, completes onboarding fields, then registers the install. Seller role provisioning and seller readiness are distinct states. |
| AIM Data listing preparation | `aim-data/frontend/src/pages/DatasetDetail.tsx:ListingPreparation` | Dataset processing record; `record.metadata.listing_metadata`; PII actions/attestation; component approval and disclosure state | `POST /api/datasets/{dataset_id}/listing-metadata`; disclosure sample endpoints; allAI review when a draft id exists | The pre-publish draft is locally persisted metadata plus UI approval state. The journey does not require a local RawListing or remote ai.market Listing before Publish. Accept all transitions Step 2 to Step 3 when title and description exist. |
| AIM Data dataset publish adapter | `aim-data/app/routers/datasets.py:publish_to_marketplace` | Local dataset `listing_id`; processed metadata, compliance, attestation | `marketplace_publish.publish_via_signed_proxy` | Requires `preview_ready`, builds the canonical payload from approved overrides/local outputs, invokes the signer/proxy, and persists the returned marketplace listing id. |
| AIM Data signed publish proxy | `aim-data/app/routers/marketplace_publish.py:publish_via_signed_proxy` | Local keystore; `serial.json`; source provenance | ai.market `POST /api/v1/vz/publish` | Resolves seller and install ids, validates source provenance, hashes the exact body, signs a short-lived EdDSA JWT, and forwards backend errors verbatim. |
| ai.market canonical publish receiver | `ai-market-backend/app/routers/vz_publish.py:publish_listing` | Redis replay/rate-limit state; `users`; capabilities | JWT validator; active-seller capability resolver; canonical listing writer | Fails closed when security services are unavailable, validates the signed body, enforces seller `active`, then calls the one listing writer. |
| ai.market canonical listing writer | `ai-market-backend/app/services/vz_publish_service.py:create_or_update_listing` | `listings`; translation outbox; versions; notification/share side effects | Search/translation/version/discovery services | Upserts by seller plus `vz_raw_listing_id`, sets status published, and returns the record used to construct `https://ai.market/listings/{slug}`. See `publish-paths.md` for the system-wide invariant. |

Journey order:

1. AIM Data sign-in persists the ai.market seller session and pre-warms `POST /api/v1/vz/register`.
2. Registration provisions seller role and binds the install public key; seller readiness remains independently gated.
3. A `preview_ready` dataset completes privacy review and generates/persists listing metadata.
4. **Accept all & continue** approves the metadata and opens Step 3 even when no draft listing id exists.
5. The seller selects a sample disclosure, checks `ai-training-disclosure-confirmation`, and clicks **Publish to ai.market**.
6. AIM Data signs the payload and calls the single `POST /api/v1/vz/publish` route.
7. ai.market enforces active-seller readiness, upserts the `listings` row, and returns `listing_id` and `marketplace_url`.
8. AIM Data records the listing id, submits the disclosure snapshot, and the operator verifies the returned live URL.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| mars | Operate and isolate the end-to-end browser journey | `shell_request` from either instance to submit a checked kd-browser job script to `127.0.0.1:8790` | Approved AIM Data test profile; production customer or money-path access requires Max | COMPLETE |
| mars | Inspect AIM Data registration/publish logs and local non-secret state | `shell_request` to the AIM Data host/container; inspect response status and redacted `serial.json` fields only | Customer install operator scope; never emit access tokens or private keys | COMPLETE |
| mars | Inspect backend route behavior and deploy status | `shell_request`/repository read against ai-market-backend and approved production observability | Backend read; mutation or production customer repair escalates to Max | COMPLETE |
| allAI | Generate and optionally revise listing metadata | AIM Data metadata generation and listing-edit tools | Current seller's local dataset/draft only | COMPLETE |
| Max | Approve actions involving Stripe payouts, money-path state, or production customer accounts | Owner intervention through the authoritative account/Stripe procedures | Owner and production money-path scope | COMPLETE |

Browser verification uses a job script, not ad hoc DOM driving. The script targets the signed-in AIM Data install, records the journey checkpoints, addresses the shadcn checkbox by `#ai-training-disclosure-confirmation`, and submits through the runner at `127.0.0.1:8790`. Both instances operate the job through `shell_request`; credentials stay in the approved browser profile, never in the script.

## §E. Operate

```yaml operate
- id: E-01
  trigger: A customer with a running AIM Data install signs in with their ai.market account to begin selling.
  pre_conditions:
    - AIM Data install is authenticated locally and can reach ai.market over HTTPS
    - customer controls the ai.market account and can complete 2FA when prompted
    - local DeviceCrypto keystore is configured and writable
  tool_or_endpoint: "POST AIM Data /api/auth/aim-market-login {email, password, pre_auth_token?, code?}; AIM Data then calls POST ai.market /api/v1/vz/register {public_key_b64, serial?, serial_install_token?}"
  argument_sourcing:
    email: customer enters it in the AIM Data sign-in form
    password: customer enters it in the AIM Data sign-in form; never log or script it
    pre_auth_token: returned by ai.market when the account requires 2FA
    code: customer supplies the current TOTP code
    public_key_b64: generated from the local DeviceCrypto Ed25519 keypair
    serial: read from local serial state when the install is serial-backed
    serial_install_token: read from local serial state when the install is serial-backed
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: "AIM Data sign-in succeeds; ai.market POST /api/v1/vz/register returns HTTP 201 {install_id, install_token}; local serial.json persists ai_market_seller_id and vz_install_id; caller is provisioned to seller role"
    verification: "Read redacted AIM Data logs for 'VZ install registered with ai.market' and inspect only presence/non-empty status of serial.json.vz_install_id; T-2026-000256 live probe returned 201 for a buyer-role account on 2026-07-14"
  expected_failures:
    - signature: "POST /api/v1/vz/register returns 500 with operator does not exist: userrole <> character varying"
      cause: "Resolved enum-vs-varchar role.not_in predicate regression, T-2026-000256 (§F-01)"
    - signature: "VZ install registration auth failed (401 or 403)"
      cause: "Missing/expired ai.market bearer token or account access denial (§F-05)"
  next_step_success: Continue to E-02; registration provisions seller identity but the publish gate still requires active readiness.
  next_step_failure: Match the exact registration signature in §F before attempting Publish.
- id: E-02
  trigger: A signed-in seller has a preview-ready dataset and wants to prepare the buyer-facing listing.
  pre_conditions:
    - AIM Data ai.market session is present
    - dataset status is preview_ready
    - privacy scan has completed and flagged columns are resolved or explicitly attested
  tool_or_endpoint: "AIM Data ListingPreparation: Continue to metadata -> POST /api/datasets/{dataset_id}/listing-metadata -> Accept all & continue"
  argument_sourcing:
    dataset_id: current DatasetDetail route and dataset API response
    privacy_actions: seller decisions shown in Step 1
    title_description_tags_category: generated listing_metadata plus seller edits in Step 2
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: "listing_metadata is persisted under the dataset record; title and description populate; Accept all & continue is enabled without a draft listing id; activeStep becomes 3"
    verification: "Step 3: Listing Details and Disclosure is visible; S1219 verified this in real Chrome against build a13d9a4 after Accept all"
  expected_failures:
    - signature: "Accept all & continue remains disabled while title and description are populated and dataset.listing_id is null"
      cause: "Resolved draft-listing-id guard regression, T-2026-000251 (§F-03)"
    - signature: "Metadata generation failed"
      cause: "Listing metadata service failure; inspect the dataset endpoint response before changing publish code"
  next_step_success: Continue to E-03.
  next_step_failure: Isolate UI state and endpoint responses via §F-03; do not create a second marketplace listing path.
- id: E-03
  trigger: The seller is on Step 3 and is ready to publish the reviewed listing.
  pre_conditions:
    - approvedMetadataDraft exists and still matches the public fields
    - title and description are non-empty and price is at least USD 25
    - sample decision is none or the displayed approved sample is available
    - ai-training-disclosure-confirmation is checked
    - seller capability is active, including Stripe payouts live
  tool_or_endpoint: "Click Publish to ai.market; frontend calls POST AIM Data /api/marketplace/publish, which signs and calls POST ai.market /api/v1/vz/publish"
  argument_sourcing:
    vz_dataset_id: current AIM Data dataset id
    listing_fields: approvedMetadataDraft and Step 3 form
    source_identity: authenticated AIM Data user plus serial.json.ai_market_seller_id
    install_id: serial.json.vz_install_id or POST /api/v1/vz/register response
    signing_key: local DeviceCrypto Ed25519 private key; never exported
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: "ai.market upserts by seller_id + vz_raw_listing_id (the AIM Data dataset id); every retry uses a fresh JWT jti"
  expected_success:
    shape: "HTTP 201 {status: accepted, seller_id, install_id, listing_id, vz_raw_listing_id, marketplace_url}; canonical listings row status is published"
    verification: "Open marketplace_url and confirm the title/seller; confirm AIM Data persisted dataset.listing_id; S1219 verified disclosure checked and Publish clicked in real Chrome"
  expected_failures:
    - signature: "HTTP 409 VZ install registration not available — sign in with ai.market and try publishing again"
      cause: "Registration did not produce/persist an install id (§F-02)"
    - signature: "HTTP 403 detail.error=capability_required capability=seller"
      cause: "Seller is provisioned but not active; use missing_steps (§F-04)"
    - signature: "HTTP 503 Publish unavailable: security services offline"
      cause: "Backend Redis replay/rate-limit dependency unavailable; fail-closed by design (§F-05)"
  next_step_success: Continue to E-04 and verify the live listing plus disclosure completion.
  next_step_failure: Preserve the response detail and route through §F; never fall back to a website or alternate publish endpoint.
- id: E-04
  trigger: Publish returned a listing id and the operator must prove that the customer journey reached a live listing.
  pre_conditions:
    - E-03 returned listing_id and marketplace_url
    - no production customer or money-path mutation will be performed without Max approval
  tool_or_endpoint: "Submit the checked AIM Data seller journey job script to kd-browser at http://127.0.0.1:8790 through shell_request; read the returned job artifact and live marketplace_url"
  argument_sourcing:
    job_script: checked seller-publish journey script in the operator browser-job workspace
    marketplace_url: E-03 response
    browser_profile: approved authenticated AIM Data test profile; credentials are not script arguments
  idempotency: IDEMPOTENT
  expected_success:
    shape: "Browser artifact records sign-in/registration, Accept all enabled, Step 3 visible, #ai-training-disclosure-confirmation checked, Publish invoked, and marketplace_url rendering the live listing"
    verification: "Compare artifact listing title/id with the E-03 response and canonical listing; S1219 real-Chrome verification covered Accept all, Step 3, checkbox, and Publish"
  expected_failures:
    - signature: "Listing published, disclosure snapshot pending"
      cause: "Publish succeeded but the follow-up disclosure snapshot did not complete (§F-06)"
    - signature: "runner/job failure before the Publish request"
      cause: "Harness/browser problem; isolate from product failure using e2e-browser-runner.md"
  next_step_success: Journey complete; supply the listing URL to the seller and update lifecycle evidence when this is a refresh run.
  next_step_failure: Separate browser-runner failures from product failures; for snapshot pending use §G-05 without republishing.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `POST /api/v1/vz/register` returns 500 for a non-seller, with Postgres `operator does not exist: userrole <> character varying` | **RESOLVED, T-2026-000256.** `users.role` is a Postgres `userrole` enum while the ORM maps it as String; bare strings in `User.role.not_in(("seller", "admin"))` produced enum-varchar comparison operators. Backend main `dfd926ec` contains explicit `USERROLE_ENUM` casts. | Confirm deployed backend contains `app/routers/vz_publish.py` casts in both `role.not_in` literals and the role assignment; run `tests/integration/test_vz_register_role_promotion.py`; live reference is HTTP 201 for a buyer-role account on 2026-07-14. | §G-01 | CONFIRMED |
| F-02 | AIM Data Publish returns 409 `VZ install registration not available — sign in with ai.market and try publishing again` | Registration failed or timed out, auth failed, or its success response did not persist `serial.json.vz_install_id`. In S1219 this was downstream of F-01, not an independent publish defect. | Read the immediately preceding AIM Data registration log and the `POST /api/v1/vz/register` status; inspect only whether `serial.json.vz_install_id` is present; do not expose the bearer/install token. If register was 500 with enum error, diagnose F-01 first. | §G-04 | CONFIRMED |
| F-03 | Listing metadata is present but `Accept all & continue` stays disabled, Step 3 never unlocks, and no Publish action becomes available | **RESOLVED, T-2026-000251.** No draft listing id was ever created in this flow, but the button was guarded by `!draftListingId`; persisted listing metadata was also not surfaced on reload. AIM Data `2430bb9` removes the guard and rehydrates metadata/privacy state. | Confirm dataset is `preview_ready`, title/description are non-empty, `dataset.listing_id` is null, and the deployed `DatasetDetail.tsx` button no longer checks `draftListingId`; run `DatasetDetail.test.tsx`. S1219 real Chrome against a13d9a4 reached Accept all, Step 3, disclosure confirmation, and Publish. | §G-02 | CONFIRMED |
| F-04 | Canonical publish returns 403 with `detail.error=capability_required`, `capability=seller`, and one or more `missing_steps` | Registration provisioned seller role, but effective seller readiness is not active. Common missing steps are `profile_name`, `company_name`, `totp_enabled`, and `stripe_payouts_live`; suspended/not-requested states also fail closed. | Read the structured 403 detail and `missing_steps`; follow `account-capability-onboarding.md`. Verify the durable `users.stripe_payouts_enabled` signal rather than inferring readiness from role or a transient Stripe response. | §G-03 | CONFIRMED |
| F-05 | Registration/publish returns 401/403, or publish returns 503 `security services offline` | Expired/missing seller bearer for registration; invalid EdDSA publish JWT/body hash; revoked install; or Redis replay/rate-limit service unavailable. | Separate the hop: inspect AIM Data register status, then signed `/api/v1/vz/publish` status. For 503, verify backend Redis health; for auth failures, inspect token expiry/install active state without printing secrets. | §G-04 | CONFIRMED |
| F-06 | The listing URL exists but AIM Data shows `Listing published, disclosure snapshot pending` or `Disclosure status unknown` | Canonical publish succeeded; the distinct follow-up disclosure-snapshot request failed, or ai.market accepted it but AIM Data failed to persist the local audit record. | Preserve `publishedListingId` and `retrySnapshotPayload`; open the listing URL to prove publish succeeded; inspect only the disclosure-snapshot response. Do not call Publish again. | §G-05 | CONFIRMED |

Read the exact first failing hop. A UI failure before `/api/marketplace/publish`, an AIM Data registration failure, a signed-receiver failure, and a post-publish disclosure failure have different owners and must not be collapsed into “publish broken.”

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: ai.market registration receiver
  root_cause: "The registration seller-provisioning predicate compared a Postgres userrole enum column to VARCHAR parameters, so non-seller registration failed before install creation."
  repair_entry_point: ai-market-backend/app/routers/vz_publish.py:register_install
  change_pattern: "Keep USERROLE_ENUM(create_type=False) and cast both seller/admin literals inside User.role.not_in plus the seller assignment to that enum. Preserve admin exclusion and onboarding completion. Do not rename the public route; it remains POST /api/v1/vz/register. Backend main dfd926ec is the known-good implementation."
  rollback_procedure: "Revert only the regressing change and redeploy the last known-good backend containing dfd926ec/e4c22a88; do not roll back user records or manually edit a production customer's role without Max."
  integrity_check: "Run tests/integration/test_vz_register_role_promotion.py against real Postgres enum substrate, then verify an approved buyer-role test account receives HTTP 201 and is provisioned seller. Production customer verification requires Max."
- id: G-02
  symptom_ref: F-03
  component_ref: AIM Data listing preparation
  root_cause: "The Step 2 Accept-all button required draftListingId even though the processed-dataset journey never created that id; reload also dropped persisted listing_metadata from the dataset response."
  repair_entry_point: aim-data/frontend/src/pages/DatasetDetail.tsx:handleAcceptAllMetadata
  change_pattern: "Preserve AIM Data 2430bb9 semantics: Accept all requires generated metadata plus non-empty title/description, not draftListingId; expose record.metadata.listing_metadata from get_dataset; initialize and rehydrate metadata/privacy state; reserve draftListingId only for conversational allAI field-edit tools that actually need it. Do not create a new remote draft or alternate publish route."
  rollback_procedure: "Revert the regressing UI/API change to AIM Data 2430bb9 and rebuild the customer image; local dataset content remains intact."
  integrity_check: "Run frontend/src/pages/DatasetDetail.test.tsx and verify in a real Chrome job that a preview-ready dataset with null listing_id enables Accept all, opens Step 3, requires #ai-training-disclosure-confirmation, and exposes Publish."
- id: G-03
  symptom_ref: F-04
  component_ref: ai.market canonical publish receiver
  root_cause: "Seller identity is provisioned but effective capability is not active because a readiness step is missing, suspended, or has an unavailable durable Stripe signal."
  repair_entry_point: ai-market-backend/app/services/capability_resolver.py:CapabilityResolver.resolve
  change_pattern: "Use the structured 403 missing_steps to direct the seller through the authoritative readiness flow: profile name, company name, TOTP, then Stripe Connect payouts-live. Never bypass assert_user_capability and never mark payouts live by hand. Escalate any production customer or money-path intervention to Max."
  rollback_procedure: "No code rollback for a genuine readiness gap. If a resolver regression caused a false gap, revert that reviewed resolver change and redeploy; do not weaken the publish gate."
  integrity_check: "GET the authoritative capability view and confirm effective seller status active with no missing_steps; then retry the same vz_raw_listing_id and receive 201. Tests/test_vz_publish.py must still prove provisioning/suspended/unavailable cases return 403 without calling the writer."
- id: G-04
  symptom_ref: F-02
  component_ref: AIM Data install registration client
  root_cause: "AIM Data lacks a persisted install id because registration failed, auth expired, or the response was interrupted before local persistence; signed publish therefore has no JWT issuer id."
  repair_entry_point: aim-data/app/services/registration_service.py:ensure_vz_install_registered
  change_pattern: "Fix the upstream registration error first. Refresh/sign in through AIM Data to obtain a current seller bearer, let ensure_vz_install_registered call POST /api/v1/vz/register, and persist the returned install_id. Keep credentials in serial.json/keystore. Do not invent /register-install, insert vz_installs manually, or bypass registration."
  rollback_procedure: "If a client regression caused the failure, redeploy the last known-good AIM Data image at 2430bb9; preserve serial.json and keystore volumes. Never delete production install state without Max."
  integrity_check: "Redacted logs show register 201/accepted recovery; serial.json has a non-empty vz_install_id; a retry reaches the signed /api/v1/vz/publish hop. Also run aim-data/tests/test_vz_publish_proxy.py."
- id: G-05
  symptom_ref: F-06
  component_ref: AIM Data listing preparation
  root_cause: "The canonical listing publish committed, but the follow-up disclosure snapshot request or local disclosure audit persistence did not complete."
  repair_entry_point: aim-data/frontend/src/pages/DatasetDetail.tsx:handleRetryDisclosureSnapshot
  change_pattern: "Use Retry disclosure snapshot with the stored publishedListingId and retrySnapshotPayload. This calls only the disclosure endpoint. Do not invoke marketplaceApi.publish again and do not create a second listing. If status is unknown, reconcile the server snapshot before another retry."
  rollback_procedure: "No listing rollback is implied; leave the live listing intact. If disclosure must be withdrawn, use the authoritative disclosure/listing management procedure with Max when customer-visible or money-adjacent."
  integrity_check: "A retry returns disclosure_version, local publishStatus becomes complete, and the marketplace listing id remains unchanged. tests/test_s804_disclosure_dataset_detail.py must prove retry does not call marketplaceApi.publish."
```

## §H. Evolve

Evaluate predicates in order; the first match wins.

### §H.1 Invariants

- The customer begins this journey from a signed-in AIM Data install; the website never creates or publishes listings.
- The install-registration route is exactly `POST /api/v1/vz/register`. Registration is the act of provisioning the authenticated caller as seller; it is not named `/register-install`.
- Registration never implies publish readiness. Every publish must pass `assert_user_capability(..., "seller", "active")`; Stripe payouts-live remains part of active readiness.
- AIM Data's Step 1/2 pre-publish draft is local dataset metadata and approval state. It must not require a remote listing id, create a second listing store, or add a draft publish endpoint.
- The Publish action remains disabled until reviewed metadata exists and the seller explicitly checks `ai-training-disclosure-confirmation`.
- The Ed25519 private key never leaves the AIM Data install. The signed JWT binds seller id, install id, action, exact payload hash, expiry, issued-at, and a fresh replay id.
- Every live listing creation/update terminates at the signed, active-seller-gated `POST /api/v1/vz/publish` route and canonical `listings` table. See `publish-paths.md` for the system-wide one-route/one-gate invariant.
- Raw customer data is not sent in the publish payload; only approved listing metadata, schema/trust signals, delivery references, and explicitly approved disclosure material traverse the appropriate endpoints.
- A successful publish returns and locally persists the canonical listing id; a disclosure retry never republishes the listing.
- Any operation touching the money path or a production customer account escalates to Max before mutation.

### §H.2 BREAKING predicates

- Changes any §H.1 invariant.
- Adds or changes a public route/response contract without a backwards-compatible shim, including renaming `/api/v1/vz/register` or adding another publish endpoint.
- Changes the seller/install auth boundary, weakens the active-seller gate, exports the signing key, or changes scope semantics for existing callers.
- Removes a field, changes a field type, or adds a required field without a default in the public registration/publish/disclosure contracts or their persisted cross-repo state.

### §H.3 REVIEW predicates

- Adds a feature to the existing sign-in, registration, listing-preparation, disclosure, or publish surfaces after all BREAKING predicates fail.
- Moves functions across the source-root module boundaries defined in §H.5 or changes more than one repository in this journey.
- Changes a config default in an authoritative config file or adds a runtime dependency.
- Changes retry/idempotency behavior, browser job checkpoints, metadata approval transitions, or registration timing without changing a public contract.

### §H.4 SAFE predicates

- Fixes a bug within existing semantics and within one module, preserving all public signatures and §H.1 invariants.
- Adds tests, browser-job assertions, or documentation without changing runtime behavior.
- Refactors within one module while preserving registration, state-transition, signing, gate, and response contracts.

### §H.5 Boundary definitions

#### module

This is a multi-repository journey. A module is an immediate subdirectory of an applicable source root: AIM Data `app/` (`routers/`, `services/`, `models/`, `core/`) or `frontend/src/` (`pages/`, `components/`, `lib/`), and ai-market-backend `app/` (`routers/`, `services/`, `api/`, `models/`, `schemas/`). Tests and migrations are peer trees, not runtime modules. Moving work between AIM Data and ai-market-backend is always REVIEW after BREAKING predicates fail.

#### public contract

The AIM Data sign-in/publish HTTP endpoints, ai.market `/api/v1/vz/register` and `/api/v1/vz/publish` OpenAPI schemas/status/error shapes, the disclosure endpoint, persisted cross-repo identifier meanings (`seller_id`, `install_id`, `vz_raw_listing_id`, `listing_id`), and the customer-visible Step 1–3 transition/confirmation contract. The checkbox id is a stable browser-verification selector.

#### runtime dependency

Any production dependency entry in either Python project's `requirements*.txt` or `pyproject.toml [project.dependencies]`, or AIM Data frontend `package.json.dependencies`. Dev/test/optional dependencies are not runtime dependencies.

#### config default

A shipped default in AIM Data `app/config.py` or ai-market-backend's canonical settings/config modules. Environment overrides, feature flags, browser job parameters, and test-only overrides are not config defaults.

### §H.6 Adjudication

If agents disagree, the more restrictive classification wins. Unresolved disputes, and every question involving the money path or production customer accounts, escalate to Max; record the ruling as a §H.1 clarification in the same change.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs:
      - E-01
    scenario: A buyer-role ai.market user signs in to a serial-backed AIM Data install for the first time. What is the first registration endpoint and argument set?
    expected_answers:
      - kind: tool_call
        tool: POST_/api/v1/vz/register
        argument_keys:
          - public_key_b64
          - serial
          - serial_install_token
    weight: 0.0909090909
  - id: I-02
    type: operate
    refs:
      - E-02
    scenario: A preview-ready dataset has completed privacy review. What call begins seller-facing listing metadata preparation?
    expected_answers:
      - kind: tool_call
        tool: POST_/api/datasets/{dataset_id}/listing-metadata
        argument_keys:
          - dataset_id
    weight: 0.0909090909
  - id: I-03
    type: operate
    refs:
      - E-03
    scenario: The seller is on Step 3 with reviewed metadata and a valid price, but Publish is disabled. What is the first customer action?
    expected_answers:
      - kind: human_action
        verb: check
        object: ai-training-disclosure-confirmation checkbox
        target: AIM Data Step 3
    weight: 0.0909090909
  - id: I-04
    type: isolate
    refs:
      - F-01
    scenario: A non-seller registration returns 500 with userrole <> character varying. What is the first verification?
    expected_answers:
      - kind: tool_call
        tool: inspect_vz_register_enum_casts
        argument_keys:
          - deployed_commit
          - route
    weight: 0.0909090909
  - id: I-05
    type: isolate
    refs:
      - F-02
    scenario: Publish returns 409 VZ install registration not available immediately after sign-in. What is the first diagnostic action?
    expected_answers:
      - kind: tool_call
        tool: inspect_preceding_vz_register_response
        argument_keys:
          - install_log
          - register_route
    weight: 0.0909090909
  - id: I-06
    type: isolate
    refs:
      - F-04
    scenario: Signed publish returns capability_required with missing_steps containing stripe_payouts_live. What is the first action?
    expected_answers:
      - kind: human_action
        verb: direct
        object: seller to complete Stripe Connect payouts-live readiness
        target: account-capability-onboarding.md procedure; Max for production customer or money path
    weight: 0.0909090909
  - id: I-07
    type: repair
    refs:
      - G-01
    scenario: A code regression removed enum casts from VZ registration. State the first repair target.
    expected_answers:
      - kind: human_action
        verb: restore
        object: USERROLE_ENUM casts in role.not_in literals and seller assignment
        target: ai-market-backend/app/routers/vz_publish.py:register_install
    weight: 0.0909090909
  - id: I-08
    type: repair
    refs:
      - G-02
    scenario: Accept all again requires a null draft listing id. State the first repair target without introducing another listing path.
    expected_answers:
      - kind: human_action
        verb: remove
        object: draftListingId dependency from Accept-all enablement and preserve metadata rehydration
        target: aim-data/frontend/src/pages/DatasetDetail.tsx:handleAcceptAllMetadata
    weight: 0.0909090909
  - id: I-09
    type: evolve
    refs:
      - §H.2
    scenario: A proposal adds POST /api/v1/aim-data/publish so AIM Data can bypass the VZ route. Classify it.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.0909090909
  - id: I-10
    type: evolve
    refs:
      - §H.4
    scenario: A proposal adds a unit test that asserts Accept all works when listing_id is null, with no production code change. Classify it.
    expected_answers:
      - kind: classification
        label: SAFE
    weight: 0.0909090909
  - id: I-11
    type: ambiguous
    refs:
      - F-02
      - F-05
    scenario: Publish says registration is unavailable, but you do not yet know whether sign-in auth, backend registration, or local persistence failed. Name a correct first-action set.
    expected_answers:
      - kind: tool_call
        tool: inspect_preceding_vz_register_response
        argument_keys:
          - install_log
          - register_route
      - kind: tool_call
        tool: inspect_redacted_local_registration_state
        argument_keys:
          - vz_install_id_presence
          - ai_market_seller_id_presence
    weight: 0.0909090909
```

The scenario set uses equal weights (1/11 each, within linter tolerance) and passes at a weighted score of at least 0.80. The expected-answer key must receive independent MP + AG concurrence before promotion into a hidden/external harness set.

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1220
last_refresh_commit: 5f968f1
last_refresh_date: 2026-07-14T19:17:29Z
owner_agent: mars
refresh_triggers:
  - any AIM Data sign-in, registration, listing-preparation, disclosure, or publish contract change
  - any ai-market-backend /api/v1/vz/register or /api/v1/vz/publish change
  - any seller-readiness or Stripe payouts-live gate change
  - incident or ticket in this end-to-end customer journey
  - new real-browser verification result or regression
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-07-14T19:17:29Z
first_staleness_detected_at: null
```

Source commits captured by this lifecycle refresh: AIM Data `2430bb9`, ai-market-backend `dfd926ec`, and runbooks base `5f968f1`. §B evidence is current to 2026-07-14, so no row carries the `UNVERIFIED` overlay.

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1220 / 2026-07-14T19:24:21Z
last_lint_result: PASS
retrofit: false
trace_matrix_path: null
word_count_delta: null
```

Conformance intent: all §A–§K sections appear once and in order; §B–§D and §F use the exact prescribed columns; §E, §G, §I, §J, and §K use their single fenced YAML agent forms; §H uses the required predicate subsections and boundary definitions; every §F repair reference, §G symptom reference, and §G component reference resolves; the 11 equal weights sum to 1.0 within tolerance and meet the required distribution. This is a new runbook, not a retrofit, so trace-matrix and word-count-delta fields are null.
