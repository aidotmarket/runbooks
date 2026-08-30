---
title: Stripe Connect Identity Bridge
owner: vulcan
last_verified: '2026-08-07'
aliases:
- connect-identity-bridge
- seller-stripe-linkage
error_signatures:
- kyc_status_absent_defaults_not_started
- seller_profiles_connect_id_never_written
- stripe_connect_user_update_zero_rows
- two_connect_onboarding_endpoints_disagree
- webhook_predicate_column_mismatch
---

# Stripe Connect Identity Bridge

## Overview


**Why this runbook exists.** On 2026-08-07 our first real seller was found to be live at
Stripe with payouts enabled while our own seller record said his verification had not
started. The diagnosis took two sessions and two operators because no document said which
of our stores was supposed to be right. This runbook is that document. Ticket:
T-2026-000572.

### M1 — Dependencies & Credentials / Source-of-Truth

| Dependency | What it provides | Where the credential lives | Owning service |
|---|---|---|---|
| Stripe Connect API | The only external authority on whether an account is live, has submitted details, and can receive payouts | `STRIPE_*` in Infisical `ai-market-backend`/prod (see `infisical-secrets.md`) | Payments |
| ai.market Postgres | `users`, `seller_profiles`, `party_identity` — the three tables that each hold a copy of the Connect fact | `DATABASE_URL`, Infisical env `ops` (see `infisical-secrets.md`) | ai.market backend |
| Stripe webhook `account.updated` | The push channel that keeps our copies in step with Stripe | Endpoint secret in Infisical | ai.market backend |

---

## Capabilities

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Connect account id resolved for checkout and payment routing, read from `party_identity` | SHIPPED | `app/api/v1/endpoints/checkout.py` | — | 2026-08-07 |
| Connect status shown on seller surfaces, read from `party_identity` | SHIPPED | `app/api/v1/endpoints/stripe_connect.py` | — | 2026-08-07 |
| KYC gate on data requests and proposals, read from `party_identity` metadata | SHIPPED | `app/api/deps.py` | — | 2026-08-07 |
| `account.updated` users leg | SHIPPED | `app/api/v1/endpoints/webhooks.py` | — | 2026-08-07 |
| `account.updated` seller_profiles leg — filters a column no live writer populates | BROKEN | `app/api/v1/endpoints/webhooks.py` | — | 2026-08-07 |
| `seller_profiles.stripe_connect_id` populated on any live onboarding path | BROKEN | — | — | 2026-08-07 |

---

## Architecture & interactions

### C.1 The Connect fact is stored in four places

| # | Store | Column or shape | Written by | Read by |
|---|---|---|---|---|
| 1 | `users` | `stripe_account_id`, plus `stripe_payouts_enabled`, `stripe_onboarding_complete`, `stripe_details_submitted` | `stripe_connect.py:159`; `webhooks.py:641-658` | `webhooks.py:649,670`; capability resolver reads `users.stripe_payouts_enabled` |
| 2 | `seller_profiles` | `stripe_account_id`, `stripe_charges_enabled`, `stripe_payouts_enabled`, `stripe_onboarding_complete`, `kyc_status` | `stripe.py:249-258` and `stripe.py:354-368` only | `profiles.py:45,294`; `stripe.py:205,293,336` |
| 3 | `seller_profiles` | `stripe_connect_id`, `stripe_connect_status`, `payout_enabled`, `kyc_verified_at` | NOTHING in `app/`. Only `alembic/versions/000_initial.py` (schema) and `scripts/setup_demo_stripe.py:186` (demo seed) | `webhooks.py:202,691,704,1501` |
| 4 | `party_identity` | `provider='stripe_connect'`, `external_id=acct_...`, metadata `{source, onboarding_status, payouts_enabled, details_submitted, kyc_status, kyc_verified_at}` | `upsert_stripe_connect_identity` via bridges in `stripe_connect.py`, `stripe.py`, `webhooks.py` | `checkout.py:69`, `deps.py:838`, `seller.py:204`, `profiles.py:140`, `stripe.py:212,297,344` |

**Store 4 is the de facto authority.** Every customer-visible read — checkout, seller
status, the KYC gate — resolves through `party_identity`. Stores 1 to 3 are legacy
copies. Store 3 has readers and no writer.

### C.2 There are two Connect onboarding endpoints and they write different stores

