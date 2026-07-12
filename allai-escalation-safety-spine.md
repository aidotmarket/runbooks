---
system_name: allai-escalation-safety-spine
purpose_sentence: "The allAI escalation safety spine preserves human-required pages through a structured always-page allowlist, an independent fail-open watchdog, dead-lettered delivery failures, and the single @allai_agent_bot Telegram sink."
owner_agent: vulcan
escalation_contact: max@ai.market
lifecycle_ref: §J
authoritative_scope: "BQ-MONITORING-SYSADMIN-AUTOMATION-S1165 safety-spine chunk only: the shipped allAI always-page allowlist, structured escalation-class extraction, fail-open watchdog, escalation pipeline settlement/dead-letter behavior, scheduler sweep, and Telegram relay configuration in ai-market-backend main bd1f0dd8. Explicitly out of scope: later C2 dedupe/coalesce, C3 sustained-window gate, C4 CI-to-ticket-to-MP auto-fix, C5 remediation library expansion, and C6 FOR MAX surfacing except as evolution constraints."
linter_version: 1.0.0
---

# allAI Escalation Safety Spine

## §A. Header

YAML frontmatter above is authoritative for the §A header fields. This runbook documents the shipped safety spine for BQ-MONITORING-SYSADMIN-AUTOMATION-S1165 as deployed from ai-market-backend main `bd1f0dd875b44fc89b8128a96532b2905829c8d0` via Railway deployment `2f9e7faf`.

Core invariant: silence is the only unacceptable outcome; over-paging is fine. `escalation_watchdog.ack(request)` means "the watchdog need not fail open for this request" - it does not mean "delivered." Delivery is proven by a successful Telegram send, a fallback send, or a confirmed dead-letter record that keeps the incident visible.

