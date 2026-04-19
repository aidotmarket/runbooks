# BQ-124 Retro-Verification Procedure

## What this is

Retro-verification procedure for the two BQ-124 beat-scheduled jobs that were previously closed without trustworthy production runtime proof:

- `qdrant-reconciler-nightly`
- `kd-janitor-weekly`

This procedure exists because the code paths landed before the production Celery runtime topology existed. Reference:

- `specs/BQ-CELERY-INFRASTRUCTURE-DEPLOYMENT-GATE1.md` at commit `47b688c7`, `§11`
- `specs/BQ-CELERY-INFRASTRUCTURE-DEPLOYMENT-GATE2.md` at commit `bf8ae43`, `§10` and `§11`

Do not treat pre-infra Gate 4 status as runtime evidence. Reopen Gate 4 for these items until one post-infra-live execution proof exists for each.

## Jobs In Scope

| Phase | Beat entry | Task | Schedule |
|-------|------------|------|----------|
| BQ-124 Phase B1 | `qdrant-reconciler-nightly` | `app.tasks.scheduled.run_qdrant_reconciler` | Daily, 04:00 UTC |
| BQ-124 Phase C | `kd-janitor-weekly` | `app.tasks.scheduled.run_kd_janitor` | Sunday, 05:00 UTC |

## Preconditions

Before running either verification:

1. Confirm Celery infra is live in production.
2. Confirm beat logs show due-task emission.
3. Confirm worker heartbeat probe is `ok`.
4. Confirm the task still appears in the beat schedule in `app/core/celery_app.py`.

## Verification Path A: Natural Scheduled Run

Use this when the next scheduled window is acceptable.

### `qdrant-reconciler-nightly`

1. Wait for the next `04:00 UTC` beat window.
2. Check beat logs for due-task emission.

```bash
unset RAILWAY_TOKEN && railway logs -s ai-market-celery-beat
```

Expected beat signal:

```text
Scheduler: Sending due task qdrant-reconciler-nightly
```

3. Check worker logs for task start and successful completion.

```bash
unset RAILWAY_TOKEN && railway logs -s ai-market-celery-worker
```

Expected worker signals:

```text
Celery task: run_qdrant_reconciler starting
Celery task complete: reconciler checked=<n> requeued=<n>
Task app.tasks.scheduled.run_qdrant_reconciler[...] succeeded
```

4. Capture the returned result dict when available. Gate 1 requires evidence for:
   - `checked`
   - `drift_found`
   - `sample_missing`
   - `requeued`
   - `elapsed_seconds`
   - `cursor`
5. Confirm downstream evidence:
   - allAI event ledger entry exists
   - any requeued `qdrant_sync_outbox` rows process downstream as expected

Expected outcome:

- Safe outcomes include a no-op pass with `requeued=0` or a real reconcile delta with `requeued>0`.
- Either is acceptable if the task completes successfully and the evidence is captured.

### `kd-janitor-weekly`

1. Wait for the next Sunday `05:00 UTC` beat window.
2. Check beat logs for due-task emission.

```bash
unset RAILWAY_TOKEN && railway logs -s ai-market-celery-beat
```

Expected beat signal:

```text
Scheduler: Sending due task kd-janitor-weekly
```

3. Check worker logs for task start and successful completion.

```bash
unset RAILWAY_TOKEN && railway logs -s ai-market-celery-worker
```

Expected worker signals:

```text
Celery task: run_kd_janitor starting
Celery task complete: janitor created=<n> expired=<n>
Task app.tasks.scheduled.run_kd_janitor[...] succeeded
```

4. Capture the returned result dict when available. Gate 1 requires evidence for:
   - `proposals_created`
   - `proposals_expired`
   - `proposals_skipped_dedup`
   - rule-specific counters
5. Confirm downstream evidence:
   - rows inserted into `state_janitor_proposals`
   - no forbidden state entity or state event mutations occurred
   - allAI event ledger entry exists

Expected outcome:

- Acceptable outcomes include zero new proposals or real proposal creation.
- The key requirement is successful execution with proof that the task remained proposal-only.

## Verification Path B: Controlled Manual Trigger

Use this when the next natural schedule window is too far away.

### Manual trigger command

```bash
unset RAILWAY_TOKEN && railway shell -s ai-market-celery-worker
python - <<'PY'
from app.core.celery_app import celery_app

task_name = "app.tasks.scheduled.run_qdrant_reconciler"
result = celery_app.send_task(task_name)
print({"task_name": task_name, "task_id": result.id})
PY
```

For janitor, replace `task_name` with `app.tasks.scheduled.run_kd_janitor`.

### Manual trigger procedure

1. Trigger the task from the production worker shell.
2. Record the returned Celery task ID.
3. Follow worker logs until completion.
4. Capture the same evidence required for a natural run.
5. Save the proof in the BQ/Gate 4 record before reclosing the item.

## Evidence Checklist

For each of the two jobs, capture:

1. Beat proof or manual trigger proof.
2. Worker success log with task name.
3. Result dict counters.
4. Downstream proof:
   - `qdrant_sync_outbox` behavior and event ledger for reconciler
   - `state_janitor_proposals` rows and no forbidden mutations for janitor
5. Timestamp of verification in UTC.

## Post-Verification Status Handling

After both jobs have trustworthy runtime proof:

1. Reopen Gate 4 on BQ-124 Phase B1 and Phase C if not already reopened.
2. Attach the captured evidence.
3. Re-close those entries only after the new proof is reviewed.

Living State follow-up after verification:

- reopen Gate 4 on BQ-124 Phase B1
- reopen Gate 4 on BQ-124 Phase C
- then close both again once the post-infra runtime evidence is attached

This document defines the procedure only. It does not execute the retro-verification itself.
