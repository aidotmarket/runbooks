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
last_verified_at: 2026-07-17
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
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Compliance reports an incomplete agent surface. | Endpoint, interaction mode, skill schema, MCP tool, or monitoring declaration is missing. | Compare source and live compliance output with the complete normative checklist in §C. | G-01 | CONFIRMED |
| F-02 | Discovery lists the agent but orchestration cannot call it. | The corresponding MCP request tool is absent or keyed differently. | Compare discovery key, BaseAgent key, route key, and tool name. | G-02 | CONFIRMED |

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
  - {id: I-01, type: operate, refs: [E-01], scenario: A new agent is ready for its Gate 3 compliance audit., expected_answers: [{kind: tool_call, tool: GET /api/v1/internal/agent-compliance, argument_keys: [agent_key]}], weight: 0.0909090909}
  - {id: I-02, type: operate, refs: [E-02], scenario: An orchestrator must discover an internal agent manifest., expected_answers: [{kind: tool_call, tool: GET /api/v1/agents/discover, argument_keys: [tier]}], weight: 0.0909090909}
  - {id: I-03, type: operate, refs: [E-03], scenario: Gate 3 must prove request and health endpoints respond., expected_answers: [{kind: classification, label: VERIFY_BOTH_ENDPOINTS}], weight: 0.0909090909}
  - {id: I-04, type: isolate, refs: [F-01], scenario: Compliance reports no MetricDeclaration for the agent., expected_answers: [{kind: classification, label: INCOMPLETE_AGENT}], weight: 0.0909090909}
  - {id: I-05, type: isolate, refs: [F-01], scenario: The agent has a request route but no typed skill., expected_answers: [{kind: classification, label: INCOMPLETE_AGENT}], weight: 0.0909090909}
  - {id: I-06, type: isolate, refs: [F-02], scenario: Discovery and MCP use different keys for the same agent., expected_answers: [{kind: classification, label: IDENTITY_MISMATCH}], weight: 0.0909090909}
  - {id: I-07, type: repair, refs: [G-01], scenario: A ValidationRule is absent from MonitoringPolicy., expected_answers: [{kind: human_action, verb: add, object: missing validation rule, target: code-first MonitoringPolicy}], weight: 0.0909090909}
  - {id: I-08, type: repair, refs: [G-02], scenario: The corresponding Koskadeux request tool is missing., expected_answers: [{kind: human_action, verb: add, object: canonical request tool, target: tools/agent_request.py}], weight: 0.0909090909}
  - {id: I-09, type: evolve, refs: [§H], scenario: A proposal removes health verification from Gate 3., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.0909090909}
  - {id: I-10, type: evolve, refs: [§H], scenario: A manifest gains an additive usage example field., expected_answers: [{kind: classification, label: REVIEW}], weight: 0.0909090909}
  - {id: I-11, type: ambiguous, refs: [§H.6], scenario: Live compliance passes but source lacks a required declaration., expected_answers: [{kind: human_action, verb: fail, object: compliance review, target: conflicting evidence until resolved}], weight: 0.090909091}
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1266
last_refresh_commit: e4d2057
last_refresh_date: 2026-07-17T22:00:00Z
owner_agent: vulcan
refresh_triggers: [CORE agent completeness changes, agent endpoint or manifest schema changes, MonitoringPolicy or compliance endpoint changes]
scheduled_cadence: 30d
last_harness_pass_rate: 1.0
last_harness_date: 2026-07-17T22:00:00Z
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1266 / 2026-07-17T22:00:00Z
last_lint_result: PASS
retrofit: false
trace_matrix_path: runbooks/boot-kernel-companion-crosswalk.md
word_count_delta: null
```
