---
runbook_id: runbooks
domain: runbooks
status: ACTIVE
owner: mars
system_name: runbooks
purpose_sentence: How the runbook corpus actually works today - where a page has to live to be findable, how to write one, how to update one without breaking the pins, and how to check a claim against ground truth - written so no session has to rediscover it.
owner_agent: mars
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: |
  The runbook corpus itself: the catalog, the router, the corpus manifest,
  the linter, the scaffolder, and the four operator verbs (find, write,
  update, check). This page describes the system AS IT IS on the date in last_verified_at,
  not as the approved truth-layer design intends it to become. Where the two differ this
  page says so and names the design. Council gate procedure is gate-procedure.md. Build
  dispatch is agent-dispatch.md.
authoritative_for:
  - topic: runbook-corpus
    section: §C. Architecture & Interactions
  - topic: runbook-discovery
    section: §E. Operate
  - topic: runbook-authoring
    section: §E. Operate
  - topic: runbook-verification
    section: §E. Operate
aliases:
  - runbook-runbook
  - how-to-write-a-runbook
  - runbook-standard
error_signatures:
  - signature: catalog regeneration failed
    section: §F. Isolate
  - signature: does not match current bytes
    section: §F. Isolate
  - signature: grandfathered source records, but current source corpus has
    section: §F. Isolate
  - signature: catalog validation failed
    section: §F. Isolate
  - signature: dangling section
    section: §F. Isolate
  - signature: search limit must be an integer from 1 to 3
    section: §F. Isolate
  - signature: catalog outputs are stale
    section: §G. Repair
last_verified_at: "2026-08-09"
superseded_by: []
supersedes: []
linter_version: 1.0.0
---

# Runbooks

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

This page exists because sessions kept rediscovering the same facts about our own
documentation and arriving surprised at where things stood. Max, S1491: "I feel like you are
forgetting things we learned in the last 10 sessions and keep coming back surprised at where
we are. I want to stop that by having a runbook for the runbooks that is accurate now."

**Read §B and §F first.** §B is what works and what does not. §F is the list of things that
have surprised us before, each with the error string that announces it.

**This page describes today, not the plan.** S1574 shipped default catalog admission for every
operational source page plus the manifest-classified recoverable archives. It derives the
first H1 and top-level section headings for discovery rows. Semantic verification and the
wider approved truth-layer design remain separate work.

## §B. Capability Matrix

Figures measured 2026-08-18 on `build/runbook-catalog-admits-all-corpus-s1574`. Recompute rather than quote:
`python3 -m runbook_tools.corpus_manifest`.

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Machine search reaches the complete immutable corpus | SHIPPED | `runbook_tools/catalog/search.py` | 110 operational records: 26 ACTIVE, 80 current discovery-only, 4 archived | 2026-08-18 |
| Machine catalog coverage | SHIPPED | `CATALOG.json` | Every path from `source_paths()` plus all manifest-classified recoverable archives | 2026-08-18 |
| Retrieval quality, human router | SHIPPED | `TOPIC-ROUTER.md` | ACTIVE authority tables plus separate current-discovery and archive tables | 2026-08-18 |
| Authority separation | SHIPPED | `CATALOG.json` | ACTIVE rows retain their prior flags; discovery rows inherit explicit fail-closed non-authority defaults | 2026-08-18 |
| Search result cap | SHIPPED | `runbook_tools/catalog/search.py` | Refuses limit above 3 | 2026-08-18 |
| Scaffolding a new page | SHIPPED | `runbook_tools/cli.py` | `tests/test_creation_flow.py` | 2026-08-09 |
| Linting a page, as advice rather than a gate | SHIPPED | `runbook_tools/lint/conformance.py` | `tests/test_checks.py`; CI runs it with continue-on-error | 2026-08-09 |
| CI lint on `main` | BROKEN | `.github/workflows/runbook-lint.yml` | Red since 2026-08-03; six failures, one root cause, repaired on the fix branch | 2026-08-09 |
| Admitting a new page for discovery | SHIPPED | `runbook_tools/catalog/generator.py` | Admission is the default; every entry retains fail-closed non-authority flags | 2026-08-18 |
| Checking a page's claims against ground truth automatically | PLANNED | `specs/RUNBOOK-TRUTH-LAYER-S1487.md` | AC12 to AC17 of the approved design, unbuilt | 2026-08-09 |

