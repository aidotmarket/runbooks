# BQ-COUNCIL-RUNBOOK-CONFORMANCE — Gate 1 Design Spec (R1)

**Status:** Gate 1 R1 authoring (vulcan-direct)
**Parent BQ:** `build:bq-runbook-standard` (Gate 1 APPROVED R9 at S486 commit `365c198`, Gate 2 chunks 1+2 in flight)
**Authored:** S528 by Vulcan
**Filed-from directive:** Max S528 — "Make sure our runbooks are updated on the current configurations (the why and the how) of the council. Include our reasoning. The runbooks should allow a new model to fully understand the council, our process and why we have it configured this way, such that they could replicate it as well as fully understand the technical implementation and business rational."
**Shape selection:** Max S528 — "Full standard conformance — restructure all three plus the new index to §A–§G, runbook-lint passing. Multi-chunk Gate 1/2/3 build, several sessions."

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

**Standard §2 explicitly names the Infisical runbook as the initial reference implementation:** *"Chosen because scope is small, the subsystem is critical, and there is no legacy document to retrofit — this isolates standard-conformance from migration risk."*

Council retrofit is therefore a parallel proving ground, not the primary one. **This is a sequencing decision (Q1 below).**

Gate 2 chunks for parent standard (`BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1`, `-CHUNK-2`) appear in flight — chunk 1 covers infrastructure (`runbook-lint` design); chunk 2 covers D4+D5 deliverables. Whether they are merged-to-main + tooling end-to-end-verified is not yet confirmed empirically.

### 3.2 Tooling state

Surveyed at S528:
- `runbook_tools/cli.py` — 19,569 bytes, exists. `python3 -m runbook_tools.cli --help` returned empty (no argparse or printing). Stub or under-implemented.
- `runbook_tools/lint/`, `runbook_tools/parser/`, `runbook_tools/scaffold/`, `runbook_tools/harness/` — directories exist with content but end-to-end behavior unverified by this BQ's authoring session.
- No prior runbook in the repo has been validated as runbook-lint-passing. There is no demonstrated baseline.

**Conformance verification path is therefore not yet automated.** Either (a) Council retrofit waits for runbook-lint to reach usable maturity (Q2 dependency), or (b) Council proceeds with manual lint-pass criteria + best-effort schema conformance per chunk.

### 3.3 Target runbook current state

| File | Current lines | Last touched | Schema conformance | Why-content | XAI/DeepSeek state |
|---|---|---|---|---|---|
| `agent-dispatch.md` | 232 | S527 (today) | None (predates standard) | Operational mostly | Updated S527 to mention DeepSeek Server; XAI still listed as active |
| `council-gate-process.md` | ~150 | 2026-04-27 | None | Operational + some why | XAI listed as Council Member |
| `council-hall-deliberation.md` | ~200 | 2026-04-27 | None | Conceptual | DeepSeek "when out of read-only eval window"; XAI active |
| `council.md` | does not exist | n/a | n/a | n/a | n/a |

All three existing runbooks need (a) §A–§K restructure, (b) S528 Council-state currency, (c) strategic "why" content.

### 3.4 Source-of-truth references for "why" content

The strategic reasoning Max wants documented is partially captured already in:
- `infra:council-comms` v21 — graduation/retirement blocks, agent quirks, dispatch_patterns, review_order
- Memory edit #1 (S528-updated) — Council membership in compressed form
- This session's Vulcan opinion (S528 turn 5) — comparative analysis of MP vs AG vs DeepSeek vs XAI on each role
- Parent `BQ-COUNCIL-USAGE-REVIEW-S527` — quirks inventory

The retrofit must consolidate these into the §A–§K shape without losing the reasoning.

## 4. Proposed approach

### 4.1 Authoring agent

**Vulcan-direct R1 + R2.** Justification: Council documentation is meta-meta — the agents authoring it ARE the agents being documented. Vulcan has the full operational context; dispatching MP-author would require lengthy context-priming and risk drift on subtle reasoning (e.g., why XAI was retired despite the architecture niche). MP author cycle was used for parent `BQ-RUNBOOK-STANDARD` and is the canonical pattern for runbook structure work, but the Council scope is content-heavy not structure-heavy. (Open question Q5 for Council to override.)

### 4.2 Strategic "why" depth

