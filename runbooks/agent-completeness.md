---
runbook_id: agent-completeness
domain: boot-kernel
status: ACTIVE
authoritative_for:
  - topic: agent-completeness
    section: §C. Architecture & Interactions
aliases: []
error_signatures:
  - signature: incomplete_agent_surface
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: vulcan
last_verified_at: "2026-08-12"
system_name: agent-completeness
purpose_sentence: This companion defines the endpoint, skill, health, manifest, and monitoring surfaces required before an agent can pass compliance review.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Delivery companion for agent creation and Gate 3 agent-compliance review; it projects the complete stable checklist from CORE without replacing it.
linter_version: 1.0.0
---

# Agent Completeness

## §A. Header

The frontmatter is authoritative for catalog identity. **Authority: delivery companion.** Full CORE and the Boot Kernel prevail over this document. This companion cannot weaken or extend the agent completeness contract.

**Fetch trigger:** agent creation or Gate 3 agent-compliance review.

**Source constitution:** CORE v9.11, SHA-256 `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`, sections 3 and 4.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| REST request and health surfaces | SHIPPED | `AgentRequestFactory` | Gate 3 compliance review | 2026-07-17 |
| Skill, schema, and manifest surfaces | SHIPPED | `BaseAgent` | Internal compliance endpoint | 2026-07-17 |
| Monitoring policy declarations | SHIPPED | `MonitoringPolicy` | Internal compliance endpoint | 2026-07-17 |

## §C. Architecture & Interactions

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
| Outcomes and verification | Outcomes are exactly `fixed`, `retryable`, or `human_required`. `fixed` requires a backend-observed newer successful run of the same GitHub workflow or a different newer healthy/successful Railway deployment. Cloudflare adapter/manual incidents cannot self-verify `fixed` in v1 and must finish `retryable` or `human_required` unless a separately reviewed verification source is added. A model run is complete only after the SDK records a completed `allai_remediator_request` call with `action=finish`; final prose is not completion. If the model exits without that call, the dispatcher uses the existing Railway-authenticated child to release the exact claim as `retryable` with reason `agent_completed_without_finish`. Telegram remains backend-owned and is sent only for deduplicated `human_required`; existing provider alerting remains authoritative. |
| For Max reporting | `GET /api/v1/ops/needs-max` derives the seven-day Remediator report directly from `Incident` and append-only `IncidentAction` records; it never starts Codex or writes reporting state. Remediator ownership is established by an audited action from actor `allAI:Remediator`; for an owned incident, the latest audited outcome is reported regardless of which authorised resolver recorded it. `handled` is the number of distinct incidents that reached a recorded `fixed`, `retryable`, or `human_required` outcome, including human escalations, and `agent_calls` counts only `remediator_claimed` actions whose actor is exactly `allAI:Remediator`. An active claim is a call but is not handled yet. `fixed` and `retrying` reflect the latest audited outcome. `needs_attention` is the current number of Remediator-owned escalated incidents. Each current escalation appears once in the existing attention feed and drives the existing red `FOR MAX` badge, title count, and red-dot favicon until it leaves `escalated`. Resolved incidents may remain visible as recently handled for seven days but must not carry a current attention indicator. Telegram remains the alert channel; `/for-max` is the read-only current-state and recent-activity view. |

### Normative projection — CORE §3, Agent Completeness Contract

Source SHA: `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`.

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

Source SHA: `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`.

> All agents register with a central discovery endpoint:
>
> - `GET /api/v1/agents/discover` — returns agent names, skills, input/output schemas, and usage examples
> - Two tiers: public (redacted, for external LLMs) and internal (full manifests, requires internal key)
> - Agents expose skills via `@skill`-decorated methods with Pydantic I/O schemas, auto-generated into tool definitions

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Agent author | Implement all required surfaces | BaseAgent and AgentRequestFactory | Repository write | COMPLETE |
| Gate 3 reviewer | Audit the complete checklist | Compliance endpoint and source read | Read-only | COMPLETE |
| Koskadeux orchestrator | Invoke the agent | `{agent_key}_request` | MCP request scope | COMPLETE |
| Claim-first operator | Programmatically claim; start Sol only for work; report bounded outcomes | production claim endpoint then `allai_remediator_request` | Railway child-process auth; personal scoped OAuth MCP; no model credentials | COMPLETE |

