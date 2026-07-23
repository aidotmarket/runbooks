---
runbook_id: e2e-test-status-publisher
domain: e2e-testing
status: ACTIVE
authoritative_for:
  - topic: e2e-test-status-publisher
    section: §C. Architecture & Interactions
aliases: []
error_signatures: []
supersedes: []
superseded_by: []
owner: mars
last_verified_at: 2026-07-23
system_name: e2e-test-status-publisher
purpose_sentence: Operate, diagnose and evolve the harness-side test-status publisher and coverage manifest - the fail-soft path that turns each e2e-harness run into the redacted, bounded coverage record at Living State key infra:e2e-test-status that the ops.ai.market Test page reads.
owner_agent: mars
escalation_contact: Max (any change to what the publisher writes, the coverage manifest contents, or the Test page's meaning of "proven"); either instance (Vulcan/Mars) operates this runbook
lifecycle_ref: §J
authoritative_scope: The harness-side status publisher in aidotmarket/e2e-harness - src/e2e_harness/status_publisher.py (TestStatusPublisher, StateTransport, publisher_from_config), the coverage manifest docs/coverage.{json,md}, the runtime call site that publishes after every run, and the publisher's dormancy / fail-soft / redaction / bounding contract. NOT authoritative for the browser_journey runner itself (e2e-browser-runner.md), the ops.ai.market Test page render surface that reads infra:e2e-test-status (ops-ai-market.md), the launchd nightly schedule and run-nightly.sh wiring beyond how it activates publishing (e2e-browser-runner.md M1 and harness-env.sh), or Council/build mechanics (agent-dispatch.md).
linter_version: 1.0.0
---

# E2E Test-Status Publisher

> The reporting seam of the E2E programme. A harness run already produces a report on disk and files tickets; this is the piece (c6, shipped S1314) that also writes a single redacted, bounded coverage record to Living State so Max has one honest place to see how much of the product is actually proven. The record lives at `infra:e2e-test-status`; the ops.ai.market Test page reads it read-only and renders it. The publisher is deliberately fail-soft: it never changes a run's outcome and never blocks a run, and it stays dormant unless the sanctioned harness runtime activates it. Owner BQ: `BQ-E2E-TESTING-FRAMEWORK-S1152` (c6 Test page); coverage catalog from `BQ-E2E-BROWSER-RUNNER-S1194`.

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

### M1 — Dependencies & Credentials / Source-of-Truth

| Dependency | What it provides | Where it lives | Owning service |
|---|---|---|---|
| `aidotmarket/e2e-harness` | The publisher and manifest: `src/e2e_harness/status_publisher.py`, `docs/coverage.{json,md}`, the runtime call site | Titan-1 clone `~/Projects/ai-market/e2e-harness`; main at `ed33a10` (c6 v1, S1314) | GitHub `aidotmarket/e2e-harness` |
| Living State key `infra:e2e-test-status` | The single published record: last run, recent-run ring, per-item coverage, and the coverage catalog. Read-only to everyone but the harness | Living State (Koskadeux); `STATE_KEY` in `status_publisher.py` | Koskadeux MCP / backend state API |
| Backend state API `/api/v1/allai/state/{key}` | The GET/PUT/PATCH transport the publisher uses, with optimistic version locking | ai-market-backend (production) | ai-market-backend |
| `E2E_STATE_API_URL` + the internal state credential | The two config values that build `StateTransport`. Absent either one, `publisher_from_config` returns a publisher with `transport=None` and publishing is dormant | harness environment via `scripts/harness-env.sh` (S1201); the credential is fetched from Infisical at runtime, never written to the plist or repo | e2e-harness config |
| `docs/coverage.json` | The canonical machine manifest: `schema_version` 1 and exactly 30 items, each `id` unique with `group` in {MAX, ADDITIONS}. `docs/coverage.md` is its human-readable twin | e2e-harness repo; path overridable via `E2E_COVERAGE_MANIFEST_PATH` (`config.py:coverage_manifest_path`) | e2e-harness |
| ops.ai.market Test page | The read-only render surface for `infra:e2e-test-status`. NOT part of this scope; see `ops-ai-market.md` | `aidotmarket/ops-ai-market`; ops main `ec3ed2e9`, merged PR #15 (S1314) | ops-ai-market |

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Publish one record per run to `infra:e2e-test-status` after every harness run | SHIPPED | `src/e2e_harness/status_publisher.py` | `tests/test_status_publisher.py` | 2026-07-22 |
| Dormant unless activated: `transport=None` when the state URL or credential is absent | SHIPPED | `src/e2e_harness/status_publisher.py` | `tests/test_status_publisher.py` | 2026-07-22 |
| Fail-soft: any publish error is swallowed with a warning and the run outcome is unchanged | SHIPPED | `src/e2e_harness/status_publisher.py` | `tests/test_status_publisher.py` | 2026-07-22 |
| Redacted and 64 KiB-bounded payload; recent-run ring capped at 20 | SHIPPED | `src/e2e_harness/status_publisher.py` | `tests/test_status_publisher.py` | 2026-07-22 |
| Coverage manifest validation: schema_version 1, exactly 30 MAX/ADDITIONS items, no duplicate ids | SHIPPED | `src/e2e_harness/status_publisher.py` | `tests/test_status_publisher.py` | 2026-07-22 |
| Honest per-item coverage (never_run/partial/passed/failed); partial never counted as proven | SHIPPED | `src/e2e_harness/status_publisher.py` | `tests/test_status_publisher.py` | 2026-07-22 |
| Optimistic-locked upsert: PUT at version 0 when absent, else PATCH at the read version | SHIPPED | `src/e2e_harness/status_publisher.py` | `tests/test_status_publisher.py` | 2026-07-22 |
| Charter-level publish cadence (weekly agentic, nightly recorded); Max directive e475ebc5, queued on BQ-E2E-TESTING-FRAMEWORK-S1152 | PLANNED | — | n/a | — |
| Console for Max-entered test goals on the ops Test page (c6 v2; inherits the command-surface gate) | PLANNED | — | n/a | — |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Publisher | `status_publisher.py:TestStatusPublisher.publish(report, charters)` | `infra:e2e-test-status` | runtime, redaction, coverage manifest | Reads the current record, folds this run into it, upserts. Returns True/False; the boolean is advisory and never gates the run. |
| Body builder | `TestStatusPublisher.build_body` | — | coverage manifest | Assembles summary, `last_run_*`, the recent-run ring, the coverage catalog and per-item coverage, then `redact_json` and the 64 KiB check. A payload over the ceiling raises here and is caught by `publish`. |
| State transport | `status_publisher.py:StateTransport` | backend state API | `/api/v1/allai/state/{key}` | GET (404 -> None), PUT when absent (`expected_version` 0), else PATCH at the read version. Sends `X-Internal-API-Key`. 15 s timeout. |
| Coverage manifest | `docs/coverage.json` (+ `docs/coverage.md`) | — | body builder | The catalog is rebuilt from the manifest on every publish; the manifest is the single source of what the 30 items ARE. `_validated_catalog` refuses a manifest that is not exactly 30 MAX/ADDITIONS items. |
| Runtime call site | `runtime.py:78` `publisher_from_config(self.config).publish(report, charters)` | — | publisher | Runs once per harness run, after the report is assembled. Because `publish` is fail-soft, a broken publish leaves the report and tickets untouched. |

Prose: after a harness run assembles its report, the runtime constructs a publisher from config and calls `publish`. If no state URL or credential is configured the publisher is a no-op (dormant). Otherwise it GETs the current record, merges this run's per-charter outcomes onto the existing per-item coverage (a charter's `covers` sets passed/failed, its `covers_partial` sets partial, and failed outranks passed within the same run), trims the recent-run ring to 20, redacts the whole body, enforces the 64 KiB ceiling, and PUT/PATCHes it back under an optimistic version lock. The ops Test page reads the resulting record and renders it; it never writes.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan/Mars | Read and verify the published status | `state_request action=get key=infra:e2e-test-status` | Living State read | COMPLETE |
| Vulcan/Mars | Run a harness charter that then publishes | `shell_request` on Titan-1: `e2e-harness run` under the sanctioned env | Titan-1 shell | COMPLETE |
| Vulcan/Mars | Edit the coverage manifest and map a charter | `shell_request` edit `docs/coverage.json` (+`.md`), then Council review | Titan-1 shell + Council dispatch | COMPLETE |
| MP (Codex) | Build publisher/manifest changes | `council_request mode=build` against a dedicated worktree | Council dispatch | COMPLETE — diff-inspect at file:line; commit messages over-claim |
| DS / GLM | Review publisher/manifest changes | `council_request mode=review` (builder excluded) | Council dispatch | COMPLETE |
| launchd (`com.ai-market.e2e-harness.nightly`) | Nightly run that publishes, at 02:15 local | plist + `scripts/run-nightly.sh` (sources `harness-env.sh`, which activates publishing) | Titan-1 | COMPLETE — the nightly is the routine writer of the record |

