# BQ-AUTONOMOUS-OPERATIONS — Gate 1 (R1)

**Parent BQ:** `build:bq-autonomous-operations`
**Gate:** 1
**Revision:** R1 (S489)
**Author:** Vulcan
**Repo:** aidotmarket/runbooks
**Spec path:** specs/BQ-AUTONOMOUS-OPERATIONS.md
**Discovery entity:** `project:bq-autonomous-operations-discovery-findings` v3
**Scope decisions source:** `build:bq-autonomous-operations` v2 `body.scope_decisions_locked_s489`

## 0. Executive Summary

Autonomous Operations builds the infrastructure that lets Market agents run recurring operational work (runbook compliance sweeps, backup verification, council-stall detection, secret rotation freshness, etc.) without Max prompting. Triggers are time-based (cron) AND state-predicated (e.g. "fire if last `backup-verify` event > 48h old"). Every autonomous run emits an event. allAI classifies results and either resolves-to-silent-success, queues for session-open digest, or escalates P0+ via Telegram.

V1 ships three parallel chunks:

1. **Backend** — schedule registry as first-class Living State entity kind + sole-API scheduler executor (APScheduler wrapped as internal substrate in v1; zero surviving direct APScheduler or `@cron` decorator use in backend code post-v1) + allAI stewardship role formalization + attention queue entity kind + missed-escalation audit meta-cron.
2. **Frontend** — greenfield `ops.ai.market` surface with proper host routing, auth gate distinct from buyer/seller dashboard gating, Next.js pages for agent/schedule/run management.
3. **Content** — consolidated runbook-of-runbooks meta-runbook authored against the Runbook Standard (§A–§K-conformant; eats its own dogfood; doubles as a proof-point that the standard works on operational content).

First concrete cron: weekly runbook stewardship sweep running `runbook-lint` across every runbook + §J staleness evaluation, writing a report entity consumed by the attention queue.

This spec establishes the design. Gate 2 produces implementation specs per chunk. Gate 3 is the build.

---

## 1. Problem Statement

**Current state.** Every agent action in the Market requires Max's explicit prompt. Sessions are human-in-the-loop; sessionless autonomous work does not happen. Operational drift (stale runbooks, missed backups, quiet council stalls, unchecked secret age, etc.) accumulates invisibly until Max either notices a symptom or a catastrophic failure surfaces the drift for him. The Market's mandate is that **AI agents run it**; a human prompting every action is the opposite of that mandate.

**End state.** Max opens a session and gets a digest of what ran while he was gone, what succeeded, what's waiting on him. Recurring operational work happens on its own cadence. When autonomous runs detect state the agents can't resolve, allAI classifies severity and either queues for Max's next session (non-urgent) or escalates to Telegram (P0/P1). Every run leaves footprints — silent failures are detectable by construction.

**Why now.** BQ-RUNBOOK-STANDARD Gate 2 Chunk 2 landed (approved 2026-04-22 at commit `4886604`), defining how D4 Infisical + D5 AIM Node G4 runbooks get authored. The standard is only useful if runbooks get kept current and agents actually use them — both of which require autonomous stewardship. Without this BQ, the runbook standard is a static document set that rots.

---

## 2. Scope

### 2.1 In-scope v1 (cross-referenced to `build:bq-autonomous-operations` v2)

Backend:
- Schedule registry as first-class Living State entity kind (`schedule:*`).
- Scheduler service: evaluates registry every minute, fires due schedules, dispatches via `council_request` or direct callable.
- Pure-replace executor contract — APScheduler wrapped as internal substrate in v1; zero direct APScheduler or `@cron` decorator usage in backend code after migration.
- Time-based triggers (cron) AND state-predicated triggers (predicate language in §7).
- allAI stewardship role formalized on `AllAIBrainAgent` — receives all autonomous-run reports, classifies severity, escalates, writes attention-queue items.
- Attention-queue Living State entity kind (`queue:attention`) consumed at `kd_session_open`.
- Missed-escalation audit meta-cron (detects P0-looking items sitting unescalated > N hours; self-escalates).
- GH-Actions-delegated execution mode for CI-shaped jobs (registry declares, CI executes, registry reads results via webhook).

Frontend (`ops.ai.market` greenfield):
- Host routing for `ops.ai.market` in `next.config.ts` + `middleware.ts`.
- Auth gate distinct from buyer/seller dashboard gating (email allowlist or explicit ops-role RBAC).
- Agent inventory page (list registered agents, health, last run, last heartbeat).
- Schedule management page (list, toggle on/off, edit cron or predicate, view last-run status + next-run estimate).
- Run history page per schedule (last N runs, duration, outcome, link to event ledger or result artifact).
- Manual-trigger affordance (fire a schedule now, bypass cadence).
- allAI frequency-recommendation surface (notification badge, review + accept/reject flow for proposed schedule changes).

Content:
- Runbook-of-runbooks meta-runbook consolidating `agent-dispatch.md` + `session-lifecycle.md` + `council-gate-process.md` + `council-hall-deliberation.md` + `vulcan-configuration.md` into a single §A–§K-conformant runbook authored against the frozen Runbook Standard at commit `365c198`.

First concrete cron:
- `schedule:weekly-runbook-stewardship-sweep` — runs `runbook-lint` across `/Users/max/Projects/runbooks/*.md` + §J staleness evaluation; writes `project:runbook-stewardship-report-YYYY-WW` entity; classifies via allAI; queues findings ≥ WARN for session digest, escalates FAIL to Telegram.

### 2.2 Out-of-scope v1