Recompute the coverage figures rather than quoting them: `python3 -m runbook_tools.corpus_manifest`.
The retrieval figures come from the frozen AC8 question set at
`/Users/max/koskadeux-state/s1491-ac8/retrieval-set-v1.json`, measured by
`measure_baseline.py` beside it.

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| The corpus | `aidotmarket/runbooks` working tree | git | everything | 106 source documents plus four recoverable archives; every one is cataloged. |
| `CATALOG.json` | `runbook-catalog generate` | git | search, router, README, boot pin | **Generated. Never hand-edit.** Contains 26 full ACTIVE authority rows and compact discovery rows for the rest of the estate. |
| `TOPIC-ROUTER.md` | `runbook-catalog generate` | git | humans | **Generated. Never hand-edit.** Lists ACTIVE authority keys, current discovery-only pages, and archived historical pages separately. |
| `CORPUS-MANIFEST.yaml` | `python3 -m runbook_tools.corpus_manifest --refresh-from <sha>` | git | CI lint | An inventory and adjudication ledger, NOT an authority. It pins a git blob OID per document, so editing any tracked page leaves the pin stale until refreshed. Since S1525 a stale pin is ADVISORY: the checker prints it and exits 0, and no check fails. Refresh when convenient, never because CI demands it. |
| Linter | `runbook-lint --mode strict` | none | CI | Checks structural conformance against the A-K template. Advice only since S1491: a failure never stops a page being indexed and never fails CI. |
| Scaffolder | `runbook-new <slug>` | none | authoring | Writes `templates/runbook.template.md` with placeholders. |
| The standard | `specs/BQ-RUNBOOK-STANDARD.md` | git | authors | 789 lines, Gate 1 approved at S486. Roughly half is marked "historical provenance" and superseded. It is a spec, so it is not indexed and search cannot reach it. |
| Legacy gate page | `runbook-first-gates.md` | git | nothing | At the repository root, therefore unroutable. Its own header says LEGACY COMPATIBILITY - DO NOT EXTEND. It documents the enforcement gates, not authoring. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan / Mars | Find a page | `grep -rn` first, `runbook-catalog search` second | operator | COMPLETE |
| Vulcan / Mars | Write, update, lint, regenerate | `runbook-new`, `runbook-lint`, `runbook-catalog generate` | operator | COMPLETE |
| Vulcan / Mars | Change declared ACTIVE metadata | edit valid frontmatter, review, regenerate | operator | COMPLETE — semantic and action-authority flags remain false |
| MP (Codex) | Author or repair pages under an approved dispatch | minimal bridge | builder | COMPLETE |
| Council (CC/Kimi/GLM) | Gate review of design and spec changes to the corpus machinery | council dispatch | reviewer | COMPLETE |
| Any agent | Check a page's claims against ground truth | none | n/a | GAP — closed by AC12 to AC17 of the approved truth-layer design, which is unbuilt |

## §E. Operate

