---
system_name: e2e-browser-runner
purpose_sentence: Operate, diagnose and evolve the browser_journey charter kind in the e2e-harness - the real Chromium browser, driven from Titan-1 via Playwright, that walks ai.market the way a customer does and turns what it finds into reports and tickets.
owner_agent: mars
escalation_contact: Max (any journey that authenticates, mutates production, or touches the money path; arming of reset/teardown routes); either instance (Vulcan/Mars) operates this runbook
lifecycle_ref: §J
authoritative_scope: The browser_journey charter kind in aidotmarket/e2e-harness - BrowserJourneyRunner, its dispatch branch in the harness runtime, its charter params contract, the production-guard exemption for anonymous journeys, and browser artifact redaction/persistence. NOT authoritative for the rest of the harness (queue, retention sweep, ticket dedup, webhook emitter, launchd schedule), for the production E2E arming of reset/teardown routes (ai-market-backend/docs/runbooks/sysadmin/e2e-prod-arming.md), for the synthetic is_test account pool and its erasure footprint (account-teardown.md), or for Council dispatch mechanics (agent-dispatch.md).
linter_version: 1.0.0
---

# E2E Browser Runner

> The missing heart of the E2E programme, shipped in phases. Before S1196 the harness had a queue, redaction, retention, ticket filing, a webhook emitter and a nightly schedule - but no browser. `browser_journey` is the charter kind that opens a real Chromium and walks the product. Phase 1 (live since S1196) is the anonymous public walk: it signs into nothing, declares no accounts and writes nothing. Later phases add the signed-in buyer journey, the mutating seller journey and nightly recorded replay. Owner BQ: `BQ-E2E-BROWSER-RUNNER-S1194`, child of `BQ-E2E-TESTING-FRAMEWORK-S1152`.

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

### M1 — Dependencies & Credentials / Source-of-Truth

