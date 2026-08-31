# BQ-DATA-VERIFICATION-S1590 ordinary Stripe pay-in onboarding amendment

**Status:** Gate 1 amendment candidate authorized for exact-SHA review in S1646. This document authorizes specification and later implementation of the bounded scope below. It does not authorize a build, Stripe call, data change, flag change, merge, deployment, or production enablement.

**Build Queue entity:** `build:bq-data-verification-s1590`

**Parent design authority:** [BQ-DATA-VERIFICATION-S1590-GATE1.md](BQ-DATA-VERIFICATION-S1590-GATE1.md). Its privacy, payment, publication, corpus, trust, and production-gate decisions remain binding except for the single scope change stated in section 1.

**Implementation-plan context:** [BQ-DATA-VERIFICATION-S1590-GATE2.md](BQ-DATA-VERIFICATION-S1590-GATE2.md). This amendment adds separate onboarding chunks. It does not rewrite or silently widen any existing Gate 2 chunk.

**Authorization and evidence:** In S1646, Max explicitly authorized this scope expansion after a read-only production probe showed that the named pilot has an authentication identity and a Stripe Connect payout identity, but has no ordinary primary `PartyIdentity(provider="stripe")` whose `external_id` is a `cus_` customer and whose `metadata.default_payment_method_id` is a `pm_` payment method. No payment or billing value from that probe belongs in this document.

**Review process context:** CC must not be used until Max's current 12-hour hold expires. Kimi and GLM are the active reviewers. This restriction changes reviewer routing only; it changes no product, security, data, or payment contract in this amendment.

## 1. Exact amendment boundary

The parent Gate 1 and Gate 2 designs required a usable ordinary seller payment method but deferred the supported way to establish one. S1646 authorizes one narrow addition:

> An authenticated seller-provisioning user with current 2FA may use an independently gated ai.market surface to create or reuse an ordinary Stripe Customer and complete a Stripe-hosted Checkout Session in `mode=setup`, making one payment method available for later data-verification charges.

This amendment supersedes only the Gate 2 section 9 statement that onboarding UI is not added to Slice 1. The original Gate 2 payment-state Chunk 3 remains unchanged: it still must not perform onboarding while authorizing or charging a verification epoch. Onboarding is an earlier, separate flow with separate endpoints, state, feature gate, tests, and release evidence.

All other S1590 decisions remain intact. In particular:

- `DATA_VERIFICATION_ENABLED` remains false by default and production data verification remains off.
- The parent manual-capture PaymentIntent state machine, USD 1-25 bound, twice-provider-cost calculation, hidden-until-captured rule, and CORE S3 checkpoints do not change.
- No source data, D6 input, raw values, samples, locators, findings, or free-form source errors enter this onboarding flow or any Stripe object.
- Stripe Connect is payout infrastructure only. A `stripe_connect` identity or any `acct_` value cannot satisfy, seed, alias, or be converted into ordinary pay-in readiness.
- Existing `(provider, external_id)` uniqueness remains. This amendment adds the separate per-party primary-Stripe invariant in section 5.
- There is no hand-edited production SQL or one-off operator write path. All writes must go through reviewed application code and its migration.

## 2. Ground truth and design consequence

The current data-verification payment loader requires all three of these facts for the same party:

1. an `auth_user` identity that resolves the signed-in user to the party;
2. one primary `PartyIdentity` with `provider="stripe"` and `external_id` matching `cus_...`; and
3. `metadata.default_payment_method_id` matching `pm_...` on that same ordinary Stripe identity.

A Stripe Connect identity uses the distinct `stripe_connect` provider and an `acct_...` external identifier. It represents where seller payouts go. It is never a Stripe Customer, never a verification-charge payment method, and never a fallback when the ordinary identity is absent or invalid.

There is currently no supported write or onboarding route that establishes the ordinary identity. The frontend has no Stripe JS dependency. The smallest safe design is therefore a server-created, Stripe-hosted Checkout Session in `mode=setup`. ai.market redirects the browser to the returned Stripe Checkout URL and never renders card fields, handles a client secret, or adds Stripe JS.

The existing webhook endpoint remains the only Stripe webhook endpoint. Its signature verification and event deduplication remain mandatory, and `checkout.session.completed` remains critical and retryable. The authenticated return path is a second reconciliation trigger, not a substitute for the signed webhook.

## 3. Roles, gates, and fixed origins

### 3.1 Authorization

Every readiness, session-creation, and return-reconciliation request requires all of the following:

- a valid signed-in application session;
- the current seller-provisioning permission already used to establish a seller party;
- a current, server-verified 2FA assertion under the existing 2FA freshness policy; and
- an `auth_user` `PartyIdentity` that maps the authenticated user to the seller party in the active provisioning context.

