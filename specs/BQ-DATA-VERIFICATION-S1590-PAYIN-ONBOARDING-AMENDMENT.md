# BQ-DATA-VERIFICATION-S1590 ordinary Stripe pay-in onboarding amendment

**Status:** Gate 1 amendment candidate revised after the exact-SHA S1646 review findings. A fresh exact-SHA review is required. This document authorizes specification and later implementation of the bounded scope below. It does not authorize a build, Stripe call, data change, flag change, merge, deployment, or production enablement.

**Build Queue entity:** `build:bq-data-verification-s1590`

**Parent design authority:** [BQ-DATA-VERIFICATION-S1590-GATE1.md](BQ-DATA-VERIFICATION-S1590-GATE1.md). Its privacy, payment, publication, corpus, trust, and production-gate decisions remain binding except for the single scope change stated in section 1.

**Implementation-plan context:** [BQ-DATA-VERIFICATION-S1590-GATE2.md](BQ-DATA-VERIFICATION-S1590-GATE2.md). This amendment adds separate onboarding chunks. It does not rewrite or silently widen any existing Gate 2 chunk.

**Authorization and evidence:** In S1646, Max explicitly authorized this scope expansion after a read-only production probe showed that the named pilot has an authentication identity and a Stripe Connect payout identity, but has no ordinary primary `PartyIdentity(provider="stripe")` whose `external_id` is a `cus_` customer and whose `metadata.default_payment_method_id` is a `pm_` payment method. No payment or billing value from that probe belongs in this document.

**Review process context:** CC must not be used until Max's current 12-hour hold expires. Kimi and GLM are the active reviewers. This restriction changes reviewer routing only; it changes no product, security, data, or payment contract in this amendment.

## 1. Exact amendment boundary

The parent Gate 1 and Gate 2 designs required a usable ordinary seller payment method but deferred the supported way to establish one. S1646 authorizes one narrow addition:

> An authenticated seller-provisioning user whose party is the one explicitly approved pilot and whose account has TOTP enabled may use an independently gated ai.market surface to check non-sensitive readiness. Creating or reconciling a Stripe-hosted Checkout Session in `mode=setup` additionally requires the existing user-scoped 60-second action-reauthentication token, making one payment method available for later data-verification charges.

This amendment supersedes only the Gate 2 section 9 statement that onboarding UI is not added to Slice 1. The original Gate 2 payment-state Chunk 3 remains unchanged: it still must not perform onboarding while authorizing or charging a verification epoch. Onboarding is an earlier, separate flow with separate endpoints, state, feature gate, tests, and release evidence.

All other S1590 decisions remain intact. In particular:

- `DATA_VERIFICATION_ENABLED` remains false by default and production data verification remains off.
- The parent manual-capture PaymentIntent state machine, USD 1-25 bound, twice-provider-cost calculation, hidden-until-captured rule, and CORE S3 checkpoints do not change.
- No source data, D6 input, raw values, samples, locators, findings, or free-form source errors enter this onboarding flow or any Stripe object.
- Stripe Connect is payout infrastructure only. A `stripe_connect` identity or any `acct_` value cannot satisfy, seed, alias, or be converted into ordinary pay-in readiness.
- Existing `(provider, external_id)` uniqueness remains. This amendment adds the separate per-party primary-Stripe invariant in section 5.
- There is no hand-edited production SQL or one-off operator write path. All writes must go through reviewed application code and its migration.

## 2. Ground truth and design consequence

This amendment owns and fixes the Gate 2 Chunk 3 default-payment-loader predicate to all three of these facts for the same party:

1. an `auth_user` identity that resolves the signed-in user to the party;
2. one primary `PartyIdentity` with `provider="stripe"` and `external_id` matching `cus_...`; and
3. `metadata.default_payment_method_id` matching `pm_...` on that same ordinary Stripe identity.

The implementation seam is `app/services/data_verification_payment_service.py`: it selects the `auth_user`-linked party's primary `provider="stripe"` `cus_` plus `metadata.default_payment_method_id` `pm_`, then passes both identifiers explicitly to the later manual-capture PaymentIntent. `tests/test_data_verification_payment.py` in Chunk B must prove that exact predicate and explicit pair remain the authorization input. Stripe Customer invoice settings are not part of readiness or charging authority.

A Stripe Connect identity uses the distinct `stripe_connect` provider and an `acct_...` external identifier. It represents where seller payouts go. It is never a Stripe Customer, never a verification-charge payment method, and never a fallback when the ordinary identity is absent or invalid.

There is currently no supported write or onboarding route that establishes the ordinary identity. The frontend has no Stripe JS dependency. The smallest safe design is therefore a server-created, Stripe-hosted Checkout Session in `mode=setup`. ai.market redirects the browser to the returned Stripe Checkout URL and never renders card fields, handles a client secret, or adds Stripe JS.

The existing webhook endpoint remains the only Stripe webhook endpoint. Its signature verification, synthetic-event suppression, event routing, and durable deduplication remain mandatory. Platform-account `checkout.session.completed` must be subscribed and classified critical and retryable under the release evidence in section 11. The authenticated return path is a second reconciliation trigger, not a substitute for the signed webhook.

## 3. Roles, gates, and fixed origins

### 3.1 Authorization and exact step-up transport

All three endpoints first require a valid signed-in application session, the current seller-provisioning permission, `totp_enabled=true`, and an unambiguous `auth_user` `PartyIdentity` that maps the authenticated user to the seller party in the active provisioning context. The server derives `auth_user_id` and `party_id`; the caller cannot supply either. Before any default-loader/readiness read, attempt or audit write, or Stripe call, the server must also prove that the feature gate is valid and the derived party is the single party in `STRIPE_PAYIN_ONBOARDING_PILOT_PARTY_IDS`. Flag-off, invalid pilot configuration, and a derived non-pilot party return the same HTTP 404 not-found response and stable internal code `PAYIN_ONBOARDING_DISABLED`. They are otherwise indistinguishable and produce no lifecycle or security audit event.

The endpoint-specific requirements are exact:

- `GET .../readiness` is non-sensitive. It requires the shared checks above, but no fresh step-up token.
- `POST .../setup-sessions` requires the shared checks plus header `X-PayIn-Reauth` containing the existing user-scoped `action_reauth` JWT. The backend verifies it for the authenticated user with `app/core/security.py:verify_reauth_token` before any attempt/audit write or Stripe work.
- `POST .../setup-sessions/reconcile` requires the shared checks plus a newly obtained `X-PayIn-Reauth` token after the hosted return. The return page invokes the existing `app/dashboard/settings/ReauthModal.tsx` before it calls reconcile.
- A correctly signed webhook may invoke the finalizer without a user token only because the attempt and Session were created under step-up and the finalizer revalidates every stored and Stripe-object binding. Signature verification is not a substitute for those bindings.

The existing token is issued through `/api/v1/auth/generate-reauth-token` plus `/api/v1/auth/reauth`, is stateless, and has the existing fixed 60-second validity. It is not one-time. It may be reused for the same or another authorized POST only while valid and only by the same authenticated user; attempt, generation, and Session idempotency prevent duplicate work. Missing, malformed, expired, or cross-user tokens fail before database/Stripe work. `X-PayIn-Reauth` is explicitly redacted at ingress and is never persisted, logged, audited, analyzed, placed in browser storage, or included in an error report or fixture.

No endpoint accepts a caller-provided user ID, party ID, customer ID, payment-method ID, Stripe account, origin, success URL, or cancel URL. An absent, ambiguous, revoked, cross-party, or non-seller mapping fails before a Stripe call.

### 3.2 Independent default-off gate

Add the backend setting:

```text
STRIPE_PAYIN_ONBOARDING_ENABLED=false
STRIPE_PAYIN_ONBOARDING_PILOT_PARTY_IDS=<default empty; exactly one approved opaque party UUID while pilot-only>
STRIPE_PAYIN_PLATFORM_ACCOUNT_ID=<required ordinary platform acct_ ID when enabled>
```

The enabled setting is false and the pilot allowlist is empty by default in every environment. While this is pilot-only, enabled configuration is valid only when the parsed allowlist contains exactly one canonical opaque party UUID that is explicitly approved for that environment. Missing, empty, malformed, duplicate, multiple, or cross-environment values fail startup closed; no value is inferred from a request or from Stripe. `STRIPE_PAYIN_PLATFORM_ACCOUNT_ID` is also required when enabled and must be one canonical `acct_` identifier for the ordinary platform account.

Before serving this flow, the ordinary Stripe API key must retrieve its platform Account and the returned Account ID must equal `STRIPE_PAYIN_PLATFORM_ACCOUNT_ID`. A wrong key, wrong account, connected-account option/header, or unproved account context keeps the flow unavailable. This `acct_` value is platform configuration only. It is pinned on an attempt as expected execution context, but is never a PartyIdentity, caller input, user response, audit value, readiness fact, or substitute for the separate `stripe_connect` payout identity.

The enabled setting is independent of `DATA_VERIFICATION_ENABLED` and is checked server-side on all three endpoints in the order fixed by section 3.1. When disabled or unavailable, the standard not-found response prevents the unfinished or non-pilot surface from being discoverable through normal product behavior.

The frontend may render the page or navigation only when its server-provided capability says onboarding is enabled, but frontend hiding is not an authorization control. Enabling `STRIPE_PAYIN_ONBOARDING_ENABLED` must not enable scans, quotes, PaymentIntent creation, or verification publication. `DATA_VERIFICATION_ENABLED` may not be enabled merely because onboarding is enabled or complete.

### 3.3 Fixed public origin

Checkout success and cancel URLs are built only from the existing `settings.FRONTEND_URL`; this amendment adds no parallel public-origin setting. When onboarding is enabled, `settings.FRONTEND_URL` must parse and serialize as one canonical origin on the environment's deploy allowlist: HTTPS, with credentials absent and with no path, query, or fragment. Production is exactly `https://ai.market`. A loopback `http://localhost` origin is allowed only in tests. Invalid or unapproved values fail startup closed. The origin is never derived from `Host`, `Origin`, `Referer`, forwarding headers, query parameters, or request JSON.

For production the path shapes are fixed as follows; the deployment supplies only the pre-approved origin:

```text
success: {CANONICAL_PUBLIC_ORIGIN}/dashboard/data-verification/payment-method/return?attempt={setup_attempt_id}&session_id={CHECKOUT_SESSION_ID}
cancel:  {CANONICAL_PUBLIC_ORIGIN}/dashboard/data-verification/payment-method?result=cancelled&attempt={setup_attempt_id}
```

`setup_attempt_id` is an application-generated opaque UUID. `{CHECKOUT_SESSION_ID}` is Stripe's literal server-side Checkout placeholder. Query strings on these paths are redacted from access and application logs. Redirect destinations are never returned by or accepted from the caller.

## 4. Exact API and frontend contracts

All JSON schemas reject unknown keys. The exact feature, pilot, TOTP, ownership, account-context, and endpoint-specific step-up checks in section 3.1 apply before the behavior described below.

### 4.1 Readiness

```text
GET /api/v1/data-verification/payment-method/readiness
response schema: DataVerificationPayInReadinessV1
```

The successful response is non-sensitive and contains exactly the following shape. This example is state-illustrative for `setup_required`; the booleans are computed from `state`, and `can_replace_payment_method` is true only for `ready`:

```json
{
  "version": "data_verification_payin_readiness_v1",
  "state": "setup_required | setup_pending | ready | blocked",
  "can_start_setup": true,
  "can_replace_payment_method": false,
  "message": "plain English from the fixed copy table"
}
```

The booleans must agree with `state`. `ready` means the current party passes the exact loader predicate owned by sections 2 and 5.1. `setup_required` means no usable ordinary mapping exists and setup may start. `setup_pending` means the current party has a reusable open current-generation attempt or reconciliation is retrying. `blocked` means an identity invariant or non-retryable ownership/configuration problem needs operator investigation. The response contains no `cus_`, `pm_`, `acct_`, `cs_`, `seti_`, email, billing value, last four digits, brand, expiry, address, cardholder name, or Connect status.

### 4.2 Create or reuse a hosted setup session

```text
POST /api/v1/data-verification/payment-method/setup-sessions
request schema: DataVerificationPayInSetupCreateV1
response schema: DataVerificationPayInSetupSessionV1
required header: X-PayIn-Reauth: <existing 60-second action_reauth JWT>
```

