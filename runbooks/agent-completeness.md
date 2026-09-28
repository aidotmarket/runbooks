---
title: Agent Completeness
owner: vulcan
last_verified: '2026-08-24'
aliases: []
error_signatures:
- incomplete_agent_surface
---

# Agent Completeness

## Overview


**Fetch trigger:** agent creation or Gate 3 agent-compliance review.

**Source:** CORE §§3–4.

## Capabilities

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| REST request and health surfaces | SHIPPED | `AgentRequestFactory` | Gate 3 compliance review | 2026-07-17 |
| Skill, schema, and manifest surfaces | SHIPPED | `BaseAgent` | Internal compliance endpoint | 2026-07-17 |
| Monitoring policy declarations | SHIPPED | `MonitoringPolicy` | Internal compliance endpoint | 2026-07-17 |

## Architecture & interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Request Surface | `POST /api/v1/agents/{key}/request` | Agent runtime | AgentRequestFactory | Required REST interaction path. |
| Skill Surface | `@skill` method | Source and generated manifests | Pydantic I/O schemas | At least one typed skill is required. |
| Discovery Surface | `GET /api/v1/agents/discover` | Public and internal manifests | Orchestrators and external agents | Public output is redacted; internal output is authenticated. |
| Health and Manifest | `GET /api/v1/agents/{key}/health` | Agent runtime | Gate 3 reviewer | Both endpoints must respond. |
| Monitoring Surface | `GET /api/v1/internal/agent-compliance` | Code-first MonitoringPolicy | Metrics, validation, escalation | Git history is the policy audit trail. |
| MCP Request Tool | `tools/agent_request.py` | MCP tool registry | Koskadeux orchestrator | An agent without this tool is operationally invisible. |
| Claim-first Operator Worker | Programmatic dispatcher, Codex SDK, and scoped remote MCP view | Incident and `IncidentAction` lease records | Backend and local user LaunchAgent | `allAI:Remediator` is not a `BaseAgent`, Vulcan, or Mars. |

### Claim-first operator companion — allAI:Remediator

`allAI:Remediator` is a claim-first operator worker, not a `BaseAgent`, Vulcan, or Mars, and does not satisfy or replace the CORE completeness contract. A one-minute programmatic dispatcher checks the existing queue and exits before importing Codex unless it has claimed actionable work. Only that positive claim starts ephemeral `gpt-5.6-sol` through the local Codex SDK and the existing ChatGPT Pro authentication. The previous recurring model task must remain paused.

