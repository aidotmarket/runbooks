# BQ-RELEASE-GATE-QUEUE-ADMISSION-CONTROL — Gate 1 Spec (Round 3)

- **BQ code:** `BQ-RELEASE-GATE-QUEUE-ADMISSION-CONTROL-S760`
- **Class:** structural (reform-track; extends S621 eligibility model)
- **Authored:** S760.w (Mars). Round 2 = MP `3db8508b`; Round 3 = MP `f9140e72`.
- **Owner lanes:** WS4 worker-pickup-contract, WS5 primary-assignment-query, WS12 agent-peer-autonomy
- **Status:** GATE1 round-3 — awaiting Council re-challenge
- **Repos:** predicate + schema + state write-guard in `ai-market-backend`; dispatch guards in the **koskadeux-mcp gateway, ACTIVE checkout `/Users/max/koskadeux-mcp`** (NOT the stale sibling `/Users/max/Projects/ai-market/koskadeux-mcp`, which lacks these files); UI in `ops-ai-market`; this doc in `runbooks/specs`. Gateway paths below are relative to `/Users/max/koskadeux-mcp`.

## §1. Purpose
Make **release the enforced front door to development.** A BQ is workable (pick-up, assignment, build dispatch) **only after Max releases it from the console.** Until then it is *held*: visible and plannable, but inert. Confirmed: block build+pickup+assignment (spec prep allowed); grandfather active work; toggleable hold; Max-only authority.

## §2. Current state and the real enforcement surface (MP-3db8508b F4)
Canonical predicate `ai-market-backend/tools/lifecycle/eligibility.py`: `_eligible_for_ownership` `:130-140` (incl `and not manual_block` `:134`; read `:108-110`); `to_sql_where_clause` `:30-62` (manual-block clause `:50`); wrappers `:20-27`. Promoted columns `app/models/allai_state.py:112-131` (precedent `lifecycle_manual_block` `:115`), mapping `:80-95`. Recompute `app/services/lifecycle_handler.py:15-19,49-60`.

**Honest reality (MP-verified):** the predicate is consumed only by recompute + tests today. The v2 dashboard list calls `list_entities(kind="build")` (`app/api/v2/endpoints/build_queue.py:181-203`), not the predicate. No live worker-pickup/primary-assignment query consumer using `to_sql_where_clause` exists yet (WS4/WS5 unshipped). Therefore:
- The predicate change (§3.2/§3.3) is the shared **definition** — necessary but not sufficient.
- The **live teeth** are the **dispatch admission guard** (§3.4) and the **write guard** (§3.6).
- **Forward invariant:** any WS4/WS5 pickup/assignment query built later MUST source eligibility from the predicate / `to_sql_where_clause` (now including `released`). Gate 2 records this as binding on WS4/WS5.

## §3. Design
### §3.1 New field `released`
`body.lifecycle.released` (bool, default **false=held**) + `released_at` + `released_by`. Promoted column `lifecycle_released = Column(Boolean, nullable=False, server_default="false")` <- `body.lifecycle.released`; add to `allai_state.py:80-95` mapping + `:112-131`, mirroring `:115`. Additive alembic migration.

### §3.2 Predicate (Python) — `eligibility.py:130-140`
Add `and released` where `released = bool(_get(lifecycle, "released", _get(b, "lifecycle_released", False)))`.

### §3.3 Predicate (SQL) — `to_sql_where_clause:44-62`
Add `AND COALESCE({t}.lifecycle_released, false) = true`. Python/SQL parity test required.

### §3.4 Dispatch admission guard — HARD (MP F1/F2). Gateway paths under `/Users/max/koskadeux-mcp`.
Shared helper `assert_release_admitted(bq_code, *, ownership)` (resolve entity, evaluate the shared predicate incl `released`, raise typed "HELD — not released" otherwise) invoked **before dispatch** at:
- `tools/agents.py:3141` — `_handle_dispatch_build` (CC)
- `tools/agents.py:3160` — `_handle_dispatch_mp_build` (MP/Codex)
- `tools/agents.py:4107` — `_handle_council_request` routing (CC build path `:4124-4197`)
- `tools/agents.py:3120` — `_handle_call_claude_code` auto-demotion path
- `council_compliance_gate.py:176-230` — extend the Gate-1 check to also require release admission

**Fail closed (F2):** `council_compliance_gate.py:180-189` currently ALLOWS dispatch when `bq_code` is absent — under this spec a missing/unresolved `bq_code` MUST reject build dispatch. The auto-create path `tools/agents.py:3721` (`_ensure_bq_entity`; auto-create + `status:in_progress` at `:3740-3751`) MUST create it **held** (`released=false`, not auto-dispatchable) and **not** auto-release; no build in the same call.

### §3.5 Migration / grandfather (MP F5: acceptable)
One-time migration sets `lifecycle_released=true` (+ body, `released_by="migration:S760"`) for every existing `kind='build'` entity. `manual_block`/reconciliation blocks stay independent conjuncts, so grandfathering unblocks nothing blocked for other reasons. New entities default held.

