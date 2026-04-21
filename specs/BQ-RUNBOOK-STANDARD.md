# BQ-RUNBOOK-STANDARD — System-Wide Runbook Standard

**Status:** Gate 1 R1 (design, under review)
**Priority:** P0
**Repo:** aidotmarket/runbooks
**Parent of:** BQ-CRM-RUNBOOK-STANDARD (reference implementation), future per-system runbook BQs
**Authored:** S486 (Vulcan)

---

## 1. Purpose

Define the system-wide standard every runbook in the ai.market ecosystem must meet so that both human operators and agentic support can:

1. **Operate** — use the system's tools to serve customers (human and agentic)
2. **Isolate** — diagnose issues from symptoms to root causes
3. **Repair** — fix problems with direct references to code
4. **Evolve** — extend the system without violating architectural invariants

A runbook is legible when a stateless agent, given only this runbook and no prior context, can produce a correct first action on any defined operational scenario.

## 2. Scope

**In scope:** All system-level runbooks in `aidotmarket/runbooks/`, including:
- CRM (`crm-target-state.md` — reference implementation)
- AIM Node (pip-installable P2P compute utility; seller + buyer modes)
- AIM Channel / vectorAIz (dual-brand desktop app)
- allAI (embedded AI agent)
- Koskadeux (session orchestration, Council dispatch, Living State)
- Infisical (secrets)
- Railway (deploy, database, proxy, Tailscale Funnel)
- GitHub Actions / CI
- Alembic migrations
- Backup pipeline

