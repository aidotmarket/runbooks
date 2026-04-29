# BQ-COUNCIL-RUNBOOK-CONFORMANCE — Gate 2 Implementation Chunking Spec (R2)

**Status:** Gate 2 R2 authoring (vulcan-direct fold of AG R1 cross-review).
**Revision history:** R1 authored S529 by MP at `d96aede` (250 lines). R2 authored S529 by vulcan-direct (folds 3 AG R1 mandates + 1 NIT + Max Q6 binding decision Option 1 migrate).
**Parent Gate 1:** `specs/BQ-COUNCIL-RUNBOOK-CONFORMANCE-GATE1.md` (APPROVED S529, merged `dd844ba`).
**R2 scope:** Folds AG R1 cross-vote `d910edcf` mandates (2 HIGH + 1 MEDIUM) + 1 NIT + Max S529 Q6 = Option 1 (migrate).

## R2 changes summary

- **Mandate 1 (HIGH, AG R1):** C2.AC5, C3.AC5, C4.AC4 updated to explicitly mandate `git mv ./<runbook>.md runbooks/<runbook>.md` per Max Q6 = Option 1. Removed "either/or" + "compatibility decision" language. Added C2.AC0/C3.AC0/C4.AC0 making the migration the first-step requirement of each chunk.
- **Mandate 2 (HIGH, AG R1):** Q6 in §7 marked **RESOLVED S529** (Option 1 migrate: `git mv` in C2/C3/C4).
- **Mandate 3 (MEDIUM, AG R1):** R7 in §5 re-framed around migration mechanics (inbound reference cleanup) rather than architectural choice. Mitigation points to specific C2/C3/C4 `git mv` ACs + C5c inbound reference cleanup per AC17.
- **NIT (AG R1, strongly advised):** C5a sub-split into C5a.1 (council.md scenarios) / C5a.2 (agent-dispatch.md scenarios) / C5a.3 (council-gate-process.md scenarios) / C5a.4 (council-hall-deliberation.md scenarios). Total chunks: 7 → **10**.
- **Q1 in §7:** **RESOLVED S529** (AG R1 NIT folded — C5a sub-split applied).
- **§0 survey notes:** updated to reflect Max Q6 binding migrate decision.
- **§1 chunk table:** updated to 10 rows.
- **§3 sequencing diagram:** `C1 → (C2 ∥ C3 ∥ C4) → (C5a.1 ∥ C5a.2 ∥ C5a.3 ∥ C5a.4) → C5b → C5c`.
- **§4 cross-review schedule:** updated for sub-chunks.
- **§6 success criteria:** "all 10 chunks" + post-migration paths.

## 0. Survey notes

Gate 1 R2 was read from `main` at `dd844ba` and is 285 lines. **Per Max S529 Q6 = Option 1 (migrate):** the existing 3 legacy Council runbooks at repo root (`agent-dispatch.md`, `council-gate-process.md`, `council-hall-deliberation.md`) are migrated via `git mv` to canonical paths under `runbooks/` as the first commit-step of C2, C3, C4 respectively. New `runbooks/council.md` is created fresh in C1 (no migration needed).

`runbook-lint` and `runbook-harness` are Click console scripts in `pyproject.toml` (`runbook_tools.cli:lint_cmd` and `runbook_tools.cli:harness_cmd`). CLI invocation pattern: `runbook-lint <path>` and `runbook-harness --runbook <path>`.

## 1. Chunk plan summary

**10 chunks total** (Gate 1 §4.5 7-chunk plan + AG R1 NIT C5a sub-split into 4 per-runbook scenario chunks).

