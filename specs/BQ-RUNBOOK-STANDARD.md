# BQ-RUNBOOK-STANDARD — System-Wide Runbook Standard

**Status:** Gate 1 R3 (design, addressing MP R2 REQUEST_CHANGES HIGH + gate-scope clarification)
**Priority:** P0
**Repo:** aidotmarket/runbooks
**Parent of:** per-system runbook BQs (CRM, Celery, AIM Node, Koskadeux, Infisical, Railway, etc.)
**Authored:** S486 R3 (Vulcan)
**Addresses:** MP R2 task 67a1a915 (REQUEST_CHANGES HIGH — 4 FAIL + 1 partial CONCERN + 5 new risks)

---

## 1. Purpose

Define the system-wide standard every runbook in the ai.market ecosystem must meet so that both human operators and agentic support can:

1. **Operate** — use the system's tools to serve customers (human and agentic)
2. **Isolate** — diagnose issues from symptoms to root causes
3. **Repair** — fix problems with direct references to code
4. **Evolve** — extend the system without violating architectural invariants

A runbook is legible when a stateless agent, given only this runbook and no prior context, can produce a correct first action on any defined operational scenario.

**R3 scope.** This revision addresses MP R2 findings. Core changes: (a) unify the §3/§4 agent-form taxonomy into a single linter-checkable contract (each section has one required schema); (b) scenario scoring weights default to equal, unequal weights require written justification; (c) §H predicate definitions gain concrete boundaries for `module`, `public contract`, `runtime dependency`, `config default`; (d) §J adds `last_refresh_date` + `first_staleness_detected_at` timestamps and defines the WARN→FAIL grace workflow; (e) G4 falsifiability rewritten so Vulcan cannot see the evaluation scenario set; (f) §C/§G entry-point overlap resolved via component-entry vs repair-touchpoint distinction; (g) new §12 Gate Boundaries delineates Gate 1 (design) vs Gate 2 (implementation schemas).

---

## 2. Scope

**In scope:** All system-level runbooks in `aidotmarket/runbooks/`.

**Initial reference implementation:** Infisical runbook (to be authored during Gate 2). Chosen because scope is small, the subsystem is critical, and there is no legacy document to retrofit — this isolates standard-conformance from migration risk.

**Retrofit candidates** (not yet conformant — structural retrofits, not near-misses):
- CRM (`crm-target-state.md` — R5 shipped content; requires structural retrofit)
- Celery (`celery-infrastructure-deployment.md` — requires structural retrofit)

**Greenfield targets** (no runbook yet):
- AIM Node (pip-installable P2P compute; G4 falsifiability test)
- AIM Channel / vectorAIz (dual-brand desktop app)
- allAI (embedded AI agent)
- Koskadeux (session orchestration, Council dispatch, Living State)
- Infisical (secrets) — **initial reference**
- Railway (deploy, database, proxy, Tailscale Funnel)
- GitHub Actions / CI
- Alembic migrations
- Backup pipeline