| Contract | Operational rule |
|---|---|
| Transport and actions | The dispatcher claims through `POST /api/v1/observability/remediator/claim` before Codex exists. Empty and human-only responses exit locally. For a positive claim, the model's only service transport is the personal/dev scoped remote MCP view `https://mcp2.ai.market/remediator/`, whose live `tools/list` must be exactly `{allai_remediator_request}`. The singleton retains closed `services`, `claim`, `finish`, and bounded `search` actions, but the claim-first agent uses only `finish` and optional `search` for its already bounded claim. |
| Authentication | The credential-free dispatcher starts a short login-shell child that loads the operator's existing Railway CLI login, then `railway run` injects the production internal key only into the nested claim subprocess. Both children exit before Codex can start. The dispatcher captures only the typed claim response, never prints a credential, and explicitly removes internal and Railway credential names from the later SDK environment. The model receives no backend, Railway, provider, or other credential. The gateway still injects backend authentication for the model's scoped MCP calls. |
| Personal plugin | Plugin contents are metadata plus one remote `.mcp.json` only: no `.app.json`, local executable or script, bearer environment variable, or secret. The plugin and state-changing tool must never be published, shared, distributed, or attached to a public ai.market App; any public surface requires separate review. |
| Runner isolation | Use only `/Users/max/Projects/ai-market/allai-remediator-runner`. Its project-local `.codex/config.toml` keeps the workspace read-only, command network disabled, approval policy `never`, and all shell, browser, app, multi-agent, memory, image, and non-remediator plugin capabilities disabled. It enables only the personal `allai-remediator` server and `allai_remediator_request`; only that exact tool is approved. The SDK must run with the current signed-in ChatGPT authentication, `gpt-5.6-sol`, read-only sandbox, and auto-review so the singleton approval can work. Root host controls remain inert scaffolding; only `functions.exec` may be used, solely to call the singleton. |
| Provider intake and filtering | GitHub uses the existing signed `workflow_run` webhook. Railway reuses the existing five-minute SysAdmin health contract and forwards only latest `FAILED` or `CRASHED` deployments. Cloudflare v1 remains adapter-only/manual. Before queue creation and again before claim, deterministic exact-match policy gives failure states precedence, ignores reviewed no-attention statuses/messages, and treats every unknown as actionable. Do not use fuzzy matching. Filtered queued rows are audit-marked and closed without a model call. |
| Queue and lease | `ALLAI_REMEDIATOR_INCIDENT_QUEUE_ENABLED=false` by default. Claim only owned P2/P3 work using database time and `FOR UPDATE SKIP LOCKED`; leases are 15 minutes and only the current unexpired token may finish. Provider adapters stay read-only and `/services` must report `execute_allowed=false` for every provider. |
| Outcomes and verification | Outcomes are exactly `fixed`, `retryable`, or `human_required`. GitHub recovery (`github_workflow_recovery`) is verified when ANY of these holds: (a) the original run's current conclusion is `success` after a re-run; (b) a newer run of the same workflow on the same head branch has conclusion `success`; (c) the head branch is deleted or fully contained in the repository default branch AND the latest completed run of the same workflow on the default branch has conclusion `success`. Verification uses run-level conclusions, with no event-type eligibility, admission table, head-repository check, job identity matching, or fail-closed pagination requirement. Railway `fixed` still requires a different newer healthy/successful deployment. Cloudflare adapter/manual incidents cannot self-verify `fixed` in v1 and must finish `retryable` or `human_required` unless a separately reviewed verification source is added. A model run is complete only after the SDK records a completed `allai_remediator_request` call with `action=finish`; final prose is not completion. If the model exits without that call, the dispatcher uses the existing Railway-authenticated child to release the exact claim as `retryable` with reason `agent_completed_without_finish`. Telegram remains backend-owned and is sent only for deduplicated `human_required` within the Needs-Max audience below; existing provider alerting remains authoritative. |
| Needs-you rule (Max directive, S1657) | An item stays on Needs-you only while it is a current failure that a human must act on; anything the system can observe as resolved leaves by itself. |
| GitHub audience (S1657) | Only failures on the repository default branch or branches beginning `release/`, `hotfix/`, or `deploy/` can page Max. GitHub failures on every other branch never appear in `/ops/needs-max` and never trigger the `human_required` Telegram. They are recorded as incidents, emitted to the Event Ledger as `build_branch_ci_failure` with `bq_slug` equal to the branch name minus its leading `build/` (otherwise the branch name unchanged) for the owning build session, and self-resolve or demote. |
| Verification retry cap and aging (S1657) | After 8 consecutive verification failures with the same `safe_reason`, the incident receives a `remediator_demotion` action with reason `verification_stalled`, leaves Needs-Max for the operator Attention list, and is not rechecked by the old autonomous Remediator verifier/closeout lane. Seven-day demotion applies to every escalated incident in that old recovery pass, measured from its latest escalation, regardless of playbook attempts: action `remediator_demotion`, reason `aged_out`, Event Ledger event `incident_aged_out`. Demoted incidents remain excluded from old autonomous recovery checks; the separate default-off Phase 1 lane may record bounded metadata observations while they remain escalated, without reversing demotion or closing them. |
| Needs-Max reporting (S1585, S1657) | `GET /api/v1/ops/needs-max` derives its data from `Incident` and append-only `IncidentAction` records; it never starts Codex or writes state. Since S1585 the seven-day Remediator report is no longer rendered on the queue page; the feed excludes GitHub failures outside the audience above, incidents with any demotion action, and tickets whose first-class assignee names a non-Max owner. `needs_attention` counts Remediator-owned escalated incidents within that audience that carry no demotion action. Each such escalation renders as a flagged needs-Max row on BUILD QUEUE and drives the red badge on the BUILD QUEUE nav item, title count, and red-dot favicon until it is resolved (incl. superseded) or demoted. Demoted incidents surface on the OPS Attention list via `GET /api/v1/ops/operator-attention`; an escalation leaving the feed with a demotion or supersession record is intended behaviour, not drift. Telegram remains the alert channel. |
| Manual closeout (S1605, residual since S1657) | This is the existing human-authorized path, not an effect of Phase 1 metadata. Manual closeout is residual only for non-GitHub incidents and GitHub incidents where the default-branch workflow is genuinely still red. GitHub incidents with backend-observed recovery auto-resolve as `superseded` and need no operator action. When manual closeout applies, verify the original provider failure and current recovery evidence; for GitHub, retain the repository, workflow run, branch, SHA, failure cause, corrective diff, merged PR and merge identity. When runtime behaviour is affected, verify a successful production deployment containing the correction. Record the evidence through the existing incident supersede endpoint from a short-lived Railway production child that injects `INTERNAL_API_KEY`; never retrieve Infisical through a browser, print the key, or move it into the operator browser. Verify the append-only resolution actions by GET and then verify in authorized operator Chrome that the row and badge count changed. A Phase 1 read, `success_observed` label, or projected disposition alone never authorizes supersede or establishes recovery. |

### S1760 Phase 1 incident observation companion — preactivation

This is the independent, incident-only operator companion to accepted Gate 2 `koskadeux-mcp@f7414e770b63b5ead85cc07e4dd5c7d942244752` (`specs/BQ-AUTONOMOUS-OPS-RECOVERY-PHASE1-S1760-GATE2.md`) and its separately reviewed prerequisite artifacts at `df8d1de4590f1f0e2f8b966d8b89632dc1be79b6` (`specs/BQ-AUTONOMOUS-OPS-PHASE1-S1760-ACTOR-ALLOWLIST.json`, `specs/BQ-AUTONOMOUS-OPS-PHASE1-S1760-REASON-CATALOG.json`). The exact actor list is `actors=[]`; its projection therefore reports `owner=null`, `owner_state=assignment_gap`. The catalog contains fixed, full sentences for action reasons and disposition/gap combinations. Backend candidate `1b81730c9cc73db9f806ff4762506f22035c3567` supplies disabled source, not deployed or accepted behavior: `PHASE1_READ_ONLY_ENABLED=False` and `PHASE1_READ_MODEL_ENABLED=False`. The independent controller's 13 new tests passed, but the original benchmark exercised zero D rows and zero L rows; its native plan evidence was correspondingly unproved. Populated plans and fairness coverage are being folded separately; do not infer performance or full 142-test acceptance from this candidate. Author objective fold `11cfb8814a95` corrects benchmark/test coverage and is not a verified design source.