| Endpoint file | Writes `users.stripe_account_id` | Writes `seller_profiles.stripe_account_id` | Writes `seller_profiles.stripe_connect_id` | Writes `party_identity` |
|---|---|---|---|---|
| `app/api/v1/endpoints/stripe_connect.py` (current path) | yes (`:159`) | no | no | yes (`:176`) |
| `app/api/v1/endpoints/stripe.py` (legacy path) | no | yes (`:251`) | no | yes (`:265`, `:378`) |

A seller onboarded through `stripe_connect.py` therefore has both `seller_profiles`
Connect columns NULL for ever. That is not a data accident; it is the designed behaviour
of the path they used.

### C.3 `webhooks.py` disagrees with itself about which column identifies a seller

| Line | Predicate | Width |
|---|---|---|
| `:202` | `WHERE sp.stripe_connect_id = :acct OR sp.stripe_account_id = :acct` | wide |
| `:691` | `WHERE stripe_connect_id = :stripe_id` on `UPDATE seller_profiles` | narrow |
| `:704` | `WHERE stripe_connect_id = :stripe_id` on `SELECT ... FROM seller_profiles` | narrow |
| `:1501` | `WHERE stripe_connect_id = :destination OR stripe_account_id = :destination` | wide |

The two narrow predicates are the ones on the `account.updated` path. Because store 3 has
no writer, both match zero rows for every seller onboarded through the current path, and
the `seller_profiles` leg of `_handle_account_update` silently does nothing. It logs
nothing on zero rows — only the users leg has a `rowcount == 0` alarm
(`webhooks.py:659-668`).

### C.4 How the divergence stays invisible

`party_identity` metadata is merged per source. The users leg writes `source='users'` and
carries `onboarding_status`, `payouts_enabled`, `details_submitted`. The seller_profiles
leg writes `source='seller_profiles'` and is the ONLY writer of `kyc_status` and
`kyc_verified_at`. When the seller_profiles leg never fires, the identity row still looks
healthy — it simply has no `kyc_status` key. `deps.py:846` then reads
`metadata.get("kyc_status", "not_started")` and refuses the seller. A missing key and a
failed verification are indistinguishable at the reader.

---

## Agent capabilities

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| vulcan / mars | Read production Connect state | `psql` via `scripts/test-db-dsn.sh` | DSN from Infisical `ops` | COVERED (E-01) |
| vulcan / mars | Compare our copies against Stripe | Stripe API read | `STRIPE_SECRET_KEY` | COVERED (E-02) |
| vulcan / mars | Repair a divergent seller | NOT COVERED — must be reviewed code with a dry run, never hand SQL | none | GAP, owned by T-2026-000565 |

---

## How to operate

```yaml operate
- id: E-01
  name: Read every copy of the Connect fact for one seller
  when: A seller reports being connected to Stripe while a surface says otherwise, or the reverse.
  procedure: |
    DSN="$(scripts/test-db-dsn.sh)"   # from a koskadeux-mcp checkout
    psql "$DSN" -c "SELECT email, role, stripe_account_id, stripe_payouts_enabled,
                           stripe_onboarding_complete, onboarding_completed
                    FROM users WHERE email = 'SELLER_EMAIL'"
    psql "$DSN" -c "SELECT sp.stripe_connect_id, sp.stripe_account_id, sp.kyc_status,
                           sp.payout_enabled, sp.stripe_connect_status, sp.kyc_verified_at
                    FROM seller_profiles sp JOIN users u ON u.id = sp.user_id
                    WHERE u.email = 'SELLER_EMAIL'"
    psql "$DSN" -c "SELECT pi.provider, pi.external_id, pi.metadata
                    FROM party_identity pi WHERE pi.provider = 'stripe_connect'"
  expect: |
    A correctly linked seller has users.stripe_account_id set, a party_identity
    stripe_connect row whose metadata carries BOTH source legs (source='both')
    including kyc_status, and seller_profiles columns that may legitimately be
    NULL if the seller onboarded through stripe_connect.py.
  do_not: Repair anything found here by hand. See G-01.

- id: E-02
  name: Establish what Stripe itself says
  when: Before any claim that a seller is or is not live.
  procedure: |
    Our stores are all derived. Stripe is the only authority. Read the account
    through the Stripe API (payouts_enabled, charges_enabled, details_submitted)
    before comparing it to anything of ours.
  expect: Stripe's answer treated as ground truth and our four stores treated as caches.
```

---