The server derives `auth_user_id` and `party_id` from that trusted context. No endpoint accepts a caller-provided user ID, party ID, customer ID, payment-method ID, Stripe account, origin, success URL, or cancel URL. An absent, ambiguous, revoked, cross-party, or non-seller mapping fails before a Stripe call.

### 3.2 Independent default-off gate

Add the backend setting:

```text
STRIPE_PAYIN_ONBOARDING_ENABLED=false
STRIPE_PAYIN_ONBOARDING_PUBLIC_ORIGIN=<required allowlisted HTTPS origin when enabled>
```

The enabled setting is false by default in every environment. The public-origin setting has no fallback to request headers and startup fails closed when onboarding is enabled without an environment-approved HTTPS value. The enabled setting is independent of `DATA_VERIFICATION_ENABLED` and is checked server-side on all three endpoints before readiness data is read or Stripe is called. When false, the endpoints return the standard not-found response with stable internal code `PAYIN_ONBOARDING_DISABLED`; this prevents an unfinished surface from being discoverable through normal product behavior.

The frontend may render the page or navigation only when its server-provided capability says onboarding is enabled, but frontend hiding is not an authorization control. Enabling `STRIPE_PAYIN_ONBOARDING_ENABLED` must not enable scans, quotes, PaymentIntent creation, or verification publication. `DATA_VERIFICATION_ENABLED` may not be enabled merely because onboarding is enabled or complete.

### 3.3 Fixed public origin

Checkout success and cancel URLs are built only from the deployment's `STRIPE_PAYIN_ONBOARDING_PUBLIC_ORIGIN`, read from trusted server configuration and checked against that environment's deploy allowlist. They are not derived from `Host`, `Origin`, `Referer`, forwarding headers, query parameters, or request JSON.

For production the path shapes are fixed as follows; the deployment supplies only the pre-approved origin:

```text
success: {CANONICAL_PUBLIC_ORIGIN}/dashboard/data-verification/payment-method/return?attempt={setup_attempt_id}&session_id={CHECKOUT_SESSION_ID}
cancel:  {CANONICAL_PUBLIC_ORIGIN}/dashboard/data-verification/payment-method?result=cancelled&attempt={setup_attempt_id}
```

`setup_attempt_id` is an application-generated opaque UUID. `{CHECKOUT_SESSION_ID}` is Stripe's literal server-side Checkout placeholder. Query strings on these paths are redacted from access and application logs. Redirect destinations are never returned by or accepted from the caller.

## 4. Exact API and frontend contracts

All JSON schemas reject unknown keys. Authentication, 2FA, ownership, and the server gate apply before the behavior described below.

### 4.1 Readiness

```text
GET /api/v1/data-verification/payment-method/readiness
response schema: DataVerificationPayInReadinessV1
```

The successful response is non-sensitive and contains exactly:

```json
{
  "version": "data_verification_payin_readiness_v1",
  "state": "setup_required | setup_pending | ready | blocked",
  "can_start_setup": true,
  "can_replace_payment_method": false,
  "message": "plain English from the fixed copy table"
}
```

The booleans must agree with `state`. `ready` means the current party passes the unchanged default payment loader. `setup_required` means no usable ordinary mapping exists and setup may start. `setup_pending` means the current party has a reusable unexpired setup attempt or reconciliation is retrying. `blocked` means an identity invariant or non-retryable ownership/configuration problem needs operator investigation. The response contains no `cus_`, `pm_`, `acct_`, `cs_`, `seti_`, email, billing value, last four digits, brand, expiry, address, cardholder name, or Connect status.

### 4.2 Create or reuse a hosted setup session

```text
POST /api/v1/data-verification/payment-method/setup-sessions
request schema: DataVerificationPayInSetupCreateV1
response schema: DataVerificationPayInSetupSessionV1
```

The request body is exactly:

```json
{"version": "data_verification_payin_setup_v1"}
```

It contains no other fields. In particular, it has no URL, party, user, customer, payment method, email, or Stripe-account override.

A new response is HTTP 201; reuse of the same still-valid open attempt is HTTP 200. The response is exactly:

```json
{
  "version": "data_verification_payin_setup_session_v1",
  "setup_attempt_id": "opaque UUID",
  "checkout_url": "Stripe-hosted HTTPS Checkout URL",
  "expires_at": "RFC 3339 UTC timestamp"
}
```

`checkout_url` is returned once for immediate top-level navigation. It is never persisted in application state, analytics, logs, audit events, error reports, or spec metadata. The server accepts only an HTTPS URL returned by the configured Stripe SDK whose host matches Stripe's documented Checkout host allowlist; otherwise it fails closed.

The server creates the Checkout Session with these fixed inputs:

- `mode="setup"`;
- the ordinary `customer="cus_..."` created or reused under section 5;
- `payment_method_types=["card"]` and SetupIntent usage `off_session`;
- the fixed success and cancel URLs from section 3.3;
- `client_reference_id=setup_attempt_id`;
- exact metadata `purpose="data_verification_payin"`, `contract_version="v1"`, and opaque `setup_attempt_id`, `party_id`, and `auth_user_id` bindings on the Checkout Session and SetupIntent; and
- a server-derived Stripe idempotency key scoped to the setup attempt.