The old autonomous Remediator lane retains its independent three-row budget, S1657 audience, demotion, notifications, provider verification and closeout. The additional lane reserves at most three escalated incidents per tick satisfying `D OR L`: `D` is an existing `remediator_demotion` action; `L` is absence of a string `context.queue_owner` exactly equal to `allAI:Remediator` (missing, null, malformed or foreign marker). D and L may overlap. Open, diagnosing, mitigating, monitoring, exhausted, resolved and closed rows are ineligible. An escalated demoted row stays on Operator Attention and outside the old autonomous verifier; an escalated legacy row gains no automatic Needs You entry. The new action actor is always `allAI:ReadOnlyObserver`, never a Remediator attribution, incident assignee, queue owner or permission to act. No Phase 1 path claims, calls `finish(fixed)`, resolves, supersedes, writes `queue_owner`, executes a provider operation, retries a provider job, pages anyone, or creates a Needs You decision. It adds no assignment writer or recovery authority.

Two new slots prefer never-checked rows in `(created_at,id)` order; one prefers due rechecks in `(last_started_at,created_at,id)` order. Empty pools may lend slots, without exceeding three reservations, three total provider reads or three reads per provider per tick. The DB clock and latest `phase1_read_only_check_started` action alone determine the 900-second recheck cooldown. Recheck eligibility, status, source, context and demotion under `FOR UPDATE OF Incident SKIP LOCKED`; append and commit the started action before provider I/O, releasing the lock. Bound each invoked read to 10 seconds and the whole lane to 30 seconds. After the read, recheck status, context version and exact target; append a `phase1_read_only_check_completed` action linked to the reservation ID. Completion never advances cooldown. A crash or missing completion stays unknown until the started-action cooldown expires. An unsupported source, missing/unconfigured adapter, unsafe or incomplete exact target, or deadline reached before invocation records a bounded unknown completion with `read_performed=false` and zero adapter calls. An actually invoked timeout, refusal or partial read records `read_performed=true` with unknown/refused result, never success. Only the configured source adapter and one validated same-source exact target may be read. Current adapters lack the complete witness required by Gate 2: even historical `verified=true` is `unknown` with `witness=null`, never auto-recovery.

The two new action details are closed and typed: start has only `schema_version`, `reservation_id`, `source`, `target_key`, `context_version`; completion has only `schema_version`, `reservation_id`, `read_performed`, `read_result`, `reason_code`, `evidence_refs`, `witness`. New persistence, projections and logs use validated target tokens, fixed enums and literal reason sentences; they exclude raw provider/context text, secrets, customer data, exceptions and unvalidated URLs. Original incident context and historical action bytes remain available in the existing detail API; this change does not repair their prior privacy surface. `runbook_ref=runbooks/agent-completeness.md` applies only to proved indexed S1657 Remediator cases. Other cases have `runbook_ref=null` and the fixed runbook-gap sentence unless a separately reviewed indexed applicable runbook is proved.

The proposed list/detail read model adds exactly seven fields: `owner`, `owner_state`, `disposition`, `reason`, `runbook_ref`, `last_read_at`, `read_result`. Owner derives only from a reviewed actor allowlist and independently attributable `Incident.escalated_to` or a separately reviewed typed assignment action; `queue_owner`, action actor and BQ owner do not count. With `actors=[]`, every owner is null. `last_read_at` is only the DB `created_at` of the latest completed, actually invoked read linked to a same-incident start matching validated source, target and context version; a no-adapter completion or missing completion cannot set it. The latest unmatched or missing completion makes `read_result=unknown`, even if an earlier matching completion supplies `last_read_at`. An invoked timeout/refusal may set `last_read_at` while the result remains unknown/refused.

The existing GET list keeps its fields, default limit 25, `1<=limit<=100`, offset, and status values `open|diagnosing|mitigating|monitoring|resolved|escalated|all`; `status=closed` remains 422. New optional `unresolved`, `demoted`, `legacy`, `owner_state` and `disposition` filters intersect status, with invalid or repeated conflicting values returning 422. `status=all` plus `disposition=closed` or `unresolved=false` selects closed rows. An incompatible explicit status/unresolved pair returns zero. One first-match SQL CASE controls row disposition, filter and count **before** offset/limit: resolved; closed; escalated D as `demoted_operator_review`; escalated latest started check, with or without linked matching completion, as `recovery_pending_verification`; escalated existing `remediator_human_required` as `action_pending`; escalated recognized source with valid context as `current_failure`; otherwise `unknown_history`. D+L takes demotion precedence, check takes precedence over human-required, and terminal status takes precedence over historical actions. Rows order `(created_at DESC,id DESC)`; `total` is the current matching SQL count, not a cross-page snapshot. Reads remain write-free and start no agent. Source supersession, exact retirement and EXPECTED negative controls remain separate reviewed manual decisions, never automatic CASE outcomes.

