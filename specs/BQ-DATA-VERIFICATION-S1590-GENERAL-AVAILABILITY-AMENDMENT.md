# BQ-DATA-VERIFICATION-S1590 general-availability amendment

**Status:** Specification candidate only. It authorizes no code change, configuration change, deployment, Stripe action, or production mutation until the review and rollout gates below pass.

**Build Queue entity:** `build:bq-data-verification-s1590`

**Authority:** Max decision S1652, Event Ledger `7966c74c-320f-436c-a874-8190c4953c51`: “The paid verification service will be available to all sellers.”

**Parent authorities:** [Gate 1](BQ-DATA-VERIFICATION-S1590-GATE1.md), [Gate 2](BQ-DATA-VERIFICATION-S1590-GATE2.md), and the [S1646 pay-in onboarding amendment](BQ-DATA-VERIFICATION-S1590-PAYIN-ONBOARDING-AMENDMENT.md).

**Source trace:** `ai-market-backend@31efd4c607ace06319bbbbc697834584952f7ed9`, `ai-market-frontend@97051799a9c4ecd209e94b9ea0ea456fed5142c5`, and `aim-data@0660c106f04addf641dcb2684d6af2804f6b0435`. Citations below are to those exact checkouts.

## 1. Decision and amendment boundary

S1652 retires the single-party restriction in the pay-in amendment. Every seller may use the paid verification service when the existing caller eligibility checks and the two independent server-side feature gates pass.

For seller availability, this decision supersedes the pilot-only statements in the pay-in amendment, including its single-party product boundary, configuration, tests, rollout, and non-goals (`specs/BQ-DATA-VERIFICATION-S1590-PAYIN-ONBOARDING-AMENDMENT.md:21`, `:54`, `:73-81`, `:498-499`, `:527-534`, and `:552`). It also supersedes older Gate 1 and Gate 2 wording only where that wording would retain a named-party or known-counterparty seller restriction (`specs/BQ-DATA-VERIFICATION-S1590-GATE1.md:106`, `:343`; `specs/BQ-DATA-VERIFICATION-S1590-GATE2.md:421`, `:429`). It does not widen the connector, scan manifest, payment state machine, publication contract, attestation claim, or any privacy boundary.

This is a seller-availability amendment, not a second data-verification gate. The data-verification service already checks only `DATA_VERIFICATION_ENABLED`; neither its service projection nor its API gate contains a party allowlist (`ai-market-backend:app/services/data_verification_service.py:106-114`; `ai-market-backend:app/api/v1/endpoints/data_verification.py:52-58`). Reviewers must not add a second seller allowlist there.

## 2. Required backend change

### 2.1 Retire the pilot setting

Remove `STRIPE_PAYIN_ONBOARDING_PILOT_PARTY_IDS` from `Settings`; do not keep it as an empty, optional, deprecated, compatibility, or emergency restriction. The current setting sits beside the independent onboarding flag and platform-account pin (`ai-market-backend:app/core/config.py:228-233`).

Delete the complete `stripe_payin_pilot_party_ids` parser and its canonical/duplicate UUID rules (`ai-market-backend:app/core/config.py:642-662`). Delete only the exactly-one-pilot branch from `validate_stripe_payin_onboarding` (`ai-market-backend:app/core/config.py:874-885`).

The validator must retain all other fail-closed behavior unchanged:

- when onboarding is off, validation returns without enabling any surface (`ai-market-backend:app/core/config.py:875-879`);
- when onboarding is on, `STRIPE_PAYIN_PLATFORM_ACCOUNT_ID` remains required in canonical `acct_` form (`ai-market-backend:app/core/config.py:886-891`); and
- `FRONTEND_URL` remains one canonical approved origin, with production fixed to `https://ai.market` and only the existing test/staging exceptions (`ai-market-backend:app/core/config.py:893-928`).

No replacement seller-list, organization-list, rollout percentage, request override, or Stripe-derived eligibility setting is authorized.

### 2.2 Make the pay-in surface gate party-independent

Replace `payin_surface_enabled_for_party` with a party-independent surface gate. Its complete result is:

```text
STRIPE_PAYIN_ONBOARDING_ENABLED is true
AND STRIPE_PAYIN_PLATFORM_ACCOUNT_ID is a pinned canonical acct_ identifier
```