Production evidence as of 2026-07-12: deployed SHA `bd1f0dd8`, `/health` returned 200, the watchdog sweep job was confirmed in deployment logs on its 15s interval, both safety flags default ON when unset, and no false pages were observed. Known limitation: the Gate-4 assertion "an allowlisted class actually pages end-to-end to Telegram" has not been proven with a live production page because that would place a test alarm on the operator's phone; unit tests cover the page path.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Always-page allowlist with 13 hard classes | SHIPPED | `app/allai/escalation_policy.py:9` | tests/test_escalation_pipeline.py (49 tests passing) | 2026-07-12 |
| Structured class extraction from explicit class or context only | SHIPPED | `app/allai/escalation_policy.py:34` | tests/test_escalation_pipeline.py (49 tests passing) | 2026-07-12 |
| Reversible allowlist flag defaults ON when unset | SHIPPED | `app/allai/escalation_policy.py:26` | tests/test_escalation_pipeline.py (49 tests passing) | 2026-07-12 |
| Allowlisted classes are evaluated before dedupe and sustained-window suppression | SHIPPED | `app/allai/escalation_pipeline.py:340` | tests/test_escalation_pipeline.py (49 tests passing) | 2026-07-12 |
| Watchdog enable flag and 30-60s clamped timeout default ON at 45s | SHIPPED | `app/allai/escalation_watchdog.py:25` | tests/test_escalation_pipeline.py (49 tests passing) | 2026-07-12 |
| Watchdog pending entries persist to Redis with in-memory fallback when Redis is unavailable | SHIPPED | `app/allai/escalation_watchdog.py:59` | tests/test_escalation_pipeline.py (49 tests passing) | 2026-07-12 |
| Watchdog ack deletes pending state without claiming delivery | SHIPPED | `app/allai/escalation_watchdog.py:253` | tests/test_escalation_pipeline.py (49 tests passing) | 2026-07-12 |
| Hard-down classes fail open directly when allAI heartbeat is stale or quarantine is set | SHIPPED | `app/allai/escalation_watchdog.py:287` | tests/test_escalation_pipeline.py (49 tests passing) | 2026-07-12 |
| Background watchdog sweep registered every 15s | SHIPPED | `app/core/scheduler.py:1005` | tests/test_escalation_pipeline.py (49 tests passing) | 2026-07-12 |
| Pipeline submit settles only on normal return or confirmed dead-letter record | SHIPPED | `app/allai/escalation_pipeline.py:287` | tests/test_escalation_pipeline.py (49 tests passing) | 2026-07-12 |
| Pipeline immediate send, P2+ batch queue, dedupe, and PII redaction | SHIPPED | `app/allai/escalation_pipeline.py:257` | tests/test_escalation_pipeline.py (49 tests passing) | 2026-07-12 |
| Telegram DISABLED result records dead-letter instead of silently dropping | SHIPPED | `app/allai/escalation_pipeline.py:478` | tests/test_escalation_pipeline.py (49 tests passing) | 2026-07-12 |
| Dead-letter list and escalation-path-failed alerting | SHIPPED | `app/allai/escalation_pipeline.py:596` | tests/test_escalation_pipeline.py (49 tests passing) | 2026-07-12 |
| Telegram relay configured as the @allai_agent_bot page sink | SHIPPED | `app/services/telegram_relay.py:41` | tests/test_escalation_pipeline.py (49 tests passing) | 2026-07-12 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Escalation policy | ai-market-backend app/allai/escalation_policy.py:is_always_page_class | Env flag `ALLAI_ALWAYS_PAGE_ALLOWLIST_ENABLED`; structured request context fields `failure_class` and `incident_class`; explicit request field `escalation_class` | Escalation pipeline and watchdog | Defines `ALWAYS_PAGE_ALLOWLIST` at lines 9-23. `extract_escalation_class()` reads only structured fields at lines 34-46, never free text. Default is ON when Railway env does not set the flag. |
| Escalation watchdog | ai-market-backend app/allai/escalation_watchdog.py:EscalationWatchdog.check_timeouts | Redis set `allai:escalation:watchdog:pending`; Redis records `allai:escalation:watchdog:pending:<key>`; in-memory `_pending`; allAI keys `allai:brain:heartbeat` and `allai:brain:quarantined` | Escalation pipeline, Redis, scheduler | Independent fail-open path. Pending records include epoch `started_at` and timeout. Redis outage logs `escalation_watchdog: Redis unavailable for pending persistence; using in-memory fallback`. Ack clears watchdog ownership, not Telegram delivery. |
| Escalation pipeline | ai-market-backend app/allai/escalation_pipeline.py:EscalationPipeline.submit | Redis keys `allai:escalation:dedup:<hash>`, `allai:escalation:batch`, `allai:escalation:processing`, `allai:escalation:flush_lock`, `allai:escalation:dead_letter`, `allai:escalation:allowlist_update:<incident>` | allAI callers, watchdog, Telegram relay, Redis | Allowlist path runs before Redis dedupe and the C3 sustained-window hook. P0/P1 sends immediately. P2+ batches. `TelegramSendResult.DISABLED` always dead-letters. If dead-letter recording itself raises, submit logs CRITICAL and leaves the watchdog pending. |
| Watchdog scheduler | ai-market-backend app/core/scheduler.py:sweep_allai_escalation_watchdog_job | APScheduler job `allai_escalation_watchdog_sweep` | Escalation watchdog and pipeline | Runs every 15 seconds when `watchdog_enabled()` is true. Logs `Running scheduled job: allai_escalation_watchdog_sweep` and warns with `allAI escalation watchdog sweep delivered %d fail-open page(s)` when it sends. |
| Telegram relay | ai-market-backend app/services/telegram_relay.py:TelegramRelay.is_configured | Railway env `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID`, optional `TELEGRAM_BOT_USERNAME`; Infisical source of truth for secrets is the `ai-market` project | Telegram Bot API, allAI event bus, operator notification policy | The sole operator page sink is `@allai_agent_bot`; `TELEGRAM_BOT_USERNAME` defaults to `allai_agent_bot`. Cross-reference [operator-telegram-notifications.md](operator-telegram-notifications.md). |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| vulcan | Diagnose no-page, dead-letter, watchdog, and dedupe symptoms | Read-only source/log/Redis inspection plus this runbook §F | repo read, Railway read, Redis read as authorized | COMPLETE |
| vulcan | Change safety-spine docs and evolution classification | runbooks repo edit, `runbook-lint` | docs branch only | COMPLETE |
| sysadmin | Emit operational escalations through allAI pipeline | `EscalationPipeline.submit(EscalationRequest)` | backend runtime service identity | COMPLETE |
| allAI Brain | Triage operational events without becoming a silence point | allAI event handling and escalation pipeline | backend runtime service identity | COMPLETE |
| Max | Approve disabling safety flags or live Telegram test pages | human decision via escalation_contact | owner/operator | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: "A normal operational escalation should enter the allAI escalation pipeline."
  pre_conditions:
    - "Caller can construct an EscalationRequest with source_agent, priority, domain, summary, context, and recommended_action."
    - "Telegram relay is configured or delivery failure must be dead-lettered."
    - "Safety flags are not explicitly disabled."
  tool_or_endpoint: "EscalationPipeline.submit(EscalationRequest)"
  argument_sourcing:
    source_agent: "calling agent key, for example sysadmin"
    priority: "incident priority P0 as 0, P1 as 1, P2 as 2, P3 as 3"
    domain: "incident domain from caller"
    context: "structured incident context; put failure_class or incident_class here when known"
    incident_id: "stable incident id when available"
    correlation_id: "request trace id when incident_id is absent"
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: "incident_id if present, otherwise hash(correlation_id + source_agent + summary prefix) as implemented by _dedup_key"
  expected_success:
    shape: "True for accepted new work, False when non-allowlisted work is deduplicated or suppressed."
    verification: "For P0/P1, grep logs for `escalation_pipeline: sent P` or fallback/dead-letter logs; for P2+ inspect Redis `allai:escalation:batch`."
  expected_failures:
    - signature: "escalation_pipeline: Telegram disabled/unconfigured"
      cause: "Telegram relay is not configured; the request must be recorded to `allai:escalation:dead_letter`."
    - signature: "escalation_pipeline: submit failed and dead-letter recording failed; leaving watchdog pending unacked"
      cause: "Primary submit path and dead-letter recording both failed; watchdog must fail open."
  next_step_success: "Treat the request as visible unless it returned False from non-allowlisted dedupe/suppression."
  next_step_failure: "Go to §F-01 for no page, §F-03 for dead-letter, or §F-05 for watchdog retry."