Activation requires this reviewed companion published at the current indexed runbooks head **first**, then ownership quiescence and current-main parity/preservation, the exact full-source CC/GLM/DeepSeek review, current CI and source identity, any needed separately reviewed action-index DDL, production-shaped populated query plans with measured caps and concurrency/fairness proof, exact deployment identity, supported API comparison and normal authenticated operator API plus Chrome proof. Do not mutate T820 or the four paused rows as a shortcut. No production SQL, credential, provider, customer, runtime or activation step is part of this companion. On a later misclassification or load regression, disable only the new selector and read model; retain all original incidents, old notifications, and both old and new append-only actions. A flag rollback cannot erase observations or create a closeout.

### Normative projection — CORE §3, Agent Completeness Contract

Source: CORE §3.

> Every agent MUST satisfy ALL of the following before it can pass Gate 3:
>
> - REST endpoint via AgentRequestFactory (POST /api/v1/agents/{key}/request)
> - interaction_modes includes "rest_api" on the BaseAgent subclass
> - At least one @skill method with Pydantic I/O schema
> - Corresponding Koskadeux MCP tool ({agent_key}_request) in tools/agent_request.py
> - Health endpoint responding (GET /api/v1/agents/{key}/health)
> - Manifest endpoint responding (GET /api/v1/agents/{key}/manifest)
> - **MonitoringPolicy declared** on the BaseAgent subclass:
>   - At least 1 MetricDeclaration (what the agent monitors)
>   - At least 1 ValidationRule (post-skill output validation)
>   - At least 1 EscalationRule (what happens on persistent failure)
>   - Policy is code-first: defined in source, git history is the audit trail
>   - Tier 1 agents (SysAdmin, CRM Steward) require full policies with P0/P1 coverage
>   - Tier 2+ agents may use minimal policies (1 metric, 1 validation, 1 escalation)
>   - Compliance checked at GET /api/v1/internal/agent-compliance

> An agent without an MCP tool is invisible to the orchestrator and therefore does not exist operationally. The CRM Steward pattern (one NL request tool → agent handles internally) is the template for all agents.

### Normative projection — CORE §4, Agent Discovery

Source: CORE §4.

> All agents register with a central discovery endpoint:
>
> - `GET /api/v1/agents/discover` — returns agent names, skills, input/output schemas, and usage examples
> - Two tiers: public (redacted, for external LLMs) and internal (full manifests, requires internal key)
> - Agents expose skills via `@skill`-decorated methods with Pydantic I/O schemas, auto-generated into tool definitions

## Agent capabilities

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Agent author | Implement all required surfaces | BaseAgent and AgentRequestFactory | Repository write | COMPLETE |
| Gate 3 reviewer | Audit the complete checklist | Compliance endpoint and source read | Read-only | COMPLETE |
| Koskadeux orchestrator | Invoke the agent | `{agent_key}_request` | MCP request scope | COMPLETE |
| Claim-first operator | Programmatically claim; start Sol only for work; report bounded outcomes | production claim endpoint then `allai_remediator_request` | Railway child-process auth; personal scoped OAuth MCP; no model credentials | COMPLETE |

## How to operate

