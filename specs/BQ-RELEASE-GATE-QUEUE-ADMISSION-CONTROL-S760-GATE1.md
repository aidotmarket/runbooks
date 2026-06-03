# BQ-RELEASE-GATE-QUEUE-ADMISSION-CONTROL — Gate 1 Spec (Round 2)

- **BQ code:** `BQ-RELEASE-GATE-QUEUE-ADMISSION-CONTROL-S760`
- **Class:** structural (reform-track; extends S621 eligibility model)
- **Authored:** S760.w (Mars). Round 2 after MP challenge `3db8508b` (REQUEST_CHANGES).
- **Owner lanes:** WS4 worker-pickup-contract, WS5 primary-assignment-query, WS12 agent-peer-autonomy
- **Status:** GATE1 round-2 — awaiting Council re-challenge
- **Code home:** predicate + schema + dispatch guards in `ai-market-backend` and `koskadeux-mcp`; this doc in `runbooks/specs`.

## §1. Purpose

Make **release the enforced front door to development.** A Build Queue item is workable (pick-up, assignment, or build dispatch) **only after Max releases it from the console.** Until then it is *held*: visible and plannable, but inert. Max-confirmed: block build+pickup+assignment (spec prep allowed); grandfather active work; toggleable hold; Max-only authority.

## §2. Current state and the real enforcement surface (MP-3db8508b finding 4)

The canonical predicate `tools/lifecycle/eligibility.py` (`_eligible_for_ownership` `:130-140`, incl `and not manual_block` `:134`; read `:108-110`; `to_sql_where_clause` `:30-62`, manual-block clause `:50`; wrappers `:20-27`) is the **shared definition** of workability. Promoted columns: `app/models/allai_state.py:112-131` (precedent `lifecycle_manual_block` `:115`), mapping `:80-95`. Recompute: `app/services/lifecycle_handler.py:15-19,49-60`.

**Honest reality (verified by MP):** the predicate is currently consumed only by the recompute path + tests. The v2 dashboard list just calls `list_entities(kind="build")` (`app/api/v2/endpoints/build_queue.py:181-203`), **not** the predicate. No live worker-pickup / primary-assignment query consumer using `to_sql_where_clause` exists yet (WS4/WS5 not shipped). **Therefore:**
- The predicate change (§3.2/§3.3) is the shared definition — necessary but **not sufficient** on its own.
- The **live enforcement teeth** are (a) the **dispatch admission guard** (§3.4) at every build entry point, and (b) the **write guard** (§3.6).
- **Forward invariant (WS4/WS5):** any pickup/assignment query consumer built later MUST source eligibility from `to_sql_where_clause` / the predicate (which now includes `released`). Gate 2 records this as a binding constraint on WS4/WS5.

## §3. Design

### §3.1 New state field `released`
`body.lifecycle.released` (bool, **default false=held**) + `released_at` + `released_by`. Promoted column `lifecycle_released = Column(Boolean, nullable=False, server_default="false")` <- `body.lifecycle.released`, added to `allai_state.py:80-95` mapping + `:112-131` columns, mirroring `lifecycle_manual_block` `:115`. Additive alembic migration, `server_default='false'`.

### §3.2 Predicate (Python) — `tools/lifecycle/eligibility.py:130-140`
Add conjunct `and released` where `released = bool(_get(lifecycle, "released", _get(b, "lifecycle_released", False)))`.

### §3.3 Predicate (SQL) — `to_sql_where_clause:44-62`
Add `AND COALESCE({t}.lifecycle_released, false) = true`. Python/SQL parity enforced by test.

### §3.4 Dispatch admission guard — HARD requirement (MP finding 1 & 2)
A single shared helper `assert_release_admitted(bq_code, *, ownership)` (resolves the entity, evaluates the shared eligibility predicate incl `released`, raises a typed "HELD — not released" rejection otherwise) MUST be invoked **before dispatch** at every build entry point:
- `koskadeux-mcp/tools/agents.py:333-348` — `dispatch_build` (CC).
- `koskadeux-mcp/tools/agents.py:351-363` — `dispatch_mp_build` (MP/Codex).
- `koskadeux-mcp/tools/agents.py:459-472` — `council_request agent=cc mode=build` routing.
- `call_claude_code` auto-demotion path.
- `koskadeux-mcp/council_compliance_gate.py:176-230` — extend the existing Gate-1 check to also require release admission.

**Fail closed (MP finding 2):** `council_compliance_gate.py:180-189` currently ALLOWS dispatch when no `bq_code` is supplied. Under this spec, a missing/unresolved `bq_code` MUST **reject** build dispatch. The auto-create path `koskadeux-mcp/tools/agents.py:393-439` (today creates a missing build entity `status: in_progress` and fails open) MUST instead create it **held** (`released=false`, not auto-`in_progress`-dispatchable) and **not** auto-release. No build proceeds on an auto-created entity in the same call.

### §3.5 Migration / grandfather (MP finding 5: acceptable)
One-time migration sets `lifecycle_released=true` (+ body fields, `released_by="migration:S760"`) for every existing `kind='build'` entity. Existing manual/reconciliation blocks remain independent conjuncts, so grandfathering does not unblock anything that was blocked for other reasons. New entities default held.

