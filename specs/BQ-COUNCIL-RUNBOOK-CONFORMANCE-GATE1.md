# BQ-COUNCIL-RUNBOOK-CONFORMANCE — Gate 1 Design Spec (R2)

**Status:** Gate 1 R2 authoring (vulcan-direct).
**Revision history:** R1 authored S528 vulcan-direct (commit `2ed873e`); R2 authored S529 vulcan-direct (folds AG R1 + MP R1 + Max S529 Q1 decision).
**Parent BQ:** `build:bq-runbook-standard` (Gate 1 APPROVED R9 at S486 commit `365c198`, Gate 2 chunks 1+2 in flight).
**Filed-from directive:** Max S528 — "Make sure our runbooks are updated on the current configurations (the why and the how) of the council. Include our reasoning. The runbooks should allow a new model to fully understand the council, our process and why we have it configured this way, such that they could replicate it as well as fully understand the technical implementation and business rational."
**Shape selection:** Max S528 — "Full standard conformance — restructure all three plus the new index to §A–§G, runbook-lint passing. Multi-chunk Gate 1/2/3 build, several sessions."
**R2 scope:** Folds 12 R1 findings (5 HIGH + 4 MEDIUM + 2 LOW + 1 INFO) + Max S529 decision on Q1 sequencing. DeepSeek R1 cross-vote failed twice (DeepSeekResponseParseError) — follow-up `BQ-COUNCIL-DEEPSEEK-SPEC-AUTHORING-PARSE-FAILURE` filed S528. R2 cross-vote falls back to AG single read-only review.

## R2 changes summary

- **H1, H3, AC11:** §J freshness telemetry expanded with `last_refresh_commit`, `last_refresh_date`, `first_staleness_detected_at` fields. §J doubles as the final-conformance gate per Q1 decision (mechanism in §10).
- **H2, AC13/AC14:** Lint and harness locked as real gates; manual-lint fallback removed. MP S528 probe confirmed `runbook-lint` v1.0.0 functional via Click CLI invocation (NOT `python3 -m`); `runbook-harness` loads YAML + dispatches MP + scores.
- **H4, §4.5:** Chunk C5 split into C5a (§I scenarios) / C5b (harness execution) / C5c (§J + §K + lint sweep) → 7 chunks total. Locked plan in §4.5 table.
- **H5, §4.3, AC8:** Sub-runbook §C tables scope to their own slice; no back-references to `council.md`. `council.md` is the canonical parent index defining `council_request` as the code entry point. Cross-runbook §F/§G references use file-qualified ID syntax `<file-stem>:<id>`.
- **M1, AC3:** §B Capability Matrix rows must reference executable surfaces with backing code (file:line or symbol) for all non-`PLANNED` statuses.
- **M3, AC8:** Cross-runbook reference convention added (e.g., `agent-dispatch:F-01`).
- **M4, AC10:** §I scenario distribution adjusted: `council.md` ≥10 (full distribution); sub-runbooks ≥5 each (≥2 §E, ≥1 §F, ≥1 §G, ≥1 §H or ambiguous).
- **L1, §A:** §A `authoritative_scope` defers live config authority to `infra:council-comms` Living State entity; runbooks describe stable architecture + mechanics + reasoning.
- **L2, §4.5:** By-file chunking confirmed; 7-chunk plan locked.
- **I1, §4.2:** Literal-why content aligns with Max directive — already aligned; no change.
- **Q1 (Max S529):** Parallel-with-constraint. §J telemetry gates final conformance (see §10).
- **Q2:** Tooling maturity confirmed via MP probe.
- **Q3:** AG mandate accepted (Council-as-one-system).
- **Q4:** By-file confirmed; C5 split → 7 chunks.
- **Q5:** Deferred to Gate 2 chunking spec author round.
- **Q6:** Literal-why approved.
- **Q7:** Sub-runbook §C scopes without back-references; cross-file refs file-qualified per AC8.
- **Q8:** DeepSeek participation deferred until parse-failure BQ ships.

## 1. Problem

