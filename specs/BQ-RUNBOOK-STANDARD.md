# BQ-RUNBOOK-STANDARD — System-Wide Runbook Standard

**Status:** Gate 1 R8 (design, addressing AG cross-vote CONDITIONAL — §E agent autonomy + §9 retrofit + 2 elevated nits)
**Priority:** P0
**Repo:** aidotmarket/runbooks
**Parent of:** per-system runbook BQs (CRM, Celery, AIM Node, Koskadeux, Infisical, Railway, etc.)
**Authored:** S486 R8 (Vulcan)
**Addresses:** MP R7 task fe003f94 (APPROVE_WITH_NITS LOW — all structural items closed) + AG cross-vote task dfe3090b (CONDITIONAL — 3 REQUEST_CHANGES, 1 CONCERN, 3 CONCUR incl G4 falsifiability 'genuine and robust')

---

## 1. Purpose

Define the system-wide standard every runbook in the ai.market ecosystem must meet so that both human operators and agentic support can:

1. **Operate** — use the system's tools to serve customers (human and agentic)
2. **Isolate** — diagnose issues from symptoms to root causes
3. **Repair** — fix problems with direct references to code
4. **Evolve** — extend the system without violating architectural invariants

A runbook is legible when a stateless agent, given only this runbook and no prior context, can produce a correct first action on any defined operational scenario.

**R3 scope (retained).** Unified §3/§4 agent-form taxonomy, §I equal-weight default, §H boundary definitions, §J timestamps + grace workflow, G4 hidden-scenario protocol, §C/§G entry-point distinction, §12 Gate Boundaries.

**R4 scope (retained).** §J grace-clear tightened, G4 reviewer-independence partial split, §K.1 severity classification, `linter_version` drift closed.

**R5 scope (retained).** G4 reviewer independence via XAI challenger, attempt-scoped Living State keys, §K.1 checks #19/#20, AG operational dependency.

**R6 scope (retained).** Retry Cases C + D, XAI verdict taxonomy with decision rules, Koskadeux-issued attempt_id, 72h stall escalation, failure routing table.

**R7 scope (retained).** Attempt-registry shape split (per-attempt + manifest), multi-predicate precedence, state-transition table, Case D → Case A routing.