- id: E-02
  trigger: "An allowlisted class arrives and must produce the first human-required page even if duplicate keys already exist."
  pre_conditions:
    - "Escalation class is one of the 13 values in ALWAYS_PAGE_ALLOWLIST."
    - "Class is supplied through request.escalation_class, context.failure_class, or context.incident_class."
    - "ALLAI_ALWAYS_PAGE_ALLOWLIST_ENABLED is unset or true."
  tool_or_endpoint: "EscalationPipeline.submit(EscalationRequest(context={'failure_class': '<allowlisted_class>'}))"
  argument_sourcing:
    failure_class: "structured incident classifier output or explicit caller field; never infer from summary text"
    incident_id: "stable incident id so repeated updates coalesce as same-incident metadata"
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: "same-incident update key `allai:escalation:allowlist_update:<incident>`; the first page is still sent"
  expected_success:
    shape: "True and immediate page path before dedupe or sustained-window checks."
    verification: "Log contains `escalation_pipeline: allowlist immediate page`; no Redis `allai:escalation:dedup:<hash>` decision is required first."
  expected_failures:
    - signature: "No allowlist log and no page"
      cause: "Class was missing, not structured, misspelled, or the allowlist flag was explicitly disabled."
  next_step_success: "Leave same-incident update metadata in Redis and continue normal incident handling."
  next_step_failure: "Go to §F-01 and §G-04 before considering any flag change."
