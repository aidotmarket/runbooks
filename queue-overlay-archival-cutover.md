# Queue-Overlay Archival Cutover (Reform WS11)

> Retires the 8 sub-surfaces accreted on `config:parallel-worker-queue.body` (S577–S626) and
> moves Worker-pickup / Primary-replenish reads onto the dashboard + build-entity query path.
> Workstream 11 of 11 of the S621 single-source-of-truth reform. **Code is BUILT and on main;
> the Phase-D production cutover is DESIGNED BUT NOT YET EXECUTED** (gated — see §E.2).

## §A. Header

- **BQ:** `build:bq-reform-queue-overlay-archival-s621` (parent `build:bq-single-source-of-truth-development-state-reform-s621`).
- **Repo / surfaces:** `koskadeux-mcp` — `tools/queue_overlay/{reader_shim,parity_checker,orchestrate,phase_b_prime,flip,archival,rollback,slo,telemetry,sub_surfaces}.py` + `tools/queue_replacement_reader.py` (G1 §7.1 public surface). Tests: `tests/queue_overlay/`.
- **Authoritative design:** `specs/BQ-REFORM-QUEUE-OVERLAY-ARCHIVAL-S621-GATE2.md` (merged d779fdf5) over WS11 G1 (squash 813c9e9) over Gate 0 §8.5 (4f02d1f). This runbook summarises; the spec is source of truth.
- **Operator config:** `config:queue-overlay-feature-flags` (Living State). Legacy data: `config:parallel-worker-queue`.
- **Status (S992):** Gate-3 BUILD COMPLETE — chunks 1,2,3,4a,4b + 5 all on main; chunk 5 merged 7a023a80; 4b Gate-4 deploy-verified S991. Phase-D cutover PENDING.

## §B. Capability Matrix

| Capability | State | Where |
|---|---|---|
| 4-mode reader shim (`legacy`/`dual`/`writer_flipped_dual`/`new_only`) | BUILT | `reader_shim.py`, `queue_replacement_reader.py` |
| Per-sub-surface parity + SLO predicate (<0.1%; zero-mismatch on `worker_pickup_signal`) | BUILT | `parity_checker.py`, `slo.py` |
| Phase B-prime per-sub-surface writer flip | BUILT | `phase_b_prime.py` |
| Phase D session-boundary atomic reader flip (WS3-guarded) | BUILT, **not executed** | `flip.py:maybe_execute_phase_d` |
| Archive + C8 ACL row + 12 `qo_*` telemetry events | BUILT | `archival.py`, alembic `s621_008_queue_overlay_c8_acl`, `telemetry.py` |
| Per-sub-surface rollback + forward-replay re-cutover | BUILT, **not exercised in prod** | `rollback.py`, `flip.py:execute_recutover` |

## §C. Architecture & Interactions

Phases A→B→B-prime→C→D→E per sub-surface. Readers go through the shim, switched by
`config:queue-overlay-feature-flags.body.reader_mode_<sub_surface>` (helper `mode=` param takes
precedence over the global flag). Writers are re-pointed in Phase B-prime
(`writer_routes`/`writer_flips`). Phase D atomically flips a sub-surface's reader to `new_only`.
Phase E archives the legacy body into `body.archived_queue_overlay_pre_s621_reform` (the rollback
source). **WS3 dashboard is the replacement read path** — the sharpest dependency (C4).

8 sub-surfaces total; the Table-B *policy* fields (`PRESERVED_POLICY_SUB_SURFACES` in
`sub_surfaces.py`) are preserved in place, not retired. Do not hardcode the split — read the enum.

## §D. Agent Capability Map

- **Vulcan/Mars (primary role):** only role that may execute Phase D / re-cutover (`flip.py`
  checks `caller role == 'primary'`). Sets the operator sign-off flags below.
- **Reconciliation/lifecycle handler:** maintains build-entity `git_state`; not a writer of these flags.
- **No agent auto-advances Phase D** — it is operator-gated by design.

## §E. Operate

### §E.1 Feature-flag surfaces (`config:queue-overlay-feature-flags.body`)

`reader_mode_<sub_surface>` (`legacy`|`dual`|`writer_flipped_dual`|`new_only`),
`ws3_dashboard_production_stable` (bool, default **False**), `recutover_approved_<sub_surface>` (bool),
`phase_d_complete` (bool), `writer_routes`, `writer_flips`, `writer_flip_attempts`.

### §E.2 Phase-D execution — PRECONDITIONS (NOT yet met as of S992)

`flip.py:maybe_execute_phase_d()` flips a sub-surface to `new_only` only when ALL hold per sub-surface:
(a) caller role `primary`; (b) `evaluate_slo(sub_surface)` eligible with timestamp <24h;
(c) Phase B-prime `writer_flip` emitted ≥3 days ago; (d) `ws3_dashboard_production_stable == True`.

The four programme-level preconditions before Phase D may run at all (tracker `wip_order`):
1. **WS7 Phase D** landed (sibling stash-collapse cutover).
2. **S757** reconciler-git fix in prod.
3. **WS3 dashboard production-stable** — 72h clean validation telemetry, then Primary flips
   `ws3_dashboard_production_stable=True` (Gate 0 §8 Step 1).
4. **Chunk-2 F1** read-volume telemetry confirmed.