```yaml operate
- id: E-01
  trigger: You need to find whether we already know something - an error string, a procedure, a system
  pre_conditions:
    - The runbooks clone is present at the path in config:resource-registry
  tool_or_endpoint: grep -rn "<exact string>" /Users/max/Projects/ai-market/runbooks --include='*.md'
  argument_sourcing:
    arg: The literal error string or system name, not a paraphrase
  idempotency: IDEMPOTENT
  expected_success:
    shape: "File paths and line numbers"
    verification: "Open the hit and read the surrounding section"
  expected_failures:
    - signature: no output
      cause: "Genuinely absent, or the string is paraphrased. Retry with a shorter distinctive fragment before concluding it is absent."
  next_step_success: Read the page
  next_step_failure: Say plainly that nothing was found and carry on. Grep is not a guarantee; measured on four real error strings in S1484 it found two.

- id: E-02
  trigger: You want the indexed, ranked answer rather than every textual hit
  pre_conditions:
    - CATALOG.json validates at the commit you are searching
  tool_or_endpoint: runbook-catalog search --query "<question>"
  argument_sourcing:
    arg: A question in words that appear on the page
  idempotency: IDEMPOTENT
  expected_success:
    shape: "At most three results with paths and sections"
    verification: "Confirm the returned page actually answers the question and observe whether it is ACTIVE, discovery-only, or archived"
  expected_failures:
    - signature: catalog validation failed
      cause: "See F-04. On main today this fires for every query."
    - signature: search limit must be an integer from 1 to 3
      cause: "The surface refuses more than three results. Precision@5 is therefore capped at 0.2 by the surface itself."
  next_step_success: Read the page
  next_step_failure: Fall back to E-01 and report the validation failure; both surfaces cover the same operational corpus when healthy.

- id: E-03
  trigger: You need to write a new runbook
  pre_conditions:
    - The subject is a system we operate, not a one-off incident
  tool_or_endpoint: runbook-new <slug>
  argument_sourcing:
    arg: A slug matching the runbook_id you intend
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: "A scaffolded page with A-K sections and placeholder frontmatter"
    verification: "runbook-lint --mode strict passes on the finished page"
  expected_failures:
    - signature: page not indexed after writing it
      cause: "See F-02. Generated outputs are stale, source discovery rejected the path, or the page failed an integrity exception."
  next_step_success: Fill every section from evidence and regenerate; generated entries remain integrity-only
  next_step_failure: See F-02

- id: E-04
  trigger: You need to update an existing page
  pre_conditions:
    - You have the evidence for the change, not a recollection of it
  tool_or_endpoint: edit the file, then python3 -m runbook_tools.corpus_manifest --refresh-from $(git rev-parse HEAD)
  argument_sourcing:
    arg: The commit SHA the refresh pins against
  idempotency: IDEMPOTENT
  expected_success:
    shape: "refreshed-and-validated with the corpus counts"
    verification: "python3 -m runbook_tools.corpus_manifest with no arguments passes"
  expected_failures:
    - signature: does not match current bytes
      cause: "Refresh only: it refuses to pin a dirty working tree. Commit the page first, then refresh. The plain checker treats the same drift as advisory (S1525). See F-03."
  next_step_success: Regenerate per G-01, update last_verified_at and §J
  next_step_failure: See F-03

- id: E-05
  trigger: You need to know whether what a page says is still true
  pre_conditions:
    - none
  tool_or_endpoint: manual - read the page and check each claim against the system it describes
  argument_sourcing:
    arg: n/a
  idempotency: IDEMPOTENT
  expected_success:
    shape: "Each §B row confirmed or corrected against its Backing Code column"
    verification: "Update last_verified_at only for what you actually checked"
  expected_failures:
    - signature: none - there is no tooling to fail
      cause: "Automated ground-truth checking does not exist. It is AC12-AC17 of the approved design and is unbuilt."
  next_step_success: Commit the corrections
  next_step_failure: n/a
```

## §F. Isolate

These are the things that have surprised sessions before. Each row is a real failure we have hit.

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `WARNING: catalog regeneration failed; commit continues with advisory generated-index drift.` | The local pre-commit hook could not run the generator or stage its two index outputs. The commit still proceeds by design. | Run `python3 -m runbook_tools.catalog generate`, then inspect the error if tidy indexes are wanted | G-01 | CONFIRMED |
| F-02 | A page you wrote does not appear in the catalog or router | Generated outputs are stale; source discovery rejected a symlink/unreadable path; or an integrity exception refused the page | Compare `source_paths()` paths with all `CATALOG.json` entry paths, then run `python3 -m runbook_tools.catalog check` | G-01 | CONFIRMED |
| F-03 | `ADVISORY (not a failure): documents[N].git_blob_oid ... does not match current bytes for '<path>'` | A tracked page was edited after the last manifest pin. Expected and harmless since S1525; the checker exits 0 and CI stays green. Nothing to repair unless you want a tidy ledger. | `python3 -m runbook_tools.corpus_manifest` | G-02 | CONFIRMED |
| F-04 | `catalog validation failed:` followed by a long list, and every search returns nothing | The committed catalog is malformed or internally inconsistent with its pinned source snapshot. Search validates the catalog before returning anything, so an invalid catalog means zero results rather than degraded results. | `runbook-catalog validate --catalog-ref "git:aidotmarket/runbooks@$(git rev-parse HEAD):CATALOG.json"` | G-01 | CONFIRMED |
| F-05 | `manifest has N grandfathered source records, but current source corpus has N+1` | A page was added or removed without refreshing the inventory | `python3 -m runbook_tools.corpus_manifest` | G-02 | CONFIRMED |
| F-06 | `<path>: dangling section '§X.N'` | Frontmatter or a cross-reference names a section heading that does not exist in the page body | `grep -n "^#" <path>` and compare against the declared sections | G-03 | CONFIRMED |
| F-07 | A discovery-only or archived page is treated as sanctioned procedure | A consumer ignored `catalog_state` and the fail-closed discovery defaults | Check `catalog_state`, `authority_admission`, and `action_authority_eligible`; archived pages also carry `status: archived` | G-04 | CONFIRMED |
| F-08 | Hand-curated error signatures do not match the errors you actually hit | Signatures are declared by hand in frontmatter. The index scored 0 of 8 on error strings taken from pages it already held (S1487). Indexing more hand-curated pages does not fix this; deriving signals from page bodies does, and that is unbuilt. | Try E-01 with the literal string | G-04 | CONFIRMED |
| F-09 | A command line tool disagrees with the same check run as a module, e.g. `runbook-catalog validate` says `schema_version must be 1` while `python3 -m runbook_tools.catalog validate` passes | A stale global install of the console scripts shadows the working tree. CI installs the tree with `pip install -e '.[dev]'` and is unaffected, so this appears as a local-only phantom failure. | `which runbook-catalog` against `python3 -c "import runbook_tools;print(runbook_tools.__file__)"` | G-05 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Generated catalog
  root_cause: Generated outputs are stale, or generation reported a source integrity error.
  repair_entry_point: python3 -m runbook_tools.catalog generate
  change_pattern: >
    Regenerate from the current source tree. The local hook does this automatically when
    generator inputs are staged, but failure remains advisory and never blocks the commit.
  rollback_procedure: git revert the content or authority change and regenerate.
  integrity_check: python3 -m runbook_tools.catalog check && runbook-catalog validate --catalog-ref "git:aidotmarket/runbooks@$(git rev-parse HEAD):CATALOG.json"

