---
title: Money-Path Clean-Seed Proof Loop and the S3 Verification-Artifact Route
owner: mars
last_verified: '2026-09-11'
aliases:
  - money-path proof loop
  - clean-seed proof loop
  - verify --from-clean-seed
  - verification-artifact route
  - G14 route
  - S1681 G14
  - repin-and-record
error_signatures:
  - "seed: host handoff failed (details suppressed); check seed revocation result"
  - "S1681 refusal: independent observation or device operation"
  - "S3 version scan failed after assume-role propagation retries"
  - "verification_artifact_unavailable"
  - "verification_artifact_ambiguous"
  - "POST /api/v1/serials/{serial}/s3-connections/verification-artifact"
  - "FAILED_VOIDED"
  - "rate_limit_exceeded"
  - "mint-teardown-token: a previous unexpired teardown-token record exists"
---

# Money-Path Clean-Seed Proof Loop and the S3 Verification-Artifact Route

This page is the operating procedure behind BQ-MONEY-PATH-DELIVERY-LEG-S1681: how one clean-seed run of the S1656 environment is executed, how each of the failures found on 2026-09-09/10 was diagnosed, how a fix is taken from root cause to a repinned environment without losing the audit trail, and the exact contract of the backend route added by S1681 Amendment G14. `money-path-test-environment.md` (aliases `S1656 money path`) is the reference for topology, secrets, seed contract and evidence; read it first. This page is the loop that sits on top of it. Source references are `repo:file:line` at the pinned identities in §A and must be re-verified with `git show` before relying on them, because every fold moves lines.

## A. Identities this page was verified against