The request body is exactly:

```json
{"version": "data_verification_payin_setup_v1"}
```

It contains no other fields. In particular, it has no reauth token, URL, party, user, customer, payment method, email, or Stripe-account override. The header is verified and redacted exactly as section 3.1 requires.

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
- `payment_method_types=["card"]`;
- no `setup_intent_data.usage` field; the pinned Stripe Python SDK does not accept it, and the retrieved Checkout-created SetupIntent must later validate with `usage="off_session"`;
- the fixed success and cancel URLs from section 3.3;
- `client_reference_id=setup_attempt_id`;
- exact metadata `purpose="data_verification_payin"`, `contract_version="v1"`, and opaque `setup_attempt_id`, `party_id`, and `user_id` bindings on the Checkout Session and SetupIntent; and
- the stored Session-operation Stripe idempotency key scoped to the setup attempt.

The exact `user_id` metadata key preserves the existing webhook helper's synthetic-routing contract. The handler still applies its existing synthetic suppression before local attempt lookup, then treats metadata only as one binding to compare with stored `auth_user_id`; it does not weaken suppression or trust metadata alone. Checkout setup mode with the existing Customer must attach the created PaymentMethod to that same Customer.

The application does not send name, email, phone, address, source data, listing data, D6, or a Connect account to prefill Checkout. Stripe may collect the billing fields required by its hosted product, but ai.market neither requests those values back nor stores or logs them.

### 4.3 Authenticated return reconciliation

The frontend return page reads the fixed `attempt` and `session_id` query values, does not log or analyze them, and removes them from visible browser history with `history.replaceState`. It then invokes the existing `ReauthModal`, obtains a new action-reauthentication token after the hosted return, and only then calls:

```text
POST /api/v1/data-verification/payment-method/setup-sessions/reconcile
request schema: DataVerificationPayInSetupReconcileV1
response schema: DataVerificationPayInReconcileResultV1
required header: X-PayIn-Reauth: <new existing 60-second action_reauth JWT obtained after return>
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
/dashboard/settings
/dashboard/data-verification/payment-method
/dashboard/data-verification/payment-method/return
```

The existing Settings page is the discoverability seam. Only after its authenticated call to readiness succeeds may it render a plain-English entry/card headed `Payment method for verification charges`; the card links to or hosts the dedicated flow. A flag-off, invalid-config, or non-pilot HTTP 404 hides the entry without revealing why. The Settings page and dedicated flow use the authenticated `api/client.ts` transport through `api/dataVerificationPayin.ts`; `lib/api.ts` is a public/server-fetch helper and must not be used. Creation and post-return reconciliation reuse the existing `ReauthModal`; readiness does not prompt for reauthentication.

The exact user-facing copy is:

| State or element | Copy |
| --- | --- |
| Heading | `Payment method for verification charges` |
| Explanation | `Add a payment method that ai.market can use for data-verification charges. This is separate from Stripe payouts.` |
| Hosted handoff | `You will continue securely on Stripe. ai.market does not collect or store your card details, and no verification charge is made during setup.` |
| Setup step-up | `Confirm it is you to continue. This confirmation is valid for 60 seconds.` |
| Return step-up | `Confirm it is you again to finish adding your payment method.` |
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

This is the exact application default selected by `app/services/data_verification_payment_service.py`. That service must continue to pass this `cus_` and `pm_` pair explicitly to the later manual-capture PaymentIntent. Neither onboarding nor charging reads or writes `Customer.invoice_settings.default_payment_method`.

`provider="stripe_connect"`, `external_id="acct_..."`, Connect account fields, and payout readiness are excluded from every lookup and write in this flow. An `acct_` value observed in an ordinary identity is an invariant violation and produces `blocked`; it is never repaired by reinterpretation.

### 5.2 Customer create/reuse

Under a per-party database lock, creation first checks for the one primary ordinary Stripe identity:

- If a valid `cus_` identity exists, reuse that Customer. Never create a replacement Customer merely to replace a payment method.
- If no such identity exists, create one bare ordinary Stripe Customer with a per-party idempotency key. Send only the opaque party binding and `purpose=data_verification_payin`, `contract_version=v1` as Stripe metadata. Do not send an email or billing/profile values.
- Keep the returned `cus_` only on the bounded setup attempt until successful finalization. The final transaction inserts the primary ordinary identity with both the `cus_` external ID and its one-key `pm_` metadata; it never exposes an incomplete primary ordinary identity to the default loader.
- If an invalid or duplicate ordinary identity exists, stop as `blocked`; do not select one by age, overwrite it, demote it, or use a Connect identity.

The Customer and Checkout Session are created on the platform's ordinary Stripe account with the environment's ordinary Stripe credentials. Before the flow is served, those credentials must resolve to the configured `STRIPE_PAYIN_PLATFORM_ACCOUNT_ID`. Every create, retrieve, expire, and finalizer call uses that same ordinary API-key context and never passes a connected-account option or header. Session, SetupIntent, and PaymentMethod do not have an account-ID field; account context is proven by the prevalidated API-key identity, absence of any connected-account option, `event.account` being absent, and each object's `livemode`, not by an impossible child-object account comparison.

Creation crosses Stripe and database boundaries in this fixed order:

1. in one database transaction, lock the party lineage; resolve prior-generation handling under section 6.1; create the one current local attempt; store its immutable party, user, purpose, contract, generation, environment/livemode, expected platform-account, and operation bindings plus both exact idempotency keys; and commit that durable row before the first Stripe call;
2. create or retrieve the bare Customer with the stored Customer-operation idempotency key, then persist its `cus_` on that attempt;
3. create or retrieve the fixed Checkout Session with the stored Session-operation idempotency key, then persist its `cs_` and mark the attempt `open`; and
4. return the retrieved Session URL without persisting or logging the URL.

The two keys are deterministic as well as stored: `dvpayin:customer:v1:{setup_attempt_uuid_hex}` and `dvpayin:session:v1:{setup_attempt_uuid_hex}`, where the UUID is lowercase hexadecimal without hyphens. Each is printable lowercase ASCII, no more than 64 characters, collision-separated by operation domain, immutable after the pre-call commit, and reused forever only for that attempt and that operation. A retry, process crash, database timeout, or ambiguous Stripe response must reload the stored key; it cannot derive a different key or borrow one from another generation.

