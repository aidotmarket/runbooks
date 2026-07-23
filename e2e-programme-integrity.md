---
runbook_id: e2e-programme-integrity
domain: e2e-testing
status: ACTIVE
authoritative_for:
  - topic: e2e-programme-integrity
    section: §C. Architecture & Interactions
aliases: []
error_signatures: []
supersedes: []
superseded_by: []
owner: mars
last_verified_at: 2026-07-23
system_name: e2e-programme-integrity
purpose_sentence: Prove that the automated testing programme is telling the truth - that its tests actually run, actually exercise the product, honestly claim only what they proved, and surface what they find - because every failure this system has had looked exactly like success.
owner_agent: mars
escalation_contact: Max (any change to what a checked coverage item MEANS, to the 30-item catalog, or to what a charter is permitted to do on production); either instance (Vulcan/Mars) operates this runbook
lifecycle_ref: §J
authoritative_scope: The INTEGRITY of the E2E testing programme end to end - the honesty rules a browser charter must satisfy before it may be committed or enqueued, the audit procedure that proves the programme is actually working rather than merely appearing to, and the catalogue of known deception modes with their detection steps. NOT authoritative for the browser_journey runner mechanism itself (e2e-browser-runner.md), the status publisher and coverage manifest plumbing (e2e-test-status-publisher.md), the ops.ai.market Test page render surface (ops-ai-market.md), the synthetic account pool and its erasure footprint (account-teardown.md), or Council dispatch mechanics (agent-dispatch.md).
linter_version: 1.0.0
---

# E2E Programme Integrity

> Max, S1315: "This is the crucial test of our system. If we solve this we have a business. If not we have a gigantic pile of crap."
>
> This runbook exists because of a single recurring pattern: **every failure this programme has had looked exactly like success**. The nightly died at startup for weeks and the page simply showed nothing. Runs completed while coverage sat at zero. Findings were published as a bare count with no text. Tickets were silently never filed. When ticketing was finally connected it pointed at a decommissioned host, which would have looked like it was working. A dead charter was mapped to a real journey, which would have shown a permanent false red. A charter claimed a whole journey while walking one page, which would have shown a false green. A charter was written that could not perform its own steps and would have improvised password guesses against our only enabled production account.
>
> None of those announced themselves. A future instance CANNOT assume this programme is healthy because it is running. Run §E-01 and prove it.

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

### M1 — Dependencies & Credentials / Source-of-Truth