Council documentation across 3 existing runbooks (`agent-dispatch.md`, `council-gate-process.md`, `council-hall-deliberation.md`) is content-current-ish but predates `BQ-RUNBOOK-STANDARD`. It does not conform to §A–§K, has no §I scenario set, no §J lifecycle metadata, and no §K linter conformance. There is no top-level overview/index runbook, so a new Vulcan/model has no canonical entry-point document to read first when learning the Council operating system.

The S528 Council restructure (XAI retirement → cold storage; DeepSeek graduation → full voter; new dispatch_patterns + review_order in `infra:council-comms` v21) compounded the gap: the existing runbooks reference XAI as active and DeepSeek as eval-window-only.

Per Max S528 directive, the bar is replicability — "a new model could fully understand the council, our process and why we have it configured this way, such that they could replicate it." Operational-mechanics-only content does not meet that bar. Strategic reasoning ("why this shape") must be in the documentation.

## 2. Scope

### In scope (4 runbooks)

1. **NEW: `council.md`** — top-level overview/index runbook. Entry point for new Vulcan/model boot. Explains what the Council is, why this shape (5 active members reduced to 4 at S528), how the agents differ in measured capability, when to use which, and how to extend or retire members. Cross-references the three sub-runbooks for operational details.
2. **RESTRUCTURE: `agent-dispatch.md`** — dispatch mechanics (council_request tool, agent backends, env requirements, quirks). Adds "Retired Agents" appendix with XAI cold-storage + reactivation runbook pointer to `infra:council-comms.retired_agents.xai`.
3. **RESTRUCTURE: `council-gate-process.md`** — BQ system + 4-gate flow (Gate 1 design → Gate 2 chunking → Gate 3 build/audit → Gate 4 production verification) + cross-review-gate enforcement mechanism.
4. **RESTRUCTURE: `council-hall-deliberation.md`** — multi-agent deliberation pattern (3 phases: independent assessment → collection/synthesis → cross-pollination).

### Out of scope

- Other agent-related runbooks (`vulcan-configuration.md`, `session-lifecycle.md`) — separate retrofit BQs if Max scopes them.
- Building runbook-lint or harness tooling itself (parent `BQ-RUNBOOK-STANDARD` Gate 2 owns that).
- The Infisical reference runbook (parent `BQ-RUNBOOK-STANDARD` Gate 2 owns that).
- Migrating prior session's review-history references that named XAI as active.

## 3. Investigation findings

### 3.1 Parent standard maturity

`BQ-RUNBOOK-STANDARD` Gate 1 is APPROVED at R9 (commit `365c198`, S486). The standard mandates §A–§K with prescribed agent forms (YAML frontmatter, capability tables, scenario YAML, repair YAML, evolve predicates, scenario_set with weighted scoring, lifecycle YAML, conformance YAML).

Standard §2 explicitly names the Infisical runbook as the initial reference implementation: *"Chosen because scope is small, the subsystem is critical, and there is no legacy document to retrofit — this isolates standard-conformance from migration risk."*

Council retrofit is therefore a parallel proving ground. Per **Q1 RESOLVED S529**, parallelism is permitted with constraint: the §J freshness telemetry mechanism (§10) gates final-conformance status until Infisical cutover lands. AG's R1 isolation concern is satisfied at the *final-conformance* tier; MP's R1 parallel-with-constraint framing is the *provisional-conformance* working state.

Gate 2 chunks for the parent standard (`BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1`, `-CHUNK-2`) appear in flight — chunk 1 covers infrastructure (`runbook-lint` design); chunk 2 covers D4+D5 deliverables.

### 3.2 Tooling state — UPDATED R2

MP probe S528 confirmed (replaces R1 §3.2 unverified hedging):
- `runbook-lint` v1.0.0 — functional via Click CLI invocation. Lints `tests/fixtures/conformant.md` cleanly (FAIL=0). Reports 19 failures on legacy `agent-dispatch.md` baseline. 20 checks defined in `runbook_tools/lint/checks.py:554-575`. **Important:** invocation is via the Click CLI entry point, NOT `python3 -m runbook_tools.cli` (the latter returns empty per R1 observation; the Click CLI is the real surface).
- `runbook-harness` — loads scenario YAML, dispatches MP, scores against expected-answer keys. Production use requires `KOSKADEUX_MCP_URL` env, dispatch token, and scenario YAML files at canonical path.

