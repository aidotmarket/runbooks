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
last_verified_at: 2026-08-12
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
| Scheduled Operator Worker | Codex recurring task and scoped remote MCP view | Incident and `IncidentAction` lease records | Backend `c706094867ee3806f53c0ececfa4c0bf65170a20` | `allAI:Remediator` is not a `BaseAgent`, Vulcan, or Mars. |

### Scheduled operator companion — allAI:Remediator

`allAI:Remediator` is a scheduled operator worker, not a `BaseAgent`, Vulcan, or Mars, and does not satisfy or replace the CORE completeness contract. It is configured to run as a Codex recurring task using `gpt-5.6-sol` on the existing ChatGPT Pro account every 15 minutes; treat it as stale after 35 minutes without a fresh heartbeat.

| Contract | Operational rule |
|---|---|
| Transport and actions | The only worker transport is the personal/dev scoped remote MCP view `https://mcp2.ai.market/remediator/`, whose live `tools/list` must be exactly `{allai_remediator_request}`. That canonical hostname must match the gateway's OAuth protected-resource metadata; `mcp.ai.market` is only an alias and must not be used as this plugin's OAuth resource. The singleton accepts only closed actions: `services` with no other fields to `GET /api/v1/observability/remediator/services`; `claim` with no other fields to `POST /api/v1/observability/remediator/claim` using fixed worker `allAI:Remediator`; `finish` with `incident_id`, `claim_token`, and `outcome`, plus only optional `reason` and typed `proposal`, to `POST /api/v1/observability/remediator/finish`; and bounded read-only `search` with `query` plus only `scope`, `category`, `corpus`, `limit`, `score_threshold`, and `include_archived` to `POST /api/v1/allai/search`. Search is inside the singleton and is not a separate general tool. |
| Authentication | The scheduled model receives no `INTERNAL_API_KEY`, Railway operator token, provider token, or other credential. The gateway injects its existing backend authentication server-side. Reviewed and merged gateway fold `64fd2bb7be105110bb2a5bf9b6fe4cc1b674664e` is the current idle-safe fold/reload target; its three transport blobs are byte-identical to reviewed implementation commit `702f3f27db8b9570503f541f750be201b8bc5d01`. Neither commit is proof of deployment or activation. The deployed-SHA marker covers `com.koskadeux.mcp`; because the public OAuth route is served by separate launch service `com.koskadeux.gateway`, activation also requires an idle-safe restart of that service and a live unauthenticated `401` from `/remediator/`. |
| Personal plugin | Plugin contents are metadata plus one remote `.mcp.json` only: no `.app.json`, local executable or script, bearer environment variable, or secret. The plugin and state-changing tool must never be published, shared, distributed, or attached to a public ai.market App; any public surface requires separate review. |
| Runner isolation | Use only `/Users/max/Projects/ai-market/allai-remediator-runner`. Its project-local `.codex/config.toml` sets `approval_policy=never`, `web_search=disabled`, `code_mode_host=true`, and `collaboration_modes=false`; disables `shell_tool`, `unified_exec`, `view_image`, `multi_agent`, `apps`, `in_app_browser`, `browser_use`, `browser_use_full_cdp_access`, `browser_use_external`, `computer_use`, `image_generation`, `goals`, `hooks`, `memories`, `skill_search`, `tool_suggest`, and `workspace_dependencies`; disables inherited `node_repl` and every currently installed non-remediator plugin; and enables only plugin `ai-market@personal`, server `allai-remediator`, tool `allai_remediator_request`. The tool alone has `approval_mode="approve"`, which is required for non-interactive scheduled execution under `approval_policy=never`; never set the server-wide default or pre-approve any future tool. Codex CLI 0.147 `codex exec` still cancels external MCP calls with `user cancelled MCP tool call` despite that setting ([upstream #29857](https://github.com/openai/codex/issues/29857)); it is a diagnostic limitation, not activation proof. Activation must use the actual scheduled desktop task. `code_mode_host` must remain enabled because `functions.exec` is the orchestrator through which the plugin MCP tool is called. Fresh `gpt-5.6-sol` strict-config runs show that Codex root host-control names (`functions.exec`, `functions.wait`, `functions.request_user_input`, and collaboration controls) remain system-visible despite the disabled feature flags. They are non-operational platform host scaffolding for this worker, not service/provider integrations: the automation must never invoke them except `functions.exec` solely to call `allai_remediator_request`. After plugin installation but before OAuth, nested `functions.exec` inventory was exactly `{apply_patch, update_plan, list_mcp_resource_templates, list_mcp_resources, read_mcp_resource}`; the three resource helpers are generic host scaffolding bound only to the same scoped server and must return no resources or templates after OAuth. None of those five host primitives may be used by the automation. Empirical `apply_patch` attempts against the runner workspace and `/tmp` were rejected by the read-only sandbox and created no file. The decisive activation contract is therefore not literally one total model-visible tool: live scoped MCP `tools/list` must equal `{allai_remediator_request}`; live resource and resource-template lists must be empty; that tool must be the runner's exactly one external operational/service integration; nested host inventory must contain no `exec_command`, browser, app, provider, repository, network tool, or other external integration; and any unexpected executable, resource, template, or external tool keeps ingress false and the task paused. The `allai-remediator` permission profile keeps root and temp denied, the runner workspace read-only, and command network disabled as defense in depth. |
| Provider intake | GitHub uses the existing signed `workflow_run` webhook. Railway reuses the existing five-minute SysAdmin health contract and forwards only latest `FAILED` or `CRASHED` deployment facts; do not add Railway's undocumented-auth project webhook or a second scheduler. The existing active-incident unique fingerprint prevents duplicate incidents while a failure is open; after resolution or closure, a recurring failure may open a fresh incident. Cloudflare v1 is adapter-only/manual intake: do not add a webhook, upgrade a zone plan, or widen the read token merely to automate ingestion. |
| Queue and lease | `ALLAI_REMEDIATOR_INCIDENT_QUEUE_ENABLED=false` by default. Claim only owned P2/P3 work using database time and `FOR UPDATE SKIP LOCKED`; leases are 15 minutes and only the current unexpired token may finish. Provider adapters stay read-only and `/services` must report `execute_allowed=false` for every provider. |
| Outcomes and verification | Outcomes are exactly `fixed`, `retryable`, or `human_required`. `fixed` requires a backend-observed newer successful run of the same GitHub workflow or a different newer healthy/successful Railway deployment. Cloudflare adapter/manual incidents cannot self-verify `fixed` in v1 and must finish `retryable` or `human_required` unless a separately reviewed verification source is added. Telegram remains backend-owned and is sent only for deduplicated `human_required`; existing provider alerting remains authoritative. |

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
| Scheduled operator | Claim and report bounded remediation work | `allai_remediator_request` only | Personal/dev scoped OAuth MCP; gateway-held backend auth | PLANNED — activation gated |

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
  trigger: The restricted allAI Remediator runner is prepared for activation proof.
  pre_conditions: [dedicated_runner_project_exists, recurring_task_paused, incident_ingress_false]
  tool_or_endpoint: Fresh runner root host-control inventory, functions.exec nested ALL_TOOLS inventory, project-local Codex config, and live scoped MCP tools/list
  argument_sourcing: {runner_config: /Users/max/Projects/ai-market/allai-remediator-runner/.codex/config.toml, required_live_mcp_tools: "[allai_remediator_request]", required_live_resources: "[]", required_live_resource_templates: "[]", required_external_integrations: "[allai_remediator_request]", required_tool_approval: "allai_remediator_request only = approve; server default unset", allowed_inert_nested_host_primitives: "[apply_patch, update_plan, list_mcp_resource_templates, list_mcp_resources, read_mcp_resource]", forbidden_inventory: "exec_command or any command runner, browser, app, provider, repository, network tool, resource, resource template, or other external integration"}
  idempotency: IDEMPOTENT
  expected_success: {shape: layered host-scaffolding and singleton external-integration evidence, verification: inspect a fresh actual runner context; require live scoped MCP tools/list to equal exactly allai_remediator_request, require resource and resource-template lists to be empty, and require the tool to be the exactly one external operational/service integration; prove nested host inventory contains no exec_command, browser, app, provider, repository, network tool, resource, resource template, or other external integration; record that the remaining root host controls are platform scaffolding and may not be invoked except functions.exec solely to call allai_remediator_request; record the exact five inert nested host primitives, none may be used by the automation, and apply_patch was write-denied for both runner workspace and /tmp with no file created; cross-check code_mode_host remains enabled only for MCP orchestration while every forbidden feature and non-remediator plugin is disabled, approval_policy=never, web_search=disabled, the workspace is read-only, and command network is disabled}
  expected_failures: [{signature: remediator_isolation_failed, cause: live scoped tools/list is not exactly allai_remediator_request; more than one external operational/service integration exists; nested host inventory contains exec_command, a browser, app, provider, repository, network tool, another executable, or another external integration; any host scaffolding is invoked outside the sole functions.exec call to allai_remediator_request; or the layered inventories cannot be proven complete}]
  next_step_success: Retain the proof with the exact runner and plugin configuration for E-05.
  next_step_failure: Keep ingress false, keep the recurring task paused, and apply G-03. Treat the observed apply_patch write denials as defense-in-depth evidence, not as a substitute for the executable and external-integration inventory contract.
- id: E-05
  trigger: An operator is ready to activate allAI Remediator incident ingress.
  pre_conditions: [exact_gateway_sha_reviewed_and_merged, idle_safe_reload_complete, deployed_marker_and_live_health_confirmed, scoped_discovery_exactly_singleton, live_services_and_claim_no_work_passed, personal_plugin_installed, runner_layered_isolation_contract_proof_passed, fresh_scheduled_no_work_run_observed]
  tool_or_endpoint: Normal backend configuration rollout for ALLAI_REMEDIATOR_INCIDENT_QUEUE_ENABLED
  argument_sourcing: {gateway_sha: use the exact reviewed scoped gateway commit, discovery: require only allai_remediator_request, readiness_calls: use services and claim through the scoped tool}
  idempotency: IDEMPOTENT
  expected_success: {shape: ingress enabled only after every precondition, verification: repeat services through the scoped tool and preserve owned P2/P3, read-only-provider, and singleton boundaries}
  expected_failures: [{signature: remediator_activation_not_ready, cause: any review, reload, deployment, discovery, no-work, plugin, layered-isolation-contract, or scheduled-run proof is absent or fails}]
  next_step_success: Run E-06 on the normal cadence.
  next_step_failure: Keep ingress false; do not infer that reviewed and merged gateway fold 64fd2bb7be105110bb2a5bf9b6fe4cc1b674664e or its byte-identical implementation commit 702f3f27db8b9570503f541f750be201b8bc5d01 is deployed.
- id: E-06
  trigger: The allAI Remediator recurring task reaches its 15-minute cycle.
  pre_conditions: [E-05_complete, scoped_singleton_available]
  tool_or_endpoint: allai_remediator_request
  argument_sourcing: {sequence: call services then claim; call search only for bounded read-only allAI knowledge; on work echo the incident_id and current claim_token to finish, outcome: "fixed, retryable, or human_required only"}
  idempotency: NOT_IDEMPOTENT
  expected_success: {shape: services plus work, no_work, or human_required heartbeat and an exact terminal outcome when work exists, verification: accept fixed only when backend verification accepts it; never execute a provider write}
  expected_failures: [{signature: remediator_worker_stale, cause: no fresh heartbeat for 35 minutes}, {signature: remediator_claim_conflict, cause: lease expired or token is mismatched or terminal}, {signature: remediator_verification_failed, cause: backend evidence cannot verify fixed}]
  next_step_success: Return on the next scheduled cycle.
  next_step_failure: Apply G-04; never widen tools, credentials, filesystem, network, or provider scope.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Compliance reports an incomplete agent surface. | Endpoint, interaction mode, skill schema, MCP tool, or monitoring declaration is missing. | Compare source and live compliance output with the complete normative checklist in §C. | G-01 | CONFIRMED |
| F-02 | Discovery lists the agent but orchestration cannot call it. | The corresponding MCP request tool is absent or keyed differently. | Compare discovery key, BaseAgent key, route key, and tool name. | G-02 | CONFIRMED |
| F-03 | Live scoped MCP `tools/list` is not exactly `{allai_remediator_request}`; a live MCP resource or template exists; the runner has another external operational/service integration; nested host inventory exposes `exec_command`, another executable, or a browser/app/provider/repository/network tool; host scaffolding is invoked outside the sole `functions.exec` call to `allai_remediator_request`; or layered inventory proof is incomplete. | A forbidden feature is enabled, inherited `node_repl` or a non-remediator plugin remains enabled, plugin/server/tool/resource scope drifted, the run did not load the project-local config, or inert built-in host scaffolding was mistaken for an authorized automation capability. Root `functions.exec`/`wait`/`request_user_input` and collaboration control names can remain system-visible even under strict config; visibility alone is not an extra external integration. | Keep ingress false and the recurring task paused. Separately capture root host controls, nested `functions.exec` `ALL_TOOLS`, live scoped MCP `tools/list`, and resource/template lists. Require the live MCP singleton, empty resources/templates, and exactly one external operational/service integration; require no nested command runner or browser/app/provider/repository/network/external tool; and verify that all host scaffolding remains unused except `functions.exec` solely for the MCP call. Confirm `code_mode_host=true`, retain the exact five inert nested host primitives, and retain the proof that workspace and `/tmp` patch attempts were write-denied and created no file. | G-03 | CONFIRMED |
| F-04 | The worker is stale, cannot claim/finish, or cannot prove `fixed`. | The task is paused or unhealthy, scoped OAuth/gateway/backend auth failed, a 15-minute lease expired, or fixed verification failed. | Compare the last heartbeat with the 35-minute threshold; inspect only bounded tool errors and allowlisted evidence; verify the current claim token and backend-owned provider result. Cloudflare deployment presence is not fixed proof. Do not use the Codex 0.147 `codex exec` cancellation defect as evidence that scheduled-task OAuth failed. | G-04 | CONFIRMED |

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
  component_ref: Scheduled Operator Worker
  root_cause: The runner exposed an unexpected executable or external integration, violated the non-invocation rule for built-in host scaffolding, or failed to load the project-local feature, plugin, server, tool, approval, search, or permission restrictions.
  repair_entry_point: /Users/max/Projects/ai-market/allai-remediator-runner/.codex/config.toml and personal ai-market plugin metadata
  change_pattern: Keep ingress false and the task paused; disable shell_tool, unified_exec, view_image, multi_agent, apps, in_app_browser, all browser_use variants, computer_use, image_generation, goals, hooks, memories, skill_search, tool_suggest, workspace_dependencies, inherited node_repl, and every installed non-remediator plugin; set collaboration_modes=false; retain approval_policy=never, web_search=disabled, code_mode_host=true solely to orchestrate the plugin MCP call, the allai-remediator permission profile, command network disabled, and only ai-market@personal server allai-remediator tool allai_remediator_request; set approval_mode=approve only on that exact tool and leave the server-wide default unset; prohibit invoking all built-in host scaffolding except functions.exec solely to call allai_remediator_request, including prohibiting automation use of the five inert nested host primitives; then start a fresh runner context and rerun E-04.
  rollback_procedure: Keep or restore ingress false and remove the personal plugin. Do not rotate a nonexistent task internal key.
  integrity_check: Live scoped tools/list is exactly allai_remediator_request; resource and resource-template lists are empty; it is the exactly one external operational/service integration; nested host inventory contains no exec_command, browser, app, provider, repository, network tool, other executable, resource, resource template, or other external integration; remaining built-in host scaffolding is unused except functions.exec solely for the MCP call; and the apply_patch write-denial evidence remains defense in depth rather than a total-tool claim.
- id: G-04
  symptom_ref: F-04
  component_ref: Scheduled Operator Worker
  root_cause: Scheduled execution, the scoped transport, the current lease, or backend-owned fixed verification is unavailable or invalid.
  repair_entry_point: Recurring-task status, scoped gateway health, bounded incident evidence, and normal human repair path
  change_pattern: Pause the recurring task; keep or restore ingress false; remove the personal plugin; if transport rollback is required, revert and idle-safe reload only the exact scoped gateway commit; let leases expire. Repair provider incidents only through existing authorized paths.
  rollback_procedure: Preserve the root gateway/App surface and existing provider alerting; do not add credentials or tools, bypass an active peer, widen provider permissions, or rotate a nonexistent task internal key.
  integrity_check: Before reactivation, repeat E-04 and every E-05 gate, including a fresh scheduled no-work run; fixed remains backend-verified and Telegram remains deduplicated human_required only.
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
  - {id: I-14, type: isolate, refs: [F-04], scenario: The last scheduled heartbeat is 35 minutes old., expected_answers: [{kind: classification, label: PAUSE_TASK_AND_RESTORE_INGRESS_FALSE}], weight: 0.0625}
  - {id: I-15, type: repair, refs: [G-03], scenario: "A fresh nested host inventory exposes exec_command, a live MCP resource/template, or another external integration, or the automation invokes an inert host primitive.", expected_answers: [{kind: human_action, verb: keep paused and remove, object: unexpected executable, resource, template, or external integration and prohibit host-primitive use before fresh layered proof, target: project-local Codex config and automation instructions}], weight: 0.0625}
  - {id: I-16, type: isolate, refs: [F-04, G-04], scenario: Cloudflare reports a deployment and the worker submits fixed without separate health proof., expected_answers: [{kind: classification, label: REJECT_FIXED_AND_PRESERVE_READ_ONLY_BOUNDARY}], weight: 0.0625}
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1533
last_refresh_commit: 64fd2bb7be105110bb2a5bf9b6fe4cc1b674664e
last_refresh_date: 2026-08-12T23:39:10Z
owner_agent: vulcan
refresh_triggers: [CORE agent completeness changes, agent endpoint or manifest schema changes, MonitoringPolicy or compliance endpoint changes, allAI Remediator backend, scoped transport, runner isolation, plugin, cadence, or activation changes]
scheduled_cadence: 30d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: null
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1533 / 2026-08-12T23:39:10Z
last_lint_result: PASS
retrofit: false
trace_matrix_path: runbooks/boot-kernel-companion-crosswalk.md
word_count_delta: null
```