| Chunk | Title | Files touched | LOC est | Dependencies | Reviewer agents |
|---|---|---|---|---|---|
| C1 | council.md NEW (index + entry-point) | NEW: `runbooks/council.md` | ~180 | none | MP build, AG+DeepSeek review |
| C2 | agent-dispatch.md migration + §A-§K restructure + retired-agents | `git mv ./agent-dispatch.md → runbooks/agent-dispatch.md`, then §A-§K | ~280 net | C1 | MP build, AG review |
| C3 | council-gate-process.md migration + §A-§K restructure | `git mv ./council-gate-process.md → runbooks/council-gate-process.md`, then §A-§K | ~250 net | C1 | MP build, AG review |
| C4 | council-hall-deliberation.md migration + §A-§K restructure | `git mv ./council-hall-deliberation.md → runbooks/council-hall-deliberation.md`, then §A-§K | ~250 net | C1 | MP build, AG review |
| C5a.1 | council.md §I scenarios (≥10 full distribution) | `runbooks/council.md` §I | ~150 | C1 | MP build, AG+DeepSeek review |
| C5a.2 | agent-dispatch.md §I scenarios (≥5) | `runbooks/agent-dispatch.md` §I | ~70 | C2 | MP build, AG+DeepSeek review |
| C5a.3 | council-gate-process.md §I scenarios (≥5) | `runbooks/council-gate-process.md` §I | ~70 | C3 | MP build, AG+DeepSeek review |
| C5a.4 | council-hall-deliberation.md §I scenarios (≥5) | `runbooks/council-hall-deliberation.md` §I | ~70 | C4 | MP build, AG+DeepSeek review |
| C5b | Harness execution + score validation | n/a (test runs) | n/a | C5a.1-4 | MP build, AG audit |
| C5c | §J + §K + final lint sweep + AC17 inbound-reference cleanup | All 4 runbooks §J + §K + memory edit #1 + `infra:council-comms` patches | ~80 net | C5b | MP build, Vulcan audit |

## 2. Per-chunk specs

### Chunk 1: council.md NEW (index + entry-point)

**Files:**
- NEW: `runbooks/council.md`

**Scope:**
- Top-level index runbook. Entry point for new Vulcan/model boot.
- §A YAML frontmatter (`system_name=Council`, `owner_agent=vulcan`, `authoritative_scope` deferring to `infra:council-comms` per AC2 + L1).
- §B Capability Matrix for Council operations: dispatch, gate review, deliberation, escalation; backing code references per AC3.
- §C Architecture: defines `council_request` as canonical code entry point; agent rosters; `review_order`; `dispatch_patterns`. Council-as-one-system view per Q3.
- §D Agent Capability Map: MP, AG, DeepSeek, CC, Vulcan operations + skills + auth + coverage. XAI listed as `DEPRECATED` with cold-storage pointer.
- §E Operate scenarios: dispatch a review, run a gate, escalate to deliberation, refresh Council config from Living State.
- §F Isolate symptom index: Council-level failure modes.
- §G Repair patterns referencing §F by ID.
- §H Evolve predicates: `BREAKING|REVIEW|SAFE` classification of Council changes.
- §I scenario set placeholder only in C1; ≥10 scenarios authored in C5a.1.
- §J placeholder only in C1; populated in C5c with `last_refresh_commit` at C5c merge SHA.
- §K placeholder only in C1; populated in C5c with `conformance_status=provisional` initially.
- AC15 strategic "why" content: MP=primary reviewer, AG=cross-vote, DeepSeek=full voter graduated S528, XAI retired, CC=fallback. Literal-named per Q6.
- Document AC8 file-qualified cross-runbook reference convention in §A `authoritative_scope` text.

**Acceptance criteria (chunk-local):**
- C1.AC1: `runbooks/council.md` exists with §A-§K sections in order; §I/§J/§K placeholders are acceptable until C5a.1/C5c.
- C1.AC2: §A YAML frontmatter validates per AC2.
- C1.AC3: §B-§D and §F-§H populated with backing-code or Living State reference for non-`PLANNED` rows per AC3.
- C1.AC4: AC15 strategic-why content present.
- C1.AC5: AC8 cross-runbook reference convention documented in §A.
- C1.AC6: `runbook-lint runbooks/council.md` runs without crash; failures attributable only to §I/§J/§K placeholders are acceptable.

