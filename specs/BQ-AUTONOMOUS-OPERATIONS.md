# BQ-AUTONOMOUS-OPERATIONS — Gate 1 (R2)

**Parent BQ:** `build:bq-autonomous-operations`
**Gate:** 1
**Revision:** R3 (S489) — addresses MP R2 `4b56cce5` REQUEST_CHANGES (1H+1M+1L); R1 findings closed in R2
**Author:** Vulcan
**Repo:** aidotmarket/runbooks
**Spec path:** specs/BQ-AUTONOMOUS-OPERATIONS.md
**Discovery entity:** `project:bq-autonomous-operations-discovery-findings` v3+
**Scope decisions source:** `build:bq-autonomous-operations` v3 `body.scope_decisions_locked_s489`
**R1 commit:** `88b3d20`
**R2 commit:** `5de988c`

## 0. Executive Summary

Autonomous Operations builds the infrastructure that lets Market agents run recurring operational work (runbook compliance sweeps, backup verification, council-stall detection, secret rotation freshness, etc.) without Max prompting. Triggers are time-based (cron) AND state-predicated. Every autonomous run emits an event. allAI classifies results and either resolves-to-silent-success, queues for session-open digest, or escalates P0+ via Telegram.

V1 ships three parallel chunks:

1. **Backend** — schedule registry as first-class Living State entity kind + sole-API scheduler executor (APScheduler wrapped as internal substrate in v1; zero surviving direct APScheduler or `@cron` decorator use in backend code post-v1) + allAI stewardship role on `AllAIBrainAgent` with bounded queue and degradation policy + attention queue entity kind + missed-escalation audit with independent severity derivation.
2. **Frontend** — extend existing `aidotmarket/ops-ai-market` Vite+React+TanStack app by adding SCHEDULES, RUNS, ATTENTION, RECOMMENDATIONS panels alongside existing OPS/MONITOR/BUILD QUEUE/AGENTS/RUNBOOKS/MARKETING/FINANCE tabs. No host-routing, auth, or tech-stack changes.
3. **Content** — consolidated runbook-of-runbooks meta-runbook authored against the Runbook Standard with a reviewer-authored challenge scenario subset preventing self-validation tautology.

First concrete cron: weekly runbook stewardship sweep running `runbook-lint` across every runbook + §J staleness evaluation, writing a report entity consumed by the attention queue.

**R2 changes (see Appendix E for full table):**
- §9 rewritten: missed-escalation audit now derives severity INDEPENDENTLY of allAI's queue classification (H1).
- §4.2 schedule schema extended: `concurrency_policy`, `max_instances`, `misfire_grace_time_seconds`, `coalesce` (H2).
- §5.5 migration table CLOSED: Celery Beat audit complete (2 jobs migrate); backup-verify duplication resolved by staggered timing (H3).
- §10 rewritten: extend `aidotmarket/ops-ai-market`, NOT greenfield in `ai-market-frontend` (H4).
- §5.3, §5.4 expanded: idempotency model with `run_id` generation authority + `attempt_number` + duplicate-completion semantics (M1).
- §5.1 strengthened: CI lint paired with startup-assertion against a maintained `migration-manifest.yaml` (M2).
- §5.6 rewritten: `dispatch_mode=gh_actions_external` — classified as external schedules, outside the sole-API invariant (M3).
- §6.1 expanded: minimal v1 comparator surface (10 comparators) (M4).
- §7 expanded: bounded queue + rate isolation + degradation policy + split criterion (M5).
- §13.4 expanded: reviewer-authored challenge scenario subset ≥5 (L1).

---

## 1. Problem Statement

**Current state.** Every agent action in the Market requires Max's explicit prompt. Sessions are human-in-the-loop; sessionless autonomous work does not happen. Operational drift (stale runbooks, missed backups, quiet council stalls, unchecked secret age, etc.) accumulates invisibly until Max either notices a symptom or a catastrophic failure surfaces the drift for him. The Market's mandate is that **AI agents run it**; a human prompting every action is the opposite of that mandate.

**End state.** Max opens a session and gets a digest of what ran while he was gone, what succeeded, what's waiting on him. Recurring operational work happens on its own cadence. When autonomous runs detect state the agents can't resolve, allAI classifies severity and either queues for Max's next session (non-urgent) or escalates to Telegram (P0/P1). Every run leaves footprints — silent failures are detectable by construction.

**Why now.** BQ-RUNBOOK-STANDARD Gate 2 Chunk 2 landed (approved 2026-04-22 at commit `4886604`), defining how D4 Infisical + D5 AIM Node G4 runbooks get authored. The standard is only useful if runbooks get kept current and agents actually use them — both of which require autonomous stewardship. Without this BQ, the runbook standard is a static document set that rots.

---

## 2. Scope

### 2.1 In-scope v1

Backend:
- Schedule registry as first-class Living State entity kind (`schedule:*`).
- Scheduler service: evaluates registry every minute, fires due schedules, dispatches via `council_request` or direct callable.
- Pure-replace executor contract — APScheduler wrapped as internal substrate in v1; zero direct APScheduler or `@cron` decorator usage in backend code after migration.
- Startup-assertion against `migration-manifest.yaml` proving every recurring job maps to a registry schedule OR has an explicit disposition tag.
- Time-based triggers (cron) AND state-predicated triggers (predicate language in §6).
- allAI stewardship role on `AllAIBrainAgent` with bounded queue, rate isolation, degradation policy, split criterion.
- Attention-queue Living State entity kind (`queue:attention`) consumed at `kd_session_open`.
- Missed-escalation audit meta-cron with INDEPENDENT severity derivation from run events (not from queue contents).
- `gh_actions_external` dispatch mode for GH Actions workflows (external schedules tracked but not sole-API-governed).

Frontend (extending `aidotmarket/ops-ai-market`):
- Four new panels added to existing `Panel` union: `schedules`, `runs`, `attention`, `recommendations`.
- New TopNav tabs with URL routing at `/schedules`, `/runs`, `/attention`, `/recommendations`.
- New `src/components/{schedules,runs,attention,recommendations}/` component subdirs.
- New `src/lib/scheduleRegistryApi.ts` API client module following existing `apiFetch<T>` pattern.
- New TypeScript types for `Schedule`, `Run`, `AttentionItem`, `FrequencyRecommendation`.
- Reuse existing auth (Google OAuth via `useOpsAuth`), API key injection (`X-Internal-API-Key` from localStorage config), React Query, Recharts, shadcn/ui.

Content:
- Runbook-of-runbooks meta-runbook consolidating `agent-dispatch.md` + `session-lifecycle.md` + `council-gate-process.md` + `council-hall-deliberation.md` + `vulcan-configuration.md` into a single §A–§K-conformant runbook with ≥ 10 Vulcan-authored §I scenarios + ≥ 5 reviewer-authored challenge scenarios (Gate 3 acceptance).

First concrete cron:
- `schedule:weekly-runbook-stewardship-sweep` — runs `runbook-lint` across `/Users/max/Projects/runbooks/*.md` + §J staleness evaluation; writes `project:runbook-stewardship-report-YYYY-WW` entity; classifies via allAI.

### 2.2 Out-of-scope v1

- Agent-initiated schedule changes without Max approval.
- Multi-agent deliberative autonomy.
- Predictive/ML-driven frequency recommendations beyond simple operational signals.
- Replacing human-in-the-loop for any P0+ decision.
- Native executor replacement for APScheduler (v1 keeps it as internal substrate; swap-out is later BQ).
- Migration of non-backend scheduled work (e.g. Railway-side services external to backend process).
- Compound state-predicate logic (AND/OR); deferred to follow-on BQ.
- Registry-authoritative regeneration of GH Actions workflow files (deferred; R2 keeps .yml files as source of truth for external schedules — see §5.6).

---

## 3. Consumer Model

**C1 — Schedule authors (agents + Max).** Registry API is stable and versioned, entity schema enforced, validation errors precise, editing never loses run history.

**C2 — Scheduled agents (executors).** At fire time, receive well-formed dispatch envelope (schedule id, trigger, predicate result if any, budget caps, allowed_tools, run_id, attempt_number). On completion, emit structured result event with run_id. Idempotent duplicate-completion handling (§5.4).