Within Stripe's idempotency guarantee, retrying the same stored key must retrieve the same operation outcome and allow the exact returned `cus_` or `cs_` to be persisted. If the Customer outcome remains unknown after that guarantee can establish it and the attempt has no persisted `cus_`, the attempt becomes `blocked`: no fresh Customer create, successor attempt, recent-object search, metadata guess, email match, Connect lookup, or arbitrary adoption is permitted. A known persisted `cus_` may remain an `orphan_customer` candidate and retry only through the same proven attempt/account/binding path in section 6.3.

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
- immutable positive party-scoped `generation` and nullable write-once `superseded_by_attempt_id`;
- stored immutable `customer_idempotency_key` and `session_idempotency_key` with the exact derivation in section 5.2;
- expected `customer_id` (`cus_`) and exact `checkout_session_id` (`cs_`);
- fixed `purpose`, `contract_version`, expected environment/livemode, and expected `STRIPE_PAYIN_PLATFORM_ACCOUNT_ID` execution context;
- state `creating | open | reconciling | ready | cancelled | expired | failed | orphan_customer | blocked`;
- retry-safe timestamps, last fixed error code, and optimistic version.

It does not store a Checkout URL, client secret, payment-method details, email, name, address, raw billing value, raw webhook body, or free-form Stripe error. It need not persist `pm_` or `seti_`; those are retrieved and validated during reconciliation, and the finalized `pm_` is stored only in the ordinary PartyIdentity metadata.

Party generation is exact and monotonic. Under the party-lineage lock, generation 1 is first; each successor is prior generation plus one. The current generation is the maximum stored generation for the party and is the only attempt whose `superseded_by_attempt_id` is null. When a successor is committed, its predecessor's `superseded_by_attempt_id` is set once to that successor ID in the same transaction and can never be cleared or changed. A finalizer may update PartyIdentity only for the current generation while that field is null.

The database enforces unique `(party_id, generation)`, at most one row per party with `superseded_by_attempt_id IS NULL`, and a foreign key from `superseded_by_attempt_id` to an attempt. Under the lineage lock, service code verifies that the referenced successor has the same party and exactly generation plus one; it never infers current generation from timestamps.

Before creating a successor, the service must retrieve and reconcile the prior Session under its pinned account context:

1. If the prior Session is still open, unexpired, and safe, reuse it and return its currently retrieved URL; no successor is created.
2. If it is complete, reconcile/finalize that prior attempt first. A later deliberate replacement may then start from the resulting ready state.
3. If a new Session is necessary, explicitly expire the prior Session when Stripe still permits expiry, retrieve it again, and verify a terminal expired/cancelled state. If Stripe already reports a terminal state, retrieve and verify it. Local time expiry alone is never terminal proof.
4. If terminal state cannot be established, leave the current generation retryable or blocked; do not create a successor.

Only after terminal proof may the transaction create exactly one successor and mark the prior attempt superseded. Database locking, lineage uniqueness, and the stored Stripe idempotency keys must prove that duplicate requests cannot create two canonical ordinary Customers or two active Sessions. A late completion for attempt A after successful successor B is a fixed `superseded_generation` no-op/fail-closed result: it cannot change B's PartyIdentity mapping, readiness, or attempt state.

### 6.2 Two completion triggers, one finalizer

Both triggers invoke the same `finalize_data_verification_payin_setup(setup_attempt_id)` service:

1. the authenticated return reconciliation in section 4.3; and
2. the existing signed webhook endpoint after its existing durable deduplication accepts `checkout.session.completed`.

The webhook handler first preserves the existing synthetic-routing suppression, then maps the event to the local attempt through exact Session metadata using `user_id` plus the stored Checkout Session ID. Existing deduplication may mark the critical event durably complete only after the finalizer reaches a durable terminal result, including a durable `superseded_generation` no-op; a transient Stripe or database failure returns a retryable failure and must not consume the event. The handler never trusts event metadata alone and never writes PartyIdentity directly.

The finalizer retrieves the Checkout Session, expanded SetupIntent, and PaymentMethod from Stripe using the server's ordinary platform account context. Before any final write, it validates all of these conjunctively:

1. the attempt belongs to the currently authenticated `auth_user` and party for a return call, or the signed event's Session maps to that stored attempt for a webhook call;
2. stored purpose is `data_verification_payin`, contract version is `v1`, and Session, SetupIntent, and local bindings agree on purpose, version, attempt, metadata `user_id` equal to stored `auth_user_id`, and party;
3. the supplied, event, retrieved, and stored Checkout Session IDs are equal;
4. Checkout `mode` is exactly `setup` and its completion state is complete;
5. while holding the party-lineage lock, the attempt is the current maximum generation and has no `superseded_by_attempt_id`; an older or superseded attempt exits as the fixed no-op before a mapping write;
6. the Session Customer equals the attempt Customer and has a `cus_` prefix; if an ordinary identity already exists, its `external_id` must equal that Customer, while a first setup requires that no ordinary identity appeared after the attempt was created;
7. the Session's SetupIntent is present, belongs to that same Customer, has status `succeeded`, and its retrieved `usage` is exactly `off_session`;
8. the selected PaymentMethod has a `pm_` prefix, is attached to and retrievable under that same Customer, and is of the approved `card` type;
9. the Session, SetupIntent, and PaymentMethod each expose `livemode` equal to the attempt's expected environment;
10. every call used the same ordinary API key already proved to resolve to the attempt's expected platform account, no connected-account request option/header was passed, and a webhook's `event.account` is absent; and
11. the party still has the same valid `auth_user` ownership and at most one primary ordinary Stripe identity.

The Session, SetupIntent, and PaymentMethod have `livemode` but no account-ID field. The finalizer must not assert nonexistent child-object account equality. Account isolation is the conjunctive API-key identity, attempt pin, no connected-account option/header, absent `event.account`, and livemode proof above.

Any failed equality or ownership check is a non-retryable substitution/security failure for that attempt. It never adopts the presented Customer or PaymentMethod, never changes the old default, and never falls back to an `acct_` identity. Transient retrieval failures leave the attempt retryable and return `pending`.