## §E. Operate

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
  trigger: An operator opens /for-max or verifies Remediator reporting.
  pre_conditions: [ops_needs_max_endpoint_deployed, incident_audit_available]
  tool_or_endpoint: GET /api/v1/ops/needs-max
  argument_sourcing: {period: fixed seven-day window, ownership: "an audited action from actor allAI:Remediator", handled: "distinct owned incident ids with a recorded fixed, retryable, or human_required outcome; use the latest audited outcome regardless of resolver actor", agent_calls: "count remediator_claimed actions only when actor is exactly allAI:Remediator", needs_attention: current Remediator-owned escalated incidents, recent_limit: "10"}
  idempotency: IDEMPOTENT
  expected_success: {shape: existing attention total and items plus remediator handled, agent_calls, fixed, retrying, needs_attention, and recent, verification: compare counts to IncidentAction audit rows; confirm one attention row per current escalation; confirm the request creates no action row and starts no agent}
  expected_failures: [{signature: remediator_reporting_drift, cause: claim actions and displayed calls differ; a current Remediator escalation is absent or duplicated; resolved work remains attention; or the report performs a write or starts Codex}]
  next_step_success: Leave the report read-only and continue normal queue operation.
  next_step_failure: Apply G-05; do not add a reporting store, reporting queue, or reporting agent.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Compliance reports an incomplete agent surface. | Endpoint, interaction mode, skill schema, MCP tool, or monitoring declaration is missing. | Compare source and live compliance output with the complete normative checklist in §C. | G-01 | CONFIRMED |
| F-02 | Discovery lists the agent but orchestration cannot call it. | The corresponding MCP request tool is absent or keyed differently. | Compare discovery key, BaseAgent key, route key, and tool name. | G-02 | CONFIRMED |
| F-03 | An empty or human-only queue result can start Codex; live scoped `tools/list` is not exactly `{allai_remediator_request}`; the runner exposes another external integration; or backend/Railway credentials reach the SDK environment. | Dispatcher ordering drifted, the Railway child boundary was removed, the project-local config was not loaded, or plugin/tool scope widened. | Unload the dispatcher and keep the recurring model task paused. Run dispatcher unit tests, a foreground no-work proof, the exact credential-removal test, and a fresh SDK singleton proof. | G-03 | CONFIRMED |
| F-04 | The dispatcher is stale, cannot claim/finish, cannot prove `fixed`, or the model exits with prose but no completed finish tool call. | LaunchAgent is absent or failing, Railway CLI auth failed, scoped OAuth/gateway failed, a 15-minute lease expired, fixed verification failed, or the agent did not call `allai_remediator_request(action=finish)`. | Inspect `launchctl print gui/$UID/com.aimarket.allai-remediator-dispatcher` and the compact dispatcher logs; run one foreground check; verify only bounded tool errors, the current claim token, backend-owned provider evidence, and either a completed finish call or a deterministic retryable release with reason `agent_completed_without_finish`. Cloudflare deployment presence is not fixed proof. | G-04 | CONFIRMED |
| F-05 | `/for-max` counts do not match the audit, a current Remediator escalation is missing or duplicated, or viewing the report starts an agent. | The read model stopped using canonical `IncidentAction` events, attention selection drifted from current `escalated` state, or reporting gained a write/agent path. | Compare `remediator_claimed` and terminal actions for the seven-day window with the endpoint; compare current Remediator-owned escalated incidents with attention rows; confirm repeated GET requests add no audit rows and start no Codex process. | G-05 | CONFIRMED |

## §G. Repair

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
  integrity_check: Before reactivation, repeat E-04 and E-05, including foreground and scheduled no-work results with agent_started=false; fixed remains backend-verified and Telegram remains deduplicated human_required only.
- id: G-05
  symptom_ref: F-05
  component_ref: Claim-first Operator Worker
  root_cause: The For Max read model no longer projects the canonical incident audit and current escalation state exactly once.
  repair_entry_point: Backend ops needs-max aggregation and the existing For Max console view
  change_pattern: Restore the seven-day read-only projection from Incident and IncidentAction, prove Remediator ownership from actor allAI:Remediator, report the latest audited outcome regardless of authorised resolver actor, deduplicate completed outcomes by incident for handled and current escalations for attention, count only allAI:Remediator remediator_claimed actions as agent calls, and keep the UI indicator driven only by the unified attention total.
  rollback_procedure: Remove the Remediator report projection while retaining the existing attention feed and Telegram alerting; never create a second reporting store or call Codex to prepare reporting.
  integrity_check: E-07 passes against live audit counts, repeated reads are write-free, and an empty queue cannot start Codex.