**C3 — Stewardship + escalation consumers (allAI + Max).** Every run emits an event allAI can classify. Severity ladder well-defined. Missed-escalation audit (§9) proves P0/P1 items don't sit silently — its derivation of "should-have-escalated" is INDEPENDENT of the classifier it's auditing.

---

## 4. Schedule Registry Design

### 4.1 Entity kind

Key convention: `schedule:<dashed-name>`, e.g. `schedule:weekly-runbook-stewardship-sweep`.

### 4.2 Required fields (R2 — added H2 execution semantics fields)

| Field | Type | Required | Purpose |
|---|---|---|---|
| `id` | string | yes | Derived from key |
| `name` | string | yes | Display name |
| `description` | string | yes | 1–3 sentences describing purpose |
| `trigger_type` | enum | yes | `cron` \| `state_predicate` \| `manual_only` |
| `cron_expression` | string | conditional | 5-field cron when `trigger_type=cron` |
| `timezone` | string | conditional | IANA tz; default `UTC` |
| `predicate` | object | conditional | Shape per §6; required when `trigger_type=state_predicate` |
| `evaluation_cadence_seconds` | integer | conditional | Min 60; required when `trigger_type=state_predicate` |
| `agent` | string | yes | `mp`, `ag`, `xai`, `cc`, `sysadmin`, `allai-brain`, `crm-steward`, etc. |
| `dispatch_mode` | enum | yes | `council_request` \| `direct_callable` \| `gh_actions_external` |
| `task_prompt` | string | conditional | For `council_request` |
| `callable_path` | string | conditional | Python dotted path for `direct_callable` |
| `gh_workflow_path` | string | conditional | `.github/workflows/X.yml` for `gh_actions_external` |
| `council_mode` | enum | conditional | `review` \| `build` for `council_request` |
| `allowed_tools` | array | optional | MP tool restriction |
| `timeout_seconds` | integer | yes | Hard wall-clock cap; default 600 |
| `budget_usd` | number | conditional | Required for LLM-invoking dispatches; default 1.0 |
| `escalation_target` | enum | yes | `telegram_p0_p1` \| `attention_queue` \| `silent_success_only` |
| `priority` | integer | yes | 0–3 matching `_PRIORITY_MAP` |
| `enabled` | boolean | yes | Default `true` |
| `paused_until` | datetime | optional | Soft pause |
| **`concurrency_policy`** | **enum** | **yes** | `serial_queue` \| `skip_if_running` \| `allow_parallel`; **default `skip_if_running`** |
| **`max_instances`** | **integer** | **yes** | **Max concurrent instances when policy is `allow_parallel`; default 1** |
| **`misfire_grace_time_seconds`** | **integer** | **yes** | **If schedule missed by > this, drop rather than catch up; default 3600** |
| **`coalesce`** | **boolean** | **yes** | **If multiple fires were missed, run once; default `true`** |
| **`run_id_authority`** | **enum** | **yes** | **`executor` (default) \| `external_webhook` (for `gh_actions_external` mode)** |
| `last_run_at` | datetime | auto | |
| `last_run_status` | enum | auto | `success` \| `failure` \| `timeout` \| `agent_error` \| `dispatch_error` |
| `last_run_task_id` | string | auto | |
| `last_run_run_id` | string | auto | |
| `last_run_result_entity_key` | string | auto | |
| `next_run_at` | datetime | auto | |
| `run_count_total` | integer | auto | Monotonic |
| `run_count_failure` | integer | auto | Monotonic; frequency-signal input |
| `owner` | string | yes | Default `max` |
| `created_session` | string | yes | |
| `last_edited_by` | string | auto | |

### 4.3 Schedule lifecycle states

- `enabled=true` — normal operation
- `enabled=false` — disabled by Max; retains entity + history; does NOT fire
- `paused_until=<future>` — soft pause (e.g. during incident response); auto-resumes
- `deleted` — entity removed from Living State; retain run history in event ledger

### 4.4 Execution semantics defaults (R2 — answers H2)

| Field | Default | Rationale |
|---|---|---|
| `concurrency_policy` | `skip_if_running` | Safest for long-running ops; avoids pile-up |
| `max_instances` | `1` | Implies `concurrency_policy=skip_if_running` behavior |
| `misfire_grace_time_seconds` | `3600` | If backend was down > 1h, don't replay stale fires |
| `coalesce` | `true` | Multiple misses collapse to single run |
| `run_id_authority` | `executor` | Backend is authoritative; external mode overrides |

Registry schema validator enforces: if `concurrency_policy=allow_parallel` then `max_instances > 1`. If `trigger_type=manual_only` then `concurrency_policy` field is informational only (manual fires ignore it).

### 4.5 History retention

Last 100 runs per schedule kept in `schedule:<id>.body.run_history` (bounded array). Older runs are event-ledger-only. `run_count_total` + `run_count_failure` are monotonic across truncation.

---

## 5. Scheduler Executor Design (D3 — pure replace)

### 5.1 Sole-API invariant (R2 — strengthened per M2)

The registry IS the scheduling API for anything running inside the ai-market-backend process. After v1 migration completes:

**Static enforcement (CI lint):**
- Zero `import apscheduler` statements outside the substrate module.
- Zero `@cron(...)` or equivalent decorator usage.
- Zero direct APScheduler `add_job(...)` calls outside the substrate.

**Dynamic enforcement (startup assertion):**
- On backend boot, the scheduler executor reads `backend/config/migration-manifest.yaml`.
- The manifest lists every recurring job in the codebase with one of four dispositions:
  - `migrated_to: schedule:<id>` — points to a registry entity
  - `keep_ephemeral: <rationale>` — per-instance lifecycle (e.g. `BaseAgent` heartbeat)
  - `retired: <commit_sha>` — removed; commit recorded
  - `external_to_backend: <location>` — outside backend process (e.g. Railway services)
- Executor walks `app/` for `while True: ... asyncio.sleep(N)` patterns where N ≥ 60, inspects Celery `app.conf.beat_schedule` keys, and cross-checks each detected recurring job against the manifest.
- Startup fails with fatal error if any detected recurring job is NOT in the manifest. New recurring work cannot be merged without updating the manifest.

**Rationale:** CI lint catches the easy cases (imports, decorators). Startup assertion catches the hard cases (bare `while True` loops, Celery beat entries, ad-hoc timers). The manifest is the explicit audit record; additions to it require review.

### 5.2 Internal substrate (APScheduler in v1)

The registry's executor module (`app/services/schedule_registry/executor.py`) owns the single APScheduler instance for the backend process. On startup:

1. Runs the `§5.1` startup assertion; fails boot if manifest incomplete.
2. Reads all `schedule:*` entities from Living State.
3. For each `enabled=true` schedule where `trigger_type=cron`, registers an APScheduler job with the schedule's `concurrency_policy`, `max_instances`, `misfire_grace_time_seconds`, `coalesce` fields translated to APScheduler job kwargs.
4. For each `enabled=true` state-predicate schedule, registers an APScheduler interval job at `evaluation_cadence_seconds` that evaluates the predicate and fires the schedule on match.
5. For each `gh_actions_external` schedule, does NOT register APScheduler (the schedule is external); only subscribes to `schedule.run.complete` webhooks.
6. Subscribes to Living State change events for `schedule:*`; on edit/add/delete, updates APScheduler registration.

APScheduler handles misfire policy, concurrent-run limits, clock skew, DST — translated from the schedule's execution-semantics fields.

### 5.3 Dispatch envelope + idempotency model (R2 — expanded per M1)

When a schedule fires, the executor assembles and emits:

```json
{
  "schedule_id": "schedule:weekly-runbook-stewardship-sweep",
  "schedule_name": "Weekly Runbook Stewardship Sweep",
  "run_id": "run-<uuidv4>",
  "attempt_number": 1,
  "fired_at": "2026-04-22T07:00:00Z",
  "trigger": {
    "type": "cron",
    "cron_expression": "0 7 * * 1",
    "timezone": "UTC"
  },
  "agent": "sysadmin",
  "dispatch_mode": "direct_callable",
  "callable_path": "app.agents.sysadmin.runbook_stewardship.run_sweep",
  "timeout_seconds": 900,
  "budget_usd": null,
  "escalation_target": "attention_queue",
  "priority": 2
}
```