| Dependency | What it provides | Where it lives | Owning service |
|---|---|---|---|
| Coverage catalog | The 30 items (M1–M11 MAX, A1–A19 ADDITIONS) that define what "tested" means. The single source of what the programme claims to cover | `docs/coverage.json` (+ `docs/coverage.md`) in `aidotmarket/e2e-harness` | e2e-harness |
| Committed charters | The journey definitions, each declaring `covers` / `covers_partial` against the catalog | `charters/*.json` in `aidotmarket/e2e-harness` | e2e-harness |
| The charter guard | The test that refuses a committed charter which does not parse, declares no coverage id, references an unknown id, or names a non-allowlisted account | `tests/test_charters.py` | e2e-harness |
| Live run queue | What the nightly ACTUALLY runs. NOT the same set as the committed charters — a charter can be appended here directly and escape the guard | `queue.jsonl` under `E2E_HARNESS_ROOT` (runtime, not in the repo) | e2e-harness runtime |
| Published status record | The per-item coverage and per-run findings the ops Test page renders | Living State key `infra:e2e-test-status` | e2e-test-status-publisher.md |
| Nightly scheduler | The launchd job that runs the queue and activates publishing | `com.ai-market.e2e-harness.nightly` → `scripts/run-nightly.sh` → `scripts/harness-env.sh` | e2e-browser-runner.md |
| Support ticket API | Where findings become tickets. Must resolve to the PRODUCTION backend | `E2E_SUPPORT_API_URL` + `E2E_SUPPORT_INTERNAL_API_KEY`, exported by `scripts/harness-env.sh` | ai-market-backend |

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Charter guard refuses a committed charter with no coverage mapping, an unknown id, or a non-allowlisted account | SHIPPED | `tests/test_charters.py` | self | 2026-07-23 |
| Coverage moves only from a real mapped run; `covers` sets passed/failed, `covers_partial` sets partial | SHIPPED | `src/e2e_harness/status_publisher.py` | `tests/test_status_publisher.py` | 2026-07-23 |
| Unmapped charter that ran emits a WARNING instead of silently moving nothing | SHIPPED | `src/e2e_harness/status_publisher.py` | `tests/test_status_publisher.py` | 2026-07-23 |
| Finding text (not just a count) reaches the published record, bounded and redacted | SHIPPED | `src/e2e_harness/status_publisher.py` | `tests/test_status_publisher.py` | 2026-07-23 |
| Ticket-filing failure is announced rather than swallowed, and counted per run | SHIPPED | `src/e2e_harness/tickets.py` | `tests/test_runtime.py` | 2026-07-23 |
| Production runs fail closed when a service URL resolves off the production backend | SHIPPED | `src/e2e_harness/config.py` | `tests/test_runtime.py` | 2026-07-23 |
| Guard sees charters appended straight to the runtime queue | BROKEN | `tests/test_charters.py` | — | 2026-07-23 |
| Charter authoring standard (§H.1) enforced mechanically rather than by review judgement | PLANNED | — | n/a | — |
| Stale-record and expiring-blocker mechanisms (`BQ-STALE-RECORD-AND-EXPIRING-BLOCKER-CLAIMS-S1315`) | PLANNED | — | n/a | — |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Catalog | `docs/coverage.json` | — | publisher, charters, guard | Defines what "tested" means. Changing it changes the meaning of every green tick, so it is a Max-escalation change. |
| Charter | `charters/<id>.json` | — | queue, runner | Carries the goal text the AI executes AND the coverage claim. Both are integrity surfaces: the goal decides what actually happens on production, the claim decides what the page tells Max. |
| Guard | `tests/test_charters.py` | — | CI, charters | Enforces the mechanical half of honesty on COMMITTED charters. It cannot see the runtime queue (§F-05). |
| Queue | `queue.jsonl` under `E2E_HARNESS_ROOT` | — | nightly runner | The authoritative list of what actually runs. Diverges from `charters/` silently. |
| Publisher | `status_publisher.py` | `infra:e2e-test-status` | Test page | Turns run outcomes into the coverage record. Fail-soft by design, so a publish failure is invisible unless looked for. |
| Test page | ops.ai.market/test | — | published record | Read-only. What Max sees. A blank or stale page is indistinguishable from a healthy quiet night without §E-01. |