The application does not send name, email, phone, address, source data, listing data, D6, or a Connect account to prefill Checkout. Stripe may collect the billing fields required by its hosted product, but ai.market neither requests those values back nor stores or logs them.

### 4.3 Authenticated return reconciliation

The frontend return page reads the fixed `attempt` and `session_id` query values, does not log or analyze them, removes them from visible browser history with `history.replaceState`, and calls:

```text
POST /api/v1/data-verification/payment-method/setup-sessions/reconcile
request schema: DataVerificationPayInSetupReconcileV1
response schema: DataVerificationPayInReconcileResultV1
```

The request is exactly:

```json
{
  "version": "data_verification_payin_reconcile_v1",
  "setup_attempt_id": "opaque UUID",
  "checkout_session_id": "cs_..."
}
```

The response contains exactly:

```json
{
  "version": "data_verification_payin_reconcile_result_v1",
  "state": "ready | pending | failed",
  "message": "plain English from the fixed copy table"
}
```

The supplied Checkout Session ID is only a retrieval key. It must equal the server-stored session ID for the authenticated user's setup attempt before it can affect state. A mismatch returns the fixed `SETUP_SESSION_MISMATCH` error, records an opaque security audit event, and changes nothing.

### 4.4 Frontend routes and fixed copy

Use these routes and no embedded payment form:

```text
/dashboard/data-verification/payment-method
/dashboard/data-verification/payment-method/return
```

The exact user-facing copy is:

| State or element | Copy |
| --- | --- |
| Heading | `Payment method for verification charges` |
| Explanation | `Add a payment method that ai.market can use for data-verification charges. This is separate from Stripe payouts.` |
| Hosted handoff | `You will continue securely on Stripe. ai.market does not collect or store your card details, and no verification charge is made during setup.` |
| Setup button | `Add payment method` |
| Replacement button | `Replace payment method` |
| Ready | `A payment method is ready for verification charges. Your Stripe payouts are separate and were not changed.` |
| Cancelled | `No payment method was changed and no verification charge was made. You can try again.` |
| Pending | `Stripe is still confirming your payment method. Check again in a moment.` |
| Failed | `We could not confirm your payment method. No verification charge was made. Try again.` |
| Success | `Your payment method is ready for verification charges. Your Stripe payouts were not changed.` |
| Blocked | `Payment-method setup is unavailable for this seller account. Contact support without sending payment details.` |

The page must never call Stripe JS, render an iframe, accept card or billing input, display masked card details, or describe this payment method as a payout account.

## 5. Ordinary Customer and PartyIdentity contract

### 5.1 Ordinary identity shape

The only identity that satisfies pay-in readiness is:

```text
provider = "stripe"
is_primary = true
external_id = "cus_..."
metadata = {"default_payment_method_id": "pm_..."}
```

The `external_id` prefix and metadata key value are validated before read or write. `metadata` contains only `default_payment_method_id`; it contains no email, name, phone, address, card data, Checkout Session, SetupIntent, Connect account, billing values, source data, D6, listing data, or free-form Stripe response.

`provider="stripe_connect"`, `external_id="acct_..."`, Connect account fields, and payout readiness are excluded from every lookup and write in this flow. An `acct_` value observed in an ordinary identity is an invariant violation and produces `blocked`; it is never repaired by reinterpretation.

### 5.2 Customer create/reuse

Under a per-party database lock, creation first checks for the one primary ordinary Stripe identity:

- If a valid `cus_` identity exists, reuse that Customer. Never create a replacement Customer merely to replace a payment method.
- If no such identity exists, create one bare ordinary Stripe Customer with a per-party idempotency key. Send only the opaque party binding and `purpose=data_verification_payin`, `contract_version=v1` as Stripe metadata. Do not send an email or billing/profile values.
- Keep the returned `cus_` only on the bounded setup attempt until successful finalization. The final transaction inserts the primary ordinary identity with both the `cus_` external ID and its one-key `pm_` metadata; it never exposes an incomplete primary ordinary identity to the default loader.
- If an invalid or duplicate ordinary identity exists, stop as `blocked`; do not select one by age, overwrite it, demote it, or use a Connect identity.

The Customer and Checkout Session are created on the platform's ordinary Stripe account with the environment's ordinary Stripe credentials. The implementation must not set a connected-account request header or accept an account override.

Creation crosses Stripe and database boundaries in this fixed order:

1. in one database transaction, lock the party and create or reuse the single active local attempt with its stable local ID and idempotency keys;
2. create or retrieve the bare Customer with the attempt's Customer idempotency key, then persist its `cus_` on that attempt;
3. create or retrieve the fixed Checkout Session with the attempt's Session idempotency key, then persist its `cs_` and mark the attempt `open`; and
4. return the retrieved Session URL without persisting or logging the URL.