R2 LOCKS AC13 (lint FAIL=0) and AC14 (harness ≥ 0.80 weighted score) as real gates. Manual-lint and manual-harness fallbacks removed. **Q2 RESOLVED.**

### 3.3 Target runbook current state

| File | Current lines | Last touched | Schema conformance | Why-content | XAI/DeepSeek state |
|---|---|---|---|---|---|
| `agent-dispatch.md` | 232 | S527 | None (predates standard) | Operational mostly | Updated S527 to mention DeepSeek Server; XAI still listed as active |
| `council-gate-process.md` | ~150 | 2026-04-27 | None | Operational + some why | XAI listed as Council Member |
| `council-hall-deliberation.md` | ~200 | 2026-04-27 | None | Conceptual | DeepSeek "when out of read-only eval window"; XAI active |
| `council.md` | does not exist | n/a | n/a | n/a | n/a |

All three existing runbooks need (a) §A–§K restructure, (b) S528 Council-state currency, (c) strategic "why" content.

### 3.4 Source-of-truth references for "why" content

The strategic reasoning Max wants documented is partially captured already in:
- `infra:council-comms` v21 — graduation/retirement blocks, agent quirks, dispatch_patterns, review_order
- Memory edit #1 (S528-updated) — Council membership in compressed form
- This BQ's R1 spec — comparative analysis of MP vs AG vs DeepSeek vs XAI on each role
- Parent `BQ-COUNCIL-USAGE-REVIEW-S527` — quirks inventory

The retrofit must consolidate these into the §A–§K shape without losing the reasoning.

## 4. Proposed approach

### 4.1 Authoring agent

**Vulcan-direct R1 + R2.** Justification: Council documentation is meta-meta — the agents authoring it ARE the agents being documented. Vulcan has the full operational context; dispatching MP-author would require lengthy context-priming and risk drift on subtle reasoning. MP author cycle was used for parent `BQ-RUNBOOK-STANDARD` and is the canonical pattern for runbook structure work, but the Council scope is content-heavy not structure-heavy. **Q5 (per-chunk authoring agent) deferred to Gate 2 chunking spec.**

### 4.2 Strategic "why" depth

Literal naming, not euphemism. Per Max directive, replication value > soft-pedaling. Examples of language:
- ✅ "XAI fabricates line numbers in code audits (S499 confirmed: claimed `antigravity_cli_bridge.py:24`, real content is at line 25). Excluded from `gate3_post_build_audit` since S342."
- ❌ "XAI has been excluded from code audits due to reliability concerns."
- ✅ "DeepSeek graduated to full Council voter at S528 (day 2 of 14-day eval window) based on 94 dispatches with success_rate=1.0, verdict_agreement_with_primary=1.0, fabricated_line_reference_rate=0.0, statistical_record_floor crushed 4.7×."
- ❌ "DeepSeek demonstrated strong performance during evaluation."

**Q6 RESOLVED:** literal-why approved. Aligns with parent §C2 Agentic Support per AG INFO finding.

### 4.3 Cross-runbook content boundaries — REVISED PER H5 + Q7 RESOLVED

- **`council.md` is the index AND the canonical entry point.** §C defines `council_request` as the code entry point for Council operations. Hosts agent rosters, comparative reasoning, when-to-use guidance, replication sequencing, top-level scenario set covering full Council operation.
- **`agent-dispatch.md` is the mechanics.** §C describes its own architectural slice (dispatch backends, env requirements, agent quirks). **No back-reference to `council.md`'s `council_request` definition** — sub-runbook §C is slice-scoped and independently lintable.
- **`council-gate-process.md` is the gate flow.** §C describes BQ lifecycle internals (state entity shapes, gate transition events, cross-review-gate enforcement). No back-reference.
- **`council-hall-deliberation.md` is the deliberation pattern.** §C describes phase-1/2/3 internals (independent assessment → collection/synthesis → cross-pollination). No back-reference.

Per **H5**, sub-runbook §C tables MUST NOT reference `council.md` as a parent. Each is slice-scoped.