- id: E-03
  trigger: "A P2 or lower-priority escalation is accepted for digest batching."
  pre_conditions:
    - "Request priority is 2 or greater."
    - "Request is not allowlisted and not hard-down fail-open."
    - "Redis is available."
  tool_or_endpoint: "EscalationPipeline.submit(EscalationRequest(priority=2))"
  argument_sourcing:
    priority: "caller incident priority"
    batch_record: "serialized EscalationRequest pushed by `_batch`"
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: "Redis `allai:escalation:dedup:<hash>` with 900 second TTL"
  expected_success:
    shape: "True and serialized request appended to `allai:escalation:batch`."
    verification: "Grep logs for `escalation_pipeline: batched P`; later flush logs `escalation_pipeline: flushed`."
  expected_failures:
    - signature: "escalation_pipeline: deduplicated escalation"
      cause: "Same non-allowlisted incident already accepted inside the dedupe window."
    - signature: "escalation_pipeline: Redis unavailable - sending without dedup"
      cause: "Redis unavailable; pipeline fails open to immediate delivery."
  next_step_success: "Wait for the batch flush or manually inspect `allai:escalation:batch`."
  next_step_failure: "If the operator expected a human page, confirm this was not an allowlisted class."
- id: E-04
  trigger: "allAI is unresponsive, heartbeat is stale, or allAI is quarantined while a hard-down class arrives."
  pre_conditions:
    - "Class is one of escalation_pipeline_down, mcp_server_unhealthy, dead_man_switch, escalation_path_failed."
    - "Redis state has stale `allai:brain:heartbeat` or truthy `allai:brain:quarantined`."
    - "ALLAI_ESCALATION_WATCHDOG_ENABLED is unset or true."
  tool_or_endpoint: "EscalationWatchdog.fail_open_hard_down_if_needed(request, escalation_pipeline, redis)"
  argument_sourcing:
    heartbeat: "Redis key `allai:brain:heartbeat`, epoch timestamp"
    quarantined: "Redis key `allai:brain:quarantined`, truthy string means hard down"
    escalation_class: "structured class from request.escalation_class or context"
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: "request incident_id or correlation_id as watchdog pending key"
  expected_success:
    shape: "True and immediate fallback-capable page with recommended_action `triage_timeout_fail_open`."
    verification: "Grep logs for `escalation_watchdog: fail-open page delivered` with incident id, class, timeout, and `fail_open_page=True`."
  expected_failures:
    - signature: "escalation_watchdog: fail-open page failed; retained for retry"
      cause: "Delivery failed; pending state remains for retry and eventual dead-letter."
  next_step_success: "Repair allAI heartbeat/quarantine separately; do not disable the watchdog because duplicates are possible."
  next_step_failure: "Go to §F-05 and §G-03."
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Operator says "no alert" or "missed page" for a human-required incident | Telegram delivered nowhere, class not structured, allowlist flag off, request dead-lettered, or watchdog still pending | Check logs for `escalation_pipeline: allowlist immediate page`, `escalation_pipeline: sent P`, `escalation_pipeline: fallback page delivered`, `escalation_pipeline: Telegram disabled/unconfigured`, and `escalation_watchdog: fail-open page delivered`; inspect Redis `allai:escalation:dead_letter` and `allai:escalation:watchdog:pending*` | G-01 | CONFIRMED |
| F-02 | No page arrived, but the request was intentionally suppressed | Non-allowlisted duplicate inside the 15 minute dedupe window or future C3 sustained-window suppression | Grep for `escalation_pipeline: deduplicated escalation` and `escalation_pipeline: sustained-window suppressed escalation`; inspect Redis `allai:escalation:dedup:<hash>`; confirm the class was not allowlisted | G-05 | CONFIRMED |
| F-03 | Delivery failed and was dead-lettered | Telegram relay unconfigured, raw fallback failed, Redis write failed then CRITICAL log fallback emitted | Inspect Redis list `allai:escalation:dead_letter`; grep for `escalation_pipeline: DEAD_LETTER`, `escalation_pipeline: fallback page failed`, and `escalation_pipeline: dead-letter Redis write failed` | G-02 | CONFIRMED |
| F-04 | Genuinely nothing escalated | No caller submitted an EscalationRequest, allAI observed/delegated/remediated without human-needed outcome, or P2+ is waiting in batch | Search logs by incident id and correlation id; inspect `allai:escalation:batch`; absence of submit logs plus no batch/dead-letter/pending keys means no escalation entered this pipeline |  | HYPOTHESIZED |
| F-05 | Watchdog is paging repeatedly or alert storm mentions watchdog | allAI heartbeat stale, quarantine key stuck, primary delivery failing so watchdog retries, or ack never reached settled state | Inspect Redis `allai:brain:heartbeat`, `allai:brain:quarantined`, `allai:escalation:watchdog:pending`, and pending records; grep `Running scheduled job: allai_escalation_watchdog_sweep`, `allAI escalation watchdog sweep delivered`, and `escalation_watchdog: fail-open page failed; retained for retry` | G-03 | CONFIRMED |
| F-06 | Telegram disabled messages appear but no operator page appears | `TelegramRelay.is_configured` is false because token or admin chat id is missing; pipeline correctly dead-lettered instead of dropping | Check backend env for `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ADMIN_CHAT_ID`; grep `TelegramRelay: Cannot send - missing token or chat_id` and `Telegram disabled/unconfigured`; inspect `allai:escalation:dead_letter` | G-01 | CONFIRMED |
| F-07 | Safety flag is explicitly off | Operator or deploy changed `ALLAI_ALWAYS_PAGE_ALLOWLIST_ENABLED` or `ALLAI_ESCALATION_WATCHDOG_ENABLED` to false | Inspect Railway env; grep deploy logs for missing scheduler registration when watchdog off; remember unset means ON for both flags | G-04 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Telegram relay
  root_cause: "The page sink is unconfigured or the incident never reached a configured Telegram send path."
  repair_entry_point: "app/services/telegram_relay.py:TelegramRelay.is_configured"
  change_pattern: "Confirm `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ADMIN_CHAT_ID` exist for the ai-market-backend Railway service and that the source secret is in the Infisical `ai-market` project. Do not create or revive any second bot. If the incident is already in `allai:escalation:dead_letter`, manually page or ticket it before clearing the record."
  rollback_procedure: "Restore the prior Telegram env values from Infisical and redeploy ai-market-backend. All Railway CLI commands must be prefixed with `unset RAILWAY_TOKEN &&`."
  integrity_check: "After redeploy, `curl -fsS https://api.ai.market/health` returns 200; a non-live mocked or unit path shows `TelegramRelay.is_configured` true; no new `telegram_unconfigured` dead-letter appears for the same probe."
