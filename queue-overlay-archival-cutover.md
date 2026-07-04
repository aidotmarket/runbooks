# Queue-Overlay Archival Cutover (Reform WS11)

> Retires the 8 sub-surfaces accreted on `config:parallel-worker-queue.body` (S577–S626) and
> moves Worker-pickup / Primary-replenish reads onto the dashboard + build-entity query path.
> Workstream 11 of 11 of the S621 single-source-of-truth reform. **EXECUTED AND COMPLETE
> through Gate 4 (S1117, 2026-07-04)** via the Max-approved zero-traffic archive-and-close
> path (§E.4). The live-traffic machinery in §E.2 remains documented for any future
> re-cutover of a surface that has real traffic.

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
3. **WS3 dashboard production-stable** — 72h clean validation telemetry, then the operating instance flips
   `ws3_dashboard_production_stable=True` (Gate 0 §8 Step 1). *S1097: the hourly comparator is now
   genuinely scheduled — Titan-1 launchd `com.koskadeux.ws3-comparator` runs
   `tools/dashboard/comparator_job.py` hourly; run evidence accrues on Living State entity
   `infra:heartbeat:ws3-dual-read-comparator` plus `mismatch_log` rows on divergence. Clean clock
   started 2026-07-02; earliest honest flip ≈ 2026-07-05. Both mirror SQL predicates were corrected
   S1097 to the canonical unified predicate (`ai-market-backend tools/lifecycle/eligibility.py
   to_sql_where_clause`); the G1 §4.4 inline SQL is stale (ownership retired with S811).*
4. **Chunk-2 F1** read-volume telemetry confirmed. *S1097 disposition: SATISFIED-BY-ZERO-READERS —
   cross-repo AG-M4 inventory found zero production readers of the 8 retired sub-surfaces
   (`config:parallel-worker-queue` archived since S803, zero writes since). No conversion build;
   the shim stays as the mandated surface for future consumers. DeepSeek-checked; full record at
   `config:queue-overlay-feature-flags.body.s1097_p4_disposition`, incl. the deferred reader_mode
   global-vs-per-ss defect that MUST be fixed inside the Phase-D build.*

Until then Phase D returns `FlipResult(executed=False, reason='ws3_dashboard_not_production_stable')`
(the one expected xfail in the suite). **Do not force the flag without the 72h validation.**

### §E.3 Post-Phase-D → WS9 ACL enforce tie-in

Setting `phase_d_complete=True` flips the C8 `field_acl` row for `config:parallel-worker-queue`
from `enforce_mode='warn'` → `'enforce'`. This is the WS9 sole-writer enforce-flip and carries
**403-brick risk** — it is strictly ordered after S849 handoff cutover + WS11 Phase D, and is
Max-gated. Do not flip enforce while any reader is still on `legacy`/`dual`.

### §E.4 EXECUTED — zero-traffic archive-and-close (method A, S1117)

The 8 sub-surfaces were retired on 2026-07-04 (S1117) via
`tools/queue_overlay/zero_traffic_close.py:execute_zero_traffic_archive_and_close`
(sentinel `ARCHIVE-AND-CLOSE-S621-WS11`), NOT via `maybe_execute_phase_d`. Rationale
(Max-approved method A; decision event 1fc3189c): the surface had verifiably zero
production readers and writers (double inventory S803+S1097), so the live-traffic
gates in §E.2 (B-prime writer flip ≥3d, SLO volume floor, 14d Phase-E archive wait,
primary-role check) could never be satisfied honestly. The module is evidence-gated
(ws3 flag True + `s1097_p4_disposition` present + not already complete) and convergent
on re-run (already_flipped / already_archived skips).

Execution record: all 8 `reader_mode_<ss>='new_only'` (flags entity v13);
all 8 snapshotted into `body.archived_queue_overlay_pre_s621_reform` on
`config:parallel-worker-queue`, 5 retired live fields nulled, 3 preserved Table-B
policy fields intact; events 8× `qo_reader_flip` + 8× `qo_archive` + `qo_done`,
zero `qo_missing_post_archive`. Operational note: invoke via a background process,
not a timeout-capped foreground exec — the S1117 first run outlived its shell
timeout and overlapped a re-run (harmless: one duplicate `qo_archive`, snapshot
overwrite-safe, but avoidable).

**§E.3 correction (as-executed):** setting `phase_d_complete=True` does NOT
auto-flip the ACL row — no code watches that flag. The WS9 warn→enforce flip is a
**manual, Max-gated, unanimous-Council operator SQL step**, executed S1117 in a
guarded transaction that re-checks the §H.2 preconditions (all 8 readers
`new_only` + `phase_d_complete=true` read from `state_entities`) in the same DB
session and asserts exactly 1 row updated.

**CRITICAL — field_acl key_pattern must be the FULL entity key.**
`state_service._acl_key_matches` compares `key_pattern` against the full key
(e.g. `config:parallel-worker-queue`). The C8 row (and the ws3 warn row) were
originally seeded kind-less per the Gate-2 spec and were therefore DEAD — caught
S1117 by a PROVE-IT-RUNS-LIVE probe (a post-enforce write was accepted) and
corrected by a unanimous-Council data fix to full-key patterns. Any future
key-scoped field_acl seed MUST use the full `kind:key` form; probe-verify after
seeding (expect rejection or `acl_warn_violation`). Liveness proof on file:
403 `sole_writer_mismatch` on the enforce row; `acl_warn_violation` event
2026-07-04T15:08:21Z on the warn row.

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

**Rollback ordering (post-S1117):** the C8 ACL row is in `enforce` — flip it
`enforce`→`warn` FIRST (inverse of the §E.4 guarded UPDATE), or every restore write
in step (1) below 403s. Re-flip to `enforce` after re-cutover.

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
- **S1097 conformance:** comparator scheduler live-verified (first run 0/0 divergences, heartbeat v1);
  P4 resolved by zero-reader evidence; P1 (WS7 Phase D) remains outstanding alongside the 72h P3 clock.
- **S1117 conformance (2026-07-04): Phase D + Phase E + WS9 enforce flip EXECUTED and
  Gate-4 liveness-verified.** Live observations folded into §E.4 and §G. Suite on merged
  main `d85db2d0`: 47 passed / 1 xfailed (the historical WS3-guard xfail; the zero-traffic
  path does not use `maybe_execute_phase_d`). BQ completed at Gate 4 with evidence links.

## Operator guide (quick procedures)

- **"Is WS11 done?"** YES — executed + Gate-4 verified S1117 (§E.4). See `config:reform-completion-tracker`.
- **"Can I run Phase D now?"** Only if all four §E.2 preconditions hold AND you are primary. Otherwise it no-ops with `reason='ws3_dashboard_not_production_stable'`.
- **"A sub-surface looks wrong post-flip"** → §G: check parity events, fallback to `legacy` or `initiate_rollback`; never touch the other seven.
- **"How do I re-enable after rollback?"** → §G re-cutover: forward-replay → SLO eligible → set `recutover_approved_<ss>=True` → `execute_recutover`.