```

## §H. Evolve

### §H.1 Invariants

All completeness items are conjunctive; no single healthy surface substitutes for another.

### §H.2 BREAKING predicates

Removing a required endpoint, typed skill, MCP tool, or monitoring declaration is BREAKING and cannot be normalized by companion prose.

### §H.3 REVIEW predicates

Review changes to agent keys, endpoint shapes, manifest tiers, MonitoringPolicy schema, or compliance aggregation.

### §H.4 SAFE predicates

Examples and explanatory prose are safe when the full normative checklist remains intact.

### §H.5 Boundary definitions

#### module

The agent subclass, routes, generated manifest, MCP request tool, and monitoring declaration.

#### public contract

Discovery, request, health, and public manifest response shapes.

#### runtime dependency

Agent service, internal authentication, discovery registry, and Koskadeux MCP.

#### config default

No requirement defaults to satisfied; missing evidence fails Gate 3 closed.

### §H.6 Adjudication

CORE decides constitutional requirements. This companion only makes their verification route explicit.

## §I. Acceptance Criteria

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
  - {id: I-09, type: evolve, refs: [§H], scenario: A proposal removes health verification from Gate 3., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.0625}
  - {id: I-10, type: evolve, refs: [§H], scenario: A manifest gains an additive usage example field., expected_answers: [{kind: classification, label: REVIEW}], weight: 0.0625}
  - {id: I-11, type: ambiguous, refs: [§H.6], scenario: Live compliance passes but source lacks a required declaration., expected_answers: [{kind: human_action, verb: fail, object: compliance review, target: conflicting evidence until resolved}], weight: 0.0625}
  - {id: I-12, type: operate, refs: [E-04], scenario: "A fresh strict-config runner still shows Codex root functions.exec, wait, request_user_input, and collaboration controls, while live scoped MCP tools/list is exactly allai_remediator_request and no nested executable or other external integration exists.", expected_answers: [{kind: classification, label: ACCEPT_ONLY_AS_NON_OPERATIONAL_HOST_SCAFFOLDING_WITH_FUNCTIONS_EXEC_RESERVED_FOR_THE_MCP_CALL}], weight: 0.0625}
  - {id: I-13, type: operate, refs: [E-05], scenario: Candidate transport code exists but deployed marker or live singleton discovery is absent., expected_answers: [{kind: classification, label: DO_NOT_ACTIVATE_OR_INFER_DEPLOYMENT}], weight: 0.0625}
  - {id: I-14, type: isolate, refs: [F-04], scenario: The LaunchAgent repeatedly exits nonzero while the queue is enabled., expected_answers: [{kind: classification, label: UNLOAD_DISPATCHER_KEEP_MODEL_TASK_PAUSED_AND_PRESERVE_QUEUE}], weight: 0.0625}
  - {id: I-15, type: repair, refs: [G-03], scenario: A no_work response imports the Codex SDK or a Railway credential appears in the SDK environment., expected_answers: [{kind: human_action, verb: unload and restore, object: claim-before-import and credential-separation boundary before fresh proof, target: dispatcher and runner configuration}], weight: 0.0625}
  - {id: I-16, type: isolate, refs: [F-04, G-04], scenario: Cloudflare reports a deployment and the worker submits fixed without separate health proof., expected_answers: [{kind: classification, label: REJECT_FIXED_AND_PRESERVE_READ_ONLY_BOUNDARY}], weight: 0.0625}
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1533
last_refresh_commit: 2d7140878b28911e612b7e037d0d926a121ceb55
last_refresh_date: 2026-08-13T16:57:07Z
owner_agent: vulcan
refresh_triggers: [CORE agent completeness changes, agent endpoint or manifest schema changes, MonitoringPolicy or compliance endpoint changes, allAI Remediator backend, filter policy, dispatcher, scoped transport, runner isolation, plugin, cadence, activation, or For Max reporting changes]
scheduled_cadence: 30d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: null
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1533 / 2026-08-13T16:57:07Z
last_lint_result: PASS
retrofit: false
trace_matrix_path: runbooks/boot-kernel-companion-crosswalk.md
word_count_delta: null
```
