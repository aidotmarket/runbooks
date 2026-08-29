---
title: Session Open Protocol
owner: unassigned
last_verified: '2026-08-20'
aliases: []
error_signatures: []
---

# Session Open Protocol

## O.1 Purpose
The canonical Koskadeux session-open flow for the two trusted peers, `vulcan` and `mars`: handoff load, planning gate, and briefing review. Owned by **BQ-PROCESS-SESSION-LIFECYCLE-RELIABILITY-S612** (P0). Absorbs the prior `session_open_standup.md` per AG S612 mandate to eliminate two-file fragmentation.

## O.2 Instance open sequence
1. `kd_session_open(session_id="S{N}", instance="vulcan")` or `kd_session_open(session_id="S{N}", instance="mars")`. Reads CORE.md + per-instance handoff + BQ status + service health in one atomic call. Registers session start in `registry.db`. Returns business briefing.
2. If the response indicates a stale registry row, reconcile per §O.5.
3. Inspect the exact deployed `kd_session_plan` schema/contract identity and follow
   §O.2.1. A text sentence that says a plan was accepted is not state evidence.
4. Confirm the response is the typed accepted result and the server moved this
   instance from PLANNING to OPERATIONAL. Only then are tools unlocked.
5. Verify the DB-owned pickup source points at a real not-yet-shipped target. If stale, advance the queue before any other work.
6. Pick up the highest-leverage work from §O.4 priority order.

### O.2.1 kd_session_plan context contract

The intended contract is server-delivered context, not caller-authored proof of
reading. Detect the deployed contract from the exact connected tool schema and
contract digest; do not infer rollout state from this file, a prior session, or
response prose.

**When typed context delivery is deployed:**

1. Submit the objective-bearing plan without consultation IDs. Before any plan,
   debt, or status mutation, the server resolves one immutable runbooks
   `origin/main` SHA and returns the typed non-success outcome
   `RUNBOOK_CONTEXT_SELECTION_REQUIRED` with ranked bounded excerpts and an
   honest gap ID for every objective. The instance remains PLANNING.
2. Resubmit the unchanged plan using only the server-delivered consultation IDs
   or gap IDs. Caller-supplied paths, excerpts, scores, coverage claims, and
   reading attestations are not authority. The server binds each ID to this
   session, instance, objective set, catalog SHA, and excerpt digest.
3. A gap ID records a search miss; it does not prove that no runbook exists and
   does not force an agent to manufacture documentation. A changed objective or
   incomplete/truncated envelope requires a fresh selection response.
4. Proceed only after a typed accepted result atomically records the delivery
   receipt and moves the instance to OPERATIONAL.

**Bounded legacy compatibility, while the connected schema still exposes only
`runbook_consultation`:** resolve a freshly fetched full `origin/main` SHA in a
trusted clean checkout and search every objective against that one snapshot as
documented in the runbooks README. Submit exact existing `{path, section,
covers?}` references. Use `{no_entry_found: true, subject, reason, covers?}` only
after a recorded search miss; never invent a path, section, synthesis, or
runbook merely to satisfy the gate. Legacy debt/waiver rows are rollout
telemetry, not evidence that a runbook update is useful. A rejected or retried
plan must not be treated as a documentation obligation. If the legacy gateway
does create such a row, preserve it for migration and do not write filler to
discharge it.

In the legacy schema, `covers` contains 1-based objective numbers and every
objective must be covered. A RunbookRef section must be an exact heading, anchor,
or present § token. Incident synthesis, where the deployed schema still demands
it, is explanatory telemetry only and never proof that the source was read.

## O.3 Peer open sequence
Either peer may open first. There is no parent session and no `.W` derivation. Work pickup is DB-driven and independent per instance.

## O.3.5 Two-instance coordination

The boot gate is instance-keyed in `registry.db`. `vulcan` open does not disturb `mars`, and `mars` close marks only `mars` closed.

- Each peer may open, plan, and operate concurrently. Each PLANNING→OPERATIONAL transition is independent.
- If a peer sees a PLANNING_GATE error after a known gateway restart, re-open with `kd_session_open(instance=...)` then `kd_session_plan` and resume.
- New opens pass `instance`, never `instance_role`, `parent_session_id`, or `.W` session ids.
- **Missing-instance and agent-dispatch opens are namespaced to `scratch` (S858), not defaulted to `vulcan`.** An open with no `instance` arg, or an agent sub-session opened via `council_request`, lands in the non-human `scratch` row and skips the human boot payload. `_instance_liveness_collision` additionally refuses an open when the named `instance` already holds a live `PLANNING`/`OPERATIONAL` row under a DIFFERENT `session_id` (same-id reopen is allowed; `scratch` is exempt). A live `scratch` row in the registry is normal, not a fault. See agent-dispatch.md §M.1 and session-registry-recovery.md Overview.


## O.4 Peer work pickup priority order
After open, each peer independently works the highest-leverage item it can claim:
1. Pending reviewer verdicts on open PRs (check; merge if clean).
2. R2/R3 folds needed on PRs with mandates.
3. New builds from the queue (highest priority first).
4. Hygiene (Living State drift, missing entities, stale audits).
5. Process consolidation work (per the 5 surviving process BQs).

## O.5 Stale registry reconciliation
If `kd_session_open` returns evidence of a stale prior instance row:
1. Check the instance row in `/Users/max/koskadeux-state/registry.db`. That is the canonical path (`koskadeux-mcp tools/registry.py:47`, overridable only by `KOSKADEUX_REGISTRY_DB`). `/var/tmp/koskadeux/registry.db` is a retired compatibility path and is normally absent; opening it with `sqlite3` silently CREATES an empty database and returns no rows, so a diagnosis run against it reads as "no sessions" rather than as an error. Verified S1585.
2. Verify via `ps -ef` that the prior session's processes are not actually running.
3. Prefer `kd_session_close` for that stale session. Direct SQL is an audited last resort.
4. Re-attempt `kd_session_open(instance=...)` if needed.