**Out of scope:** Per-BQ specs (which live in the owning repo's `specs/`), product marketing docs, per-feature READMEs aimed at developer onboarding rather than operation.

---

## 3. Consumer Model

Every runbook serves three consumer classes. **Narrative prose alone is not compliant** — every §C–§K section has a *required agent form* defined in §4; the linter verifies the form is present and well-formed.

**C1 — Human Operator:** support, ops, or engineering doing diagnosis, manual intervention, or onboarding. Assumed to read top-to-bottom when onboarding, then jump via ToC when triaging.

**C2 — Agentic Support:** Claude / MP / AG / XAI / any future agent. Assumed to be stateless — each request starts from zero context; the runbook is the entire working memory for that system during the session.

**C3 — Escalation:** when the primary consumer (human or agent) cannot resolve, where do they hand off? Named human, named Slack channel, or named parent runbook.

**Compliance contract.** A runbook is compliant only if every §C–§K section contains its required agent form (per §4) in a parseable structure. The form is not chosen by the author; it is prescribed by the section. Prose narrative may accompany the required form for human consumers, but the required form is what the linter validates and what agent consumers parse.

Consumer-specific affordances:
- Agentic consumers need exact tool names, argument shapes, expected return shapes, failure signatures — not prose descriptions.
- Human consumers need scannable structure, visual hierarchy, and narrative for novel situations.
- Both need confidence surfaces (§5).

---

## 4. Mandatory Sections

Every runbook under this standard contains §A through §K, in order. Sections can be extended but not omitted or renamed. Each §C–§K section has a *single* required agent form with a prescribed schema. The linter (§K.1) validates schema conformance.

### §A. Header
**Agent form:** header block (prescribed keys)

- `system_name`
- `purpose_sentence` (one sentence)
- `owner_agent` + `escalation_contact`
- `lifecycle_ref` (anchor to §J, which is authoritative for refresh tracking)
- `authoritative_scope` (what this runbook IS the source of truth for)
- `linter_version` (matches §K.0)

Header is a summary display; §J is authoritative. When they diverge, §J wins and the linter flags Header drift.

### §B. Capability Matrix
**Agent form:** table with fixed columns

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |

**Canonical status values:** `SHIPPED`, `PARTIAL`, `PLANNED`, `DEPRECATED`, `BROKEN`.

**`PARTIAL` definition:** shipped but known to have one or more listed defects in §F, OR shipped for a subset of documented use cases. Non-`PARTIAL` cells with known defects are runbook defects.

**`UNVERIFIED` is not a status value.** It is a cell annotation overlay applied when `Last Verified` is empty or older than 90 days. Rendered as e.g., `SHIPPED (UNVERIFIED)`. The linter flags unverified cells.

**Canonical → legacy mapping** (for retrofits):
- `Working` → `SHIPPED`
- `Partial` → `PARTIAL`
- `Broken` → `BROKEN`
- `Planned` → `PLANNED`

Every row must cite a code path (\`file:function\` or module). `SHIPPED` without a backing-code reference is a runbook defect.

### §C. Architecture & Interactions
**Agent form:** architecture table with fixed columns

| Component | Component Entry Point | State Stores | Integrates With | Notes |

- **Component** — logical subsystem name
- **Component Entry Point** — top-level `file:function` (one per component; this is the entry to the component, NOT specific failure-repair touchpoints which live in §G)
- **State Stores** — data models, queue names, cache keys, Living State keys this component reads/writes
- **Integrates With** — other systems this component calls or is called by; reference by endpoint / queue name / file path
- **Notes** — data flow summary, sufficient for an agent to reason about side effects

Prose narrative may accompany the table for human consumers. Diagrams optional (encouraged for human consumers; prose + table must stand alone).

### §D. Agent Capability Map
**Agent form:** capability table with fixed columns

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |

- **Coverage Status** values: `COMPLETE`, `PARTIAL`, `GAP`, `PLANNED`
- **Gap analysis**: table rows with `GAP` or `PARTIAL` status must name what closes the gap in the Notes column (free text)
- Rate limits noted in Notes column when relevant

### §E. Operate — Serving Customers
**Agent form:** operate scenario list with fixed fields per scenario

Each scenario:
- `id` (e.g., `E-01`)
- `trigger` (customer/upstream request)
- `tool_or_endpoint` (exact name and argument shape)
- `expected_success` (return shape, side effects, verification path)
- `expected_failures` (list of signatures; same failure in §F only if cause diagnosis differs)
- `next_step_success`
- `next_step_failure`

§E covers **expected paths**: common operational scenarios and their anticipated failure branches. Deviations outside any §E branch are handled in §F. Covers both human-initiated (support ticket, ops request) and agent-initiated (allAI triage, scheduled job, cross-system call) flows.

### §F. Isolate — Diagnosing Deviations
**Agent form:** symptom index table with fixed columns

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |

- **ID** (e.g., `F-01`) for cross-reference
- **Repair Ref** — anchor to §G entry if known (e.g., `§G-03`) or empty if §F-only
- **Confidence** — `CONFIRMED` / `HYPOTHESIZED` / `DEPRECATED` (per §5)

**Scoping rule:** §F answers "what is wrong and where to look." Symptoms with known repair patterns get `Repair Ref` populated; symptoms with no known repair pattern have empty `Repair Ref`.

Accompanying prose for log locations, trace IDs, and metric dashboards is allowed.

### §G. Repair — Fixing Problems
**Agent form:** repair pattern list with fixed fields per pattern

Each pattern:
- `id` (e.g., `G-01`)
- `symptom_ref` (back-reference to §F entry, e.g., `F-03`) — REQUIRED (repair patterns without a diagnosed symptom belong in the system's README)
- `component_ref` (back-reference to §C component)
- `root_cause`
- `repair_entry_point` (specific `file:function` — typically more granular than §C Component Entry Point)
- `change_pattern` (semantic description, not a diff)
- `rollback_procedure`
- `integrity_check` (how to confirm repair succeeded without regression)

**Scoping rule:** §G answers "how to fix it." Entries must back-reference a §F symptom AND a §C component.

### §H. Evolve — Extending the System
**Agent form:** change-class predicate tree

**Invariants.** Properties that must NOT change without re-architecting (e.g., "non-custodial", "sellers retain ≥ X% of GMV", "all secrets via Infisical"). Per-system invariant list required as a subsection `§H.1 Invariants`.

**Change-class decision tree — executable predicates.** A proposed change is classified by evaluating predicates in order. First match wins.

**BREAKING** if ANY of:
- Changes a *public contract* (definition below) without backwards-compatible shim
- Changes a data-model field type, removes a field, or adds a required field without a default value
- Changes or removes a per-system invariant listed in §H.1
- Changes an authz boundary (requires a new scope, or changes scope semantics for existing callers)

**REVIEW** if ANY of (after BREAKING predicates fail):
- Adds a new feature on an existing public surface
- Refactors across *module* boundaries (definition below): creates a new module, deletes a module, or moves functions across modules
- Changes a *config default* (definition below)
- Adds a new *runtime dependency* (definition below)

**SAFE** otherwise:
- Bugfix within existing semantics
- Documentation update
- Test addition
- Internal refactor within a single module preserving all public signatures

**Boundary definitions (uniform across all runbooks under this standard):**

- **`module`** — an immediate subdirectory of the system's source root (i.e., top-level package directory). Example (ai-market-backend): `app/api/`, `app/models/`, `app/services/`, `app/allai/` are modules; `app/` itself is the source root (not a module); `tests/`, `migrations/`, `scripts/` are not modules (they are peer trees, not part of the product). Per-system deviations (e.g., a monorepo with multiple source roots) are declared in §H.1 Invariants.
- **`public contract`** — anything in any of: (a) a module's `__init__.py` exports, (b) an OpenAPI / JSON-schema / protobuf artifact served by the system, (c) an MCP tool signature registered by the system, (d) a CLI flag published in the system's `--help`. Internal helpers are not public contract even if other modules import them.
- **`runtime dependency`** — an entry in `requirements.txt` or `pyproject.toml [project.dependencies]`. Dev/test/optional extras (`[project.optional-dependencies.*]`, `requirements-dev.txt`, etc.) are NOT runtime dependencies. Per-system deviations for non-Python runtimes (npm, go.mod, Cargo.toml) declared in §H.1.
- **`config default`** — a value shipping in the system's canonical config file (declared in §C State Stores). Environment-variable overrides, feature flags, and test-only overrides are not config defaults.

**Adjudication.** If two agents classify the same change differently, the more restrictive classification wins. Disputes unresolvable under the predicates escalate to Max for ruling; the ruling is added as a per-system clarification to §H.1.

### §I. Acceptance Criteria (for the runbook itself)
**Agent form:** scenario set declaration

**Scenario set (minimum 10 per-system).**

Required distribution:
- At least 3 §E Operate scenarios
- At least 3 §F Isolate scenarios
- At least 2 §G Repair scenarios
- At least 2 §H Evolve scenarios (propose a change, classify it per §H predicates)
- At least 1 **ambiguous-symptom** scenario (multiple plausible first actions with a defined correct set)

**Correct-first-action definition.** The stateless agent must produce one of:
- The first tool call / endpoint invocation (matched by tool-name AND argument-key-set; argument-value correctness scored separately per rubric), OR
- The first instruction to a human operator (matched by action verb + object + target; e.g., "run Alembic upgrade against production database" matches regardless of exact wording), OR
- A classification verdict (for §H Evolve scenarios: SAFE / REVIEW / BREAKING).

**Scoring rubric** (per scenario):
- **Correct (1.0):** produces one of the answers in the scenario's expected-answer key
- **Partial (0.5):** correct intent and correct target but incorrect detail (e.g., right tool, missing one argument; right human-action verb + object but wrong target subsystem)
- **Incorrect (0.0):** off-path or harmful

**Weighting.** Each scenario carries a weight; **default is equal-weight (1/N where N = scenario count)**. Authors may declare unequal weights in §I subsection `§I.1 Weight Justification` with one sentence per scenario explaining why it carries more or less weight (e.g., production-risk scenarios may justify higher weight). Linter enforces sum of weights = 1.0 (±0.001 tolerance). Unjustified unequal weights are a FAIL.

**Pass threshold:** weighted score ≥ 0.80 across the full scenario set.

**Adjudication.** The scenario's expected-answer key may list multiple acceptable answers; any listed answer scores 1.0. MP + AG must concur on the expected-answer key when scenarios are authored (for each scenario, both sign off before it enters the harness set). Disputes escalate to Max.

**Harness.** Stateless MP dispatch with `allowed_tools=[Read,Grep,Glob,LS]` restricted to this runbook file. Harness script in `aidotmarket/runbooks/harness/` (§K.2). Full scenario-YAML grammar and harness execution semantics are Gate 2 deliverables (see §12); this section specifies what the harness must achieve, not its implementation details.

### §J. Lifecycle
**Agent form:** lifecycle metadata block

Authoritative refresh tracking. §A Header is a display summary; §J is the source of truth.

**Required fields:**
- `last_refresh_session` — session ID of last refresh
- `last_refresh_commit` — commit SHA at last refresh
- `last_refresh_date` — ISO timestamp of last refresh
- `owner_agent` — agent responsible for refresh cycles
- `refresh_triggers` — list (BQ completion, gate approval, incident, scheduled cadence)
- `scheduled_cadence` — e.g., `90 days` (optional; must be set if not event-driven)
- `last_harness_pass_rate` — most recent §I harness score
- `last_harness_date` — ISO timestamp of last harness run
- `first_staleness_detected_at` — ISO timestamp; initialized `null`; set by linter when STALE transitions `true`; cleared by linter on refresh

**Staleness detection (STALE true if ANY of):**
- `last_refresh_commit != current HEAD of system's primary repo` AND `now - last_refresh_date > 60 days`
- `now - last_harness_date > 90 days`
- Any §B row has `UNVERIFIED` overlay

**Non-compliance workflow:**
1. On STALE transition `false → true`: linter sets `first_staleness_detected_at = now` and emits `WARN` (not PR-blocking).
2. If `now - first_staleness_detected_at > 30 days`: linter emits `FAIL` (PR-blocking).
3. On refresh (author updates `last_refresh_*` fields to current values): linter clears `first_staleness_detected_at = null` and resumes normal state.

Other linter `FAIL` triggers (always PR-blocking, no grace period):
- Any §A–§K section missing
- Any §C–§K section missing its required agent form
- Internal contradictions (Header/Lifecycle mismatch, §F Repair Ref pointing to nonexistent §G entry, §G symptom_ref pointing to nonexistent §F entry)

### §K. Conformance
**Agent form:** conformance statement block

**Required fields:**
- `linter_version` — version of `runbook-lint` validated against
- `last_lint_run` — session + date
- `last_lint_result` — `PASS` | `WARN` | `FAIL` with diff summary if WARN/FAIL
- `trace_matrix_path` — if this runbook is a retrofit, path to the trace matrix document
- `word_count_delta` — if retrofit, before/after word count and percentage change

**§K.0 — Linter version compatibility.** Each runbook declares the linter version it was validated against. The linter reads its own version from `runbook-lint --version` and compares against §K.0; mismatch is a `WARN` (not blocking) until the runbook re-validates.

**§K.1 — `runbook-lint`** (CI job in `aidotmarket/runbooks` repo):
- Verifies all §A–§K sections present and in order
- Verifies every §C–§K section contains the section's required agent form in a parseable structure (schema per §4)
- Verifies §B status cells use only canonical values and cite backing code
- Verifies §J metadata fields populated; computes STALE status; manages `first_staleness_detected_at` transitions
- Verifies Header (§A) fields match §J authoritative values
- Verifies §F ↔ §G bidirectional cross-references are consistent (every §F Repair Ref resolves to a real §G id; every §G symptom_ref resolves to a real §F id)
- Verifies §I weights sum to 1.0 (±0.001) and unequal weights have §I.1 justification
- PR-blocking on FAIL; emits WARN for linter-version drift

**§K.2 — Stateless-agent harness** (`aidotmarket/runbooks/harness/`):
- Reads scenario YAML from `harness/scenarios/<system>.yaml`
- Dispatches MP with `allowed_tools=[Read,Grep,Glob,LS]` restricted to the target runbook file
- Scores each response against expected-answer key per §I rubric
- Writes result to `harness/results/<system>-<session>.json`
- Nightly scheduled via GitHub Actions
- YAML grammar + scoring implementation = Gate 2 deliverable (see §12)

**§K.3 — Template validator** (for new-runbook scaffolding):
- `runbook-new <system-name>` generates a §A–§K skeleton with placeholders
- Scaffold passes `runbook-lint` structurally (content placeholders emit WARN until filled)
- Placeholder tokens and WARN-vs-FAIL derivation = Gate 2 deliverable (see §12)

---

## 5. Confidence Surface

§B capability-matrix status cells carry `Last Verified` session ID + backing-code reference. Missing either triggers the `UNVERIFIED` overlay (see §4 §B).

Every §F symptom and §G repair procedure carries a confidence tag:
- `CONFIRMED` — observed in production, repair verified
- `HYPOTHESIZED` — plausible from code review, unverified in production
- `DEPRECATED` — documented for historical completeness, no longer applicable

---

## 6. Runbook Index

**Gate 2 deliverable.** `aidotmarket/runbooks/README.md` does not exist as of R3; creating it is a §9 Gate 2 line item.

When created, the index lists:
- All runbooks under this standard
- Status (up-to-standard / migrating / not-yet-adopted)
- Last refresh session + commit SHA
- Owner agent
- Last harness pass rate

The index itself conforms to a micro-version of this standard (§A header + table of runbooks + §J lifecycle entry).

---

## 7. Acceptance Criteria for this BQ

**G1 — Gate 1 (spec) AC:** MP review verdict `APPROVE` or `APPROVE_WITH_NITS`. AG cross-vote concurs on consumer-first framing. Both sign off that §4 mandatory sections cover operate/isolate/repair/evolve with agent-executable detail at design resolution (schema shape named; implementation grammar deferred to Gate 2 per §12).

**G2 — Gate 2 (implementation spec) AC:**
- `runbook-lint` CI job authored with full YAML/schema grammar for each §C–§K required form, landing in `aidotmarket/runbooks` repo; PR-blocking on FAIL
- Stateless-agent harness (`harness/`) authored with scenario YAML grammar, scorer, adjudication rule, nightly CI scheduling
- Template validator (`runbook-new`) authored with placeholder token set and WARN/FAIL derivation
- Runbook index `README.md` authored under this standard, listing existing + planned runbooks
- **Infisical runbook** authored from scratch under this standard (initial reference implementation)
- Migration plan documents retrofit sequence for CRM and Celery with owner assignment and trace-matrix requirement

**G3 — Gate 3 (code audit) AC:**
- Infisical runbook passes `runbook-lint` and passes harness at ≥ 0.80 weighted first-action accuracy on a ≥10-scenario set with required distribution per §4 §I
- `runbook-lint` passes on itself (the linter's own code comments documenting each check)

**G4 — Gate 4 (production / falsifiability) AC.** The standard is ratified only if a second runbook authored against the *frozen* standard passes an *externally-authored hidden* evaluation set:

1. **Standard freeze.** When this BQ reaches Gate 1 APPROVED, the spec commit SHA is pinned. No edits to the spec during G4 testing; any change reopens Gate 1.
2. **Vulcan authors AIM Node runbook** using only the frozen standard as input. Vulcan may reference per-system code and incident evidence for AIM Node, but may NOT reference the Infisical runbook content or the Infisical scenario set.
3. **Hidden evaluation set.** After Vulcan submits the AIM Node draft, **MP + AG jointly author** a ≥10-scenario evaluation set (distribution per §4 §I) from AIM Node code + incident evidence. Vulcan does not see the evaluation set until after first-pass MP R1 verdict.
4. **Pass criteria.** First-pass MP R1 verdict is `APPROVE` or `APPROVE_WITH_NITS` AND the runbook scores ≥ 0.80 weighted on the hidden evaluation set. Failure on either leg fails G4.
5. **Why this is falsifiable.** Vulcan cannot overfit scenarios (never sees the eval set). Vulcan cannot import Infisical patterns directly (explicit constraint). If the standard is good, a frontier-quality agent can author a conformant runbook once; if not, we learn that here rather than after shipping the standard.

---

## 8. Open Questions

**R1 + R2 questions (all resolved in R3 or earlier):** Q1–Q9 resolved in R2 change log. See Appendix A.

**R2-surfaced new risks (resolved in R3):**
- **§3/§4 agent-form taxonomy inconsistency** — resolved by removing §3's three-form enum; §4 section-specific forms are the single contract (§3, §4).
- **§I weighting ambiguity** — resolved by equal-weight default + §I.1 justification requirement + linter sum-to-1.0 check (§4 §I).
- **§J field-name bug (`last_refresh`)** — resolved by introducing `last_refresh_date` as a required field (§4 §J).
- **§J grace-period unspecified** — resolved by `first_staleness_detected_at` + explicit WARN→FAIL workflow (§4 §J).
- **§C/§G entry-point overlap** — resolved by component-entry (§C) vs repair-entry (§G) distinction (§4 §C, §4 §G).
- **G4 gaming** — resolved by standard-freeze + hidden eval set authored by MP + AG (§7 G4).

**Open for R4 (if MP R3 surfaces more):** TBD.

---

## 9. Migration Plan (Gate 2 preview)

**Gate 2 deliverable order:**

1. **`runbook-lint`** — linter + template validator in `aidotmarket/runbooks` repo, PR-blocking. §K.1 + §K.3.
2. **Stateless-agent harness scaffold** — `aidotmarket/runbooks/harness/` with MP dispatch invocation, scoring script, scenario-YAML grammar. §K.2.
3. **Runbook index** — `aidotmarket/runbooks/README.md` listing adoption targets + statuses.
4. **Initial reference — Infisical runbook** — authored from scratch by Vulcan using only this standard. Validated by `runbook-lint` + harness ≥ 0.80.
5. **G4 falsifiability — AIM Node runbook** — authored by Vulcan against **frozen standard**, no Infisical reference, evaluated on MP + AG hidden scenario set. See §7 G4.
6. **Retrofit Phase — CRM** — `crm-target-state.md` restructured to §A–§K. Required artifacts: trace matrix, word-count delta, MP orphan review.
7. **Retrofit Phase — Celery** — same procedure as CRM.
8. **Remaining systems** — Koskadeux, AIM Channel, allAI, Railway, GitHub Actions, Alembic, Backup pipeline. Each a child BQ with its own Gate 1–4 cycle.

**Retrofit preservation contract** (applies to steps 6–8):
- **Trace matrix** — table with columns `Legacy Section | New §A–§K | Notes`. Every legacy section maps to a new section OR is explicitly marked `REMOVED` with rationale.
- **Word-count delta** — before/after word count per section. Warn threshold ±15%; explicit justification required if exceeded.
- **MP orphan review** — content in legacy not represented in retrofit is preserved or explicitly removed with rationale; silent drops are FAIL.
- **Harness score** — must match or exceed legacy harness score (if one existed). For CRM/Celery, harness must pass at ≥ 0.80.

---

## 10. Non-goals

- This BQ does not dictate per-system content — it dictates structure, consumer model, and acceptance criteria.
- This BQ does not retire the existing Gate 1 APPROVED status of `BQ-CRM-RUNBOOK-STANDARD`; it reclassifies the CRM runbook as a retrofit candidate. The existing child BQ's content work remains valid and feeds into the Phase 6 retrofit.
- This BQ does not specify Gate 2 build order beyond the §9 migration plan preview.

---

## 11. Review Targets

**MP R3 (primary review, read-only).** Verify R2 STILL_OPEN items closed:
- F2 (consumer model mechanical implementability): §3 now defers to §4; §4 prescribes one required form per section with a defined schema. Verify the linter contract is unambiguous.
- F3 (AC harness-readiness at design level): §I defines correct-first-action matching rules, 3-tier rubric, equal-weight default + justification requirement, adjudication (MP + AG concur on expected-answer key). Full YAML grammar explicitly deferred to Gate 2 per §12.
- F5 (change classes executable): §H now defines `module`, `public contract`, `runtime dependency`, `config default`. Verify these are unambiguous enough to resolve the dev-only-dependency and monorepo-package-move examples MP raised.
- F6 (enforcement near-buildable at design level): §K.1–§K.3 specify what each mechanism does; implementation grammars deferred per §12. Verify design resolution is sufficient.
- C3 (lifecycle): §J adds `last_refresh_date` and `first_staleness_detected_at`; grace workflow defined. Field-name bug resolved. Verify.

Also verify R2 NEW risks closed: §3/§4 taxonomy unification, §I weighting rule, §J field-name fix + grace timestamps, §C/§G entry-point distinction, G4 gaming fix.

**AG cross-vote (after MP R3 passes).** Consumer-first framing. Does §3 + §4 section-form contract actually produce runbooks readable by stateless agents? Is §E scenario-list form complete for agent-initiated flows? Is §5 confidence surface adequate? Is G4 falsifiability actually falsifiable (MP + AG authoring hidden scenarios requires both agents be willing and able; is this process viable)?

---

## 12. Gate Boundaries (Gate 1 vs Gate 2)

MP R2 raised several asks that are appropriate at Gate 2 (implementation) rather than Gate 1 (design). This section draws the line explicitly so future reviews do not scope-creep Gate 1.

**Gate 1 (this BQ) delivers a design:**
- The schema *shape* for each §C–§K required agent form (named columns / named fields / named predicates)
- The *intent* each form serves (what question the consumer is trying to answer)
- The *contract* the linter must enforce at the design level (section presence, form presence, cross-reference consistency, staleness transition rules)
- The *falsifiability* test (G4 hidden-scenario evaluation on frozen standard)

**Gate 2 delivers implementation:**
- Exact YAML / markdown-table / code-block grammars the linter parses (including escape rules, optional vs required attributes, type constraints)
- Scenario-YAML grammar (how authors write a scenario, how the harness loads it, how the scorer normalizes arguments)
- Linter placeholder-token set for scaffolds (what tokens emit WARN vs FAIL)
- Harness execution semantics (retry policy, timeout, how tool-name and argument-key-set matching is implemented)
- `runbook-lint` version-to-standard-version compatibility matrix

**Why this line matters.** Collapsing Gate 2 into Gate 1 would (a) pay implementation tax before the design is ratified, risking rework; (b) blur the Gate 1 exit criterion, letting "not fully implementable" veto a coherent design; (c) set a precedent that distorts future BQs. Gate 1 approves when the design resolves ambiguity at design resolution and clearly enumerates what Gate 2 must produce. Gate 2 approves when those implementation artifacts exist and pass their own review.

---

## Appendix A: R2 → R3 Change Log

| R2 STILL_OPEN / NEW RISK | R3 fix | Location |
|---|---|---|
| F2 consumer model mechanical | §3 defers to §4; single required form per section; linter contract unambiguous at design level | §3, §4 |
| F3 AC harness-ready | Correct-first-action matching rules, equal-weight default + justification, adjudication; full YAML grammar → Gate 2 per §12 | §4 §I, §12 |
| F5 change classes executable | `module`, `public contract`, `runtime dependency`, `config default` defined | §4 §H |
| F6 enforcement buildable | §K.1–§K.3 specify what each mechanism does; implementation grammars → Gate 2 per §12 | §4 §K, §12 |
| C3 PARTIAL lifecycle | `last_refresh_date` + `first_staleness_detected_at` added; grace workflow defined | §4 §J |
| NEW HIGH §3/§4 taxonomy | Unified — §4 is the single contract | §3, §4 |
| NEW HIGH §I weighting | Equal-weight default + §I.1 justification + linter sum check | §4 §I |
| NEW HIGH §J field-name bug | `last_refresh_date` added; staleness uses it | §4 §J |
| NEW HIGH §J grace ambiguous | `first_staleness_detected_at` + explicit WARN→FAIL workflow | §4 §J |
| NEW MEDIUM §C/§G overlap | Component-entry vs repair-entry distinction | §4 §C, §4 §G |
| G4 gaming CONFIRMED | Standard-freeze + hidden eval set authored by MP + AG | §7 G4 |
