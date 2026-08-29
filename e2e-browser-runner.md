---
title: E2E Browser Runner
owner: mars
last_verified: '2026-08-27'
aliases: []
error_signatures:
- 'browser_journey refused: E2E_PROD_FRONTEND_URL is required'
- status harness_error, summary browser_journey requires params.mode
- preflight refusal (404, 403, 401, non-200, allowed=false, timeout)
- 'Production targeting refused: E2E_INTERNAL_API_KEY is required for preflight'
- no screenshot present
- one attempt remains on Submitting or no persistent held result is visible
- held audit exists but an inquiry row was created
- buyer-01 reaches Listings, sees no create control or incomplete seller onboarding, and the run reports a product blocker
- recording manifest or artifact refusal before Playwright launch
- flaky_pass_after_retry
---

# E2E Browser Runner

> The missing heart of the E2E programme, shipped in phases. Before S1196 the harness had a queue, redaction, retention, ticket filing, a webhook emitter and a nightly schedule - but no browser. `browser_journey` is the charter kind that opens a real Chromium and walks the product. Phase 1 (live since S1196) is the anonymous public walk: it signs into nothing, declares no accounts and writes nothing. Phase 4 recorded replay is live since S1622 for committed, human-approved journeys; the first promoted recording is the production-read-only `anonymous-allai-s1294.v1`. The signed-in buyer and mutating seller journeys remain later phases. Owner BQ: `BQ-E2E-BROWSER-RUNNER-S1194`, child of `BQ-E2E-TESTING-FRAMEWORK-S1152`.

## Overview


### M1 — Dependencies & Credentials / Source-of-Truth

| Dependency | What it provides | Where it lives | Owning service |
|---|---|---|---|
| `aidotmarket/e2e-harness` | The harness itself: queue, runtime dispatch, agentic and recorded browser runners, redaction, retention, tickets | Titan-1 clone `~/Projects/ai-market/e2e-harness`; main at `b3da50904b3019e091487297f5ffde7ed4f694ac` (S1622) | GitHub `aidotmarket/e2e-harness` |
| Playwright + Chromium | The browser substrate. Declared in `pyproject.toml`; the browser binary is installed separately (`playwright install chromium`) | Titan-1, inside the harness virtualenv | Playwright |
| `E2E_PROD_FRONTEND_URL` | The ONLY source of the sanctioned production frontend URL. No hardcoded fallback exists; a `browser_journey` refuses to run when it is unset | set by `scripts/harness-env.sh` (S1201); the launchd plist no longer carries it | e2e-harness config |
| `E2E_PROD_TARGETING_ENABLED` | Harness-side opt-in for production targeting. Required for every browser journey EXCEPT the anonymous exemption (Architecture & interactions) | set by `scripts/harness-env.sh` (S1201) | e2e-harness config |
| `scripts/harness-env.sh` | The ONE place the harness gets its production environment. Exports the targeting opt-in and the two sanctioned URLs, and fetches `INTERNAL_API_KEY` from Infisical **at runtime** into `E2E_INTERNAL_API_KEY`. No secret is written to the plist, a dotenv file or the repo. The Infisical bearer token reaches curl on stdin via a `-K` config block, never on argv | `e2e-harness/scripts/harness-env.sh`; sourced by `scripts/run-nightly.sh`, which is what the launchd plist runs | e2e-harness (S1201, main `f8c7ba2`) |
| `E2E_HARNESS_ROOT` | Root for queue, reports, artifacts, profiles, auth-states | harness environment; launchd sets it | e2e-harness config |
| `GET /api/v1/e2e/preflight/{account_id}` | Per-account production preflight; proves an account is an allowlisted `is_test` pool account before a browser opens | ai.market backend (production) | ai-market-backend |
| Synthetic `is_test` pool accounts | The ten `seller-01..05@e2e-test.ai.market` / `buyer-01..05@e2e-test.ai.market` production accounts used by authenticated journeys (Phase 2+). They EXIST (created 2026-07-11) and **can all log in** since S1293 (buyer-01 since S1202) — every pool row now carries a real password_hash. Login is pool-wide but preflight authorization is NOT: only ids in E2E_RESET_ALLOWED_ACCOUNT_IDS (currently buyer-01) pass preflight, so a Phase 2+ charter for any other account needs its id added first (Capabilities, How to operate-02). See BQ-E2E-FULL-POOL-LOGIN-ENABLEMENT-S1292 (queued S1292, executed S1293) and T-2026-000241 (buyer-01, resolved S1202) | production `users` table; ids in `ai-market-backend/e2e/account_pool.json` | ai-market-backend (see account-teardown.md) |