A timeout or database failure after either Stripe call repeats that same idempotency key and retrieves the same object; it does not mint a new canonical object. If the local attempt can no longer be associated safely, reconciliation marks the Customer as an opaque orphan candidate and applies section 6.3. It never guesses ownership from email, Connect data, or recent creation time.

### 5.3 One-primary-Stripe-per-party migration

Add a database partial unique index named:

```text
uq_party_identity_one_primary_stripe_per_party
```

Its key is `party_id`, with predicate:

```sql
provider = 'stripe' AND is_primary IS TRUE
```

Before creating the index, the migration runs this read-only preflight inside the same transactional migration:

```sql
SELECT party_id, count(*)
FROM party_identity
WHERE provider = 'stripe' AND is_primary IS TRUE
GROUP BY party_id
HAVING count(*) > 1;
```

Any returned row raises a stable `S1646_DUPLICATE_PRIMARY_STRIPE_IDENTITY` migration error before the index is created. The migration performs no winner selection, metadata merge, demotion, deletion, or data repair. Transaction rollback leaves the schema and rows unchanged. Resolution requires a separately reviewed application/data-repair plan; hand-edited production SQL remains prohibited.

The existing uniqueness of `(provider, external_id)` remains separately enforced. Service code handles a race on either constraint by rolling back, rereading the canonical ordinary identity, and reusing it only if it belongs to the same party and passes every invariant. A cross-party conflict fails closed.

## 6. Setup attempt, completion, and validation

### 6.1 Persisted attempt

Add `data_verification_payin_setup_attempt` with only these logical fields:

- local opaque `id` (`setup_attempt_id`), `party_id`, and requesting `auth_user_id`;
- expected `customer_id` (`cus_`) and exact `checkout_session_id` (`cs_`);
- fixed `purpose`, `contract_version`, expected environment/livemode, and fixed platform Stripe-account context;
- state `creating | open | reconciling | ready | cancelled | failed | orphan_customer`;
- retry-safe timestamps, last fixed error code, and optimistic version.

It does not store a Checkout URL, client secret, payment-method details, email, name, address, raw billing value, raw webhook body, or free-form Stripe error. It need not persist `pm_` or `seti_`; those are retrieved and validated during reconciliation, and the finalized `pm_` is stored only in the ordinary PartyIdentity metadata.

There is at most one unexpired `creating`, `open`, or `reconciling` attempt per party. A concurrent duplicate POST returns the same open attempt and Checkout URL if it is still safe and available, or creates exactly one successor after expiry. Database locking plus the Stripe idempotency key must prove that duplicate requests cannot create two canonical ordinary Customers or two active sessions.

### 6.2 Two completion triggers, one finalizer

Both triggers invoke the same `finalize_data_verification_payin_setup(setup_attempt_id)` service:

1. the authenticated return reconciliation in section 4.3; and
2. the existing signed webhook endpoint after its existing durable deduplication accepts `checkout.session.completed`.

The webhook handler maps the event to the local attempt through exact metadata and the stored Checkout Session ID. Existing deduplication may mark the critical event durably complete only after the finalizer reaches a durable terminal result; a transient Stripe or database failure returns a retryable failure and must not consume the event. The handler never trusts event metadata alone and never writes PartyIdentity directly.

The finalizer retrieves the Checkout Session, expanded SetupIntent, and PaymentMethod from Stripe using the server's ordinary platform account context. Before any final write, it validates all of these conjunctively:

1. the attempt belongs to the currently authenticated `auth_user` and party for a return call, or the signed event's session maps to that stored attempt for a webhook call;
2. stored purpose is `data_verification_payin`, contract version is `v1`, and Session, SetupIntent, and local bindings agree on purpose, version, attempt, user, and party;
3. the supplied, event, retrieved, and stored Checkout Session IDs are equal;
4. Checkout `mode` is exactly `setup` and its completion state is complete;
5. the Session Customer equals the attempt Customer and has a `cus_` prefix; if an ordinary identity already exists, its `external_id` must equal that Customer, while a first setup requires that no ordinary identity appeared after the attempt was created;
6. the Session's SetupIntent is present, belongs to that same Customer, has status `succeeded`, and was created with `usage=off_session`;
7. the selected PaymentMethod has a `pm_` prefix, is attached to and retrievable under that same Customer, and is of the approved `card` type;
8. the Session, SetupIntent, PaymentMethod, API client, and expected environment all agree on test versus live mode;
9. the webhook event account context and all object retrievals equal the fixed platform Stripe-account context, with no connected-account event or request override; and
10. the party still has the same valid `auth_user` ownership and at most one primary ordinary Stripe identity.