### 6.3 Idempotent finalization and failure ordering

Stripe and the application database cannot share one transaction. The required order is:

1. retrieve and validate all Stripe objects without a database write;
2. lock the party lineage, attempt, and ordinary identity and reread all ownership, current-generation, supersession, and uniqueness invariants;
3. in one database transaction, insert the first ordinary PartyIdentity or replace the existing ordinary PartyIdentity metadata with exactly `{"default_payment_method_id":"pm_..."}`, mark that current attempt `ready`, and commit; and
4. reread through the exact data-verification default payment loader and return `ready` only if it selects the same party, Customer, and PaymentMethod.

Finalization mutates only PartyIdentity metadata and attempt state in that atomic application transaction. It never writes `Customer.invoice_settings.default_payment_method` or any other Stripe Customer default. Checkout has already attached the PaymentMethod to the same Customer, and later verification charges pass the selected `cus_` and `pm_` explicitly. The attempt lock/version, generation check, exact comparisons, and final metadata replacement make duplicate or reordered webhook and return calls converge without a cross-system default.

Failure behavior is fixed:

- Stripe retrieval or validation fails before the application transaction: leave PartyIdentity unchanged and retry the same attempt only for a retryable fixed error.
- The application transaction fails: the attempt remains non-ready; retry retrieves and validates the same succeeded SetupIntent and attached PaymentMethod, then repeats only the application transaction. There is no second-system repair step.
- The database is ready and a duplicate event for that same current generation arrives: reread and return success only when Customer and PaymentMethod equality still hold; otherwise fail closed for reconciliation.
- A valid late event for superseded A arrives after B is current or ready: return the durable fixed `superseded_generation` no-op, leave B and the mapping unchanged, and allow webhook deduplication to record that terminal no-op.
- A Customer is known and persisted but identity insert or Session creation cannot complete: retain an `orphan_customer` attempt bound to the stored key, exact returned Customer, party, account context, and metadata. Retry only that proven operation. If no `cus_` was persisted and the outcome can no longer be established under Stripe's idempotency guarantee, mark `blocked`; never issue a fresh create, search recent Customers, guess, or adopt an arbitrary object.

No failure path creates a PaymentIntent, confirms a charge, detaches a payment method, or changes Stripe Connect.

## 7. Replacement and recovery

Replacement uses the same POST and finalizer with the existing ordinary `cus_` Customer. The current PartyIdentity `pm_` remains the application default until the replacement SetupIntent has succeeded and section 6 validation completes. Checkout must attach the replacement PaymentMethod to that same Customer. Cancel, expiry, browser loss, webhook delay, return-before-webhook, webhook-before-return, duplicate calls, and temporary Stripe failure leave the old mapping usable.

Slice 1 supports add and replace only. It does not support removal, detach, deletion, clearing the application default, selecting among saved methods, or editing billing details. A failed or cancelled first setup remains `setup_required`; a failed or cancelled replacement remains `ready` with the prior mapping. Expired Sessions are never revived; a new attempt can be created only after section 6.1 proves the prior Session terminal and records exact supersession.

Setup makes no charge and creates no PaymentIntent. Later verification charges remain exclusively governed by the parent Gate 1 manual-capture flow.

## 8. Threat model, forbidden fields, and audit

| Threat | Required control | Failure result |
| --- | --- | --- |
| Authentication, TOTP, step-up, pilot, or seller-role bypass | Derive user/party, require the single pilot and TOTP on all endpoints, and verify the existing 60-second action-reauth header on both user POSTs. | 401/403 or indistinguishable not-found before readiness/state/audit/Stripe work. |
| Connect/pay-in identity confusion | Exact provider and prefix checks; fixed platform account context; never inspect `stripe_connect` as a candidate. | `blocked`; no adoption or mutation. |
| Open redirect, header poisoning, or caller URL injection | Canonical allowlisted origin and fixed paths; strict request schemas; Stripe-host allowlist on returned Checkout URL. | Reject before session creation or redirect. |
| Cross-user, cross-party, cross-session, or cross-account substitution | Stored attempt/session/customer bindings plus conjunctive Session, SetupIntent, PaymentMethod, user, party, account, purpose, and version equality. | Fixed security failure; old default unchanged. |
| Test/live object confusion | Environment-derived credentials and livemode equality across every retrieved object. | Non-retryable mismatch; no write. |
| Forged, replayed, duplicated, or reordered events | Existing webhook signature verification and durable dedupe plus one idempotent finalizer. | Invalid signatures rejected; valid duplicates converge. |
| Late or competing attempt generation | Monotonic generation, verified prior-Session terminal state, write-once supersession, and current-generation finalizer lock. | Stale generation is a durable no-op and cannot replace the current mapping. |
| Duplicate Customers or primary identities under concurrency/crash | Pre-call committed operation keys/bindings, per-party lock, lineage uniqueness, existing identity uniqueness, and new partial unique index. | One canonical object or fail closed; unknown Customer outcome becomes blocked. |
| Hosted-page or frontend skimming regression | No Stripe JS, Elements, iframe, app card input, client secret, or billing display. | Frontend test/build failure; release blocked. |
| Sensitive payment data in telemetry or state | Strict schemas, response minimization, query redaction, fixed error codes, and captured-log/analytics tests. | Release blocked and affected telemetry treated as a security incident. |
| Application mapping/Stripe attachment mismatch | PartyIdentity loader remains readiness authority; finalizer accepts only the attached owned PaymentMethod and never writes a Stripe Customer default. | Verification stays blocked; no newest-value choice or repair mutation. |

The following are forbidden in application logs, audit events, analytics, error tracking, application state, PartyIdentity metadata other than the one allowed key, and this specification's operational evidence:

- card number, CVC, magnetic-stripe or cryptogram data, fingerprints, last four digits, brand, expiry, wallet details, bank data, or any other payment credential;
- Stripe client secret, Checkout URL, raw webhook body, signature secret, API key, `X-PayIn-Reauth` value, OTP, or browser query string;
- email, name, phone, postal address, IP-derived profile, raw billing details, or Stripe billing/profile response;
- source data, source metadata, D6, listing content, scan findings, locator, or free-form source/Stripe error text; and
- caller-provided redirect URL, Customer, PaymentMethod, Connect account, user, or party value.