- id: G-02
  symptom_ref: F-03
  component_ref: Escalation pipeline
  root_cause: "Delivery failed after primary and fallback paths, or Telegram was disabled, and the request was made visible through the dead-letter list."
  repair_entry_point: "app/allai/escalation_pipeline.py:_record_dead_letter"
  change_pattern: "Inspect `allai:escalation:dead_letter` from an approved Redis client. For each record, capture incident_id or correlation_id, path, primary_error, fallback_error, and created_at. Manually page Max or create a support/dev ticket for any human-required record before draining. Drain only records whose replacement notification has been confirmed."
  rollback_procedure: "If a record was drained prematurely, reconstruct a new EscalationRequest from the captured dead-letter JSON and submit it again, or manually page Max with the captured fields."
  integrity_check: "Redis list length decreases only by the confirmed count; logs stop producing `escalation_pipeline: DEAD_LETTER` for the same incident; the incident has an operator-visible page, ticket, or BQ note."
- id: G-03
  symptom_ref: F-05
  component_ref: Escalation watchdog
  root_cause: "The watchdog is correctly failing open because allAI looks hard down, an ack never settled, or fail-open delivery is failing and retrying."
  repair_entry_point: "app/allai/escalation_watchdog.py:EscalationWatchdog.check_timeouts"
  change_pattern: "First decide whether the pages are true positives. Check `allai:brain:heartbeat` age and clear `allai:brain:quarantined` only after the allAI process is healthy. If fail-open delivery is failing, repair Telegram and dead-letter handling through G-01/G-02. Do not ack or delete pending watchdog keys merely to stop noise unless Max explicitly accepts the silence risk."
  rollback_procedure: "If a bad deploy caused the storm, roll back or redeploy ai-market-backend, then verify `/health` 200 and that scheduler logs no longer deliver repeated fail-open pages for the same key."
  integrity_check: "Pending keys under `allai:escalation:watchdog:pending*` drain naturally after successful page or settlement; new heartbeat is fresh; `allAI escalation watchdog sweep delivered` stops repeating for the same incident."