Any failed equality or ownership check is a non-retryable substitution/security failure for that attempt. It never adopts the presented Customer or PaymentMethod, never changes the old default, and never falls back to an `acct_` identity. Transient retrieval failures leave the attempt retryable and return `pending`.

### 6.3 Idempotent finalization and failure ordering

Stripe and the application database cannot share one transaction. The required order is:

1. retrieve and validate all Stripe objects without a database write;
2. lock the attempt and ordinary identity and reread all ownership and uniqueness invariants;
3. set the validated PaymentMethod as the Stripe Customer's default payment method;
4. in one database transaction, insert the first ordinary PartyIdentity or replace the existing ordinary PartyIdentity metadata with exactly `{"default_payment_method_id":"pm_..."}`, mark the attempt `ready`, and commit;
5. reread through the unchanged data-verification default payment loader and return `ready` only if it selects the same party, Customer, and PaymentMethod.

Repeated Stripe default-setting to the same `pm_` is safe. The attempt lock/version, exact comparisons, and final metadata replacement make duplicate or reordered webhook and return calls converge to the same result.

Failure behavior is fixed:

- Stripe fails before changing its Customer default: roll back/leave the database unchanged and retry the same attempt.
- Stripe changes its default but the database transaction fails: the attempt remains non-ready; retry retrieves the same succeeded SetupIntent, confirms the Stripe default, and completes the database write. No verification loader may infer readiness from Stripe alone.
- The database is ready but a duplicate late event arrives: reread and return success only when Customer and PaymentMethod equality still hold; otherwise fail closed for reconciliation.
- A Customer is created but the ordinary identity insert or session creation cannot complete: retain an `orphan_customer` attempt bound to the idempotency key. Automated reconciliation retries adoption only when the Customer is on the expected platform account, has the exact opaque purpose/party binding, has no successful foreign setup, and no other party references it. No operator SQL or arbitrary Customer adoption is allowed.
- Stripe's Customer default and PartyIdentity metadata disagree: block verification readiness. If the setup attempt proves the database `pm_` came from a succeeded owned SetupIntent, reconciliation may reapply that same `pm_` to Stripe. Any other drift requires reviewed investigation; it is never resolved by choosing whichever value is newest.

No failure path creates a PaymentIntent, confirms a charge, detaches a payment method, or changes Stripe Connect.

## 7. Replacement and recovery

Replacement uses the same POST and finalizer with the existing ordinary `cus_` Customer. The current `pm_` remains the default until the replacement SetupIntent has succeeded and section 6 validation completes. Cancel, expiry, browser loss, webhook delay, return-before-webhook, webhook-before-return, duplicate calls, and temporary Stripe failure leave the old default usable.

Slice 1 supports add and replace only. It does not support removal, detach, deletion, clearing the default, selecting among saved methods, or editing billing details. A failed or cancelled first setup remains `setup_required`; a failed or cancelled replacement remains `ready` with the prior default. Expired sessions are never revived; a new attempt can be created after the prior attempt is terminal or expired.

Setup makes no charge and creates no PaymentIntent. Later verification charges remain exclusively governed by the parent Gate 1 manual-capture flow.

## 8. Threat model, forbidden fields, and audit

| Threat | Required control | Failure result |
| --- | --- | --- |
| Authentication, 2FA, or seller-role bypass | Server-side checks on every endpoint and return finalization; derive user and party from trusted context. | 401/403 before Stripe; no state change. |
| Connect/pay-in identity confusion | Exact provider and prefix checks; fixed platform account context; never inspect `stripe_connect` as a candidate. | `blocked`; no adoption or mutation. |
| Open redirect, header poisoning, or caller URL injection | Canonical allowlisted origin and fixed paths; strict request schemas; Stripe-host allowlist on returned Checkout URL. | Reject before session creation or redirect. |
| Cross-user, cross-party, cross-session, or cross-account substitution | Stored attempt/session/customer bindings plus conjunctive Session, SetupIntent, PaymentMethod, user, party, account, purpose, and version equality. | Fixed security failure; old default unchanged. |
| Test/live object confusion | Environment-derived credentials and livemode equality across every retrieved object. | Non-retryable mismatch; no write. |
| Forged, replayed, duplicated, or reordered events | Existing webhook signature verification and durable dedupe plus one idempotent finalizer. | Invalid signatures rejected; valid duplicates converge. |
| Duplicate Customers or primary identities under concurrency | Per-party lock, Customer idempotency key, attempt uniqueness, existing identity uniqueness, and new partial unique index. | One canonical object or fail closed. |
| Hosted-page or frontend skimming regression | No Stripe JS, Elements, iframe, app card input, client secret, or billing display. | Frontend test/build failure; release blocked. |
| Sensitive payment data in telemetry or state | Strict schemas, response minimization, query redaction, fixed error codes, and captured-log/analytics tests. | Release blocked and affected telemetry treated as a security incident. |
| Stripe-default/database drift | Database loader remains readiness authority; evidence-bound reconciliation only. | Verification stays blocked until convergence. |