| Dependency | What it provides | Where it lives | Owning service |
|---|---|---|---|
| `aidotmarket/e2e-harness` | The harness itself: queue, runtime dispatch, `browser.py` runner, redaction, retention, tickets | Titan-1 clone `~/Projects/ai-market/e2e-harness`; main at `9d38d2e` (S1196) | GitHub `aidotmarket/e2e-harness` |
| Playwright + Chromium | The browser substrate. Declared in `pyproject.toml`; the browser binary is installed separately (`playwright install chromium`) | Titan-1, inside the harness virtualenv | Playwright |
| `E2E_PROD_FRONTEND_URL` | The ONLY source of the sanctioned production frontend URL. No hardcoded fallback exists; a `browser_journey` refuses to run when it is unset | harness environment / launchd plist | e2e-harness config |
| `E2E_PROD_TARGETING_ENABLED` | Harness-side opt-in for production targeting. Required for every browser journey EXCEPT the anonymous exemption (§C) | harness environment | e2e-harness config |
| `E2E_HARNESS_ROOT` | Root for queue, reports, artifacts, profiles, auth-states | harness environment; launchd sets it | e2e-harness config |
| `GET /api/v1/e2e/preflight/{account_id}` | Per-account production preflight; proves an account is an allowlisted `is_test` pool account before a browser opens | ai.market backend (production) | ai-market-backend |
| Synthetic `is_test` pool accounts | The ten `seller-01..05@e2e-test.ai.market` / `buyer-01..05@e2e-test.ai.market` production accounts used by authenticated journeys (Phase 2+) | production `users` table | ai-market-backend (see account-teardown.md) |

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| `browser_journey` charter kind accepted through the existing JSONL queue and CLI | SHIPPED | `e2e-harness src/e2e_harness/queue.py`, `cli.py` (unchanged; generic `kind`) | `tests/test_queue.py` | 2026-07-12 |
| Real Chromium launch via Playwright, per-run profile dir | SHIPPED | `src/e2e_harness/browser.py:BrowserJourneyRunner._walk_public_page` | `tests/test_runtime.py` | 2026-07-12 (live walk of https://ai.market, S1196) |
| Anonymous public production walk (Phase 1): signs into nothing, writes nothing | SHIPPED | `src/e2e_harness/browser.py:BrowserJourneyRunner.run` | `tests/test_runtime.py` | 2026-07-12 |
| Fail-closed param handling: malformed charter reports without opening a browser | SHIPPED | `browser.py:_harness_error` | `tests/test_runtime.py` | 2026-07-12 |
| Config-only production URL, fail-closed when unset | SHIPPED | `src/e2e_harness/runtime.py` (`browser_journey` dispatch branch) | `tests/test_runtime.py` | 2026-07-12 |
| Narrow production-guard exemption (no accounts AND `requires_mutation` falsy AND `anonymous: true`) | SHIPPED | `runtime.py:_is_anonymous_browser_preflight_exempt` | `tests/test_runtime.py` | 2026-07-12 |
| Artifact policy: redacted step transcript persisted; trace zip and screenshots WITHHELD | SHIPPED | `browser.py:_redact_and_cleanup`, `src/e2e_harness/redaction.py:redact_artifact` | `tests/test_redaction_retention.py` | 2026-07-12 |
| Zip-aware trace redaction (unpack, redact, repack) | PLANNED — prerequisite for Phase 2 persisting any trace | n/a | n/a | n/a |
| Phase 2: authenticated buyer read-only journey to the pay boundary | PLANNED — needs the backend `E2E_PREFLIGHT_ROUTES_ENABLED` split | n/a | n/a | n/a |
| Phase 3: mutating seller journey (publish a listing); pay step blocked on the Stripe sandbox order router | PLANNED — `build:bq-stripe-sandbox-order-router-s1196` gates the pay step | n/a | n/a | n/a |
| Phase 4: recorded/deterministic nightly replay, agentic re-walk policy | PLANNED | n/a | n/a | n/a |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Charter queue | `src/e2e_harness/queue.py` | `$E2E_HARNESS_ROOT/queue.jsonl` | CLI `e2e-harness enqueue @<path>` | Unchanged by the browser work. `kind` is a free string, so `browser_journey` needed no queue redesign. |
| Runtime dispatch | `src/e2e_harness/runtime.py:_run_charter` | reports dir | `BrowserJourneyRunner` | One branch. Refuses with a config error when `E2E_PROD_FRONTEND_URL` is unset — there is no hardcoded host. |
| Browser runner | `src/e2e_harness/browser.py:BrowserJourneyRunner.run(run_id, charter, profile_dir, auth_state)` | per-run `profile_dir`, artifacts dir | Playwright Chromium, redaction | Returns the same outcome dict shape the runtime already consumes. Phase 1 supports `mode: agentic` only; any other mode is a `harness_error`. |
| Production guard | `runtime.py:_require_prod_preflight` + `_is_anonymous_browser_preflight_exempt` | — | backend preflight route | Every production charter needs `E2E_PROD_TARGETING_ENABLED`, declared account ids and per-account preflight — EXCEPT a browser journey that declares no accounts AND has `requires_mutation` falsy AND sets `anonymous: true`. That exemption exists because the anonymous public walk touches no account and writes nothing. Anything else takes the full guard. |
| Artifact redaction | `src/e2e_harness/redaction.py:redact_artifact` | `$E2E_ARTIFACTS_DIR/traces/<charter_id>/` | retention sweep | Text/JSON only. `.png/.jpg/.jpeg/.webp` and `.zip` are WITHHELD with a placeholder — a text redactor cannot scan a compressed archive, and pretending otherwise produced a mangled blob whose contents were never actually scanned (defect found S1196). Phase 1 therefore persists the redacted step transcript only. |
| Failure classification | `runtime.py` finding creation | reports, support tickets | `tickets.py` | Only `failed` (a product failure) becomes a Finding and a ticket. `harness_error` (browser launch, malformed params, redaction failure) writes a report and NEVER files a product ticket: a false ticket burns response capacity and trains operators to distrust the harness. |

Prose: a charter is appended to the JSONL queue; `e2e-harness run` loads it, creates the per-run profile directory and the account-scoped auth-state path, and dispatches on `kind`. For `browser_journey`, `BrowserJourneyRunner` launches a persistent Chromium context on that profile directory, navigates to the sanctioned production frontend, asserts the page and a public element, then writes a step transcript, redacts it, deletes the raw browser working files, and returns an outcome. Nothing leaves the machine except reports and (later) tickets.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan/Mars | Queue and run a browser journey | `shell_request` on Titan-1: `e2e-harness enqueue @charter.json`, `e2e-harness run` | Titan-1 shell | COMPLETE |
| Vulcan/Mars | Read the run report and artifacts | `shell_request` on `$E2E_HARNESS_ROOT/reports`, `/artifacts` | Titan-1 shell | COMPLETE |
| MP (Codex) | Build harness changes | `council_request mode=build` against a dedicated worktree | Council dispatch | COMPLETE — builder output must be diff-inspected at file:line; commit messages over-claim |
| DS / AG | Review harness changes | `council_request mode=review` (builder excluded) | Council dispatch | COMPLETE |
| launchd (`com.ai-market.e2e-harness.nightly`) | Nightly run at 02:15 local | plist in the harness repo | Titan-1 | PARTIAL — recorded browser journeys are queued nightly only from Phase 4 |
| Codex-as-driver (agentic page reasoning) | Improvise a first walk like a first-time customer | n/a | n/a | PLANNED — Phase 1 walks a fixed public path; the live agent loop lands with the authenticated journeys |

## §E. Operate

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
    verification: 'cat the newest report json; find $E2E_ARTIFACTS_DIR -type f - there must be no trace zip and no screenshot'
  expected_failures:
    - signature: 'browser_journey refused: E2E_PROD_FRONTEND_URL is required'
      cause: production frontend URL not configured (§F-01)
    - signature: 'status harness_error, summary browser_journey requires params.mode'
      cause: malformed charter params; no browser was opened (§F-02)
  next_step_success: promote the charter into the nightly queue once recorded mode exists (Phase 4)
  next_step_failure: repair per §G-01 / §G-02
- id: E-02
  trigger: A browser journey needs to touch an account (Phase 2+)
  pre_conditions:
    - the charter declares account ids from the synthetic is_test pool
    - E2E_PROD_TARGETING_ENABLED is set
    - the backend read-only preflight route is enabled and reachable
  tool_or_endpoint: "e2e-harness run (the runtime calls GET /api/v1/e2e/preflight/{account_id} before any browser opens)"
  argument_sourcing:
    account_ids: the allowlisted is_test pool accounts only - never a real customer account
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: preflight returns allowed=true for every declared account, then the browser opens
    verification: report shows the charter ran; preflight refusals appear before any browser artifact exists
  expected_failures:
    - signature: preflight refusal (404, 403, non-200, allowed=false, timeout)
      cause: route disabled, account not allowlisted, or not an is_test account (§F-03)
  next_step_success: proceed; remember that a mutating journey writes real rows and must tag/manifest them (§H.1)
  next_step_failure: do NOT relax the guard; fix the account or the route (§G-03)
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
    - signature: no trace zip present
      cause: BY DESIGN - traces are withheld until zip-aware redaction exists (§F-04)
  next_step_success: file or update a ticket only for a product failure, never for a harness_error
  next_step_failure: see §G-04
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `browser_journey refused: E2E_PROD_FRONTEND_URL is required` | The sanctioned production frontend URL is not configured. There is deliberately NO hardcoded fallback — a hardcoded `https://ai.market` default was removed at S1196 | `echo $E2E_PROD_FRONTEND_URL` in the harness environment; check the launchd plist | §G-01 | CONFIRMED |
| F-02 | Outcome `harness_error` with a params message; no browser opened | Charter missing `params.mode`, missing `params.goal` for agentic mode, an unsupported mode (recorded mode is not built yet), or a `start_url` that is not `frontend` or a sanctioned production URL | read the outcome summary in the report; check the charter JSON | §G-02 | CONFIRMED |
| F-03 | Run refused before the browser opened, citing production targeting or preflight | `E2E_PROD_TARGETING_ENABLED` unset, account ids not declared, backend preflight route disabled or returning `allowed=false` | curl the preflight route for the account id; check the flag | §G-03 | CONFIRMED |
| F-04 | No trace zip in the artifacts, only a step transcript | BY DESIGN. `redact_artifact` is a text/JSON redactor; a `.zip` is withheld with a placeholder because a compressed archive cannot be scanned by regex. Persisting it through the text path produced a mangled blob that had never actually been scanned | `find $E2E_ARTIFACTS_DIR -name '*.zip'` returns nothing; the placeholder text appears where a trace would be | §G-04 | CONFIRMED |
| F-05 | Playwright cannot launch: executable missing | The Chromium binary was never installed for this virtualenv (the pip dependency does not install the browser) | run `playwright install chromium` in the harness venv and retry | §G-05 | CONFIRMED |
| F-06 | A browser journey targeted production without the targeting flag | The charter set `anonymous: true` with no accounts and `requires_mutation` falsy, which is the sanctioned exemption — or a charter is abusing that exemption while actually mutating | read the charter params; a journey that authenticates or writes MUST NOT set `anonymous: true` | §G-06 | CONFIRMED |
| F-07 | A harness problem raised a support ticket | Should not happen: only `failed` outcomes become findings/tickets; `harness_error` never does | grep the run report for the outcome status; check `tickets.py` dedup | §G-07 | CONFIRMED |

## §G. Repair

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
  change_pattern: 'supply mode: agentic and a goal; use start_url frontend; do not request recorded mode until Phase 4 ships'
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
  root_cause: zip-aware redaction is not implemented
  repair_entry_point: src/e2e_harness/redaction.py
  change_pattern: to persist traces, implement zip-aware redaction - unpack the archive, redact each text/JSON entry, withhold binary resources, repack - with a test asserting no artifact contains a password, session cookie or Authorization header. This is a prerequisite for Phase 2 (authenticated journeys) persisting any trace. Until then, withholding is the correct behaviour, not a bug
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
- id: G-07
  symptom_ref: F-07
  component_ref: Failure classification
  root_cause: harness_error leaked into ticket filing
  repair_entry_point: runtime.py finding creation condition
  change_pattern: only outcome status failed creates a Finding; harness_error writes a report and stops. Restore that condition if it drifts
  rollback_procedure: n/a
  integrity_check: force a redaction failure; a report is written and no ticket is filed
```

## §H. Evolve

### §H.1 Invariants

- **The anonymous walk writes nothing.** No sign-in, no account, no cookie loaded, no storage state saved, no production row created.
- **The production URL comes from config, always.** No hardcoded host may reappear; when it is unset the runner refuses.
- **The production guard is never widened to make a charter pass.** The anonymous exemption requires all three conditions (no account ids, `requires_mutation` falsy, `anonymous: true`). Any journey that authenticates or mutates takes the full guard: targeting flag, declared accounts, per-account preflight.
- **Nothing is persisted that has not actually been redacted.** A format the redactor cannot scan is WITHHELD, never passed through and labelled redacted.
- **Credentials never enter an artifact.** No password, session cookie, Authorization header, or customer-data response body may reach a report, transcript, trace or ticket.
- **A harness problem is never a product ticket.** Only a product failure files a ticket.
- **The browser never presses pay on production** while `E2E_PAYMENT_ISOLATION_VERIFIED` is unset. That flag is set only once the Stripe sandbox order router (`build:bq-stripe-sandbox-order-router-s1196`, money path, unanimous Council plus Max GO) is live and verified.
- **A mutating journey tags and manifests every row it creates** (Max Ruling 1, S1194), so a future reset has an exact target list rather than a re-derivation guess.

### §H.2 BREAKING predicates

BREAKING if ANY of (first match wins):
- Removing or widening the production guard, or letting a journey reach production without the targeting flag outside the three-condition anonymous exemption.
- Persisting an artifact format the redactor cannot actually scan, or removing the withholding of screenshots/zips before zip-aware redaction exists.
- Allowing a browser journey to authenticate, mutate production, or transact without the gates in §H.1.
- Reintroducing a hardcoded production host, or making the missing-config case fall through instead of refusing.
- Making `harness_error` outcomes file product tickets.

### §H.3 REVIEW predicates

REVIEW if ANY of (after BREAKING predicates fail):
- Adding a new charter mode (recorded replay, agentic re-walk) or changing the step/timeout/cost caps.
- Implementing zip-aware trace redaction (new persistence surface).
- Changing the failure-signature composition used for ticket dedup.
- Adding the live Codex agent loop that drives the browser.

### §H.4 SAFE predicates

SAFE otherwise:
- New public-page assertions on the anonymous walk; test additions; README and documentation.
- Selector or timeout tuning that does not change what is persisted or which guard applies.

### §H.5 Boundary definitions

#### module

Immediate modules of `e2e-harness/src/e2e_harness/`: `browser.py`, `runtime.py`, `redaction.py`, `preflight.py`, `queue.py`, `tickets.py`, `retention.py`, `config.py`, `models.py`.

#### public contract

The `browser_journey` charter shape (`kind`, `account_id`, `params.mode`, `params.goal`, `params.start_url`, `params.anonymous`, `params.requires_mutation`, `params.public_selector`, `params.public_text`), the outcome dict returned to the runtime, and the artifact policy.

#### runtime dependency

`e2e-harness/pyproject.toml [project.dependencies]` — currently `playwright`.

#### config default

Environment variables read in `config.py`: `E2E_PROD_FRONTEND_URL`, `E2E_PROD_TARGETING_ENABLED`, `E2E_HARNESS_ROOT`, artifact/report/retention paths and windows.

### §H.6 Adjudication

The more restrictive classification wins between disagreeing agents. Anything touching authentication, production mutation or the money path escalates to Max; the ruling is added to §H.1 as a clarification.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: You need the fastest real signal that ai.market is reachable and renders for a stranger. What do you queue?
    expected_answers:
      - kind: human_action
        action: 'a browser_journey charter with params mode agentic, anonymous true, requires_mutation false, start_url frontend, and no account ids; then e2e-harness run'
    weight: 0.1
  - id: I-02
    type: operate
    refs: [E-01]
    scenario: The run passed. Which artifacts should exist?
    expected_answers:
      - kind: human_action
        action: the redacted step transcript only - no trace zip and no screenshots, both are withheld by policy
    weight: 0.1
  - id: I-03
    type: operate
    refs: [E-02]
    scenario: A charter must sign in as a synthetic buyer. What must be true before the browser opens?
    expected_answers:
      - kind: human_action
        action: declared is_test pool account ids, E2E_PROD_TARGETING_ENABLED set, and per-account preflight returning allowed=true; the anonymous exemption must NOT be used
    weight: 0.1
  - id: I-04
    type: isolate
    refs: [F-01]
    scenario: 'A browser_journey refuses with: E2E_PROD_FRONTEND_URL is required. Is this a bug?'
    expected_answers:
      - kind: human_action
        action: no - it is the designed fail-closed behaviour; set the config, never add a hardcoded host back
    weight: 0.1
  - id: I-05
    type: isolate
    refs: [F-04]
    scenario: A colleague reports the trace zip is missing from the artifacts and wants it restored by passing it through redact_artifact. Response?
    expected_answers:
      - kind: human_action
        action: refuse - the text redactor cannot scan a compressed archive, so that would persist an unscanned artifact while labelling it redacted; implement zip-aware redaction first
    weight: 0.1
  - id: I-06
    type: isolate
    refs: [F-06]
    scenario: A new seller charter that publishes a listing sets anonymous true so that it runs without the targeting flag. Assessment?
    expected_answers:
      - kind: human_action
        action: that is an abuse of the exemption and a BREAKING change in effect - a mutating journey must take the full production guard
    weight: 0.1
  - id: I-07
    type: repair
    refs: [G-05]
    scenario: Playwright reports the Chromium executable is missing on a fresh checkout. Fix?
    expected_answers:
      - kind: human_action
        action: run playwright install chromium in the harness virtualenv and keep the step documented in the harness README
    weight: 0.1
  - id: I-08
    type: repair
    refs: [G-07]
    scenario: A redaction failure filed a support ticket against the product. Fix?
    expected_answers:
      - kind: human_action
        action: restore the classification rule - only outcome status failed creates a Finding; harness_error writes a report and files nothing
    weight: 0.1
  - id: I-09
    type: evolve
    refs: [§H.2]
    scenario: A proposed change lets any browser_journey without account ids skip the production targeting flag. Classify.
    expected_answers:
      - kind: classification
        verdict: BREAKING
    weight: 0.1
  - id: I-10
    type: evolve
    refs: [§H.3]
    scenario: A proposed change implements zip-aware trace redaction so traces can be persisted. Classify.
    expected_answers:
      - kind: classification
        verdict: REVIEW
    weight: 0.1
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1196
last_refresh_commit: 9d38d2e
last_refresh_date: 2026-07-12T14:40:00Z
owner_agent: mars
refresh_triggers:
  - any phase of BQ-E2E-BROWSER-RUNNER-S1194 landing (Phase 2 authenticated buyer, Phase 3 mutating seller, Phase 4 recorded nightly)
  - zip-aware trace redaction landing (the artifact policy changes)
  - the Stripe sandbox order router going live (the pay boundary moves)
  - any change to the production guard or the anonymous exemption
scheduled_cadence: 90d
last_harness_pass_rate: NOT_RUN
last_harness_date: 2026-07-12T14:40:00Z
first_staleness_detected_at: null
```

Refresh log:
- S1196 (2026-07-12): first authoring, against the code shipped this session (e2e-harness main `9d38d2e`) and a live production verification run (headless Chromium walked https://ai.market anonymously; report `run-20260712T143553Z-dc69f64b`). Discharges S1196-D1 and S1196-D2.

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1196 / 2026-07-12T14:40:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