- id: G-04
  symptom_ref: F-07
  component_ref: Escalation policy
  root_cause: "A safety flag was disabled or an operator wants to disable one during an emergency."
  repair_entry_point: "app/allai/escalation_policy.py:env_flag_enabled"
  change_pattern: "Max-gated only: set `ALLAI_ALWAYS_PAGE_ALLOWLIST_ENABLED=false` or `ALLAI_ESCALATION_WATCHDOG_ENABLED=false` in Railway env, then redeploy. Example shape: `unset RAILWAY_TOKEN && railway variables --service ai-market-backend --set \"ALLAI_ESCALATION_WATCHDOG_ENABLED=false\"`; then `unset RAILWAY_TOKEN && railway redeploy --service ai-market-backend --yes`. Turning either flag off reintroduces possible silence and must be time-boxed with an owner."
  rollback_procedure: "Remove the env override or set it back to true and redeploy. Because unset means ON, deleting the override is the preferred rollback."
  integrity_check: "Health endpoint returns 200 after deploy; when watchdog is enabled, scheduler registers `allai_escalation_watchdog_sweep`; when allowlist is enabled, an allowlisted unit or non-live probe reaches the allowlist path before dedupe."
- id: G-05
  symptom_ref: F-02
  component_ref: Escalation pipeline
  root_cause: "A non-allowlisted duplicate was suppressed, or future suppression logic was applied to a class that should have bypassed it."
  repair_entry_point: "app/allai/escalation_pipeline.py:_submit_impl"
  change_pattern: "Confirm the event class with `extract_escalation_class()`. If it is allowlisted, this is a regression: allowlist evaluation must remain before dedupe and sustained-window logic. If it is not allowlisted, inspect the dedupe key and decide whether to wait for TTL, widen context, or escalate manually."
  rollback_procedure: "For an allowlist regression, revert the suppression change or disable the new suppression mechanism, not the allowlist framework. For non-allowlisted incidents, let the 900s dedupe TTL expire or create a new incident id only if it is genuinely a distinct incident."
  integrity_check: "Allowlisted requests log `escalation_pipeline: allowlist immediate page`; non-allowlisted duplicates log exactly one dedupe suppression inside the TTL."
