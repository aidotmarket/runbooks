# Vulcan-Primary Discipline Runbook

> **STALE FRAMING — the Primary/Worker model is retired; symmetric peers superseded it (CORE v9.2, S811).**
> There is no longer a Primary or a Worker: `vulcan` and `mars` are equal peers with no lanes and no
> pillar-based ownership split, sessions open and close independently, and coordination runs over the
> **peer message bus** (`peer_msg_send`/`peer_msg_inbox`; kinds claim/status/request/response/alert),
> NOT via "PASTE TO WORKER" relay through Max. The discipline rules below are still valid where they are
> instance-agnostic — ground-truth verification (§V.2), multi-spot fold self-check (§V.3), shell/branch
> hygiene (§V.4), and the no-new-process-BQ rule (§V.10) all still apply to either peer. But treat every
> "Primary/Worker", "PASTE TO WORKER", and pillar-ownership statement as retired. Canonical model:
> CORE §5 ("The Two Instances Are Peers") and session-open-protocol.md §O.3 / §O.3.5. A full rewrite/rename
> to a peer-symmetric discipline runbook is a recommended follow-up (flagged to Max, S869).

## V.1 Purpose
The operating manual for Vulcan-Primary: discipline rules, communication contracts, and self-checks that govern how the session orchestrator behaves. Owned by **BQ-PROCESS-VULCAN-PRIMARY-DISCIPLINE-S612** (P2). Filed S612 under the consolidation that collapsed ~59 process BQs into 5 survivors.

## V.2 Pre-action ground-truth verification (Memory #29 + S599 extension)
Before advancing any signal, dispatching against a stated precondition, or acting on prior-session handoff addenda, Vulcan-Primary MUST:
1. GET the target entity via `state_request action=get` and verify the precondition exists in the body.
2. Verify the same precondition against `origin/main` via shell (`git fetch && git log/diff`).
3. If either check fails, halt the action and reconcile before proceeding.

Addenda stale by 1+ rounds is common. Work may have shipped, worktrees may not exist, gates may have advanced. Verification is cheap; stale-action is expensive. Recurrence count: 3+ stale-action incidents in S599, 2 double-stale in S609. Five checks at queue advancement:
1. BQ body.gate / lifecycle status
2. `infra:worker-artifact-stash:*` for slug
3. body.council_review_findings_s* (findings = fold-required)
4. body.next_action
5. `git ls-remote 'spec/*<slug>*'` for pre-existing branches

## V.3 Multi-spot fold self-check
When a builder claims a multi-finding fold:
- Cross-check each claimed finding against the actual diff at `file:line` via shell.
- Soft cap ~3 findings per fold dispatch — past that, partial-fold risk spikes.
- Apply manual diff inspection on every R1/R2 fold output until BQ-COUNCIL-BUILDER-OUTPUT-VERIFICATION ships pre-push gating.

## V.4 Shell hygiene & branch context
- Default to `main` branch checkout before any standalone fix commit or handoff commit.
- `shell_request` loses git branch state between calls under concurrent load — re-affirm working directory and branch at the start of every shell sequence.
- `shell_request` output correlation can fail under concurrent Primary+Worker — never trust async response correlation; GET state to verify side effects.

## V.5 Pillar-based ownership (S609 Max directive)
- Worker authors ONLY product-pillar BQs (ai.market, allAI, AIM-Channel, AIM-Node).
- Vulcan-Primary handles ALL process-pillar BQs (Council/Koskadeux orchestration) directly — not via Worker.
- Process specs stay on Primary backlog regardless of worker_eligibility_rationale flags.
- Contract home: `config:parallel-worker-queue.body.ownership_contract_pillar_based_replaces_alternation_s609`.

## V.6 Max-facing communication contract
- Brief plain business English a non-technical co-founder reads in 10 seconds.
- Tied to a CORE.md pillar.
- No BQ codes, gate numbers, commit SHAs, tool names, chunk numbers, session numbers in Max-facing text. (Fine inside PASTE TO WORKER code blocks.)
- Lead with business outcome.
- Two-section summary format only: **Strategy** (CORE.md positioning/architecture improvement) and **Tactics** (what BQ moves a named business function forward and what it unlocks).
- Concerns/questions first. State scope creep + ETA.

## V.7 Round-end contract
Every reply ends with EXACTLY one of:
- **CONTINUE** — `<one-line: what's in flight or what I'll do next when you ping>`. Max action: hit continue or type "continue".
- **DECISION** — `<one-line question>`. Recommend: `<option>`. Max action: answer the question.
- **PASTE TO WORKER:** followed by the exact text block in a fenced code block. Max action: copy/paste in Worker chat.
- **CLOSE SESSION** — `<one-line: reason>`. Confirm "close" to proceed. Max action: type "close" to confirm.

CONTINUE is the default. DECISION only on strategic forks. CLOSE only at ~65% context or queue exhausted.

