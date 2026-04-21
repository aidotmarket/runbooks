# BQ-RUNBOOK-STANDARD — System-Wide Runbook Standard

**Status:** Gate 1 R2 (design, addressing MP R1 REQUEST_CHANGES HIGH)
**Priority:** P0
**Repo:** aidotmarket/runbooks
**Parent of:** per-system runbook BQs (CRM, Celery, AIM Node, Koskadeux, Infisical, Railway, etc.)
**Authored:** S486 R2 (Vulcan)
**Addresses:** MP R1 task 37a67038 (REQUEST_CHANGES HIGH — 6 FAIL / 7 CONCERN / 3 NIT)

---

## 1. Purpose

Define the system-wide standard every runbook in the ai.market ecosystem must meet so that both human operators and agentic support can:

1. **Operate** — use the system's tools to serve customers (human and agentic)
2. **Isolate** — diagnose issues from symptoms to root causes
3. **Repair** — fix problems with direct references to code
4. **Evolve** — extend the system without violating architectural invariants

A runbook is legible when a stateless agent, given only this runbook and no prior context, can produce a correct first action on any defined operational scenario.

**R2 scope:** This revision addresses MP R1 findings. Core changes: (a) CRM demoted from "reference implementation" to retrofit candidate; Infisical runbook becomes the initial reference (built from scratch). (b) Narrative prose alone is no longer compliant — every §C–§H section with prose must include a machine-consumable structure. (c) AC `>=80%` upgraded to harness-ready with scenario diversity floors and scoring rubric. (d) Migration plan replaces "reviewer diligence" with mandatory trace matrix + word-count delta. (e) §H change classes become executable predicates. (f) New §K Conformance defines CI linter, nightly harness, template validator.

---

## 2. Scope

**In scope:** All system-level runbooks in `aidotmarket/runbooks/`.

**Initial reference implementation:** Infisical runbook (to be authored during Gate 2). Chosen because scope is small, the subsystem is critical, and there is no legacy document to retrofit — this isolates standard-conformance from migration risk.

**Retrofit candidates** (not yet conformant — structural retrofits, not near-misses):
- CRM (`crm-target-state.md` — R5 shipped content; requires structural retrofit)
- Celery (`celery-infrastructure-deployment.md` — requires structural retrofit)

**Greenfield targets** (no runbook yet):
- AIM Node (pip-installable P2P compute; G4 falsifiability test candidate)
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

Every runbook serves three consumer classes. **Narrative prose alone is not compliant** — every §C–§H section with prose must be accompanied by at least one machine-consumable structure (see §4).

**C1 — Human Operator:** support, ops, or engineering doing diagnosis, manual intervention, or onboarding. Assumed to read top-to-bottom when onboarding, then jump via ToC when triaging.

**C2 — Agentic Support:** Claude / MP / AG / XAI / any future agent. Assumed to be stateless — each request starts from zero context; the runbook is the entire working memory for that system during the session.

**C3 — Escalation:** when the primary consumer (human or agent) cannot resolve, where do they hand off? Named human, named Slack channel, or named parent runbook.

**Compliance contract:** A runbook is compliant only if every §C–§H section that uses narrative prose also includes at least one of:
- **Decision table:** columns `Trigger | Action | Verify`
- **Enumerated scenario list:** items `symptom: X → first action: Y → verify: Z`
- **Mermaid flowchart** rendering the same decision structure in text-parseable form

The section's subheader declares which form is present: `(Agent form: decision table)`, `(Agent form: enumerated scenarios)`, or `(Agent form: mermaid flowchart)`. The linter verifies presence (§K).

Consumer-specific affordances:
- Agentic consumers need exact tool names, argument shapes, expected return shapes, failure signatures — not prose descriptions.
- Human consumers need scannable structure, visual hierarchy, and narrative for novel situations.
- Both need confidence surfaces (§5).

---

## 4. Mandatory Sections

Every runbook under this standard contains §A through §K, in order. Sections can be extended but not omitted or renamed.