```

## §H. Evolve

### §H.1 Invariants

- Silence is the only unacceptable outcome; over-paging is fine.
- `escalation_watchdog.ack(request)` means "the watchdog need not fail open for this request"; it never means "Telegram delivered."
- The first human-required page for any class in `ALWAYS_PAGE_ALLOWLIST` must never be suppressible by dedupe, coalesce, sustained-window gating, model triage, batching, rate limiting, or disabled Telegram state. If delivery cannot happen, the request must dead-letter or remain pending for fail-open.
- `extract_escalation_class()` may read `request.escalation_class`, `context.failure_class`, or `context.incident_class`; it must never infer class from free text.
- Both `ALLAI_ALWAYS_PAGE_ALLOWLIST_ENABLED` and `ALLAI_ESCALATION_WATCHDOG_ENABLED` default true when unset. Disabling either is a Max-gated incident action because it reintroduces silence.
- Operator Telegram has one sink: `@allai_agent_bot` through the backend Telegram relay. No new bot, chat path, or direct daemon Telegram path is allowed.
- Payment, auth, and security alert-routing changes require unanimous Council approval, 4/4. Stripe webhook signatures remain mandatory; this runbook is alert routing only and does not alter Stripe Connect marketplace payment behavior.

Remaining S1165 chunks must preserve the invariants above: C2 dedupe/coalesce, C3 sustained-window gate, C4 CI failure to probed dev ticket to MP auto-fix, and C6 FOR MAX ops-console surfacing. Hard rule for C2/C3: no suppression mechanism may ever suppress the first page for an allowlisted class.

### §H.2 BREAKING predicates

- Changing, removing, or renaming any allowlisted class in `ALWAYS_PAGE_ALLOWLIST`.
- Moving allowlist evaluation after dedupe, batch, sustained-window, allAI triage, or any future suppression mechanism.
- Treating `ack()` as proof of Telegram delivery or deleting pending watchdog state before submit is settled or dead-lettered.
- Changing either safety flag default from true to false.
- Adding a second operator Telegram bot or bypassing `@allai_agent_bot`.
- Changing payment, auth, security, payout, or webhook-signature alert routing without unanimous 4/4 Council approval.

### §H.3 REVIEW predicates

- Adding a new allowlisted class.
- Changing watchdog timeout clamp, Redis pending key shape, retry behavior, or scheduler interval.
- Implementing C2 dedupe/coalesce or C3 sustained-window thresholds.
- Implementing C4 CI ticketing or C6 FOR MAX surfacing.
- Changing dead-letter record shape, dead-letter alert behavior, or manual drain process.

### §H.4 SAFE predicates

- Documentation-only clarification that preserves this runbook's invariants.
- Adding tests for existing allowlist, watchdog, dead-letter, or Telegram-disabled behavior.
- Tightening log messages while preserving the existing searchable substrings listed in §F.
- Manually inspecting Redis keys or logs without mutating production state.

### §H.5 Boundary definitions

#### module

For ai-market-backend, `app/allai/`, `app/core/`, and `app/services/` are product modules. This runbook's safety-spine code lives in `app/allai/escalation_policy.py`, `app/allai/escalation_watchdog.py`, `app/allai/escalation_pipeline.py`, `app/core/scheduler.py`, and `app/services/telegram_relay.py`.

#### public contract

Public operational contracts are the `EscalationRequest` fields consumed by callers, the structured class fields `escalation_class`, `context.failure_class`, and `context.incident_class`, the Redis keys named in §C/§F, the two safety flags, and the operator-visible Telegram behavior. Internal helper names may change only if these contracts and tests remain equivalent.

#### runtime dependency

Runtime dependencies are Redis, Railway env, the ai-market-backend scheduler, the allAI runtime heartbeat/quarantine writers, and Telegram Bot API via the backend relay. Secret source of truth for Telegram and related runtime secrets is Infisical project `ai-market`.

#### config default

`ALLAI_ALWAYS_PAGE_ALLOWLIST_ENABLED` default true. `ALLAI_ESCALATION_WATCHDOG_ENABLED` default true. `ALLAI_ESCALATION_WATCHDOG_TIMEOUT_SECONDS` default 45 and clamps to 30-60. `TELEGRAM_BOT_USERNAME` defaults to `allai_agent_bot`.

### §H.6 Adjudication

Owner agent vulcan adjudicates documentation and SAFE changes. REVIEW changes require at least one non-builder review. BREAKING changes require a spec, Council approval, and for payment/auth/security classes unanimous 4/4 approval. Max is the only authority allowed to disable either safety flag in production, because disabling them accepts a possible silence path.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs:
      - E-01
    scenario: "Submit a normal P0 operational escalation and verify it becomes visible through send, fallback, or dead-letter."
    expected_answers:
      - kind: tool_call
        tool: "EscalationPipeline.submit"
        argument_keys:
          - request
          - source_agent
          - priority
          - context
    weight: 0.090909
  - id: I-02
    type: operate
    refs:
      - E-02
    scenario: "An allowlisted payment_failure arrives with a duplicate Redis key already present."
    expected_answers:
      - kind: tool_call
        tool: "EscalationPipeline.submit"
        argument_keys:
          - request
          - failure_class
          - incident_id
    weight: 0.090909
  - id: I-03
    type: operate
    refs:
      - E-03
    scenario: "A non-allowlisted P2 escalation is accepted into the batch path."
    expected_answers:
      - kind: tool_call
        tool: "_batch"
        argument_keys:
          - redis
          - request
    weight: 0.090909
  - id: I-04
    type: isolate
    refs:
      - F-01
    scenario: "Operator reports a missed page for a human-required incident."
    expected_answers:
      - kind: tool_call
        tool: "redis_inspect"
        argument_keys:
          - allai:escalation:dead_letter
          - allai:escalation:watchdog:pending
    weight: 0.090909
  - id: I-05
    type: isolate
    refs:
      - F-02
    scenario: "No page arrived because a non-allowlisted request may have been deduplicated."
    expected_answers:
      - kind: tool_call
        tool: "log_grep"
        argument_keys:
          - "escalation_pipeline: deduplicated escalation"
          - "allai:escalation:dedup"
    weight: 0.090909
  - id: I-06
    type: isolate
    refs:
      - F-03
    scenario: "Telegram delivery failed and the incident may be dead-lettered."
    expected_answers:
      - kind: tool_call
        tool: "redis_lrange"
        argument_keys:
          - allai:escalation:dead_letter
    weight: 0.090909
  - id: I-07
    type: repair
    refs:
      - G-02
    scenario: "Drain confirmed dead-letter records after manually making them visible."
    expected_answers:
      - kind: human_action
        verb: "inspect"
        object: "dead-letter records"
        target: "allai:escalation:dead_letter"
    weight: 0.090909
  - id: I-08
    type: repair
    refs:
      - G-03
    scenario: "Watchdog is paging repeatedly for the same hard-down class."
    expected_answers:
      - kind: tool_call
        tool: "redis_inspect"
        argument_keys:
          - allai:brain:heartbeat
          - allai:brain:quarantined
          - allai:escalation:watchdog:pending
    weight: 0.090909
  - id: I-09
    type: evolve
    refs:
      - §H.2 BREAKING predicates
    scenario: "A proposed C2 dedupe change would run before the allowlist check."
    expected_answers:
      - kind: classification
        label: BREAKING
        tool: "change_class_predicate"
        argument_keys:
          - allowlist_order
    weight: 0.090909
  - id: I-10
    type: evolve
    refs:
      - §H.3 REVIEW predicates
    scenario: "A proposed C3 sustained-window threshold preserves allowlist bypass but changes the threshold."
    expected_answers:
      - kind: classification
        label: REVIEW
        tool: "change_class_predicate"
        argument_keys:
          - sustained_window_threshold
    weight: 0.090909
  - id: I-11
    type: ambiguous
    refs:
      - F-01
      - F-02
      - F-03
      - F-04
    scenario: "No operator page arrived and it is unclear whether the request was suppressed, dead-lettered, still batched, or never submitted."
    expected_answers:
      - kind: tool_call
        tool: "log_and_redis_triage"
        argument_keys:
          - incident_id
          - allai:escalation:dead_letter
          - allai:escalation:watchdog:pending
          - allai:escalation:batch
          - allai:escalation:dedup
    weight: 0.090909
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1165
last_refresh_commit: bd1f0dd875b44fc89b8128a96532b2905829c8d0
last_refresh_date: "2026-07-12T00:00:00Z"
owner_agent: vulcan
refresh_triggers:
  - change to ALWAYS_PAGE_ALLOWLIST membership, class extraction, or allowlist flag default
  - change to watchdog timeout, Redis pending keys, ack semantics, hard-down checks, or scheduler interval
  - change to EscalationPipeline submit settlement, dedupe ordering, batching, fallback delivery, or dead-letter behavior
  - change to Telegram relay configuration, operator bot policy, or Infisical/Railway secret source
  - implementation of S1165 C2, C3, C4, or C6
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: "2026-07-12T00:00:00Z"
first_staleness_detected_at: null
```

## §K. Conformance

Source citations in this runbook were verified against the ai-market-backend checkout at `/Users/max/Projects/ai-market/ai-market-backend`, branch `main`, commit `bd1f0dd875b44fc89b8128a96532b2905829c8d0`. The test file contains 49 test functions. I did not create a live production Telegram test page; that remains pending an operator decision because it would alert Max's phone.

```yaml conformance
linter_version: 1.0.0
last_lint_run: "S1165 / 2026-07-12T00:00:00Z"
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
