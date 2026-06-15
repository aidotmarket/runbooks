# Session Close Protocol

## C.1 Purpose
The Koskadeux session close flow for Primary and Worker instances: gates, lock release, handoff write, and recovery procedures when close partial-completes. Owned by **BQ-PROCESS-SESSION-LIFECYCLE-RELIABILITY-S612** (P0). Major rewrite from 35-line stub during S612 process consolidation.

## C.2 When to close
Primary closes when:
1. Max explicitly says "close" or "close session".
2. Context utilization approaches ~65%.
3. Queue is genuinely exhausted with nothing in flight AND no Worker active.

Primary does NOT close just because a work unit finished. Pick up the next eligible item per the session-loop discipline in the system prompt.

## C.2.5 Two-instance coordination — boot gate & close isolation (S630)

Primary and Worker run as independent boot-gate slots. The fix landed at session_boot_gate.py S630 makes the gate **per-role, session-id-scoped** so concurrent Primary↔Worker activity does not cross-contaminate:

- `_active_session(role=...)` accepts an optional role filter. The default (no role) preserves legacy "most-recent non-closed across roles" semantics for read-only properties.
- `_advance_open(args)` reads `instance_role` from args, writes the session entry with that role, and only marks **same-role** prior sessions CLOSED. Worker opening does NOT close Primary's registry entry.
- `_advance_plan(args)` and `_advance_close(result, args)` look up the target session by `args.session_id` rather than "most recent". Worker close marks ONLY the worker session CLOSED.
- `check(name, args)` scopes gate-state lookup to `args.session_id` when present. Worker activity no longer trips PLANNING_GATE for Primary's tool calls.
- `checkpoint_required` is Primary-scoped: cleared only when a Primary session opens or closes. Worker open/close does not touch the flag.

**Operational consequences:**
- Worker may open, plan, dispatch, and close while Primary is mid-session. Primary's gate state is unaffected.
- Primary may dispatch + commit while Worker is mid-session. Worker's gate state is unaffected.
- Worker close path is also locally isolated (see §C.5): worker close writes `infra:session-status:{sid}:role=worker`, releases the worker slot on `infra:active-session-lock`, and SKIPS HANDOFF.md write / git ops / allai log / close-gate verification. Those are Primary-only.
- Codex CLI dispatch routing (commit c1cbddf) routes by cwd: dispatches against `/Users/max/Projects/*` run on the laptop (Worker's host); dispatches against `/Users/max/koskadeux-mcp` stay on Titan-1 (Primary's host). Each instance dispatches against its own working repos; cross-host dispatch happens only when explicitly cwd-targeted.

**What to verify after a gateway restart that loads new boot-gate code:**
1. Primary opens with `instance_role="primary"`; registry shows role=primary on its session entry.
2. Worker opens with `instance_role="worker"`; Primary's session entry is unchanged (still OPERATIONAL).
3. Worker closes; Primary tool calls continue without hitting PLANNING_GATE.


## C.3 Pre-close checklist
1. `git status` on every active repo (ai-market-backend, ai-market-frontend, koskadeux-mcp, aim-node, ops-ai-market). All clean OR all dirty-work committed-pushed.
2. Worker state: if Worker is active, check `infra:active-session-lock.body.worker` — close decision must preserve Worker liveness if Worker is still working.
3. Local branch on `main` for koskadeux-mcp (close gate checks this).
4. Handoff content drafted with next session's pending items.

## C.4 The close gate (kd_session_close)
Atomic close path runs:
1. Pre-flight: verify repo state and Living State sync.
2. Living State write: emits `session_end` event.
3. Handoff write: writes HANDOFF.md and pushes to main.
4. allAI log: writes session summary to allAI brain.
5. Lock release: clears `infra:active-session-lock.body.primary` (or `.worker`).

Each step is atomic; failure at any step rolls back the others where possible.