### §A. Header
- System name
- One-sentence purpose
- Owner agent(s) + escalation contact
- Link to §J Lifecycle (which is authoritative for refresh tracking)
- Authoritative scope (what this runbook IS the source of truth for)
- Linter version validated against (§K)

Header is a summary display; §J is authoritative. When they diverge, §J wins and the linter flags Header drift.

### §B. Capability Matrix
Table with columns:

\`\`\`
| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
\`\`\`

**Canonical status values:** \`SHIPPED\`, \`PARTIAL\`, \`PLANNED\`, \`DEPRECATED\`, \`BROKEN\`.

**\`PARTIAL\` definition:** shipped but known to have one or more listed defects in §F, OR shipped for a subset of documented use cases. Non-\`PARTIAL\` cells with known defects are runbook defects.

**\`UNVERIFIED\` is not a status value.** It is a cell annotation overlay applied when \`Last Verified\` is empty or older than 90 days. Rendered as e.g., \`SHIPPED (UNVERIFIED)\`. The linter flags unverified cells.

**Canonical → legacy mapping** (for retrofits):
- \`Working\` → \`SHIPPED\`
- \`Partial\` → \`PARTIAL\`
- \`Broken\` → \`BROKEN\`
- \`Planned\` → \`PLANNED\`

Every row must cite a code path (\`file:function\` or module). \`SHIPPED\` without a backing-code reference is a runbook defect.

### §C. Architecture & Interactions
**(Agent form: decision table, enumerated scenarios, or mermaid flowchart — declare which in subheader)**

- Component overview (services, storage, external dependencies)
- **Code entry points:** top-level \`file:function\` for each component (required; agents need exact entry points for §G repair)
- **Ownership boundaries:** which components this runbook owns vs. consumes from other runbooks
- **State-store schemas:** data models, queue schemas, cache keys, Living State keys
- **Integration surface:** which other systems this one reads from / writes to, with interface references (endpoints, queue names, file paths)
- Data flow: textual description of primary request paths, sufficient for an agent to reason about side effects
- Diagrams optional (encouraged for human consumers; prose must stand alone)

### §D. Agent Capability Map
**(Agent form: table required)**

- Which agents can perform which operations on this system (table: agent × operation)
- Skill/tool-to-feature mapping
- Gap analysis: where agent coverage is incomplete and what would close it
- Auth/authz surface for agentic callers (tokens, scopes, rate limits)

### §E. Operate — Serving Customers
**(Agent form: enumerated scenarios required)**

§E covers **expected paths**: common operational scenarios and their anticipated failure branches. Deviations outside any §E branch are handled in §F.

For each scenario:
- **Trigger** — what the customer or upstream system is asking
- **Tool or endpoint to use** — with exact argument shape
- **Expected success signal** — return shape, side effects, where to verify
- **Expected failure modes** — with signatures (same failure in §F only if cause diagnosis differs)
- **Next step** on success / on failure

Covers both human-initiated (support ticket, ops request) and agent-initiated (allAI triage, scheduled job, cross-system call) flows.

### §F. Isolate — Diagnosing Deviations
**(Agent form: symptom index table required)**

§F answers "**what is wrong and where to look**". Scope: deviations outside §E's anticipated failure branches.

- Symptom index: \`symptom → probable causes → verification procedure\`
- Log locations, trace IDs, metric dashboards
- Known failure modes with exact error signatures (log-line patterns, HTTP status codes, exception types)

**Scoping rule:** A symptom with no known repair pattern is §F-only. Symptoms with known repair patterns get a forward-reference \`→ see §G.<id>\`.

### §G. Repair — Fixing Problems
**(Agent form: enumerated repair patterns required)**

§G answers "**how to fix it**". Scope: patterns that correspond to §F symptoms.

For each known failure mode in §F:
- Root cause
- File path + function-level entry point
- Specific change pattern (semantic description, not a diff)
- Rollback procedure
- Data integrity check to confirm repair

**Scoping rule:** Every §G entry must back-reference a §F symptom (\`← see §F.<id>\`). Repair patterns without a diagnosed symptom belong in the system's README, not this runbook.

### §H. Evolve — Extending the System
**(Agent form: change-class decision tree — predicates, not prose)**

**Invariants:** properties that must NOT change without re-architecting (e.g., "non-custodial", "sellers retain ≥ X% of GMV", "all secrets via Infisical"). Per-system invariant list required.

**Change-class decision tree — executable predicates.** A proposed change is classified by evaluating predicates in order. First match wins.

**BREAKING** if ANY of:
- Changes a public contract (endpoint signature, tool signature, event schema) without backwards-compat shim
- Changes a data-model field type, removes a field, or adds a required field without default
- Changes or removes a per-system invariant
- Changes authz boundary (requires new scope or changes scope semantics)

**REVIEW** if ANY of (after BREAKING predicates fail):
- Adds a new feature on an existing public surface
- Refactors across module boundaries (new module, deleted module, or moved functions across modules)
- Changes a config default value
- Adds a new runtime dependency

**SAFE** otherwise:
- Bugfix within existing semantics
- Documentation update
- Test addition
- Internal refactor within a single module preserving signatures

**Adjudication:** If two agents classify the same change differently, the more restrictive classification wins.

### §I. Acceptance Criteria (for the runbook itself)
**(Agent form: scenario set declaration required)**

**Scenario set (minimum 10 per-system).**

Required distribution:
- At least 3 §E Operate scenarios
- At least 3 §F Isolate scenarios
- At least 2 §G Repair scenarios
- At least 2 §H Evolve scenarios (propose a change, classify it)
- At least 1 **ambiguous-symptom** scenario (multiple plausible first actions with a defined correct set)

**Correct-first-action definition:**

The stateless agent must produce one of:
- The first tool call / endpoint invocation (by name and argument shape) that a correct resolution path requires, OR
- The first instruction to a human operator (by exact text intent) that a correct resolution path requires, OR
- A classification verdict (for §H Evolve scenarios: SAFE / REVIEW / BREAKING matching adjudication).

**Scoring rubric:**
- **Correct (1.0):** exact first action per the scenario's expected-answer key, correct intent and correct target
- **Partial (0.5):** correct intent, wrong target (e.g., correct tool name but wrong argument shape; correct diagnosis target but wrong log file)
- **Incorrect (0.0):** off-path or harmful

**Adjudication:** When multiple first actions are acceptable, the scenario's expected-answer key lists them all; any listed answer scores 1.0. MP + AG must concur on the expected-answer key when scenarios are authored. Disputes escalate to Max.

**Pass threshold:** weighted score ≥ 80% across the full scenario set.

**Harness:** stateless MP dispatch with \`allowed_tools=[Read,Grep,Glob,LS]\` restricted to this runbook file. Harness script in \`aidotmarket/runbooks/harness/\` (§K).

### §J. Lifecycle
**(Agent form: metadata table required)**

Authoritative refresh tracking. §A Header is a display summary; §J is the source of truth.

**Required fields:**
- \`last_refresh_session\`: session ID of last refresh
- \`last_refresh_commit\`: commit SHA at last refresh
- \`owner_agent\`: agent responsible for refresh cycles
- \`refresh_triggers\`: list (BQ completion, gate approval, incident, scheduled cadence)
- \`scheduled_cadence\`: e.g., \`90 days\` (optional; must set if not event-driven)
- \`last_harness_pass_rate\`: most recent §I harness score
- \`last_harness_date\`: when the harness was last run

**Staleness detection.** A runbook is \`STALE\` if any of:
- \`last_refresh_commit != current HEAD of system's primary repo\` AND \`last_refresh > 60 days\`
- \`last_harness_date > 90 days\`
- Any §B capability-matrix cell has an \`UNVERIFIED\` overlay

**Non-compliance** (blocks PR merge via linter):
- Any §A–§K section missing
- Any §C–§H section missing its declared agent form
- \`STALE\` status for more than 30 days after detection

### §K. Conformance
**(Agent form: compliance statement required)**

**Required fields:**
- \`linter_version\`: version of \`runbook-lint\` validated against
- \`last_lint_run\`: session + date
- \`last_lint_result\`: \`PASS\` | \`WARN\` | \`FAIL\` with diff summary if WARN/FAIL
- \`trace_matrix_path\`: if this runbook is a retrofit, path to the trace matrix document
- \`word_count_delta\`: if retrofit, before/after word count and percentage change

**§K.1 — \`runbook-lint\`** (CI job in \`aidotmarket/runbooks\` repo):
- Verifies all §A–§K sections present and in order
- Verifies every §C–§H section declares an agent form in its subheader and contains at least one matching structure
- Verifies §B status cells use only canonical values and cite backing code
- Verifies §J metadata fields populated; computes \`STALE\` status
- Verifies Header (§A) fields match §J authoritative values
- PR-blocking on FAIL

**§K.2 — Stateless-agent harness** (\`aidotmarket/runbooks/harness/\`):
- Reads scenario YAML from \`harness/scenarios/<system>.yaml\`
- Dispatches MP with \`allowed_tools=[Read,Grep,Glob,LS]\` restricted to the target runbook file
- Scores each response against expected-answer key per §I rubric
- Writes result to \`harness/results/<system>-<session>.json\`
- Nightly scheduled via GitHub Actions

**§K.3 — Template validator** (for new-runbook scaffolding):
- \`runbook-new <system-name>\` generates a §A–§K skeleton with placeholders
- Scaffold passes \`runbook-lint\` structurally (content placeholders are allowed but flagged as \`WARN\`)

---

## 5. Confidence Surface

§B capability-matrix status cells carry \`Last Verified\` session ID + backing-code reference. Missing either triggers the \`UNVERIFIED\` overlay (see §4 §B).

Every §F symptom and §G repair procedure carries a confidence tag:
- \`CONFIRMED\` — observed in production, repair verified
- \`HYPOTHESIZED\` — plausible from code review, unverified in production
- \`DEPRECATED\` — documented for historical completeness, no longer applicable

---

## 6. Runbook Index

**Gate 2 deliverable.** \`aidotmarket/runbooks/README.md\` does not exist as of R2; creating it is a §9 Gate 2 line item.

When created, the index lists:
- All runbooks under this standard
- Status (up-to-standard / migrating / not-yet-adopted)
- Last refresh session + commit SHA
- Owner agent
- Last harness pass rate

The index itself conforms to a micro-version of this standard (§A header + table of runbooks + §J lifecycle entry).

---

## 7. Acceptance Criteria for this BQ

**G1 — Gate 1 (spec) AC:** MP R1/R2/Rn review verdict \`APPROVE\` or \`APPROVE_WITH_NITS\`. AG cross-vote concurs on consumer-first framing. Both sign off that §4 mandatory sections cover operate/isolate/repair/evolve with agent-executable detail.

**G2 — Gate 2 (implementation spec) AC:**
- Runbook index \`README.md\` authored under this standard, listing existing + planned runbooks
- **Infisical runbook** authored from scratch under this standard (initial reference implementation)
- \`runbook-lint\` CI job landing in \`aidotmarket/runbooks\` repo; PR-blocking on FAIL
- Migration plan documents retrofit sequence for CRM and Celery with owner assignment and trace-matrix requirement

**G3 — Gate 3 (code audit) AC:**
- Stateless-agent harness implemented in \`aidotmarket/runbooks/harness/\`
- Infisical runbook passes harness at ≥80% first-action accuracy on a ≥10-scenario set (with required distribution per §4 §I)
- \`runbook-lint\` passes on Infisical runbook

**G4 — Gate 4 (production / falsifiability) AC:** A second runbook (recommend **AIM Node**) is authored by Vulcan using only this standard as input, and passes MP R1 on first submission, and passes the harness at ≥80%. This is the falsifiability test: the standard is real only if a new runbook built against it gets ratified on first pass.

---

## 8. Open Questions

**R1 questions (now resolved in R2):**

**Q1 RESOLVED** (§I automated vs manual harness): Automated. G3 depends on harness existing; §K.2 specifies \`aidotmarket/runbooks/harness/\`.

**Q2 RESOLVED** (§H universal vs per-system change tree): Universal shell with executable predicates (§4 §H). Per-system content lists invariants and examples under each class.

**Q3 RESOLVED** (§C diagrams): Prose mandatory, agent-consumable structure mandatory, visual diagrams optional.

**Q4 RESOLVED** (§B PARTIAL semantics): Defined in §4 §B as "shipped but known to have one or more listed defects in §F, OR shipped for a subset of documented use cases."

**Q5 RESOLVED** (§E/§F separation): §E = expected paths including anticipated failure branches. §F = deviations outside §E. Scoping rules added in §4 §E and §4 §F.

**Q6 RESOLVED** (CRM retrofit risk): Demoted. CRM is now a retrofit candidate, not the reference. Infisical is the initial reference. Trace matrix + word-count delta is the preservation mechanism (§9).

**New questions surfaced by MP R1 (now resolved in R2):**

**Q7 RESOLVED** (mechanical enforcement): CI linter \`runbook-lint\` in \`aidotmarket/runbooks\` repo, PR-blocking on FAIL. Nightly harness runner. Template validator for new-runbook scaffolding. §K.1–§K.3 specify.

**Q8 RESOLVED** (agent-consumable restatement shape): Decision table OR enumerated scenarios OR mermaid flowchart. Section subheader declares form. Linter verifies presence. §3 compliance contract + §4 section-by-section forms.

**Q9 RESOLVED** (retrofit preservation proof): Mandatory trace matrix (legacy section → §A–§K mapping or \`REMOVED + rationale\`). Word-count delta warn threshold ±15%. MP reviews matrix for orphan content. §9 specifies.

**Open for R3 (if MP R2 surfaces more):** TBD.

---

## 9. Migration Plan (Gate 2 preview)

**Gate 2 deliverable order:**

1. **Runbook lint + template validator (\`runbook-lint\`)**: CI job in \`aidotmarket/runbooks\` repo, blocking on PRs. §K.1 + §K.3.
2. **Stateless-agent harness scaffold**: \`aidotmarket/runbooks/harness/\` with MP dispatch invocation, scoring script, scenario-YAML format. §K.2.
3. **Runbook index**: \`aidotmarket/runbooks/README.md\` listing adoption targets + statuses.
4. **Initial reference — Infisical runbook**: authored from scratch by Vulcan using only this standard. Validated by \`runbook-lint\` + harness ≥80%.
5. **G4 falsifiability — AIM Node runbook**: authored by Vulcan using only this standard + lessons from Infisical authoring. Must pass MP R1 on first submission.
6. **Retrofit Phase — CRM**: \`crm-target-state.md\` restructured to §A–§K. **Required artifacts:** trace matrix (legacy section → §A–§K or \`REMOVED + rationale\`), word-count delta, MP review for orphan content.
7. **Retrofit Phase — Celery**: same procedure as CRM.
8. **Remaining systems**: Koskadeux, AIM Channel, allAI, Railway, GitHub Actions, Alembic, Backup pipeline. Each a child BQ with its own Gate 1–4 cycle.

**Retrofit preservation contract** (applies to steps 6–8):
- **Trace matrix:** table with columns \`Legacy Section | New §A–§K | Notes\`. Every legacy section maps to a new section OR is explicitly marked \`REMOVED\` with rationale.
- **Word-count delta:** before/after word count per section. Warn threshold ±15%; explicit justification required if exceeded.
- **MP reviews trace matrix** for orphan content. Content in legacy not represented in the retrofit is either preserved or explicitly removed with rationale; silent drops are FAIL.
- **Harness score** must match or exceed legacy harness score (if one existed). For CRM/Celery (no legacy harness), harness must pass at ≥80%.

---

## 10. Non-goals

- This BQ does not dictate per-system content — it dictates structure, consumer model, and acceptance criteria.
- This BQ does not retire the existing Gate 1 APPROVED status of \`BQ-CRM-RUNBOOK-STANDARD\`; it reclassifies the CRM runbook as a retrofit candidate. The existing child BQ's content work remains valid and feeds into the Phase 6 retrofit.
- This BQ does not specify Gate 2 build order beyond the §9 migration plan preview.

---

## 11. Review Targets

**MP R2 (primary review, read-only).** Verify R1 FAILs closed:
- F1 (CRM over-claim): §2 and §9 now position CRM as retrofit candidate; Infisical is reference. Verify §2 scoping and §9 sequence.
- F2 (consumer model ambiguity): §3 and §4 now require agent-consumable structure; prose-only is non-compliant. Verify §K enforcement is concrete enough to implement.
- F3 (AC not harness-ready): §4 §I now has scenario distribution floor, scoring rubric, adjudication rule, harness specification. Verify testability.
- F4 (migration preservation): §9 now requires trace matrix + word-count delta; §K records artifacts. Verify preservation contract is auditable.
- F5 (change classes not executable): §4 §H now uses predicate-based first-match classification. Verify predicates are unambiguous.
- F6 (no enforcement): §K Conformance section + CI linter + harness + template validator. Verify §K.1–§K.3 specifications are concrete enough to implement in Gate 2.

Also verify R1 CONCERNs closed: README forward-reference (§6 now Gate 2 deliverable), isolate/repair boundary (§F/§G scoping rules with cross-refs), lifecycle enforceability (§J staleness detection + non-compliance blocks), G3 scenario mismatch (std minimum bumped to 10), Celery retrofit effort (§2 acknowledges structural retrofit).

R1 NITs: status value mapping (§4 §B table), UNVERIFIED annotation (§4 §B), Header vs Lifecycle authority (§4 §A, §4 §J).

**AG cross-vote (after MP R2 passes):** consumer-first framing. Does §3 consumer model + §4 agent-form requirement actually produce runbooks readable by stateless agents? Is §E scenario structure complete for agent-initiated flows? Is §5 confidence surface adequate? Is the G4 falsifiability AC (AIM Node) a genuine test, or can Vulcan game it by over-specifying AIM Node scenarios?

**Out of review scope for R2:** Gate 2 linter implementation details, per-system invariant catalogs, scenario-set authoring for Infisical/AIM Node, migration execution details.

---

## Appendix A: R1 → R2 Change Log

| R1 FAIL | R2 fix | Location |
|---|---|---|
| CRM over-claim | Demoted to retrofit candidate; Infisical is initial reference | §2, §7, §9 |
| Consumer model ambiguous | Agent-consumable structure required per §C–§H | §3, §4 |
| AC not harness-ready | Scenario distribution + scoring rubric + adjudication | §4 §I |
| Migration preservation weak | Trace matrix + word-count delta | §9 |
| Change classes not executable | Predicate-based classification | §4 §H |
| No enforcement | §K Conformance + \`runbook-lint\` CI | §4 §K, §K.1–§K.3 |

| R1 CONCERN | R2 fix | Location |
|---|---|---|
| README.md forward reference | Moved to Gate 2 deliverable | §6 |
| Isolate/Repair boundary | Scoping rules + cross-refs | §4 §F, §4 §G |
| Lifecycle decorative | Staleness detection + non-compliance | §4 §J |
| G3 scenario mismatch | Standard min bumped to 10 | §4 §I |
| Trace matrix missing | Added as mandatory | §9 |
| Celery retrofit effort | Acknowledged as structural retrofit | §2 |
| Missing R2 questions | Q7, Q8, Q9 resolved | §8 |

| R1 NIT | R2 fix | Location |
|---|---|---|
| Status value mapping | Canonical → legacy table | §4 §B |
| UNVERIFIED ambiguity | Clarified as annotation overlay | §4 §B |
| Header vs Lifecycle duplication | Lifecycle is authoritative | §4 §A, §4 §J |