Literal naming, not euphemism. Per Max directive, replication value > soft-pedaling. Examples of language:
- ✅ "XAI fabricates line numbers in code audits (S499 confirmed: claimed `antigravity_cli_bridge.py:24`, real content is at line 25). Excluded from `gate3_post_build_audit` since S342."
- ❌ "XAI has been excluded from code audits due to reliability concerns."
- ✅ "DeepSeek graduated to full Council voter at S528 (day 2 of 14-day eval window) based on 94 dispatches with success_rate=1.0, verdict_agreement_with_primary=1.0, fabricated_line_reference_rate=0.0, statistical_record_floor crushed 4.7×."
- ❌ "DeepSeek demonstrated strong performance during evaluation."

(Open question Q6 for Council to override or refine.)

### 4.3 Cross-runbook content boundaries

- `council.md` is the *index*. Contains the agent rosters, comparative reasoning, when-to-use guidance, sequencing of how-to-replicate. Cross-references the other three for operational details.
- `agent-dispatch.md` is the *mechanics*. Contains tool signatures, auth, env, quirks, dispatch protocols, retired-agents appendix.
- `council-gate-process.md` is the *gate flow*. BQ lifecycle, Gate 1–4 semantics, cross-review-gate enforcement, dispatch-binding tokens for author-mode.
- `council-hall-deliberation.md` is the *deliberation pattern*. Phase 1/2/3 deliberation, when to invoke, output schemas.

§C Architecture tables in the 3 sub-runbooks reference `council.md` as their parent index where overlap exists, with per-runbook-scoped components. (Q7 for Council to refine.)

### 4.4 §I scenario set strategy

Standard mandates ≥10 scenarios per runbook with distribution (≥3 §E, ≥3 §F, ≥2 §G, ≥2 §H, ≥1 ambiguous). 4 runbooks × 10 = 40+ scenarios minimum.

Cross-reference rule: scenarios may reference shared §C components but each runbook's scenario set is independently weighted and harness-scored. No scenario sharing across files. (Q3 for Council to confirm.)