Cross-runbook *references* (when needed, e.g., `council-hall-deliberation.md` §G repair pattern citing a symptom from `agent-dispatch.md` §F) use file-qualified ID syntax for §F symptoms and §G repair patterns. Format: `<file-stem>:<id>` (e.g., `agent-dispatch:F-01`). Same-file references retain bare `<id>` form. Convention documented in §A `authoritative_scope` of each runbook.

### 4.4 §I scenario set strategy — REVISED PER M4 + Q3 RESOLVED

Council-as-one-system distribution (AG mandate accepted):

- **`council.md`:** ≥10 scenarios with full distribution per parent standard (≥3 §E, ≥3 §F, ≥2 §G, ≥2 §H, ≥1 ambiguous-symptom).
- **`agent-dispatch.md`:** ≥5 scenarios scoped to dispatch mechanics (≥2 §E, ≥1 §F, ≥1 §G, ≥1 §H or ambiguous).
- **`council-gate-process.md`:** ≥5 scenarios scoped to gate flow (same distribution).
- **`council-hall-deliberation.md`:** ≥5 scenarios scoped to deliberation pattern (same distribution).

Total scenarios: ≥25 across 4 runbooks. MP + AG concur on expected-answer keys before scenarios enter the harness set. DeepSeek concurrence deferred until `BQ-COUNCIL-DEEPSEEK-SPEC-AUTHORING-PARSE-FAILURE` ships (Q8).

Cross-file scenario references (e.g., a scenario in `council-hall-deliberation.md` that cites a symptom from `agent-dispatch.md`) use the AC8 file-qualified ID convention. No scenario sharing — each runbook's set is independently weighted and harness-scored.

### 4.5 Recommended Gate 2 chunking — REVISED PER H4 + L2 + Q4 RESOLVED

7 chunks total. Locked plan:

| Chunk | File / Cross-cut | Scope |
|---|---|---|
| C1 | `council.md` (NEW) | §A–§K authoring; ~150–200 lines; index + entry-point §C; primary scenario set ≥10 |
| C2 | `agent-dispatch.md` + retired-agents appendix | Existing 232 lines → §A–§K; XAI cold-storage appendix in §D or §K; ≥5 scenarios |
| C3 | `council-gate-process.md` | Existing ~150 lines → §A–§K; cross-review-gate enforcement in §C; ≥5 scenarios |
| C4 | `council-hall-deliberation.md` | Existing ~200 lines → §A–§K; 3-phase deliberation in §C; ≥5 scenarios |
| C5a | §I scenario sets (cross-cut) | All 4 §I sets authored together for consistency; MP+AG concur on expected-answer keys |
| C5b | Harness execution (cross-cut) | Run `runbook-harness` against each §I; require ≥ 0.80 weighted score per AC14 |
| C5c | §J + §K + final lint sweep (cross-cut) | Populate §J freshness telemetry per AC11; populate §K conformance YAML per AC12; all 4 pass `runbook-lint` FAIL=0 per AC13 |

By-§-section chunking rejected per L2 (per-file coherence; §C feeds §E feeds §F feeds §G within a file).

## 5. Acceptance Criteria — REVISED R2

**AC1.** 4 runbooks at `runbooks/{council.md,agent-dispatch.md,council-gate-process.md,council-hall-deliberation.md}` each contain §A–§K in order with no omissions.

**AC2.** §A YAML frontmatter present + valid (`system_name`, `purpose_sentence`, `owner_agent`, `escalation_contact`, `lifecycle_ref`, `authoritative_scope`, `linter_version`). **Per L1:** `authoritative_scope` defers live config authority to `infra:council-comms` Living State entity; runbook describes stable architecture + mechanics + reasoning.

**AC3.** [REVISED M1] §B Capability Matrix populated. Status from `{SHIPPED, PARTIAL, PLANNED, DEPRECATED, BROKEN}`. **For all non-`PLANNED` rows, a backing-code reference is required** (file:line OR fully-qualified symbol). PLANNED rows may omit backing code. No meta-meta capability claims without a code anchor.

**AC4.** §C Architecture table identifies components scoped per runbook. `council.md` treats the whole Council as one system; sub-runbooks scope to their dispatch/gate/deliberation slice (per H5: no back-references to `council.md`).