**`run_id` generation authority:**
- For `dispatch_mode` in (`council_request`, `direct_callable`): issued by the executor at fire time (UUIDv4). `run_id_authority=executor`.
- For `dispatch_mode=gh_actions_external`: issued by the GH Actions workflow on run start, sent to backend via webhook. `run_id_authority=external_webhook`.

**`attempt_number`:**
- Starts at 1 for fresh runs.
- Incremented on executor-initiated retry (e.g. after `dispatch_error` within a single-firing window).
- Manual retries via ops console issue a NEW `run_id` with `attempt_number=1`; retry is user-explicit action.

**Same run_id across retries:** when the same `run_id` retries (executor-initiated), `attempt_number` increments. Run history retains all attempts in the event ledger.

### 5.4 Result event contract + duplicate-completion handling (R3 — H1 sole-completion-event contract)

**Single completion event contract (R3 — H1 closure).** The registry defines EXACTLY ONE completion event type: `schedule.run.complete`. The `status` field discriminates outcome:

- `status: success` — agent completed successfully
- `status: failure` — agent raised an exception or returned a failure result
- `status: timeout` — wall-clock cap exceeded; either synthesized by executor (§5.4 below) or emitted by an agent that self-detected timeout
- `status: agent_error` — agent framework error (infrastructure-side, not agent-logic-side)
- `status: dispatch_error` — dispatch itself failed before agent started

No separate `schedule.run.failed` or `schedule.run.timeout` event types exist. All consumers (allAI stewardship subscription §7.2, missed-escalation audit §9.2) MUST filter on `status` field of `schedule.run.complete` events. This is a hard invariant; Gate 3 tests include "no non-`schedule.run.complete` events are emitted for run lifecycle."

On completion, the executing agent emits:

```json
{
  "event_type": "schedule.run.complete",
  "schedule_id": "schedule:weekly-runbook-stewardship-sweep",
  "run_id": "run-<uuidv4>",
  "attempt_number": 1,
  "started_at": "2026-04-22T07:00:00Z",
  "completed_at": "2026-04-22T07:04:12Z",
  "status": "success",
  "result_entity_key": "project:runbook-stewardship-report-2026-W17",
  "task_id": null,
  "summary": "Linted 30 runbooks; 3 staleness WARN, 0 FAIL.",
  "severity": "info"
}
```

**Idempotent result-consume semantics:**
- Executor treats `(run_id, attempt_number)` as primary key for result events.
- Duplicate `schedule.run.complete` events with the same `(run_id, attempt_number)` are IDEMPOTENT: overwrite same fields in `schedule:*` entity (with `expected_version` check), do NOT re-increment `run_count_total` or `run_count_failure`.
- For `gh_actions_external`: the webhook endpoint `/api/v1/schedules/<id>/run-result` checks event ledger for prior matching `(run_id, attempt_number)` event before writing; duplicates return 200 with `idempotent=true` in response body.
- Late-arriving duplicates (e.g. after webhook retry): same idempotency rule applies; no clobbering of newer state.

**Outcomes not completing:** if `completed_at - fired_at > timeout_seconds + 60s`, executor emits a synthesized `schedule.run.complete` with `status=timeout` and `severity=p2`; if the real result event arrives later, it is dropped as duplicate (but logged).

### 5.5 Migration plan — CLOSED inventory (R2 — answers H3)

| Current Location | Cadence | Disposition |
|---|---|---|
| `app/core/scheduler.py:830-849` SysAdmin health | 5min | **Migrate** → `schedule:backend-sysadmin-health-check-5m` |
| `app/core/scheduler.py:830-849` Backup verify | Daily 03:00 UTC | **Migrate** → `schedule:backend-backup-verify-daily` at **03:30 UTC** (staggered after GH backup) |
| `app/core/celery_app.py:107` `celery-worker-heartbeat` | Default beat cadence | **Migrate** → `schedule:backend-celery-worker-heartbeat` |
| `app/core/celery_app.py:166` `gmail-polling` | Per beat schedule | **Migrate** → `schedule:backend-gmail-polling` |
| `IncidentSweeper` 300s loop | 300s | **Migrate** → `schedule:backend-incident-sweeper-5m` |
| `BaseAgent` heartbeat (90s TTL) | 90s | **Keep ephemeral** — per-instance lifecycle, manifest tag `keep_ephemeral: per-instance-heartbeat` |
| `CRMStewardAgent` daily maintenance | Daily at `DAILY_MAINTENANCE_HOUR_UTC` | **Migrate** → `schedule:crm-steward-daily-maintenance` |
| `SysAdminAgent` proactive monitors (N monitors) | Various | **Migrate** per-monitor → `schedule:backend-sysadmin-monitor-<name>` |
| Telegram remediation per-proposal timeouts | Short-lived | **Keep ephemeral** — ephemeral per-request timers, manifest tag `keep_ephemeral: per-request-timeout` |
| GH `smoke-test.yml` (6h) | `0 */6 * * *` | **External** → `schedule:gh-smoke-test` (dispatch_mode=gh_actions_external) |
| GH `backup.yml` (03:00 UTC) | `0 3 * * *` | **External** → `schedule:gh-backup-daily` |
| GH `backup-verify.yml` (06:00 UTC) | `0 6 * * *` | **External** → `schedule:gh-backup-verify-ci-daily` (separate from backend 03:30 verify; different verifier) |
| GH `health-check.yml` (07:00 UTC) | `0 7 * * *` | **External** → `schedule:gh-health-check-daily` |
| GH `quarantine-weekly.yml` (Mon 08:00 UTC) | `0 8 * * 1` | **External** → `schedule:gh-quarantine-weekly` |
| GH `runbook-harness.yml` (07:00 UTC) | `0 7 * * *` | **External** → `schedule:gh-runbook-harness-daily` |

**Backup-verify duplication resolution (H3 sub-issue):**
- GH `backup.yml` runs the actual backup job at 03:00 UTC (external environment, appropriate for heavy pg_dump work).
- Backend APScheduler backup verification migrates to `schedule:backend-backup-verify-daily` at **03:30 UTC** (staggered 30 min after GH backup completes). The backend verify reads from DB and checks freshness — a different, complementary check.
- GH `backup-verify.yml` at 06:00 UTC does a CI-environment verify — third check, different codepath. Name changed to `schedule:gh-backup-verify-ci-daily` to disambiguate.
- Net: three distinct checks, three distinct schedules, no duplication.

**Celery Beat (H3 disposition closed):**
- Two live jobs in `app/core/celery_app.py:105-170`: `celery-worker-heartbeat` (line 107) + `gmail-polling` (line 166).
- Both migrate to registry schedules with `dispatch_mode=direct_callable` or equivalent.
- Post-migration: `app/core/celery_app.py` `app.conf.beat_schedule` dict is EMPTY (retained as empty for forward-compat); Celery Beat process in deploy config can be removed from Dockerfile/Procfile in a separate cleanup PR (not blocking v1).
- Manifest entry: `app/core/celery_app.py:105-170` beat_schedule dict has `migrated_to` pointers for each key.

**Manifest file:** `backend/config/migration-manifest.yaml` is created in Chunk A and must list every recurring job with its disposition. Startup assertion reads this file.

### 5.6 gh_actions_external dispatch mode (R2 — rewritten per M3)

**Design call:** GH Actions workflows are classified as **external schedules** — outside the sole-API invariant of backend code. The registry tracks them for unified reporting/dashboarding but the workflow `.yml` file's `schedule:` block remains the source of truth for the actual cron trigger.