Security and lifecycle audit events use local opaque `setup_attempt_id`, `party_id`, and `auth_user_id` only, plus fixed event name, fixed outcome/error code, environment label, actor type, and timestamp. They do not contain `cus_`, `pm_`, any `acct_` including `STRIPE_PAYIN_PLATFORM_ACCOUNT_ID`, `cs_`, `seti_`, Checkout URL, reauth token, OTP, billing data, or free text. Flag-off, invalid-config, and non-pilot requests emit none of these events. Required fixed events are `payin_setup_requested`, `payin_setup_reused`, `payin_setup_returned`, `payin_setup_webhook_received`, `payin_setup_ready`, `payin_setup_failed`, `payin_setup_substitution_rejected`, `payin_setup_superseded_noop`, and `payin_setup_orphan_customer`.

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

**Boundary:** Add the default-off gate, single-party pilot configuration, platform-account configuration validation, generation/supersession attempt model, pre-call durable operation keys, partial unique index, exact-loader-backed readiness response, and endpoint-specific authorization checks. Stripe object creation and frontend work are excluded.

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

**Boundary:** Implement the strict POST schemas, bare Customer creation/reuse, Stripe-hosted setup Session, authenticated reconciliation, critical/retried webhook route, shared finalizer, replacement, and exact default-loader integration owned by this amendment. No PaymentIntent or charge is allowed in this chunk.

### Chunk C — hosted-redirect frontend

**Depends on:** Chunk B contract fixtures.

**Repository:** `ai-market-frontend`

**Files:**

- `app/dashboard/settings/page.tsx`
- `app/dashboard/settings/page.test.tsx`
- `app/dashboard/data-verification/payment-method/page.tsx` (new)
- `app/dashboard/data-verification/payment-method/return/page.tsx` (new)
- `components/DataVerificationPaymentMethod.tsx` (new)
- `api/dataVerificationPayin.ts` (new)
- `api/dataVerificationPayin.test.ts` (new)
- `types/index.ts`
- `app/dashboard/data-verification/payment-method/page.test.tsx` (new)
- `app/dashboard/data-verification/payment-method/return/page.test.tsx` (new)

**Boundary:** Use the existing authenticated `api/client.ts` only through the new domain module; do not use `lib/api.ts`. Add the Settings entry only after readiness succeeds, hide flag-off/non-pilot not-found, render readiness and fixed copy, reuse the existing `ReauthModal` before both POST actions, navigate top-level to the server-returned Stripe-hosted URL, obtain a new step-up after return, reconcile, redact/remove query values, and cover success/cancel/pending/error. Do not add a Stripe dependency, payment form, iframe, or card display.

### Chunk D — integration and release evidence

**Depends on:** Chunks A-C deployed with both flags false and every review/checkpoint in section 11 satisfied.

**Repositories:** no new production files. Evidence-only fixtures or runbook records require their own exact manifest at dispatch.

**Boundary:** Run the real Stripe test-mode setup journey, end-to-end loader proof, named-pilot confirmation, signed-in browser proof, flag-order rehearsal, and rollback rehearsal. No production enablement occurs inside the chunk.

## 10. Acceptance criteria and tests

Each item is independently required.