```yaml operate
- id: E-01
  trigger: A new or revised agent is being prepared for Gate 3.
  pre_conditions: [agent_key_known, source_available]
  tool_or_endpoint: GET /api/v1/internal/agent-compliance
  argument_sourcing: {agent_key: use the BaseAgent registration key}
  idempotency: IDEMPOTENT
  expected_success: {shape: complete compliance record, verification: match every required surface against source and live endpoints}
  expected_failures: [{signature: incomplete_agent_surface, cause: one or more endpoint, skill, tool, schema, or monitoring requirements are absent}]
  next_step_success: Attach the checklist evidence to Gate 3.
  next_step_failure: Isolate every missing surface before review can pass.
- id: E-02
  trigger: An orchestrator must confirm that an agent is discoverable and callable.
  pre_conditions: [agent_deployed, internal_auth_available]
  tool_or_endpoint: GET /api/v1/agents/discover
  argument_sourcing: {tier: use internal for complete manifest validation}
  idempotency: IDEMPOTENT
  expected_success: {shape: agent manifest with skills and schemas, verification: locate the agent key and compare its manifest to source}
  expected_failures: [{signature: missing_agent_manifest, cause: registration or manifest generation omitted the agent}]
  next_step_success: Verify the corresponding MCP request tool.
  next_step_failure: Repair registration or manifest generation before dispatch.
- id: E-03
  trigger: Gate 3 validates the agent health and request endpoints.
  pre_conditions: [agent_route_registered, service_running]
  tool_or_endpoint: GET health and POST request endpoints
  argument_sourcing: {routes: derive both paths from the canonical agent key}
  idempotency: IDEMPOTENT
  expected_success: {shape: healthy response and schema-valid request handling, verification: exercise both endpoints and validate the response contract}
  expected_failures: [{signature: agent_endpoint_unhealthy, cause: route registration, runtime startup, or schema wiring is incomplete}]
  next_step_success: Mark endpoint evidence complete.
  next_step_failure: Repair the failed surface and rerun the full checklist.
- id: E-04
  trigger: The restricted claim-first allAI Remediator runner is prepared for activation proof.
  pre_conditions: [dedicated_runner_project_exists, recurring_model_task_paused, dispatcher_not_loaded]
  tool_or_endpoint: Project-local Codex config, pinned SDK, dispatcher dry run, and live scoped MCP tools/list
  argument_sourcing: {runner_config: /Users/max/Projects/ai-market/allai-remediator-runner/.codex/config.toml, dispatcher: scripts/allai_remediator_dispatch.py, launch_agent: scripts/com.aimarket.allai-remediator-dispatcher.plist, required_live_mcp_tools: "[allai_remediator_request]", required_external_integrations: "[allai_remediator_request]", required_tool_approval: "allai_remediator_request only = approve; server default unset"}
  idempotency: IDEMPOTENT
  expected_success: {shape: no-work dry run reports agent_started=false and a separate SDK singleton proof succeeds, verification: require exact singleton discovery, read-only runner config, pinned SDK, current ChatGPT login, production claim transport, credential-removal test, nonoverlap lock test, and proof that no_work and human_required paths never import or start Codex}
  expected_failures: [{signature: remediator_isolation_failed, cause: an empty or human-only result can initialize Codex; live tools/list is not exactly allai_remediator_request; the model receives a backend or provider credential; another external integration is available; or the current SDK and CLI cannot call the singleton}]
  next_step_success: Retain the proof with the exact runner and plugin configuration for E-05.
  next_step_failure: Keep the recurring model task paused, do not load the dispatcher, and apply G-03.
- id: E-05
  trigger: An operator is ready to activate the claim-first dispatcher.
  pre_conditions: [exact_backend_sha_reviewed_merged_and_deployed, live_health_confirmed, scoped_discovery_exactly_singleton, personal_plugin_installed, E-04_complete, recurring_model_task_paused]
  tool_or_endpoint: User LaunchAgent com.aimarket.allai-remediator-dispatcher
  argument_sourcing: {plist: scripts/com.aimarket.allai-remediator-dispatcher.plist, cadence: 60 seconds, readiness: run one foreground dispatcher check before loading}
  idempotency: IDEMPOTENT
  expected_success: {shape: loaded user job with last foreground and scheduled no-work results agent_started=false, verification: confirm the old Codex recurring task remains paused, launchd reports the expected program and cadence, and no new Codex rollout appears for empty checks}
  expected_failures: [{signature: remediator_activation_not_ready, cause: any review, deployment, singleton, SDK, no-work, credential-isolation, or launchd proof is absent or fails}]
  next_step_success: Operate E-06.
  next_step_failure: Unload the dispatcher and leave the recurring model task paused; the queue remains durable.
- id: E-06
  trigger: The one-minute programmatic dispatcher runs.
  pre_conditions: [E-05_complete, production_claim_endpoint_available]
  tool_or_endpoint: scripts/allai_remediator_dispatch.py then allai_remediator_request only after status=work
  argument_sourcing: {sequence: acquire local nonblocking lock; claim in the Railway-authenticated child; exit for no_work or human_required; only for work start ephemeral gpt-5.6-sol and optionally search before finishing the exact claim, outcome: "fixed, retryable, or human_required only"}
  idempotency: NOT_IDEMPOTENT
  expected_success: {shape: no agent process for empty or human-only work; one bounded agent for one actionable claim; completion requires a completed allai_remediator_request action=finish tool call, verification: log only compact dispatcher state; accept fixed only when backend verification accepts it; never execute a provider write}
  expected_failures: [{signature: remediator_dispatcher_stale, cause: launchd job missing or repeatedly nonzero}, {signature: remediator_claim_conflict, cause: lease expired or token is mismatched or terminal}, {signature: remediator_verification_failed, cause: backend evidence cannot verify fixed}, {signature: remediator_agent_completed_without_finish, cause: model returned final prose without a completed allai_remediator_request action=finish call; release the exact claim retryable through the existing authenticated child}]
  next_step_success: Return on the next programmatic check.
  next_step_failure: Apply G-04; never widen tools, credentials, filesystem, network, or provider scope.
- id: E-07
  trigger: An operator opens /build-queue (needs-Max rows) or OPS Attention, verifies Remediator reporting, or reviews the Phase 1 incident read-model contract before activation.
  pre_conditions: [ops_needs_max_endpoint_deployed, incident_audit_available, phase1_source_identity_known]
  tool_or_endpoint: GET /api/v1/ops/needs-max, GET /api/v1/ops/operator-attention, and authenticated GET /api/v1/observability/incidents with detail when the reviewed Phase 1 read-model flag is enabled
  argument_sourcing: {period: fixed seven-day old Remediator window, ownership: "old reporting attributes only audited allAI:Remediator actions; Phase 1 allAI:ReadOnlyObserver is never ownership or assignee", handled: "distinct old owned incident ids with a recorded fixed, retryable, or human_required outcome; use the latest audited outcome regardless of resolver actor", agent_calls: "count remediator_claimed actions only when actor is exactly allAI:Remediator", needs_attention: current Remediator-owned escalated incidents within the S1657 Needs-Max audience that carry no demotion action, recent_limit: "10", phase1_filters: "status plus optional unresolved, demoted, legacy, owner_state, disposition; count before offset page"}
  idempotency: IDEMPOTENT
  expected_success: {shape: old needs-Max totals/items and Remediator metrics retain their S1657 audience; demoted incidents and unknown-owner human_required tickets stay on operator-attention; when separately activated the incident list/detail adds only the seven typed Phase 1 fields and preserves original context/actions, verification: compare old counts to IncidentAction audit rows and new filtered SQL count to all fixed-fixture pages; confirm one needs-Max row per current old-audience undemoted escalation and one Attention row per demoted escalation; confirm Phase 1 owner null under actors[], exact CASE precedence, latest matching completed DB-time last_read_at, no false recovery, and repeated GETs create no action or agent}
  expected_failures: [{signature: remediator_reporting_drift, cause: old claim counts or Needs-Max/Attention parity drift; Phase 1 projects ReadOnlyObserver as assignee/Remediator, infers recovery or Needs You, filters after pagination, misorders CASE precedence, uses a start or unmatched completion as last_read_at, leaks new free text, writes on GET, or starts an agent}]
  next_step_success: Keep the old report and any separately activated Phase 1 read model read-only; retain independent activation evidence.
  next_step_failure: Apply G-05; leave new flags off or roll them back without removing history or old notifications.
```