Mechanism:
1. Schedule entity has `dispatch_mode=gh_actions_external`, `gh_workflow_path=.github/workflows/<n>.yml`, `run_id_authority=external_webhook`.
2. Registry does NOT fire the job. GH Actions fires on its own cron (from the `.yml` file).
3. Workflow emits webhook to `POST /api/v1/schedules/<id>/run-start` at run start with `{run_id, attempt_number, started_at}` (issuing the run_id).
4. Workflow emits webhook to `POST /api/v1/schedules/<id>/run-result` on completion with the §5.4 result event shape.
5. Registry receives webhooks, writes `last_run_*` fields, emits `schedule.run.complete` for allAI consumption.
6. ops.ai.market UI renders these schedules with a "GitHub Actions" badge; the cron-edit UI is DISABLED for them with tooltip "External schedule — edit the .yml file."

**Authority separation:**
- Internal schedules (backend in-process): registry is authoritative. Edit cron in registry → APScheduler re-registers.
- External schedules (GH Actions): `.yml` file is authoritative for the trigger. Registry is authoritative for the DISPATCH SEMANTICS (escalation_target, priority, etc.) but NOT for the fire time. Drift between .yml cron and registry cron is a reporting warning only.

**Why not make registry authoritative for external schedules too?** Would require GH-Actions-manifests-to-be-regenerated-from-registry, a build-time-codegen loop that adds complexity without v1 value. Deferred to follow-on BQ `bq-gh-actions-registry-authoritative`.

---

## 6. State-Predicate Triggers

### 6.1 Predicate language (R2 — expanded comparator surface per M4)

Predicates are JSON objects. Two forms in v1:

**Form A — event-age predicate.**
```json
{"kind": "event_age_exceeds", "event_type": "backup.verify.complete", "threshold_seconds": 172800}
```
Fires if no event matching `event_type` has been ledgered in the last `threshold_seconds`.

**Form B — entity-field predicate.**
```json
{
  "kind": "entity_field_comparison",
  "entity_key": "config:backup-verify-latest",
  "field_path": "body.last_success_at",
  "comparator": "older_than_seconds",
  "value": 86400
}
```

**Minimal v1 comparator surface for Form B (R2 — M4 closure):**

| Comparator | Value type | Semantic |
|---|---|---|
| `equals` | any | `field == value` |
| `not_equals` | any | `field != value` |
| `exists` | none | `field is present and non-null` |
| `missing` | none | `field is absent or null` |
| `older_than_seconds` | integer | `now - parse(field) > value` (field must be datetime) |
| `newer_than_seconds` | integer | `now - parse(field) < value` |
| `in_set` | array | `field in value` |
| `not_in_set` | array | `field not in value` |
| `count_exceeds` | integer | `len(field) > value` (field must be array) |
| `count_below` | integer | `len(field) < value` |

No arithmetic, no regex, no string operations in v1. Predicates needing those use `dispatch_mode=direct_callable` with a Python function that computes freely.

**Compound logic (AND/OR) deferred.** Schedules needing compound logic split into multiple schedules OR use `direct_callable` for complex evaluation.

### 6.2 Evaluation cadence

Predicates evaluated on schedule's `evaluation_cadence_seconds` (min 60). Evaluation emits `schedule.predicate.evaluated` events at DEBUG severity.

### 6.3 Debouncing

Registry tracks `last_predicate_true_fire_at` per schedule. If predicate was true at last evaluation AND schedule fired within the last `max(evaluation_cadence_seconds * 2, 300s)`, it does NOT fire again until the predicate returns false at least once (reset).

---

## 7. allAI Stewardship Role (R2 — operational per M5)

### 7.1 Role placement

Stewardship lands on `AllAIBrainAgent` at `app/allai/agents/allai_brain.py`. Rationale: brain is already Tier 0 wildcard subscriber + incident triage + escalation + remediation proposals. Adding "autonomous-run reports" is coherent with the existing role.

**Council invited to challenge.** MP or AG may recommend `AllAIStewardAgent` (dedicated) during review.

### 7.2 Subscription (R3 — H1 aligned to sole-completion-event contract)

`AllAIBrainAgent.startup()` adds ONLY `schedule.run.complete` to its subscription list. The brain filters by `status` field internally: `status in {failure, timeout, agent_error, dispatch_error}` routes to classification; `status=success` with `escalation_target=silent_success_only` logs-and-drops; `status=success` otherwise still passes through classification in case the schedule's success conditions have semantic content (e.g., staleness WARN). Consistent with §5.4 sole-completion-event contract.

### 7.3 Bounded queue + rate isolation (R2 — M5)

Incoming stewardship events hit a bounded in-memory priority queue per brain instance:
- **Max size:** 100 items.
- **Overflow policy:** items exceeding the bound are written to a Redis spillover queue `allai:stewardship:spillover`; brain instance drains spillover as slots free up.
- **Prioritization:** queue sorted by event `severity` (P0 first), then `fired_at` (oldest first within severity).

Classification runs in a **dedicated thread pool** (max 2 workers) isolated from incident triage's thread pool. Prevents a stewardship event storm from delaying incident triage classification.

### 7.4 Routing after classification

- `silent_success_only` → log to agent-log and drop.
- `attention_queue` → enqueue `queue:attention` item (§8).
- `telegram_p0_p1` + severity P0/P1 → immediate Telegram via escalation pipeline.
- `telegram_p0_p1` + severity P2+ → attention queue fallback (respecting existing P2+ batch semantics once G1 flusher-wiring gap is closed).

### 7.5 Degradation policy (R2 — M5)

Brain monitors its own classification latency. If p95 latency > 5s sustained for 5+ minutes:
- Emit `allai_brain.stewardship_degraded` event at severity P1.
- Switch to **safe-default mode**: all classifications default to `route_to_attention_queue` regardless of escalation_target. No Telegram sends from stewardship during degraded mode. Attention queue accumulates; Max sees them at next session open.
- Exit degradation when p95 latency < 2s for 10 consecutive minutes.

### 7.6 Split criterion (R2 — M5)

Steward-agent-split criterion (triggers filing of follow-on BQ `bq-allai-steward-agent-split`):
- Sustained classification load > 1000 events/day for 7+ days, OR
- Degradation mode fires 3+ times/week, OR
- p95 latency > 10s sustained for 15+ minutes twice in any 48h window.