- Agent-initiated schedule changes without Max approval. Every adjustment goes through the ops console; allAI can *recommend*, only Max approves.
- Multi-agent deliberative autonomy (agents negotiating work among themselves). Future BQ.
- Predictive/ML-driven frequency recommendations beyond simple operational signals (see §12). Future BQ.
- Replacing human-in-the-loop for any P0+ decision.
- Native executor replacement for APScheduler — v1 keeps APScheduler as internal substrate. Swap-out is a later BQ.
- Migration of non-backend scheduled work (e.g. Railway-side services, cron-like services outside backend process). Out of v1.

---

## 3. Consumer Model

Autonomous Operations infrastructure has three consumer classes. Gate 1 names them explicitly so Gate 2 and 3 acceptance criteria can bind.

**C1 — Schedule authors (agents + Max).** The party who adds a `schedule:*` entity or edits one. Max authors via ops console. Agents (e.g. allAI in frequency-recommendation mode) author via state_request after Max approval. Consumer contract: the registry API is stable and versioned, entity schema is enforced, validation errors are precise, editing a schedule never loses run history.

**C2 — Scheduled agents (executors).** The agent that runs when a schedule fires. Consumer contract: at fire time, the agent receives a well-formed dispatch envelope including the schedule id, the trigger that fired, any predicate-evaluation result, budget caps, and allowed_tools. On completion, the agent emits a structured result event that the registry consumes for `last_run_status`.

**C3 — Stewardship + escalation consumers (allAI + Max).** The parties who observe outcomes. allAI subscribes to all autonomous-run events, classifies, and either silently resolves, queues, or escalates. Max consumes the attention queue at session open and the Telegram stream continuously. Consumer contract: every run emits an event that allAI can classify; severity ladder is well-defined; missed-escalation audit proves P0 items don't sit silently.

---

## 4. Schedule Registry Design (answers Q5)

### 4.1 Entity kind

New Living State entity kind: `schedule`. Key convention: `schedule:<dashed-name>`, e.g. `schedule:weekly-runbook-stewardship-sweep`.

### 4.2 Required fields

| Field | Type | Required | Purpose |
|---|---|---|---|
| `id` | string | yes | Derived from key; stable across versions |
| `name` | string | yes | Human-readable display name |
| `description` | string | yes | What this schedule does, in 1–3 sentences |
| `trigger_type` | enum | yes | `cron` \| `state_predicate` \| `manual_only` |
| `cron_expression` | string | conditional | Required when `trigger_type=cron`; 5-field cron |
| `timezone` | string | conditional | IANA tz; required when `trigger_type=cron`; default `UTC` |
| `predicate` | object | conditional | Required when `trigger_type=state_predicate`; shape per §7 |
| `evaluation_cadence_seconds` | integer | conditional | Required when `trigger_type=state_predicate`; min 60 |
| `agent` | string | yes | Target agent: `mp`, `ag`, `xai`, `cc`, `sysadmin`, `allai-brain`, `crm-steward`, etc. |
| `dispatch_mode` | enum | yes | `council_request` \| `direct_callable` \| `gh_actions_webhook` |
| `task_prompt` | string | conditional | Required for `council_request` mode |
| `callable_path` | string | conditional | Required for `direct_callable` mode; Python dotted path |
| `gh_workflow_path` | string | conditional | Required for `gh_actions_webhook` mode; `.github/workflows/X.yml` |
| `council_mode` | enum | conditional | Required for `council_request` mode: `review` \| `build` |
| `allowed_tools` | array | optional | Tool restriction for MP dispatches |
| `timeout_seconds` | integer | yes | Hard wall-clock cap; default 600 |
| `budget_usd` | number | conditional | Required for LLM-invoking dispatches; default 1.0 |
| `escalation_target` | enum | yes | `telegram_p0_p1` \| `attention_queue` \| `silent_success_only` |
| `priority` | integer | yes | 0–3, matching existing `_PRIORITY_MAP`; determines escalation-pipeline routing |
| `enabled` | boolean | yes | Disabled schedules don't fire; default `true` |
| `paused_until` | datetime | optional | Soft pause; if set and in future, schedule does not fire |
| `last_run_at` | datetime | auto | Updated by executor on fire |
| `last_run_status` | enum | auto | `success` \| `failure` \| `timeout` \| `agent_error` \| `dispatch_error` |
| `last_run_task_id` | string | auto | Council task_id or dispatch id for traceability |
| `last_run_result_entity_key` | string | auto | Living State key of result artifact (if applicable) |
| `next_run_at` | datetime | auto | Computed from cron or predicate evaluation window |
| `run_count_total` | integer | auto | Monotonic count |
| `run_count_failure` | integer | auto | Monotonic failure count for frequency-recommendation signal |
| `owner` | string | yes | Responsible human for this schedule; default `max` |
| `created_session` | string | yes | Session in which this schedule was created |
| `last_edited_by` | string | auto | Last editor (agent or user id) |

### 4.3 Schedule lifecycle states

- `enabled=true` — normal operation; fires on trigger match
- `enabled=false` — disabled by Max; registry retains entity + history; does NOT fire
- `paused_until=<future>` — soft pause (e.g. during incident response); auto-resumes at `paused_until`
- `deleted` — entity removed from Living State; retain run history in event ledger; not recoverable via UI (requires direct Living State operation)

State transitions are enforced by registry CRUD validators; v1 ships a JSON Schema at `backend/app/services/schedule_registry/schemas/schedule.schema.json`.

### 4.4 History retention