1. **Shared auth, TOTP, and ownership:** unauthenticated, `totp_enabled=false`, non-seller, missing/revoked `auth_user`, ambiguous party, other-user attempt, and other-party attempt fixtures fail before readiness/attempt/audit/Stripe work. The readiness GET succeeds for the authenticated eligible pilot without a reauth header.
2. **Pilot and configuration permutations:** flag-off, empty/missing/malformed/duplicate/multiple/cross-environment pilot values, missing/malformed platform-account ID, and an otherwise eligible non-pilot party all return or remain indistinguishable from flag-off and cause zero loader reads, attempts, audits, frontend capability, or Stripe mock calls. Caller-supplied party values and unknown keys are rejected and cannot select the pilot.
3. **Exact action reauth:** setup POST rejects missing, malformed, expired, and cross-user `X-PayIn-Reauth` before writes or Stripe. A valid user-scoped token works only within the existing 60 seconds; reuse inside that window is allowed and idempotent rather than falsely treated as one-time. The hosted-return test proves the pre-redirect token expires, the page opens `ReauthModal`, and reconcile succeeds only with a newly obtained token.
4. **Flag independence:** all three endpoints fail closed under `STRIPE_PAYIN_ONBOARDING_ENABLED=false`; Settings and dedicated frontend surfaces are absent. `DATA_VERIFICATION_ENABLED` stays false and controls none of onboarding.
5. **Origin and URL pinning:** request schemas reject success/cancel/return URL fields and unknown keys. Host/Origin/forwarded-header attacks cannot change URLs. Enabled configuration accepts only the allowlisted canonical HTTPS `settings.FRONTEND_URL` with no credentials/path/query/fragment, plus the localhost-only test exception; production is exactly `https://ai.market`. Only the exact approved Stripe Checkout HTTPS hosts pass the returned-URL guard.
6. **Customer create/reuse and Connect separation:** the first eligible call creates one bare `cus_`; later and concurrent calls reuse it. Existing `acct_`/`stripe_connect` data is neither read as pay-in readiness nor changed. Captured Stripe requests contain no email, profile, billing, listing, D6, source, or free text.
7. **Durable pre-call keys and crashes:** the attempt, bindings, generation, expected account/environment, and both exact deterministic/stored operation keys are committed before the first Stripe call. Fault injection after that commit, before/after each Customer and Session call, after an ambiguous timeout, and before/after each ID persist proves every retry reloads the same key and resolves the same `cus_`/`cs_`. No duplicate Customer or active Session appears. An unknown Customer result beyond the idempotency guarantee with no persisted `cus_` becomes blocked and never issues a fresh create or guess/adopt.
8. **Generation and A/B race:** concurrent successor requests produce one next generation. Open A is reused; complete A is reconciled; a new Session is created only after A is explicitly expired when necessary and re-retrieved terminal. Inject expired A, successful B, then late complete A across return-before-webhook, webhook-before-return, duplicate, and reordered-event permutations. A is a durable `superseded_generation` no-op and cannot change B's PartyIdentity mapping, readiness, or state.
9. **Checkout create contract:** captured create parameters contain `mode="setup"`, `payment_method_types=["card"]`, the fixed Customer/URLs/metadata, and no `setup_intent_data.usage`, connected-account option/header, email, or caller value. Checkout attaches the resulting PaymentMethod to the same Customer; retrieved `SetupIntent.usage!="off_session"` fails closed.
10. **Substitution and completion:** wrong attempt, Session, `user_id`, party, Customer, purpose, contract version, generation, SetupIntent, PaymentMethod, or binding changes nothing and emits only the fixed opaque audit event. `mode!=setup`, incomplete Session, absent/unsucceeded SetupIntent, unattached/wrong-customer/wrong-type PaymentMethod, and invalid prefixes fail closed.
11. **Platform account and livemode:** before serving the flow, the ordinary API key resolves to configured `STRIPE_PAYIN_PLATFORM_ACCOUNT_ID`. Wrong key, wrong Account ID, connected-account option/header, webhook `event.account` present, and every Session/SetupIntent/PaymentMethod livemode mismatch fail closed. Tests assert no nonexistent child-object account field and never expose or audit the configured `acct_`.
12. **Webhook signature, routing, subscription, and dedupe:** invalid signatures are rejected before lookup; exact `user_id` Session metadata works with existing synthetic routing without weakening suppression; repeated/reordered valid platform-account `checkout.session.completed` events use durable dedupe and one finalizer; transient failures remain critical/retryable; return and webhook converge. Release evidence separately proves the endpoint subscription and event classification.
13. **Replacement and sole application default:** a successful replacement reuses `cus_` and atomically changes only PartyIdentity `metadata.default_payment_method_id` plus attempt state. Captures prove zero `Customer.invoice_settings.default_payment_method` mutation and no second default-authority path. Cancelled, expired, failed, or pending replacement preserves the old `pm_`; there is no remove/detach/clear path.
14. **Application transaction ordering:** fault injection before/after object retrieval, lineage lock, identity insert/update, and database commit proves section 6.3. Retries validate the same attached method and repeat only the application transaction; no manual SQL or Stripe Customer-default repair is part of recovery.
15. **Exact default-loader integration:** readiness becomes `ready` only when `app/services/data_verification_payment_service.py` selects the authenticated party's primary ordinary `cus_` plus finalized `pm_`, and later manual-capture code receives both explicitly. A Connect identity alone, empty metadata, malformed prefix, duplicate identity, unattached method, or mapping mismatch is not ready.
16. **Migration uniqueness:** empty, single-identity, many-party, nullable/non-primary, and duplicate-primary fixtures prove the partial index. Duplicate preflight aborts without changing rows or schema; downgrade/re-upgrade is tested in a disposable database; existing `(provider, external_id)` uniqueness remains.
17. **Settings and frontend behavior:** Settings hides the entry until readiness succeeds; flag-off/non-pilot not-found hides it, while the eligible pilot sees the exact `Payment method for verification charges` entry. Tests prove calls use `api/dataVerificationPayin.ts` over `api/client.ts`, never `lib/api.ts`; success, cancel, pending, retryable error, blocked, return rechallenge, and network-loss states render fixed copy. Query identifiers are removed from visible history and analytics.
18. **No card surface or charges:** dependency/build/DOM searches prove no Stripe JS, Elements, iframe, client secret, card/billing input, or card display. Captured Stripe mocks and the real test journey show Checkout setup only: zero PaymentIntent creation, confirmation, capture, refund, Customer-default mutation, or Connect mutation.
19. **Forbidden data and privacy:** captured request, response, DB row, log, audit, analytics, error-report, browser-console, browser-storage, and webhook fixtures contain none of section 8's forbidden fields. Reauth headers/OTPs and platform Account ID never enter logs or audit; audit payloads equal the fixed opaque schema.
20. **Parent and finite-scope invariants:** parent manual-capture payment tests, webhook tests, S1590 privacy/exfiltration searches, migration tests, and feature-off tests remain green. No customer-to-cloud scan manifest, D6 contract, corpus field, publication rule, pricing rule, or verification state transition changes.

## 11. Review and release checkpoints

Passing tests is necessary but insufficient. Static review, deployment, Stripe test evidence, database state, and signed-in browser proof are independent and conjunctive.