**R8 scope.** This revision addresses AG cross-vote findings (which passed MP R7 APPROVE_WITH_NITS LOW). Core changes: (a) §E scenario form extended with `pre_conditions`, `idempotency`, `argument_sourcing` fields to close the agent-autonomy gap AG identified; (b) §9 retrofit plan strengthened — new "harness coverage proof" requirement mapping legacy procedural content to new scenarios (coverage matrix, MP orphan review for unmapped procedural content); (c) §J state machine adds `stalled → superseded` transition (elevated from MP R7 Gate 2 nit to Gate 1 per AG); (d) §7 G4 Case D runbook-content reviewer actor + logged artifact shape named (elevated per AG); (e) step 2(c) attempt-id discovery handshake de-circularized (MP R7 nit); (f) terminal-state language explicit (MP R7 nit).

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
- `linter_version` (display mirror of §K.0; §K.0 is authoritative; linter flags A↔K drift as FAIL per §K.1 check #4)

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
- `pre_conditions` (list of states/assumptions that must hold before execution; e.g., `user_authenticated`, `target_entity_exists`, `payment_method_on_file`). An agent checks these before invoking the tool.
- `tool_or_endpoint` (exact name and argument shape)
- `argument_sourcing` (for each non-literal argument, where the agent gets the value — e.g., `user_id: read from §C state-store user_sessions`; `target_email: prompt human operator`; `entity_version: read from §D endpoint /api/entities/{id}`). Literal/constant arguments do not require sourcing.
- `idempotency` (one of: `IDEMPOTENT` / `NOT_IDEMPOTENT` / `IDEMPOTENT_WITH_KEY`). If `IDEMPOTENT_WITH_KEY`, include `idempotency_key` field describing the dedupe mechanism (e.g., `hash(user_id+action+target)`, `uuid_v4`, `request_id_from_trigger`).
- `expected_success` (return shape, side effects, verification path)
- `expected_failures` (list of signatures; same failure in §F only if cause diagnosis differs)
- `next_step_success`
- `next_step_failure`

§E covers **expected paths**: common operational scenarios and their anticipated failure branches. Deviations outside any §E branch are handled in §F. Covers both human-initiated (support ticket, ops request) and agent-initiated (allAI triage, scheduled job, cross-system call) flows.

**Why `pre_conditions`, `argument_sourcing`, `idempotency` are required.** Agent-initiated flows need to check pre-conditions before acting (no human intuition to fall back on), need to know where to fetch argument values (stateless agents cannot assume values are in-context), and need to know whether a retry after a timeout is safe (critical for agent error-recovery paths). Human-initiated flows benefit from the same fields but could survive without them; the contract is written for the stricter agent consumer.

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
- `first_staleness_detected_at` — ISO timestamp; initialized `null`; set by linter when STALE transitions `true`; cleared by linter ONLY when all stale predicates re-evaluate to `false` (see non-compliance workflow below)

**Staleness detection (STALE true if ANY of):**
- `last_refresh_commit != current HEAD of system's primary repo` AND `now - last_refresh_date > 60 days`
- `now - last_harness_date > 90 days`
- Any §B row has `UNVERIFIED` overlay

**Non-compliance workflow:**
1. On STALE transition `false → true`: linter sets `first_staleness_detected_at = now` and emits `WARN` (not PR-blocking).
2. If `now - first_staleness_detected_at > 30 days` AND any stale predicate is still true: linter emits `FAIL` (PR-blocking).
3. On metadata refresh (author updates `last_refresh_*` fields OR re-runs the harness OR re-verifies a §B cell): linter **re-evaluates all stale predicates**. `first_staleness_detected_at` is cleared to `null` ONLY if every stale predicate is false. If any predicate remains true (e.g., `last_harness_date` still > 90d, or a §B cell still `UNVERIFIED`), `first_staleness_detected_at` is preserved and the grace clock continues — the runbook is not considered re-freshed for grace-workflow purposes until the underlying staleness is cured.

**Rationale:** without this rule, a metadata-only refresh could wipe the grace clock while the runbook remained substantively stale, defeating the non-compliance mechanism.

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

**§K.1 — `runbook-lint`** (CI job in `aidotmarket/runbooks` repo).

The linter's complete validation set with design-level severity classification:

| # | Check | Severity |
|---|---|---|
| 1 | Every §A–§K section present and in prescribed order | FAIL |
| 2 | Every §C–§K section contains its required agent form (§4 schema) | FAIL |
| 3 | §A fields match §J authoritative values (Header drift) | FAIL |
| 4 | §A `linter_version` matches §K.0 `linter_version` (A↔K consistency) | FAIL |
| 5 | §B status cells use only canonical values (`SHIPPED`/`PARTIAL`/`PLANNED`/`DEPRECATED`/`BROKEN`) | FAIL |
| 6 | Every §B row cites backing code (`file:function` or module) | FAIL |
| 7 | §B cell with `Last Verified` empty or > 90 days gets `UNVERIFIED` annotation overlay | WARN (informational; contributes to STALE per §J) |
| 8 | §F Repair Ref resolves to a real §G `id` | FAIL |
| 9 | §G `symptom_ref` resolves to a real §F `id` | FAIL |
| 10 | §G `component_ref` resolves to a real §C Component | FAIL |
| 11 | §I scenario count ≥ 10 with required distribution (§4 §I) | FAIL |
| 12 | §I weights sum to 1.0 (±0.001) | FAIL |
| 13 | §I unequal weights have §I.1 justification with one sentence per weighted scenario | FAIL |
| 14 | §J required fields populated | FAIL |
| 15 | §J STALE predicate evaluation and `first_staleness_detected_at` transition management | see §J grace workflow (WARN → FAIL after 30 days) |
| 16 | §K.0 `linter_version` on this runbook matches `runbook-lint --version`  | WARN (until runbook re-validates) |
| 17 | §K required fields populated (`last_lint_run`, `last_lint_result`, etc.) | FAIL |
| 18 | Retrofit runbook has `trace_matrix_path` + `word_count_delta` populated | FAIL (if runbook is marked as retrofit in §K) |
| 19 | §A required fields populated (`system_name`, `purpose_sentence`, `owner_agent`, `escalation_contact`, `lifecycle_ref`, `authoritative_scope`, `linter_version`) | FAIL |
| 20 | §B renders as a markdown table with the exact required column set (`Feature/Capability`, `Status`, `Backing Code`, `Test Coverage`, `Last Verified`) in the prescribed order | FAIL |

FAIL is PR-blocking. WARN is informational (logged, surfaced in CI output, does not block). The STALE/grace workflow (check #15) is the only check that has a time-based WARN→FAIL escalation; all other checks resolve to WARN or FAIL immediately on each linter run.

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

**G4 — Gate 4 (production / falsifiability) AC.** The standard is ratified only if a second runbook authored against the *frozen* standard passes an *externally-authored hidden* evaluation set, under reviewer-independence constraints spanning three agents:

1. **Standard freeze.** When this BQ reaches Gate 1 APPROVED, the spec commit SHA is pinned as `frozen_commit_sha`. No edits to the spec during G4 testing; any change reopens Gate 1.

2. **G4 attempt identification.** Each G4 run has a unique `g4_attempt_id` (UUID v4) issued by **Koskadeux**, not Vulcan. Attempt state lives in two Living State entities — a per-attempt registry and a per-frozen-commit manifest — so that multiple retries under one `frozen_commit_sha` are cleanly representable without overwriting prior attempt state.

   **At attempt start:**

   a. Vulcan emits a Living State event `event_type=g4-attempt-opened` with `entity_key=build:bq-runbook-standard`, `payload={frozen_commit_sha, opened_by: 'vulcan', retry_case: <A|B|C|D|null>, prior_attempt_id: <id|null>}`. (On first attempt for a `frozen_commit_sha`, `retry_case` and `prior_attempt_id` are `null`.)

   b. Koskadeux responds by:
   - **Writing a per-attempt registry entity** at `state:bq-runbook-standard:g4:aim-node:{frozen_commit_sha}:{g4_attempt_id}:attempt-registry` with `{g4_attempt_id, frozen_commit_sha, prior_attempt_id, retry_case, opened_at, opened_by, status: 'active'}`. Create-only (`expected_version=0`); collision on this key is architecturally impossible because Koskadeux just generated the UUID.
   - **Patching the per-frozen-commit manifest** at `state:bq-runbook-standard:g4:aim-node:{frozen_commit_sha}:attempt-manifest` to append `g4_attempt_id` to its `attempt_ids` list. Manifest is updated via `patch` with optimistic locking (`expected_version` must match); concurrent opens under the same `frozen_commit_sha` serialize naturally — second opener's patch fails, Koskadeux retries with fresh read of manifest.

   c. Vulcan reads the per-frozen-commit manifest at `…:{frozen_commit_sha}:attempt-manifest` to obtain the newest `g4_attempt_id` (the last entry in the `attempt_ids` list). Vulcan then reads the per-attempt registry at `…:{frozen_commit_sha}:{g4_attempt_id}:attempt-registry` for authoritative attempt state. This manifest-first read path removes the circular dependency that would otherwise arise from trying to read an attempt-scoped key without first knowing the attempt id.

   **Why two entities, not one.** The per-attempt registry holds the authoritative state for a single attempt (created once, mutated only via defined status transitions per step 9). The manifest holds the ordered list of attempt_ids under a `frozen_commit_sha` so auditors and retries can traverse the attempt chain without scanning the full keyspace. Separating them lets the registry be create-only with defined mutations while the manifest grows monotonically under optimistic locking.

   **Why Koskadeux issues.** The attempt id is a property of the system of record, not the author. Neutral issuance via Koskadeux (the session + state owner) gives clean provenance and prevents Vulcan from concurrently self-issuing under race conditions.

   **Artifact namespace.** All other Living State entities in G4 are namespaced under `state:bq-runbook-standard:g4:aim-node:{frozen_commit_sha}:{g4_attempt_id}:<artifact>` where `<artifact>` ∈ `{answer-key, harness-result, reconciliation-transcript, xai-correspondence-verdict, stall-log, attempt-registry}`.

3. **Vulcan authors AIM Node runbook** using only the frozen standard as input. Vulcan may reference per-system code and incident evidence for AIM Node, but may NOT reference the Infisical runbook content or the Infisical scenario set. Draft committed to `aidotmarket/runbooks/aim-node.md`.

4. **Hidden evaluation set — three-party authoring:**
   - **MP and AG each author a draft ≥10-scenario evaluation set independently** (no shared working session; no access to each other's drafts during authoring) from AIM Node code + incident evidence.
   - **MP + AG reconcile** their drafts into a single evaluation set in a joint session. Disputes on scenario inclusion, expected-answer keys, or weights escalate to Max. The session transcript (participant messages + per-scenario vote log) is recorded.
   - **Reconciliation transcript logged** to `…:reconciliation-transcript` with create-only semantics (`expected_version=0` on first write; subsequent writes FAIL).
   - **Final expected-answer key** (scenario id → acceptable first actions set → weight) logged to `…:answer-key` with fields `{authored_session, mp_session, ag_session, reconciled_at, frozen_commit_sha, g4_attempt_id}`, create-only semantics. Once logged, immutable; edits require a new `g4_attempt_id`.
   - Vulcan does not see the evaluation set or the answer key before or during AIM Node authoring.

5. **XAI correspondence challenger pass.** Before harness scoring runs, **XAI independently reviews** the pair `(answer-key, AIM Node runbook)` for *correspondence bias* — does the scenario set appear hand-tailored to the runbook's content or structure in a way that would undeservingly inflate pass rate? XAI is read-only and does not author scenarios or score; it only red-teams the scenario-runbook pairing for author bias. XAI's documented Council role is architecture/sign-off, which this correspondence check fits.

   **Verdict taxonomy** (each with decision rule + exemplar):

   - **`CLEAN`** — No observed correspondence bias. Decision rule: scenarios test runbook behaviors but are not phrased, structured, or sequenced in a way that mirrors runbook wording. Exemplar: scenario says "agent is asked to rotate a leaked API key; what is the first action?" while the runbook's rotation section uses different language and structure — the scenario tests the runbook without quoting or mirroring it.
   - **`MINOR_OVERLAP`** — Some phrasing or structure mirrors the runbook, but does not obviously inflate pass rate. Decision rule: up to 2 scenarios share incidental phrasing with the runbook; no scenario uniquely maps to a single runbook section in a way a non-author would have difficulty answering without that section. Exemplar: a scenario uses the phrase "half-open circuit breaker" which also appears in the runbook — shared terminology from the underlying system, not from author bias. Does not block.
   - **`SUSPECT_OVERFITTING`** — Scenarios appear hand-tailored. Decision rule: 3 or more scenarios share structure, phrasing, or decision paths that closely mirror runbook sections in ways unlikely to occur if the scenario author had written independently of the runbook; OR any single scenario is essentially a restatement of a runbook passage. Exemplar: runbook §F-03 says "if X, check log Y for pattern Z"; scenario expected-answer says "check log Y for pattern Z" — the scenario is the runbook passage in different clothing. Blocks; forces eval-set re-draft via retry Case D (see step 8).

   Borderline cases escalate to Max via Living State event `g4-correspondence-escalation`. XAI's verdict + rationale logged to `state:bq-runbook-standard:g4:aim-node:{frozen_commit_sha}:{g4_attempt_id}:xai-correspondence-verdict` with `{verdict, rationale, session, borderline_escalated}`.

6. **Review and scoring — split roles:**
   - **MP first-pass design review** on AIM Node runbook (verdict: `APPROVE` / `APPROVE_WITH_NITS` / `CONDITIONAL` / `REQUEST_CHANGES`). Runs in a session separate from MP's scenario-authoring session.
   - **AG runs the harness and scores** against the logged expected-answer key. MP does NOT score.
   - Harness score logged to `…:harness-result` with `{scorer_agent, scored_session, per_scenario_scores, weighted_total}`.

7. **Pass criteria.** G4 passes if and only if ALL THREE legs pass:
   - MP first-pass design-review verdict is `APPROVE` or `APPROVE_WITH_NITS`
   - XAI correspondence verdict is `CLEAN` or `MINOR_OVERLAP` (not `SUSPECT_OVERFITTING`)
   - AG-scored weighted total on the harness is ≥ 0.80

   **Failure routing** (which retry Case the failure triggers; see step 8):
   - MP verdict `REQUEST_CHANGES` or `CONDITIONAL` → Case B (runbook revision) or Case A (if feedback indicates spec defect)
   - XAI verdict `SUSPECT_OVERFITTING` → Case D (fresh eval set, runbook unchanged)
   - AG score < 0.80 → typically Case B (runbook revision); Case C only if AG also reports a scorer/harness defect in the scoring session
   - Any leg stalled > 72 hours → stall-escalation event (step 9); Max routes.

   **Multi-predicate failure precedence.** If two or more failure predicates fire in the same attempt:
   - **Case A wins** if any failure indicates a spec defect. Spec defects supersede runbook, eval-set, or scorer issues because they invalidate the frame in which the other artifacts were produced.
   - **Case C is compatible with any other case.** A scorer defect can coexist with a runbook or eval-set problem; in that event the non-C case runs first (producing a new attempt with correct artifacts), and only then does Case C re-score if needed. This is because Case C alone reuses existing answer-key + runbook + XAI verdict, which other cases change.
   - **Otherwise Max adjudicates.** Ambiguous multi-predicate failures (e.g., MP `CONDITIONAL` + XAI `SUSPECT_OVERFITTING` with no clear Case A) are adjudicated by Max via Living State event `g4-multi-predicate-adjudication` with payload listing each fired predicate and its rationale.

8. **Retry protocol.** G4 retries fall into four mechanically representable cases. Each case requires Koskadeux to issue a new `g4_attempt_id` via step 2 (the `g4-attempt-opened` event carries a `retry_case` field and `prior_attempt_id` to link attempts).

   - **Case A — spec revision required.** If G4 failure reveals a design flaw in the standard itself, Gate 1 reopens. On Gate 1 re-approval, a new `frozen_commit_sha` applies; a new `g4_attempt_id` is issued. All prior G4 artifacts are preserved under the old namespace for audit. Fresh everything: runbook may need revision for the new standard; new MP + AG eval set; new XAI verdict; new harness result.

   - **Case B — runbook revision required (spec unchanged).** The AIM Node runbook has a content defect but the standard and eval infrastructure are sound. Vulcan re-authors the AIM Node runbook against the same `frozen_commit_sha`. New `g4_attempt_id`. MP + AG author a NEW hidden evaluation set (prior set is in Living State but quarantined; new authoring session, no access to prior set). XAI re-runs correspondence. AG re-scores. All new artifacts at the new attempt-scoped namespace; old artifacts preserved.

   - **Case C — scorer/harness defect (new in R6).** AG scoring reveals a defect in the harness or scorer itself (e.g., the scorer misclassifies a correct answer as incorrect due to a normalization bug), NOT a content problem with either the runbook or the eval set. Case C preserves all non-defective artifacts and re-scores only. Mechanically:
     - `answer-key` from prior attempt: preserved, REUSED (copied under new attempt id with `source_attempt_id` reference)
     - `AIM Node runbook` content: unchanged (same commit SHA on the runbook side)
     - `xai-correspondence-verdict` from prior attempt: preserved, REUSED (same pair)
     - `harness-result` from prior attempt: INVALIDATED; logged to `…:{prior_attempt_id}:harness-result-invalidated` with `{invalidation_reason, invalidated_at, invalidated_by}`
     - New `g4_attempt_id` with `retry_case=C`; AG re-runs harness after scorer fix; only the new `…:{new_attempt_id}:harness-result` is written.
     - This is the only case where the answer-key and XAI verdict are reused across attempts — because the authoring inputs and the runbook content did not change; only the scoring machinery did.

   - **Case D — XAI SUSPECT_OVERFITTING (new in R6).** XAI's correspondence challenger pass returns `SUSPECT_OVERFITTING`, indicating the MP + AG eval set appears hand-tailored to the runbook. Case D forces a fresh eval set without impugning the runbook. Mechanically:
     - `AIM Node runbook`: unchanged (no runbook content problem)
     - Prior `answer-key`: preserved under old attempt id; NOT reused
     - New `g4_attempt_id` with `retry_case=D`; MP + AG author a FRESH eval set in new isolated sessions (no access to prior answer-key or prior XAI rationale)
     - New XAI correspondence pass on `(new-answer-key, unchanged-runbook)`
     - If XAI returns `SUSPECT_OVERFITTING` twice in a row on the same runbook, escalates to Max (Living State event `g4-repeated-overfitting`); Max may authorize a runbook-content review to check for spec-induced authoring patterns that force correspondence.
     - **Runbook-content reviewer appointment.** Max appoints a reviewer agent. The reviewer MUST be an agent independent of the prior failing eval-set authoring and scoring sessions. Eligible: MP (if MP did not co-author the overfitting eval set — i.e., this is the first `SUSPECT_OVERFITTING` in the current retry chain and MP did not author) OR XAI (per its architecture/sign-off role). Ineligible: Vulcan (conflict of interest as standard + runbook author), AG (conflict of interest as scorer and prior eval-set co-author).
     - **Review artifact.** Reviewer writes to Living State at `state:bq-runbook-standard:g4:aim-node:{frozen_commit_sha}:{g4_attempt_id}:runbook-content-review` with create-only semantics, fields `{reviewer_agent, reviewer_session, reviewed_attempt_id, reviewed_at, outcome, rationale}`. `outcome` is one of: `runbook_defect` (authoring problem in AIM Node runbook) → routes to Case B; `standard_defect` (the standard itself forces correspondence patterns) → routes to Case A (reopens Gate 1, new `frozen_commit_sha`); `no_defect` (review finds neither; eval-set was drafted poorly both times) → routes to a third Case D attempt with new MP + AG pair or Max manually authors eval-set.
     - AG scores against new answer-key.

   **Cross-case invariants:**
   - Koskadeux issues every new `g4_attempt_id`; Vulcan does not self-issue.
   - No silent overwrites. Any attempt to write to an already-populated attempt-scoped key FAILS (create-only semantics enforced at Living State level via `expected_version=0` on put).
   - Every retry's `attempt-registry` entry back-references `prior_attempt_id` and declares `retry_case` so an auditor can traverse attempt chains.
   - Invalidation writes (Case C) are logged, not destructive. The invalidated `harness-result` entity remains in Living State.

9. **AG operational dependency.** G4 step 6 requires AG to score. If AG is unavailable or fails to complete scoring within 48 hours of harness dispatch, the attempt stalls. A stall record is logged to `…:stall-log` with `{stall_reason, stalled_at, last_known_state}`. There is NO automatic fallback to MP for scoring — preserving the reviewer-independence split is more important than attempt velocity.

   **Explicit escalation deadline.** If the stall persists beyond 72 hours from `stalled_at`, Koskadeux emits a Living State event `event_type=g4-stall-escalation` with payload `{g4_attempt_id, stall_reason, stalled_for_hours, last_known_state}`. This event is the spec's page-Max signal. Max then decides: resume (if the blocker cleared), abort the attempt (Case A/B/C/D retry as appropriate), or reissue (exceptional cases; must be justified in the event reply payload). The escalation record persists at `…:stall-escalation` until the attempt resolves.

   **Attempt-registry status transitions.** The per-attempt registry entity (step 2) has a `status` field with defined states and transitions. Koskadeux patches `status` on every transition; Vulcan never writes to `status` directly.

   | From | To | Trigger |
   |---|---|---|
   | `active` | `stalled` | AG scoring unresponsive for 48 hours (Koskadeux detects, patches status, begins 72h escalation timer) |
   | `stalled` | `active` | Max `resume` action (stall blocker cleared); Koskadeux patches status, clears `stalled_at` |
   | `stalled` | `aborted` | Max `abort` action (attempt dead-ended without resolving); Koskadeux patches status, logs abort reason |
   | `stalled` | `superseded` | A new attempt with `prior_attempt_id = this_stalled_attempt_id` is opened without Max first issuing `abort` — i.e., Max elects to start a fresh attempt in parallel with or replacing the stalled one. Koskadeux patches the stalled attempt's status when the new `attempt-manifest` write lands. |
   | `active` | `superseded` | A new attempt with `prior_attempt_id = this_attempt_id` is opened (any retry Case); Koskadeux patches status when the new `attempt-manifest` write lands |
   | `active` | `passed` | All three pass-criteria legs met (MP APPROVE, XAI non-SUSPECT, AG ≥ 0.80); Koskadeux patches status on harness-result write |
   | `active` | `failed` | Any pass-criteria leg failed and Max elects not to retry; Koskadeux patches status on Max's `failed` action event |

   **Terminal states.** `passed`, `failed`, `aborted`, and `superseded` are terminal. No outgoing transitions are defined from any terminal state; any attempt to transition out of a terminal state is a linter-level FAIL (spec-internal contradiction). The only ways an attempt's `status` can change from a terminal value is: (a) never (audit-preserved); (b) a new attempt is opened with `prior_attempt_id = this_attempt_id`, which does NOT re-animate the terminal attempt — it creates a new attempt entry with its own `status: 'active'`.

   A registry entry's `status` is the authoritative answer to "what is this attempt's current state." Auditors consult the manifest to list attempts, then the per-attempt registries to see state.

10. **Why this is falsifiable.** Vulcan cannot overfit scenarios (never sees the eval set). Vulcan cannot import Infisical patterns directly (explicit constraint). MP cannot bias scoring toward its own authored scenarios (AG scores independently). AG cannot bias scenarios toward its scoring preferences (MP co-authors and reconciles). MP + AG cannot align during reconciliation to produce a hand-tailored set (XAI red-teams the answer-key-vs-runbook correspondence). Retry attempts cannot reuse the same eval set (attempt-scoped namespace + create-only writes). If the standard is good, a frontier-quality agent can author a conformant runbook against it on first submission; if not, G4 reveals that before the standard ships.

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
- **Harness coverage proof** — every legacy section with procedural content (operate / isolate / repair instructions, decision trees, step-by-step procedures) must be represented by at least one harness scenario in the new runbook's §I scenario set. The retrofit PR includes a `procedural-coverage-matrix` with columns `Legacy Procedural Section | Scenario ID(s) in new runbook`. MP reviews this matrix for unmapped procedural content. Unmapped procedural content is a FAIL — either add a scenario covering it, restructure to preserve the content, or explicitly justify why the procedural content is obsolete with the new design.
- **Harness score** — must match or exceed legacy harness score (if one existed). For CRM/Celery, harness must pass at ≥ 0.80 AND procedural-coverage-matrix must be complete.

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

## Appendix B: R3 → R4 Change Log

| R3 STILL_OPEN / NEW FINDING | R4 fix | Location |
|---|---|---|
| §J grace-clear loophole (metadata refresh wipes 30-day clock while stale for other reasons) | Clear `first_staleness_detected_at` only when ALL stale predicates are false; re-evaluate on every refresh | §4 §J non-compliance workflow |
| G4 reviewer independence (same MP authors scenarios AND reviews) | Independent MP + AG scenario drafts → joint reconciliation → immutable logged answer key. MP reviews, AG scores. | §7 G4 steps 3–6 |
| Fail-severity model incomplete (§J lists 3, §K.1 implies more) | §K.1 complete severity classification table (18 checks × WARN/FAIL) | §4 §K.1 |
| `linter_version` drift (§A + §K duplicated, no consistency check) | §K.0 authoritative; §A is display mirror; A↔K drift is §K.1 FAIL check #4 | §4 §A, §4 §K.1 |

## Appendix C: R4 → R5 Change Log

| R4 STILL_OPEN / NEW RISK | R5 fix | Location |
|---|---|---|
| G4 reviewer independence still partial (MP co-authors eval set + supplies review leg) | XAI added as third-party correspondence challenger (`CLEAN` / `MINOR_OVERLAP` / `SUSPECT_OVERFITTING`); reconciliation transcript logged | §7 G4 steps 4–7 |
| NEW MEDIUM: Static Living State keys collide on retry | Attempt-scoped namespace `…:{frozen_commit_sha}:{g4_attempt_id}:…`; create-only semantics via `expected_version=0` | §7 G4 step 2, all artifact references |
| NEW MEDIUM: Retry protocol underspecified | Case A (spec revision → reopen Gate 1, new `frozen_commit_sha`) + Case B (runbook revision only → new `g4_attempt_id`, new eval set) explicit | §7 G4 step 8 |
| §K.1 completeness: §A required fields + §B table form checks missing | §K.1 checks #19 and #20 added | §4 §K.1 |
| NEW LOW: AG operational dependency undocumented | 48-hour stall rule; no auto-fallback to MP (preserves independence); escalation to Max | §7 G4 step 9 |

## Appendix D: R5 → R6 Change Log

| R5 STILL_OPEN / NEW RISK | R6 fix | Location |
|---|---|---|
| Retry protocol incomplete for scorer/harness defect | Case C added — invalidate harness-result only; reuse answer-key, runbook, XAI verdict; new `g4_attempt_id` for re-score | §7 G4 step 8 Case C |
| `SUSPECT_OVERFITTING` routing not explicit | Case D added — fresh eval set (runbook unchanged), new `g4_attempt_id`, MP + AG re-author with no access to prior answer-key | §7 G4 step 8 Case D |
| NEW MEDIUM: XAI verdict taxonomy needs operationalization | Decision rules + exemplars per verdict band (`CLEAN`/`MINOR_OVERLAP`/`SUSPECT_OVERFITTING`); borderline escalates to Max | §7 G4 step 5 |
| NEW LOW: `g4_attempt_id` authority should be neutral | Koskadeux issues via `g4-attempt-opened` event → attempt-registry entity; Vulcan consumes | §7 G4 step 2 |
| NEW LOW: Stall escalation deadline should be in spec | 72h escalation rule explicit; Koskadeux emits `g4-stall-escalation` event | §7 G4 step 9 |
| NEW LOW: Three-leg pass criteria increase failure probability | Acknowledged tradeoff (stronger falsifiability); failure-routing table added to step 7 to speed recovery path selection | §7 G4 step 7 |

## Appendix E: R6 → R7 Change Log

| R6 STILL_OPEN / NEW LOW | R7 fix | Location |
|---|---|---|
| **BLOCKING**: `attempt-registry:{frozen_commit_sha}` is single-slot; incompatible with per-retry new attempt_ids and concurrent opens | Per-attempt registry entries at `…:{g4_attempt_id}:attempt-registry` (create-only) + per-frozen-commit manifest at `…:attempt-manifest` (append-only via optimistic lock). Separation lets registry be create-only while manifest serializes concurrent opens. | §7 G4 step 2 |
| NEW LOW: Multi-predicate failure precedence not defined | Case A precedence for spec defects; Case C compatible with any other case (runs after non-C resolution); otherwise Max adjudicates via `g4-multi-predicate-adjudication` event | §7 G4 step 7 |
| NEW LOW: Attempt-registry state transitions implicit | Explicit state machine in §7 G4 step 9: active/stalled/aborted/superseded/passed/failed with transitions-and-triggers table | §7 G4 step 9 |
| NEW LOW: Case D → Case A routing implied, not explicit | Runbook-content review outcomes routed explicitly: runbook defect → Case B; standard defect → Case A | §7 G4 step 8 Case D |

## Appendix F: R7 → R8 Change Log (AG cross-vote response)

R7 received MP APPROVE_WITH_NITS LOW. AG cross-vote (task dfe3090b) returned CONDITIONAL with 3 REQUEST_CHANGES items; R8 addresses all three plus elevates 2 MP R7 nits to Gate 1 per AG's recommendation.

| AG CONCERN / MP R7 NIT | R8 fix | Location |
|---|---|---|
| §E scenario form incomplete for agent autonomy | Added `pre_conditions`, `argument_sourcing`, `idempotency` (+ optional `idempotency_key`) per scenario | §4 §E |
| §9 retrofit manual-check risk of content loss | Added `harness coverage proof` requirement: every legacy procedural section must map to ≥1 scenario in new harness; `procedural-coverage-matrix` artifact required; MP orphan review extended | §9 Retrofit preservation contract |
| `stalled → superseded` transition missing (AG elevated from MP R7 nit) | Added row to state machine; Max can open a replacement attempt on a stalled attempt without first issuing `abort` | §4 §J state transitions |
| Case D reviewer actor + artifact (AG elevated from MP R7 nit) | Reviewer appointment rules (must be independent; MP or XAI eligible; Vulcan and AG ineligible); artifact `…:runbook-content-review` with create-only semantics and full field set; 3-way `outcome` routing (`runbook_defect`/`standard_defect`/`no_defect`) | §7 G4 step 8 Case D |
| Step 2(c) attempt-id discovery circular (MP R7 nit) | Vulcan reads manifest first (gets latest attempt_id), then reads per-attempt registry | §7 G4 step 2(c) |
| Terminal-state explicit language (MP R7 nit) | Added "Terminal states" paragraph stating passed/failed/aborted/superseded are terminal; no outgoing transitions; retry creates new attempt rather than re-animating | §4 §J state transitions |