### How to operate.1 Manual Needs-Max incident closeout

Use this existing, human-authorized residual path only for non-GitHub incidents and GitHub incidents where the default-branch workflow is genuinely still red. GitHub recovery observed by the old backend verifier auto-resolves as `superseded` without manual closeout. Phase 1 metadata does not make a demoted or legacy incident eligible for autonomous closeout, does not establish current recovery, and grants no supersede authority. This procedure does not replace the claim-first worker or make provider adapters writable.

1. Read the incident and its append-only actions first. Freeze the original provider failure and failure text; for GitHub, retain the workflow run, repository, branch and SHA. If required identity is absent or ambiguous, leave the incident escalated.
2. Verify current recovery evidence for the incident before closeout. For GitHub, inspect the corrective diff, merged PR and merge SHA. For a runtime-affecting correction, verify that the live production deployment is successful and its deployed source contains the correction.
3. Check whether the old backend verifier already observes one of the three GitHub recovery conditions above; those eligible old-lane incidents leave automatically. A demoted incident is excluded from that old verifier, and a Phase 1 observation does not move it out of Attention. A genuinely red default-branch workflow still requires investigation and evidence of resolution before manual closeout. Preserve paused T820 and the four paused rows until their separately authorized decisions.
4. Resolve only through `POST /api/v1/observability/incidents/{incident_id}/supersede`, executed by a short-lived `railway run --service ai-market-backend --environment production --no-local` child using its injected `INTERNAL_API_KEY`. Do not open Infisical in a browser, perform an interactive Infisical login, print the key, or copy it into another process or browser.
5. GET the incident and require `status=resolved`, `resolved_by=human:admin`, plus final `superseded` and `transitioned_to_resolved` actions containing the exact evidence. In authorized operator Chrome, confirm the incident row is gone and the Needs-Max badge decreased. API output alone is not the required rendered-page proof.

## When it breaks

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Compliance reports an incomplete agent surface. | Endpoint, interaction mode, skill schema, MCP tool, or monitoring declaration is missing. | Compare source and live compliance output with the complete normative checklist in Architecture & interactions. | G-01 | CONFIRMED |
| F-02 | Discovery lists the agent but orchestration cannot call it. | The corresponding MCP request tool is absent or keyed differently. | Compare discovery key, BaseAgent key, route key, and tool name. | G-02 | CONFIRMED |
| F-03 | An empty or human-only queue result can start Codex; live scoped `tools/list` is not exactly `{allai_remediator_request}`; the runner exposes another external integration; or backend/Railway credentials reach the SDK environment. | Dispatcher ordering drifted, the Railway child boundary was removed, the project-local config was not loaded, or plugin/tool scope widened. | Unload the dispatcher and keep the recurring model task paused. Run dispatcher unit tests, a foreground no-work proof, the exact credential-removal test, and a fresh SDK singleton proof. | G-03 | CONFIRMED |
| F-04 | The dispatcher is stale, cannot claim/finish, cannot prove `fixed`, or the model exits with prose but no completed finish tool call. | LaunchAgent is absent or failing, Railway CLI auth failed, scoped OAuth/gateway failed, a 15-minute lease expired, fixed verification failed, or the agent did not call `allai_remediator_request(action=finish)`. | Inspect `launchctl print gui/$UID/com.aimarket.allai-remediator-dispatcher` and the compact dispatcher logs; run one foreground check; verify only bounded tool errors, the current claim token, backend-owned provider evidence, and either a completed finish call or a deterministic retryable release with reason `agent_completed_without_finish`. Cloudflare deployment presence is not fixed proof. | G-04 | CONFIRMED |
| F-05 | Old Needs-Max counts do not match the audit, an undemoted S1657-audience Remediator escalation is absent or duplicated, or a report GET starts an agent. In the separately enabled Phase 1 view, a D/L row is misclassified, an owner is invented, a latest missing completion is treated as recovery, or filters/count/pages disagree. | Old projection drifted from canonical `IncidentAction` or escalated-minus-demoted selection. New projection may have treated `allAI:ReadOnlyObserver`/`queue_owner` as assignee, changed CASE precedence, accepted incomplete witness, filtered after pagination, used reservation time as read time, or copied untrusted text. A demotion or supersession legitimately removes an old Needs-Max row; an outside-audience GitHub failure is intentionally absent. | Compare old seven-day `remediator_claimed` and terminal actions plus Needs-Max/Attention rows to the audit. For the new view check `actors=[]`, seven exact fields, D/L/status intersections, one SQL CASE and COUNT before offset, all pages, same-reservation/source/target/version completed DB-time `last_read_at`, latest unmatched unknown, null witness and fixed literal reasons. Repeated GETs must add no actions and start no agent; old detail bytes must remain intact. | G-05 | CONFIRMED |

## Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Monitoring Surface
  root_cause: One or more required code-first completeness declarations or runtime surfaces are absent.
  repair_entry_point: BaseAgent subclass and agent route registration
  change_pattern: Implement every missing checklist item and rerun source plus live compliance checks.
  rollback_procedure: Revert the incomplete agent change or keep the agent out of Gate 3 promotion.
  integrity_check: The compliance response and source audit show every required item.
- id: G-02
  symptom_ref: F-02
  component_ref: MCP Request Tool
  root_cause: Agent registration and MCP tool identity diverged.
  repair_entry_point: tools/agent_request.py
  change_pattern: Add or correct the canonical request tool and bind it to the same agent key.
  rollback_procedure: Remove the mismatched tool registration and leave the agent undispatched.
  integrity_check: The orchestrator resolves and invokes the canonical request tool.
- id: G-03
  symptom_ref: F-03
  component_ref: Claim-first Operator Worker
  root_cause: The dispatcher can start Codex without actionable work, credential boundaries widened, or the runner/plugin isolation contract drifted.
  repair_entry_point: scripts/allai_remediator_dispatch.py, its LaunchAgent, runner .codex/config.toml, and personal plugin metadata
  change_pattern: Unload the dispatcher and keep the recurring model task paused. Restore the claim-before-import order, separate Railway claim child, explicit credential removal, nonblocking lock, read-only runner, disabled non-remediator capabilities, singleton plugin, and exact-tool approval; then rerun E-04.
  rollback_procedure: Leave both dispatch mechanisms paused; the durable queue and existing provider alerting remain available.
  integrity_check: no_work and human_required never import or start Codex; work starts one ephemeral Sol process; credentials are absent; singleton discovery and SDK call pass.
- id: G-04
  symptom_ref: F-04
  component_ref: Claim-first Operator Worker
  root_cause: LaunchAgent execution, programmatic claim transport, scoped model transport, the current lease, or backend-owned fixed verification is unavailable or invalid.
  repair_entry_point: LaunchAgent status, dispatcher logs, Railway CLI login, scoped gateway health, bounded incident evidence, and normal human repair path
  change_pattern: Unload the dispatcher; keep the recurring model task paused. Repair claim transport or SDK compatibility without adding credentials or tools. Require a completed singleton finish call for success; if the model exits without one, release the exact claim retryable through the existing Railway-authenticated child instead of waiting for lease expiry. Repair provider incidents only through existing authorized paths.
  rollback_procedure: Preserve the root gateway/App surface and existing provider alerting; do not add credentials or tools, bypass an active peer, widen provider permissions, or rotate a nonexistent task internal key.
  integrity_check: Before reactivation, repeat E-04 and E-05, including foreground and scheduled no-work results with agent_started=false; fixed remains backend-verified and Telegram remains deduplicated human_required only within the S1657 Needs-Max audience.
- id: G-05
  symptom_ref: F-05
  component_ref: Claim-first Operator Worker
  root_cause: The old needs-Max projection or the separate Phase 1 read model no longer matches canonical Incident and IncidentAction evidence at its own boundary.
  repair_entry_point: Backend ops needs-max aggregation, BUILD QUEUE needs-Max rows (S1585), and default-off Phase 1 selector/read-model flags
  change_pattern: Restore old read-only Incident/IncidentAction projection with S1585/S1657 selection (escalated minus any demotion and outside-audience GitHub failures for Needs-Max; demoted incidents and unknown-owner human_required tickets on Attention; needsMax.total alone drives badge, title and favicon). Prove old Remediator attribution only from actor allAI:Remediator; count only its remediator_claimed actions, latest audited outcome and deduplicated incidents. Independently restore Phase 1 to escalated AND (D OR L), actor allAI:ReadOnlyObserver, actors[] owner gap, fixed reason catalog, exact seven fields, first-match CASE/filter/count before offset, completion-linked DB-time reads and unknown for incomplete witnesses. Do not turn metadata into an old-lane claim, notification, owner assignment or closeout.
  rollback_procedure: Disable only the new Phase 1 selector and read-model flags on a Phase 1 regression; preserve original incidents/context, historical and new append-only actions, old Needs-Max/Attention/Telegram notifications, and the old Remediator lane. For an old report-only fault, restore that projection under its existing authority; never erase audit history or add a second reporting store/agent.
  integrity_check: E-07 matches the canonical audit and every fixed-fixture page/count; both GETs remain write-free, demoted Attention and legacy no-auto-Needs-You stay distinct, and an empty queue cannot start Codex. Reactivation waits for the exact reviewed indexed companion, full-source review, measured plan/CI, deployment identity and authorized API/Chrome proof.