1. **Exact-SHA amendment review:** after this document is committed, Kimi and GLM must review that exact runbooks SHA under the active directive and record their exact model identity, verdict, mandates, and immutable response references. Any document edit invalidates the reviews. CC is not contacted or counted while Max's 12-hour hold is active; after expiry, only the then-current directive determines whether CC review is also required.
2. **Build dispatch:** no product repository work starts until the amendment has the required review result and a dispatch names the exact backend/frontend baselines and one chunk's file manifest. This document itself does not dispatch a build.
3. **Migration preflight:** the release candidate runs the duplicate query against a read-only production snapshot or approved read-only production transaction. Any duplicate blocks migration and requires a separately reviewed repair; no hand SQL.
4. **Both flags false:** deploy migration and code with `STRIPE_PAYIN_ONBOARDING_ENABLED=false` and `DATA_VERIFICATION_ENABLED=false`. Prove old data-verification and payout behavior unchanged before either gate is considered.
5. **Exact pilot, origin, and account configuration:** release evidence proves enabled configuration parses exactly one explicitly approved opaque party UUID, `settings.FRONTEND_URL` is the canonical allowlisted origin, and the ordinary API key resolves to the configured `STRIPE_PAYIN_PLATFORM_ACCOUNT_ID`. Missing/malformed/multiple/cross-environment pilot values, wrong key/account, connected-account options, or a noncanonical origin fail closed. Evidence may name the approved opaque local party reference but must not expose API keys, Stripe object IDs, or billing data.
6. **PR #48 same-release hold:** the dependency is [`aidotmarket/ai-market-frontend` PR #48](https://github.com/aidotmarket/ai-market-frontend/pull/48), currently **OPEN/DRAFT**, titled `feat: add verified shape explainer page`, with current exact reviewed head `1a3b0088a0795072da12400dbf7ac78a4ecc7a1e`. It adds the public `/verified` explainer and links it from the footer, AIM Data, Find Data, Sell Data, and sitemap, with corrected optional-shape wording, `Verified shape` footer wording, and an explicit Terms link. It is deliberately held for the same S1590 release and must not be called merged. Before onboarding enablement, evidence must record its final exact merged SHA, the deployed frontend artifact/SHA, and browser verification of every required behavior. A PR number, current draft head, merge label, or later-release promise is not release evidence.
7. **Webhook subscription and retry evidence:** verify the existing Stripe webhook endpoint's configured event list includes platform-account `checkout.session.completed`, `event.account` is absent for that route, and backend handling classifies it critical/retryable with durable deduplication and unchanged synthetic suppression. Any provider event-list change requires separately reviewed configuration evidence attached to the release candidate; an assumed or dashboard-only unrecorded state is insufficient.
8. **Real Stripe test-mode journey:** using the release candidate and Stripe test mode, complete the hosted `mode=setup` flow through both a freshly reauthenticated return and a signed `checkout.session.completed` webhook. Prove Customer equality, `usage="off_session"`, succeeded SetupIntent, attached PaymentMethod, zero PaymentIntent/charge/Customer-default mutation, duplicate and superseded-event convergence, and exact-loader readiness without recording payment details in evidence.
9. **Signed-in browser proof:** with an authorized pilot seller-provisioning test identity whose TOTP is enabled, show flag-off and non-pilot absence, Settings hidden/visible behavior, fixed copy, pre-setup `ReauthModal`, top-level Stripe-hosted handoff, post-return `ReauthModal`, cancel, pending/retry, success, replacement, no card collection in ai.market, and clear separation from Stripe payouts. Synthetic or unauthenticated API output does not substitute for this proof.
10. **Named pilot confirmation:** through an authorized read-only check after test evidence passes, confirm the allowlisted opaque party is the approved pilot and has one `auth_user` identity, one primary ordinary `provider="stripe"` `cus_`, one `pm_` application default selected by the exact loader, and an unchanged separate `stripe_connect` `acct_` payout identity. Evidence records only pass/fail and opaque local references, not Stripe IDs or billing data.
11. **Flag order:** only after checkpoints 1-10 may an authorized operator enable onboarding for the one bounded pilot. Data verification remains off. `DATA_VERIFICATION_ENABLED` may be enabled later only after the parent Gate 1/Gate 2 payment and privacy checkpoints, named-pilot readiness, PR #48 final-merge/same-release proof, deployment proof, and signed-in verification journey all pass.
12. **Rollback rehearsal:** first disable `DATA_VERIFICATION_ENABLED`, then disable `STRIPE_PAYIN_ONBOARDING_ENABLED`; verify the Settings entry, setup surfaces, and endpoints are unavailable and no new attempts start. Reverting application code must not delete or detach Customers/payment methods or alter Connect. The uniqueness index remains unless a separately approved rollback proves no dependent writes and uses the reviewed migration downgrade. Existing finalized ordinary identities remain for explicit `cus_`/`pm_` payment reconciliation.
13. **No production enablement in this amendment:** authoring, review, merge, test-mode proof, and deployment with flags false do not authorize either production gate. Enablement requires a separate explicit operator action and its evidence.

## 12. Explicit non-goals

This amendment does not add or authorize:

- production enablement of onboarding or data verification;
- any charge, PaymentIntent, verification quote, authorization, capture, refund, or pricing change;
- Stripe Connect onboarding, payout-status changes, payout identity migration, or reuse of an `acct_` value;
- card fields, Stripe JS, Elements, an iframe, a client secret, or application collection/display of payment or billing data;
- payment-method removal, detach, clearing, selection UI, billing-profile editing, multiple ordinary Customers, or multiple primary ordinary Stripe identities per party;
- any read or mutation of `Customer.invoice_settings.default_payment_method`; PartyIdentity metadata is the sole application default;
- caller-supplied redirects, origins, party/user/customer/payment-method/account identifiers, or arbitrary metadata;
- manual production SQL, database repair, Stripe Dashboard edits, one-off scripts, customer adoption by guess, or email-based Customer matching;
- changes to the S1590 scan manifest, D6, AIM Data, allAI narrative, corpus, badge, publication, pricing, capture, cancellation, or refund contracts;
- a new webhook endpoint, replacement of signature verification/deduplication, or weakening of critical webhook retry behavior;
- a general billing wallet, buyer checkout, subscription, invoices, tax, non-card payment types, or general seller settings redesign; or
- general availability. The known-counterparty pilot and every parent release blocker remain.

## 13. Falsifiers and stop conditions

Implementation or release stops and returns to design review if any of the following is true:

- Stripe-hosted setup cannot establish an off-session-compatible method without adding Stripe JS or exposing a client secret to application code.
- The derived party cannot be checked against exactly one environment-approved pilot UUID before any readiness/state/audit/Stripe work.
- The existing 60-second action-reauthentication token cannot be verified for the authenticated user on both POSTs, or the return page cannot obtain a new token after Stripe.
- The ordinary API key cannot be proved to resolve to configured `STRIPE_PAYIN_PLATFORM_ACCOUNT_ID`, or ordinary platform Customer context cannot be distinguished conjunctively from Connect payout and test/live context.
- Existing data contains duplicate primary ordinary Stripe identities, or the new uniqueness rule cannot be added without data loss or winner selection.
- Concurrent calls can produce two canonical Customers, two primary identities, or conflicting current generations for one party; or a prior Session cannot be proved terminal before a successor.
- The durable attempt/bindings/idempotency keys cannot be committed before the first Stripe call, or an unknown Customer outcome would require a fresh create or guessed adoption.
- Signed webhook and authenticated return calls cannot converge without trusting caller or event metadata alone.
- A late superseded attempt can replace a newer successful PartyIdentity mapping.
- A PaymentMethod cannot be proven to belong to the expected Customer and succeeded SetupIntent.
- Any forbidden payment, billing, source, D6, listing, or credential field enters application state, telemetry, evidence, or PartyIdentity metadata.
- Any path charges, creates a PaymentIntent, removes a method, changes Connect, or enables data verification.
- PR #48's final merged SHA, required behavior, and deployed frontend artifact cannot all be proved in the same release candidate before gate enablement.
- The parent S1590 privacy, payment, or production-enable invariants regress.