The current function also parses and compares a party UUID; those branches are removed (`ai-market-backend:app/services/data_verification_payin_service.py:307-321`). The gate must accept no party, user, organization, listing, or caller-supplied identifier. Runtime absence or invalidity of either remaining condition returns unavailable before readiness, attempt, audit, or Stripe work.

The three endpoint operations continue to call the same shared eligibility path before readiness, setup-session creation, or reconciliation (`ai-market-backend:app/api/v1/endpoints/data_verification_payin.py:105-127`, `:134-153`, `:163-185`). Eligibility remains all of:

- a signed-in application session;
- current seller-provisioning permission;
- `totp_enabled=true`; and
- exactly one active, undeleted `auth_user` `PartyIdentity` mapping the authenticated user to the party.

The current checks and actor resolution are at `ai-market-backend:app/api/v1/endpoints/data_verification_payin.py:38-66` and `ai-market-backend:app/services/data_verification_payin_service.py:360-376`. The server still derives user and party; the request supplies neither.

Every unavailable or ineligible caller receives the same HTTP 404 body with code `PAYIN_ONBOARDING_DISABLED`, with no readiness, attempt, audit, or Stripe work. This includes signed-out, non-seller, no-TOTP, ambiguous/missing actor, flag-off, and missing/invalid platform-account cases. The current checkout still has 401/403 branches for session and TOTP and therefore must be normalized to this contract during implementation (`ai-market-backend:app/api/v1/endpoints/data_verification_payin.py:44-69`). No response may disclose which check failed.

### 2.3 Preserve party ownership and isolation

General availability changes who may begin; it does not weaken party scoping. Readiness continues to load ordinary identities and the current setup attempt only for the derived party (`ai-market-backend:app/services/data_verification_payin_service.py:393-416`, `:1132-1159`). Return reconciliation continues to compare both stored user and party with the derived actor and returns not found on either mismatch (`ai-market-backend:app/services/data_verification_payin_service.py:766-816`).

Party A must never read Party B's readiness, current attempt, Checkout binding, payment-method mapping, or audit result, and must never reconcile, replace, supersede, or finalize Party B's attempt.

## 3. Frontend and AIM Data impact

There is no pilot decision in frontend behavior. `api/dataVerificationPayin.ts` treats an unavailable response generically and does not inspect party identity or the `PAYIN_ONBOARDING_DISABLED` body (`ai-market-frontend:api/dataVerificationPayin.ts:158-166`). `DataVerificationPaymentMethod.tsx` hides the dedicated surface on the generic unavailable result for readiness, creation, and reconciliation (`ai-market-frontend:components/DataVerificationPaymentMethod.tsx:150-205`, `:227-265`, `:290-304`).

Required `ai-market-frontend` production behavior change: none. Replace only the stale comment text `disabled/non-pilot` with party-neutral wording in `api/dataVerificationPayin.ts:163-165`. No existing frontend test name or assertion mentions a pilot; keep the generic 404 hiding coverage (`ai-market-frontend:api/dataVerificationPayin.test.ts:223-224`; `ai-market-frontend:app/dashboard/data-verification/payment-method/page.test.tsx:327-346`; `ai-market-frontend:app/dashboard/data-verification/payment-method/return/page.test.tsx:518-575`).

Required `aim-data` frontend change: none. `DataVerificationFlow.tsx` has no pilot logic. It asks for a quote, requires both acknowledgements, and calls the paid start only after the seller's explicit action (`aim-data:frontend/src/components/DataVerificationFlow.tsx:226-256`, `:385-435`). Its API schema carries only party-neutral setup state and URL fields (`aim-data:frontend/src/lib/api.ts:340-352`, `:378-392`). The existing test proves card setup is absent before explicit paid start and appears only after the server returns `setup_required` (`aim-data:frontend/src/components/DataVerificationFlow.test.tsx:168-191`).

General Settings remains free of proactive card controls; the current test makes that boundary explicit (`ai-market-frontend:app/dashboard/settings/page.test.tsx:104-111`). The dedicated payment-method route is reachable only through the accepted-quote, explicit-paid-start handoff.

## 4. Test replacement