## When it breaks

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Seller is live at Stripe but `seller_profiles.kyc_status='not_started'` and `payout_enabled=false` | The seller_profiles leg of `_handle_account_update` matched zero rows because `stripe_connect_id` is NULL and nothing writes it | E-01, then confirm `seller_profiles.stripe_connect_id IS NULL` | G-01 | HIGH — source and production, S1472 |
| F-02 | Seller refused with an identity-verification message while other surfaces show Stripe connected | `party_identity.metadata` has no `kyc_status` key and `deps.py:846` defaults it to `not_started` | Read `party_identity.metadata` for the account and check whether `source` is `users` only | G-01 | HIGH — source and production, S1472 |
| F-03 | `stripe_connect_user_update_zero_rows` appears in logs | `users.stripe_account_id` is not linked to the account Stripe is describing | E-01 | G-01 | HIGH |
| F-04 | Two sellers onboarded in the same week have different `seller_profiles` shapes | They used different endpoints, `stripe.py` versus `stripe_connect.py` (see C.2) | Check which endpoint the account-creation timestamp corresponds to | G-02 | HIGH |
| F-05 | A fix to the identity bridge helpers changes nothing for an affected seller | The helpers sit downstream of the predicate and the seller never reaches them | Confirm the narrow predicates at `webhooks.py:691,704` | G-02 | HIGH — this is exactly what happened with T-2026-000567 |

---

## Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: seller_profiles and party_identity divergence for an existing seller
  root_cause: >-
    The seller_profiles leg of account.updated filters on a column with no
    application writer, so the leg that is the sole writer of kyc_status never
    runs for sellers onboarded through stripe_connect.py.
  repair_entry_point: NOT AUTHORISED AS AN AD-HOC PROCEDURE
  change_pattern: >-
    Reconciliation must be reviewed code driven from live Stripe state, with a dry
    run and an audit trail. Hand-written SQL across these three tables is what
    produced the divergence in the first place. Owned by T-2026-000565.
    Production-data mutation requires Max's explicit go under CORE S3.
  rollback_procedure: not applicable until that design ships
  integrity_check: >-
    The acceptance test is that the named seller can transact, not that a row
    count changed.

- id: G-02
  symptom_ref: F-04
  component_ref: the writer and reader mismatch itself
  root_cause: >-
    Store 3, seller_profiles.stripe_connect_id, is read by four sites and written
    by none, and two onboarding endpoints write different stores.
  repair_entry_point: app/api/v1/endpoints/webhooks.py, app/api/v1/endpoints/stripe.py, app/api/v1/endpoints/stripe_connect.py
  change_pattern: >-
    Do not add a writer for store 3 to make the existing predicates match. Name one
    authority, migrate the readers onto it, and retire the copies.
  rollback_procedure: revert the reader migration commit; the legacy columns are still present
  integrity_check: >-
    After any change, re-run E-01 for a seller onboarded through EACH endpoint and
    confirm both produce the same customer-visible answer.