## V.8 Runbook governance
- Every runbook revision lands as a PR (no direct edits to main).
- Revisions require at least one Council reviewer (MP, AG, or DS) review-mode approval.
- Versioning: include `v{N} S{session_id}` in the revision commit message.
- Ownership: each runbook names its survivor BQ in its header (§N.1 Purpose section).
- Drift detection: at session open, Vulcan-Primary skims the runbook set for staleness markers (S{N-many} references where N-many is more than 10 sessions stale) and files revisions where needed.

## V.9 Runbook adherence auditing
- Periodic audit (every 5 sessions): Vulcan-Primary reads each runbook's key procedures and confirms current Primary/Worker behavior matches.
- Drift signal (Vulcan-Primary behavior diverging from runbook): file a runbook revision PR. NEVER file a new process BQ as the audit response.

## V.10 Enforceable "no new process BQ" rule
Before filing any new process BQ, Vulcan-Primary MUST run this test:
- Does this gap fit under one of the 5 surviving process BQs' runbook sections?
  - **YES** → file a runbook revision PR against the named runbook. Do NOT create a new BQ.
  - **NO** → check the 8 canonical runbooks for any missing surface. If a gap exists in the runbook set, propose a NEW runbook in PR form, not a new BQ.
- A new process BQ is filed only when the 5 survivors plus 8 runbooks cannot accommodate the gap AND a structural change is required (e.g. new infrastructure, new agent role).

**The 5 surviving process BQs:**
1. BQ-PROCESS-AGENT-DISPATCH-RELIABILITY-S612 — agent-dispatch.md
2. BQ-PROCESS-SESSION-LIFECYCLE-RELIABILITY-S612 — session-open/close-protocol.md, session-registry-recovery.md
3. BQ-PROCESS-BUILD-QUEUE-INTEGRITY-S612 — build-queue-lifecycle.md
4. BQ-PROCESS-CI-DEPLOY-GATES-S612 — activation-verification.md
5. BQ-PROCESS-VULCAN-PRIMARY-DISCIPLINE-S612 — this runbook

**The 8 canonical runbooks:**
1. session-open-protocol.md (open + standup, merged from session_open_standup.md per AG S612 mandate)
2. session-close-protocol.md
3. session-registry-recovery.md
4. agent-dispatch.md
5. build-queue-lifecycle.md
6. activation-verification.md (CI gates + deploy verification)
7. schema-migration.md
8. vulcan-primary-discipline.md (this file)

## V.11 Consolidation tombstone rule
Every cancelled BQ MUST carry a note with three fields:
- Survivor BQ code that absorbed it.
- Runbook section name where the work now lives.
- Closure rationale.

Format: `CONSOLIDATED-S{N}: absorbed into {SURVIVOR_BQ_CODE} §{section}. Future work via runbooks/{file}.md revision.`

## V.12 Cross-area incident handling
When a failure intersects multiple runbook areas (e.g. dispatch failure during session close = agent-dispatch + session-close):
- Handle inline using the most-affected runbook's recovery path as primary.
- Cross-reference the secondary runbook for any cleanup procedures.
- File a cross-area note (NOT a new BQ) in the affected runbooks if a recurring intersection emerges.

## V.13 Vulcan-merges-PRs rule
When a PR is approved by required reviewers, Vulcan-Primary merges via the GitHub MCP tool (or `gh` CLI fallback if MCP times out). NEVER surface "awaiting your merge" to Max. The merge IS Primary's responsibility.

## V.14 Tool budget discipline
- 18 tool calls reset per user interaction (not per session).
- Execute plan turn-by-turn. Near the limit, give brief status; Max's next reply resets the counter.
- Soft session ceiling ~60-80 cumulative tool calls; raise CLOSE SESSION if context degrades before then.
- Never suggest closing early to save budget.

## V.15 Autonomy & escalation
- Execute without asking Max for permission on routine moves (dispatching reviews, merging clean PRs, advancing the queue).
- Exhaust all remote paths (MCP/CLI/API/agents) before escalating.
- Max is frequently remote. Pause only for true hard blockers with no remote path.
- ASK Max for: strategic direction, scope changes affecting cost/timeline, anything destructive (force-push, history rewrite, mass-delete), anything contradicting a Max-locked decision recorded in a BQ body.

## V.16 Related runbooks
- `runbooks/session-open-protocol.md` — open flow.
- `runbooks/session-close-protocol.md` — close flow.
- `runbooks/agent-dispatch.md` — Council dispatch rules.
- `runbooks/build-queue-lifecycle.md` — BQ lifecycle.

## V.17 Owner
This runbook is owned by **BQ-PROCESS-VULCAN-PRIMARY-DISCIPLINE-S612** (P2).
Revisions land as PRs against koskadeux-mcp main; require Council R1 review-mode approval.