- id: G-02
  symptom_ref: F-03
  component_ref: "`CORPUS-MANIFEST.yaml`"
  root_cause: The manifest pins a git blob OID per document and any edit leaves that pin stale. Since S1525 this is advisory and blocks nothing, so this repair is optional tidying, not a fix.
  repair_entry_point: python3 -m runbook_tools.corpus_manifest --refresh-from <full-sha>
  change_pattern: Refresh from the current HEAD, then re-run the checker with no arguments to confirm a clean advisory list. Never open a bookkeeping commit solely to satisfy a check; the check no longer asks.
  rollback_procedure: git checkout CORPUS-MANIFEST.yaml
  integrity_check: python3 -m runbook_tools.corpus_manifest

- id: G-03
  symptom_ref: F-06
  component_ref: The corpus
  root_cause: A declared section reference does not resolve to a heading in the body.
  repair_entry_point: the page's frontmatter or the cross-reference
  change_pattern: Correct the section token to an existing heading, or add the heading. Section tokens use the section sign and must match exactly.
  rollback_procedure: git checkout the page
  integrity_check: runbook-lint --mode strict --format github

- id: G-04
  symptom_ref: F-07
  component_ref: The corpus
  root_cause: A consumer confused discoverability with authority, or ranking missed the relevant page.
  repair_entry_point: catalog state inspection plus grep over the working tree
  change_pattern: >
    Inspect the catalog state before using any result. Search with the literal string if ranking
    missed it. Do not promote or execute discovery-only guidance merely because it was found.
  rollback_procedure: none - the repair is a read followed by an additive frontmatter edit.
  integrity_check: grep -rn "<string>" /Users/max/Projects/ai-market/runbooks --include='*.md'

- id: G-05
  symptom_ref: F-09
  component_ref: Linter
  root_cause: A globally installed copy of the console scripts shadows the checked-out working tree.
  repair_entry_point: python3 -m runbook_tools.<module>
  change_pattern: >
    Prefer the module form over the console script for every check, or reinstall the working
    tree with pip install -e '.[dev]'. Never diagnose a catalog or lint failure from the
    console script alone without confirming which copy answered.
  rollback_procedure: none - the repair is a change of invocation.
  integrity_check: python3 -c "import runbook_tools;print(runbook_tools.__file__)"