**Out of scope:** Per-BQ specs (which live in the owning repo's `specs/`), product marketing docs, per-feature READMEs aimed at developer onboarding rather than operation.

## 3. Consumer Model

Every runbook identifies three consumer classes explicitly:

**C1 — Human Operator:** support, ops, or engineering doing diagnosis, manual intervention, or onboarding. Assumed to read top-to-bottom when onboarding, then jump via ToC when triaging.

**C2 — Agentic Support:** Claude / MP / AG / XAI / any future agent. Assumed to be stateless — each request starts from zero context; the runbook is the entire working memory for that system during the session.

**C3 — Escalation:** when the primary consumer (human or agent) cannot resolve, where do they hand off? Named human, named Slack channel, or named parent runbook.

Consumer-specific affordances (the runbook is correct only if it serves all three):
- Agentic consumers need exact tool names, argument shapes, expected return shapes, failure signatures — not prose descriptions.
- Human consumers need scannable structure, visual hierarchy, and narrative for novel situations.
- Both need confidence surfaces (§5).

## 4. Mandatory Sections

Every runbook under this standard contains the following sections, in order. Sections can be extended but not omitted or renamed.

### §A. Header
- System name
- One-sentence purpose
- Owner agent(s) + escalation contact
- Last-refresh session + commit SHA
- Authoritative scope (what this runbook IS the source of truth for)

### §B. Capability Matrix
Table with columns:

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |

Status values: `SHIPPED`, `PARTIAL`, `PLANNED`, `DEPRECATED`, `BROKEN`.

Every row must cite a code path (file:function or module). `SHIPPED` without a backing-code reference is a runbook defect. `Last Verified` cites the session ID of the verification.

### §C. Architecture & Interactions
- Component overview (services, storage, external dependencies)
- Integration surface: which other systems this one reads from / writes to, with interface references (endpoints, queue names, file paths)
- Data flow: textual description of primary request paths, sufficient for an agent to reason about side effects
- Diagrams optional (encouraged for human consumers; agents cannot parse visual-only diagrams, so prose must stand alone)

### §D. Agent Capability Map
- Which agents can perform which operations on this system
- Skill/tool-to-feature mapping
- Gap analysis: where agent coverage is incomplete and what would close it
- Auth/authz surface for agentic callers (tokens, scopes, rate limits)

### §E. Operate — Serving Customers
Scenario-based. For each common operational scenario:
- **Trigger** — what the customer or upstream system is asking
- **Tool or endpoint to use** — with exact argument shape
- **Expected success signal** — return shape, side effects, where to verify
- **Expected failure modes** — with signatures
- **Next step** on success / on failure

Covers both human-initiated (support ticket, ops request) and agent-initiated (allAI triage, scheduled job, cross-system call) flows.

### §F. Isolate — Diagnosing Issues
- Symptom index: `symptom → probable causes → verification procedure`
- Log locations, trace IDs, metric dashboards
- Known failure modes with exact error signatures (log-line patterns, HTTP status codes, exception types)

### §G. Repair — Fixing Problems
For each known failure mode in §F:
- Root cause
- File path + function-level entry point
- Specific change pattern (semantic description, not a diff)
- Rollback procedure
- Data integrity check to confirm repair

### §H. Evolve — Extending the System
- **Invariants:** properties that must NOT change without re-architecting (e.g., "non-custodial", "sellers retain ≥ X% of GMV", "all secrets via Infisical")
- **Change-class decision tree:**
  - `SAFE` — bugfix, doc update, test add; no review required
  - `REVIEW` — new feature or refactor within invariants; Council review required
  - `BREAKING` — changes an invariant or public contract; full BQ required
- How to add new capabilities without violating invariants

### §I. Acceptance Criteria (for the runbook itself)
- Defined scenario list (minimum 5, recommended 10+) covering common operate/isolate/repair cases
- **Stateless-agent-correctness test:** given only this runbook, a fresh agent with `allowed_tools=[Read,Grep,Glob,LS]` restricted to this runbook file must produce a correct first action on ≥80% of scenarios
- How the test is run (MP dispatch procedure, scoring rubric)

### §J. Lifecycle
- Refresh cadence (what triggers an update: BQ completion, gate approval, incident)
- Last-refresh session and commit SHA
- Owner agent for refresh cycles
- Link back to the runbook index (cross-runbook discovery)

## 5. Confidence Surface

A runbook is either authoritative or not for a given claim. §B capability-matrix status cells cannot be trusted unless they include `Last Verified` (session ID) AND backing-code reference. Cells written at planning time and never reverified are explicitly marked `UNVERIFIED` until checked.

Every §F symptom and §G repair procedure carries a confidence tag:
- `CONFIRMED` — observed in production, repair verified
- `HYPOTHESIZED` — plausible from code review, unverified in production
- `DEPRECATED` — documented for historical completeness, no longer applicable

## 6. Runbook Index

`aidotmarket/runbooks/README.md` is the authoritative index, listing:
- All runbooks under this standard
- Status (up-to-standard / migrating / not-yet-adopted)
- Last refresh session + commit SHA
- Owner agent

The index itself conforms to a micro-version of this standard (§A header + table of runbooks + §J lifecycle entry).

## 7. Acceptance Criteria for this BQ

**G1 — Gate 1 (spec) AC:** MP R1 review verdict APPROVE or APPROVE_WITH_NITS. AG cross-vote concurs on consumer-first framing. Both sign off that §4 mandatory sections cover operate/isolate/repair/evolve with agent-executable detail.

**G2 — Gate 2 (implementation spec) AC:**
- Runbook index `README.md` under this standard exists and lists existing + planned runbooks
- `crm-target-state.md` retrofitted to cite parent BQ-RUNBOOK-STANDARD and reorganized to §4 section structure (no content loss, structural mapping only)
- Migration plan documents sequence for remaining systems with owner assignment

**G3 — Gate 3 (code audit) AC:** Stateless-agent harness test passes on the CRM reference implementation at ≥80% first-action accuracy on a defined ≥10-scenario set.

**G4 — Gate 4 (production) AC:** A second runbook (recommend AIM Node) is authored by Vulcan using only this standard as input, and passes MP R1 on first submission. This is the falsifiability test: the standard is real only if a new runbook built against it gets ratified on first pass.

## 8. Open Questions (for R2 refinement)

**Q1 (§I AC):** Automated stateless-agent test harness vs. manual per-refresh check. Automated is more rigorous but requires the harness itself to be built (becomes a dependency). Recommend: automated as G3 AC (Gate 3 depends on harness existing); manual acceptable for Gate 1–2.

**Q2 (§H change-class tree):** Per-system or universal. Per-system is more accurate because invariants differ by system. Recommend: universal shell defined in this standard (SAFE / REVIEW / BREAKING), per-system content listing what falls in each class.

**Q3 (§C diagrams):** Does the standard mandate diagrams? Agents cannot parse visual-only content, so prose must be complete. Recommend: prose mandatory, diagrams optional-but-encouraged.

**Q4 (§B PARTIAL semantics):** Proposed definition — "shipped but known to have one or more listed defects in §F, or shipped for a subset of documented use cases." Accept or refine?

**Q5 (§E vs §F separation):** MP may argue operate/isolate are not cleanly separable. Proposed: §E covers expected paths (success scenarios with their anticipated failure branches); §F covers diagnosis of deviations that land outside any §E branch. Accept or refine?

**Q6 (Gate 2 retrofit risk):** Retrofitting `crm-target-state.md` to §4 structure is non-trivial — the existing document is at R5 with substantial content. Risk: structural reorg drops context in translation. Mitigation: MP reviews the retrofit diff for content preservation. Accept or propose stronger?

## 9. Migration Plan (Gate 2 preview)

1. **Retrofit CRM as reference:** `crm-target-state.md` mapped to §4 structure. Existing §2-§7 maps to §B-§J with minimal loss.
2. **Create runbook index:** `aidotmarket/runbooks/README.md` listing all adoption targets with status.
3. **Author AIM Node runbook from scratch** using this standard as sole input. This is the G4 falsifiability test.
4. **Backfill remaining systems** in this order (rationale: highest operational impact first):
   - Koskadeux (session + council — most frequently used by agents)
   - AIM Channel / vectorAIz
   - allAI
   - Railway + Infisical (infra)
   - GitHub Actions / CI
   - Alembic migrations
   - Backup pipeline

Each per-system runbook is a child BQ under this parent, with its own Gate 1–4 cycle.

## 10. Non-goals

- This BQ does not dictate per-system content — it dictates structure, consumer model, and acceptance criteria.
- This BQ does not change the existing Gate 1 APPROVED status of BQ-CRM-RUNBOOK-STANDARD; the CRM runbook's content becomes the reference implementation; its child-BQ relationship to this parent is established in Gate 2.
- This BQ does not specify the Gate 2 build order beyond the §9 migration plan preview.

## 11. Review Targets

**MP R1 (primary review, read-only):** structural rigor of §4 mandatory sections. Does the schema actually support operate/isolate/repair/evolve for agents? Are AC in §7 testable? Are invariants in §H adequately defined as a concept (even though per-system content is out of scope)?

**AG cross-vote (after MP):** consumer-first framing. Does §3 consumer model actually produce runbooks readable by stateless agents? Does §E scenario structure capture agent-initiated flows as well as human-initiated? Is §5 confidence surface adequate?

**Out of review scope for R1:** automated harness design, per-system invariant catalogs, Gate 2 migration details beyond the §9 preview.