Under any of these, Max is notified via attention queue (P1) and a pre-scoped BQ for AllAIStewardAgent is automatically filed (with Max's confirmation) to split stewardship from the brain.

### 7.7 Gap remediation dependencies

- **G1 (P2+ escalation flusher unwired)** — MUST be closed before autonomous-ops launches; follow-on BQ `bq-allai-escalation-flusher-wiring` filed during Gate 2 Chunk A authoring.
- **G10 (core ops path doesn't write Living State)** — **DELIVERABLE** of this BQ; registry + run events close G10 by construction.
- G2–G9: non-blocking; separate BQs at Max's discretion.

---

## 8. Attention Queue Entity Kind

### 8.1 Entity kind

Single entity `queue:attention`. Items live in `body.items` as a bounded array.

### 8.2 Item shape

```json
{
  "item_id": "att-<uuid>",
  "created_at": "2026-04-22T07:04:12Z",
  "source_schedule_id": "schedule:weekly-runbook-stewardship-sweep",
  "source_run_id": "run-<uuid>",
  "source_event_ledger_id": "<event_id>",
  "severity": "warn",
  "classified_by": "allai-brain",
  "classification_confidence": 0.87,
  "title": "3 runbooks stale (> 30 days since last verified)",
  "body_markdown": "- celery-infrastructure-deployment.md last verified 2026-03-10...",
  "actions_suggested": [
    {"kind": "link", "label": "View report", "entity_key": "project:runbook-stewardship-report-2026-W17"},
    {"kind": "dispatch", "label": "Re-verify runbook X", "schedule_id": "schedule:runbook-verify-x"}
  ],
  "resolved": false,
  "resolved_at": null,
  "resolved_by": null,
  "resolution_note": null
}
```

### 8.3 Severity ladder

| Severity | Meaning | Default routing |
|---|---|---|
| `debug` | Diagnostic | Agent log only (not queued) |
| `info` | Successful run | Agent log only (not queued) |
| `warn` | Non-urgent drift | Attention queue; no Telegram |
| `p2` | Degraded operation | Attention queue + P2 batch (requires G1) |
| `p1` | Urgent | Immediate Telegram + attention queue |
| `p0` | Critical | Immediate Telegram + attention queue + re-ping if unacked > 1h |

### 8.4 Session-open consumption

On `kd_session_open`, session-open bundle SHOULD include `queue:attention` items with `resolved=false` sorted by severity desc, created_at desc. Items are NOT auto-resolved by session open. Max acknowledges via ops console or by running the suggested action. Ack = `state_request patch` setting `resolved=true`.

Retention: resolved items > 90 days are purged nightly by `schedule:attention-queue-purge-resolved`.

---

## 9. Missed-Escalation Audit (R2 — INDEPENDENT derivation per H1)

### 9.1 Motivation

allAI classification is the single point of escalation decision. If the classifier drops or downgrades a P0/P1 item, Max doesn't learn until next session or never. The audit must catch this — and critically, **must not rely on allAI's classification output to do so**.

### 9.2 Audit mechanism — independent severity derivation

Meta-cron `schedule:missed-escalation-audit-hourly` runs every hour with `agent=sysadmin`, `dispatch_mode=direct_callable`:

**Step 1 — Derive candidate "should-have-escalated" set from RAW events, not queue contents (R3 — H1 aligned to sole-completion-event contract; M1 correlation keys specified):**

The audit reads the event ledger for the last 2h and applies the following **independent rules** (not dependent on allAI's classification). All rules filter on `schedule.run.complete` events with `status` discriminator per §5.4, NOT separate failed/timeout event types:

- **R1 — escalation-target P0/P1 failure:** any `schedule.run.complete` with `status=failure` AND `escalation_target=telegram_p0_p1` AND `priority in {0,1}` → candidate P0/P1. **Correlation key:** `run_id`.
- **R2 — persistent failure pattern:** any `schedule.run.complete` with `status in {failure, timeout, agent_error}` where the same schedule's previous `schedule.run.complete` with failing status was within the last 24h AND the schedule's `escalation_target=telegram_p0_p1` → candidate P1 (pattern of failure). **Correlation key:** `run_id` (of the current event).
- **R3 — dispatch error:** any `schedule.run.complete` with `status=dispatch_error` → candidate P1 (unconditional). **Correlation key:** `run_id`.
- **R4 — missed schedule fire (CRON SCHEDULES ONLY):** any cron schedule (`trigger_type=cron`) where `now - last_run_at > (cron_expected_interval_seconds * 2)` AND `enabled=true` AND `paused_until` is null or past → candidate P1. `cron_expected_interval_seconds` is derived from the cron expression (e.g. `0 7 * * *` → 86400s; `*/5 * * * *` → 300s). For cron expressions with irregular intervals (e.g. `0 0 * * 1` weekly vs `0 0 1 * *` monthly), the MAX gap between consecutive fire times in a year is used. State-predicate schedules and `manual_only` schedules are EXCLUDED from R4 (no predictable interval). **Correlation key:** `schedule_id + expected_fire_at` (synthesized — there is no prior run_id because the run didn't happen).
- **R5 — timeout on P0/P1-priority schedule:** any `schedule.run.complete` with `status=timeout` AND `priority in {0,1}` → candidate P0. **Correlation key:** `run_id`.
- **R6 — predicate-true-but-no-fire:** any schedule where `schedule.predicate.evaluated` returned `true` but no `schedule.run.complete` followed within `timeout_seconds + 60s` → candidate P1. **Correlation key:** `schedule_id + predicate_evaluated_at` (the predicate-evaluation event's `event_ledger_id`).

These rules are implemented in `app/services/schedule_registry/missed_escalation_audit.py` as deterministic Python code. **They do not call allAI.** They do not read `queue:attention`. Severity derivation is independent.

**Step 2 — Verify Telegram delivery for each candidate (R3 — M1 per-rule correlation):**

For each candidate, scan `telegram.send` events in the last 2.5h using the candidate's rule-specific correlation key:

- **R1, R2, R3, R5:** `telegram.send.body.correlation_run_id == candidate.run_id` → match.
- **R4:** `telegram.send.body.correlation_schedule_id == candidate.schedule_id` AND `telegram.send.body.correlation_expected_fire_at == candidate.expected_fire_at` → match.
- **R6:** `telegram.send.body.correlation_schedule_id == candidate.schedule_id` AND `telegram.send.body.correlation_predicate_evaluated_at == candidate.predicate_evaluated_at` → match.

Match found → candidate verified, move on. No match → candidate is a MISSED ESCALATION.

**Gate 3 contract:** backend Telegram-send code paths that escalate schedule events MUST populate `correlation_run_id` / `correlation_schedule_id` / `correlation_expected_fire_at` / `correlation_predicate_evaluated_at` fields in the send body. Missing correlation fields fail a Chunk A unit test.

**Step 3 — Self-escalate missed items:**

For each missed candidate:
1. Emit `autonomous_ops.missed_escalation_detected` event at severity P1.
2. Send Telegram message DIRECTLY (bypass allAI classifier — use `TelegramRelay.send_message()` directly with a pre-formatted alert template).
3. Write P1 attention queue item with `source_schedule_id=schedule:missed-escalation-audit-hourly` (clear paper trail: the audit caught this).

**Step 4 — Audit self-heartbeat:**

The audit emits `schedule.audit.heartbeat` at end of each run. A SEPARATE watchdog schedule `schedule:missed-escalation-audit-watchdog` runs every 3h with a state predicate `(event_age_exceeds, event_type=schedule.audit.heartbeat, threshold_seconds=10800)`. If the audit itself hasn't heartbeat'd in 3h, the watchdog fires a P0 Telegram directly — "the thing that's supposed to catch missed escalations has itself gone silent."

### 9.3 Why this is non-gameable

- Audit rules operate on raw events and schedule entity state, not on allAI's classification output.
- If allAI downgrades a P0 to info, the failure/timeout/dispatch_error event still exists in the ledger with `priority=0` on the schedule — the audit catches it.
- If allAI drops the write to `queue:attention` entirely, the audit doesn't care — it doesn't read the queue.
- If the audit itself fails silently, the watchdog catches it.
- If the watchdog fails silently — that's a single failure away from undetectable, but both the audit and watchdog must fail simultaneously AND the backend's own existing healthcheck must also miss it. This is acceptable risk for v1; a fourth-layer check is future work.

### 9.4 Acceptance

Gate 3 build must include end-to-end tests where:
1. A deliberately-misclassified-as-info P0 run is caught by the audit's R1 rule within 2h.
2. A dispatch error is caught by R3 within 2h.
3. The audit itself is killed; the watchdog fires Telegram within 3h.

---

## 10. ops.ai.market Frontend — EXTENDING `aidotmarket/ops-ai-market` (R2 — D1 per H4 investigation)

### 10.1 Topology correction

**R1 erroneously proposed** building a greenfield ops frontend inside `aidotmarket/ai-market-frontend` with Next.js host routing. Discovery supplement (runbook `ops-ai-market.md` + local clone at `/Users/max/Projects/ops-ai-market`) established:

- `ops.ai.market` IS a deployed Vite + React + TypeScript static site on Railway.
- Repo: `aidotmarket/ops-ai-market`. Tech stack: Vite 5, React 18, TanStack React Query 5.83, React Router DOM 6.30, shadcn/ui, Tailwind, Recharts, ReactFlow.
- Existing panels: OPS, MONITOR, BUILD QUEUE, AGENTS, RUNBOOKS, MARKETING, FINANCE (see `src/pages/Index.tsx` `Panel` string-literal union).
- Auth: Google OAuth via `src/hooks/useOpsAuth.ts`.
- API client: `src/lib/api.ts` with `apiFetch<T>(endpoint, options)` using `X-Internal-API-Key` header from localStorage config (`insaits_api_config`).

**R2 direction:** **EXTEND** this app. No host routing changes. No Next.js migration. No new repo.

### 10.2 New panels added to existing `Panel` union

Before (R1 incorrectly assumed greenfield):
```
Panel = "ops" | "monitor" | "build-queue" | "agents" | "runbooks" | "marketing" | "finance"
```

After (R2 — extends):
```
Panel = "ops" | "monitor" | "build-queue" | "agents" | "runbooks" | "marketing" | "finance"
       | "schedules" | "runs" | "attention" | "recommendations"
```

New panels:
- **SCHEDULES** (`/schedules`) — list all schedules with filter by agent / enabled / trigger_type; row → detail.
- **SCHEDULES detail** (`/schedules/:id`) — full entity view, run history table, edit form (respecting gh_actions_external read-only tooltip), manual-trigger button, toggle enabled.
- **RUNS** (`/runs`) — run history across all schedules, filterable; row → detail.
- **RUNS detail** (`/runs/:runId`) — full envelope, result event, agent-log excerpt link.
- **ATTENTION** (`/attention`) — attention queue items, unresolved first, severity ladder colored, resolve affordance with optional note.
- **RECOMMENDATIONS** (`/recommendations`) — allAI frequency recommendations: current cadence vs recommended cadence, rationale, signals summary, accept / reject buttons.

### 10.3 File additions

```
src/components/schedules/
  SchedulesPanel.tsx             # list view
  ScheduleDetail.tsx             # detail view
  ScheduleEditForm.tsx           # create + edit
  ScheduleList.tsx               # table component
  ScheduleRow.tsx
  ScheduleBadges.tsx             # gh_actions_external badge etc.
src/components/runs/
  RunsPanel.tsx
  RunDetail.tsx
  RunStatusBadge.tsx
src/components/attention/
  AttentionPanel.tsx
  AttentionItem.tsx              # card with severity, actions
src/components/recommendations/
  RecommendationsPanel.tsx
  RecommendationCard.tsx
src/lib/scheduleRegistryApi.ts   # API module, apiFetch<T> pattern
src/types/scheduleRegistry.ts    # Schedule, Run, AttentionItem, FrequencyRecommendation
```

### 10.4 API client module (`src/lib/scheduleRegistryApi.ts`)

Follows existing `apiFetch<T>(endpoint, options)` pattern, reuses `X-Internal-API-Key` header injection. New functions:

```typescript
listSchedules(filters?: ScheduleFilters): Promise<Schedule[]>
getSchedule(id: string): Promise<Schedule>
createSchedule(body: ScheduleCreateBody): Promise<Schedule>
updateSchedule(id: string, patch: SchedulePatchBody): Promise<Schedule>
deleteSchedule(id: string): Promise<void>
toggleSchedule(id: string, enabled: boolean): Promise<Schedule>
triggerSchedule(id: string): Promise<{ run_id: string }>
listRuns(filters?: RunFilters): Promise<Run[]>
getRun(runId: string): Promise<Run>
listAttentionItems(filters?: AttentionFilters): Promise<AttentionItem[]>
resolveAttentionItem(itemId: string, note?: string): Promise<AttentionItem>
listFrequencyRecommendations(): Promise<FrequencyRecommendation[]>
acceptRecommendation(recId: string): Promise<FrequencyRecommendation>
rejectRecommendation(recId: string, reason: string): Promise<FrequencyRecommendation>
```

### 10.5 Backend API contract

Backend ships the following routes at `/api/v1/ops/*`:

- `GET/POST/PATCH/DELETE /api/v1/ops/schedules[/:id]`
- `POST /api/v1/ops/schedules/:id/trigger`
- `GET /api/v1/ops/runs[/:runId]`
- `GET/PATCH /api/v1/ops/attention[/:itemId]`
- `GET/POST /api/v1/ops/recommendations[/:recId]`
- `POST /api/v1/schedules/:id/run-start` (webhook for `gh_actions_external`)
- `POST /api/v1/schedules/:id/run-result` (webhook for `gh_actions_external`)

All backend routes require the same `X-Internal-API-Key` gate as existing `/api/v1/ops/*` routes already used by OpsPanel (no new auth model needed).

### 10.6 State management

React Query with hooks per resource:
- `useSchedules()`, `useSchedule(id)`, `useCreateSchedule()`, etc.
- Query keys: `['schedules', ...filters]`, `['schedule', id]`, `['runs', ...filters]`, `['attention', ...filters]`, `['recommendations']`.
- Optimistic updates for toggle + manual trigger.
- Invalidation on create/update/delete.
- Refetch cadence: schedules list 30s; attention list 10s (attention queue is time-sensitive); runs list 60s.

### 10.7 Auth + routing

- No changes to `useOpsAuth.ts` — existing Google OAuth flow is reused.
- No changes to `next.config.ts` or middleware (those don't exist in this repo; it's Vite, not Next.js).
- No changes to `nginx.conf` (static serving, already set up).
- DNS and Railway deployment untouched.

---

## 11. Frequency-Recommendation Surface

### 11.1 Signal sources

allAI computes recommendations using four signals:

1. **Run duration trend** — moving average over last 10 runs.
2. **Failure rate** — `run_count_failure / run_count_total` over last 20 runs.
3. **State-drift observed** — for periodic-comparison schedules, delta between run results at current cadence.
4. **Session-prompted interventions** — scan session logs for Max-prompted operational work that matches an existing schedule's domain.

### 11.2 Recommendation generation

Daily `schedule:allai-frequency-recommendations-daily` cron at 02:00 UTC evaluates signals across all schedules, writes `recommendation:*` entities, emits `allai.recommendation.new` events.

### 11.3 Max approval flow

Frontend RECOMMENDATIONS panel lists pending recommendations. Accept → backend issues `PATCH /api/v1/ops/schedules/<id>`; recommendation `status=accepted`. Reject with reason → `status=rejected`; reason stored.

Recommendations older than 30 days with `status=pending` are auto-purged weekly.

---

## 12. Runbook Usage Enforcement

### 12.1 Decision: audit-first, policy-later (staged)

- **Policy-layer (strict):** support-dispatched agents must cite a runbook section; deferred to follow-on BQ after audit data informs instrumentation priority.
- **Audit-layer (lax):** allAI periodically reviews agent responses from past 24h, scores runbook-citation rate. Scores below threshold emit WARN attention item.

### 12.2 V1 ships audit-layer only

Additive + observational; doesn't break existing dispatches. Audit cron: `schedule:allai-runbook-citation-audit-daily`.

---

## 13. Runbook-of-Runbooks Deliverable (D2)

### 13.1 Consolidation scope

Source documents (pre-standard): `agent-dispatch.md`, `session-lifecycle.md`, `council-gate-process.md`, `council-hall-deliberation.md`, `vulcan-configuration.md`.

### 13.2 Consolidation form

Single new runbook at `/Users/max/Projects/runbooks/operating-guide.md` authored §A–§K-conformant to Runbook Standard at commit `365c198`.

### 13.3 Relationship to source documents

Source documents NOT deleted in v1. operating-guide.md is canonical; source documents get a header note "SUPERSEDED — see operating-guide.md."

### 13.4 Stateless-agent harness self-validation (R2 — L1 closure)

Validation must NOT be tautological (Vulcan-authored scenarios validating Vulcan-authored content). Two-part validation:

**Part A — Vulcan self-assertion set (≥ 10 scenarios).**
- Authored by Vulcan in the same session as the operating-guide.md body.
- Must pass `runbook-harness --runbook operating-guide.md --mode conformant` at ≥ 80% weighted score.
- Committed inline in §I of operating-guide.md.

**Part B — Reviewer-authored challenge set (≥ 5 scenarios) (R3 — L1 single source of truth).**
- Authored by MP (or AG if MP unavailable) in a SEPARATE session, AFTER Part A is committed.
- Reviewer reads the 5 source documents independently and derives challenge scenarios from facts mentioned in source but that may have been lost/drifted during consolidation.
- Committed INLINE in §I of operating-guide.md under a clearly labeled "Reviewer-authored challenge scenarios" subsection with author attribution per scenario (`authored_by: mp-<session>` or `authored_by: ag-<session>`). This is the **single source of truth**; no external `reviewer-challenge/` directory.
- Harness contract: the normal `runbook-harness --runbook operating-guide.md --mode conformant` invocation loads the ENTIRE §I set (Part A + Part B combined) and scores them together. No `--external-scenario-set` flag needed; no separate external directory.

**Combined acceptance (R3 — L1):**
- Part A scenarios (authored_by: vulcan-<session>) must pass at ≥ 80% weighted score in isolation (filter §I to Part A only for this measurement).
- Part B scenarios (authored_by: mp-<session> OR ag-<session>) must pass at ≥ 80% weighted score in isolation (filter §I to Part B only for this measurement).
- If Part B fails while Part A passes, the finding implies the meta-runbook drifted from source documents during consolidation — Vulcan must amend operating-guide.md to cover the failing scenarios' facts.
- The partition-by-author-attribution is implemented as a loader feature in `runbook_tools/harness/loader.py` (Chunk 1 of BQ-RUNBOOK-STANDARD follow-on, tracked by `bq-runbook-harness-production-wiring` or filed separately if that BQ's scope doesn't cover attribution-based scoring).

This breaks the tautology: the reviewer's scenarios test whether the consolidated meta-runbook accurately represents its sources, not just whether the consolidator's own scenarios agree with the consolidator's own content.

---

## 14. First Concrete Cron: Runbook Stewardship Sweep

`schedule:weekly-runbook-stewardship-sweep`
- Trigger: cron `0 7 * * 1` (Mondays 07:00 UTC)
- Agent: `sysadmin`
- Dispatch: `direct_callable` → `app.agents.sysadmin.runbook_stewardship.run_sweep`
- Concurrency: `skip_if_running`, max_instances 1
- Actions:
  1. `runbook-lint` across every `.md` in `/Users/max/Projects/runbooks` root (excluding `specs/`, `tests/`, `templates/`, `harness/`, `runbook_tools/`).
  2. For each runbook, evaluate §J staleness predicate.
  3. Aggregate to `project:runbook-stewardship-report-YYYY-WW`.
  4. Emit `schedule.run.complete`.
- Severity: FAIL → P1; staleness beyond grace → P2; staleness within grace → WARN; all OK → info.
- Retention: last 12 weekly reports; older purged by `schedule:stewardship-report-purge-quarterly`.

---

## 15. Acceptance Criteria (Gate 1 closure)

Gate 1 APPROVED when MP + AG both concur ≥ APPROVE_WITH_NITS on R_N:

1. **AC1 — Schedule schema complete + execution-semantics fields included** (H2 closure).
2. **AC2 — Pure-replace contract + startup-assertion-against-manifest enforcement clear** (M2 closure).
3. **AC3 — State-predicate comparator surface specified** (M4 closure).
4. **AC4 — allAI stewardship placement with operational queue/rate-isolation/degradation/split criterion** (M5 closure).
5. **AC5 — Attention queue + severity ladder + session-open integration sound.**
6. **AC6 — Missed-escalation audit derives severity INDEPENDENTLY of allAI classification** (H1 closure).
7. **AC7 — ops.ai.market extension scope on existing Vite/React repo** (H4 closure).
8. **AC8 — Frequency-recommendation signals + Max approval flow specified.**
9. **AC9 — Runbook-enforcement audit-first-then-policy decision staged.**
10. **AC10 — Runbook-of-runbooks consolidation with reviewer-authored challenge set breaking tautology** (L1 closure).
11. **AC11 — Gate 2 chunking (3 chunks) viable with clean inter-chunk contracts.**
12. **AC12 — Gap remediation dependencies explicit (G1 prerequisite, G10 deliverable).**
13. **AC13 — Migration inventory CLOSED (all jobs have dispositions, no deferred Celery audit, backup-verify duplication resolved)** (H3 closure).
14. **AC14 — Idempotency model + `run_id` authority + `attempt_number` + duplicate-completion semantics specified** (M1 closure).
15. **AC15 — `gh_actions_external` mode coherent as external-schedule classification** (M3 closure).
16. **AC16 — R2 open questions are narrow and R3-answerable.**

---

## 16. Gate 2 Chunking Proposal

**Chunk A — Backend schedule registry + executor + allAI stewardship + attention queue + missed-escalation audit.**
- Scope: §4, §5, §6, §7, §8, §9 of this spec.
- Dependencies: follow-on BQ `bq-allai-escalation-flusher-wiring` (G1) Gate 3 APPROVED before Chunk A Gate 3.
- Output: `app/services/schedule_registry/` package + `backend/config/migration-manifest.yaml` + new `/api/v1/ops/*` routes + Alembic migration for `user.ops_role` field (existing?) or confirm existing auth covers.
- Sub-chunks: A1 registry data model + CRUD, A2 executor + substrate + startup-assertion, A3 predicate engine + dispatch envelopes, A4 allAI subscription + bounded queue + degradation, A5 attention queue + missed-escalation audit + watchdog.

**Chunk B — ops.ai.market panel extensions.**
- Scope: §10 of this spec.
- Dependencies: Chunk A Gate 3 API routes stable before Chunk B Gate 3 integration tests.
- Output: new panels + components + api client + types in `aidotmarket/ops-ai-market` repo.
- Sub-chunks: B1 schedules + runs panels, B2 attention + recommendations panels.

**Chunk C — Runbook-of-runbooks meta-runbook.**
- Scope: §13 of this spec.
- Dependencies: Independent from A+B at authoring time. Reviewer-authored challenge scenarios (Part B of §13.4) require MP session AFTER Part A commits.
- Output: `operating-guide.md` + supersession notes on source documents.
- Single chunk, no sub-chunks.

---

## 17. Open Questions for R3

- **Q1 (R3).** Does `ops-ai-market` already have an `ops_role` or admin-access concept, or does Chunk A Gate 2 need to introduce auth field changes? Per R2 §10.7, no auth changes — confirm with Chunk A Gate 2 spec author that existing `X-Internal-API-Key` gate is sufficient.
- **Q2 (R3).** Are any of the existing `ops-ai-market` tabs (OPS, MONITOR, BUILD QUEUE, AGENTS) natural homes for SCHEDULES/RUNS/ATTENTION/RECOMMENDATIONS as sub-tabs, or is four sibling panels the right choice? Current R2 proposal: four sibling panels (keeps separation clean).
- **Q3 (R3).** `migration-manifest.yaml` location — `backend/config/` or `/mnt/manifests/`? Repo-local is simpler; the manifest is code-reviewable.
- **Q4 (R3).** Backup-verify three-way check (GH backup 03:00 + backend verify 03:30 + GH ci-verify 06:00) — is the third check redundant or does it provide distinct signal? R3 may consolidate.
- **Q5 (R3).** `run_id_authority=external_webhook` must still enforce idempotency per §5.4. If GH workflow retries its webhook call 3 times with same run_id, backend must dedupe. Is the deduplication window unbounded or time-bounded?
- **Q6 (R3).** Telegram direct-send from audit (§9.2 step 3) uses `TelegramRelay.send_message()` — does the audit share a rate-limit bucket with the main Telegram escalation path, and could audit bursts starve legitimate P0 sends?
- **Q7 (R3).** Operating-guide.md challenge-scenario reviewer — MP or AG? MP has better structural rigor; AG has better consumer-first framing. R2 proposes MP with AG fallback. R3 may let council decide.
- **Q8 (CLOSED R3).** Missed-escalation audit R4 rule ("missed schedule fire") is scoped to cron schedules only per R3 §9.2 Step 1 R4. State-predicate schedules and manual-only schedules are excluded (no predictable interval). `cron_expected_interval_seconds` is derived from the cron expression.
- **Q9 (R3).** Compound predicate logic: how often will v1 schedules genuinely need AND/OR? If > 20% of filed schedules want compound, R3 may elevate this to v1 scope; if < 5%, defer is fine.
- **Q10 (R3).** Backend `/api/v1/ops/*` prefix collides with existing OpsPanel routes on `/api/v1/ops/*`? Need Chunk A Gate 2 to confirm namespace is clear or choose sub-namespace like `/api/v1/ops/schedules/*`.

---

## 18. Review Targets

**MP R2 (primary, read-only).** Verify R1 findings closed:
- H1 (audit independence) — §9 now derives candidates from raw events via 6 independent rules, bypassing queue.
- H2 (execution semantics) — §4.2 adds `concurrency_policy`, `max_instances`, `misfire_grace_time_seconds`, `coalesce`; §4.4 defaults.
- H3 (migration completeness) — §5.5 table is closed; Celery Beat dispositions explicit; backup-verify staggered resolution.
- H4 (frontend topology) — §10 rewritten for `ops-ai-market` extension; no Next.js assumptions remain.
- M1 (idempotency) — §5.3/§5.4 specify `run_id_authority`, `attempt_number`, duplicate-completion semantics.
- M2 (enforcement) — §5.1 adds startup-assertion against `migration-manifest.yaml`.
- M3 (gh_actions coherence) — §5.6 classifies as external; sole-API invariant applies to backend-in-process only.
- M4 (comparator surface) — §6.1 enumerates 10 comparators.
- M5 (stewardship operational) — §7 adds bounded queue + rate isolation + degradation + split criterion.
- L1 (self-validation tautology) — §13.4 adds reviewer-authored challenge subset ≥ 5.

**AG cross-vote (after MP approves).** Consumer-first:
- Three consumer classes (§3) served by v1 deliverables?
- allAI stewardship coherent with existing brain role?
- ops.ai.market extension gives Max the right controls?
- Frequency-recommendation approval flow right-sized?

---

## Appendix A — Schedule Entity Example

```json
{
  "key": "schedule:weekly-runbook-stewardship-sweep",
  "kind": "schedule",
  "summary": "Weekly runbook-lint + staleness sweep across /Users/max/Projects/runbooks",
  "body": {
    "id": "weekly-runbook-stewardship-sweep",
    "name": "Weekly Runbook Stewardship Sweep",
    "description": "Runs runbook-lint against every .md in runbooks repo root + §J staleness eval, aggregates to weekly report entity, classifies via allAI.",
    "trigger_type": "cron",
    "cron_expression": "0 7 * * 1",
    "timezone": "UTC",
    "agent": "sysadmin",
    "dispatch_mode": "direct_callable",
    "callable_path": "app.agents.sysadmin.runbook_stewardship.run_sweep",
    "timeout_seconds": 900,
    "budget_usd": null,
    "escalation_target": "attention_queue",
    "priority": 2,
    "enabled": true,
    "concurrency_policy": "skip_if_running",
    "max_instances": 1,
    "misfire_grace_time_seconds": 3600,
    "coalesce": true,
    "run_id_authority": "executor",
    "owner": "max",
    "created_session": "S490"
  }
}
```

---

## Appendix B — Closed Migration Inventory

See §5.5 for full table. Manifest file location: `backend/config/migration-manifest.yaml`.

---

## Appendix C — allAI Backend Gap Remediation Plan

| Gap | Disposition |
|---|---|
| G1 P2+ flusher unwired | PREREQUISITE — follow-on BQ `bq-allai-escalation-flusher-wiring` |
| G2 Remediation callbacks unwired | Non-blocking |
| G3 Telegram callback format inconsistency | Non-blocking |
| G4 reply_markup dropped | Non-blocking |
| G5 Inbox model not unified | Non-blocking |
| G6 No cross-signal classifier | Non-blocking (rules-first sufficient for v1) |
| G7 Remediation proposals Redis-only | Non-blocking |
| G8 Delegate route unimplemented | Non-blocking |
| G9 Agent REST surface dynamic | Non-blocking |
| **G10 Core ops path doesn't write Living State** | **DELIVERABLE of this BQ** |

---

## Appendix D — Ops Frontend Stack Reference (R2 — new)

Existing `aidotmarket/ops-ai-market` stack (authoritative as of R2 authoring):
- **Build:** Vite 5.4
- **Framework:** React 18.3
- **Language:** TypeScript
- **Routing:** react-router-dom 6.30
- **State:** @tanstack/react-query 5.83
- **UI:** shadcn/ui + Tailwind CSS 3.4
- **Charts:** Recharts 2.15
- **Graphs:** ReactFlow
- **Markdown:** react-markdown 10
- **Forms:** react-hook-form 7.61
- **Auth:** Google OAuth (`src/hooks/useOpsAuth.ts`)
- **API:** `src/lib/api.ts` `apiFetch<T>(endpoint, options)` with `X-Internal-API-Key` from localStorage `insaits_api_config`
- **Routing model:** panel name in URL path `/panel`; `Panel` string-literal union in `src/pages/Index.tsx`
- **Deploy:** Railway static site (nginx via Dockerfile); DNS `ops.ai.market` → Railway service

---

## Appendix E — R1 → R2 Change Log

MP R1 task `5c85b3f3` returned REQUEST_CHANGES (4H+5M+1L). R2 closes all 10:

| Finding | Severity | R2 fix location |
|---|---|---|
| Missed-escalation audit gameable (relied on queue) | HIGH #1 | §9 rewritten with independent severity derivation rules R1–R6 + watchdog + self-escalation |
| Schedule schema omits execution semantics | HIGH #2 | §4.2 adds `concurrency_policy`, `max_instances`, `misfire_grace_time_seconds`, `coalesce`, `run_id_authority`; §4.4 defaults table |
| Migration table not closed (Celery + backup-verify dup) | HIGH #3 | §5.5 closed: Celery Beat 2-job migration specified; backup-verify 3-way stagger (GH backup 03:00 / backend verify 03:30 / GH ci-verify 06:00) |
| Frontend topology assumed Next.js greenfield | HIGH #4 | §10 rewritten for `ops-ai-market` extension; Appendix D added documenting existing stack |
| Idempotency model missing | MEDIUM #1 | §5.3 adds `run_id_authority` + `attempt_number`; §5.4 adds duplicate-completion semantics |
| Lint can't prove registry-completeness | MEDIUM #2 | §5.1 adds startup-assertion against `migration-manifest.yaml` |
| gh_actions_webhook not coherent as sole-API | MEDIUM #3 | §5.6 rewritten; mode renamed `gh_actions_external`; classified as external-schedule; sole-API invariant applies to backend-in-process only |
| Comparator surface underspecified | MEDIUM #4 | §6.1 adds 10-comparator table |
| Stewardship rationale conceptual not operational | MEDIUM #5 | §7.3–§7.6 adds bounded queue + rate isolation + degradation + split criterion |
| Self-validation tautological | LOW #1 | §13.4 adds reviewer-authored challenge subset ≥ 5 + dual-set acceptance criterion |

R1 → R2 net diff expected: ~+300 / -100 lines (R1 711 → R2 ~900).

---

## Appendix F — R2 → R3 Change Log

MP R2 task `4b56cce5` returned REQUEST_CHANGES (1H+1M+1L). R3 closes all 3 while all 10 R1 findings remain closed:

| Finding | Severity | R3 fix location |
|---|---|---|
| Event taxonomy inconsistency (`schedule.run.complete` vs `schedule.run.failed/timeout`) | HIGH #1 | §5.4 adds sole-completion-event contract paragraph; §7.2 subscription narrowed to only `schedule.run.complete` with `status` field filtering; §9.2 Step 1 rules R1/R2/R3/R5 rewritten to filter on `schedule.run.complete` with status discriminator; Gate 3 test requirement added for "no non-`schedule.run.complete` events emitted for run lifecycle" |
| R4/R6 audit rule under-specification (`expected_interval` undefined for non-cron; correlation key missing) | MEDIUM #1 | §9.2 Step 1 R4 explicitly scoped to cron schedules only; `cron_expected_interval_seconds` derivation specified; §9.2 Step 2 per-rule correlation keys enumerated (R1/R2/R3/R5 use `run_id`; R4 uses `schedule_id + expected_fire_at`; R6 uses `schedule_id + predicate_evaluated_at`); Gate 3 test for `correlation_*` fields in Telegram-send body |
| §13.4 challenge-scenario source-of-truth split | LOW #1 | §13.4 Part B + Combined Acceptance rewritten: inline §I with author-attribution partitioning is the single source of truth; no external `reviewer-challenge/` directory; harness loader adds author-attribution-based partition scoring |

R2 → R3 net diff: ~+60 / -30 lines, all in §5.4, §7.2, §9.2, §13.4, §17 Q8, header + new Appendix F. Narrow, targeted, no structural changes.