The following are forbidden in application logs, audit events, analytics, error tracking, application state, PartyIdentity metadata other than the one allowed key, and this specification's operational evidence:

- card number, CVC, magnetic-stripe or cryptogram data, fingerprints, last four digits, brand, expiry, wallet details, bank data, or any other payment credential;
- Stripe client secret, Checkout URL, raw webhook body, signature secret, API key, or browser query string;
- email, name, phone, postal address, IP-derived profile, raw billing details, or Stripe billing/profile response;
- source data, source metadata, D6, listing content, scan findings, locator, or free-form source/Stripe error text; and
- caller-provided redirect URL, Customer, PaymentMethod, Connect account, user, or party value.

Security and lifecycle audit events use local opaque `setup_attempt_id`, `party_id`, and `auth_user_id` only, plus fixed event name, fixed outcome/error code, environment label, actor type, and timestamp. They do not contain `cus_`, `pm_`, `acct_`, `cs_`, `seti_`, Checkout URL, billing data, or free text. Required fixed events are `payin_setup_requested`, `payin_setup_reused`, `payin_setup_returned`, `payin_setup_webhook_received`, `payin_setup_ready`, `payin_setup_failed`, `payin_setup_substitution_rejected`, and `payin_setup_orphan_customer`.

## 9. Finite implementation chunks and files

The chunks are dependency-ordered and finite. A builder who needs another production file or route must stop and return with an amendment rather than widening the manifest silently. Test fixtures and generated migration metadata required by a named test are included with that test.

### Chunk A — persistence, uniqueness, gate, and readiness

**Repository:** `ai-market-backend`

**Files:**

- `app/core/config.py`
- `app/domains/crm/core/models.py`
- `app/models/__init__.py`
- `app/models/data_verification_payin.py` (new)
- `app/schemas/data_verification_payin.py` (new)
- `app/services/data_verification_payin_service.py` (new)
- `app/api/v1/endpoints/data_verification_payin.py` (new)
- `app/api/v1/router.py`
- `alembic/env.py`
- `alembic/versions/20260901_001_s1646_payin_primary_identity.py` (new)
- `tests/test_data_verification_payin_readiness.py` (new)
- `tests/test_data_verification_payin_migration.py` (new)

**Boundary:** Add the default-off gate, setup-attempt model, partial unique index, loader-backed readiness response, and authorization checks. Stripe calls and frontend work are excluded.

### Chunk B — Customer, hosted session, webhook, and shared finalizer

**Depends on:** Chunk A.

**Repository:** `ai-market-backend`

**Files:**

- `app/schemas/data_verification_payin.py`
- `app/services/data_verification_payin_service.py`
- `app/api/v1/endpoints/data_verification_payin.py`
- `app/api/v1/endpoints/webhooks.py`
- `tests/test_data_verification_payin_setup.py` (new)
- `tests/test_data_verification_payin_reconciliation.py` (new)
- `tests/test_webhooks.py`
- `tests/test_data_verification_payment.py`

**Boundary:** Implement the strict POST schemas, bare Customer creation/reuse, Stripe-hosted setup Session, authenticated reconciliation, critical/retried webhook route, shared finalizer, replacement, and unchanged default-loader integration. No PaymentIntent or charge is allowed in this chunk.

### Chunk C — hosted-redirect frontend

**Depends on:** Chunk B contract fixtures.

**Repository:** `ai-market-frontend`

**Files:**

- `app/dashboard/data-verification/payment-method/page.tsx` (new)
- `app/dashboard/data-verification/payment-method/return/page.tsx` (new)
- `components/DataVerificationPaymentMethod.tsx` (new)
- `lib/api.ts`
- `types/index.ts`
- `app/dashboard/data-verification/payment-method/page.test.tsx` (new)
- `app/dashboard/data-verification/payment-method/return/page.test.tsx` (new)

**Boundary:** Render readiness and fixed copy, navigate top-level to the server-returned Stripe-hosted URL, reconcile the fixed return, redact/remove query values, and cover success/cancel/pending/error. Do not add a Stripe dependency, payment form, iframe, or card display.

### Chunk D — integration and release evidence

**Depends on:** Chunks A-C deployed with both flags false and every review/checkpoint in section 11 satisfied.

**Repositories:** no new production files. Evidence-only fixtures or runbook records require their own exact manifest at dispatch.

**Boundary:** Run the real Stripe test-mode setup journey, end-to-end loader proof, named-pilot confirmation, signed-in browser proof, flag-order rehearsal, and rollback rehearsal. No production enablement occurs inside the chunk.

## 10. Acceptance criteria and tests

Each item is independently required.