## O.6 Retired lock entity
`infra:active-session-lock`, parent ids, and role-keyed status are retired from the open protocol. Do not recreate them for reconciliation.

## O.7 Memory #29 — RETIRED (2026-07-04, S1117)
The Memory #29 defensive ground-truth protocol is formally retired: the S621 reform
replaced every drift surface it defended with the single reconciled database, the
continuous reconciler, and the boot tripwire standup. Retirement was unanimously
Council-ratified with Max signoff; the full 11-criterion evaluation and evidence
live on the event ledger (pending event `ddca7b6a`, entity
`build:bq-reform-memory-29-protocol-retirement-s621`).

**Reactivation window: until 2026-08-03.** Trigger signals — boot tripwire blocking
drift, reconciler drift reports, or ACL warn/403 telemetry on
`config:parallel-worker-queue` — mandate a reactivation evaluation: revert this
commit and emit a `memory_29_protocol_reactivated` event referencing the ledger
record. Beyond the window, reactivation requires a fresh BQ.

Ordinary engineering judgment still applies: verify load-bearing claims against
ground truth before acting on them. That is standing practice, not a numbered
protocol.

## O.8 Canonical peer prompt
Use the live `infra:opening-prompt` Living State entity returned by
`kd_session_open` for either peer. The former
`docs/instance-opening-prompt.md` file is retired and is not a current path.

## O.9 Business briefing review at open
`kd_session_open` returns a `business_briefing` with the top BQs in business English. Either peer uses this for:
- Stale-priority signals (any item over 10 days untouched warrants a check).
- Pending Max input items (one-line decisions blocking Federate or other P0 work).
- Backfill count (any items missing business summary).

## O.10 The 5 surviving process BQs at open
After S612 consolidation, process work pickup is routed via the 5 survivors:

The names below are historical S612 work-item identifiers retained verbatim; they do not assign current instance roles or authority:
- BQ-PROCESS-AGENT-DISPATCH-RELIABILITY-S612 (P0)
- BQ-PROCESS-SESSION-LIFECYCLE-RELIABILITY-S612 (P0)
- BQ-PROCESS-BUILD-QUEUE-INTEGRITY-S612 (P1)
- BQ-PROCESS-CI-DEPLOY-GATES-S612 (P1)
- BQ-PROCESS-VULCAN-PRIMARY-DISCIPLINE-S612 (P2)

New process gaps file as runbook revision PRs against the survivor's named runbook — NOT as new BQs (see runbooks/peer-instance-discipline.md Changes and maintenance / Repair).

## O.10.5 Boot wire budget and the boot-size bake (T-2026-000271, S1256)

The `kd_session_open` boot payload has a hard wire budget of 64,000 JSON characters (`BOOT_WIRE_BUDGET_CHARS` in `koskadeux-mcp tools/session.py`; raised from 46,000 by Max decision, 2026-07-17). Non-truncatable content (constitution, opening prompt, plan contract, handoff or its durable spillover digest) is never cut; advisory content (business briefing items, aging lists, standup extras) is trimmed with every cut recorded in the payload's `truncated` ledger and `boot_payload_fit`.

- `BOOT_NON_TRUNCATABLE_OVER_BUDGET` at open means the protected floor alone exceeds the budget. Do not bypass the spillover stash, manually digest a handoff, or trim the constitution (constitution changes need a unanimous Council gate plus Max). Diagnose which component grew (fetch `infra:constitution`, `infra:opening-prompt`, `infra:handoff:instance=...` sizes; wire size is the JSON-escaped length), then escalate to Max for a budget or content decision. Reference diagnosis: T-2026-000271.
- Boot truth telemetry: every open publishes a v2 context profile (per-component chars, wire total, truncated ledger) to the backend `/api/v1/internal/context-profile`; the ops console renders it verbatim. Verify a boot by checking delivered profile == stored profile on chars and the truncated ledger (per-component token estimates are intentionally omitted server-side).
- Bake acceptance (Phase 0, `build:bq-session-boot-footprint-phase0-s1229`): at least 10 successful boots across both instances with zero BOOT_* inconsistencies, `truncated==[]` on qualifying boots, and console/profile equality. The original 24-hour floor was waived by Max (decision event 954f509f, 2026-07-17). Boots that trim advisory content are recorded as advisory evidence, not counted toward the qualifying total.
- Keeping boots clean: the biggest instance-controlled lever is the handoff — write lean handoffs (aim well under ~2k chars; durable detail belongs in Living State entities, not the handoff). Instance-to-instance close/reopen cycling for bake evidence requires Max's consent per the close protocol.

## O.11 Related runbooks
- `session-close-protocol.md` — transition and legacy close record.
- `session-registry-recovery.md` — recovery when session registry desyncs.
- `runbooks/peer-instance-discipline.md` — Vulcan/Mars peer operating discipline.
- `build-queue-lifecycle.md` — BQ lifecycle and pickup semantics.

## O.12 Owner
This runbook is owned by **BQ-PROCESS-SESSION-LIFECYCLE-RELIABILITY-S612** (P0).
Revisions land as reviewed changes against the owning gateway repository. This
historical protocol is not roster authority. Resolve builders, voters, paused
members, and retired members from the exact signed deployed tool-and-Council
contract; if that contract is absent or disagrees with the connected schema,
stop roster-dependent work rather than copying a prior-session panel.

## When it breaks

Use the open sequence and stale-registry reconciliation above when normal session open cannot complete.
