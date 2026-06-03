# BQ-RELEASE-GATE-QUEUE-ADMISSION-CONTROL — Gate 1 Spec

- **BQ code:** `BQ-RELEASE-GATE-QUEUE-ADMISSION-CONTROL-S760`
- **Class:** structural (reform-track; extends the S621 single-source-of-truth eligibility model)
- **Authored:** S760.w (Mars), 2026-06-03
- **Owner lanes:** WS4 worker-pickup-contract, WS5 primary-assignment-query, WS12 agent-peer-autonomy
- **Status:** GATE1 authored — awaiting Council challenge
- **Code home:** predicate + schema live in `ai-market-backend`; this spec doc lives in `runbooks/specs`.
- **Relation to reform:** adds one required conjunct to the canonical eligibility predicate ratified in S621 Gate 0 §5.2/§5.3 and implemented in `tools/lifecycle/eligibility.py`.

## §1. Purpose

Make **release the enforced front door to development.** A Build Queue item is admitted to the workable pool **only after Max explicitly releases it from the console.** Until then it is *held*: visible and plannable, but no worker may pick it up, no primary may be assigned it, and no manual build dispatch may target it.

Max-confirmed decisions (S760, "defaults"):

1. **Scope of the block** — held BQs are blocked from *build dispatch + autonomous pickup/assignment*. Spec authoring / Council planning on a held BQ is **allowed**, so a BQ can be made ready-to-build and then released.
2. **In-flight work** — all currently-active BQs are **grandfathered** (auto-released at migration) so live work, including the S621 reform itself, is not frozen. Only new / not-yet-released BQs require an explicit release.
3. **Latch or toggle** — **toggle.** Max can release a BQ and later re-hold it to halt further admission.
4. **Authority** — **Max only.** Release/hold is a Max-authenticated console action. Agent writes to the release flag are rejected.

## §2. Current state (source-of-truth, cited)

The reform already centralizes admission in one predicate used by the lifecycle handler, dashboard, pickup, and assignment paths (`tools/lifecycle/eligibility.py:3-5`).

- Python predicate: `_eligible_for_ownership(...)` returns the conjunction at `tools/lifecycle/eligibility.py:130-140`. It already contains an ops-style block: `and not manual_block` (`:134`; value read at `:108-110`).
- SQL equivalent: `to_sql_where_clause(...)` at `tools/lifecycle/eligibility.py:30-62`, including the manual-block clause `AND COALESCE({t}.lifecycle_manual_block, false) = false` (`:50`).
- `worker_pickup_eligible` / `primary_assignment_eligible` thin wrappers at `:20-27`.
- Promoted columns (schema SoT): `app/models/allai_state.py:112-131`, body->column mapping documented at `:80-95`. Precedent column: `lifecycle_manual_block = Column(Boolean, nullable=False, server_default="false")` (`:115`) <- `body.lifecycle.manual_block`. Denormalized eligibility: `lifecycle_pickup_eligible` / `lifecycle_primary_eligible` (`:130-131`).
- Recompute: `app/services/lifecycle_handler.py:15-19,49-60` recomputes eligibility from the predicate on transitions, so any new conjunct propagates to the denormalized columns automatically.

**Key insight:** `manual_block` is the existing template — a boolean conjunct that, when set, removes a BQ from the eligible pool. The release gate is the same shape with the **inverse default** (held until released) and **Max-only authority**, kept **orthogonal** to `manual_block` (the ops/agent-controlled reconciliation pause).

## §3. Design

### §3.1 New state field: `released`
- Body: `body.lifecycle.released` (bool, **default `false` = held**), plus `body.lifecycle.released_at` (ISO ts | null) and `body.lifecycle.released_by` (string | null; expected `"max"`).
- Promoted column: `lifecycle_released = Column(Boolean, nullable=False, server_default="false")` <- `body.lifecycle.released`. Added to the mapping comment block (`app/models/allai_state.py:80-95`) and the column list (`:112-131`), mirroring `lifecycle_manual_block` (`:115`). `released_at` / `released_by` stay JSONB-only.
- Alembic migration: additive, non-null with `server_default='false'`, following the S621 promoted-column pattern. No false-backfill — see §3.5.

### §3.2 Eligibility predicate (Python)
Add one conjunct to `_eligible_for_ownership` (`tools/lifecycle/eligibility.py:130-140`):
```
released = bool(_get(lifecycle, "released", _get(b, "lifecycle_released", False)))
return (
    pickup_ownership in ownerships
    and released                       # NEW — Max admission gate
    and gate_status in ELIGIBLE_GATE_STATUSES
    and not reconciliation_block
    and not manual_block
    ...
)
```

### §3.3 Eligibility predicate (SQL)
Add to `to_sql_where_clause` (`tools/lifecycle/eligibility.py:44-62`), adjacent to the manual-block clause (`:50`):
```
AND COALESCE({t}.lifecycle_released, false) = true
```
Python and SQL forms MUST remain equivalent (Gate 1 §3.4 "one reference implementation"). A parity test asserts they agree.