**Dependencies:** none.

**Risks + mitigations:**
- R: §C agent rosters drift from `infra:council-comms` before C5c lifecycle population. M: §C cites Living State as authoritative; concrete agent state in §C is descriptive only per L1.

### Chunk 2: agent-dispatch.md migration + §A-§K restructure + retired-agents appendix

**Files:**
- MIGRATE: `agent-dispatch.md` (repo root) → `runbooks/agent-dispatch.md` via `git mv` (preserves git history).
- MODIFY: `runbooks/agent-dispatch.md` (post-migration) — restructure to §A-§K.

**Scope:**
- **First commit-step in chunk:** `git mv ./agent-dispatch.md runbooks/agent-dispatch.md`. Preserves git history; canonical location per Gate 1 AC1 + Max Q6 = Option 1.
- §A YAML frontmatter slice-scoped to dispatch mechanics; `authoritative_scope` defers live config to `infra:council-comms` per L1.
- §B Capability Matrix: dispatch tools (`council_request`, `dispatch_mp_build`, `council_hall`), backends, environment requirements.
- §C Architecture, slice-scoped and no back-reference to `council.md` per H5: dispatch backends, agent processes (Codex CLI, Gemini/AG server, DeepSeek server/API, CC), environment wiring.
- §D Agent Capability Map for dispatch surfaces.
- §E Operate scenarios: dispatch MP build, dispatch AG review, dispatch DeepSeek review, dispatch CC fallback build.
- §F Isolate symptoms: gateway timeout, AG progress-guard timeout, MP mutex queue, dispatcher-stale-but-files-committed, MCP tool prefix lowercase silent-fail.
- §G Repair patterns referencing §F.
- §H Evolve predicates for dispatch surface changes.
- §I ≥5 scenarios scoped to dispatch mechanics (≥2 §E, ≥1 §F, ≥1 §G, ≥1 §H or ambiguous) per AC10. Authored in C5a.2.
- §J populated in C5c.
- §K populated in C5c.
- Retired-agents appendix per AC16: XAI cold-storage with reactivation runbook pointer to `infra:council-comms.retired_agents.xai`.
- AC15 strategic-why: literal-named XAI fabrication + retirement reasoning.