Prose: the catalog defines the 30 journeys. A charter claims some of them and carries the goal an AI executes in a real browser against production. The guard checks committed charters. The queue decides what actually runs and is NOT the same set. The publisher folds outcomes into one record, fail-soft, and the Test page renders it. Integrity is not any one of these — it is the agreement between them. Every incident in this programme has been a disagreement between two of these surfaces that nothing detected.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan/Mars | Run the integrity audit (§E-01) | `shell_request` + `state_request` | Titan-1 + Living State read | COMPLETE — run it before trusting any coverage number |
| Vulcan/Mars | Author or amend a charter against §H.1 | `shell_request` edit + Council review | Titan-1 shell | COMPLETE |
| Vulcan/Mars | Reconcile the queue against committed charters (§E-03) | `shell_request` | Titan-1 shell | COMPLETE — the guard cannot do this yet |
| MP (Codex) | Build charters and guard changes | `council_request mode=build` | Council dispatch | COMPLETE — its summaries over-claim; diff-inspect at file:line every time |
| CC / GLM / DS | Review charters for safety and coverage honesty | `council_request mode=review` (builder excluded) | Council dispatch | COMPLETE — this review has caught a dangerous charter and two false coverage claims |
| launchd nightly | Execute the queue and publish | plist + `scripts/run-nightly.sh` | Titan-1 | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: Prove the testing programme is actually working. Run this before quoting ANY coverage number to Max, after any harness change, and whenever the Test page looks quiet
  pre_conditions:
    - Living State reachable
    - Titan-1 shell available
  tool_or_endpoint: "the six-point integrity audit below, in order, all six"
  argument_sourcing:
    record: state_request get on infra:e2e-test-status
    reports: newest files under $E2E_HARNESS_ROOT/reports
    queue: queue.jsonl under E2E_HARNESS_ROOT
  idempotency: IDEMPOTENT
  expected_success:
    shape: 'all six points pass - (1) the newest run is RECENT and its duration is plausible for the journeys it ran, not sub-second; (2) every queued charter appears in the run report, and every charter in the run report carries a coverage mapping; (3) the per-item coverage in the record was moved by that run id, not by an older one; (4) recent_runs entries carry finding TEXT, not only a count; (5) findings that should have produced tickets have ticket refs, and unticketed_findings_count is zero; (6) the run report status matches what the Test page shows'
    verification: 'each point is checked against a DIFFERENT surface than the one that produced it - report on disk vs published record vs live queue vs ticket system. Agreement across surfaces is the signal; a single surface looking healthy is not'
  expected_failures:
    - signature: newest run finished in under a second, or is days old
      cause: the nightly is dying at startup or not firing at all - the exact failure that went unnoticed for weeks (§F-01)
    - signature: runs complete but every coverage item still reads never_run
      cause: the charters that ran carry no coverage mapping, or the queue copy lost its mapping (§F-02)
    - signature: findings_count above zero but no finding text and no ticket refs
      cause: the publisher or the ticket path is degraded (§F-03, §F-04)
  next_step_success: the number you are about to quote is trustworthy; quote it
  next_step_failure: do NOT quote coverage; repair per the referenced §G entry first
- id: E-02
  trigger: Author or amend a charter, before committing it
  pre_conditions:
    - the journey it claims exists in docs/coverage.json
  tool_or_endpoint: "the §H.1 authoring standard, then Council review by a reviewer that is not the author"
  argument_sourcing:
    item_ids: from docs/coverage.json
    account_id: only an id that passes production preflight
  idempotency: IDEMPOTENT
  expected_success:
    shape: 'the charter can actually perform every step it instructs; it claims covers ONLY where it exercises the whole catalog item, covers_partial otherwise; its goal hunts rather than confirms; it cannot pay, purchase, delete, edit live data or reset a password; its declared environment contract matches what it really writes'
    verification: 'a reviewer who is not the author confirms each clause of §H.1 against the goal text AND against the harness code that would execute it - not against the charter description'
  expected_failures:
    - signature: the goal instructs an action the harness has no primitive for
      cause: the agent will IMPROVISE that step against production. This is how a charter came to guess passwords at our only enabled account (§F-06)
    - signature: covers claims a whole item for a partial walk
      cause: a false green on the page Max reads (§F-07)
  next_step_success: commit, then enqueue
  next_step_failure: rewrite the goal to what the charter can honestly do, and reduce the claim to match