The S1590-scoped grep for `PILOT_PARTY_IDS` or `pilot` finds exactly-one-pilot assumptions only in `tests/test_data_verification_payin_readiness.py`:

- `_enabled_settings` requires the pilot variable, and the invalid-configuration table rejects empty, malformed, duplicate, and multiple pilot values (`ai-market-backend:tests/test_data_verification_payin_readiness.py:25-59`);
- the defaults test asserts an empty pilot variable (`ai-market-backend:tests/test_data_verification_payin_readiness.py:62-67`);
- `test_surface_gate_is_exactly_one_pilot_and_runtime_invalid_is_indistinguishable` compares the caller party with the one configured UUID (`ai-market-backend:tests/test_data_verification_payin_readiness.py:103-120`); and
- `test_nonpilot_gate_precedes_loader_attempt_audit_and_stripe` names pilot exclusion (`ai-market-backend:tests/test_data_verification_payin_readiness.py:184-200`).

Delete or rewrite those pilot assertions. Replacement coverage is binding:

1. flag off returns 404 `PAYIN_ONBOARDING_DISABLED` before loader, attempt, audit, or Stripe work;
2. onboarding flag on with missing or malformed platform account fails startup closed, and a runtime-invalid/missing pin returns the same 404 before provider work;
3. with both surface conditions valid, two different eligible seller parties each reach readiness and may create their own setup attempt; no configured party list exists;
4. signed-out, missing seller-provisioning permission, no-TOTP, missing actor, and ambiguous actor each return the same 404 and do no protected work;
5. readiness for Party A cannot observe Party B's identity or current attempt;
6. Party A cannot reconcile or act on Party B's setup attempt or Checkout Session, and the response remains not found; and
7. the existing real cross-party identity-conflict test remains fail-closed (`ai-market-backend:tests/test_data_verification_payin_postgres.py:701-750`).

All non-pilot terminology must disappear from S1590 pay-in production comments and tests. Unrelated pilots in other product areas are out of scope.

## 5. Binding invariants that do not change

- **Just-in-time card boundary:** a card is requested only after an accepted quote and explicit paid start. General Settings has no proactive add/manage-card control (`aim-data:frontend/src/components/DataVerificationFlow.tsx:385-435`; `ai-market-frontend:app/dashboard/settings/page.test.tsx:104-111`).
- **Pay-in is not payout:** the application default remains exactly one primary ordinary `provider="stripe"` identity with canonical `cus_` and one-key canonical `pm_` metadata; the ordinary-identity query excludes `stripe_connect`, so a Connect `acct_` is never reused (`ai-market-backend:app/services/data_verification_payment_service.py:159-178`; `ai-market-backend:app/services/data_verification_payin_service.py:1132-1147`).
- **No raw customer data at ai.market:** accepted reports remain frozen, extra-field-forbidden schemas with the exhaustive approved manifest, and raw values, samples, locators, credentials, queries, and data-plane payloads remain prohibited (`ai-market-backend:app/schemas/data_verification.py:109-110`, `:587-624`, `:783-810`).
- **Webhook integrity:** Stripe signature verification remains before dispatch, and durable event dedupe remains atomic with handler completion; critical failure rolls back so the provider retry can run (`ai-market-backend:app/api/v1/endpoints/webhooks.py:108-137`, `:303-375`, `:580-618`).
- **Idempotent single start:** the seller/idempotency binding continues to converge on one verification epoch and one manual authorization key; retries return the existing nonterminal epoch rather than creating a second start (`ai-market-backend:app/services/data_verification_payment_service.py:595-616`, `:647-710`).
- **Rollback without deletion:** disable `DATA_VERIFICATION_ENABLED` first and `STRIPE_PAYIN_ONBOARDING_ENABLED` second. Do not delete or detach any Customer, payment method, setup attempt, verification epoch, Stripe event, or Connect identity (`specs/BQ-DATA-VERIFICATION-S1590-PAYIN-ONBOARDING-AMENDMENT.md:534`).

## 6. Production rollout

S1652 reconciliation records production with `DATA_VERIFICATION_ENABLED=true`, `STRIPE_PAYIN_ONBOARDING_ENABLED=true`, and one party in `STRIPE_PAYIN_ONBOARDING_PILOT_PARTY_IDS`. Use this order:

1. Merge and deploy the reviewed backend change that removes and no longer reads the allowlist setting. Do not delete the Railway variable first, because the current validator requires exactly one UUID when onboarding is enabled (`ai-market-backend:app/core/config.py:875-891`).
2. Prove the deployed artifact ignores/removes the allowlist and retains the platform-account and canonical-origin startup checks.
3. Delete the Railway variable `STRIPE_PAYIN_ONBOARDING_PILOT_PARTY_IDS`.
4. In normal signed-in Chrome, use one authorized eligible seller that was not the former pilot. Prove the payment-method surface is reachable only after the paid-service handoff: completed quote acknowledgements followed by explicit paid start.
5. In signed-out Chrome and with a signed-in non-seller identity, prove the same surface and endpoints return 404 without eligibility detail.
6. Confirm no proactive card control appears in Settings, no cross-party object is visible or mutable, no raw customer data crossed, and no Connect payout identity changed.

Rollback remains the binding order in section 5. Removing the new code or disabling either flag must not delete customer, Stripe, attempt, epoch, webhook, or identity records.

## 7. Acceptance criteria

**AC1.** A repository search finds no `STRIPE_PAYIN_ONBOARDING_PILOT_PARTY_IDS`, `stripe_payin_pilot_party_ids`, or S1590 pay-in pilot branch in backend production code.

**AC2.** With onboarding on, a canonical platform account, and an approved canonical origin, startup succeeds without any seller allowlist variable; malformed platform account or origin still fails startup.

**AC3.** Flag-off and runtime-missing/invalid platform-account cases return identical 404 `PAYIN_ONBOARDING_DISABLED` responses before readiness, persistence, audit, or Stripe calls.

**AC4.** Two distinct eligible seller parties independently receive readiness and may create isolated setup attempts under the same deployment configuration.

**AC5.** Signed-out, non-seller, no-TOTP, missing-actor, and ambiguous-actor cases each return the same 404 without protected work or eligibility disclosure.

**AC6.** Party A cannot read readiness derived from Party B or read, reconcile, replace, supersede, or finalize Party B's setup attempt; every attempted cross-party action is a not-found result and changes nothing.

**AC7.** `DATA_VERIFICATION_ENABLED` remains the only data-verification service gate; no second party allowlist is added to its service, endpoint, frontend, or AIM Data paths.

**AC8.** `ai-market-frontend` behavior is unchanged, its one `disabled/non-pilot` comment is party-neutral, and generic unavailable-response tests pass. `aim-data` requires no production or test wording change.

**AC9.** Browser and component tests prove the S1646 just-in-time boundary: no Settings card control, no card prompt before quote acceptance and explicit paid start, and the handoff appears only after the server requests setup.

**AC10.** Ordinary pay-in identity, Connect separation, no-raw-data schemas, webhook signature/dedupe, and idempotent-start regression suites remain green.

**AC11.** Deployment occurs before Railway variable deletion, the deployed process starts without the variable, and configuration evidence proves the variable is absent afterward.

**AC12.** Signed-in Chrome proof from one eligible former non-pilot seller reaches the setup surface only through the paid-service handoff; signed-out and non-seller Chrome proof receives 404.

**AC13.** Rollback rehearsal disables data verification first and onboarding second and proves no customer, Stripe, attempt, epoch, event, payment-method, or Connect record was deleted or detached.

**AC14.** This exact spec SHA and every later implementation SHA each receive unanimous CORE S3 payments approval from CC, GLM, and DeepSeek before build dispatch, merge/deployment, or production configuration change.

## 8. Council review checklist

- [ ] Review the exact spec or implementation SHA; any edit invalidates the verdict.
- [ ] CC, GLM, and DeepSeek each record model identity, verdict, mandates, and immutable evidence reference.
- [ ] Confirm the allowlist is removed rather than made optional or relocated.
- [ ] Confirm caller-ineligibility responses are indistinguishable 404s and cross-party isolation is unchanged.
- [ ] Confirm platform-account pinning, canonical origin, JIT card setup, Connect separation, privacy, webhook, idempotency, and rollback invariants remain binding.
- [ ] Record unanimous approval; any dissent or missing reviewer blocks the payments change.