**Acceptance criteria (chunk-local):**
- **C2.AC0 (NEW per Mandate 1):** `git mv ./agent-dispatch.md runbooks/agent-dispatch.md` performed as first commit-step of chunk. Repo-root path `./agent-dispatch.md` no longer exists post-chunk; canonical `runbooks/agent-dispatch.md` exists with git history preserved.
- C2.AC1: §A-§H plus retired-agents appendix per AC16.
- C2.AC2: §C does not back-reference `council.md` per H5; cross-runbook references use AC8 file-qualified syntax.
- C2.AC3: AC15 + AC16 present.
- C2.AC4: `runbook-lint runbooks/agent-dispatch.md` structural FAIL count drops to only expected §I/§J/§K placeholder failures.
- **C2.AC5 (REVISED per Mandate 1):** `git mv ./agent-dispatch.md runbooks/agent-dispatch.md` performed as first step (subsumed by C2.AC0). Repo-root path is removed by the migration. Inbound reference cleanup (memory edit #1, `infra:council-comms` cross-refs, tooling) is deferred to C5c per AC17.

**Dependencies:** C1 (cross-runbook reference convention defined in `council.md` §A).

### Chunk 3: council-gate-process.md migration + §A-§K restructure

**Files:**
- MIGRATE: `council-gate-process.md` (repo root) → `runbooks/council-gate-process.md` via `git mv`.
- MODIFY: `runbooks/council-gate-process.md` — restructure to §A-§K.

**Scope:**
- **First commit-step in chunk:** `git mv ./council-gate-process.md runbooks/council-gate-process.md`.
- §A YAML frontmatter slice-scoped to gate flow.
- §B Capability Matrix: BQ lifecycle states, 4-gate flow, cross-review-gate enforcement.
- §C Architecture, slice-scoped: `build:bq-*` entity shape, gate state transitions, dispatch-binding tokens for author-mode, compliance gate logic. Living State key shapes documented.
- §D Agent Capability Map: per-agent gate participation (MP=primary reviewer + builder, AG=cross-vote, DeepSeek=full voter, CC=fallback builder, Vulcan=orchestrator).
- §E Operate scenarios: open Gate 1, advance to Gate 2 chunking, run Gate 3 audit, close Gate 4 production verification.
- §F Isolate symptoms: gate compliance trap, ghost entity bug, `dispatch_mp_build` authoring trap referencing `BQ-COUNCIL-COMPLIANCE-GATE-AUTHORING-DISTINCTION`, break_glass misuse.
- §G Repair patterns including the `gate1.status` patch trap (`APPROVED_WITH_MANDATES` → `APPROVED`).
- §H Evolve predicates for gate-flow changes.
- §I ≥5 scenarios scoped to gate flow per AC10. Authored in C5a.3.
- AC15 strategic-why: why 4 gates, why cross-review-gate, why dispatch-binding tokens for author-mode.

**Acceptance criteria (chunk-local):**
- **C3.AC0 (NEW per Mandate 1):** `git mv ./council-gate-process.md runbooks/council-gate-process.md` performed as first commit-step of chunk.
- C3.AC1: §A-§H plus ≥5 scenario placeholders.
- C3.AC2: §C documents `build:bq-*` entity shape and dispatch-binding mechanism.
- C3.AC3: §F-§G covers gate compliance trap, ghost entity bug, and authoring-distinction trap.
- C3.AC4: AC15 strategic-why on gate-process design choices.
- **C3.AC5 (REVISED per Mandate 1):** `git mv ./council-gate-process.md runbooks/council-gate-process.md` performed as first step (subsumed by C3.AC0). Repo-root path is removed by the migration.

**Dependencies:** C1.

### Chunk 4: council-hall-deliberation.md migration + §A-§K restructure

**Files:**
- MIGRATE: `council-hall-deliberation.md` (repo root) → `runbooks/council-hall-deliberation.md` via `git mv`.
- MODIFY: `runbooks/council-hall-deliberation.md` — restructure to §A-§K.

**Scope:**
- **First commit-step in chunk:** `git mv ./council-hall-deliberation.md runbooks/council-hall-deliberation.md`.
- §A frontmatter slice-scoped to deliberation pattern.
- §B Capability Matrix: 3-phase deliberation (independent assessment + collection/synthesis + cross-pollination).
- §C Architecture: phase 1/2/3 internals, `council_hall` tool, `deliberation_id` state, response collection.
- §D Agent Capability Map: per-agent deliberation participation.
- §E scenarios: when to invoke Council Hall, when independent reviews suffice.
- §F symptoms: deliberation deadlock, agent silence, conflicting verdicts without resolution.
- §G repairs.
- §H evolve predicates.
- §I ≥5 scenarios per AC10. Authored in C5a.4.
- AC15 strategic-why: why 3 phases, why cross-pollination required, when to escalate to Hall vs single review.

**Acceptance criteria (chunk-local):**
- **C4.AC0 (NEW per Mandate 1):** `git mv ./council-hall-deliberation.md runbooks/council-hall-deliberation.md` performed as first commit-step of chunk.
- C4.AC1: §A-§H plus ≥5 scenario placeholders.
- C4.AC2: §C accurately documents 3-phase mechanism.
- C4.AC3: AC15 strategic-why on Hall design.
- **C4.AC4 (REVISED per Mandate 1):** `git mv ./council-hall-deliberation.md runbooks/council-hall-deliberation.md` performed as first step (subsumed by C4.AC0). Repo-root path is removed by the migration.

**Dependencies:** C1.

### Chunk 5a.1: council.md §I scenarios (≥10 full distribution)

**Files:**
- MODIFY: `runbooks/council.md` §I section.

**Scope:**
- ≥10 scenarios with full distribution per AC10: ≥3 §E (operate), ≥3 §F (isolate symptom), ≥2 §G (repair), ≥2 §H (evolve), ≥1 ambiguous-symptom.
- Each scenario has all required fields per AC6: `id`, `trigger`, `pre_conditions`, `tool_or_endpoint`, `argument_sourcing`, `idempotency`, `expected_success`, `expected_failures`, `next_step_success`, `next_step_failure`.
- Cross-runbook references (where they appear) use AC8 file-qualified syntax `<file-stem>:<id>`.
- MP + AG concur on expected-answer keys; DeepSeek deferred per Q8.

**Acceptance criteria (chunk-local):**
- C5a.1.AC1: ≥10 scenarios in `runbooks/council.md` §I.
- C5a.1.AC2: Distribution per AC10.
- C5a.1.AC3: All scenarios have full required fields per AC6.
- C5a.1.AC4: Cross-runbook references use AC8 syntax where applicable.
- C5a.1.AC5: MP + AG cross-review concurs on expected-answer keys.

**Dependencies:** C1.

### Chunk 5a.2: agent-dispatch.md §I scenarios (≥5)

**Files:**
- MODIFY: `runbooks/agent-dispatch.md` §I section.

**Scope:**
- ≥5 scenarios with sub-runbook distribution: ≥2 §E, ≥1 §F, ≥1 §G, ≥1 §H or ambiguous.
- All scenarios have full required fields per AC6.
- Cross-runbook references use AC8 file-qualified syntax.

**Acceptance criteria (chunk-local):**
- C5a.2.AC1: ≥5 scenarios in `runbooks/agent-dispatch.md` §I.
- C5a.2.AC2: Distribution per AC10 sub-runbook variant.
- C5a.2.AC3: All scenarios have full required fields per AC6.
- C5a.2.AC4: Cross-runbook references use AC8 syntax where applicable.
- C5a.2.AC5: MP + AG cross-review concurs on expected-answer keys.

**Dependencies:** C2.

### Chunk 5a.3: council-gate-process.md §I scenarios (≥5)

**Files:**
- MODIFY: `runbooks/council-gate-process.md` §I section.

**Scope:** Same shape as C5a.2 but for gate-process scenarios.

**Acceptance criteria (chunk-local):**
- C5a.3.AC1-AC5: same shape as C5a.2 applied to `runbooks/council-gate-process.md`.

**Dependencies:** C3.

### Chunk 5a.4: council-hall-deliberation.md §I scenarios (≥5)

**Files:**
- MODIFY: `runbooks/council-hall-deliberation.md` §I section.

**Scope:** Same shape as C5a.2 but for deliberation scenarios.

**Acceptance criteria (chunk-local):**
- C5a.4.AC1-AC5: same shape as C5a.2 applied to `runbooks/council-hall-deliberation.md`.

**Dependencies:** C4.

### Chunk 5b: Harness execution + score validation

**Files:**
- n/a (test execution chunk; produces harness reports).

**Scope:**
- Run `runbook-harness --runbook <path>` against each runbook's §I scenario set.
- Production prerequisites per AC14: `KOSKADEUX_MCP_URL` env, dispatch token, scenario YAML files at canonical path.
- Each runbook must produce weighted score ≥ 0.80.
- Capture harness reports for §J `last_harness_pass_rate` population in C5c.

**Acceptance criteria (chunk-local):**
- C5b.AC1: All 4 runbooks produce harness weighted score ≥ 0.80.
- C5b.AC2: Harness reports captured (raw output + summary stats per runbook).

**Dependencies:** C5a.1, C5a.2, C5a.3, C5a.4.

### Chunk 5c: §J + §K + final lint sweep + AC17 inbound-reference cleanup

**Files:**
- MODIFY: All 4 runbook §J + §K sections.
- MODIFY: Memory edit #1 (path strings updated to `runbooks/...` per Max Q6 = Option 1 migration).
- PATCH: `infra:council-comms` Living State entity (cross-references updated to `runbooks/...`).

**Scope:**
- §J Lifecycle YAML per AC11: `last_refresh_session=S5XX`, `last_refresh_commit=<merge SHA>`, `last_refresh_date=ISO-8601`, `first_staleness_detected_at=null` initially, `refresh_triggers`, `scheduled_cadence`, `last_harness_pass_rate` from C5b, `last_harness_date`.
- §K Conformance YAML per AC12: `linter_version=1.0.0`, `last_lint_run`, `last_lint_result=PASS`, `trace_matrix_path`, `word_count_delta`, `conformance_status=provisional` per Gate 1 §10.
- Run `runbook-lint` Click CLI on all 4 runbooks; require FAIL=0 per AC13.
- AC17 inbound-reference cleanup: memory edit #1 path strings + `infra:council-comms` cross-refs updated to `runbooks/...` (post-migration paths).

**Acceptance criteria (chunk-local):**
- C5c.AC1: All 4 §J sections populated with required AC11 fields.
- C5c.AC2: All 4 §K sections populated with required AC12 fields plus `conformance_status=provisional`.
- C5c.AC3: `runbook-lint` FAIL=0 across all 4 files using Click CLI invocation.
- C5c.AC4: Memory edit #1 + `infra:council-comms` cross-references updated to post-migration paths per AC17.

**Dependencies:** C5b.

## 3. Sequencing + parallelization

Sequential dependency chain:

`C1 → (C2 ∥ C3 ∥ C4) → (C5a.1 ∥ C5a.2 ∥ C5a.3 ∥ C5a.4) → C5b → C5c`

C2, C3, C4 can build in parallel after C1 lands. They migrate + restructure different files; no merge conflicts expected. After all 4 file structures are present, C5a.1 (depends on C1 only) and C5a.2/C5a.3/C5a.4 (depend on C2/C3/C4 respectively) can build in parallel — though C5a.1 can technically start as soon as C1 lands since `runbooks/council.md` is created in C1.

## 4. Cross-review schedule

- C1 (`council.md` NEW): MP build primary; AG + DeepSeek cross-review for Council semantics and literal-why content.
- C2, C3, C4 (migration + sub-runbook restructures): MP build; AG cross-review.
- C5a.1 (council.md §I scenarios): MP build; AG + DeepSeek cross-review for expected-answer key concurrence.
- C5a.2, C5a.3, C5a.4 (sub-runbook §I scenarios): MP build; AG + DeepSeek cross-review.
- C5b (harness execution): MP build; AG audit.
- C5c (§J/§K + lint + inbound-ref cleanup): MP build; Vulcan audit, including Vulcan-direct verification of memory edit + Living State patches per AC17.

Reviewer rationale: DeepSeek concurs on C1 + C5a.* where Council semantics and scenario realism are critical. AG handles broader restructures and migration mechanics. DeepSeek participation conditional on `BQ-COUNCIL-DEEPSEEK-SPEC-AUTHORING-PARSE-FAILURE` resolution; if unresolved at chunk dispatch time, AG single review suffices and DeepSeek can rejoin at Gate 3 audit.

## 5. Risk register

- R1: §I scenario authoring scope was substantial in single C5a chunk. **MITIGATED** at R2 by C5a sub-split into C5a.1-C5a.4 (per AG R1 NIT). Each sub-chunk now scoped to one runbook (≤10 scenarios per chunk).
- R2: Harness production prerequisites (`KOSKADEUX_MCP_URL` + dispatch token) may not be available in CI. M: C5b runs locally on Titan-1 first; CI integration is a follow-up BQ if needed.
- R3: Cross-runbook reference syntax (AC8) is novel to `runbook-lint`. M: lint may not enforce syntax; manual schema spot-check is acceptable fallback at Gate 3 verification.
- R4: §J final-conformance gate per Gate 1 §10 requires Infisical cutover commit reference. M: chunks land at provisional `conformance_status`; final transition is post-Infisical follow-up.
- R5: AC17 memory + `infra:council-comms` cross-reference patches drift over time. M: include in C5c scope (now explicitly per Max Q6 = Option 1 migration cleanup); Vulcan audit verifies.
- R6: DeepSeek deferred for C1 + C5a.* may require Gate 2 cross-review re-roll if parse-failure BQ ships mid-build. M: AG single review is sufficient at Gate 2; DeepSeek concurrence can land at Gate 3 audit if BQ resolves in time.
- **R7 (REVISED MEDIUM per AG R1 Mandate 3):** Inbound references to repo-root paths require updating after migration. Memory edit #1 carries `agent-dispatch.md` path strings; `infra:council-comms` cross-references list runbook paths; any tooling that hard-codes repo-root paths breaks post-migration. **Mitigation:** C2.AC0/C2.AC5, C3.AC0/C3.AC5, C4.AC0/C4.AC4 mandate `git mv` as first commit-step of their respective chunks (preserves git history; atomic per-chunk migration). C5c.AC4 mandates inbound-reference cleanup per AC17 (memory edit + `infra:council-comms` patches). If inbound-reference cleanup scope expands beyond C5c (e.g., tooling discovery), file follow-up BQ rather than block C5c.

## 6. Success criteria (Gate 2 close)

- **All 10 chunks** built + audited per Gate 3.
- All chunk-local ACs pass.
- Gate 1 AC1-AC17 satisfied at integration tier.
- `runbook-lint` FAIL=0 across all 4 files (AC13).
- `runbook-harness --runbook <path>` weighted score ≥ 0.80 per file (AC14).
- §J + §K populated per AC11 + AC12.
- `conformance_status=provisional` initial state per Gate 1 §10; final-tier transition deferred to post-Infisical follow-up.
- Memory + `infra:council-comms` cross-references updated per AC17 (post-migration paths).
- Repo-root legacy paths (`./agent-dispatch.md`, `./council-gate-process.md`, `./council-hall-deliberation.md`) no longer exist; canonical paths under `runbooks/` are in place.

## 7. Open questions for Gate 2 cross-review

- **Q1 — RESOLVED S529 (AG R1 NIT folded):** C5a sub-split into C5a.1-C5a.4 per file. Net 10 chunks total; per-runbook scope keeps each MP build ≤150 LOC.
- Q2: Should C5c lint sweep be merged into C5b because harness assumes lint pre-passes, or kept separate as a dedicated lint-pass chunk?
- Q3: AC17 memory + `infra:council-comms` patches: Vulcan-direct in C5c (current plan) or separate post-merge maintenance chunk? (R2 keeps in C5c per current plan unless cross-review pushes back.)
- Q4: Should Gate 3 verification include automated drift detection per Gate 1 §10 `first_staleness_detected_at` population trigger, or is manual scan acceptable for MVP?
- Q5: Per-chunk authoring agent: Vulcan-direct vs MP-author per chunk? Recommended: MP-author for C2-C5c (repetitive-structure rendering, migration mechanics); Vulcan-direct for C1 (meta-meta content density).
- **Q6 — RESOLVED S529 (Max chose Option 1 migrate):** C2/C3/C4 each `git mv` their respective file from repo root to `runbooks/` as first commit-step. Path migration is per-chunk + atomic + preserves git history. Inbound reference cleanup deferred to C5c (AC17).

---

**End of Gate 2 R2 spec.** Awaiting AG R2 cross-vote (read-only) for Gate 2 close, then dispatch C1 build (council.md NEW) on a fresh feature branch.