- Last 100 runs per schedule kept in `schedule:<id>.body.run_history` (bounded array, truncated oldest-first).
- Older runs are event-ledger-only — no duplication of data.
- `run_count_total` + `run_count_failure` are monotonic counters preserved across truncation for frequency-recommendation signal quality (see §12).

---

## 5. Scheduler Executor Design (D3 — pure replace)

### 5.1 Sole-API invariant

The registry IS the scheduling API for anything running inside the ai-market-backend process. After v1 migration completes, the following MUST be true:

- Zero `import apscheduler` statements in backend code outside of the registry's internal substrate module.
- Zero `@cron(...)` or equivalent decorator usage in backend code.
- Zero direct APScheduler `add_job(...)` calls outside the registry's internal substrate.
- Every recurring in-process job has a corresponding `schedule:*` Living State entity.

Enforcement: a lint check in backend CI at Gate 3; blocks any PR that introduces direct APScheduler usage outside the substrate module.

### 5.2 Internal substrate (APScheduler in v1)

The registry's executor module (`app/services/schedule_registry/executor.py`) owns the single APScheduler instance for the backend process. On startup, the executor:

1. Reads all `schedule:*` entities from Living State.
2. For each `enabled=true` schedule where `trigger_type=cron`, registers an APScheduler job.
3. For each `enabled=true` schedule where `trigger_type=state_predicate`, registers an APScheduler interval job at the `evaluation_cadence_seconds` that evaluates the predicate and fires the schedule on match.
4. Subscribes to Living State change events for `schedule:*` entities; on edit/add/delete, updates the APScheduler registration.

APScheduler handles misfire policy, concurrent-run limits, clock skew, DST. These are the hard reliability problems v1 deliberately does NOT re-solve; they're inherited from APScheduler. Swap-out to a native executor is a later BQ once the registry contract is proven in production.

### 5.3 Dispatch envelope

When a schedule fires, the executor assembles a dispatch envelope:

```json
{
  "schedule_id": "schedule:weekly-runbook-stewardship-sweep",
  "schedule_name": "Weekly Runbook Stewardship Sweep",
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
  "priority": 2,
  "run_id": "run-<uuid>"
}
```

For `trigger_type=state_predicate`, the envelope also includes `trigger.predicate_evaluation_result` (truth value + triggering fact).

### 5.4 Result event contract

On completion (success, failure, timeout), the executing agent emits a `schedule.run.complete` event:

```json
{
  "event_type": "schedule.run.complete",
  "schedule_id": "schedule:weekly-runbook-stewardship-sweep",
  "run_id": "run-<uuid>",
  "started_at": "2026-04-22T07:00:00Z",
  "completed_at": "2026-04-22T07:04:12Z",
  "status": "success",
  "result_entity_key": "project:runbook-stewardship-report-2026-W17",
  "task_id": null,
  "summary": "Linted 30 runbooks; 3 staleness WARN, 0 FAIL.",
  "severity": "info"
}
```

Executor consumes the event, updates `last_run_*` fields on the schedule entity. allAI also subscribes (see §8).

### 5.5 Migration plan for existing APScheduler + Celery jobs

Existing backend scheduled work identified in discovery (see Appendix B):

| Current Location | Migration Target |
|---|---|
| `app/core/scheduler.py:830-849` SysAdmin 5min health | `schedule:backend-sysadmin-health-check-5m` (cron `*/5 * * * *`) |
| `app/core/scheduler.py:830-849` Daily 03:00 UTC backup verify | `schedule:backend-backup-verify-daily` (cron `0 3 * * *`) |
| `IncidentSweeper` 300s loop | `schedule:backend-incident-sweeper-5m` (cron `*/5 * * * *`) |
| `BaseAgent` heartbeat (90s TTL) | Keep in `BaseAgent`; NOT migrated — heartbeat is per-instance lifecycle, not a schedule |
| `CRMStewardAgent` daily maintenance timer | `schedule:crm-steward-daily-maintenance` (cron `0 <DAILY_MAINTENANCE_HOUR_UTC> * * *`) |
| SysAdmin proactive monitors | `schedule:backend-sysadmin-monitor-<name>` per monitor |
| Telegram remediation per-proposal timeouts | Keep ephemeral; not migrated — these are short-lived per-request timers, not schedules |
| Celery Beat (`app/tasks/scheduled.py`) | Audit during Gate 2 Chunk A; migrate if actively used; retire if dead code |

Migration rule: a job is "migrated" when (a) a `schedule:*` entity exists, (b) the old APScheduler registration is removed, (c) the schedule fires on the same cadence as the old job, (d) result events flow to allAI, (e) the backend-CI lint check passes confirming no direct APScheduler use remains outside the substrate.

### 5.6 GH-Actions-delegated execution mode

For CI-shaped jobs that genuinely belong in GitHub Actions (smoke tests, deploy validations), the registry declares the schedule but CI runs it. Mechanism:

1. Schedule entity has `dispatch_mode=gh_actions_webhook` and `gh_workflow_path=.github/workflows/<name>.yml`.
2. Registry does NOT fire the job; GH Actions fires on its own cron (preserved in the workflow file).
3. Workflow emits a webhook to `/api/v1/schedules/<id>/run-result` on completion.
4. Registry receives the webhook, writes `last_run_*` fields, emits `schedule.run.complete` event.
5. allAI subscribes normally; escalation flows are identical to in-process jobs.

Authority on the cron expression: source of truth remains the `schedule:*` entity. On any edit of the cron in the registry, ops console shows a warning that the workflow file must be updated to match; Gate 3 may add a reconciliation check.