- id: E-03
  trigger: Reconcile what actually runs against what has been reviewed
  pre_conditions:
    - access to both the repo and E2E_HARNESS_ROOT
  tool_or_endpoint: "compare charter_ids in queue.jsonl against charters/*.json, and compare each queued entry's covers/covers_partial against the committed file"
  argument_sourcing:
    queue: queue.jsonl under E2E_HARNESS_ROOT
    committed: charters/*.json
  idempotency: IDEMPOTENT
  expected_success:
    shape: 'every queued charter_id has a committed file; every queued entry carries the same coverage mapping as its file; no queued entry has an empty mapping'
    verification: 'diff the two sets by id, then field by field on covers and covers_partial'
  expected_failures:
    - signature: a queued charter has no file in charters/
      cause: it has never passed the guard or a review; its goal text has never been checked for safety or honesty (§F-05)
    - signature: a queued entry has covers null while its committed file declares ids
      cause: the queue copy predates the mapping; coverage can never move for it (§F-02)
  next_step_success: none - the two surfaces agree
  next_step_failure: repair per §G-02 / §G-05
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | The Test page is quiet, or the newest run finished in well under a second | The nightly is failing at startup before a browser opens. Historically: the scheduler's stripped environment could not find the tool the planner needs. It reports as a harness error with no product signal, so the page simply shows nothing new | read the newest run report: a sub-second duration with `harness_error` on every charter is a startup failure, not a quiet night. Check the scheduler log | §G-01 | CONFIRMED |
| F-02 | Runs complete and pass, but coverage items stay `never_run` | The charter that ran declares no `covers`/`covers_partial`, or the QUEUE copy of the charter lost the mapping the committed file has | GET the record and look for the WARNING naming the charter; compare the queue entry against `charters/<id>.json` | §G-02 | CONFIRMED |
| F-03 | Findings exist but the page shows only a count | The published record carries `findings_count` without the per-finding text, or the payload breached its ceiling and the whole record was silently dropped | GET the record: `recent_runs[].findings` should carry severity/summary/owner_hint. Check whether the record version advanced at all | §G-03 | CONFIRMED |
| F-04 | Findings are never ticketed, or tickets appear nowhere useful | Ticketing not configured, or configured against the wrong backend. Both fail quietly by design so a support outage cannot fail a test run | read the run log for the not-configured vs attempted-and-failed warning; check `unticketed_findings_count` in the report; resolve `E2E_SUPPORT_API_URL` in a clean env and confirm it is the PRODUCTION backend | §G-04 | CONFIRMED |
| F-05 | A charter runs nightly that nobody has reviewed | It was appended straight to the runtime queue. The guard only scans `charters/*.json`, so a queue-only charter escapes parse, coverage-mapping and account checks entirely | run §E-03; any queued id with no committed file is unreviewed | §G-05 | CONFIRMED |
| F-06 | A charter's goal instructs a step the harness cannot perform | Authored against the charter's own description rather than the harness code. The agent is an LLM improvising in a live browser: an impossible step becomes an invented one | trace each instructed step to the harness primitive that would execute it. Credentials in particular are consumed once at sign-in and then destroyed, so anything after a logout has no credential path | §G-06 | CONFIRMED |
| F-07 | An item shows green but the journey was never fully exercised | A charter claimed `covers` (complete) for a partial walk, or a charter that can only ever fail was mapped to a real item to satisfy the guard | read the goal against the catalog item's description; a plural catalog item ("key journeys") is not proved by one page | §G-07 | CONFIRMED |
| F-08 | A charter declares a read-only contract while writing to production | The contract field was set to the convenient value rather than the true one. Submitting chat messages, for instance, writes records and spends money | compare the declared contract against every action the goal actually instructs | §G-08 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Queue
  root_cause: the nightly fails before a browser opens, usually a stripped scheduler environment
  repair_entry_point: the launchd plist and scripts/harness-env.sh
  change_pattern: fix the environment at the sanctioned entrypoint so every caller inherits it, not by hand for one run. Then PROVE it by triggering the job immediately rather than waiting for the schedule, and confirm the run lasts a plausible length and opens a browser. A startup failure must never again be able to look like a quiet night
  rollback_procedure: restore the previous plist; the archived copy is kept beside it
  integrity_check: trigger the job; the run report shows real durations and real steps, not sub-second harness errors
- id: G-02
  symptom_ref: F-02
  component_ref: Charter
  root_cause: the charter that ran carries no coverage mapping, or the queue copy lost it
  repair_entry_point: charters/<id>.json and the queue entry
  change_pattern: restore the mapping on the queue entry from the committed file, or add an honest mapping to the charter. NEVER hand-edit the coverage record to show green - coverage moves only from a real mapped run. If a charter cannot honestly claim any item, it should not be queued
  rollback_procedure: remove the mapping; the item returns to never_run on the next publish
  integrity_check: run the charter; the mapped item shows that run id with passed or failed
- id: G-03
  symptom_ref: F-03
  component_ref: Publisher
  root_cause: finding text missing from the record, or the record was dropped for exceeding its size ceiling
  repair_entry_point: src/e2e_harness/status_publisher.py
  change_pattern: 'bound the growth, never raise the ceiling. Remember the ceiling breach is silent - it raises inside the body builder and is swallowed by the fail-soft publish, dropping the ENTIRE record including coverage, in exactly the scenario (everything failing at once) where the page matters most'
  rollback_procedure: none wanted
  integrity_check: measure the worst case - full run ring, maximum findings, every field at its cap - and confirm it sits well under the ceiling with real headroom
- id: G-04
  symptom_ref: F-04
  component_ref: Publisher
  root_cause: ticketing unconfigured, or pointed at the wrong backend
  repair_entry_point: scripts/harness-env.sh and src/e2e_harness/config.py
  change_pattern: export the support endpoint explicitly at the sanctioned entrypoint, pointing at PRODUCTION, and make a production run REFUSE rather than fall back to any non-production host. Do not rely on a library default - one such default silently pointed at a backend decommissioned months earlier, and filing our defects into a dead system is worse than filing none because it looks like it works
  rollback_procedure: unset the support credential; ticketing returns to dormant, which is the safe resting state
  integrity_check: source the env in a clean shell and print the resolved support URL; it must be the production backend. Then run a charter that finds something and confirm a real ticket appears
- id: G-05
  symptom_ref: F-05
  component_ref: Guard
  root_cause: a charter reached the runtime queue without passing through a committed file
  repair_entry_point: tests/test_charters.py and the enqueue path
  change_pattern: require every enqueued charter to originate from a committed file, so the guard and the review gate cannot be bypassed by appending to the queue. Until that lands, run §E-03 by hand at every audit. Do NOT add a skip-list or an exemption to make a guard pass - an exemption is the bypass
  rollback_procedure: none wanted
  integrity_check: append a deliberately unmapped charter to a scratch queue and confirm it is refused
- id: G-06
  symptom_ref: F-06
  component_ref: Charter
  root_cause: the goal instructs a step no harness primitive can perform, so the agent improvises against production
  repair_entry_point: the charter goal text
  change_pattern: 'rewrite the goal down to what the harness can actually do, and reduce the coverage claim to match. Never leave an impossible step in a goal on the assumption the agent will skip it - it will attempt it. Credentials are the classic case - they are consumed once at sign-in and destroyed, so any instruction to sign in again invites password guessing against a live account, which risks lockout and puts the account identity into transcripts'
  rollback_procedure: revert the charter
  integrity_check: a reviewer traces every instructed step to the primitive that executes it
- id: G-07
  symptom_ref: F-07
  component_ref: Catalog
  root_cause: an overclaimed coverage mapping
  repair_entry_point: the charter's covers / covers_partial
  change_pattern: move the claim to covers_partial, or delete it. A checked item must mean a charter proved the WHOLE item as the catalog describes it. A charter that can only fail (for instance one targeting a decommissioned system) must be RETIRED, never mapped - mapping it drags a real journey to a permanent false red
  rollback_procedure: restore the previous mapping
  integrity_check: read the goal beside the catalog description and ask whether a customer would agree the journey was proved
- id: G-08
  symptom_ref: F-08
  component_ref: Charter
  root_cause: the declared environment contract does not match what the charter really writes
  repair_entry_point: the charter params
  change_pattern: make the contract truthful. The contract is what the rest of the harness uses to reason about write exposure, so a comfortable label is a lie the system then acts on. If a charter writes anything to production - chat messages, records, spend - it is not read-only
  rollback_procedure: restore the previous contract value
  integrity_check: enumerate every action the goal instructs and confirm the contract admits all of them
```

## §H. Evolve

### §H.1 Invariants

These are the authoring standard. A charter that breaches any of them must not be committed or enqueued.

- **A checked item means proven.** `covers` may be claimed only when the charter exercises the WHOLE catalog item as described. Anything less is `covers_partial`. Partial never counts as proven, and the record is never hand-edited to show green.
- **A charter can perform every step it instructs.** Trace each step to the harness primitive that executes it. An impossible step is not skipped by the agent, it is improvised — in a real browser, against production.
- **No charter can pay, purchase, delete, unpublish, edit live data, or reset a password.** The pay path stays fail-closed until the money-path work ships and is verified.
- **Authenticated charters use only an account that passes production preflight**, and never attempt to authenticate again after the harness has consumed and destroyed the credential.
- **Every goal hunts rather than confirms.** It must instruct the agent to report anything broken, confusing, inconsistent, slow or missing — not only hard errors — and to report immediately rather than at the end.
- **The declared environment contract is truthful.** If the charter writes anything to production, it is not read-only.
- **A charter that can only ever fail is retired, not mapped.** Mapping a dead charter to a real item manufactures a false failure on the page Max reads.
- **Guards are never weakened to pass.** No skip-list, no exemption, no escape hatch. If a charter cannot satisfy the guard honestly, that is a signal not to ship it.

### §H.2 BREAKING predicates

BREAKING if ANY of (first match wins):
- Claiming `covers` for a journey the charter does not fully exercise, or marking any item proven from anything other than a real mapped run.
- Adding a skip-list, exemption or escape hatch to the charter guard, or any other change that lets an unreviewed charter run.
- Permitting a charter to pay, purchase, delete, unpublish, edit live data, or reset a password on production.
- Allowing a charter to attempt authentication with credentials it does not have, or to a non-allowlisted account.
- Declaring a read-only contract for a charter that writes to production.

### §H.3 REVIEW predicates

REVIEW if ANY of (after BREAKING predicates fail):
- Changing the 30-item catalog: ids, descriptions, or what an item means.
- Changing the audit in §E-01, or removing any of its six points.
- Adding a new charter, or materially rewriting an existing goal.
- Changing which accounts a charter may use, or the production-targeting guards.

### §H.4 SAFE predicates

SAFE otherwise:
- Wording and formatting of this runbook and of `docs/coverage.md`.
- Adding tests that tighten an existing guard without exempting anything.
- Read-only tooling that reports on coverage or run history.

### §H.5 Boundary definitions

#### module

The integrity surfaces taken together: `docs/coverage.json`, `charters/*.json`, `tests/test_charters.py`, and the runtime `queue.jsonl`.

#### public contract

What a green tick on the ops Test page MEANS: a complete, mapped, reviewed charter ran against production and proved that catalog item. Every rule here exists to keep that sentence true.

#### runtime dependency

The nightly scheduler and its environment, the production backend and its preflight, and the support ticket API.

#### config default

The account allowlist that decides which accounts a charter may use, and the production service URLs a run refuses to start without.

### §H.6 Adjudication

The more restrictive classification wins between disagreeing agents. Anything that changes the meaning of a green tick, the catalog, or what a charter may do on production escalates to Max; the ruling is added to §H.1 as a clarification.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: Max asks how much of the product is tested. The Test page shows a number. Do you quote it?
    expected_answers:
      - kind: human_action
        action: not until the six-point audit passes - every failure this programme has had looked like success, so a healthy-looking page proves nothing on its own
    weight: 0.076923077
  - id: I-02
    type: isolate
    refs: [F-01]
    scenario: The newest nightly run finished in under a second and reported no findings. Quiet night?
    expected_answers:
      - kind: human_action
        action: no - that is a startup failure before a browser opened; read the report and the scheduler log, then fix the environment at the sanctioned entrypoint and trigger a run to prove it
    weight: 0.076923077
  - id: I-03
    type: isolate
    refs: [F-02]
    scenario: Charters run and pass every night, yet every coverage item still reads never_run. Where do you look?
    expected_answers:
      - kind: human_action
        action: at the coverage mapping - the queue copy of the charter may have lost the covers ids its committed file declares, so no run can ever move an item
    weight: 0.076923077
  - id: I-04
    type: isolate
    refs: [F-05]
    scenario: You audit the queue and find a charter running nightly with no file in charters/. How serious?
    expected_answers:
      - kind: human_action
        action: it has never passed the guard or a review, so its goal text has never been checked for safety or honesty, and it contributes no coverage signal; reconcile by hand until enqueue is restricted to committed files
    weight: 0.076923077
  - id: I-05
    type: repair
    refs: [G-04]
    scenario: Ticketing is connected but a library default supplies the destination. Ship it?
    expected_answers:
      - kind: human_action
        action: no - resolve the URL in a clean environment and confirm it is the production backend; a default once pointed at a decommissioned host, and filing defects into a dead system is worse than filing none because it looks like it works
    weight: 0.076923077
  - id: I-06
    type: repair
    refs: [G-07]
    scenario: A charter targeting a decommissioned system fails the guard because it declares no coverage. Someone maps it to a real item to make the guard pass. Response?
    expected_answers:
      - kind: human_action
        action: reject and retire the charter - mapping a charter that can only fail drags a real journey to a permanent false red on the page Max reads
    weight: 0.076923077
  - id: I-07
    type: repair
    refs: [G-06]
    scenario: A charter tells the agent to log out and then log back in, but the harness destroys the credential after first use. What happens if it ships?
    expected_answers:
      - kind: human_action
        action: the agent improvises - it reads the account email off the screen and guesses passwords against a live account, risking lockout and putting the identity into transcripts; rewrite the goal to what the session can prove and reduce the claim
    weight: 0.076923077
  - id: I-08
    type: evolve
    refs: [§H.2]
    scenario: A change adds an exemption to the charter guard so one awkward charter can ship. Classify.
    expected_answers:
      - kind: classification
        verdict: BREAKING
    weight: 0.076923077
  - id: I-09
    type: evolve
    refs: [§H.2]
    scenario: A charter walks one public page on a phone-sized window and claims the whole phone-journeys item as complete. Classify.
    expected_answers:
      - kind: classification
        verdict: BREAKING
    weight: 0.076923077
  - id: I-10
    type: evolve
    refs: [§H.3]
    scenario: A change rewrites the goal text of an existing committed charter to explore a new part of the product. Classify.
    expected_answers:
      - kind: classification
        verdict: REVIEW
    weight: 0.076923077
  - id: I-11
    type: ambiguous
    refs: [§H.6, F-07]
    scenario: A charter exercises a catalog item fully on the happy path but cannot reach one error branch the description mentions. Complete claim, or partial?
    expected_answers:
      - kind: classification
        label: PARTIAL_UNTIL_ADJUDICATED
      - kind: human_action
        action: default to covers_partial, because a checked item must mean the whole item was proved; if the branch is genuinely unreachable by any customer the catalog description should change instead, and that is a Max escalation under §H.6 rather than a judgement call at authoring time
    weight: 0.076923077
  - id: I-12
    type: operate
    refs: [E-03]
    scenario: You want to know what the nightly ACTUALLY runs. Is reading charters/ enough?
    expected_answers:
      - kind: human_action
        action: no - the runtime queue is the authoritative list of what runs and it diverges from the committed charters silently; reconcile the two by id and by coverage mapping
    weight: 0.076923077
  - id: I-13
    type: operate
    refs: [E-02]
    scenario: You are about to commit a new charter. What is the last check before it goes in?
    expected_answers:
      - kind: human_action
        action: trace every instructed step to the harness primitive that would execute it, and confirm the coverage claim matches what the goal actually exercises - then have a reviewer who is not the author do the same
    weight: 0.076923077
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1315
last_refresh_commit: ed7660a
last_refresh_date: 2026-07-23T10:35:00Z
owner_agent: mars
refresh_triggers:
  - any change to the 30-item catalog or to what a checked item means
  - the enqueue path being restricted to committed charters (closes F-05)
  - a new class of silent failure being discovered - add it to §F and §G the same session
  - the money path shipping, which changes what a charter is permitted to do
scheduled_cadence: 30d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-07-23T10:35:00Z
first_staleness_detected_at: "2026-07-23T10:49:39.734984+00:00"
```

Refresh log:
- S1315 (2026-07-23): first authoring, on Max's direction, after a session in which the nightly was found dead at startup, coverage was found unable to move, findings were found published without text, ticketing was found silently unconfigured and then pointed at a decommissioned host, a dead charter was found mapped to a real journey, a charter was found overclaiming a whole journey, and a charter was found that would have guessed passwords against our only enabled production account. Every one of those looked like success from the outside. §E-01 exists so a future instance does not have to rediscover that.

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1315 / 2026-07-23T10:35:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