| Thing | Identity |
| --- | --- |
| Environment head | `aidotmarket/money-path-test-environment@6abc612c45f3e5fb89960cd2c79adc1327506c6f` (after PR #18) |
| Backend candidate (`BACKEND_RC_SHA`, `seed/seed.py:51`) | `31f09b5666314aa375d41d269be52552d518ba94` (main; contains backend PR #374 `c673eafd`, the G14 route) |
| Frontend candidate | `943429b586fa4acd55f81f23ded5005cbcf841e1` |
| AIM Data candidate | `51e2740f6972c008626e186d8b265601c58eca32` as `v1.23.3-rc.2@sha256:67fd600590e2608c2019cef6f802488bd04ed69474b896c803e878c352c55925` |
| Acceptance pins (`/Users/max/koskadeux-state/s1656/nightly-pins.env`, 0600) | both `S1656_SPEC_A2_SHA` and `S1681_SPEC_SHA` = merge commit of the latest runbooks record PR (`b73741f2e570187646d35ddbb3059b47e9dabb83` at writing) |
| Specs | `specs/BQ-MONEY-PATH-TEST-ENV-S1656-GATE1.md` (A2 items 14–20 are the fold history), `specs/BQ-MONEY-PATH-DELIVERY-LEG-S1681-GATE1.md` (Amendments G10–G14, G14.5–G14.8) |
| Checkout | `/Users/max/Projects/ai-market/money-path-test-environment-s1656`, detached at the environment head, clean |
| Run logs | `/Users/max/koskadeux-state/s1656/logs/verify-run<N>-<stamp>.log` (0600; contains nothing secret but is not evidence — evidence is the run bundle under `acceptance-evidence/`) |

## B. The loop, in order

Every cycle is the same six steps. Do not skip the record step even when the code change is one line; the acceptance pins refuse a run whose spec record does not name the environment head.

1. **Run.** From the clean checkout at the environment head, with both pins exported:
   `S1656_SPEC_A2_SHA=<pin> S1681_SPEC_SHA=<pin> rtk proxy ./bin/verify --from-clean-seed` (background it with `nohup … > /Users/max/koskadeux-state/s1656/logs/verify-run<N>-$(date +%Y%m%dT%H%M%S).log 2>&1 &` under `umask 0077`; a run takes 15–25 min to the delivery leg). `rtk proxy` prints `failed to wait for command termination: exit status 1` three times on any failure; that line carries no information. Exit 2 with `pending-hold` is the online-phase success (settlement runs later, §F). Do not run `./bin/preflight` bare; `bin/up` runs it with the Infisical test-env loaded.
2. **Diagnose** (§C). Find the failing phase from the log, then the true error from the product logs or databases — the seed and evidence helpers suppress details by design.
3. **Fix at the root.** Product defect → product repo (backend / aim-data) → its own PR, Gate 3, merge, then an environment repin PR. Environment defect (seed, evidence, browser) → environment PR on `main`. Spec/contract gap → runbooks amendment first (Gate 1/2), then build. Dispatch MP with `repo=aidotmarket/money-path-test-environment` (not the `-s1656` checkout name), `aidotmarket/aim-data` or `aidotmarket/ai-market-backend`; MP resolves the base to the repo's current main, so check `git diff --name-only <expected base> <resolved base>` for the files you cite before reviewing. MP will not push when the full suite has pre-existing failures; push the worktree commit yourself after confirming the failure set is identical on base.
4. **Council.** Money path, auth and customer-data scope: CC, GLM and DeepSeek, unanimous, builder excluded. Dispatch all three at once with `dispatch_sha` and `base_sha`; tell CC to write the response file first (it otherwise sometimes produces none; a placeholder starting `REVISE (PROVISIONAL` means it is still working — poll until the word `PROVISIONAL` is gone). Grep the verdict token rather than reading line 1 (files sometimes begin with a title). Fold every finding into a new commit and re-dispatch; a REVISE/REJECT restarts at the same gate, never earlier. Never commit to a branch while a review on it is running — GLM flags branch mutation mid-review — and if two Mars instances are alive after a connection loss, one claims the branch on the peer bus before touching it.
5. **Record.** Merge the PR, then append to the runbooks in one docs-only PR: an S1656 A2 item (next number), an S1681 G14.x record (or a new amendment), the head statement and product-identity table in `money-path-test-environment.md`, and a When-it-breaks row for the new signature. Per Max's decision of 2026-09-10 (Event Ledger `7ea142d5-bcbb-4e12-b54b-8a01521daf33`) a documentation-only record rides on the vote of the code or environment PR it records and gets no separate vote; substantive design amendments (a new contract or route) still get Gate 1/2. Merge the record PR, then `printf 'S1656_SPEC_A2_SHA=%s\nS1681_SPEC_SHA=%s\n' <merge> <merge> > /Users/max/koskadeux-state/s1656/nightly-pins.env` (0600) and prove it: `S1656_SPEC_A2_SHA=… S1681_SPEC_SHA=… python3 bin/check-settlement --pins` → exit 0.
6. **Gate the rerun.** Serial issuance for seller-01 is rate-limited at 2 per email per hour and 5 per IP per hour (`backend:app/services/rate_limit_service.py`); each clean-seed run mints one serial, so reruns are at most two per hour. Re-mint the teardown token when its record is within a few hours of expiry: `rtk proxy ./bin/mint-teardown-token --replace` (24 h; records under `/Users/max/koskadeux-state/s1656/mint-policy/`). Then go to step 1.

## C. Diagnosing a failed run

The log tells you the phase; it almost never tells you the error. Work from the last phase line.

| Last log line | Phase | Where the real error is |
| --- | --- | --- |
| `seed: host handoff failed (details suppressed); check seed revocation result` after `status: seeded` | `seed/host-seed.py` (G9 IAM trust update → broker verify → version scan → objects → register) | `.state/s1681-seed.json` tells you how far it got: `connection_id` only → verify never passed; `external_id_sha256` present, no `scan_id` → scan; `scan_id`, no `dataset_id` → register. Backend access log (`docker logs ai-market-money-path-s1656-backend-1`) shows `external-id`, `verify`, `list-objects` calls with status codes. AIM Data table `s3_scan_job` (`docker exec ai-market-money-path-s1656-aim-data-postgres-1 psql -U aim_data -d aim_data -Atc "select status,error_message,started_at from s3_scan_job"`) holds the scan error (`assume_role:AccessDenied` = IAM propagation flap, tolerated since PR #18). AIM Data's `register` route swallows failures into bare HTTP errors without logging (ticket T-2026-000782). |
| Playwright `1 failed` in `s1590-money-path.spec.ts` with `S1681 refusal: …` from `s1681-delivery-leg.ts:7` | S1681 delivery leg | `independent observation or device operation` = the `bin/verify` evidence helper on `127.0.0.1:18003` answered non-2xx (the helper returns 503 whenever `delivery_snapshot()` raises, `bin/verify:602–607`). Reproduce the SQL by hand (§D). Any other label names the assertion at `browser/s1681-delivery-leg.ts`. |
| Playwright failure at `finishPaidVerification` (`browser/s1590-money-path.spec.ts:872`, assertion `:889`) with an epoch `AUTHORIZED` then `FAILED_VOIDED` | Paid verification (AC5–AC10 tail) | Backend access log around the epoch: a `404` on `POST /api/v1/serials/{serial}/s3-connections/verification-artifact` means the backend candidate predates PR #374; a `404` body `verification_artifact_unavailable` from a backend that has the route means the handle→listing→serial resolution failed (§E). `data_verification_payment_transition` log lines show the authorize/void timeline. |
| `S3 version publication identity or status differs` | Signed version publish | AIM Data reported `version_status: null` → backend predates PR #371 (`1d7bed61`). |
| `version publish requires a non-empty s3_connection prefix` | Signed version publish | AIM Data dropped S3 provenance → AIM Data predates v1.23.3-rc.2. |
| `real S3 broker verification failed` | Seed, verify loop (120 s) | Trust document, `role_arn` or ExternalId is actually wrong; do not reissue the serial, inspect read-only (`aws iam get-role` through the seed identity). |
| `ParamValidation: Invalid JSON received` from aws-cli | Seed, G9 | Environment predates PR #13. |

Hosted Stripe pages: when the browser stops on a hosted Checkout or setup page with a URL-free error, do not guess at locators — copy the leg's steps into a scratch `.mjs` inside the browser-runner (`docker cp … :/work/diag.mjs`, run with `docker compose … exec -T -w /work -e E2E_SYNTHETIC_BUYER_01_EMAIL -e E2E_SYNTHETIC_BUYER_01_PASSWORD browser-runner node /work/diag.mjs` under the Infisical test-env), log each step with URLs redacted, stop before Pay, and delete the script. Run 10 was diagnosed that way in five minutes. Stale `created` orders it leaves behind are cleared by the next clean seed.

Stripe blocks: any code that runs inside the backend container against the Stripe SDK (settlement, the release command) must be dry-run live before Council — extract the block with the same regex the tests use, replace the mutating call (`expire`, `cancel`, transfer) with `raise SystemExit("DRY")`, run it under the Infisical test-env through `docker compose … exec -T backend python -c`, and confirm it reaches the mutating line. Mocked tests cannot see SDK object semantics (PR #22: `.get` on a StripeObject).

## D. Reproducing the evidence SQL by hand

Since environment PR #33 (`6c953f0e1152c1dee21d3fd80302e42a11972d1b`, S1656 A2 item 34 / S1681 G14.20), `bin/check-settlement` `delivery_snapshot()` performs fresh read-only observations without Compose interpolation. With `POSTGRES_PASSWORD` present the backend query uses host `psql` at `127.0.0.1:15432`; otherwise it resolves `postgres` and uses direct `docker exec -i`. AIM Data always uses direct `docker exec -i` to `aim-data-postgres`. Both lookups use exact `com.docker.compose.project=ai-market-money-path-s1656` and `com.docker.compose.service=<svc>` labels and reject missing or multiple matches. SQL still uses `psql -X -qAt -v ON_ERROR_STOP=1 -U <user> -d <db>` with the existing read-only transaction blocks. Backend duplicate evidence reads `docker logs` from a freshly resolved backend ID, retaining stdout and stderr for aggregate counts; cross-stream chronological order is not guaranteed.

For a read-only diagnostic on the current clean checkout, `rtk proxy python3 -c 'import runpy; d=runpy.run_path("bin/check-settlement")["delivery_snapshot"](); print("orders", len(d["orders"]), "events", len(d["events"]))'` needs no secret injection because the no-password path runs psql inside the two owned database containers. Do not print the full snapshot. Missing containers or SQL/schema errors refuse; inspect the exact SQL from the pinned function and database schema privately. Never put Compose or a snapshot cache back into the one-second polling path.

## E. The `verification-artifact` route (S1681 Amendment G14)

Why it exists: AIM Data's local verification scanner (`aim-data:app/services/data_verification/scanner.py:140`) reads an S3-sourced artifact through `S3BrokerClient.stream_registered_artifact` (`aim-data:app/services/s3_broker_client.py:111–136`), which sends only the opaque `source_handle_id` (`= dataset.id`, the same value the publish path sends as `vz_raw_listing_id` and the backend stores as `Listing.source_dataset_id`). Nothing else may travel: no connection id, bucket, key or role ARN. Until backend PR #374 the receiver did not exist, so every S3-sourced paid verification voided.

Contract (`backend:app/api/v1/endpoints/s3_connections.py` at `31f09b56`, tests `tests/test_s1681_verification_artifact_route.py`):

- `POST /api/v1/serials/{serial}/s3-connections/verification-artifact` body `{source_handle_id}` matching `^[A-Za-z0-9_-]{1,64}$`; auth and limits identical to `presign-object` (install token as Bearer, IP pre-auth limiter, `RateLimiter(cost=5)`); 401/403/422/429 keep their ordinary codes.
- Resolution, fail closed, every step answering HTTP 404 with the exact body `{"status":"error","error_message":"verification_artifact_unavailable"}` (plain `JSONResponse`, byte-identical across reasons): listing by `source_dataset_id` (exactly one) → `raw_metadata.s3_connection` present with `serial_id == str(Serial.id)` of the calling serial (the route loads the `Serial` row itself; the shared dependency discards it; `Serial.id` is a UUID, the path parameter is the `VZ-…` code) → `listing.seller_id == serial.user_id` when set → exactly one `listing_versions` row `active` → `assume_seller_role(role_arn, derive_external_id(serial), "verification")` → `list_objects_v2(prefix, MaxKeys=10)`, discard directory markers and out-of-prefix keys, then exactly one object (two or more, or a truncated listing → 409 `verification_artifact_ambiguous`, reachable only by the owning serial) → presign `get_object` 300 s → `{url, expires_in, expires_at}` and nothing else.
- Read-only and idempotent. AWS/STS errors are logged through the sanitized `_log_presign_error` path and answer the same 404. Timing differs between unknown/foreign/owned handles and is accepted (handles are unguessable, the caller is authenticated and rate-limited).

Diagnosing a 404 with the route present: check, in order, `select id, source_dataset_id, seller_id, raw_metadata->'s3_connection' from listings where source_dataset_id='<handle>'` (exactly one row; `serial_id` inside the block must equal `select id::text from serials where serial='<VZ code>'`), `select id,status,prefix,object_count from listing_versions where listing_id=…` (exactly one `active`), then the IAM trust of `role_arn` for `derive_external_id(serial)` (compare with the backend's `external-id` route output for that serial). A 409 means the active prefix holds more than one real object or the listing was truncated at 10 keys — the seed guarantees one object; find who wrote the extra.

Relationship to the Seller Workspace (Vulcan's browser-only cloud seller, `seller-workspace-cloud-listing-delivery.md`): the two paths share only `app/services/sts_assumer.py` and the presigner idea. Workspace listings publish `fulfillment_type='file_download'` with a `workspace_connection` source and per-connection random ExternalIds; `FulfillmentService` branches on `is_workspace_source(order.source_delivery)` (`backend:app/services/fulfillment_service.py:177–178`) before the Trust-Channel device path this page proves, and buyers download through `/seller-workspace/orders/{id}/download` rather than `/orders/{id}/download/redeem`. G14 is serial-scoped and does not apply to Workspace listings; a verified label for Workspace listings would need a scanner that runs outside ai.market (the W3 profiling unit is the natural host) — an open design question, not a defect.

## F. After the first exit-2 run

Daily after 01:30 Madrid: `rtk proxy ./bin/check-settlement` (exit 2 `pending-hold` until the genuine 48 h hold passes; then it drives the test settlement scheduler, retrieves the real test Transfer and continues). Then the offline phase (`S1681_PHASE=offline`), the summary, promotion of AIM Data v1.23.3 to stable, the two plists in `config/`, one proven scheduled run (DL12), Gate 4 with gate-level verdicts patched, then `bq_complete`. Never reset underneath pending money; `bin/verify` resumes an active run from `acceptance-evidence/active-run.json` and refuses mutation while settlement is pending.

## When it breaks

| Symptom | Cause | Fix | Exact command or evidence path |
| --- | --- | --- | --- |
| `rate_limit_exceeded` from `POST /api/v1/serials/generate` during the seed | More than two clean-seed runs in one hour for seller-01 (or five per IP) | Wait for the hour window; never edit the limiter or reuse a serial | backend access log; `backend:app/services/rate_limit_service.py` |
| `mint-teardown-token: a previous unexpired teardown-token record exists` | A valid token record is still live | `rtk proxy ./bin/mint-teardown-token --replace` revokes and re-mints (24 h) | `/Users/max/koskadeux-state/s1656/mint-policy/*.json` |
| Every run exits in under a minute with `preserve active run`; `active-run.json` says `purchasing` | A run failed between `begin_purchase` and payment; the money guard holds | After proving no money, `rtk proxy python3 bin/check-settlement --abandon-unpaid <run> <env_sha> [<order_uuid>...]` (PR #20); do not create orders by hand while a checkpoint is live — it forces you to name them | `money-path-test-environment.md` When-it-breaks |
| Every run exits `preserve active run` and the checkpoint's order is paid/delivered (money in flight) | The proof failed after payment | `--abandon-refunded <run> <env_sha> <order>` (PR #24, S1681 G15): full refund at Stripe, product marks refunded/revoked, checkpoint released; never settle it | `money-path-test-environment.md` When-it-breaks |
| Helper connect timeout or a device-stop 503 after `delivered` | Docker Desktop API starved (VM memory, stale containers, exec churn) | See `money-path-test-environment.md` When-it-breaks; keep the VM at ≥ 24 GiB; prune stale containers with Max's approval; never cache the snapshot | Docker host log |
| `check-settlement --pins` exits non-zero after a record merge | A pin is not the merge commit of the runbooks PR carrying the environment head, or the record does not name the head | Fix the record or the pins file; the head string must appear literally in both specs | `S1656_SPEC_A2_SHA=… S1681_SPEC_SHA=… python3 bin/check-settlement --pins` |
| Council member never writes a response file | CC hit the profile lock or exited before writing | Re-dispatch with "write the response file first"; check `pgrep -fl "^/opt/homebrew/bin/claude"` and `/Users/max/koskadeux-state/locks/cc-profile.lock` | `/Users/max/council/cc/launcher-*.log` |
| MP diffstat shows hundreds of unrelated deletions | The bridge diffed the branch against a stale local main | Trust `git diff --stat <parent> <head>` on the branch head, not the bridge diffstat | `git log --oneline -1 <head>`; `git merge-base <head> origin/main` |
| Living State note or branch commit under your own session label that you did not make | A second instance of the same peer is alive after a connection loss | Claim the branch on the peer bus, wait 20 min for a reply, then proceed; verify every step against Git and Council files before building on it | `sqlite3 /Users/max/koskadeux-state/registry.db "select instance,session_id,last_seen_at from sessions where ended_at is null"` |
