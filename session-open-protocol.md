# Session Open Protocol

## O.1 Purpose
The canonical Koskadeux session-open flow for the two trusted peers, `vulcan` and `mars`: handoff load, planning gate, and briefing review. Owned by **BQ-PROCESS-SESSION-LIFECYCLE-RELIABILITY-S612** (P0). Absorbs the prior `session_open_standup.md` per AG S612 mandate to eliminate two-file fragmentation.

## O.2 Instance open sequence
1. `kd_session_open(session_id="S{N}", instance="vulcan")` or `kd_session_open(session_id="S{N}", instance="mars")`. Reads CORE.md + per-instance handoff + BQ status + service health in one atomic call. Registers session start in `registry.db`. Returns business briefing.
2. If the response indicates a stale registry row, reconcile per §O.5.
3. `kd_session_plan(session_id, work_type, objectives, delegation_strategy, tool_budget)`. Transitions boot gate from PLANNING to OPERATIONAL. Tools unlock after this call.
4. Verify the DB-owned pickup source points at a real not-yet-shipped target. If stale, advance the queue before any other work.
5. Pick up the highest-leverage work from §O.4 priority order.

## O.3 Peer open sequence
Either peer may open first. There is no parent session and no `.W` derivation. Work pickup is DB-driven and independent per instance.

## O.3.5 Two-instance coordination

The boot gate is instance-keyed in `registry.db`. `vulcan` open does not disturb `mars`, and `mars` close marks only `mars` closed.

- Each peer may open, plan, and operate concurrently. Each PLANNING→OPERATIONAL transition is independent.
- If a peer sees a PLANNING_GATE error after a known gateway restart, re-open with `kd_session_open(instance=...)` then `kd_session_plan` and resume.
- New opens pass `instance`, never `instance_role`, `parent_session_id`, or `.W` session ids.
- **Missing-instance and agent-dispatch opens are namespaced to `scratch` (S858), not defaulted to `vulcan`.** An open with no `instance` arg, or an agent sub-session opened via `council_request`, lands in the non-human `scratch` row and skips the human boot payload. `_instance_liveness_collision` additionally refuses an open when the named `instance` already holds a live `PLANNING`/`OPERATIONAL` row under a DIFFERENT `session_id` (same-id reopen is allowed; `scratch` is exempt). A live `scratch` row in the registry is normal, not a fault. See agent-dispatch.md §M.1 and session-registry-recovery.md §A.


## O.4 Primary work pickup priority order
After open, Primary works the highest-leverage item:
1. Pending reviewer verdicts on open PRs (check; merge if clean).
2. R2/R3 folds needed on PRs with mandates.
3. New builds from the queue (highest priority first).
4. Hygiene (Living State drift, missing entities, stale audits).
5. Process consolidation work (per the 5 surviving process BQs).

## O.5 Stale registry reconciliation
If `kd_session_open` returns evidence of a stale prior instance row:
1. Check the instance row in `/var/tmp/koskadeux/registry.db`.
2. Verify via `ps -ef` that the prior session's processes are not actually running.
3. Prefer `kd_session_close` for that stale session. Direct SQL is an audited last resort.
4. Re-attempt `kd_session_open(instance=...)` if needed.

## O.6 Retired lock entity
`infra:active-session-lock`, parent ids, and role-keyed status are retired from the open protocol. Do not recreate them for reconciliation.

## O.7 Memory #29 ground-truth verification at open
Before acting on anything in the handoff or queue body:
1. GET the referenced entity.
2. Verify against `origin/main` via shell.
3. Reconcile if drift detected.

Common drift signals at open: queue body addenda 1+ rounds stale, ships listed in handoff not visible on origin/main, BQ gate status patched in handoff but not in entity.

## O.8 Canonical peer prompt
Use `docs/instance-opening-prompt.md` for either peer.

## O.9 Business briefing review at open
`kd_session_open` returns a `business_briefing` with the top BQs in business English. Vulcan-Primary uses this for:
- Stale-priority signals (any item over 10 days untouched warrants a check).
- Pending Max input items (one-line decisions blocking Federate or other P0 work).
- Backfill count (any items missing business summary).

## O.10 The 5 surviving process BQs at open
After S612 consolidation, process work pickup is routed via the 5 survivors:
- BQ-PROCESS-AGENT-DISPATCH-RELIABILITY-S612 (P0)
- BQ-PROCESS-SESSION-LIFECYCLE-RELIABILITY-S612 (P0)
- BQ-PROCESS-BUILD-QUEUE-INTEGRITY-S612 (P1)
- BQ-PROCESS-CI-DEPLOY-GATES-S612 (P1)
- BQ-PROCESS-VULCAN-PRIMARY-DISCIPLINE-S612 (P2)

New process gaps file as runbook revision PRs against the survivor's named runbook — NOT as new BQs (see peer-instance-discipline.md §H / §G).

## O.11 Related runbooks
- `runbooks/session-close-protocol.md` — close flow.
- `runbooks/session-registry-recovery.md` — recovery when session registry desyncs.
- `runbooks/peer-instance-discipline.md` — Vulcan/Mars peer operating discipline.
- `runbooks/build-queue-lifecycle.md` — BQ lifecycle and pickup semantics.

## O.12 Owner
This runbook is owned by **BQ-PROCESS-SESSION-LIFECYCLE-RELIABILITY-S612** (P0).
Revisions land as PRs against koskadeux-mcp main; require MP+AG review-mode approval (open-path criticality).
