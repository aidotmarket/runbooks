---
title: Run It As A Seller (done means a seller can do it)
owner: unassigned
last_verified: '2026-09-18'
aliases: [run it as a seller, seller run, dogfood, seller-facing done, Gate 4 seller run, not contingent on a customer]
error_signatures: ["registration_evidence_unavailable", "rescan_required", "personal_data", "Intentionally has no transport"]
---

# Run It As A Seller

## The rule (Max decision, 2026-09-18, S1719)

Nothing seller-facing is done until Mars or Vulcan has run it **as a seller, on the released install, against production, from the first click to the buyer seeing the result**. Tests, reviews, green deploys and a customer's goodwill are not substitutes. Do not wait for a real customer to find out whether it works, and do not make progress contingent on one.

Max, same day: "I am not building a police state. I want to remove things that stand in the way. If we have an issue we deal with it then. Gut anything that is going to cause failures." When the seller run hits a refusal that is not technical or cryptographic, the default fix is to remove it, not to explain it.

## Why this page exists

BQ-LISTING-ENRICHMENT-SELLER-TOOLS-S1294 shipped a verified sample preview through three Council-reviewed repos, a released AIM Data v1.24.0 and two production deploys. The first time anyone ran it as a seller (S1719) it turned out no seller could ever have used it:

| Step | What happened | Cause |
|---|---|---|
| Local scan | every row refused `personal_data` | ML detector tags any ISO date as DATE_TIME, `Lisbon` as LOCATION, and the column name `reading_id` as NRP |
| Sign candidate | `registration_evidence_unavailable` | signing required an operator-supplied file under one hour old |
| Submit | nothing sent | `submit()` had no transport; the producer was never wired to the live backend |
| Publish | HTTP 500 | null category and a price under the $25 floor hit database constraints instead of a clean message |

Each layer had passed its own tests and reviews. Only the run found them.

## How to run it (headless, Titan-1)

1. **Account.** Use the production synthetic account the nightly E2E harness already publishes with, `buyer-01@e2e-test.ai.market` (`is_test`). The five `seller-0x` pool accounts cannot publish: seller readiness needs live Stripe payouts. Credentials come from Infisical through `e2e-harness/scripts/harness-env.sh` (source it in a subshell; never echo the values).
2. **Install.** A fresh directory `~/aim-data-<bq>-<session>/` with the release's `docker-compose.aim-data.yml`, a generated `.env` (`POSTGRES_PASSWORD`, `VECTORAIZ_SECRET_KEY`, `AIM_DATA_KEYSTORE_PASSPHRASE`, `AIM_DATA_VERSION`, a free `AIM_DATA_PORT`), its own compose project name. Never reuse another session's install. To test an unreleased branch, build `Dockerfile.customer` (not `Dockerfile`) and point the app service at the local tag with a compose override.
3. **Sign in.** `POST /api/auth/aim-market-login` on the install with the harness credentials; keep the access token in a 0600 file. It expires within the hour; sign in again rather than debugging 401s.
4. **Data.** Synthetic only, generated on the spot, and deliberately ordinary: dates, place names, ids, free text. A dataset designed to pass proves nothing.
5. **Publish** with a `[TEST]` title, category `Synthetic / Test Data`, price at or above $25.
6. **Walk the feature** through the install's own API or UI exactly as a seller would, then open the public listing in a real browser as an anonymous buyer.
7. **A seller-side public host** for anything the seller must host: a static server on `127.0.0.1` behind `cloudflared tunnel --no-autoupdate --config <empty file> --url http://127.0.0.1:<port>`. The empty `--config` matters: without it the quick tunnel inherits `~/.cloudflared/config.yml` ingress and answers 404. The local resolver may not resolve the new `trycloudflare.com` name for a while; verify with `curl --doh-url https://1.1.1.1/dns-query`.
8. **Record** every refusal with its exact code and the layer that produced it on the BQ entity, fix or remove it, and run again from step 4.

## When it breaks

| Symptom | Cause | Fix |
|---|---|---|
| Install API answers `Invalid or expired ai.market token` | access token is short-lived | sign in again (step 3) |
| Publish returns HTTP 500 | null category or 0 < price < $25 on a backend older than the S1719 fix | send a category and a price of $0 or at least $25 |
| Quick tunnel URL answers 404 from Cloudflare | `~/.cloudflared/config.yml` ingress inherited | start the tunnel with `--config <empty file>` |
| `Could not resolve host: …trycloudflare.com` | local resolver lag | `curl --doh-url https://1.1.1.1/dns-query …` |
| `publish-status` says `Device not registered` | registration runs on sign-in; a failed sign-in leaves it unset | sign in again and read the install log for `VZ install registration` |

## Done means

The buyer-visible result exists on a production listing, reached without operator help, and the run is recorded on the BQ entity with the listing id and install version.

## History

- 2026-09-18 (S1719, Vulcan): first run; install `~/aim-data-s1294-t-s1719/`, listings `670364d4-…` and `203f60d8-…`; findings above.