1. **Auth, 2FA, and ownership:** unauthenticated, stale/missing-2FA, non-seller, missing `auth_user`, revoked binding, ambiguous party, other-user attempt, and other-party attempt fixtures fail before Stripe and create no attempt or identity. An eligible seller-provisioning user succeeds.
2. **Flag off:** all three backend endpoints fail closed under `STRIPE_PAYIN_ONBOARDING_ENABLED=false`; the frontend navigation/surface is absent; no Stripe mock is invoked. `DATA_VERIFICATION_ENABLED` stays false and does not control onboarding.
3. **URL pinning:** request schemas reject success/cancel/return URL fields and unknown keys. Host/Origin/forwarded-header attacks cannot change the canonical URLs. Only the approved production/test origin and Stripe Checkout HTTPS hosts pass.
4. **Customer create/reuse and Connect separation:** the first eligible call creates one bare `cus_`; later and concurrent calls reuse it. Existing `acct_`/`stripe_connect` data is neither read as pay-in readiness nor changed. Captured Stripe requests contain no email, profile, billing, listing, D6, source, or free text.
5. **Concurrent duplicates:** parallel first calls, transaction retry, Stripe timeout-before-response, and retry-after-response fixtures converge to one primary ordinary identity, one canonical Customer, and one active setup Session, or a safe retryable orphan record. Cross-party `(provider, external_id)` collision fails closed.
6. **Setup-session substitution:** wrong attempt, session, user, party, Customer, purpose, contract version, SetupIntent, PaymentMethod, platform account, or object binding changes nothing and emits only the fixed opaque audit event.
7. **Completion validity:** `mode!=setup`, incomplete Session, absent/unsucceeded SetupIntent, `usage!=off_session`, unattached/wrong-customer/wrong-type PaymentMethod, invalid prefixes, and cross-account retrieval all fail closed.
8. **Webhook signature and dedupe:** invalid signatures are rejected before lookup; repeated and reordered valid `checkout.session.completed` events use existing durable dedupe and the same finalizer; transient failures remain critical/retryable; return-before-webhook and webhook-before-return converge.
9. **Mode and livemode:** every test/live permutation across configuration, Session, SetupIntent, and PaymentMethod is covered; only complete equality succeeds.
10. **Replacement and recovery:** a successful replacement reuses `cus_` and atomically changes only `metadata.default_payment_method_id`; cancelled, expired, failed, or pending replacement preserves the old `pm_`. There is no remove/detach/clear path.
11. **Stripe/database ordering:** fault injection before and after Customer creation, identity insert, Session creation, Stripe-default update, and database commit proves the ordering and recovery rules in section 6.3, including orphan Customer and default drift. No manual SQL is part of recovery.
12. **Default loader integration:** readiness becomes `ready` only when the unchanged data-verification loader selects the authenticated party's primary ordinary `cus_` and the finalized `pm_`. A Connect identity alone, empty metadata, malformed prefix, duplicate identity, or Stripe/DB drift is not ready.
13. **Migration uniqueness:** empty, single-identity, many-party, nullable/non-primary, and duplicate-primary fixtures prove the partial index. Duplicate preflight aborts without changing rows or schema; downgrade/re-upgrade is tested in a disposable database; existing `(provider, external_id)` uniqueness remains.
14. **Frontend behavior:** success, cancel, pending, retryable error, blocked, flag-off, and network-loss states render the fixed copy. Query identifiers are removed from visible history and excluded from analytics. No application element accepts card/billing input, and dependency/build searches prove no Stripe JS/Elements/iframe/client secret was added.
15. **No charges:** captured Stripe mocks and the real test journey show SetupIntent/Checkout setup only: zero PaymentIntent creation, zero confirmation/capture/refund, and zero Connect mutation.
16. **Forbidden data:** captured request, response, DB row, log, audit, analytics, error-report, browser-console, browser-storage, and webhook fixtures contain none of section 8's forbidden fields. Audit payloads equal the fixed opaque schema.
17. **Parent invariants:** the parent manual-capture payment tests, webhook tests, S1590 privacy/exfiltration searches, and feature-off tests remain green. No customer-to-cloud scan manifest, D6 contract, corpus field, publication rule, pricing rule, or verification state transition changes.

## 11. Review and release checkpoints

Passing tests is necessary but insufficient. Static review, deployment, Stripe test evidence, database state, and signed-in browser proof are independent and conjunctive.