```

---

## Changes and maintenance

### H.1 Invariants

- Stripe is the only authority on Connect account state. Everything of ours is a cache and must be reconcilable from Stripe outward, never from our own rows outward.
- A store with readers and no writer is a defect, not a spare column. Either give it an authority or delete it.
- A missing metadata key must not be readable as a negative verdict. `metadata.get("kyc_status", "not_started")` turns "we never looked" into "you failed".
- Zero-row writes on the money path must log. The users leg does; the seller_profiles leg does not.
- Repair of production seller records is reviewed code with a dry run, never hand SQL.
- General seller profile edit paths, including `aim.profile.update`, may write only these five business fields: `business_name`, `business_description`, `website_url`, `require_buyer_approval`, and `auto_approve_threshold`. Payment, KYC, earnings, and Stripe identity fields are never profile-editable; `updated_at` is server-controlled.
- **Final S1606 evidence.** The allow-list merged to backend `main` at `db5e2ea6e2dcdf0c70d215a23e034e696b5444c1` and deployed as `db21d9a3-e44c-4d74-9f8b-6e90b84fc81b`; the action-path compatibility repair merged at `ca1837b47bf292411295e314195486186adad44a` and deployed as `fd112e13-5eb7-4091-860f-65933a6e7e19`; the audit UUID/datetime JSON serialization repair merged at `79e62b758e3efdb9622fa016d0a2808ec11c7e33` and deployed as `e8f732d8-450f-4f09-8c67-5a28c403f206`.
- Live isolated synthetic-seller proof on that exact final deployment returned HTTP 200 for action list/check and confirmed `aim.profile.update` succeeded: the allowed `business_name` digest changed and was restored, forbidden Stripe/KYC digests remained unchanged, and permission tier moved 1→2→1. Mutation and restoration each produced a successful audit row with a result. Final-deployment logs contained no UUID-serialization or action-path `AttributeError`; this is not a blanket error-free service-log claim. Normal seller-capability provisioning created the synthetic seller profile, and its failed and successful audit rows were retained, not deleted.

### H.2 Known gaps

- No regression test asserts that a seller onboarded through `stripe_connect.py` ends up with a `kyc_status` in `party_identity`.
- No test exercises `account.updated` against a seller whose `seller_profiles.stripe_connect_id` is NULL.
- `app/models/profile.py` `SellerProfile` does not declare `stripe_connect_id`, `stripe_connect_status`, `payout_enabled`, `kyc_status` or `kyc_verified_at`. Those columns exist in the database and are touched only by raw SQL, so the ORM gives no protection and no discoverability.
- **The frontend has no onboarding-error redirect.** Recorded S1483, 2026-08-08, paired with the T-2026-000565 C2-A merge. `ai-market-frontend` used to carry a global axios response interceptor keyed on `detail.onboarding_url` that redirected any 403 of that shape to `/dashboard`, plus `getOnboardingStatus` against `/auth/onboarding/status` and two `skipOnboardingRedirect` opt-outs. All of it is deleted as of frontend `main` (chunk C2-A, base `a823e45a`, head `e37c595d`). Consequences for anyone working this surface: a backend 403 carrying `onboarding_url` now reaches the calling component as an ordinary rejected promise, so any new client-side gate must be built deliberately rather than assumed to exist. The dashboard catches its own fetch errors and renders a retry card; no other caller depended on the redirect. The only surviving `onboarding_url` references in the frontend are the Stripe-hosted Connect flow at `api/connect.ts:15-16` and its test, which are unrelated to the retired gate and must not be removed with it. The backend enforcers (`app/api/deps.py:_enforce_onboarding` and the second implementation at `app/api/v1/endpoints/listings.py:71`) are still in place and are retired in C2-B.
- **C2-C legacy-path deletion remains blocked by fresh evidence.** T-2026-000565 Gate 2 Amendment A1 R4 (`aidotmarket/ai-market-backend` `1ab86d07291fc333622ca1a572e499ff35d35084`) discharges only the unproducible requirement for retroactive long-window Railway logs. Before C2-C dispatch, all P1-P7 checks in that exact artifact remain binding: current writer/caller inventory, deployed-frontend reachability, live and test Stripe registration reads, fresh `stripe_account_id` measurement, durable `aim.profile.update` history, connected-account reconciliation, C2-B production proof, and Max's explicit deletion approval. P1-P6 must be measured at the declared heads no more than 24 hours before dispatch; any unavailable or failed read blocks dispatch. The amendment does not authorize deletion or production-data mutation.

## Maintenance

| Field | Value |
|---|---|
| Created | S1472, 2026-08-07, vulcan |
| Ticket | T-2026-000572 |
| Verified against | `aidotmarket/ai-market-backend` `origin/main` at `c98a9e7fc`; production Postgres read 2026-08-07 |
| Updated | S1606, 2026-08-25 — recorded the final merged/deployed allow-list and isolated live proof for `BQ-PROFILE-UPDATE-MASS-ASSIGNMENT-S1604` |
| Updated | S1605, 2026-08-24, vulcan — recorded the unanimous approval-class Council ratification of T-2026-000565 Gate 2 Amendment A1 R4 at backend `1ab86d07291fc333622ca1a572e499ff35d35084`; documented the replacement P1-P7 evidence gate for C2-C without authorizing deletion |
| Updated | S1529, 2026-08-11, mars — moved to `runbooks/` canonical path and admitted to the catalog via G-01 anchor advance (`runbooks/runbooks.md`); H.3 catalog debt discharged |
| Updated | S1483, 2026-08-08, vulcan — H.2 frontend onboarding-error redirect retired (`ai-market-frontend` C2-A, base `a823e45a`, head `e37c595d`, Gate 3 unanimous); H.3 catalog debt recorded |
| Refresh trigger | Any change to the Connect onboarding endpoints, `_handle_account_update`, or the `party_identity` metadata contract |
| Related | `account-capability-onboarding.md` (E-06 activation chain), `auth-signup-flow.md`, `infisical-secrets.md`, T-2026-000565, T-2026-000567 |