Until then Phase D returns `FlipResult(executed=False, reason='ws3_dashboard_not_production_stable')`
(the one expected xfail in the suite). **Do not force the flag without the 72h validation.**

### §E.3 Post-Phase-D → WS9 ACL enforce tie-in

Setting `phase_d_complete=True` flips the C8 `field_acl` row for `config:parallel-worker-queue`
from `enforce_mode='warn'` → `'enforce'`. This is the WS9 sole-writer enforce-flip and carries
**403-brick risk** — it is strictly ordered after S849 handoff cutover + WS11 Phase D, and is
Max-gated. Do not flip enforce while any reader is still on `legacy`/`dual`.

## §F. Isolate

Per-sub-surface granularity throughout — a problem on one sub-surface never forces action on the
other seven. Telemetry to scope an incident (all `qo_*`, ≤32 chars): `qo_parity_mismatch`,
`qo_flip_blocked`, `qo_fallback_used`, `qo_missing_post_archive`, `qo_rollback`, `qo_reader_flip`.
Check the offending sub-surface's `reader_mode_<ss>` + recent parity events before acting.

## §G. Repair

Rollback triggers (spec §12.4.1): dashboard/build-entity query failure → auto fallback to `legacy`
(no rollback needed); parity >0.1% (or any mismatch on `worker_pickup_signal`) → per-sub-surface
rollback; lost-write skew → rollback + forward-replay; reader inventory miss → **block Phase D for
that sub-surface, do not roll back already-flipped ones**.

**Rollback** (`rollback.py:initiate_rollback(sub_surface, reason)`, 5 steps): (1) restore
`body.<ss>` from `body.archived_queue_overlay_pre_s621_reform.<ss>`; (2) `reader_mode_<ss>='legacy'`;
(3) re-enable legacy writer for that ss; (4) record rollback timestamp + keep legacy writes flowing;
(5) emit `qo_rollback` (no unregistered event types).

**Re-cutover** (`flip.py:execute_recutover(sub_surface)`): runs forward-replay FIRST — enumerate every
legacy overlay write since the rollback timestamp from the event ledger and replay derived values into
the canonical replacement target (`lifecycle.pickup_ownership`, `lifecycle.ready_at`, or the G1 Table-A
replacement), per Gate 0 §8.5 row #4. Then requires `evaluate_slo` eligible + Primary sign-off
`recutover_approved_<ss>=True`, then atomically flips `reader_mode_<ss>='new_only'` + emits
`qo_reader_flip` with `payload.re_cutover=True`.

**Recovery budget:** <15 min clean operator-triggered halt; <60 min mass multi-sub-surface; after
10 min elapsed emit `qo_rollback` with `payload.long_running=True` (no new event type).

## §H. Evolve

### §H.1 Invariants
- 8 sub-surfaces; preserved Table-B policy fields stay writable in place.
- 12 `qo_*` events only, each ≤32 chars; no new event types for approvals/long-running (use config flags + existing events).
- Phase D is per-sub-surface, primary-only, WS3-guarded, atomic.
- Forward-replay direction is rollback-era legacy writes → canonical targets, BEFORE re-cutover (Gate 0 row #4).

### §H.2 Do NOT
- Force `ws3_dashboard_production_stable=True` without the 72h dashboard validation.
- Flip `phase_d_complete`/ACL enforce while any reader is on `legacy`/`dual` (403-brick).
- Add unregistered `qo_*` event types.

## §I. Acceptance Criteria

- Build: `pytest tests/queue_overlay/` green (S992: 34 passed / 1 xfailed — the xfail is
  `test_phase_d_blocks_on_ws3_dashboard_not_production_stable`, expected until WS3 flag flips),
  coverage ≥90% on `tools/queue_overlay/*` + `tools/queue_replacement_reader.py` (S992: 91%).
- Phase-D Gate-4 (FUTURE): per-sub-surface reader flip verified live, parity clean, archive present,
  no `qo_missing_post_archive`, rollback drill within budget.

## §J. Lifecycle

Gate 1 design (813c9e9) → Gate 2 chunking (d779fdf5) → Gate 3 build chunks 1–5 (S984→S992,
final chunk 5 at 7a023a80) → **Phase-D cutover (PENDING, gated §E.2)** → Gate-4 prod verification →
WS9 ACL enforce-flip. Tracker: `config:reform-completion-tracker` (v13, S992).

## §K. Conformance

- Last verified: **S992** — chunk 5 merged + suite green on main (34/1xfail, 91%); Gate-3 PASS
  (DeepSeek + XAI APPROVE; MP excluded as builder).
- Phase-D dry-run / execution: **NOT yet performed** (gated). This runbook documents the designed
  procedure; update §E/§G with live observations when Phase D is executed.

## Operator guide (quick procedures)

- **"Is WS11 done?"** No — build is done, cutover (Phase D) is not. See `config:reform-completion-tracker`.
- **"Can I run Phase D now?"** Only if all four §E.2 preconditions hold AND you are primary. Otherwise it no-ops with `reason='ws3_dashboard_not_production_stable'`.
- **"A sub-surface looks wrong post-flip"** → §G: check parity events, fallback to `legacy` or `initiate_rollback`; never touch the other seven.
- **"How do I re-enable after rollback?"** → §G re-cutover: forward-replay → SLO eligible → set `recutover_approved_<ss>=True` → `execute_recutover`.