**AC5.** §D Agent Capability Map populated for each active agent (`mp`, `ag`, `deepseek`, `cc`, `vulcan`). Includes Operation, Skill/Tool, Auth Scope, Coverage Status. Retired XAI documented as `DEPRECATED` row in `agent-dispatch.md` §D with a pointer to `infra:council-comms.retired_agents.xai` cold-storage entry.

**AC6.** §E Operate scenarios contain all required fields per parent standard §4 (`id`, `trigger`, `pre_conditions`, `tool_or_endpoint`, `argument_sourcing`, `idempotency`, `expected_success`, `expected_failures`, `next_step_success`, `next_step_failure`).

**AC7.** §F Isolate symptom index covers ≥3 known Council failure modes per runbook (≥1 for sub-runbooks per AC10), including: AG progress-guard timeout (review-mode), MP READ-ONLY commit-during-review, dispatcher-stale-but-files-committed, AG line-number fabrication, gateway timeout, DeepSeek server `/health` failure, MCP tool prefix lowercase silent-fail.

**AC8.** [REVISED M3] §G Repair patterns for each §F symptom (retry, redispatch, manual escalation paths). Each §G entry references a §F entry by ID and a §C component by name. **Cross-runbook references use file-qualified ID syntax**: `<file-stem>:<id>` (e.g., `agent-dispatch:F-01` for symptom F-01 from `agent-dispatch.md` referenced from `council-hall-deliberation.md`). Same-file references retain bare `<id>` form. Convention defined in §A `authoritative_scope` text.

**AC9.** §H Evolve predicates classify Council change examples per `BREAKING|REVIEW|SAFE`: adding an agent, retiring an agent, changing dispatch participants, changing model frontiers, increasing $/dispatch cap, enabling write-mode for read-only agent.

**AC10.** [REVISED M4] §I scenario distribution:
- `council.md`: ≥10 scenarios (≥3 §E, ≥3 §F, ≥2 §G, ≥2 §H, ≥1 ambiguous-symptom)
- `agent-dispatch.md`, `council-gate-process.md`, `council-hall-deliberation.md`: ≥5 scenarios each (≥2 §E, ≥1 §F, ≥1 §G, ≥1 §H or ambiguous)

MP + AG concur on expected-answer keys before scenarios enter harness set. DeepSeek concurrence deferred (Q8). Weighted scoring per parent §I.

**AC11.** [REVISED H1, H3] §J Lifecycle YAML populated. Required fields:
- `last_refresh_session` (e.g., `S529`)
- `last_refresh_commit` (full SHA — the commit that last refreshed runbook content)
- `last_refresh_date` (ISO-8601)
- `first_staleness_detected_at` (ISO-8601, nullable; populated when an automated drift check first observes referenced infrastructure has changed)
- `refresh_triggers` (list)
- `scheduled_cadence`
- `last_harness_pass_rate` (≥ 0.80 per AC14)
- `last_harness_date`

§J doubles as the final-conformance gate per Q1 decision (mechanism in §10).

**AC12.** §K Conformance YAML populated: `linter_version`, `last_lint_run`, `last_lint_result`, `trace_matrix_path`, `word_count_delta`, `conformance_status` (`provisional` | `stale_provisional` | `final` per §10).

**AC13.** [REVISED H2] All 4 runbooks pass `runbook-lint` invoked via the Click CLI entry point (NOT `python3 -m runbook_tools.cli`) with FAIL=0. **Manual-lint fallback removed.** MP S528 probe confirmed lint v1.0.0 functional.

**AC14.** [REVISED H2] Harness execution against each §I scenario set produces weighted score ≥ 0.80. Production prerequisites documented in §K of each runbook: `KOSKADEUX_MCP_URL` env, dispatch token, scenario YAML files at canonical path. **Manual-harness fallback removed.**

**AC15.** "Why" content includes strategic reasoning literal-named:
- Why MP = primary reviewer (Codex-CLI automated; deeper wiring-gap detection per S526 Chunk 3B precedent)
- Why AG = cross-vote / secondary (Gemini 3.1 Pro frontier; line-number fabrication risk on code audits per S499)
- Why DeepSeek = full voter graduated S528 (94 dispatches, success_rate=1.0, verdict_agreement=1.0, fabricated_line_rate=0.0, SERVER-PARITY shipped capability completeness)
- Why XAI retired (line-number fabrication exclusion since S342; DeepSeek superseded the architecture-only niche)
- Why CC = fallback builder (300s MP Codex-CLI timeout safety net; Opus-tier reasoning for complex multi-file builds)