Migration recommendations from discovery (Appendix B):
- `ai-market-backend/backup.yml` → `schedule:gh-backup-daily` (gh_actions_webhook)
- `ai-market-backend/backup-verify.yml` → `schedule:gh-backup-verify-daily` (gh_actions_webhook)
- `ai-market-backend/health-check.yml` → `schedule:gh-health-check-daily` (gh_actions_webhook)
- `ai-market-backend/quarantine-weekly.yml` → `schedule:gh-quarantine-weekly` (gh_actions_webhook)
- `runbooks/runbook-harness.yml` → `schedule:gh-runbook-harness-daily` (gh_actions_webhook)
- `ai-market-backend/smoke-test.yml` → NOT migrated (coexist); stays CI-native (6h high-frequency; not operationally interesting to allAI)

---

## 6. State-Predicate Triggers (answers Q5 predicate shape)

### 6.1 Predicate language

State predicates are expressed as JSON objects interpreted by the scheduler's predicate engine. Two forms in v1:

**Form A — event-age predicate.**
```json
{
  "kind": "event_age_exceeds",
  "event_type": "backup.verify.complete",
  "threshold_seconds": 172800
}
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
Fires if the entity field evaluates the comparator against the value to `true`.

V1 supports these two forms only. Form C (compound logic: AND/OR of predicates) is deferred to a follow-on BQ; v1 schedules needing compound logic should be split into multiple schedules or use a `direct_callable` that evaluates complex logic internally.

### 6.2 Evaluation cadence

Predicates are evaluated on the schedule's `evaluation_cadence_seconds` (min 60s). Evaluation is cheap (single Living State or event-ledger query); 60s resolution is adequate for all v1 use cases. Predicate evaluation itself emits `schedule.predicate.evaluated` events at DEBUG severity for auditability.

### 6.3 Debouncing

To prevent storm-firing when a predicate stays true across multiple evaluation windows, the registry tracks `last_predicate_true_fire_at`. If the predicate was true at the last evaluation AND the schedule already fired within the last `max(evaluation_cadence_seconds * 2, 300s)`, it does not fire again until the predicate returns false at least once.

---

## 7. allAI Stewardship Role (answers Q4)

### 7.1 Role placement

Stewardship lands on `AllAIBrainAgent` at `app/allai/agents/allai_brain.py`. Rationale: the brain is already the Tier 0 wildcard subscriber, already does incident triage + escalation + remediation proposals. Adding "autonomous-run reports" as another event class it subscribes to is coherent with the existing role shape and avoids creating a new agent with overlapping responsibilities.

Council is invited to challenge this during R1 review. If MP or AG recommend a dedicated `AllAIStewardAgent` (distinct from the brain), R2 will revisit.

### 7.2 Subscription

`AllAIBrainAgent.startup()` adds `schedule.run.complete` and `schedule.run.failed` to its subscription list. On receipt:

1. Classify severity using existing `_PRIORITY_MAP` + schedule metadata (priority field, escalation_target).
2. Route:
   - `silent_success_only` → log to agent-log and drop.
   - `attention_queue` → enqueue `queue:attention` item (see §8).
   - `telegram_p0_p1` + severity P0/P1 → immediate Telegram via existing escalation pipeline.
   - `telegram_p0_p1` + severity P2+ → attention queue fallback (respecting existing P2+ batch semantics if the unwired flusher gap G1 is closed in parallel).

### 7.3 Gap remediation dependencies

The backend discovery (Appendix C) identified 10 gaps in allAI. The following are **prerequisite to BQ-AUTONOMOUS-OPERATIONS Gate 3 build**:

- G1 (P2+ escalation flusher unwired) — MUST be closed before autonomous-ops launches; otherwise P2 attention-queue-bound items queue indefinitely in Redis. A follow-on BQ `bq-allai-escalation-flusher-wiring` should be filed during Gate 2 authoring.
- G10 (core ops path does not persist to Living State) — this BQ's registry + event flow is precisely that integration; G10 closure is a DELIVERABLE of this BQ, not a prerequisite.

Gaps G2–G9 are independent of autonomous-ops v1 and do not block. They may become follow-on BQs at Max's discretion.

---

## 8. Attention Queue Entity Kind (answers Q6)

### 8.1 Entity kind

New kind: `queue:attention`. Single entity with key `queue:attention` — not per-item keys; items live in `body.items` as a bounded array.

### 8.2 Item shape

```json
{
  "item_id": "att-<uuid>",
  "created_at": "2026-04-22T07:04:12Z",
  "source_schedule_id": "schedule:weekly-runbook-stewardship-sweep",
  "source_run_id": "run-<uuid>",
  "source_event_ledger_id": "<event_id>",
  "severity": "warn",
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
| `debug` | Diagnostic trace; not queued | Agent log only |
| `info` | Successful run; observed, not queued | Agent log only |
| `warn` | Non-urgent drift; handle at next session | Attention queue, no Telegram |
| `p2` | Degraded operation; batch to Telegram digest | Attention queue + P2 batch (requires G1 flusher) |
| `p1` | Urgent; immediate Telegram | Immediate Telegram + attention queue |
| `p0` | Critical; immediate Telegram + persistent until acknowledged | Immediate Telegram + attention queue + re-ping if unacked > 1h |

### 8.4 Session-open consumption

On `kd_session_open`, the session-open bundle SHOULD include the attention queue (all `resolved=false` items sorted by severity desc, created_at desc). Items are NOT auto-resolved by session open; Max acknowledges explicitly via ops console or by running the suggested action. Ack is a state_request patch setting `resolved=true`.

Retention: resolved items > 90 days old are purged in a nightly `schedule:attention-queue-purge-resolved` cron (not user-visible; self-stewardship).

---

## 9. Missed-Escalation Audit

### 9.1 Motivation

allAI classification is the single point of escalation decision. If the classifier drops a P0 item (miscategorized as info, or routed to attention queue when it should have gone to Telegram), Max doesn't learn until he next opens a session — or never. This breaks the trust contract that P0 is escalated.

### 9.2 Audit mechanism

A meta-cron `schedule:missed-escalation-audit-hourly` runs every hour:

1. Scan `queue:attention` for items where (`severity` in [`p0`, `p1`]) AND (`resolved=false`) AND (`created_at` > 2h ago).
2. For each match, scan Telegram send-history (event ledger `telegram.send`) for a send event referencing the item's `source_event_ledger_id` within the original item creation window.
3. Items with no matching Telegram send event are flagged: emit `autonomous_ops.missed_escalation_detected` event at severity P1 AND immediately enqueue to `queue:attention` as a P1 item with source_schedule_id pointing to the audit itself.
4. Self-escalation: the audit emits a Telegram message directly (bypassing the classifier it's auditing).

### 9.3 Acceptance

The audit is NON-NEGOTIABLE for v1 (per original BQ design principle). Gate 3 build must include an end-to-end test where a deliberately-misclassified P0 item is caught by the audit within 2h and escalated to Telegram.

---

## 10. ops.ai.market Frontend (D1)

### 10.1 Host routing

`next.config.ts`:
- Add `ops.ai.market` as a recognized host.
- Rewrite rule: requests to `ops.ai.market/*` serve pages from the `/ops/*` route namespace in the Next.js app.
- Preserve existing `www.ai.market` canonicalization; `ops.ai.market` is NOT canonicalized to `www.`.

`middleware.ts`:
- Gate all `/ops/*` routes behind ops-role auth (see §10.2).
- Unauthenticated requests redirect to `/login?returnTo=/ops/<path>`.

### 10.2 Auth gate

Current buyer/seller dashboard gating (`app/dashboard/layout.tsx` client-side role check + email-based "Blog Admin") is NOT reused. New ops RBAC:

- Backend adds `ops_role` field to the `user` model (values: `none` | `read` | `admin`; default `none`).
- Max gets `admin` via manual DB migration (Gate 3 seed data).
- `/ops/*` routes require `ops_role` in (`read`, `admin`). Write operations (schedule edit, manual trigger) require `admin`.
- New API endpoint `GET /api/v1/auth/ops-context` returns `{ ops_role, permitted_actions }`; frontend caches and uses for client-side UI gating (though server-side middleware is authoritative).

### 10.3 Pages

- `/ops` — landing dashboard (agent count, schedule count, attention-queue unresolved count, last 10 runs across all schedules).
- `/ops/agents` — agent inventory (name, health, last heartbeat, registered schedules count).
- `/ops/agents/[key]` — per-agent detail (manifest, health history, run history, schedules).
- `/ops/schedules` — all schedules (filterable by agent, enabled, trigger_type).
- `/ops/schedules/[id]` — schedule detail (full entity, run history, edit form, manual-trigger button).
- `/ops/schedules/new` — create schedule form.
- `/ops/runs` — run history across all schedules (filterable).
- `/ops/runs/[id]` — run detail (envelope, result event, agent-log excerpt link).
- `/ops/attention` — attention queue (unresolved items, ack/resolve affordance).
- `/ops/recommendations` — allAI frequency recommendations (see §12).

### 10.4 TypeScript types

New file `types/ops.ts`:
- `Agent` — { key, name, status, last_heartbeat_at, schedule_count }
- `Schedule` — full mirror of the registry entity body (§4.2)
- `Run` — { schedule_id, run_id, started_at, completed_at, status, summary, severity }
- `AttentionItem` — mirror of §8.2 shape
- `FrequencyRecommendation` — { schedule_id, current_cadence, recommended_cadence, rationale, signals, proposed_at, status }

### 10.5 API wrappers

New file `api/ops.ts`:
- `listAgents()`, `getAgent(key)`
- `listSchedules(filters)`, `getSchedule(id)`, `createSchedule(body)`, `updateSchedule(id, patch)`, `deleteSchedule(id)`, `toggleSchedule(id, enabled)`, `triggerSchedule(id)`
- `listRuns(filters)`, `getRun(runId)`
- `listAttentionItems(filters)`, `resolveAttentionItem(itemId, note)`
- `listFrequencyRecommendations()`, `acceptRecommendation(recId)`, `rejectRecommendation(recId, reason)`

### 10.6 State management

Use React Query explicitly for the ops surface — it's already provided at `components/Providers.tsx` but underused in the existing dashboard. Every API wrapper gets a corresponding query key and mutation hook. Optimistic updates for toggle + manual trigger; invalidation on create/update/delete.

---

## 11. Frequency-Recommendation Surface (answers Q9)

### 11.1 Signal sources

allAI computes recommendations using four signals:

1. **Run duration trend** — moving average of run duration over last 10 runs. If duration is monotonically increasing or volatile, flag for review.
2. **Failure rate** — `run_count_failure / run_count_total` over last 20 runs. If > 20%, recommend investigating (not necessarily frequency change).
3. **State-drift observed** — for schedules whose result artifact is a periodic comparison (e.g. runbook staleness), compare deltas across runs. If drift is negligible between runs at current cadence, recommend reducing cadence. If drift is large, recommend increasing.
4. **Session-prompted interventions** — scan session logs (Vulcan history) for Max-prompted operational work that matches an existing schedule's domain. If Max is frequently doing X manually AND schedule X exists, it may be firing too infrequently.

### 11.2 Recommendation generation

A daily `schedule:allai-frequency-recommendations-daily` cron runs at 02:00 UTC, evaluates signals across all schedules, writes recommendations to Living State as `recommendation:*` entities, and emits an `allai.recommendation.new` event per new recommendation.

### 11.3 Max approval flow

Frontend `/ops/recommendations` page lists pending recommendations. Max reviews each with current-vs-recommended cadence + rationale + signal summary; clicks Accept or Reject.

- Accept → API issues a `PATCH /api/v1/schedules/<id>` with the new cadence; recommendation entity marked `status=accepted`.
- Reject with reason → recommendation entity marked `status=rejected`; reason stored; used as training signal (informally) for future recommendation tuning.

Recommendations older than 30 days with `status=pending` are auto-purged in a weekly cleanup cron.

---

## 12. Runbook Usage Enforcement (answers Q7)

### 12.1 Decision: both (policy + audit), staged

Policy-layer (strict): support-dispatched agents must cite a runbook section in their response. Enforced at dispatch-time by adding a required `runbook_citations` field to the support agent response envelope. Requires instrumenting each support-dispatched agent (CRM Steward, SysAdmin, etc.).

Audit-layer (lax): allAI periodically reviews agent responses sampled from the past 24h and scores runbook-citation rate. Missing citations below threshold emit a warning to the attention queue.

### 12.2 Staging

V1 ships audit-layer only. Policy-layer requires instrumenting multiple agents (substantial surgery) and risks breaking existing dispatches. Audit-layer is additive and observational — it surfaces the gap without changing behaviour.

Follow-on BQ `bq-runbook-policy-enforcement` picks up the policy layer after audit-layer data shows which agents are worst offenders and what the citation-rate distribution looks like.

### 12.3 Audit cron

`schedule:allai-runbook-citation-audit-daily` — samples 20 support-dispatched runs from the last 24h; for each, allAI reads the runbook relevant to the request and scores whether the agent's response aligns with the runbook + cites it. Scores below 0.5 emit a WARN attention item referencing the run.

---

## 13. Runbook-of-Runbooks Deliverable (D2)

### 13.1 Consolidation scope

Source documents (all in `/Users/max/Projects/runbooks`, pre-standard):
- `agent-dispatch.md` (8,423 bytes) — how agents are dispatched, council conventions
- `session-lifecycle.md` — `kd_session_*` mechanics
- `council-gate-process.md` (5,006 bytes) — how code gets reviewed/approved/shipped through the BQ system
- `council-hall-deliberation.md` (7,151 bytes) — multi-agent deliberation process
- `vulcan-configuration.md` — Vulcan context hydration + memory architecture

### 13.2 Consolidation form

Single new runbook at `/Users/max/Projects/runbooks/operating-guide.md` authored §A–§K-conformant to the Runbook Standard at commit `365c198`. Structure:

- §A (System + scope) — "Operating Guide: how work flows through the Market's autonomous systems."
- §B (Capabilities Matrix) — what the operating system does (session management, agent dispatch, council reviews, gate flow, Living State, scheduling).
- §C (Architecture) — components: Koskadeux MCP gateway, Living State, council agents, Vulcan, allAI, schedule registry.
- §D (Agent Capability Map) — which agent does what.
- §E (Operate) — normal operational flow scenarios.
- §F (Isolate) — diagnosing deviations.
- §G (Repair) — resolving common breakages.
- §H (Evolve) — change-class taxonomy for Market infrastructure itself.
- §I (Acceptance Criteria) — stateless-agent harness scenarios ≥10.
- §J (Lifecycle) — staleness rules, refresh cadence.
- §K (Migration) — this is a from-scratch authoring (not a retrofit); §K.retrofit=false.

### 13.3 Relationship to source documents

Source documents are NOT deleted in v1 (reduce blast radius). operating-guide.md is canonical; source documents get a header note "SUPERSEDED — see operating-guide.md" pointing to the new file. A follow-on cleanup BQ can delete source files once operating-guide.md has been stable for 30+ days.

### 13.4 Stateless-agent harness self-validation

Per Runbook Standard §I, operating-guide.md must include ≥ 10 Vulcan-authored self-assertion scenarios + pass `runbook-harness --runbook operating-guide.md --mode conformant` at ≥ 80% weighted score. This is Gate 3 acceptance for this chunk.

---

## 14. First Concrete Cron: Runbook Stewardship Sweep

`schedule:weekly-runbook-stewardship-sweep`
- Trigger: cron `0 7 * * 1` (Mondays 07:00 UTC)
- Agent: `sysadmin`
- Dispatch: `direct_callable` → `app.agents.sysadmin.runbook_stewardship.run_sweep`
- Actions:
  1. `runbook-lint` across every `.md` in `/Users/max/Projects/runbooks` root (excluding `specs/`, `tests/`, `templates/`, `harness/`, `runbook_tools/`).
  2. For each runbook, evaluate §J staleness predicate.
  3. Aggregate results into `project:runbook-stewardship-report-YYYY-WW` entity.
  4. Emit `schedule.run.complete` event with summary.
- Severity derivation:
  - Any runbook FAILS lint → result severity P1.
  - Any runbook has §J staleness violation above grace period → severity P2.
  - Any runbook has §J staleness warning within grace period → severity WARN.
  - All OK → severity info.
- Result entity retention: last 12 weekly reports retained; older entities purged by `schedule:stewardship-report-purge-quarterly`.

---

## 15. Acceptance Criteria (Gate 1 closure)

Gate 1 is APPROVED when MP primary review + AG cross-vote both concur with verdict ≥ APPROVE_WITH_NITS on R_N of this spec. Specifically the design must establish:

1. **AC1 — Schedule entity schema complete and JSON-Schema-expressible.** §4.2 fields are necessary and sufficient; no ambiguity about which fields are required when.
2. **AC2 — Pure-replace executor contract clear.** §5.1 sole-API invariant + §5.2 substrate model + §5.5 migration plan form a coherent whole.
3. **AC3 — State-predicate language sufficient for v1 use cases.** §6 Form A + Form B cover the identified v1 cron needs; compound logic deferral is explicit.
4. **AC4 — allAI stewardship role placement defensible.** §7.1 rationale for placing stewardship on `AllAIBrainAgent` addresses why NOT a new agent; council is explicitly invited to challenge.
5. **AC5 — Attention queue + severity ladder + session-open integration sound.** §8 specifies entity shape, routing rules, resolution mechanism, retention.
6. **AC6 — Missed-escalation audit is non-gameable.** §9 audit cannot be silently suppressed by the same classifier it's auditing; self-escalation bypasses the classifier.
7. **AC7 — ops.ai.market scope includes host routing, auth gate distinct from buyer/seller, page inventory, data shapes, API wrappers.** §10 complete enough that Gate 2 can spec without re-deliberation.
8. **AC8 — Frequency-recommendation signals + approval flow specified.** §11 signals are computable from existing data (event ledger, run_count_*, session logs); Max approval is required for every change.
9. **AC9 — Runbook-enforcement policy vs audit decision made with staging rationale.** §12 audit-first-then-policy is justified.
10. **AC10 — Runbook-of-runbooks consolidation scope identifies source docs, form, and §I harness validation.** §13 concrete enough to start Gate 2 authoring.
11. **AC11 — Gate 2 chunking proposal is viable.** Three chunks (backend, frontend, content) can be specified and built somewhat in parallel, with clear inter-chunk contract boundaries.
12. **AC12 — Gap remediation dependencies explicit.** §7.3 names G1 as prerequisite (flusher wiring) and G10 as deliverable; others non-blocking.
13. **AC13 — Backward-compat with existing scheduled infrastructure specified.** §5.5 migration table + §5.6 GH-Actions delegation cover every cron found in discovery.
14. **AC14 — Open questions R2 should resolve are named** (see §17).

---

## 16. Gate 2 Chunking Proposal

Three chunks, specified somewhat in parallel with clear contract boundaries.

**Chunk A — Backend schedule registry + executor + allAI stewardship + attention queue + missed-escalation audit.**
- Scope: §4, §5, §6, §7, §8, §9 of this spec.
- Dependencies: the filed follow-on BQ `bq-allai-escalation-flusher-wiring` (G1 closure) — ideally reaches Gate 3 APPROVED before Chunk A Gate 3 starts.
- Output: `app/services/schedule_registry/` package + `app/agents/sysadmin/runbook_stewardship.py` + allAI brain updates + new API routes under `/api/v1/ops/*` + Alembic migration for `user.ops_role` field.
- Gate 2 sub-chunks likely: A1 (registry data model + CRUD), A2 (executor + substrate), A3 (state-predicate engine + dispatch envelopes), A4 (allAI subscription + attention queue + missed-escalation audit).

**Chunk B — ops.ai.market greenfield frontend.**
- Scope: §10 + §11.3 of this spec.
- Dependencies: Chunk A Gate 3 API routes must be stable before Chunk B Gate 3 integration tests.
- Output: `next.config.ts` host routing updates + `middleware.ts` updates + `app/ops/*` page tree + `types/ops.ts` + `api/ops.ts` + component library.
- Gate 2 sub-chunks likely: B1 (host routing + auth gate), B2 (agents + schedules pages), B3 (runs + attention + recommendations pages).

**Chunk C — Runbook-of-runbooks consolidated meta-runbook.**
- Scope: §13 of this spec.
- Dependencies: none (independent; can start immediately after Gate 2 Chunk C spec approval).
- Output: `operating-guide.md` authored §A–§K-conformant + harness self-validation passing + supersession notes on source documents.
- Single-chunk, no sub-chunks.

---

## 17. Open Questions for R2

- **Q1 (R2).** Should compound state-predicate logic (AND/OR of predicates) be in v1 or deferred? Current spec defers; if any identified v1 cron actually needs compound logic (not yet identified), R2 should revisit.
- **Q2 (R2).** Schedule-entity-level concurrent-run policy — should the registry enforce "only one run of schedule X at a time" or delegate to APScheduler defaults? Spec silent.
- **Q3 (R2).** Per-schedule budget caps vs per-dispatch budget caps. For high-frequency schedules with LLM dispatches, how does monthly budget aggregate? Spec silent.
- **Q4 (R2).** Attention queue pagination + filtering semantics at the API level. §8 describes entity shape but not read-API.
- **Q5 (R2).** ops.ai.market auth gate: single-tenant (only Max) vs multi-admin (future ops team). Current spec assumes Max-as-admin; field allows for `ops_role=read`; is that sufficient?
- **Q6 (R2).** Is `AllAIStewardAgent` (dedicated) preferable to role-extension on `AllAIBrainAgent`? Council invited to challenge.
- **Q7 (R2).** `gh_actions_webhook` dispatch mode's authority question: when the registry and workflow file disagree on cron, what happens? Current spec warns on edit but doesn't enforce. Gate 3 may add a reconciliation check.
- **Q8 (R2).** Should the runbook-of-runbooks be a G4 falsifiability test candidate (like D5 AIM Node)? Would require frozen-standard isolation discipline. Current spec does not treat it as G4.
- **Q9 (R2).** Telegram callback format inconsistency (allAI G3 gap) — does THIS BQ's Telegram interactions use the legacy format, the canonical underscore format, or await G3's broader fix? Spec silent.
- **Q10 (R2).** Migration ordering: does the Celery Beat audit (§5.5) produce a finding before or during Chunk A? Timing matters for migration-table completeness.
- **Q11 (R2).** Runbook-stewardship sweep frequency: weekly is proposed; weekly may be too infrequent during active runbook rollout. R2 or Chunk A Gate 2 may tune.

---

## 18. Review Targets

**MP R1 (primary, read-only).** Structural rigor:
- Schedule entity field list complete? Any field that will obviously be missed at Gate 2?
- Pure-replace executor semantics coherent? Internal-substrate/external-API split clean?
- State-predicate language sufficient for v1 cron types not listed in §14?
- Missed-escalation audit non-gameable? Self-escalation path truly bypasses the classifier?
- Gate 2 chunking boundaries clean? No hidden cross-chunk coupling?
- Does §7.3 correctly identify G1 as prerequisite (vs trying to close it in-scope)?

**AG cross-vote (consumer-first).** After MP approves:
- Do the three consumer classes (§3) actually get served by v1 deliverables?
- Is allAI-as-stewardship-hub coherent with the system Max operates, or should stewardship split out?
- Does the ops.ai.market surface give Max the controls he actually needs?
- Frequency-recommendation approval flow: too noisy, too sparse, or right-sized?

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
    "description": "Runs runbook-lint against every .md in the runbooks repo root, evaluates §J staleness for each, aggregates to a weekly report entity, classifies via allAI.",
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
    "owner": "max",
    "created_session": "S490"
  }
}
```

## Appendix B — Existing Scheduled Infrastructure (from discovery)

Source: `project:bq-autonomous-operations-discovery-findings` v3.

**APScheduler + in-allAI loops in ai-market-backend (pulled from MP backend audit, task 96a48267):**

| Location | Cadence | Migration disposition |
|---|---|---|
| `app/core/scheduler.py:830-849` SysAdmin health | 5min | Migrate → registry |
| `app/core/scheduler.py:830-849` backup verify | Daily 03:00 UTC | Migrate → registry (overlaps with GH Actions `backup-verify.yml`; audit for duplication) |
| `IncidentSweeper` loop | 300s | Migrate → registry |
| `BaseAgent` heartbeat | 90s TTL | KEEP — per-instance lifecycle |
| `CRMStewardAgent` daily maintenance | Daily | Migrate → registry |
| `SysAdminAgent` proactive monitors | Various | Per-monitor migration → registry |
| Telegram remediation per-proposal timeouts | Short-lived | KEEP — ephemeral |
| Celery Beat (`app/tasks/scheduled.py`) | Various | Audit during Chunk A; migrate-or-retire |

**GH Actions crons (pulled from AG Stream A, task 9e602fe3):**

| Workflow | Cron | Disposition |
|---|---|---|
| `ai-market-backend/smoke-test.yml` | `0 */6 * * *` | COEXIST (not migrated) |
| `ai-market-backend/quarantine-weekly.yml` | `0 8 * * 1` | Migrate → `gh_actions_webhook` mode |
| `ai-market-backend/backup-verify.yml` | `0 6 * * *` | Migrate → `gh_actions_webhook` mode |
| `ai-market-backend/backup.yml` | `0 3 * * *` | Migrate → `gh_actions_webhook` mode |
| `ai-market-backend/health-check.yml` | `0 7 * * *` | Migrate → `gh_actions_webhook` mode |
| `runbooks/runbook-harness.yml` | `0 7 * * *` | Migrate → `gh_actions_webhook` mode |

## Appendix C — allAI Backend Gap Remediation Plan

Source: `project:bq-autonomous-operations-discovery-findings` v3 mp_backend_allai_audit gaps_identified (G1–G10).

| Gap | Disposition |
|---|---|
| G1 P2+ flusher unwired | PREREQUISITE — file follow-on BQ `bq-allai-escalation-flusher-wiring` during Chunk A Gate 2 |
| G2 Remediation callbacks unwired | Non-blocking; separate BQ `bq-allai-telegram-remediation-wiring` at Max's discretion |
| G3 Telegram callback format inconsistency | Non-blocking; R2 Q9 to decide whether v1 uses legacy or canonical |
| G4 reply_markup dropped | Non-blocking; bundled with G3 fix if Max files that BQ |
| G5 Inbox model not unified | Non-blocking architectural cleanup; future BQ |
| G6 No cross-signal classifier | Non-blocking; rules-first deterministic classifier (routing_policy.py) is sufficient for v1 |
| G7 Remediation proposals Redis-only | Non-blocking; separate BQ at Max's discretion |
| G8 Delegate route unimplemented | Non-blocking; Phase 2 of allAI evolution |
| G9 Agent REST surface dynamic | Non-blocking; documentation issue primarily |
| **G10 Core ops path does not write to Living State** | **DELIVERABLE of this BQ — the schedule registry + run events close this gap by definition** |