## §E. Operate

```yaml operate
- id: E-01
  trigger: Read the current published test status (what the ops Test page is showing)
  pre_conditions:
    - Living State reachable
  tool_or_endpoint: "state_request action=get key=infra:e2e-test-status"
  argument_sourcing:
    key: constant infra:e2e-test-status
  idempotency: IDEMPOTENT
  expected_success:
    shape: 'entity body with last_run_id, last_run_status, recent_runs (<=20), coverage_manifest_version, coverage_catalog (30 items), and coverage (per-item never_run/partial/passed/failed)'
    verification: 'coverage has exactly 30 keys; every item status is one of never_run/partial/passed/failed; last_run_id matches the newest run report on disk'
  expected_failures:
    - signature: entity not found (404 / null)
      cause: the publisher has never successfully written - either never activated or every run so far failed to publish (§F-01)
    - signature: last_run banner shows a failed staging-health run
      cause: the decommissioned staging-health charter is running and 404ing (§F-05)
  next_step_success: read coverage to see what is proven; partial is not proven
  next_step_failure: repair per §G-01 / §G-05
- id: E-02
  trigger: Confirm a harness run actually published (after running a charter)
  pre_conditions:
    - a completed run id
    - the run went through the sanctioned env (scripts/run-nightly.sh or a shell that sourced scripts/harness-env.sh)
  tool_or_endpoint: "state_request action=get key=infra:e2e-test-status; compare last_run_id"
  argument_sourcing:
    run_id: from the run output or the newest report under $E2E_HARNESS_ROOT/reports
  idempotency: IDEMPOTENT
  expected_success:
    shape: 'last_run_id equals the run just executed; that run appears at the head of recent_runs; version incremented by one'
    verification: 'diff the record version before and after; the new run_id is present exactly once at the head of recent_runs'
  expected_failures:
    - signature: last_run_id did not change and a warning was logged
      cause: publishing was dormant (no state URL/credential) or the publish raised and was swallowed fail-soft (§F-01, §F-02)
  next_step_success: none - the record is current
  next_step_failure: check activation (§F-01) then payload/manifest (§F-02, §F-03)
- id: E-03
  trigger: Map a charter onto coverage items (so a run moves an item off never_run)
  pre_conditions:
    - the charter declares covers and/or covers_partial ids that exist in docs/coverage.json
  tool_or_endpoint: "edit docs/coverage.json (+docs/coverage.md), then Council review of the manifest/charter change"
  argument_sourcing:
    item_ids: from the 30-item catalog in docs/coverage.json (M1..M11, A1..A19)
  idempotency: IDEMPOTENT
  expected_success:
    shape: 'the manifest still validates (schema_version 1, exactly 30 MAX/ADDITIONS items, unique ids); a run of the mapped charter sets those items to passed or failed, covers_partial sets partial'
    verification: 'run the charter; the mapped item shows the run_id and passed/failed; an unmapped item stays never_run'
  expected_failures:
    - signature: publish stops writing after the manifest edit
      cause: the manifest no longer validates - not 30 items, a bad group, or a duplicate id (§F-03)
  next_step_success: none - coverage now tracks that journey
  next_step_failure: repair the manifest per §G-03
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `infra:e2e-test-status` is absent, or `last_run_id` never changes, and the harness log says "publishing is disabled: state URL or credential is absent" | The publisher is dormant: `publisher_from_config` built `transport=None` because `E2E_STATE_API_URL` or the internal credential was not present. The run did not go through the sanctioned env | run under `scripts/run-nightly.sh` or a shell that sourced `scripts/harness-env.sh`; re-check the log line | §G-01 | CONFIRMED |
| F-02 | The record exists but this run did not land; the log says "publish failed; run outcome is unchanged" | Publishing raised and was swallowed fail-soft: a transport error, a version conflict, or the payload exceeded 64 KiB | read the warning; GET the record and compare version; check payload size drivers (recent_runs, coverage_catalog) | §G-02 | CONFIRMED |
| F-03 | Publishing stopped writing right after a coverage-manifest edit | `_validated_catalog` refused the manifest: not exactly 30 items, a `group` outside {MAX, ADDITIONS}, a duplicate `id`, or `schema_version` not 1 | `python -c "import json;d=json.load(open('docs/coverage.json'));print(d['schema_version'],len(d['items']))"` — expect `1 30` | §G-03 | CONFIRMED |
| F-04 | An item shows `never_run` even though charters have run against that journey | No charter maps that item (`covers`/`covers_partial`), or every mapped run was a `harness_error` rather than `passed`/`failed` (harness errors do not move coverage) | check the charter's `covers` list against the item id; check the run outcome status | §G-04 | CONFIRMED |
| F-05 | The Test page last-run banner shows a failed run from `c2-staging-health-smoke` / a staging-health proof | The `charters/staging-health.json` charter targets the DECOMMISSIONED staging backend health endpoint and 404s every run, and its failure becomes the newest `recent_runs` entry | GET the record; `recent_runs[0].charter_id` is the staging-health charter with status failed | §G-05 | CONFIRMED |
| F-06 | A value that looks like a secret or a customer identifier appears in the published record | The body was not fully redacted, or a new field was added to `build_body` after `redact_json` runs | GET the record and scan; confirm every new field is added before the `redact_json` call, not after | §G-06 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Publisher
  root_cause: publishing was dormant because the state URL or credential was absent
  repair_entry_point: scripts/harness-env.sh on Titan-1
  change_pattern: run the harness through scripts/run-nightly.sh, or source scripts/harness-env.sh first; that is what sets E2E_STATE_API_URL and fetches the internal credential from Infisical at runtime. NEVER hardcode the state URL or paste the credential into the plist, a dotenv file or a charter - dormant-by-default is a safety property, not a bug
  rollback_procedure: n/a - not sourcing the env leaves the publisher dormant, which is the safe resting state
  integrity_check: re-run a charter; last_run_id advances and the harness log no longer prints the "publishing is disabled" warning
- id: G-02
  symptom_ref: F-02
  component_ref: Body builder
  root_cause: a publish error was swallowed fail-soft (transport, version conflict, or oversized payload)
  repair_entry_point: status_publisher.py
  change_pattern: read the warning to classify. A version conflict is transient - the next run re-reads and re-publishes. An oversized payload (>64 KiB) means the ring or catalog grew; the fix is in build_body's bounding, never raising the ceiling to paper over unbounded growth. Do NOT make publish re-raise - fail-soft is the invariant that keeps a reporting bug from failing a test run
  rollback_procedure: n/a - the run outcome was never affected
  integrity_check: the next run publishes; version advances; payload stays under 64 KiB
- id: G-03
  symptom_ref: F-03
  component_ref: Coverage manifest
  root_cause: the manifest no longer validates (not 30 items, bad group, duplicate id, or wrong schema_version)
  repair_entry_point: docs/coverage.json (and its twin docs/coverage.md)
  change_pattern: restore exactly 30 items, each id unique, group in {MAX, ADDITIONS}, schema_version 1. Changing the 30-item catalog is a coverage-meaning change and takes Council review; keep docs/coverage.md in step in the same commit
  rollback_procedure: revert the manifest commit; publishing resumes with the previous catalog
  integrity_check: the schema check prints `1 30`; a run publishes again and the coverage_catalog has 30 entries
- id: G-04
  symptom_ref: F-04
  component_ref: Publisher
  root_cause: the journey has no charter mapping, or its runs were harness_errors
  repair_entry_point: the charter's covers/covers_partial and the run outcome
  change_pattern: map the item by adding its id to a charter's covers (complete) or covers_partial (partial exercise). Do NOT hand-edit the coverage record to mark an item passed - coverage is only ever moved by a real mapped run, and a checked item must mean a charter actually proved it
  rollback_procedure: remove the mapping; the item returns to never_run on the next publish
  integrity_check: run the mapped charter; the item shows the run_id with passed/failed; partial exercise shows partial, not passed
- id: G-05
  symptom_ref: F-05
  component_ref: Publisher
  root_cause: the decommissioned staging-health charter runs, 404s, and pollutes the last-run banner
  repair_entry_point: e2e-harness charters/staging-health.json and whatever enqueues it
  change_pattern: retire or retarget charters/staging-health.json. Staging is decommissioned, so a health smoke against it can only fail; either delete the charter or point it at a live target. This is a small harness change and takes the normal build/review path; it is cosmetic (the banner), not a data-integrity issue
  rollback_procedure: restore the charter file
  integrity_check: after a run, recent_runs[0] is a real journey, not the staging-health smoke
- id: G-06
  symptom_ref: F-06
  component_ref: Body builder
  root_cause: a field bypassed redaction, or was added after redact_json
  repair_entry_point: status_publisher.py:build_body
  change_pattern: every field in the published body must be assembled BEFORE the single redact_json call and stay within it; never add a post-redaction field. Bounded text helpers exist for run/charter ids - use them. Treat the published record as world-readable
  rollback_procedure: none wanted - redaction is a one-way safety property; restore it if it drifts
  integrity_check: a test seeds a secret-shaped value into a run and asserts it does not appear in the published body
```