### §3.6 Authority / write guard — authenticated identity, ALL paths (MP F3 + f9140e72 #2)
Flag is **immutable via every generic write path**; mutable **only** via a dedicated Max-authenticated release endpoint.
- **Release endpoint:** `POST /api/v2/build-queue/{code}/release` and `.../hold`, authenticated by the console OAuth **Max identity** (`useOpsAuth`), enforced server-side. Identity is **server-derived**, never from request-body `updated_by`.
- **Generic write paths reject `released`/`lifecycle_released` changes (and body `updated_by=max` claims) regardless of caller** — cover ALL of:
  - `app/services/state_service.py:389-397` — `patch_entity` (has ACL; extend)
  - `app/services/state_service.py:302-369` — `put_entity` (no ACL today; add)
  - `app/api/v1/endpoints/bq_lifecycle.py:64-72` — atomic PUT -> `put_entity`
  - `app/api/v1/endpoints/state.py:443-477,490-507` — state PUT/PATCH; trusts body `updated_by` under internal-key auth — guard MUST NOT trust body text
  - **`app/api/v1/endpoints/state.py:537-558` -> `app/services/state_service.py:476-538` (`cas_patch`) -> `_write_locked_entity:556-582`** — the CAS generic body-merge path (`cas_patch.new_state`, `_deep_merge_state` `:521`) MUST also reject `released` changes + body `updated_by=max`. (Note: `cas_draft_status:435-469` is scoped to `body.draft` and cannot touch `released`, so it is not a release vector.)
- Net: agents create/queue BQs and edit other fields but **cannot set `released`** by any route.

### §3.7 Console UX (`ops-ai-market/src/components/build-queue/BuildQueuePanel.tsx`)
Per-row Max-only **Release/Hold** toggle (calls §3.6, version-checked, 409->refetch), **Held/Released** badge, **"Show held"** filter, inert treatment for held rows.

## §4. Enforcement sites
| Site | Repo:file:line | Change |
|---|---|---|
| Predicate (Py) | backend `eligibility.py:130-140` | `and released` |
| Predicate (SQL) | backend `eligibility.py:44-62` | `AND COALESCE(...lifecycle_released,false)=true` |
| Schema | backend `allai_state.py:112-131` + migration | `lifecycle_released` default false |
| Dispatch guard | koskadeux-mcp `tools/agents.py:3120,3141,3160,4107(+4124-4197),3721`; `council_compliance_gate.py:176-230,180-189` | shared `assert_release_admitted`; missing bq_code fails closed; auto-create held |
| Write guard | backend `state_service.py:302-369,389-397,476-538,556-582`; `state.py:443-477,490-507,537-558`; `bq_lifecycle.py:64-72` | flag immutable via generic+CAS paths; authenticated identity only |
| Release endpoint+UI | backend `/build-queue/{code}/release\|hold` + console | Max-only toggle |
| WS4/WS5 forward constraint | future pickup/assignment queries | MUST use the predicate/SQL |

## §5. Acceptance criteria & Gate-2 tests
1. New BQ held; predicate+SQL exclude it; release admits; re-hold flips back.
2. Python/SQL parity test across released/held × every other condition.
3. Dispatch-guard tests for ALL §3.4 entry points + missing/unresolved `bq_code` (reject) + auto-create-held (no same-call dispatch).
4. Write-guard tests: PATCH, PUT, atomic, top-level promoted writes, **and the CAS path (`cas_patch`)** all reject `released` changes; a body `updated_by=max` claim via any generic path is rejected; only the authenticated release endpoint succeeds.
5. Migration tests: existing build rows become released; new rows default held.
6. Console shows Held/Released, Max-only toggle, "show held" filter.
7. Reform invariant: one Python reference predicate; SQL mirror tested against it.

## §6. Risks / open questions for Council
- **Re-hold mid-flight:** future ineligibility only; does NOT abort a running dispatch/lease (graceful). Confirm.
- **Create-and-dispatch (resolved §3.4):** if any path genuinely needs create-and-immediately-work (incident auto-remediation), define a narrow, audited, server-identity-gated auto-release exception scoped to that path only.
- **Gate-2 prereq:** cross-check citations against verbatim S621 Gate 0 §5.2/§5.3 + Schema Gate 1; pin or declare-absent the WS4/WS5 consumers.

## §7. Out of scope
Bulk release UX, scheduled/auto-release, per-priority policies, `manual_block`/reconciliation changes.

## Changelog
- **R2 (MP 3db8508b):** F1 dispatch guard elevated to hard requirement at all entry points; F2 missing-bq_code fail-closed + auto-create-held; F3 authenticated-identity write guard across put/patch/atomic/top-level; F4 honest enforcement framing + WS4/WS5 forward constraint; F5 create-and-dispatch resolved.
- **R3 (MP f9140e72):** fixed gateway path repo (ACTIVE `/Users/max/koskadeux-mcp`); added the CAS generic-merge write path to §3.6/§4/§5.
- **R4 (MP f5a3e85a):** corrected dispatch-guard line numbers to the real handler symbols in the 174KB active `tools/agents.py` (`_handle_dispatch_build:3141`, `_handle_dispatch_mp_build:3160`, `_handle_council_request:4107` CC routing `:4124-4197`, `_handle_call_claude_code:3120`, `_ensure_bq_entity:3721` auto-create) — the round-1 ranges (333-472) were stale.
