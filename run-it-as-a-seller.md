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

1. **Account — `buyer-01@e2e-test.ai.market` (Max ruling, 2026-09-19, S1720).** Use it for every seller run. Production has published with it nightly for weeks, so the prohibition that used to sit on `e2e-browser-runner.md` was the thing that was wrong, not the practice; that page now says the same as this one. The account is role `seller`, `is_test`, and owns the listings the nightly E2E harness charter `aim-data-fresh-install` creates at 00:17Z (`production_side_effects: true`, install on `127.0.0.1:8099`). How it publishes without being a ready seller is no longer a mystery, and the two pages that looked contradictory are not: `aim-data.md` (Publishing, and the Boundaries section) allows a signed VZ install to create ONE fresh listing while the seller is merely provisioning, when the active-seller denial has the exact `readiness_gap` shape; that listing is not purchasable and cannot be updated or republished. `aim-data-seller-publish-journey.md` is describing the same rule from the other side when it says registration does not bypass readiness. The nightly charter creates exactly one fresh listing per night, which is precisely what the exception permits. Verified in production 2026-09-19 (S1720): `buyer-01` is role `seller`, `is_test`, has NO `user_capabilities` row, and of its 30 listings only one was ever modified after creation (`fe495b12-…`, 2026-08-23, by hand, not by the harness).
   - **What this account cannot prove.** Listings owned by ANY `is_test` account are excluded from every public read (`public.py`: `u.is_test = false`). So a run on `buyer-01` proves the seller side and the seller's own preview screen, and never the anonymous buyer page. Max accepted that limit on 2026-09-19 and did not authorise a public proof on his own seller account; ask him again if a run genuinely needs the buyer page.
   - The five `seller-0x` pool accounts have no listings, `seller-01` is `seller:provisioning`, and none has live Stripe payouts. Do not reach for them instead.
   - Credentials come from Infisical through the E2E harness loader: `e2e-harness/scripts/harness-env.sh` exports `E2E_SYNTHETIC_BUYER_01_EMAIL` and `E2E_SYNTHETIC_BUYER_01_PASSWORD`. Source it in a subshell and pass the values to the login call by environment variable; never echo them, and never print the install's `serial.json`, which holds the install and marketplace tokens in clear.
2. **Install.** A fresh directory `~/aim-data-<bq>-<session>/` with the release's `docker-compose.aim-data.yml`, a generated `.env` written under `umask 077` (mode 0600) (`POSTGRES_PASSWORD`, `VECTORAIZ_SECRET_KEY`, `AIM_DATA_KEYSTORE_PASSPHRASE`, `AIM_DATA_VERSION`, a free `AIM_DATA_PORT`), its own compose project name. Never reuse another session's install. To test an unreleased branch, build `Dockerfile.customer` (not `Dockerfile`) and point the app service at the local tag with a compose override.
3. **Sign in.** `POST /api/auth/aim-market-login` on the install with the harness credentials; keep the access token in a 0600 file. It expires within the hour; sign in again rather than debugging 401s.
4. **Data.** Synthetic only, generated on the spot, and deliberately ordinary: dates, place names, ids, free text. A dataset designed to pass proves nothing.
5. **Publish** with a `[TEST]` title, category `Synthetic / Test Data`, price at or above $25.
6. **Walk the feature** through the install's own API or UI exactly as a seller would, then open the public listing in a real browser as an anonymous buyer.
7. **A seller-side public host** for anything the seller must host. Run-scoped, synthetic assets only, torn down when the run ends:

   ```bash
   cd ~/aim-data-<bq>-<session>
   mkdir -p seller-origin            # put ONLY the run's synthetic package files here, at the exact relative path the install reports
   python3 seller-origin-server.py & # tiny static server rooted at ./seller-origin on 127.0.0.1:8795, no directory listing (copy from ~/aim-data-s1294-t-s1719/)
   : > empty-cloudflared.yml
   nohup cloudflared tunnel --no-autoupdate --config "$PWD/empty-cloudflared.yml" --url http://127.0.0.1:8795 > cloudflared.log 2>&1 &
   sleep 15; U=$(grep -o "https://[a-z0-9-]*\.trycloudflare\.com" cloudflared.log | head -1); echo "$U" > origin-url.txt
   curl -sS --doh-url https://1.1.1.1/dns-query -D - -o /dev/null "$U/<relative path>" -H "Origin: https://ai.market"
   # teardown, always:
   pkill -f "cloudflared tunnel --no-autoupdate --config $PWD/empty-cloudflared.yml"; pkill -f seller-origin-server.py
   ```

   The explicit empty `--config` matters: without it the quick tunnel inherits `~/.cloudflared/config.yml` ingress and Cloudflare answers 404 (observed S1719). The local resolver may not resolve the new name for a while, hence `--doh-url`. Never serve a directory that holds `.env`, tokens or real data.
8. **Record** every refusal with its exact code and the layer that produced it on the BQ entity, fix or remove it, and run again from step 4.

## When it breaks

| Symptom | Cause | Fix |
|---|---|---|
| Install API answers `Invalid or expired ai.market token` | access token is short-lived | sign in again (step 3) |
| Publish returns HTTP 500 | null category or 0 < price < $25 on a backend older than the S1719 fix | send a category and a price of at least $25 (every seller run uses at least $25; $0 is a free listing and is not a workaround) |
| Quick tunnel URL answers 404 from Cloudflare | `~/.cloudflared/config.yml` ingress inherited | start the tunnel with `--config <empty file>` |
| `Could not resolve host: …trycloudflare.com` | local resolver lag | add `--doh-url https://1.1.1.1/dns-query` to the curl in step 7 |
| `publish-status` says `Device not registered` | registration runs on sign-in; a failed sign-in leaves it unset | sign in again and read the install log for `VZ install registration` |

## Done means

The buyer-visible result exists on a production listing, reached without operator help, and the run is recorded on the BQ entity with the listing id and install version.

## History

- 2026-09-18 (S1719, Vulcan): first run; install `~/aim-data-s1294-t-s1719/`, listings `670364d4-…` and `203f60d8-…`; findings above.
- 2026-09-19 (S1720, Mars): second run on released **v1.24.1**, same install. The scan and the signing gate are gone — `candidate` returned `signed_candidate` against production. Two further defects surfaced that no test had caught, both of which had made the feature impossible for every seller: the marketplace compared At-a-glance field types (`BIGINT`, `VARCHAR`) against preview descriptor types (`signed_integer`, `string`) as raw strings and refused with `summary_schema_mismatch`; and it decoded a registered install key as base64url when registration had stored standard base64, telling an active install it was inactive (`signer_authority_invalid`, 4 of 12 production installs affected). Both fixed. The pattern is now three for three: every defect on this path was found by running it, and none by a test.