## §H. Evolve

### §H.1 Invariants

- **Publishing never changes a run's outcome.** `publish` catches everything and returns a boolean the runtime ignores. A reporting failure must never fail or block a test run.
- **Dormant by default.** With no state URL or credential the publisher is a no-op. Only the sanctioned harness runtime (via `harness-env.sh`) activates it; the credential is fetched at runtime and never at rest on disk.
- **Nothing unredacted is written.** The whole body passes through `redact_json` before it leaves the machine, and every field is assembled before that call. The published record is treated as world-readable.
- **The payload is bounded.** A body over 64 KiB raises rather than writing; the recent-run ring is capped at 20. Growth is bounded in code, not by raising the ceiling.
- **The manifest is exactly 30 MAX/ADDITIONS items.** `_validated_catalog` refuses anything else. The manifest is the single source of what the items are.
- **Checked means proven; partial never counts as proven.** Coverage is only ever moved by a real mapped run. `covers` sets passed/failed, `covers_partial` sets partial, and failed outranks passed within one run. The record is never hand-edited to show green.

### §H.2 BREAKING predicates

BREAKING if ANY of (first match wins):
- Making `publish` able to raise into or block the run path (removing fail-soft).
- Writing any field that has not passed through `redact_json`, or adding a field after redaction.
- Removing the payload ceiling or the recent-run cap, or letting the published body grow unbounded.
- Publishing by default without the state URL/credential activation (removing dormant-by-default), or placing the credential at rest on disk.
- Marking a coverage item proven from anything other than a real mapped charter run, or counting partial as proven.