### §3.6 Authority / write guard — authenticated identity (MP finding 3)
The flag is **immutable via the generic state write path** and mutable **only** via a dedicated Max-authenticated release endpoint:
- **Release endpoint:** `POST /api/v2/build-queue/{code}/release` and `.../hold`, authenticated by the console's **OAuth Max identity** (`useOpsAuth`), enforced server-side. Identity is **server-derived**, never taken from request-body `updated_by`.
- **Generic write paths reject flag changes regardless of claimed `updated_by`.** Cover ALL paths (MP cited):
  - `ai-market-backend/app/services/state_service.py:389-397` — `patch_entity` (has ACL today; extend to forbid `released`/`lifecycle_released` unless caller is the release endpoint).
  - `app/services/state_service.py:302-369` — `put_entity` (NO ACL today; add the same guard).
  - `app/api/v1/endpoints/bq_lifecycle.py:64-72` — atomic PUT → `put_entity` (covered via the guard above).
  - `app/api/v1/endpoints/state.py:443-477,490-507` — the state API trusts payload `updated_by` under internal-key auth; the guard MUST NOT trust body text — a `state_request patch` claiming `updated_by=max` is rejected for flag changes. Only the release endpoint (server-derived Max identity) may set the flag; the migration sets it once at rollout.
- Net: agents can create/queue BQs and change other fields, but **cannot set `released`** by any route. That is the teeth behind "agents can queue but never self-release."

### §3.7 Console UX (`ops-ai-market/src/components/build-queue/BuildQueuePanel.tsx`)
Per-row Max-only **Release/Hold** toggle (calls §3.6, version-checked, 409→refetch), **Held/Released** badge, **"Show held"** filter, inert treatment for held rows.

## §4. Enforcement sites (summary)
| Site | File:line | Change |
|---|---|---|
| Predicate (Py) | `eligibility.py:130-140` | `and released` |
| Predicate (SQL) | `eligibility.py:44-62` | `AND COALESCE(...lifecycle_released,false)=true` |
| Schema | `allai_state.py:112-131` + migration | `lifecycle_released` default false |
| Dispatch guard | `tools/agents.py:333-348,351-363,459-472,393-439`; `council_compliance_gate.py:176-230,180-189` | shared `assert_release_admitted`; fail closed on missing bq_code; auto-create held |
| Write guard | `state_service.py:302-369,389-397`; `state.py:443-477,490-507`; `bq_lifecycle.py:64-72` | flag immutable via generic path; authenticated-identity only |
| Release endpoint+UI | backend `/build-queue/{code}/release\|hold` + console | Max-only toggle |
| WS4/WS5 forward constraint | future pickup/assignment queries | MUST use the predicate/SQL |

## §5. Acceptance criteria & Gate-2 tests
1. New BQ defaults held; predicate + SQL exclude it; releasing admits it; re-hold flips back.
2. **Python/SQL parity test** across released/held × every other condition.
3. **Dispatch guard tests** for ALL entry points in §3.4 AND for missing/unresolved `bq_code` (must reject) AND auto-create-held (no same-call dispatch).
4. **Write-guard tests:** PATCH, PUT, atomic write, and top-level promoted-column writes all reject `released` changes; a body `updated_by=max` claim via the generic API is rejected; only the authenticated release endpoint succeeds.
5. **Migration tests:** existing build rows become released; new rows default held.
6. Console shows Held/Released, Max-only toggle, "show held" filter.
7. Reform invariant: one Python reference predicate; SQL mirror tested against it.

## §6. Risks / open questions for Council
- **Re-hold mid-flight:** sets future ineligibility; does NOT abort a running dispatch/lease (graceful). Confirm.
- **Create-and-dispatch (resolved by §3.4):** `tools/agents.py:393-439` no longer auto-works; if any path genuinely needs create-and-immediately-work (incident auto-remediation), define a **narrow, audited, server-identity-gated** auto-release exception scoped to that path only.
- **Gate-2 prerequisite:** cross-check §2/§3 citations against verbatim S621 Gate 0 §5.2/§5.3 and Schema Gate 1; pin or declare-absent the WS4/WS5 pickup/assignment consumers.

## §7. Out of scope
Bulk release UX, scheduled/auto-release rules, per-priority policies, `manual_block`/reconciliation changes.

## Round-2 changelog (vs MP 3db8508b)
- F1: §3.4 elevated from "trace item" to hard requirement enumerating all build entry points + shared helper.
- F2: missing `bq_code` fails closed; auto-create path creates held, no same-call dispatch.
- F3: §3.6 rewritten — authenticated identity, all write paths (put/patch/atomic/top-level), flag immutable via generic path, body `updated_by` not trusted.
- F4: §2 reframed — predicate is shared definition; live teeth are dispatch guard + write guard; WS4/WS5 forward constraint added; dashboard-list reality noted.
- F5: §6 create-and-dispatch path resolved in §3.4.