DeepSeek participates as a 3rd reviewer on the expected-answer key concurrence step (replacing the standard's "MP+AG must concur" with "MP+AG+DeepSeek must concur"). First spec-authoring participation post-graduation S528. (Q8.)

### 4.5 Recommended Gate 2 chunking

Five chunks, scoped by file + cross-cut acceptance:

- **C1 — `council.md` authoring** (NEW file). The index runbook. ~150–200 lines authored fresh against §A–§K. Highest strategic-reasoning density.
- **C2 — `agent-dispatch.md` restructure + retired-agents appendix.** Existing 232 lines reorganized into §A–§K. New "Retired Agents" appendix in §C or §D for XAI cold-storage. Updates dispatcher, quirks, env-requirements.
- **C3 — `council-gate-process.md` restructure.** BQ lifecycle + 4 gates + cross-review-gate. §C shows Living State key shapes for `build:bq-*` entities.
- **C4 — `council-hall-deliberation.md` restructure.** 3-phase deliberation. §E scenarios cover "when to invoke Council Hall" decision points.
- **C5 — §I scenario sets (cross-cut) + harness verification + lint pass.** All 4 runbook §I sets authored together for consistency. Run runbook-lint against each. Run harness against each scenario set. Patch §J lifecycle + §K conformance with results.

Alternative chunking (by §-section across files, e.g., "all §A–§D for all 4 files in chunk 1") is rejected because each runbook's content is highly interdependent within its file (e.g., §C components feed §E scenarios feed §F symptoms feed §G repairs); cross-file §-section batching fragments coherence per chunk. (Q4 for Council to refute.)

## 5. Acceptance Criteria

**AC1.** 4 runbooks at `runbooks/{council.md,agent-dispatch.md,council-gate-process.md,council-hall-deliberation.md}` each contain §A–§K in order with no omissions.

**AC2.** §A YAML frontmatter present + valid (`system_name`, `purpose_sentence`, `owner_agent`, `escalation_contact`, `lifecycle_ref`, `authoritative_scope`, `linter_version`).

**AC3.** §B Capability Matrix populated. Status values from `{SHIPPED, PARTIAL, PLANNED, DEPRECATED, BROKEN}`. Backing-code reference present for non-`PLANNED` rows.

**AC4.** §C Architecture table identifies components scoped per runbook. `council.md` treats the whole Council as one system; sub-runbooks scope to their dispatch/gate/deliberation slice.

**AC5.** §D Agent Capability Map populated for each active agent (`mp`, `ag`, `deepseek`, `cc`, `vulcan`). Includes Operation, Skill/Tool, Auth Scope, Coverage Status. Retired XAI documented as `DEPRECATED` row with a pointer to the cold-storage entry.

**AC6.** §E Operate scenarios contain all required fields per parent standard §4 (`id`, `trigger`, `pre_conditions`, `tool_or_endpoint`, `argument_sourcing`, `idempotency`, `expected_success`, `expected_failures`, `next_step_success`, `next_step_failure`).

**AC7.** §F Isolate symptom index covers ≥3 known Council failure modes per runbook, including: AG progress-guard timeout (review-mode), MP READ-ONLY commit-during-review, dispatcher-stale-but-files-committed, AG line-number fabrication, gateway timeout, DeepSeek server `/health` failure, MCP tool prefix lowercase silent-fail.

**AC8.** §G Repair patterns for each §F symptom (retry, redispatch, manual escalation paths). Each §G entry references a §F entry by ID and a §C component by name.

**AC9.** §H Evolve predicates classify Council change examples per `BREAKING|REVIEW|SAFE`: adding an agent, retiring an agent, changing dispatch participants, changing model frontiers, increasing $/dispatch cap, enabling write-mode for read-only agent.

**AC10.** §I scenario set ≥10 scenarios per runbook with required distribution (≥3 §E, ≥3 §F, ≥2 §G, ≥2 §H, ≥1 ambiguous-symptom). MP + AG + DeepSeek concur on expected-answer keys before scenarios enter harness set. Weighted scoring per parent §I.

**AC11.** §J Lifecycle YAML populated: `last_refresh_session=S528+`, refresh triggers list, scheduled cadence, `last_harness_pass_rate ≥ 0.80`, `last_harness_date`.

**AC12.** §K Conformance YAML populated: `linter_version`, `last_lint_run`, `last_lint_result`, `trace_matrix_path`, `word_count_delta`.

**AC13.** All 4 runbooks pass `runbook-lint` with FAIL=0. (Conditional on Q2 tooling-maturity resolution — see Q2.)

**AC14.** Harness execution against each §I scenario set produces weighted score ≥ 0.80. (Conditional on harness maturity per parent BQ.)

**AC15.** "Why" content includes strategic reasoning literal-named:
- Why MP = primary reviewer (Codex-CLI automated; deeper wiring-gap detection per S526 Chunk 3B precedent)
- Why AG = cross-vote / secondary (Gemini 3.1 Pro frontier; line-number fabrication risk on code audits per S499)
- Why DeepSeek = full voter graduated S528 (94 dispatches, success_rate=1.0, verdict_agreement=1.0, fabricated_line_rate=0.0, SERVER-PARITY shipped capability completeness)
- Why XAI retired (line-number fabrication exclusion since S342; DeepSeek superseded the architecture-only niche)
- Why CC = fallback builder (300s MP Codex-CLI timeout safety net; Opus-tier reasoning for complex multi-file builds)

**AC16.** Retired-agents appendix in `agent-dispatch.md` documents XAI cold-storage state + reactivation runbook pointer to `infra:council-comms.retired_agents.xai.reactivation_runbook`.

**AC17.** Memory edit #1 + parent `infra:council-comms` cross-references updated to point to new runbook canonical paths (`council.md` as primary, sub-runbooks for details).

## 6. Open questions for Council cross-review

**Q1 (Sequencing).** Parallel to Infisical reference implementation, or sequential-after?
- Parallel: risks discovering parent-standard defects late in Council Gate 2/3, forcing rework.
- Sequential: delays Council documentation by potentially-multiple weeks.
- **Vulcan recommendation:** parallel, with explicit Council-vs-Standard-defect boundary. If Council Gate 2/3 surfaces a parent-standard defect, file as parent-BQ amendment rather than blocking Council chunk completion.

**Q2 (Tooling maturity).** Does runbook-lint actually work end-to-end?
- CLI returned empty `--help`. Lint subpackage unverified.
- AC13 (lint pass) and AC14 (harness pass) depend on usable tooling.
- **Vulcan recommendation:** Council Chunk 1 (council.md) doubles as the *first* lint smoke test. If lint fails to validate Chunk 1, file blocker BQ against parent's Gate 2; convert AC13/AC14 to manual-lint pass criteria as fallback. Decision deferred until empirical Chunk 1 lint attempt.

**Q3 (Scenario count).** 40+ scenarios across 4 runbooks reasonable?
- Standard mandates ≥10 per runbook.
- Some scenarios are inherently shared subject matter (e.g., "how to dispatch a review" appears in council.md overview AND agent-dispatch.md mechanics).
- **Vulcan recommendation:** No scenario sharing across files. Each runbook's set is independent + harness-scored. Cross-file references via §C components only. Total: 40+ scenarios. (Council may refute.)

**Q4 (Chunking).** §4.5 above proposes 5 chunks (1 per file + 1 cross-cut for §I/lint/harness). Alternative: chunk by §-section.
- **Vulcan recommendation:** by-file chunking (§4.5 plan). By-§-section fragments per-file coherence.

**Q5 (Authoring agent).** Vulcan-direct vs MP-author for each chunk's R1?
- Vulcan-direct R1+R2 worked well for `BQ-COUNCIL-AG-PROGRESS-GUARD-FIX` (S528).
- MP-author was used for parent `BQ-RUNBOOK-STANDARD` Gate 1 (R1–R8) — canonical for runbook-structure work.
- **Vulcan recommendation:** Vulcan-direct for content authoring. Council content is meta-meta and Vulcan has full context. MP becomes spec-reviewer (primary) + chunk builder if any chunks have implementation work (e.g., harness wiring for §I).

**Q6 (Strategic "why" depth).** Literal naming of sharp edges (XAI fabrication, etc.) vs softer language?
- **Vulcan recommendation:** literal-name everything. Replication value > internal politics. Max explicitly asked for "business rational" — that means evidence-grounded reasoning, not euphemism.

**Q7 (Cross-runbook §C linkage).** Sub-runbook §C tables reference `council.md` as parent, or duplicate?
- Cross-reference cleaner; lint may not validate cross-file references (depends on tooling maturity).
- **Vulcan recommendation:** cross-reference with `council.md` as canonical parent. Each sub-runbook §C scopes to its slice. Tooling deficiency (if any) addressed in parent BQ-RUNBOOK-STANDARD.

**Q8 (DeepSeek participation).** First spec-authoring cross-review post-graduation. Establishes 3-reviewer concurrence pattern.
- **Vulcan recommendation:** dispatch DeepSeek as 3rd cross-reviewer on this Gate 1 R1 spec. If DeepSeek contributes meaningfully, lock in 3-reviewer concurrence for all subsequent Gate 1/2 reviews. If contribution is shallow, downgrade DeepSeek to 2-reviewer fallback only.

## 7. Risks & mitigations

- **R1: Parent-standard amendment churn.** If Infisical reference work surfaces standard defects, Council retrofit may need re-work mid-build. Mitigation: explicit parent-defect-vs-Council-defect classification at Gate 3 audit. Parent defects route to parent BQ.
- **R2: Tooling immaturity blocks Gate 3 conformance.** Mitigation: AC13/AC14 conditional on tooling maturity. Manual-lint criteria fallback authored at Gate 2 chunking.
- **R3: §I scenario set scope creep.** 40+ scenarios with MP+AG+DeepSeek expected-answer-key concurrence is significant work. Mitigation: scenario authoring = Chunk 5 cross-cut, allows other chunks to ship independently if scenario authoring stalls.
- **R4: "Why" content drift.** Strategic reasoning may drift from `infra:council-comms` over time. Mitigation: cross-reference Living State as authoritative; runbooks summarize reasoning but defer to LS for mechanical state.
- **R5: Vulcan-direct authoring fatigue.** 4 runbooks of substantial content is a lot for one Vulcan. Mitigation: chunk-by-chunk, one file per session, acceptance per chunk.

## 8. Test plan (Gate 3 verification)

For each runbook + each chunk:
- **T1 (lint).** `runbook-lint <file>` returns FAIL=0. If lint not yet usable, manual schema-spot-check per AC1–AC12.
- **T2 (harness).** `runbook-harness <file>` returns weighted score ≥ 0.80. If harness not yet usable, manual scenario-walkthrough by MP+AG+DeepSeek.
- **T3 (XAI/DeepSeek state currency).** `grep -i "xai" <runbook>` shows only retired-agent appendix references; `grep -i "deepseek" <runbook>` shows full-voter language.
- **T4 (Living State currency).** `infra:council-comms` references match runbook §A `authoritative_scope` field.
- **T5 (cross-runbook linkage).** `council.md` references each sub-runbook by relative path; sub-runbooks reference `council.md` as parent in §C.

## 9. Cross-review request (R1)

Recommended dispatch:
- **AG R1** (cross-vote secondary, breadth) — focus on §C/§D structure feasibility, scenario distribution, AC completeness.
- **MP R1** (primary reviewer, depth) — focus on §A/§K schema rigor, parent-standard alignment, tooling-maturity blocker assessment, sequencing risk.
- **DeepSeek R1** (3rd reviewer, first post-graduation) — focus on strategic-reasoning rigor, scenario realism, cross-runbook coherence, identification of any sharp edges Vulcan glossed over.

R1 cross-review prompt requires READ-ONLY discipline, max 5 findings each, cite specific spec lines/sections in findings.

---
**End of Gate 1 R1 spec.** R2 will fold cross-review mandates after Council convergence.