### §H.3 REVIEW predicates

REVIEW if ANY of (after BREAKING predicates fail):
- Changing the 30-item coverage catalog (ids, groups, or what an item means).
- Adding the charter-level cadence field or any change to how often the record is written.
- Adding the ops Test page console write path (Max-entered goals) - inherits the command-surface gate.
- Changing the redaction rules or the bounded-text limits the publisher relies on.

### §H.4 SAFE predicates

SAFE otherwise:
- Wording of `docs/coverage.md`, comments, and test additions.
- Read-only tooling that GETs and displays the record.
- Selector/label changes on the ops page that do not add a write path (owned by ops-ai-market.md).

### §H.5 Boundary definitions

#### module

`e2e-harness/src/e2e_harness/status_publisher.py` (`TestStatusPublisher`, `StateTransport`, `publisher_from_config`, the `_*` helpers) and the manifest `docs/coverage.json`.

#### public contract

The shape published to `infra:e2e-test-status`: `summary`, `last_run_at`, `last_run_id`, `last_run_status`, `recent_runs` (bounded 20), `coverage_manifest_version`, `coverage_catalog` (30 items), and `coverage` (per-item `status`/`last_run_at`/`last_run_id`). Read-only to all consumers.

#### runtime dependency

The backend state API `/api/v1/allai/state/{key}` reached with the internal API key, and `E2E_STATE_API_URL` plus the internal credential in the harness environment.