1. **Exact-SHA amendment review:** after this document is committed, Kimi and GLM must review that exact runbooks SHA under the active directive and record their exact model identity, verdict, mandates, and immutable response references. Any document edit invalidates the reviews. CC is not contacted or counted while Max's 12-hour hold is active; after expiry, only the then-current directive determines whether CC review is also required.
2. **Build dispatch:** no product repository work starts until the amendment has the required review result and a dispatch names the exact backend/frontend baselines and one chunk's file manifest. This document itself does not dispatch a build.
3. **Migration preflight:** the release candidate runs the duplicate query against a read-only production snapshot or approved read-only production transaction. Any duplicate blocks migration and requires a separately reviewed repair; no hand SQL.
4. **Both flags false:** deploy migration and code with `STRIPE_PAYIN_ONBOARDING_ENABLED=false` and `DATA_VERIFICATION_ENABLED=false`. Prove old data-verification and payout behavior unchanged before either gate is considered.
5. **PR #48 same-release hold:** identify PR #48 by repository, exact merged SHA, required behavior, and deployment artifact. It must be included in and verified as part of the same release candidate before onboarding is enabled. A PR number, merge label, or later-release promise is not evidence.
6. **Real Stripe test-mode journey:** using the release candidate and Stripe test mode, complete the hosted `mode=setup` flow through both return and a signed `checkout.session.completed` webhook. Prove Customer equality, succeeded SetupIntent, attached PaymentMethod, zero PaymentIntent/charge, duplicate-event convergence, and loader readiness without recording payment details in evidence.
7. **Signed-in browser proof:** with an authorized seller-provisioning test identity and current 2FA, show flag-off absence, fixed copy, top-level Stripe-hosted handoff, cancel, pending/retry, success, replacement, no card collection in ai.market, and clear separation from Stripe payouts. Synthetic or unauthenticated API output does not substitute for this proof.
8. **Named pilot confirmation:** through an authorized read-only check after test evidence passes, confirm the named pilot has one `auth_user` identity, one primary ordinary `provider="stripe"` `cus_`, one `pm_` default selected by the unchanged loader, and an unchanged separate `stripe_connect` `acct_` payout identity. Evidence records only pass/fail and opaque local references, not Stripe IDs or billing data.
9. **Flag order:** only after checkpoints 1-8 may an authorized operator enable onboarding for the bounded pilot. Data verification remains off. `DATA_VERIFICATION_ENABLED` may be enabled later only after the parent Gate 1/Gate 2 payment and privacy checkpoints, named-pilot readiness, PR #48 same-release proof, deployment proof, and signed-in verification journey all pass.
10. **Rollback rehearsal:** first disable `DATA_VERIFICATION_ENABLED`, then disable `STRIPE_PAYIN_ONBOARDING_ENABLED`; verify the setup surface and endpoints are unavailable and no new attempts start. Reverting application code must not delete or detach Customers/payment methods or alter Connect. The uniqueness index remains unless a separately approved rollback proves no dependent writes and uses the reviewed migration downgrade. Existing finalized ordinary identities remain for payment reconciliation.
11. **No production enablement in this amendment:** authoring, review, merge, test-mode proof, and deployment with flags false do not authorize either production gate. Enablement requires a separate explicit operator action and its evidence.

## 12. Explicit non-goals

This amendment does not add or authorize:

- production enablement of onboarding or data verification;
- any charge, PaymentIntent, verification quote, authorization, capture, refund, or pricing change;
- Stripe Connect onboarding, payout-status changes, payout identity migration, or reuse of an `acct_` value;
- card fields, Stripe JS, Elements, an iframe, a client secret, or application collection/display of payment or billing data;
- payment-method removal, detach, clearing, selection UI, billing-profile editing, multiple ordinary Customers, or multiple primary ordinary Stripe identities per party;
- caller-supplied redirects, origins, party/user/customer/payment-method/account identifiers, or arbitrary metadata;
- manual production SQL, database repair, Stripe Dashboard edits, one-off scripts, customer adoption by guess, or email-based Customer matching;
- changes to the S1590 scan manifest, D6, AIM Data, allAI narrative, corpus, badge, publication, pricing, capture, cancellation, or refund contracts;
- a new webhook endpoint, replacement of signature verification/deduplication, or weakening of critical webhook retry behavior;
- a general billing wallet, buyer checkout, subscription, invoices, tax, non-card payment types, or general seller settings redesign; or
- general availability. The known-counterparty pilot and every parent release blocker remain.

## 13. Falsifiers and stop conditions

Implementation or release stops and returns to design review if any of the following is true:

- Stripe-hosted setup cannot establish an off-session-compatible method without adding Stripe JS or exposing a client secret to application code.
- The ordinary platform Customer cannot be distinguished conjunctively from the Connect payout account and test/live account context.
- Existing data contains duplicate primary ordinary Stripe identities, or the new uniqueness rule cannot be added without data loss or winner selection.
- Concurrent calls can produce two canonical Customers, two primary identities, or conflicting active setup attempts for one party.
- Signed webhook and authenticated return calls cannot converge without trusting caller or event metadata alone.
- A PaymentMethod cannot be proven to belong to the expected Customer and succeeded SetupIntent.
- Any forbidden payment, billing, source, D6, listing, or credential field enters application state, telemetry, evidence, or PartyIdentity metadata.
- Any path charges, creates a PaymentIntent, removes a method, changes Connect, or enables data verification.
- PR #48 cannot be identified and proved in the same release candidate before gate enablement.
- The parent S1590 privacy, payment, or production-enable invariants regress.