### §3.4 Dispatch admission (manual dispatch enforcement)
Autonomous pickup/assignment are covered by §3.2/§3.3 automatically. Manual dispatch (`dispatch_mp_build`, `council_request mode=build`, CC build) MUST also refuse a held BQ, or the gate is bypassable.
- **Requirement:** before a build dispatch is admitted, the dispatch path checks `worker_pickup_eligible` / `primary_assignment_eligible` (now including `released`) and rejects with a clear "held — not released" error if false.
- **Gate-2 trace item:** pin the exact insertion point in koskadeux-mcp dispatch tooling (candidate: the pre-dispatch validation that runs Build Queue drift reconciliation — `kd_reconcile_bq` / `services/build_queue_reconciler`). Reuse the shared predicate; do not re-implement.

### §3.5 Migration / grandfather
One-time migration at rollout: set `lifecycle_released = true` (and `body.lifecycle.released = true`, `released_by = "migration:S760"`, `released_at = now`) for **every existing `kind='build'` entity**, so nothing in the queue — including in-flight work and the S621 reform — is retroactively held. New entities default to `false` (held) via column `server_default` + body default.

### §3.6 Authority (Max-only)
- **Console action:** Max-authenticated endpoints `POST /api/v2/build-queue/{code}/release` and `.../hold` set/clear `released`, stamping `released_by` + `released_at`. Auth: the Google-OAuth Max identity the console already uses (`useOpsAuth`), enforced server-side — not merely the internal API key.
- **Write guard:** the Living State write path rejects (or strips) changes to `body.lifecycle.released` / `lifecycle_released` unless the actor is Max (release endpoint) or the grandfather migration. Agent `state_request patch` with `updated_by != max` attempting to change the flag fails closed. This guard is the teeth behind "agents can queue but never self-release."

### §3.7 Console UX (`ops-ai-market/src/components/build-queue/BuildQueuePanel.tsx`)
- Per-row **Release / Hold** toggle (visible/enabled only for the authenticated Max session), calling §3.6, version-checked like existing lifecycle writes (pass `version_stamp`, handle 409 by refetch).
- **Held / Released** badge per row.
- A **"Show held"** filter and a default treatment making held items obviously inert ("Held — release to admit to the queue").

## §4. Enforcement sites (summary)

| Site | File | Change |
|---|---|---|
| Python predicate | `tools/lifecycle/eligibility.py:130-140` | `and released` conjunct |
| SQL predicate | `tools/lifecycle/eligibility.py:44-62` | `AND COALESCE(...lifecycle_released,false)=true` |
| Schema column | `app/models/allai_state.py:112-131` + migration | `lifecycle_released` boolean default false |
| Recompute | `app/services/lifecycle_handler.py` | none (propagates via predicate) |
| Manual dispatch | koskadeux-mcp dispatch path (Gate-2 trace) | reject if not eligible |
| Write guard | Living State write path | reject non-Max writes to the flag |
| Release endpoint + UI | backend `/build-queue/{code}/release\|hold` + console | Max-only toggle |

## §5. Acceptance criteria
1. New BQ defaults `released=false`; both predicates return `false`; SQL filter excludes it.
2. After Max releases (no other condition failing), both predicates return `true` and SQL includes it. Re-holding flips back.
3. Python predicate and SQL clause agree for a fixture set spanning released/held × every other condition (parity test).
4. Manual dispatch is refused for a held BQ with a clear error.
5. A non-Max `state_request patch` setting `released` is rejected; flag unchanged.
6. Grandfather migration leaves all pre-existing build entities `released=true`; post-migration smoke check confirms no active BQ became ineligible solely due to this change.
7. Console shows Held/Released state, a Max-only toggle, and a "show held" filter.
8. Reform invariant preserved: one Python reference predicate; the SQL mirror is tested against it.

## §6. Risks / open questions for Council
- **Re-hold mid-flight:** re-holding sets future ineligibility but does NOT abort a running dispatch/lease (graceful). Confirm vs. also revoking an active lease.
- **Default-held blast radius:** every newly-created BQ is inert until Max acts. Confirm no automated path needs create-and-immediately-work (e.g. incident auto-remediation); if so, define a narrow audited auto-release scope for that path only.
- **`ready_at` overlap:** `lifecycle_ready_at` exists (`app/models/allai_state.py:116`) but is not in the predicate; confirm `released` is distinct and not conflated.
- **Citation cross-check (Gate-2 prerequisite):** verify §2 citations and §3.2/§3.3 placement against the verbatim S621 Gate 0 §5.2/§5.3 and Schema Gate 1 prose before build.

## §7. Out of scope
Bulk release/hold UX, scheduled/auto-release rules, per-priority release policies, and any change to `manual_block` or reconciliation semantics. Follow-on BQs.