**AC16.** Retired-agents appendix in `agent-dispatch.md` documents XAI cold-storage state + reactivation runbook pointer to `infra:council-comms.retired_agents.xai.reactivation_runbook`.

**AC17.** Memory edit #1 + parent `infra:council-comms` cross-references updated to point to new runbook canonical paths (`council.md` as primary, sub-runbooks for details).

## 6. Open questions — RESOLUTION STATUS R2

**Q1 (Sequencing) — RESOLVED S529 (Max).** Decision: MP framing — parallel-with-constraint. Council runbook conformance authors and merges in parallel with Infisical reference; §J freshness telemetry (per AC11 fields) gates "final conformance" status until `last_refresh_commit` is at-or-after the Infisical cutover commit. "Provisional conformance" is the working state during Infisical migration. Mechanism in §10.

**Q2 (Tooling maturity) — RESOLVED S528 (MP probe).** `runbook-lint` v1.0.0 functional via Click CLI; lints conformant.md cleanly, reports 19 fails on legacy agent-dispatch.md baseline. `runbook-harness` loads YAML + dispatches MP + scores. AC13/AC14 locked as real gates per H2.

**Q3 (Scenario count) — RESOLVED S528 (AG mandate).** Council-as-one-system: `council.md` ≥10 scenarios full distribution; sub-runbooks ≥5 each scoped to slice. AC10 reflects.

**Q4 (Chunking) — RESOLVED S528 (AG+MP concur, R2 locks).** By-file chunking; C5 split into C5a/b/c → 7 chunks total. Plan locked in §4.5 table.

**Q5 (Authoring agent) — DEFERRED to Gate 2 chunking spec.** Per-chunk authoring agent (Vulcan-direct vs MP-author) decided at Gate 2 chunking spec author round. Vulcan-direct R1+R2 worked for this BQ.

**Q6 (Strategic "why" depth) — RESOLVED S528.** Literal naming approved. Aligns with Max S528 directive ("business rational" + reasoning) and AG INFO finding on §C2 Agentic Support purpose.

**Q7 (Cross-runbook §C linkage) — RESOLVED S528 (AG mandate).** Sub-runbook §C scopes to its own slice without back-references to `council.md`. Cross-runbook references for §F/§G use file-qualified ID syntax per AC8.

**Q8 (DeepSeek participation) — DEFERRED.** Pending `BQ-COUNCIL-DEEPSEEK-SPEC-AUTHORING-PARSE-FAILURE` resolution. R2 cross-vote falls back to AG single review. Re-engage DeepSeek concurrence for Gate 2 chunking R1 once parse-failure BQ ships.

## 7. Risks & mitigations — R2 update

- **R1 (Parent-standard amendment churn):** [unchanged from R1] If Infisical reference work surfaces standard defects, Council retrofit may need rework mid-build. Mitigation: explicit parent-defect-vs-Council-defect classification at Gate 3 audit; parent defects route to parent BQ.
- **R2 (Tooling immaturity blocks Gate 3):** **RESOLVED.** Tooling confirmed functional via MP S528 probe; AC13/AC14 locked as real gates.
- **R3 (§I scenario set scope creep):** **ADJUSTED.** Total scenarios now ≥25 (down from 40+ in R1) per Q3 mandate. C5a chunk dedicated to scenario authoring.
- **R4 (Why content drift):** [unchanged] Strategic reasoning may drift from `infra:council-comms` over time. Mitigation: cross-reference Living State as authoritative; runbooks summarize reasoning but defer to LS for mechanical state (per L1 §A scope language).
- **R5 (Vulcan-direct authoring fatigue):** [unchanged] Per-chunk per-session pacing.
- **R6 NEW (Infisical migration drift on §J telemetry):** §J `first_staleness_detected_at` requires drift detection. Mitigation: Vulcan or MP scans `infra:council-comms` cross-references against runbook content at session-open or on demand; mismatch sets `first_staleness_detected_at`. Final-conformance gate refuses "final" claim until cleared. Manual triggering acceptable for MVP; automation can land in a follow-up BQ.