```

## Changes and maintenance

### H.1 Invariants

All completeness items are conjunctive; no single healthy surface substitutes for another.

### H.2 BREAKING predicates

Removing a required endpoint, typed skill, MCP tool, or monitoring declaration is BREAKING and cannot be normalized by companion prose.

### H.3 REVIEW predicates

Review changes to agent keys, endpoint shapes, manifest tiers, MonitoringPolicy schema, or compliance aggregation.

### H.4 SAFE predicates

Examples and explanatory prose are safe when the full normative checklist remains intact.

### H.5 Boundary definitions

#### module

The agent subclass, routes, generated manifest, MCP request tool, and monitoring declaration.

#### public contract

Discovery, request, health, and public manifest response shapes.

#### runtime dependency

Agent service, internal authentication, discovery registry, and Koskadeux MCP.

#### config default

No requirement defaults to satisfied; missing evidence fails Gate 3 closed.

### H.6 Adjudication

CORE decides constitutional requirements. This companion only makes their verification route explicit.

## Acceptance criteria

```yaml acceptance
scenario_set:
  - {id: I-01, type: operate, refs: [E-01], scenario: A new agent is ready for its Gate 3 compliance audit., expected_answers: [{kind: tool_call, tool: GET /api/v1/internal/agent-compliance, argument_keys: [agent_key]}], weight: 0.0625}
  - {id: I-02, type: operate, refs: [E-02], scenario: An orchestrator must discover an internal agent manifest., expected_answers: [{kind: tool_call, tool: GET /api/v1/agents/discover, argument_keys: [tier]}], weight: 0.0625}
  - {id: I-03, type: operate, refs: [E-03], scenario: Gate 3 must prove request and health endpoints respond., expected_answers: [{kind: classification, label: VERIFY_BOTH_ENDPOINTS}], weight: 0.0625}
  - {id: I-04, type: isolate, refs: [F-01], scenario: Compliance reports no MetricDeclaration for the agent., expected_answers: [{kind: classification, label: INCOMPLETE_AGENT}], weight: 0.0625}
  - {id: I-05, type: isolate, refs: [F-01], scenario: The agent has a request route but no typed skill., expected_answers: [{kind: classification, label: INCOMPLETE_AGENT}], weight: 0.0625}
  - {id: I-06, type: isolate, refs: [F-02], scenario: Discovery and MCP use different keys for the same agent., expected_answers: [{kind: classification, label: IDENTITY_MISMATCH}], weight: 0.0625}
  - {id: I-07, type: repair, refs: [G-01], scenario: A ValidationRule is absent from MonitoringPolicy., expected_answers: [{kind: human_action, verb: add, object: missing validation rule, target: code-first MonitoringPolicy}], weight: 0.0625}
  - {id: I-08, type: repair, refs: [G-02], scenario: The corresponding Koskadeux request tool is missing., expected_answers: [{kind: human_action, verb: add, object: canonical request tool, target: tools/agent_request.py}], weight: 0.0625}
  - {id: I-09, type: evolve, refs: [Changes and maintenance], scenario: A proposal removes health verification from Gate 3., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.0625}
  - {id: I-10, type: evolve, refs: [Changes and maintenance], scenario: A manifest gains an additive usage example field., expected_answers: [{kind: classification, label: REVIEW}], weight: 0.0625}
  - {id: I-11, type: ambiguous, refs: [H.6], scenario: Live compliance passes but source lacks a required declaration., expected_answers: [{kind: human_action, verb: fail, object: compliance review, target: conflicting evidence until resolved}], weight: 0.0625}
  - {id: I-12, type: operate, refs: [E-04], scenario: "A fresh strict-config runner still shows Codex root functions.exec, wait, request_user_input, and collaboration controls, while live scoped MCP tools/list is exactly allai_remediator_request and no nested executable or other external integration exists.", expected_answers: [{kind: classification, label: ACCEPT_ONLY_AS_NON_OPERATIONAL_HOST_SCAFFOLDING_WITH_FUNCTIONS_EXEC_RESERVED_FOR_THE_MCP_CALL}], weight: 0.0625}
  - {id: I-13, type: operate, refs: [E-05], scenario: Candidate transport code exists but deployed marker or live singleton discovery is absent., expected_answers: [{kind: classification, label: DO_NOT_ACTIVATE_OR_INFER_DEPLOYMENT}], weight: 0.0625}
  - {id: I-14, type: isolate, refs: [F-04], scenario: The LaunchAgent repeatedly exits nonzero while the queue is enabled., expected_answers: [{kind: classification, label: UNLOAD_DISPATCHER_KEEP_MODEL_TASK_PAUSED_AND_PRESERVE_QUEUE}], weight: 0.0625}
  - {id: I-15, type: repair, refs: [G-03], scenario: A no_work response imports the Codex SDK or a Railway credential appears in the SDK environment., expected_answers: [{kind: human_action, verb: unload and restore, object: claim-before-import and credential-separation boundary before fresh proof, target: dispatcher and runner configuration}], weight: 0.0625}
  - {id: I-16, type: isolate, refs: [F-04, G-04], scenario: Cloudflare reports a deployment and the worker submits fixed without separate health proof., expected_answers: [{kind: classification, label: REJECT_FIXED_AND_PRESERVE_READ_ONLY_BOUNDARY}], weight: 0.0625}
```

## Maintenance

```yaml lifecycle
last_refresh_session: S1605
last_refresh_commit: cdaeec975a587823d93a79a84cd72584cb939b8f
last_refresh_date: 2026-08-24T16:58:19Z
owner_agent: vulcan
refresh_triggers: [CORE agent completeness changes, agent endpoint or manifest schema changes, MonitoringPolicy or compliance endpoint changes, allAI Remediator backend, filter policy, dispatcher, scoped transport, runner isolation, plugin, cadence, activation, or needs-Max reporting changes]
scheduled_cadence: 30d
first_staleness_detected_at: null
```