## Capabilities

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| `browser_journey` charter kind accepted through the existing JSONL queue and CLI | SHIPPED | `e2e-harness src/e2e_harness/queue.py`, `cli.py` (unchanged; generic `kind`) | `tests/test_queue.py` | 2026-07-12 |
| Real Chromium launch via Playwright, per-run profile dir | SHIPPED | `src/e2e_harness/browser.py:BrowserJourneyRunner._walk_public_page` | `tests/test_runtime.py` | 2026-07-12 (live walk of https://ai.market, S1196) |
| Anonymous public production walk (Phase 1): signs into nothing, writes nothing | SHIPPED | `src/e2e_harness/browser.py:BrowserJourneyRunner.run` | `tests/test_runtime.py` | 2026-07-12 |
| Fail-closed param handling: malformed charter reports without opening a browser | SHIPPED | `browser.py:_harness_error` | `tests/test_runtime.py` | 2026-07-12 |
| Config-only production URL, fail-closed when unset | SHIPPED | `src/e2e_harness/runtime.py` (`browser_journey` dispatch branch) | `tests/test_runtime.py` | 2026-07-12 |
| Narrow production-guard exemption (no accounts AND `requires_mutation` falsy AND `anonymous: true`) | SHIPPED | `runtime.py:_is_anonymous_browser_preflight_exempt` | `tests/test_runtime.py` | 2026-07-12 |
| Artifact policy: redacted step transcript AND redacted trace zip persisted; screenshots still WITHHELD (no pixel masking exists) | SHIPPED (S1197: zip-aware redaction) | `browser.py:_redact_and_cleanup`, `src/e2e_harness/redaction.py:redact_zip` | `tests/test_redaction_retention.py` | 2026-07-12 |
| Zip-aware trace redaction: NDJSON entries redacted line-by-line, `resources/` response bodies and all binary/non-UTF-8 entries WITHHELD, `redaction-manifest.json` records every entry, any failure raises (harness_error, no artifacts) | SHIPPED | `redaction.py:redact_zip`, `_redact_zip_entry` | `tests/test_redaction_retention.py` | 2026-07-12 |
| Harness production environment, S1201: the targeting opt-in, the two sanctioned URLs and the backend internal API key, loaded from one place; the key is fetched from Infisical at runtime and never written to the plist or the repo | SHIPPED | `scripts/harness-env.sh` | live production verification, How to operate-02 | 2026-07-13 |
| Preflight arming for the Phase 2 buyer, S1201: `E2E_RESET_ALLOWED_ACCOUNT_IDS` on the production backend holds buyer-01 and nothing else, so preflight allows that one account and refuses every other. Reset and teardown routes remain 404 because `E2E_TEST_ROUTES_ENABLED` is false — nothing is armed | SHIPPED | — | live production verification, How to operate-02 | 2026-07-13 |
| Phase 2: authenticated buyer read-only journey to the pay boundary. Login blocker REMOVED S1293 — all ten pool accounts now log in through the customer login endpoint (BQ-E2E-FULL-POOL-LOGIN-ENABLEMENT-S1292, queued S1292 / executed S1293, Gate-1 unanimous + Max GO; all ten verified live, HTTP 200). The journey ITSELF is not built yet. Preflight caveat: only buyer-01 is in `E2E_RESET_ALLOWED_ACCOUNT_IDS`, so only buyer-01 passes preflight today; the other nine need their id added before a browser will open. Reset/teardown routes remain 404 (`E2E_TEST_ROUTES_ENABLED` false); the pay boundary itself still needs the Stripe sandbox order router (s1196). | PLANNED | `app/e2e/synthetic_accounts.py` | live login verification S1293 | 2026-07-20 |
| Phase 3: mutating seller journey (publish a listing); pay step blocked on the Stripe sandbox order router | PLANNED — `build:bq-stripe-sandbox-order-router-s1196` gates the pay step | n/a | n/a | n/a |
| Phase 4: committed, human-approved deterministic replay with one fresh-context retry; agentic drift probes remain default-off and unimplemented | SHIPPED | `src/e2e_harness/recorded.py` | `tests/test_recorded.py` | 2026-08-27 |

## Architecture & interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Charter queue | `src/e2e_harness/queue.py` | `$E2E_HARNESS_ROOT/queue.jsonl` | CLI `e2e-harness enqueue @<path>` | Unchanged by the browser work. `kind` is a free string, so `browser_journey` needed no queue redesign. |
| Runtime dispatch | `src/e2e_harness/runtime.py:_run_charter` | reports dir | `BrowserJourneyRunner`, recorded replay | Refuses with a config error when `E2E_PROD_FRONTEND_URL` is unset — there is no hardcoded host. Agentic and recorded modes share the production guard and reporting path. |
| Browser runner | `src/e2e_harness/browser.py:BrowserJourneyRunner.run(run_id, charter, profile_dir, auth_state)` and `src/e2e_harness/recorded.py:replay_recording` | per-run `profile_dir`, artifacts dir | Playwright Chromium, redaction | Returns the same outcome dict shape the runtime already consumes. `agentic` requires a goal. `recorded` requires a committed approved recording whose manifest, script hash, host, mutation contract and fixture pass before launch; malformed or unapproved recordings are `harness_error`. |
| Production guard | `runtime.py:_require_prod_preflight` + `_is_anonymous_browser_preflight_exempt` | — | backend preflight route | Every production charter needs `E2E_PROD_TARGETING_ENABLED`, declared account ids and per-account preflight — EXCEPT a browser journey that declares no accounts AND has `requires_mutation` falsy AND sets `anonymous: true`. That exemption exists because the anonymous public walk touches no account and writes nothing. Anything else takes the full guard. |
| Harness identity marker | `src/e2e_harness/user_agent.py` (`E2E_HARNESS_USER_AGENT_TOKEN = "ai-market-e2e-harness"`) | — | backend `app/e2e/synthetic_exclusion.py:should_count_view` | The browser context launches with the real Chromium User-Agent plus `ai-market-e2e-harness/0.1`, and every harness HTTP caller (preflight, webhooks, health) sends the same token. The backend suppresses counter and telemetry writes when it sees it. This is the ONLY thing that keeps the anonymous walk out of real sellers' numbers — remove it and the nightly run silently starts inflating them again (T-2026-000242, S1202). |
| Artifact redaction | `src/e2e_harness/redaction.py:redact_artifact` | `$E2E_ARTIFACTS_DIR/traces/<charter_id>/` | retention sweep | Text/JSON only. `.png/.jpg/.jpeg/.webp` and `.zip` are WITHHELD with a placeholder — a text redactor cannot scan a compressed archive, and pretending otherwise produced a mangled blob whose contents were never actually scanned (defect found S1196). Phase 1 therefore persists the redacted step transcript only. |
| Failure classification | `runtime.py` finding creation | reports, support tickets | `tickets.py` | Only `failed` (a product failure) becomes a Finding and a ticket. `harness_error` (browser launch, malformed params, redaction failure) writes a report and NEVER files a product ticket: a false ticket burns response capacity and trains operators to distrust the harness. |

Prose: a charter is appended to the JSONL queue; `e2e-harness run` loads it, creates the per-run profile directory and the account-scoped auth-state path, and dispatches on `kind`. For `browser_journey`, `BrowserJourneyRunner` launches a persistent Chromium context on that profile directory, navigates to the sanctioned production frontend, asserts the page and a public element, then writes a step transcript, redacts it, deletes the raw browser working files, and returns an outcome. Nothing leaves the machine except reports and (later) tickets.

## Agent capabilities

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan/Mars | Queue and run a browser journey | `shell_request` on Titan-1: `e2e-harness enqueue @charter.json`, `e2e-harness run` | Titan-1 shell | COMPLETE |
| Vulcan/Mars | Read the run report and artifacts | `shell_request` on `$E2E_HARNESS_ROOT/reports`, `/artifacts` | Titan-1 shell | COMPLETE |
| MP (Codex) | Build harness changes | `council_request mode=build` against a dedicated worktree | Council dispatch | COMPLETE — builder output must be diff-inspected at file:line; commit messages over-claim |
| DS / AG | Review harness changes | `council_request mode=review` (builder excluded) | Council dispatch | COMPLETE |
| launchd (`com.ai-market.e2e-harness.nightly`) | Nightly run at 02:15 local | plist in the harness repo | Titan-1 | COMPLETE |
| Codex-as-driver (agentic page reasoning) | Improvise a first walk like a first-time customer | n/a | n/a | PLANNED — Phase 1 walks a fixed public path; the live agent loop lands with the authenticated journeys |

## How to operate

```yaml operate
- id: E-01
  trigger: Run the anonymous public browser walk against production (the Phase 1 signal)
  pre_conditions:
    - Titan-1 harness checkout on main with the virtualenv installed
    - Chromium installed for Playwright (playwright install chromium)
    - E2E_PROD_FRONTEND_URL set to the sanctioned production frontend URL
  tool_or_endpoint: "e2e-harness enqueue @<charter.json>; e2e-harness run"
  argument_sourcing:
    charter: 'kind browser_journey; params {mode: agentic, goal: <one line>, start_url: frontend, anonymous: true, requires_mutation: false, public_selector: <selector or omit for body>}'
    E2E_PROD_FRONTEND_URL: harness environment; never hardcode a host in a charter
  idempotency: IDEMPOTENT
  expected_success:
    shape: 'report under $E2E_HARNESS_ROOT/reports with status passed; charter outcome status passed; artifacts list contains the redacted step transcript ONLY'
    verification: 'cat the newest report json; find $E2E_ARTIFACTS_DIR -type f - the redacted step transcript and the redacted trace.zip are expected; there must be no screenshot'
  expected_failures:
    - signature: 'browser_journey refused: E2E_PROD_FRONTEND_URL is required'
      cause: production frontend URL not configured (When it breaks-01)
    - signature: 'status harness_error, summary browser_journey requires params.mode'
      cause: malformed charter params; no browser was opened (When it breaks-02)
  next_step_success: keep exploratory work agentic; use E-06 only after a recording has been human-approved and committed
  next_step_failure: repair per Repair-01 / Repair-02
- id: E-02
  trigger: A browser journey needs to touch an account (Phase 2+)
  pre_conditions:
    - the charter declares account ids from the synthetic is_test pool
    - E2E_PROD_TARGETING_ENABLED is set
    - the backend read-only preflight route is enabled (E2E_PREFLIGHT_ROUTES_ENABLED=true on ai-market-backend; it is DORMANT by default and is independent of E2E_TEST_ROUTES_ENABLED, which still gates the reset/teardown mutation routes)
    - E2E_INTERNAL_API_KEY is set in the harness environment (the preflight route requires the X-Internal-API-Key header since S1197; the harness refuses the run locally, before any network call, when the key is absent). Do NOT set it by hand and do NOT put it in the plist - source scripts/harness-env.sh, which fetches it from Infisical at runtime (S1201)
    - the account id is in E2E_RESET_ALLOWED_ACCOUNT_IDS on the production backend. Preflight reads the RESET allowlist; an account that is not in it is refused with 403 not_allowlisted even though it is a real is_test pool account. Adding an id to that allowlist does NOT arm anything: the reset and teardown routes stay absent while E2E_TEST_ROUTES_ENABLED is false
    - the account can actually LOG IN. As of S1293 ALL TEN pool rows carry a real password_hash and sign in through the customer login endpoint (buyer-01 since S1202, the remaining nine since S1293; BQ-E2E-FULL-POOL-LOGIN-ENABLEMENT-S1292). Login capability is now pool-wide, but preflight authorization is a SEPARATE gate; only ids in E2E_RESET_ALLOWED_ACCOUNT_IDS (currently buyer-01 only) pass preflight; every other pool account is refused 403 not_allowlisted before any browser opens, so a Phase 2+ charter for an account other than buyer-01 needs that id added to the allowlist first
  tool_or_endpoint: "e2e-harness run (the runtime calls GET /api/v1/e2e/preflight/{account_id} before any browser opens)"
  argument_sourcing:
    account_ids: the allowlisted is_test pool accounts only - never a real customer account
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: preflight returns allowed=true for every declared account, then the browser opens
    verification: report shows the charter ran; preflight refusals appear before any browser artifact exists
  expected_failures:
    - signature: preflight refusal (404, 403, 401, non-200, allowed=false, timeout)
      cause: route disabled (404), missing or wrong internal API key (401/403), rate limited (429 - the route is throttled 30/60s and fails closed if Redis is unreachable), account not allowlisted, or not an is_test account (When it breaks-03)
    - signature: 'Production targeting refused: E2E_INTERNAL_API_KEY is required for preflight'
      cause: the harness has no internal key; it refuses before opening a browser and before any network call (When it breaks-03)
  next_step_success: proceed; remember that a mutating journey writes real rows and must tag/manifest them (Changes and maintenance.1)
  next_step_failure: do NOT relax the guard; fix the account or the route (Repair-03)
- id: E-03
  trigger: Investigating what a browser run actually did
  pre_conditions:
    - a completed run id
  tool_or_endpoint: "read $E2E_HARNESS_ROOT/reports/<run-id>.json and $E2E_ARTIFACTS_DIR/traces/<charter_id>/step-transcript.jsonl"
  argument_sourcing:
    run_id: from the run output or the newest report file
  idempotency: IDEMPOTENT
  expected_success:
    shape: the transcript lists each step - timestamp, step number, action, target, result, current URL
    verification: the transcript contains no credentials, cookies, headers or DOM dumps by construction
  expected_failures:
    - signature: no screenshot present
      cause: BY DESIGN - screenshots stay withheld until pixel masking exists (When it breaks-04)
  next_step_success: file or update a ticket only for a product failure, never for a harness_error
  next_step_failure: see Repair-04
- id: E-04
  trigger: Verify that buyer-seller mediation blocks plain and disguised contact details without leaving the customer on Submitting
  pre_conditions:
    - all E-02 authenticated production gates pass for the charter's synthetic buyer account
    - backend and frontend production deployments identify the exact reviewed merge commits
    - scripts/harness-env.sh is sourced in the harness shell; never open Infisical in a browser and never copy a secret into the charter, queue, profile or report
  tool_or_endpoint: "E2E_QUEUE_PATH=<isolated temp queue> e2e-harness enqueue @charters/mediation-contact-leak-probe.json; e2e-harness run"
  argument_sourcing:
    charter: committed charters/mediation-contact-leak-probe.json; do not rewrite the goal or synthetic values for a ticket rerun
    credentials: scripts/harness-env.sh runtime loader only
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: report status passed with no findings; transcript records both submissions leaving Submitting and the final done summary says both were held for review
    verification: correlate the two submit timestamps with exactly two new held message_audit rows and zero new inquiries for the synthetic buyer in the run window
  expected_failures:
    - signature: one attempt remains on Submitting or no persistent held result is visible
      cause: customer-response latency after the mediation decision, or a frontend result that exists only as a timed toast
    - signature: held audit exists but an inquiry row was created
      cause: fail-closed delivery boundary regression; stop and treat as a security incident
  next_step_success: retain the run id, exact deployment ids, and read-only database counts in the affected backend/frontend runbooks and ticket completion evidence
  next_step_failure: keep the ticket open; inspect the backend decision/audit/event ordering and the frontend persistent authenticated alert without weakening mediation
- id: E-05
  trigger: Authoring or reviewing a production charter that asks a synthetic account to create and publish a marketplace listing
  pre_conditions:
    - check the Capabilities capability matrix before enqueueing; Phase 3 seller publication must be SHIPPED, not PLANNED
    - use a seller-purpose synthetic fixture whose exact account id is explicitly authorized by production preflight; buyer-01 is the read-only buyer fixture and must not be repurposed as a seller
    - confirm the customer surface actually implements the chartered creation path; the dashboard Listings page is currently a management view for listings published through AIM Data and vectorAIz, not a direct creation surface
  tool_or_endpoint: "review the charter against Capabilities, the production frontend Listings contract, and E-02 before enqueueing"
  argument_sourcing:
    account_id: an explicitly authorized seller-purpose is_test fixture, never buyer-01 and never a real customer
    workflow_status: the Capabilities capability matrix plus current production code/deployment identity
  idempotency: IDEMPOTENT
  expected_success:
    shape: while Phase 3 remains PLANNED, the unsupported charter is rejected as harness_error/configuration error before a product finding is created
    verification: no browser mutation occurs, no seller/security/payment state changes, and no product support ticket is filed
  expected_failures:
    - signature: buyer-01 reaches Listings, sees no create control or incomplete seller onboarding, and the run reports a product blocker
      cause: the charter demanded an unshipped seller workflow from the buyer-only fixture; this is a harness authoring/classification error (When it breaks-12), not evidence of a product regression
  next_step_success: rewrite the charter to use a shipped buyer/read-only journey, or defer it until Phase 3 and an explicitly authorized seller fixture exist
  next_step_failure: do not widen E2E_RESET_ALLOWED_ACCOUNT_IDS, modify account/security state, complete 2FA, or enter Stripe payout details merely to force the charter through; those are separately governed changes
- id: E-06
  trigger: Replay a committed, human-approved recorded browser journey
  pre_conditions:
    - the charter uses params.mode recorded and names a directory beneath committed recordings/
    - manifest approval, script hash, allowed hosts, start URL, account role, mutation contract and product assertions match the charter
    - node_modules and the exact-pinned Playwright dependency are already installed; replay never installs from the network
    - production-read-only recordings declare anonymous true and requires_mutation false; payment remains refused while E2E_PAYMENT_ISOLATION_VERIFIED is unset
  tool_or_endpoint: "e2e-harness enqueue @<recorded-charter.json>; e2e-harness run"
  argument_sourcing:
    recording: committed approved directory, for example anonymous-allai-s1294.v1
    start_url: frontend config only; never hardcode or widen allowed hosts
  idempotency: IDEMPOTENT
  expected_success:
    shape: passed recorded outcome with a distinct redacted replay transcript for this run; an initial stable product failure may retry exactly once in a fresh browser context
    verification: confirm mode recorded, exact charter/recording identity, no eager session/model request for the anonymous allAI recording, and no raw attempt directory after cleanup
  expected_failures:
    - signature: recording manifest or artifact refusal before Playwright launch
      cause: unapproved, malformed, hash-mismatched, escaped, unsafe or contract-mismatched recording (When it breaks-02)
    - signature: flaky_pass_after_retry
      cause: first stable product failure passed on the one allowed fresh-context retry; count is incremented but no ticket is filed
  next_step_success: retain the run-specific report and recording identity; explicit enqueue governs any future nightly replay
  next_step_failure: repair the reviewed recording or product; never edit an approved recording in place without a new reviewed commit
```

**T-2026-000698 production proof (2026-08-24):** `run-20260824T183519Z-9f8666bb` passed `mediation-contact-leak-probe` with no findings and no manual intervention. The plain and word-separated fake phone attempts both left **Submitting...** and visibly returned `Message held for review. Please revise.` Read-only PostgreSQL corroboration found two held audit rows (retry count 3 each) and zero new inquiries. Backend deployment `bce826e7-25f4-40a9-8b1a-513fbbfdfa75` and frontend deployment `4ea6a792-b13f-4715-bdd9-5a6ef702dc05` were both SUCCESS at their exact reviewed merge commits before the run.

## When it breaks

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `browser_journey refused: E2E_PROD_FRONTEND_URL is required` | The sanctioned production frontend URL is not configured. There is deliberately NO hardcoded fallback — a hardcoded `https://ai.market` default was removed at S1196 | `echo $E2E_PROD_FRONTEND_URL` in the harness environment; check the launchd plist | Repair-01 | CONFIRMED |
| F-02 | Outcome `harness_error` with a params or recording-refusal message; no browser opened | Charter missing `params.mode`, missing `params.goal` for agentic mode, an unsupported mode, missing/unapproved/malformed recorded artifact, manifest/script hash or contract mismatch, unsafe host/action, or a `start_url` that is not `frontend` or a sanctioned production URL | read the outcome summary in the report; check the charter JSON and the committed recording tree | Repair-02 | CONFIRMED |
| F-03 | Run refused before the browser opened, citing production targeting or preflight | `E2E_PROD_TARGETING_ENABLED` unset, account ids not declared, backend preflight route disabled or returning `allowed=false` | curl the preflight route for the account id; check the flag | Repair-03 | CONFIRMED |
| F-04 | No screenshot in the artifacts | BY DESIGN. Screenshots are replaced by a text placeholder because no deterministic pixel masking exists yet; a screenshot can show a token, an email or customer data. Traces ARE now persisted, redacted (S1197): NDJSON entries are redacted line-by-line, `resources/` response bodies and every binary or non-UTF-8 entry are withheld, and `redaction-manifest.json` records what happened to each entry | `find $E2E_ARTIFACTS_DIR -name '*.zip'` returns the redacted trace; no image files appear | Repair-04 | CONFIRMED |
| F-05 | Playwright cannot launch: executable missing | The Chromium binary was never installed for this virtualenv (the pip dependency does not install the browser) | run `playwright install chromium` in the harness venv and retry | Repair-05 | CONFIRMED |
| F-06 | A browser journey targeted production without the targeting flag | The charter set `anonymous: true` with no accounts and `requires_mutation` falsy, which is the sanctioned exemption — or a charter is abusing that exemption while actually mutating | read the charter params; a journey that authenticates or writes MUST NOT set `anonymous: true` | Repair-06 | CONFIRMED |
| F-07 | A harness problem raised a support ticket | Should not happen: only `failed` outcomes become findings/tickets; `harness_error` never does | grep the run report for the outcome status; check `tickets.py` dedup | Repair-07 | CONFIRMED |
| F-08 | `Production targeting refused: E2E_INTERNAL_API_KEY is required for preflight`, or preflight returns 401 | The harness environment was never loaded — the run did not go through `scripts/run-nightly.sh` / `scripts/harness-env.sh`, or the Infisical token at `~/.config/infisical/sysadmin-token` is dead | `env -i HOME=$HOME PATH=/usr/local/bin:/usr/bin:/bin /bin/bash -c 'source scripts/harness-env.sh && echo ${#E2E_INTERNAL_API_KEY}'` — expect 64 | Repair-08 | CONFIRMED |
| F-09 | Preflight returns 403 `not_allowlisted` for a genuine `is_test` pool account | Preflight consults `E2E_RESET_ALLOWED_ACCOUNT_IDS`. Being an `is_test` pool account is necessary but NOT sufficient — the id must also be on that allowlist | read the variable on the production backend service; compare with the charter's declared account ids | Repair-09 | CONFIRMED |
| F-10 | Preflight passes, then the browser cannot sign in as the synthetic account | RESOLVED for ALL TEN pool accounts (buyer-01..05, seller-01..05). buyer-01 enabled S1202; the remaining nine enabled S1293 (BQ-E2E-FULL-POOL-LOGIN-ENABLEMENT-S1292, Gate-1 unanimous + Max GO). Every pool row now carries a real `password_hash` and signs in through the customer login endpoint (all ten verified live, HTTP 200; queued S1292, executed S1293). NOTE: login is pool-wide, but preflight still allowlists buyer-01 only (`E2E_RESET_ALLOWED_ACCOUNT_IDS`) — the other nine need their id added to preflight before a Phase 2+ browser opens (Capabilities, How to operate-02). | query the production `users` row: every pool account shows a non-NULL `password_hash` and `auth_methods` containing `password` | Repair-10 | CONFIRMED |
| F-11 | A real seller's `view_count` (or featured impressions) climbs on nights the harness ran, or a synthetic buyer's browsing shows up in a real seller's numbers | The harness is not identifying itself. The backend suppresses counter/telemetry writes only when the ACTOR is synthetic — `is_test` on the authenticated user, or the `ai-market-e2e-harness` token in the User-Agent for the anonymous walk. A browser context launched without that UA is indistinguishable from a customer. This was live damage from S1196 to S1202 | `curl -s -X POST "$E2E_PROD_BACKEND_URL/featured-listings/impressions" -H 'Content-Type: application/json' -H 'User-Agent: Mozilla/5.0 ai-market-e2e-harness/0.1' -d '{"listing_id":"<id>","locale":"en","slot":0}'` — expect `{"recorded":false}`. Then GET a published listing twice with that UA and confirm `view_count` does not move | Repair-11 | CONFIRMED |
| F-12 | A seller-publication charter uses buyer-01, finds no create control or seller readiness, and files a product ticket | The charter asks the buyer-only fixture to perform the unshipped Phase 3 seller journey. The dashboard Listings page is a management surface for AIM Data/vectorAIz publications, not direct creation. | Confirm Phase 3 is still PLANNED in Capabilities; confirm the charter account is buyer-01; inspect the deployed Listings contract for the AIM Data/vectorAIz management-only empty state | Repair-12 | CONFIRMED |

## Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Runtime dispatch
  root_cause: production frontend URL not configured
  repair_entry_point: harness environment / launchd plist
  change_pattern: set E2E_PROD_FRONTEND_URL to the sanctioned production frontend URL; never reintroduce a hardcoded host fallback in code - the config is the single source of truth and the refusal is the safety property
  rollback_procedure: unset the variable; browser journeys refuse again (fail-closed)
  integrity_check: re-run the charter; the browser opens and the report records the configured URL
- id: G-02
  symptom_ref: F-02
  component_ref: Browser runner
  root_cause: malformed or unsupported charter params
  repair_entry_point: the charter JSON
  change_pattern: 'for agentic mode, supply a goal; for recorded mode, name a committed human-approved recording whose manifest and script hash match the charter; use start_url frontend and never weaken a refusal to force launch'
  rollback_procedure: n/a - re-enqueue a corrected charter
  integrity_check: outcome status passed; a transcript artifact exists
- id: G-03
  symptom_ref: F-03
  component_ref: Production guard
  root_cause: targeting flag, account declaration or backend preflight not satisfied
  repair_entry_point: harness environment; the charter account ids; the backend preflight route
  change_pattern: fix the account (must be an allowlisted is_test pool account) or enable the read-only preflight route. NEVER widen the code exemption to make a failing charter pass - the guard is the thing standing between a browser and a real customer account
  rollback_procedure: disable the preflight route; journeys refuse again
  integrity_check: preflight returns allowed=true and the run proceeds
- id: G-04
  symptom_ref: F-04
  component_ref: Artifact redaction
  root_cause: zip-aware redaction was not implemented (RESOLVED S1197)
  repair_entry_point: src/e2e_harness/redaction.py
  change_pattern: RESOLVED S1197. `redact_zip` unpacks the archive, redacts each text/JSON entry line-by-line, withholds every binary/`resources/` entry, repacks, and writes a redaction manifest; any failure raises and the run is harness_error with no artifacts. Sensitive JSON keys are matched by exact name plus segment (so `x-auth-token` is caught while Playwright's structural `sessionId`/`address`/`downloadPath` keys survive), and sensitive URL query values (verification, reset, presigned-download tokens) are redacted while the path and benign params survive. Screenshots stay withheld - that rule is unchanged
  rollback_procedure: revert to withholding
  integrity_check: a test proves a redacted trace contains none of the seeded secrets
- id: G-05
  symptom_ref: F-05
  component_ref: Browser runner
  root_cause: Chromium binary not installed
  repair_entry_point: the harness virtualenv on Titan-1
  change_pattern: run `playwright install chromium` in the venv; document it in the harness README rather than working around it per-machine
  rollback_procedure: n/a
  integrity_check: the anonymous walk passes
- id: G-06
  symptom_ref: F-06
  component_ref: Production guard
  root_cause: anonymous exemption used by a journey that is not anonymous
  repair_entry_point: the charter params
  change_pattern: 'remove anonymous: true from any journey that signs in, declares an account, or writes; that journey must take the full production guard. The exemption requires all three conditions - no account ids AND requires_mutation falsy AND anonymous true'
  rollback_procedure: n/a
  integrity_check: the journey now runs the preflight path before the browser opens
- id: G-08
  symptom_ref: F-08
  component_ref: Production guard
  root_cause: 'the harness environment was not loaded, or the Infisical token is dead'
  repair_entry_point: scripts/harness-env.sh on Titan-1
  change_pattern: 'source scripts/harness-env.sh, or run scripts/run-nightly.sh which does it for you. If the key still does not resolve, the Infisical token is the fault - fix the token. NEVER paste the key into the plist, a dotenv file or a charter - the whole point of the loader is that no production secret is at rest on disk'
  rollback_procedure: 'n/a - the refusal is the safety property, not the bug'
  integrity_check: 'the loader prints a 64-character key length under a launchd-minimal env, and preflight returns 200 for the allowlisted account'
- id: G-09
  symptom_ref: F-09
  component_ref: Production guard
  root_cause: the account id is not in E2E_RESET_ALLOWED_ACCOUNT_IDS
  repair_entry_point: the E2E_RESET_ALLOWED_ACCOUNT_IDS variable on the ai-market-backend production service
  change_pattern: 'add ONLY the pool account ids the journey actually needs, as a JSON array; the backend redeploys and picks it up in about a minute. Keep the list as short as the work requires - it is the list of accounts the future reset route would be permitted to destroy. Removing an id is a one-variable revert'
  rollback_procedure: 'set the variable back to an empty list and redeploy; preflight refuses every account again'
  integrity_check: 'preflight returns allowed=true for the intended account and 403 not_allowlisted for a pool account that was left off; reset and teardown still return 404'
- id: G-10
  symptom_ref: F-10
  component_ref: Production guard
  root_cause: 'the synthetic pool was created without any usable credential. Enabled for buyer-01 in S1202 and for the remaining nine in S1293; all ten now carry a real password_hash'
  repair_entry_point: 'ai-market-backend scripts/e2e_set_pool_password.py (guard: app/e2e/synthetic_accounts.py:set_synthetic_account_password)'
  change_pattern: 'enabling ANY further pool account is an auth + production-data change: it needs an explicit Max decision and unanimous Council BEFORE the write, exactly as buyer-01 did. Never set a password on a production row by hand, and never add a session-mint route. The script takes BOTH the localpart AND the expected account id and refuses if they disagree; the password comes from the process environment only (rotate it in Infisical first, via local-secops propose-review-execute) and is never on argv, in a file, or in a log. Dry-run is the default; a real write needs --apply'
  rollback_procedure: 'per account, scripts/e2e_set_pool_password.py <localpart> <account-id> --revoke --apply sets that pool row password_hash back to NULL through the same guard; a FULL rollback of the S1293 enablement is up to ten such invocations. Post-revert floor: retaining buyer-01 (its original S1202 state) leaves nine NULL password_hash rows; revoking buyer-01 as well yields all ten NULL'
  integrity_check: 'the harness signs in as any pool account through the same login endpoint a customer uses (buyer-01 verified S1202; all ten verified live S1293, HTTP 200 each); every pool row now has a non-NULL password_hash, and no artifact contains any password'
- id: G-11
  symptom_ref: F-11
  component_ref: Harness identity marker
  root_cause: 'the harness did not identify itself, so the backend counted its views as customer views. The browser context was launched with the DEFAULT Chromium User-Agent from S1196 until S1202, and every nightly anonymous walk inflated real sellers view_count'
  repair_entry_point: 'src/e2e_harness/user_agent.py + browser.py (_chromium_browser_user_agent, passed as user_agent= to launch_persistent_context); backend app/e2e/synthetic_exclusion.py:should_count_view'
  change_pattern: 'both halves must hold. The harness sends the ai-market-e2e-harness token on every request including browser page loads; the backend checks the ACTOR (is_test on the authenticated user, or that token in the User-Agent) at every counter and telemetry write site. If you add a NEW counter, telemetry, recommendation or embedding write that a view can trigger, it MUST go through should_count_view. The fail direction is to COUNT: an unknown actor is a real customer'
  rollback_procedure: 'none wanted - reverting either half resumes silent damage to real sellers data. If the UA must change, change the constant, never drop it'
  integrity_check: 'POST /featured-listings/impressions with the harness UA returns recorded:false; two consecutive GETs of a published listing with the harness UA leave view_count unchanged; the same GET on an ordinary browser UA still increments it'
- id: G-07
  symptom_ref: F-07
  component_ref: Failure classification
  root_cause: harness_error leaked into ticket filing
  repair_entry_point: runtime.py finding creation condition
  change_pattern: only outcome status failed creates a Finding; harness_error writes a report and stops. Restore that condition if it drifts
  rollback_procedure: n/a
  integrity_check: force a redaction failure; a report is written and no ticket is filed
- id: G-12
  symptom_ref: F-12
  component_ref: Failure classification
  root_cause: an unsupported seller-publication goal was assigned to the buyer-only fixture and its expected refusal was labelled as a product failure
  repair_entry_point: the charter definition and run classification
  change_pattern: 'while Phase 3 is PLANNED, reject seller-publication charters as harness_error/configuration error before browser mutation and before finding creation. Do not repurpose buyer-01. When Phase 3 ships, use only an explicitly authorized seller-purpose is_test fixture and the shipped creation path'
  rollback_procedure: n/a - removing this guard recreates false product incidents and pressures operators to bypass account and payment controls
  integrity_check: 'a seller-publication charter targeting buyer-01 is refused without a product ticket; the existing buyer read-only journey remains eligible'
```

## Changes and maintenance

### Changes and maintenance.1 Invariants

- **The anonymous walk writes nothing.** No sign-in, no account, no cookie loaded, no storage state saved, no production row created. This includes COUNTERS: the walk must never move a real seller's `view_count` or featured metrics. That holds only because the browser identifies itself with the `ai-market-e2e-harness` token and the backend suppresses counter and telemetry writes for that actor (T-2026-000242, S1202). It was NOT true between S1196 and S1202.
- **The production URL comes from config, always.** No hardcoded host may reappear; when it is unset the runner refuses.
- **The production guard is never widened to make a charter pass.** The anonymous exemption requires all three conditions (no account ids, `requires_mutation` falsy, `anonymous: true`). Any journey that authenticates or mutates takes the full guard: targeting flag, declared accounts, per-account preflight.
- **Nothing is persisted that has not actually been redacted.** A format the redactor cannot scan is WITHHELD, never passed through and labelled redacted.
- **Credentials never enter an artifact.** No password, session cookie, Authorization header, or customer-data response body may reach a report, transcript, trace or ticket. Since S1202 the harness signs in as buyer-01 with a real credential, so this invariant is now load-bearing in practice: the credential is fetched at runtime, is never placed in the Chromium process environment, and tracing does not start until the login window has closed and the value has been cleared. A run that starts tracing before login is a defect, not a preference.
- **A harness problem is never a product ticket.** Only a product failure files a ticket.
- **Recorded means approved and immutable.** Candidate generation produces only an unapproved `.DRAFT`; it cannot run, approve, enqueue or promote itself. Replay accepts only the exact committed three-file recording after manifest, hash, host, fixture and mutation-contract validation. Nightly execution includes only recordings an operator explicitly queued.
- **A charter may request only a shipped workflow from a role-appropriate fixture.** While Phase 3 seller publication is PLANNED, seller-creation goals are harness configuration errors. buyer-01 remains the read-only buyer fixture; the dashboard Listings page manages AIM Data/vectorAIz publications and is not evidence that direct creation should exist.
- **The browser never presses pay on production** while `E2E_PAYMENT_ISOLATION_VERIFIED` is unset. That flag is set only once the Stripe sandbox order router (`build:bq-stripe-sandbox-order-router-s1196`, money path, unanimous Council plus Max GO) is live and verified.
- **A mutating journey tags and manifests every row it creates** (Max Ruling 1, S1194), so a future reset has an exact target list rather than a re-derivation guess.

### Changes and maintenance.2 BREAKING predicates

BREAKING if ANY of (first match wins):
- Removing or widening the production guard, or letting a journey reach production without the targeting flag outside the three-condition anonymous exemption.
- Persisting an artifact format the redactor cannot actually scan, or removing the withholding of screenshots/zips before zip-aware redaction exists.
- Allowing a browser journey to authenticate, mutate production, or transact without the gates in Changes and maintenance.1.
- Reintroducing a hardcoded production host, or making the missing-config case fall through instead of refusing.
- Making `harness_error` outcomes file product tickets.

### Changes and maintenance.3 REVIEW predicates

REVIEW if ANY of (after BREAKING predicates fail):
- Adding a new charter mode (recorded replay, agentic re-walk) or changing the step/timeout/cost caps.
- Implementing zip-aware trace redaction (new persistence surface).
- Changing the failure-signature composition used for ticket dedup.
- Adding the live Codex agent loop that drives the browser.

### Changes and maintenance.4 SAFE predicates

SAFE otherwise:
- New public-page assertions on the anonymous walk; test additions; README and documentation.
- Selector or timeout tuning that does not change what is persisted or which guard applies.

### Changes and maintenance.5 Boundary definitions

#### module

Immediate modules of `e2e-harness/src/e2e_harness/`: `browser.py`, `runtime.py`, `redaction.py`, `preflight.py`, `queue.py`, `tickets.py`, `retention.py`, `config.py`, `models.py`.

#### public contract

The `browser_journey` charter shape (`kind`, `account_id`, `params.mode`, `params.goal`, `params.start_url`, `params.anonymous`, `params.requires_mutation`, `params.public_selector`, `params.public_text`), the outcome dict returned to the runtime, and the artifact policy.

#### runtime dependency

`e2e-harness/pyproject.toml [project.dependencies]` — currently `playwright`.

#### config default

Environment variables read in `config.py`: `E2E_PROD_FRONTEND_URL`, `E2E_PROD_TARGETING_ENABLED`, `E2E_HARNESS_ROOT`, artifact/report/retention paths and windows.

### Changes and maintenance.6 Adjudication

The more restrictive classification wins between disagreeing agents. Anything touching authentication, production mutation or the money path escalates to Max; the ruling is added to Changes and maintenance.1 as a clarification.

## Acceptance criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: You need the fastest real signal that ai.market is reachable and renders for a stranger. What do you queue?
    expected_answers:
      - kind: human_action
        action: 'a browser_journey charter with params mode agentic, anonymous true, requires_mutation false, start_url frontend, and no account ids; then e2e-harness run'
    weight: 0.0909090909
  - id: I-02
    type: operate
    refs: [E-01]
    scenario: The run passed. Which artifacts should exist?
    expected_answers:
      - kind: human_action
        action: the redacted step transcript and the redacted trace zip; screenshots are still withheld by policy
    weight: 0.0909090909
  - id: I-03
    type: operate
    refs: [E-02]
    scenario: A charter must sign in as a synthetic buyer. What must be true before the browser opens?
    expected_answers:
      - kind: human_action
        action: declared is_test pool account ids, E2E_PROD_TARGETING_ENABLED set, and per-account preflight returning allowed=true; the anonymous exemption must NOT be used
    weight: 0.0909090909
  - id: I-04
    type: isolate
    refs: [F-01]
    scenario: 'A browser_journey refuses with: E2E_PROD_FRONTEND_URL is required. Is this a bug?'
    expected_answers:
      - kind: human_action
        action: no - it is the designed fail-closed behaviour; set the config, never add a hardcoded host back
    weight: 0.0909090909
  - id: I-05
    type: isolate
    refs: [F-04]
    scenario: A colleague reports the trace zip is missing from the artifacts and wants it restored by passing it through redact_artifact. Response?
    expected_answers:
      - kind: human_action
        action: as of S1197 the trace IS persisted, redacted, by `redact_zip`. If it is missing, do NOT reach for `redact_artifact`'s text path - find out why redaction raised, because a raise means the run was classified harness_error and nothing was persisted, which is the intended fail-closed behaviour
    weight: 0.0909090909
  - id: I-06
    type: isolate
    refs: [F-06]
    scenario: A new seller charter that publishes a listing sets anonymous true so that it runs without the targeting flag. Assessment?
    expected_answers:
      - kind: human_action
        action: that is an abuse of the exemption and a BREAKING change in effect - a mutating journey must take the full production guard
    weight: 0.0909090909
  - id: I-07
    type: repair
    refs: [G-05]
    scenario: Playwright reports the Chromium executable is missing on a fresh checkout. Fix?
    expected_answers:
      - kind: human_action
        action: run playwright install chromium in the harness virtualenv and keep the step documented in the harness README
    weight: 0.0909090909
  - id: I-08
    type: repair
    refs: [G-07]
    scenario: A redaction failure filed a support ticket against the product. Fix?
    expected_answers:
      - kind: human_action
        action: restore the classification rule - only outcome status failed creates a Finding; harness_error writes a report and files nothing
    weight: 0.0909090909
  - id: I-09
    type: evolve
    refs: [Changes and maintenance.2]
    scenario: A proposed change lets any browser_journey without account ids skip the production targeting flag. Classify.
    expected_answers:
      - kind: classification
        verdict: BREAKING
    weight: 0.0909090909
  - id: I-10
    type: evolve
    refs: [Changes and maintenance.3]
    scenario: A proposed change implements zip-aware trace redaction so traces can be persisted. Classify.
    expected_answers:
      - kind: classification
        verdict: REVIEW
    weight: 0.0909090909
  - id: I-11
    type: isolate
    refs: [E-05, F-12, G-12]
    scenario: A seller-publication charter uses buyer-01 and reports a product blocker because Listings has no create control while Phase 3 is still PLANNED. Assessment?
    expected_answers:
      - kind: human_action
        verb: classify
        object: unsupported seller-publication charter
        target: harness_error without product-ticket creation
        action: classify it as a harness authoring/configuration error and file no product ticket; do not widen the allowlist, repurpose buyer-01, modify seller security state, or enter payout details to force an unshipped journey through
    weight: 0.090909091
```

## Maintenance

```yaml lifecycle
last_refresh_session: S1622
last_refresh_commit: b3da50904b3019e091487297f5ffde7ed4f694ac
last_refresh_date: 2026-08-27T16:55:00Z
owner_agent: mars
refresh_triggers:
  - any phase of BQ-E2E-BROWSER-RUNNER-S1194 landing (Phase 2 authenticated buyer, Phase 3 mutating seller, Phase 4 recorded nightly)
  - zip-aware trace redaction landing (the artifact policy changes)
  - the Stripe sandbox order router going live (the pay boundary moves)
  - any change to the production guard or the anonymous exemption
scheduled_cadence: 90d
first_staleness_detected_at: null
```

Refresh log:
- S1622 (2026-08-27): refreshed Phase 4 from planned to shipped against e2e-harness main `b3da50904b3019e091487297f5ffde7ed4f694ac`; recorded the human-approved production-read-only `anonymous-allai-s1294.v1`, exact replay guard, one-retry policy and explicit-enqueue boundary. The parent anonymous-allAI BQ remains open: production has no isolated Railway environment, so Redis/readiness fault injection, real limit exhaustion and anonymous-only kill-switch activation must not be forced against customers merely to obtain Gate-4 evidence.
- S1196 (2026-07-12): first authoring, against the code shipped this session (e2e-harness main `9d38d2e`) and a live production verification run (headless Chromium walked https://ai.market anonymously; report `run-20260712T143553Z-dc69f64b`). Discharges S1196-D1 and S1196-D2.