## C.5 Role-conditional close (resolved by PR #53, merged S607)
Worker close is NOT the same as Primary close. Worker close is slot-release-only — no git, no HANDOFF.md rewrite, no allAI log (Worker doesn't own those artifacts).

The close handler is role-conditional as of PR #53. After kickstart, `kd_session_close` branches on `instance_role`:
- **Primary**: full path C.4.
- **Worker**: lock-slot release + `session_end` event only.

If running pre-PR-#53 code (no recent kickstart), manual close path is the safe fallback (see C.8).

## C.6 Auto-release finalization gap (open as of S612)
The close gate has known partial-completion risk: if step 3 (handoff write/push) fails (non-main branch, push rejection, etc.), close transaction state can leave the registry inconsistent on retry.

Mitigation:
- Always verify `branch=main` BEFORE invoking `kd_session_close`.
- If close fails partway, do NOT retry without inspecting partial state.
- Fall back to manual close (C.8) when partial completion is detected.

## C.7 Stale-lock recurrence chain
The auto-release-finalization gap manifests as a stale primary lock at next session open. As of S612 the recurrence chain is at **9 documented manual primary clears** (S596 + S601 + S604 + S605 + S607 + S608 + S610 + S611 + S612).

When opening a session and primary slot is stale:
1. Verify via `ps -ef` that the prior session's processes are not actually running.
2. Patch `infra:active-session-lock.body.primary=null` with a `primary_clear_audit_s{N}` block.
3. Required audit fields: `cleared_at`, `cleared_by`, `authorized_by`, `pre_clear_state`, `reason`.

## C.8 Manual close protocol (fallback)
When `kd_session_close` fails or is unavailable:
1. Checkout `main` on koskadeux-mcp; commit + push any pending work.
2. Write HANDOFF.md manually with the canonical structure (C.10).
3. Commit + push HANDOFF.md to main.
4. Emit `session_end` event via `state_request action=event` with `title="session_end"` and full deliverables payload.
5. Patch `infra:active-session-lock.body.primary=null` with `primary_close_audit_s{N}` block.
6. Log to allAI via `allai_brain_request` (optional but preferred).

## C.9 The 5-finalized-check at close
Before declaring close-complete, verify:
1. `git log origin/main -1` shows the HANDOFF commit on main.
2. `infra:active-session-lock.body.primary` is `null`.
3. `infra:session-status:S{N}:role=primary` entity contains the `session_end` event reference.
4. allAI close-summary log (optional, log-only).
5. All Worker stash entities for this session are either drained or marked `stash_state=pending-next-session`.

## C.10 HANDOFF.md canonical structure
Required sections in order:
- **Header**: `closed_at`, `closed_by`, summary of Primary + Worker ships
- **Ships landed (next session: verify on main)**
- **Worker queue state (next session pickup)**
- **Pending Primary work for next session**
- **Pending Max input** (gated decisions blocking work)
- **Infrastructure health notes**
- **Key SHAs / tasks** (for resumption traceability)
- **Strategic notes** (Max directives still in force)

## C.11 Worker close audit format
Worker close audits are stored in `infra:active-session-lock.body.worker_close_audit_s{N}w`. Required fields:
- `reason` (why close)
- `cleared_at`, `cleared_by`, `authorized_by`
- `pre_clear_state`: `worker_host`, `worker_session_id`, `worker_started_at`, `worker_parent_session_id`
- `audit_summary_entity` (pointer to `infra:session-status:S{N}:role=worker`)
- `deliverables_completed` (list)
- `recurrence_chain_addition` (if applicable)
- `stash_inventory_pending_primary_drain`

## C.12 Worker-dead event false-positive guard (S608 surface)
Close handler must NOT fire `worker_dead_process` event for a Worker that is still operating on a separate host or sandbox. The S608 failure mode: Primary close cycle triggered worker_dead on an actively-authoring Worker, blocking Primary close with 422. Workaround: if Worker liveness is uncertain, skip the worker_dead event step (close still completes other artifacts; manual primary clear handles the slot release).

## C.13 Partial-completion registry inconsistency (S611 surface)
If `kd_session_close` first attempt fails on branch check and retry after main checkout returns `no_active_session_for_id`, the close transaction left the registry in an inconsistent state. Recovery:
1. Do not retry kd_session_close again.
2. Manual close path C.8 from a fresh state (write handoff via shell, patch lock entity, log session_end event).
3. File this as a known surface; the close handler should atomically roll back transaction state on first-attempt failure (open work item).

## C.14 Related runbooks
- `runbooks/session-open-protocol.md` — open flow (paired with close).
- `runbooks/session-registry-recovery.md` — recovery when session registry desyncs.
- `runbooks/peer-instance-discipline.md` — pre-close peer-bus and claim discipline checks.

## C.15 Owner
This runbook is owned by **BQ-PROCESS-SESSION-LIFECYCLE-RELIABILITY-S612** (P0).
Revisions land as PRs against koskadeux-mcp main; require MP+AG review-mode approval (close-path criticality).
