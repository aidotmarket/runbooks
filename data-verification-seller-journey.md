---
title: Data verification — seller journey and operator checks
owner: mars
last_verified: '2026-09-15'
aliases:
- verified label
- verified shape label
- scan findings badge
- data verification
- DATA_VERIFICATION_ENABLED
- STRIPE_PAYIN_ONBOARDING_ENABLED
- pay-in card
error_signatures:
- platform verification key is not configured
- data verification is disabled
- PAYIN_ONBOARDING_DISABLED
- Data verification unavailable.
- Card setup for this paid service is unavailable
---

# Data verification — seller journey and operator checks

The feature built under `BQ-DATA-VERIFICATION-S1590` (specs `specs/BQ-DATA-VERIFICATION-S1590-GATE1.md`, `-GATE2.md`, `-PAYIN-ONBOARDING-AMENDMENT.md`, `-GENERAL-AVAILABILITY-AMENDMENT.md`) lets a seller pay for a point-in-time structural scan that AIM Data executes inside the seller's environment. What crosses to ai.market is the approved aggregate manifest (the signed shape report), the sanitized structural context, the owner consent/launch envelope and, on failure, fixed-enum terminal errors; no raw cell values, sample rows, locators or credentials ever leave the seller's environment (Gate 1 §6). This page is the operating view: what the seller sees, what ai.market does at each step, and how an operator confirms the path is live without spending money or touching a customer. Design rules live in the specs; do not restate or amend them here.

## A. What "live" means and where it stands

Verified 2026-09-15 (S1717) against production:

| Check | Where | Result |
| --- | --- | --- |
| Service flag | Railway `ai-market` / `production` / `ai-market-backend`: `DATA_VERIFICATION_ENABLED` | `true` |
| Pay-in flag | same service: `STRIPE_PAYIN_ONBOARDING_ENABLED` | `true` |
| Pilot allowlist | `STRIPE_PAYIN_ONBOARDING_PILOT_PARTY_IDS` | retired from code (GA amendment, backend GA merge `229689c8`); variable absent. A seller can add a card only from an authenticated application session, when the pay-in gate and platform-account pin are valid and the account has seller-provisioning permission, exactly one active, undeleted `auth_user` party mapping, and TOTP on. |
| Quote endpoint reachable | `POST https://api.ai.market/api/v1/data-verification/quote` with `{}` | `422` field errors. Reachability only: schema validation runs before the flag check, so this cannot show whether the feature is enabled; the flag read above is the enablement evidence. A `404 "data verification is disabled"` appears once schema validation lets a request enter the route, before install signing is checked; the flag read above is the enablement evidence. |
| Card-setup readiness reachable | `GET https://api.ai.market/api/v1/data-verification/payment-method/readiness` signed out | `401`. Reachability only: authentication runs before the gate. Signed-in ineligible callers (flag off included) get an indistinguishable `404 PAYIN_ONBOARDING_DISABLED`. |
| Explainer | `https://ai.market/verified` | `200` (frontend PR #48) |
| AIM Data | stable image default `DATA_VERIFICATION_ENABLED=true` (`docker-compose.aim-data.yml`); flow rendered by `frontend/src/components/DataVerificationFlow.tsx` on the dataset page | present since v1.22.7 |
| Production usage | `verification_quotes`, `verification_epochs`, `data_verification_payin_setup_attempt`, `data_verification_corpus_events` | **0 rows each** — no seller has ever requested a quote in production |
| End-to-end proof | S1656 test environment (`money-path-test-environment.md`), GA acceptance bundle `koskadeux-state/s1656/acceptance-evidence/20260906T174901Z` and run 25 | one paid epoch `PUBLISHED` ($25.00 hold, $1.00 captured, Stripe test mode) and `listings.public_verification_epoch_id` set on the test listing |

So the machinery is complete and proven on the test environment and every production switch is on, but the Definition of DONE ("verified from outside") is not met, and the first real attempt (Max, 2026-09-15, install 9c51517b) showed why: **no customer install can pass the free probe.** AIM Data verifies the platform-signed scan spec with a public key it reads from `DATA_VERIFICATION_PLATFORM_PUBLIC_KEY_PEM` (`aim-data:app/routers/data_verification.py:50-61`), and nothing ships or fetches that key — the customer compose file and installers never set it, the backend returns it only on the RSA device-registration path that AIM Data does not use, and only the S1656 test environment injected it by hand. The product fix is `build:bq-data-verification-platform-key-distribution-s1717` (P0): the platform serves its signing public key and AIM Data fetches and persists it. Per Max (CORE §3) there is no per-install workaround; the first production run follows that build.

## B. The seller's path, step by step

Preconditions the seller must already have: an AIM Data install signed in with their ai.market account (`aim-data-sign-in-with-ai-market.md`), a dataset in that install whose local processing reached `preview_ready`, and that dataset published to ai.market (`aim-data-seller-publish-journey.md`). To add a card the ai.market account must have two-factor authentication (TOTP) enabled; without it the card surface is hidden (identical `404`), by design.

1. **Open the dataset in AIM Data.** Below the publish card the "Data verification" panel shows **Start data verification**.
2. **Free probe and quote.** The seller picks the scan depth options, optionally includes the schema preview and row counts, and selects **Run free probe and request quote**. AIM Data reaches the source locally (no raw data or sample values leave), then asks ai.market for a quote (`POST /data-verification/quote`, install-signed). The panel shows the source reachability, objects discovered, size class and the **maximum card hold**: the quoted authorization, $1–25. The final charge is separate: 2x the measured cloud-inference cost, minimum $1, capped by the authorization and never more than $25 (Gate 1 §9). Nothing is charged at the quote; a row appears in `verification_quotes`.
3. **Two acknowledgements.** Both separate checkboxes are required: the publication-terms acknowledgement and the corpus consent (Gate 1 §12, Gate 2 UX-CONSENT). Charge, cancel, reveal and refund terms are displayed beside them but are not checkboxes. Publication is never pre-consented here, and the corpus consent applies even to runs that are later declined, cancelled, failed, withdrawn or superseded.
4. **Paid start.** **Accept maximum hold and start paid verification**. If the account has no card on file the server answers `setup_required` and the panel shows **Card needed only for this paid verification** with a link to `https://ai.market/dashboard/data-verification/payment-method`. This is the only place a card is ever requested (S1646 rule: never for ordinary account, marketplace, AIM Data, listing or payout use).
5. **Card setup on ai.market.** The seller signs in (step-up re-authentication is expected), selects **Add payment method**, and completes Stripe's hosted setup. ai.market never sees card details; it stores Stripe object identifiers only — the setup attempt lineage (`cus_`, Checkout Session `cs_`, bindings, idempotency keys) in `data_verification_payin_setup_attempt`, and the finalized ordinary `cus_`/`pm_` identity on the primary `party_identity` row (pay-in amendment §7). Returning lands on `/dashboard/data-verification/payment-method/return`, which reconciles readiness.
6. **Back in AIM Data**, select the start button again (**Check card and start paid verification**). ai.market authorizes the maximum hold (`verification_epochs.state = AUTHORIZED`), issues a signed scan spec, and AIM Data scans locally (`SCANNING_LOCAL`), then ai.market runs one bounded allAI interpretation (`NARRATING_CLOUD`), captures the actual cost (`CAPTURE_PENDING` → `CAPTURED`) and reveals the findings to the seller only after capture.
7. **Review and decide.** The seller sees the complete artifact (schema preview, row counts, coverage, allAI interpretation, listing-claim comparison) and either publishes or declines. Decline publishes nothing; the charge stands. Cancel before cloud inference voids the hold with no charge.
8. **Publish.** `verification_epochs.state = PUBLISHED`, `listings.public_verification_epoch_id` points at the epoch, and the public listing page (`/listings/{slug}`) renders the report section titled **`Scan findings — <UTC date>`** with provenance, coverage, facts, interpretation, attestation and the fixed point-in-time disclaimer (`components/listings/ScanFindingsBadge.tsx`). The seller can later withdraw (30-day marker) or supersede — only by explicitly publishing a later completed and captured run; starting or paying for that run leaves the current publication in place (Gate 1 §11).

Wording note: Gate 1 §5 fixes the badge title as `Scan findings — [UTC date]` and forbids unqualified truth-status labels; the public explainer at `/verified` describes the same thing as the "verified shape label". Listing cards on `/listings` and search results carry no verification marker; only the detail page does. Changing either is a spec touch, not an operational fix.

## C. Operator checks (no money, no customer effect)

All reads. Production DB access per `ai-market-backend.md` ("Connecting to production Postgres from an external host").

```sh
# flags
railway variables -e production -s ai-market-backend --kv | grep -E '^(DATA_VERIFICATION_ENABLED|STRIPE_PAYIN_ONBOARDING_ENABLED)='
# endpoints live (expect 422 and 401)
curl -s -o /dev/null -w '%{http_code}\n' -X POST -H 'content-type: application/json' -d '{}' https://api.ai.market/api/v1/data-verification/quote
curl -s -o /dev/null -w '%{http_code}\n' https://api.ai.market/api/v1/data-verification/payment-method/readiness
# usage and lifecycle
psql "$PUB" -c "select state, count(*) from verification_epochs group by 1"
psql "$PUB" -c "select count(*) quotes from verification_quotes"
psql "$PUB" -c "select l.slug, ve.state, ve.published_at from listings l join verification_epochs ve on ve.epoch_id = l.public_verification_epoch_id"
```

Active installs (production, 2026-09-15): `vz_installs` rows exist for `max@kisa.cat` (install registered 2026-09-08 from the `aim-data-fresh-s1665` container on Koskadeux, `http://127.0.0.1:8080`, v1.23.2, signed in, TOTP on) and for Sergey (`eolymp.com`, install 2026-06-17, TOTP on). Neither is yet confirmed to satisfy every precondition of §B from that install: Max's install holds no dataset, and Sergey's one published listing is from June and its dataset state in his install is unknown to us. The daily E2E seller (`e2e-test.ai.market`, `is_test = true`, TOTP off) can reach the quote but never the card surface.

## When it breaks

| Symptom | Meaning | Action |
| --- | --- | --- |
| "platform verification key is not configured" after **Run free probe and request quote** | AIM Data has no platform signing public key; today no customer install has one | Blocked on `build:bq-data-verification-platform-key-distribution-s1717`; do not hand-set `DATA_VERIFICATION_PLATFORM_PUBLIC_KEY_PEM` on a customer install (Max, CORE §3) |
| Panel shows "Data verification unavailable." | AIM Data `DATA_VERIFICATION_ENABLED` false or the install is not signed in | Check the container env and `aim-data-sign-in-with-ai-market.md` |
| Quote returns `404 data verification is disabled` | backend flag off | Rollback order is service flag first, pay-in flag second (GA amendment §5); do not re-enable without the recorded authority |
| Card surface hidden / "Card setup for this paid service is unavailable." | Caller is ineligible: no seller capability, no `auth_user` party, TOTP off, flag off or platform account pin invalid — all return the same `404 PAYIN_ONBOARDING_DISABLED` on purpose | Check `users.totp_enabled` and seller capability for that account before suspecting the server; never disclose which check failed to the customer |
| Epoch stuck in `CAPTURE_PENDING` / `CAPTURE_RECONCILING` | Stripe webhook or reconciliation delay | Check `stripe_events` for the PaymentIntent; the reconciliation path is documented in `specs/BQ-DATA-VERIFICATION-S1590-GATE3-C5.md`; never capture, refund or reset by hand |
| Findings published but the listing page shows nothing | Seller flagged `is_test`, or listing not `published` | Public page hides test sellers and non-visible statuses (`app/api/v1/endpoints/public.py`) |

## Related

- `money-path-test-environment.md` — the disposable environment where the paid loop is proven end to end
- `aim-data-seller-publish-journey.md`, `aim-data-sign-in-with-ai-market.md` — the two preconditions
- `seller-production-payment-cutover.md` — payout side (Stripe Connect), which is separate from pay-in
- Living State: `build:bq-data-verification-s1590` (completed, Gate 4), `decision:s1715-verified-label-process-p0`