```

## §H. Evolve

### §H.1 Invariants

- `CATALOG.json`, `TOPIC-ROUTER.md` and the generated block in `README.md` are outputs. Regenerate them; never hand-edit them.
- `CORPUS-MANIFEST.yaml` is an inventory, never an authority. A page does not become true by being listed in it, and a stale pin never fails a check (S1525). The one exception is the refresh itself, which still refuses to pin a dirty working tree, and delivery at a pinned SHA, which still verifies every blob against that commit.
- Every path returned by `source_paths()` is indexed. Recoverable archives are added from the manifest and separated visibly.
- Discovery is not authority. Only declared ACTIVE rows contribute aliases, topics, error signatures, or resolver keys.
- The A-K shape is a convention. Since S1491 a conformance failure is advice to the author; it never stops a page being indexed and never fails CI. If you find yourself inventing content to satisfy a check, stop: the check is wrong, not the page.
- Recompute corpus figures. Do not quote them from a handoff, including this page: every figure here carries the date it was measured and the command that measures it.

### §H.2 BREAKING predicates

- Changing the catalog schema version or generated envelope, because pinned consumers validate both exactly.
- Changing what counts as an indexable location, because it changes the corpus in one step.
- Re-attaching template conformance, or any other shape test, to admission. It was removed on 2026-08-09 by Max directive S1491 and must not come back as a gate.
- Re-attaching pin freshness to any check that can fail. Removed on 2026-08-11 by Max directive at S1525, on the same principle: editing a page must never require a bookkeeping commit.

### §H.3 REVIEW predicates

- Adding or removing a topic in `authoritative_for`, because topics are how the router routes.
- Changing the search result cap or the ranking inputs.
- Retiring a page, which must move it to `archive/` rather than leave a second contradictory answer at the root.

### §H.4 SAFE predicates

- Correcting prose in a page you own, then refreshing the pin and regenerating.
- Adding an error signature that you have personally seen.
- Updating `last_verified_at` and §J for claims you actually rechecked.

### §H.5 Boundary definitions

#### module

A single `.md` page plus its frontmatter.

#### public contract

`CATALOG.json` and the topics declared in `authoritative_for`. Other pages and tools resolve against these.

#### runtime dependency

The local clone path in `config:resource-registry`, and git.

#### config default

The admitted source tree, archive classifications in `CORPUS-MANIFEST.yaml`, and schemas read by the catalog generator.

### §H.6 Adjudication

Where this page and the approved truth-layer design disagree, this page describes what is
true today and the design describes what is intended. Neither overrides the other. When the
design ships, this page is rewritten in the same change or it becomes the ninth thing a
session has to rediscover.

## §I. Operational Examples

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01, F-07]
    scenario: |
      id: E-01. trigger: An unfamiliar error string appears and the operator must find out whether we already know about it before diagnosing it. pre_conditions: the runbooks clone is present at the path in config:resource-registry. tool_or_endpoint: grep -rn over the working tree with --include='*.md'. argument_sourcing: the literal error string, not a paraphrase. idempotency: IDEMPOTENT. expected_success: file paths and line numbers, or no output. expected_failures: no output because the string was paraphrased rather than copied. next_step_success: read the surrounding section. next_step_failure: retry with a shorter distinctive fragment, then say plainly that nothing was found and carry on.
    expected_answers:
      - kind: human_action
        verb: grep
        object: the literal error string
        target: /Users/max/Projects/ai-market/runbooks
    weight: 0.09090909090909091
  - id: I-02
    type: operate
    refs: [E-02, F-04]
    scenario: |
      id: E-02. trigger: An operator needs ranked guidance from the complete corpus. pre_conditions: a valid pinned catalog and manifest. tool_or_endpoint: runbook-catalog search. argument_sourcing: a question phrased in words that appear on the target page. idempotency: IDEMPOTENT. expected_success: at most three results labeled ACTIVE, discovery-only, or archived. expected_failures: catalog validation failed, emitted before any result is produced. next_step_success: read the page without confusing discovery with authority. next_step_failure: fall back to grep and report the validation failure.
    expected_answers:
      - kind: classification
        label: catalog invalid, not a ranking problem
    weight: 0.09090909090909091
  - id: I-03
    type: operate
    refs: [E-03, F-02]
    scenario: |
      id: E-03. trigger: A new runbook must be written for a system we operate. pre_conditions: the subject is a system, not a one-off incident. tool_or_endpoint: runbook-new with the intended slug. argument_sourcing: a slug matching the intended identity. idempotency: NOT_IDEMPOTENT. expected_success: a scaffolded page that is discoverable immediately after regeneration. expected_failures: source discovery or an integrity exception rejects it. next_step_success: fill each section from evidence and regenerate; generated entries remain integrity-only. next_step_failure: see F-02.
    expected_answers:
      - kind: human_action
        verb: scaffold
        object: a new page under runbooks/
        target: runbook-new
    weight: 0.09090909090909091
  - id: I-04
    type: isolate
    refs: [F-01, G-01]
    scenario: |
      A staged runbook edit makes the pre-commit hook print "catalog regeneration failed". Classify this as advisory index drift: the hook exits zero and the commit continues. Run the generator directly only if the operator wants the underlying error and tidy indexes now.
    expected_answers:
      - kind: classification
        label: advisory generation failure, not a commit gate
    weight: 0.09090909090909091
  - id: I-05
    type: isolate
    refs: [F-03, G-02]
    scenario: |
      The checker prints "documents[N].git_blob_oid ... does not match current bytes for '<path>'" after an indexed page was edited. The operator must classify this before assuming the page is malformed. CORPUS-MANIFEST.yaml pins one git blob OID per document, so any edit to a tracked page leaves that pin stale until the inventory is refreshed. Since S1525 the line is prefixed ADVISORY, the checker exits 0 and CI stays green: there is nothing to fix. Verification: run the corpus manifest checker with no arguments and read which document it names.
    expected_answers:
      - kind: classification
        label: stale manifest pin, not a malformed page
    weight: 0.09090909090909091
  - id: I-06
    type: isolate
    refs: [F-05, G-02]
    scenario: |
      The corpus manifest checker reports "manifest has N grandfathered source records, but current source corpus has N+1". A page was added or removed without refreshing the inventory. This is an accounting drift in a ledger, not an authority failure: the manifest is an inventory and never decides what is true. Verification: run the checker and compare its counts against the actual file tree.
    expected_answers:
      - kind: classification
        label: inventory drift, ledger not authority
    weight: 0.09090909090909091
  - id: I-07
    type: repair
    refs: [G-01, F-01]
    scenario: |
      A directed page must become discoverable. Add it anywhere admitted by source_paths and regenerate; no frontmatter opt-in or anchor move is required. Catalog validation still checks the generated snapshot's schema, sections, links, and digests.
    expected_answers:
      - kind: human_action
        verb: regenerate
        object: the complete catalog and router
        target: python3 -m runbook_tools.catalog generate
    weight: 0.09090909090909091
  - id: I-08
    type: repair
    refs: [G-02, F-03]
    scenario: |
      An indexed page was edited and the manifest pin is stale. Refresh the inventory from the current HEAD, then re-run the checker with no arguments and confirm it passes before regenerating the catalog. Rollback is a checkout of the manifest file.
    expected_answers:
      - kind: human_action
        verb: refresh
        object: the corpus manifest pin
        target: python3 -m runbook_tools.corpus_manifest --refresh-from HEAD
    weight: 0.09090909090909091
  - id: I-09
    type: evolve
    refs: [§H.3, §C]
    scenario: |
      A page is to declare a new topic in authoritative_for. Topics are the public contract other pages and tools resolve against, and the router routes on them, so this is a REVIEW change rather than a safe one. Check the topic is not already claimed by another page, add it, regenerate, and confirm the router row points where you intended.
    expected_answers:
      - kind: classification
        label: REVIEW - changes the public contract
    weight: 0.09090909090909091
  - id: I-10
    type: evolve
    refs: [§H.3, §H.6]
    scenario: |
      A page is superseded and must be retired. Move it to archive/ in the same change that publishes its replacement. Leaving it at the repository root produces a second contradictory answer that search cannot reach and cannot rank, which is how runbook-first-gates.md came to sit at the root declaring itself legacy in its own header.
    expected_answers:
      - kind: classification
        label: REVIEW - retire by moving to archive, never by abandoning in place
    weight: 0.09090909090909091
  - id: I-11
    type: ambiguous
    refs: [§H.6, §B]
    scenario: |
      This page and specs/RUNBOOK-TRUTH-LAYER-S1487.md describe different systems: the page describes the corpus as it is, the spec describes what an approved but unbuilt design intends. An operator reading both must decide which governs the action in front of them. Neither overrides the other. For anything you are doing today, this page governs, because the design has shipped nothing. For anything you are designing or specifying, the design governs. If you cannot tell which case you are in, you are probably about to build something, and the design governs.
    expected_answers:
      - kind: classification
        label: today's action follows this page, design work follows the spec
    weight: 0.09090909090909091
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1574
last_refresh_commit: pending
last_refresh_date: 2026-08-18T23:29:18Z
owner_agent: mars
refresh_triggers:
  - Any chunk of the truth-layer build lands; §B and §C change materially with each one
  - Catalog schema, source-admission rules, or generated-output behavior changes; update F-01 and G-01
  - The AC8 retrieval set is re-run; replace the §B recall and precision figures with the new measurement
  - CI runbook-lint changes state on main
  - Automated ground-truth checking ships; E-05 stops being manual
scheduled_cadence: 30d
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1491 / 2026-08-09T15:40:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