#### config default

`E2E_COVERAGE_MANIFEST_PATH` (defaults to `docs/coverage.json`), the state URL and credential env names read in `config.py`, and the module constants `RECENT_RUN_LIMIT=20` and `MAX_PAYLOAD_BYTES=65536`.

### §H.6 Adjudication

The more restrictive classification wins between disagreeing agents. Anything that changes what the published record contains, the coverage catalog, or the meaning of "proven" escalates to Max; the ruling is added to §H.1 as a clarification.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: You want to see, in one place, how much of the product the harness has actually proven. What do you read?
    expected_answers:
      - kind: human_action
        action: 'state_request get on infra:e2e-test-status; read coverage - passed is proven, partial is not, never_run has not been exercised'
    weight: 0.090909091
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: You ran a charter and want to confirm it published. What proves it?
    expected_answers:
      - kind: human_action
        action: the record's last_run_id equals your run and it heads recent_runs, and the version incremented by one
    weight: 0.090909091
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: A journey keeps showing never_run and you want a run to start moving it. What is the correct change?
    expected_answers:
      - kind: human_action
        action: add the item id to a charter's covers (or covers_partial) in docs/coverage.json, keep the manifest at exactly 30 items, and take it through review
    weight: 0.090909091
  - id: I-04
    type: isolate
    refs: [F-01]
    scenario: The record never updates and the log says publishing is disabled. Bug in the publisher?
    expected_answers:
      - kind: human_action
        action: no - publishing is dormant because the state URL/credential was absent; run under the sanctioned env (run-nightly.sh / harness-env.sh), never hardcode the URL or paste the credential
    weight: 0.090909091
  - id: I-05
    type: isolate
    refs: [F-05]
    scenario: The Test page banner shows a failed staging-health run and Max asks why the page looks broken. Assessment?
    expected_answers:
      - kind: human_action
        action: the decommissioned staging-health charter 404s every run and became the newest recent_runs entry; retire or retarget charters/staging-health.json - it is cosmetic, not a data problem
    weight: 0.090909091
  - id: I-06
    type: isolate
    refs: [F-03]
    scenario: Publishing stopped right after someone edited the coverage manifest. First check?
    expected_answers:
      - kind: human_action
        action: validate docs/coverage.json - schema_version 1 and exactly 30 MAX/ADDITIONS items with unique ids; the publisher refuses an invalid manifest
    weight: 0.090909091
  - id: I-07
    type: repair
    refs: [G-02]
    scenario: A publish failed because the payload exceeded 64 KiB. How do you fix it?
    expected_answers:
      - kind: human_action
        action: bound the growth in build_body (the ring is 20, the catalog is 30); never raise the 64 KiB ceiling to hide unbounded growth, and never make publish re-raise
    weight: 0.090909091
  - id: I-08
    type: repair
    refs: [G-04]
    scenario: An item shows never_run but you are sure the journey ran. Someone suggests hand-editing the record to mark it passed. Response?
    expected_answers:
      - kind: human_action
        action: do not hand-edit; map the item to a charter's covers so a real run moves it - a checked item must mean a charter actually proved it
    weight: 0.090909091
  - id: I-09
    type: evolve
    refs: [§H.2]
    scenario: A change makes publish re-raise its errors so failures are visible. Classify.
    expected_answers:
      - kind: classification
        verdict: BREAKING
    weight: 0.090909091
  - id: I-10
    type: evolve
    refs: [§H.3]
    scenario: A change adds a charter-level cadence field so agentic charters publish weekly and recorded replays nightly. Classify.
    expected_answers:
      - kind: classification
        verdict: REVIEW
    weight: 0.090909091
  - id: I-11
    type: ambiguous
    refs: [§H.6, F-02]
    scenario: A publish failed once with a version conflict because a launchd run and a manual run wrote the record at the same instant. Defect to fix, or expected?
    expected_answers:
      - kind: classification
        label: TRANSIENT_EXPECTED_CONTENTION
      - kind: human_action
        action: treat a single optimistic-lock conflict as expected transient contention that self-heals on the next publish; only if it PERSISTS is it a concurrent-writer design issue to escalate under §H.6
    weight: 0.090909091
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1315
last_refresh_commit: ed33a10
last_refresh_date: 2026-07-22T22:10:00Z
owner_agent: mars
refresh_triggers:
  - the charter-level publish cadence field landing (changes how often the record is written)
  - the ops Test page console (Max-entered goals) landing (adds a write path)
  - any change to the coverage manifest's 30-item catalog or what an item means
  - any change to the published record shape, redaction, or the payload/ring bounds
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-07-22T22:10:00Z
first_staleness_detected_at: "2026-07-22T22:09:30.726062+00:00"
```

Refresh log:
- S1315 (2026-07-22): first authoring, against the c6 v1 publisher shipped S1314 (e2e-harness main `ed33a10`) and the live record `run-20260722T194244Z-dd2f4034` (opens honestly 0/30). Discharges the S1314 e2e Test-page / coverage-manifest / status-publisher runbook debt.

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1315 / 2026-07-22T22:10:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
