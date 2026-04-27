# Council & Gate Process Runbook

How code gets reviewed, approved, and shipped through the Build Queue system.

## Council Members

| Agent | Engine | Role | Dispatch |
|-------|--------|------|----------|
| **MP** | OpenAI Codex CLI (gpt-5.5) | Primary builder + mandatory reviewer | `council_request agent=mp` or `dispatch_mp_build` |
| **AG** | Gemini CLI (gemini-3.1-pro-preview, Vertex AI) | Secondary builder + reviewer | `council_request agent=ag` |
| **XAI** | Grok CLI (grok-4-1-fast-reasoning, TENTATIVE) | Challenger reviewer (excluded from code audits — fabricates line numbers) | `council_request agent=xai` |
| **DeepSeek** | DeepSeek API direct (deepseek-v4-pro, frontier-only S516) | **READ-ONLY voter during 14-day eval window (active 2026-04-27 → ~2026-05-11). Full Council parity in flight under BQ-COUNCIL-DEEPSEEK-SERVER-PARITY (Gate 1 APPROVED S516).** | `council_request agent=deepseek` |
| **CC** | Claude Code (claude-opus-4-7) | Builder only (no `gh` in PATH, can't do VZ releases) | `council_request agent=cc` |
| **Vulcan** | Claude Opus 4.7 (this agent) | Session orchestrator, dispatches all work, manages state | Direct in session |

### Key Rules

- **MP is mandatory on ALL reviews** — always dispatch MP first
- **AG defaults to ACTION** — include "READ-ONLY" in task for non-build work
- **XAI excluded from code audits** — use for design reviews, not line-by-line code
- **AG and MP run on separate mutexes** — can run in parallel
- **MP serializes via fcntl** — only one MP task at a time
- Always use `state_get("infra:council-comms")` for current agent config
- **Frontier-only model policy (S516):** Each Council agent runs exactly one configured model — the current provider frontier. Source of truth: `infra:council-comms.model_policy.agent_frontier_models`. No fast/cheap variants in production dispatch; no silent downgrades. See `agent-dispatch.md` for dispatch path detail and `BQ-MODEL-REGISTRY-CENTRALIZATION` (P1) for systemic enforcement
- **DeepSeek read-only during eval window:** DeepSeek is `read_only=true` enforced at three layers (router, DeepSeek client, XAI client) via `eval_active.is_deepseek_eval_active()`. Do NOT attempt to bypass during eval window

## Build Queue (BQ) System

Every feature, fix, or infrastructure change goes through the BQ gate system. A BQ item is tracked in Living State as `build:bq-{name}`.

### Gate System

```
Gate 1 (Design Review) → Gate 2 (Implementation Spec) → Gate 3 (Code Audit) → Gate 4 (Production Verification)
```

#### Gate 1 — Design Review

**What:** High-level design review. Is this the right thing to build? Does it fit the architecture?
**Who reviews:** MP (mandatory), optionally AG or XAI for second opinions
**Outcomes:** `APPROVED`, `APPROVED_WITH_MANDATES`, `REJECTED`
**Artifacts:** Problem statement, what ships, estimated hours, dependencies

#### Gate 2 — Implementation Spec

**What:** Detailed implementation specification. File-by-file changes, migration plans, test requirements.
**Who reviews:** MP (mandatory)
**Outcomes:** `APPROVED`, `APPROVED_WITH_MANDATES`, `REJECTED`
**Artifacts:** Spec file in `specs/BQ-{NAME}-GATE2.md` with file list, schema changes, test plan

**Important:** After Gate 2 passes on a BQ that had Gate 1 `APPROVED_WITH_MANDATES`, patch `gate1.status` to `APPROVED` before dispatching builds. Otherwise the compliance gate blocks.

#### Gate 3 — Code Audit

**What:** Post-build code review. Does the code match the spec? Are there bugs, security issues, or missing tests?
**Who reviews:** MP (mandatory first reviewer)
**Outcomes:** `PASS`, `PASS_WITH_MANDATES`, `FAIL`
**Process:** Multiple rounds (R1, R2, R3...) until PASS. Each round's mandates must be fixed before the next.

#### Gate 4 — Production Verification

**What:** Is it working in production? Endpoints responding, data correct, no errors in logs.
**Who reviews:** Cross-review required (reviewer must be different agent from builder)
**Outcomes:** `PASS` → `bq_complete`
**Artifacts:** Must include `verification` field describing what was verified from customer perspective

### Cross-Review Requirement

Before a BQ can be marked `completed`, it needs a review from an agent that didn't build it. The `cross_review_gate.py` enforces this:
- Tracks `builders` (who wrote code) and `reviewers` (who reviewed)
- `approved_reviewers - builders` must be non-empty
- Gate reads from Living State entity body: `builders`, `reviewers`, and `gate{N}.{agent}_verdict` fields
- Valid verdicts detected by regex: `APPROV|VERIF|PASS`

**If blocked:** Ensure the entity has `gate4.{agent}_verdict = "PASS"` for a non-builder agent, and `builders = ["mp"]` (or whoever built it).

### Break Glass

For emergencies where the gate is blocking incorrectly:
```bash
touch /var/tmp/koskadeux/break_glass
# ... complete the BQ ...
rm -f /var/tmp/koskadeux/break_glass
```
Always remove after use.

## Build Dispatch Patterns

### MP Build (most common)
```
dispatch_mp_build(task="...", cwd="/Users/max/Projects/ai-market/ai-market-backend")
```

### Sizing
- Builds exceeding ~150-250s must be pre-split
- Pattern: models/migrations first → endpoints/services second → tests last
- Never dispatch a monolithic build for SSO-scale work

### Timeout Recovery
If MP times out after writing files but before committing:
```
shell_request: git status --short  # Files exist on disk
shell_request: git add . && git commit -m "..."  # Commit directly
```

## Living State Integration

- Every session that touches a BQ must `state_patch` the entity before close
- Use `bq_update` for status transitions, `bq_complete` for Gate 4 completion
- HANDOFF.md references entity keys + versions for next session verification
- `state_get("build:bq-{name}")` for full entity details

## Spec Writing Rules

- Always instruct MP to APPEND to existing spec files, never rewrite
- A rewrite instruction can cause MP to delete the original mid-task then time out
- Store specs in `specs/BQ-{NAME}-GATE2.md`