## 8. Test plan (Gate 3 verification) — REVISED R2

For each runbook + each chunk:
- **T1 (lint).** `runbook-lint <file>` (Click CLI invocation) returns FAIL=0. **No manual fallback.**
- **T2 (harness).** `runbook-harness <file>` returns weighted score ≥ 0.80. **No manual fallback.**
- **T3 (XAI/DeepSeek state currency).** `grep -i "xai" <runbook>` shows only retired-agent appendix references; `grep -i "deepseek" <runbook>` shows full-voter language.
- **T4 (Living State currency).** `infra:council-comms` references match runbook §A `authoritative_scope` field (per L1).
- **T5 (cross-runbook linkage).** Cross-runbook references use file-qualified ID syntax per AC8. `council.md` references each sub-runbook by relative path; sub-runbooks DO NOT back-reference `council.md` per H5.
- **T6 NEW (§J freshness gate).** Final-conformance status requires `last_refresh_commit` at-or-after Infisical cutover commit. Provisional-conformance is the default during Infisical migration. Mechanism in §10.

## 9. Cross-review request — R2 closeout

R2 cross-review:
- **AG R2** (cross-vote, read-only review). Verifies the 12 R1 findings + Max Q1 decision are correctly folded. Single-pass concurrence sufficient for Gate 1 close.
- **MP R2:** NOT required — MP authored 7 of 12 findings; folding R2 with MP cross-vote would be self-review. MP rejoins at Gate 2 chunking spec R1.
- **DeepSeek R2:** DEFERRED per Q8.

If AG R2 returns APPROVE clean: Gate 1 closes; proceed to Gate 2 chunking spec author. If APPROVE_WITH_NITS: micro-fold + Vulcan-direct R3 final.

## 10. §J Freshness Telemetry — Final-Conformance Mechanism (NEW R2)

Per **Q1 RESOLVED S529** (Max chose MP framing), this BQ proceeds in parallel with Infisical reference implementation. The §J freshness telemetry mechanism gates final-conformance status as follows:

**Provisional conformance** (default during Infisical migration):
- All §A–§K structurally complete per AC1–AC17.
- Lint passes (AC13). Harness passes (AC14).
- §J `last_refresh_commit` populated with the commit SHA at time of authoring.
- §J `first_staleness_detected_at` is `null` (no drift detected yet).
- §K `last_lint_run`, `last_lint_result` populated.
- §K `conformance_status`: `provisional`.

**Final conformance** (post-Infisical cutover):
- All provisional conditions hold.
- §J `last_refresh_commit` SHA is at-or-after the Infisical cutover commit on the Living State `infra:council-comms` entity OR the parent `BQ-RUNBOOK-STANDARD` cutover marker.
- §J `first_staleness_detected_at` is `null` (no drift since last refresh) OR has been re-cleared after a refresh commit.
- §K `conformance_status`: `final`.

**Stale provisional** (drift detected during Infisical migration):
- Provisional conditions previously held.
- Drift detection (manual scan or automated) has set §J `first_staleness_detected_at`.
- §K `conformance_status`: `stale_provisional`.
- Triage: refresh runbook content against current `infra:council-comms` state, commit, clear `first_staleness_detected_at`, return to `provisional`.

**Drift detection** (during Infisical migration):
- Vulcan or MP scans `infra:council-comms` cross-references against each runbook's content at session-open or on demand.
- Mismatch sets §J `first_staleness_detected_at` to current ISO-8601 timestamp.
- §K `conformance_status` downgrades to `stale_provisional` until next refresh commit.

This mechanism resolves the parent-standard §2 isolation concern by making the conformance state explicitly auditable rather than implicitly provisional. AG's R1 mandate (sequential after Infisical) is satisfied at the *final-conformance* tier; MP's R1 framing (parallel-with-constraint) is the *provisional-conformance* working state. The §J telemetry fields per AC11 are the auditable primitives.

---
**End of Gate 1 R2 spec.** Awaiting AG R2 cross-vote (read-only) for Gate 1 close, then Gate 2 chunking spec author.
