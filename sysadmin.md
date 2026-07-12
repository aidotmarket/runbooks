---
system_name: sysadmin-operating-model
purpose_sentence: The SysAdmin agent runs the bounded Observe -> Decide -> Act -> Verify -> (Fix | Escalate) operating loop for infrastructure health, capability compliance, and typed health contracts.
owner_agent: sysadmin
escalation_contact: max@ai.market
lifecycle_ref: §J
authoritative_scope: ai-market-backend SysAdmin singleton, verified capability registry, bind and dispatch probes, typed health contracts, monitor_unavailable behavior, and operator repair guidance as of backend commit 02e3830f.
linter_version: 1.0.0
---

# SysAdmin Operating Model (S1086)

## §A. Header

YAML frontmatter above is authoritative for the §A header fields. Source of truth is the S1086 Gate-2
spec plus live backend code; this page is the operator map.

- **BQ:** `build:bq-sysadmin-operating-model-redesign-s1086` (docs build S1097), updated for
  BQ-MONITORING-SYSADMIN-AUTOMATION-S1165.
- **Repo / surfaces:** `ai-market-backend` - `app/allai/agents/sysadmin/agent.py`,
  `app/allai/agents/sysadmin/monitors.py`, `app/allai/agents/sysadmin/singleton.py`,
  `app/agents/sysadmin/skills/{railway_ops,infisical_ops,shell_ops}.py`,
  `app/api/v1/endpoints/agent_health.py`, `app/main.py`.
- **Status (S1165):** verified live 2026-07-12 - `HEALTHY` after backend commit `02e3830f`.
  The previous false `DEGRADED`/P0 path from a healthy Titan-1 bind probe is fixed.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| `railway_read_status` read contract | SHIPPED | `app/agents/sysadmin/skills/railway_ops.py` | tests/test_sysadmin_operating_model_s1086.py | 2026-07-12 |
| `railway_env_set_redeploy` bounded write, dry-run first | SHIPPED | `app/agents/sysadmin/skills/railway_ops.py` | tests/test_sysadmin_railway_handlers.py | 2026-07-12 |
| `infisical_read_metadata` metadata-only read | SHIPPED | `app/agents/sysadmin/skills/infisical_ops.py` | tests/test_sysadmin_operating_model_s1086.py | 2026-07-12 |
| `resend_domain_status` provider read | SHIPPED | `app/services/sysadmin_resend.py` | tests/test_sysadmin_operating_model_s1086.py | 2026-07-12 |
| `host_inspect` read-only checkout inspection | SHIPPED | `app/agents/sysadmin/skills/shell_ops.py` | tests/test_sysadmin_operating_model_s1086.py | 2026-07-12 |
| `e2e_armed_window` route arming monitor with robust string-bool coercion | SHIPPED | `app/allai/agents/sysadmin/monitors.py:41` | tests/test_sysadmin_operating_model_s1086.py | 2026-07-12 |
| `titan1_health` Titan-1/MCP health read, 2xx only healthy | SHIPPED | `app/allai/agents/sysadmin/agent.py:636` | tests/test_sysadmin_operating_model_s1086.py | 2026-07-12 |
| `mcp_server_restart` dry-run/runbook-owned restart proposal | SHIPPED | `app/agents/sysadmin/skills/railway_ops.py` | tests/test_sysadmin_operating_model_s1086.py | 2026-07-12 |
| `escalation_test` route self-test | SHIPPED | `app/allai/agents/sysadmin/agent.py:679` | tests/test_sysadmin_operating_model_s1086.py | 2026-07-12 |
| `monitor_unavailable` check-execution failure class | SHIPPED | `app/allai/agents/sysadmin/agent.py:828` | tests/test_sysadmin_operating_model_s1086.py | 2026-07-12 |

Advertised, bound, and verified names must be identical. Missing callable, probe, owner, sanitizer,
or health contract is a compliance failure. Bind probes and capability handlers must return the
`CapabilityOutput` shape: `ok`, `capability`, `status`, and `evidence`. At backend `02e3830f`,
`CapabilityOutput` is defined in `app/allai/agents/sysadmin/agent.py:119`, and skill wrappers validate
through that schema, for example `titan1_health` at `app/allai/agents/sysadmin/agent.py:1199`.

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| SysAdmin singleton | `app/allai/agents/sysadmin/singleton.py` | process memory | `/agent-health`, `/agent-compliance`, scheduler | Sole probing, compliance-reporting, and contract-scheduling instance. |
| Verified capability registry | `app/allai/agents/sysadmin/agent.py:292` | process memory | skill wrappers, health contracts | Advertised, bound, and verified capability names must match. |
| Bind and dispatch probes | `app/allai/agents/sysadmin/agent.py:434` | `disabled_capabilities`, `probe_errors`, `dispatch_probe_errors` | real provider skills and `BaseAgent.execute_skill` | Probes exercise real dependency paths and return `CapabilityOutput`-compatible payloads. |
| Health contracts | `app/allai/agents/sysadmin/agent.py:394` | contract `last_result`, evidence hash, fingerprint sets | SysAdmin scheduler, allAI escalation | Contract runners observe typed evidence and then fix, ticket, or escalate. |
| Monitor-unavailable guard | `app/allai/agents/sysadmin/agent.py:819` | contract `last_result` | allAI escalation safety spine | Runner exceptions, timeouts, validation errors, or disabled capabilities become `monitor_unavailable`, with condition UNKNOWN. |
| E2E armed-window monitor | `app/allai/agents/sysadmin/monitors.py:47` | backend settings | E2E route flags and allowlists | `_settings_bool` prevents the string `"false"` from reading as armed. |
| AgentHost SysAdmin | `app/allai/agent_host.py` | event-bus runtime | allAI events | Event-bus participant only; it starts with `probe_on_startup=False` and must never prove health. |

SysAdmin is a small loop: Observe typed evidence, Decide failure class and allowed action, Act only
through a verified capability, Verify by rerunning the contract, then Fix or Escalate. Bind failures
enter LOUD-DEGRADED: `DEGRADED` for non-core failure, `UNAVAILABLE` for core escalation/health or
router failure. Failed capabilities are hard-disabled and reported with `probe_errors`.

Capability/contract binding is part of the monitor. If a probe payload omits required
`CapabilityOutput` fields, Pydantic rejects the invocation and the health contract self-reports as a
check-execution failure, not as proof that the monitored domain is broken. The S1165 fix made every
bind probe return `ok`, `capability`, `status`, and `evidence`; `_titan1_probe` now treats only HTTP
2xx as healthy and stamps non-2xx as `mcp_server_unhealthy`
(`app/allai/agents/sysadmin/agent.py:636`, `app/allai/agents/sysadmin/agent.py:640`).

When a health contract runner raises, times out, fails schema validation, or hits
`capability disabled: <name>`, SysAdmin stamps `failure_class=monitor_unavailable`,
`condition_status=unknown`, and preserves the domain class in `monitored_failure_class`
(`app/allai/agents/sysadmin/agent.py:819`). This means the check could not run. It does not assert
the domain condition, and it is observe/escalate only; it must never enter auto-remediation.

Known limitation: singleton state is process-local; multi-worker consistency is out of scope.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| sysadmin | Probe compliance and typed health contracts | `/agent-compliance`, `run_scheduler_once`, verified capability registry | backend runtime service identity | COMPLETE |
| sysadmin | Read Railway status and propose env-set/redeploy | `railway_read_status`, `railway_env_set_redeploy` | project-scoped Railway token for project `ai-market` | COMPLETE |
| sysadmin | Read secret metadata only | `infisical_read_metadata` | Infisical project `ai-market`, env `prod` | COMPLETE |
| sysadmin | Read host checkout and provider status | `host_inspect`, `resend_domain_status`, `titan1_health` | read-only host/provider credentials | COMPLETE |
| sysadmin | Self-test escalation route | `escalation_test` | Telegram relay settings through allAI | COMPLETE |
| AgentHost SysAdmin | Receive events without probing | event-bus handler with `probe_on_startup=False` | backend runtime service identity | PARTIAL — never use registry presence as health proof |

## §E. Operate

```yaml operate
- id: E-01
  trigger: "Operator needs current SysAdmin health and compliance."
  pre_conditions:
    - "Have INTERNAL_API_KEY from Infisical project ai-market, env prod."
  tool_or_endpoint: "GET /api/v1/internal/agent-compliance"
  argument_sourcing:
    header: "X-Internal-API-Key from Infisical"
  idempotency: IDEMPOTENT
  expected_success:
    shape: "SysAdmin row with status, compliant, checks, disabled_capabilities, probe_errors, dispatch_probe_errors, and contracts."
    verification: "compliant=true only when all checks pass and contract evidence is fresh."
  expected_failures:
    - signature: "401 or 403"
      cause: "missing or wrong INTERNAL_API_KEY"
  next_step_success: "If healthy, continue normal operations; if degraded, go to §F-01."
  next_step_failure: "Verify secret source and endpoint routing before diagnosing SysAdmin."
- id: E-02
  trigger: "Operator needs to scope a health-contract failure."
  pre_conditions:
    - "E-01 returned a SysAdmin contracts map."
  tool_or_endpoint: "contracts.<id>.last_result"
  argument_sourcing:
    contract_id: "from failing contract entry"
  idempotency: IDEMPOTENT
  expected_success:
    shape: "last_result includes ok, failure_class, severity or monitor_unavailable fields."
    verification: "If failure_class=monitor_unavailable, condition_status must be unknown and monitored_failure_class must be present."
  expected_failures:
    - signature: "last_result missing or stale"
      cause: "scheduler evidence stale or contract did not run"
  next_step_success: "Use §F-02 for monitor_unavailable or §F-03 for domain failures."
  next_step_failure: "Treat scheduler evidence freshness as the immediate fault."
- id: E-03
  trigger: "Railway project token must be re-minted without dashboard access."
  pre_conditions:
    - "Titan-1 account token is available through titan-1.md Railway auth."
  tool_or_endpoint: "POST https://backboard.railway.app/graphql/v2"
  argument_sourcing:
    project_id: "e81dd66f-808c-412e-b32c-f6d910f0ac5d"
    environment_id: "23e322c3-b195-45d8-9151-c4c27a998c33"
    token_source: "source ~/bin/railway-env.sh on Titan-1"
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: "project token for ai-market production environment"
    verification: "Railway operations authenticate with Project-Access-Token; Authorization Bearer is not accepted."
  expected_failures:
    - signature: "Not Authorized"
      cause: "wrong token type or Bearer header path"
  next_step_success: "Store in Infisical, set Railway service variable, redeploy, and verify /health."
  next_step_failure: "Escalate credential recovery to Max."
```

For this agent, `RAILWAY_API_TOKEN` is project-scoped for project `ai-market`
(`e81dd66f-808c-412e-b32c-f6d910f0ac5d`) and env `production`
(`23e322c3-b195-45d8-9151-c4c27a998c33`). It authenticates only with `Project-Access-Token`;
`Authorization: Bearer <project token>` returns Not Authorized. The token lives in Infisical project
`ai-market`, env `prod`, and as a Railway service variable on `ai-market-backend`.

All Railway CLI commands in this operating context must be prefixed with `unset RAILWAY_TOKEN &&`.
After any deploy, verify the health endpoint responds. Infisical manages secrets for the `ai-market`
project, not `ai-market-backend`, when the shipped deployment rule calls that out.

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | SysAdmin row is `DEGRADED`, `UNAVAILABLE`, or `compliant=false` | bind probe failed, dispatch probe failed, scheduler evidence stale, router unavailable, or core capability disabled | Start with `/agent-compliance`; inspect `disabled_capabilities`, `probe_errors`, `dispatch_probe_errors`, and `contracts.<id>.last_result` | G-01 | CONFIRMED |
| F-02 | `contracts.<id>.last_result.failure_class=monitor_unavailable` | runner raised, timed out, failed `CapabilityOutput` validation, or called a disabled capability | Read `contract_id`, `runner_name`, `error_type`, `error`, `condition_status`, and `monitored_failure_class`; `condition_status=unknown` means the monitored condition was not observed | G-02 | CONFIRMED |
| F-03 | Contract result has `ok=false` without runner exception | genuine domain alert such as unhealthy Titan-1, over-armed E2E route, provider failure, or escalation route failure | Scope by contract: `railway_status`, `infisical_metadata`, `resend_domain_status`, `host_inspection`, `e2e_armed_window`, `titan1_health`, or `escalation_route`; confirm `failure_class` is not `monitor_unavailable` | G-03 | CONFIRMED |
| F-04 | Titan-1 or MCP page says `mcp_server_unhealthy` | Titan-1 health endpoint returned non-2xx, or the MCP restart dry run saw Titan-1 unhealthy | Check `titan1_health` evidence `endpoint` and `status_code`; 2xx is healthy, 3xx redirect is misconfiguration, and non-2xx is a domain failure | G-04 | CONFIRMED |
| F-05 | Escalation did not retry after a failed page attempt | pre-S1165 fingerprint was burned before send, or a new regression marked fingerprint before successful page | Grep for CRITICAL `Failed to escalate SysAdmin contract`; confirm the fingerprint is not in `escalated_fingerprints` until page success | G-05 | CONFIRMED |
| F-06 | Production E2E route alarm mentions `e2e_routes_over_armed` | route flag truly armed beyond window, unparsable armed timestamp, or pre-S1165 string-bool parsing false alarm | Inspect `route_flag_enabled`, `armed_at`, allowlist counts, and `condition_status`; string `"false"` must coerce to false through `_settings_bool` | G-06 | CONFIRMED |

For `monitor_unavailable`, stop before diagnosing the domain. For example,
`monitored_failure_class=e2e_routes_over_armed` does not mean E2E routes are armed, and
`monitored_failure_class=mcp_server_unhealthy` does not mean Titan-1 is down. Use `runner_name` to
find the broken capability binding or runtime dependency. S1165 records these fields in
`app/allai/agents/sysadmin/agent.py:824`.

A contract result with `ok=False` and no runner exception is different: it is a genuine domain alert
and now flows through `_handle_contract_failure` at `app/allai/agents/sysadmin/agent.py:811`.

Do not use AgentHost registry presence as proof of SysAdmin health.

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: SysAdmin singleton
  root_cause: "A bind/dispatch probe, router lookup, or scheduler freshness check failed."
  repair_entry_point: "app/allai/agents/sysadmin/agent.py:bind_check_at_init"
  change_pattern: "Fix the systemic cause in credentials, provider API, skill implementation, runbook router, model pin, or scheduler evidence. Never re-enable a capability by hand."
  rollback_procedure: "Roll back only the faulty deploy or config change; do not bypass compliance with break_glass."
  integrity_check: "/agent-compliance reports HEALTHY, compliant=true, no disabled_capabilities, no probe_errors, and fresh contracts."
- id: G-02
  symptom_ref: F-02
  component_ref: Monitor-unavailable guard
  root_cause: "The check could not run, so the monitored condition is UNKNOWN."
  repair_entry_point: "app/allai/agents/sysadmin/agent.py:run_contract"
  change_pattern: "Repair the binding, schema, timeout, disabled capability, or runtime dependency that prevented observation. Confirm contract_id, runner_name, error_type, error, and monitored_failure_class before touching the monitored system."
  rollback_procedure: "Revert the monitor-binding or dependency change that caused the runner to raise; do not run domain remediation from a monitor_unavailable page alone."
  integrity_check: "The same contract next returns CapabilityOutput-shaped evidence and either ok=true or a genuine domain failure class, not monitor_unavailable."
- id: G-03
  symptom_ref: F-03
  component_ref: Health contracts
  root_cause: "The monitored domain returned ok=false without a runner exception."
  repair_entry_point: "app/allai/agents/sysadmin/agent.py:_handle_contract_failure"
  change_pattern: "Let allowlisted remediation run only when policy, confidence, dry-run, budget, and post-action verification all pass; otherwise escalate."
  rollback_procedure: "If remediation made state worse, revert that domain action and rerun the named verify contract."
  integrity_check: "Domain contract recovers to ok=true or an operator-visible escalation/ticket exists with the failure fingerprint."
- id: G-04
  symptom_ref: F-04
  component_ref: Health contracts
  root_cause: "Titan-1 health endpoint returned non-2xx, or the MCP restart dry run could not verify health."
  repair_entry_point: "app/allai/agents/sysadmin/agent.py:_titan1_probe"
  change_pattern: "Fix Titan-1 or mcp.ai.market health endpoint behavior. Treat redirects as misconfiguration, not health. Use mcp_server_restart only through dry-run, authorization, and verify flow."
  rollback_procedure: "Rollback the endpoint/tunnel/deploy change that introduced non-2xx behavior, then verify health."
  integrity_check: "`titan1_health` evidence shows HTTP 2xx and contract ok=true."
- id: G-05
  symptom_ref: F-05
  component_ref: Health contracts
  root_cause: "A failed page attempt must not burn the dedupe fingerprint."
  repair_entry_point: "app/allai/agents/sysadmin/agent.py:_escalate_contract_failure_once"
  change_pattern: "Ensure `escalated_fingerprints.add()` occurs only after `_escalate()` returns successfully; failures log CRITICAL and leave the fingerprint unmarked for retry."
  rollback_procedure: "Revert any change that marks fingerprints before delivery confirmation."
  integrity_check: "A simulated escalation exception is retried on the next contract cycle."
- id: G-06
  symptom_ref: F-06
  component_ref: E2E armed-window monitor
  root_cause: "Route flag parsing or actual route arming state is unsafe."
  repair_entry_point: "app/allai/agents/sysadmin/monitors.py:e2e_armed_window_status"
  change_pattern: "Use `_settings_bool` for E2E_TEST_ROUTES_ENABLED; if truly armed, empty both E2E allowlists, redeploy with E2E_TEST_ROUTES_ENABLED=false, then verify E2E endpoints return 404."
  rollback_procedure: "Restore the prior safe disarmed env and redeploy. All Railway CLI commands must be prefixed with `unset RAILWAY_TOKEN &&`."
  integrity_check: "`route_flag_enabled=false`, allowlist counts are zero, and the contract returns ok=true with status disarmed."
```

Auto-remediation is allowlisted only, dry-run first, budgeted, and verified by the named contract.
Off-allowlist, low-confidence, exhausted, or failed verification paths escalate.

## §H. Evolve

### §H.1 Invariants

- Operating loop remains Observe -> Decide -> Act -> Verify -> (Fix | Escalate).
- Advertised == bound == verified for every SysAdmin capability.
- Runtime init probes exercise real dependency paths, not static metadata.
- LOUD-DEGRADED is visible through `/agent-health`, `/agent-compliance`, and `get_system_status`.
- The singleton is the only probing, compliance-reporting, and scheduling instance.
- AgentHost SysAdmin starts with `probe_on_startup=False` and never probes.
- Scheduler freshness means every contract completed within `2 * cadence + jitter + timeout` and ok.
- `monitor_unavailable` means the check is broken and the monitored condition is unknown; it is not a domain failure and is never auto-remediated.
- A domain `ok=False` result must be handled by `_handle_contract_failure`; silent drop is forbidden.
- Escalation fingerprints are marked only after the page succeeds; failed pages must retry.
- Secret values are sanitized from logs, audit payloads, compliance responses, exceptions, prompts, and returns.

### §H.2 BREAKING predicates

- Removing the singleton as the source of `/agent-compliance` or scheduler evidence.
- Letting AgentHost or class-definition fallback report SysAdmin compliance.
- Treating `monitor_unavailable` as the preserved `monitored_failure_class` or routing it to auto-remediation.
- Marking an escalation fingerprint before a page succeeds.
- Returning plaintext Infisical or Railway secret values to handlers, logs, LLMs, or endpoints.

### §H.3 REVIEW predicates

- Adding, removing, or renaming a SysAdmin verified capability or health contract.
- Changing a contract failure class, severity, cadence, timeout, or remediation policy.
- Changing bind/dispatch probe inputs, output schema, or CapabilityOutput validation behavior.
- Changing Railway project-token recovery or deployment verification procedure.

### §H.4 SAFE predicates

- Documentation-only clarification that preserves this runbook's invariants.
- Adding tests for existing capability binding, monitor_unavailable, or contract failure behavior.
- Tightening log messages while preserving searchable substrings listed in §F.
- Read-only inspection of `/agent-compliance`, logs, or provider status.

### §H.5 Boundary definitions

#### module

The module boundary is the SysAdmin singleton, capability registry, typed monitor runner, and provider
skill implementation in `app/allai/agents/sysadmin/` and `app/agents/sysadmin/skills/`.

#### public contract

The public contract is `/agent-health`, `/agent-compliance`, `CapabilityOutput`, the verified
capability names, contract IDs, failure classes, and escalation context fields.

#### runtime dependency

Runtime dependencies are Railway, Infisical, Resend, Titan-1/mcp.ai.market, the host checkout,
Telegram/allAI escalation plumbing, backend settings, and the runbook router.

#### config default

`TITAN1_HEALTH_URL` defaults to `https://mcp.ai.market/health/titan1`. E2E routes are safe only when
`E2E_TEST_ROUTES_ENABLED` coerces false and both E2E allowlists are empty. Railway operations require
the project-scoped token and `Project-Access-Token` authentication.

### §H.6 Adjudication

Docs-only changes are SAFE when they preserve the invariants above. Capability, contract, escalation,
or remediation changes require review. Changes that can create silence, false P0 paging, secret
exposure, or unverified auto-remediation are BREAKING until proven otherwise.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: "Operator checks current SysAdmin health."
    expected_answers:
      - kind: tool_call
        tool: "GET /api/v1/internal/agent-compliance"
        argument_keys: [X-Internal-API-Key]
    weight: 0.08333333333333333
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: "A contract failure must be scoped from last_result."
    expected_answers:
      - kind: human_action
        verb: "inspect"
        object: "contracts.<id>.last_result"
        target: "failure_class and condition_status"
    weight: 0.08333333333333333
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: "Railway project token must be re-minted without dashboard access."
    expected_answers:
      - kind: tool_call
        tool: "Railway GraphQL projectTokenCreate"
        argument_keys: [project_id, environment_id]
    weight: 0.08333333333333333
  - id: I-04
    type: isolate
    refs: [F-01]
    scenario: "SysAdmin is DEGRADED and the first triage step is needed."
    expected_answers:
      - kind: human_action
        verb: "inspect"
        object: "disabled_capabilities and probe_errors"
        target: "/agent-compliance"
    weight: 0.08333333333333333
  - id: I-05
    type: isolate
    refs: [F-02]
    scenario: "The page says monitor_unavailable and mentions e2e_routes_over_armed."
    expected_answers:
      - kind: classification
        label: "check broken; monitored condition UNKNOWN"
    weight: 0.08333333333333333
  - id: I-06
    type: isolate
    refs: [F-03]
    scenario: "A contract returned ok=false without an exception."
    expected_answers:
      - kind: classification
        label: "genuine domain alert"
    weight: 0.08333333333333333
  - id: I-07
    type: isolate
    refs: [F-04]
    scenario: "Titan-1 returned HTTP 302."
    expected_answers:
      - kind: classification
        label: "misconfiguration; not healthy"
    weight: 0.08333333333333333
  - id: I-08
    type: repair
    refs: [G-02]
    scenario: "A disabled capability caused monitor_unavailable."
    expected_answers:
      - kind: human_action
        verb: "repair"
        object: "monitor binding or runtime dependency"
        target: "runner_name"
    weight: 0.08333333333333333
  - id: I-09
    type: repair
    refs: [G-04]
    scenario: "Titan-1 health is a real non-2xx domain failure."
    expected_answers:
      - kind: human_action
        verb: "repair"
        object: "Titan-1 or mcp.ai.market health endpoint"
        target: "titan1_health contract"
    weight: 0.08333333333333333
  - id: I-10
    type: evolve
    refs: [§H.2 BREAKING predicates]
    scenario: "A proposed change auto-remediates monitor_unavailable as mcp_server_unhealthy."
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-11
    type: evolve
    refs: [§H.3 REVIEW predicates]
    scenario: "A proposed change renames a SysAdmin health contract."
    expected_answers:
      - kind: classification
        label: REVIEW
    weight: 0.08333333333333333
  - id: I-12
    type: ambiguous
    refs: [F-02, F-03, G-02, G-03]
    scenario: "An escalation summary names a domain failure, but the structured context may show monitor_unavailable."
    expected_answers:
      - kind: human_action
        verb: "compare"
        object: "failure_class versus monitored_failure_class"
        target: "structured escalation context"
    weight: 0.08333333333333333
```

## §J. Lifecycle

Gate 2 design S1086 specified the verified capability registry, LOUD-DEGRADED init, typed contracts,
remediation budgets, runbook router, and compliance endpoint behavior. Implementation reduced
SysAdmin to the bounded set, added the singleton, moved compliance to live evidence, and wired
lifespan scheduling with cancel-on-shutdown.

S1097 docs build added this runbook and router entry.

2026-07-12 S1165 (`02e3830f`): monitor-binding false-alarm fix. Bind probes now satisfy
`CapabilityOutput`; `monitor_unavailable` separates broken checks from domain failures and escalates
P1/HITL with condition unknown; genuine `ok=False` domain alerts are handled; escalation fingerprints
are burned only after a successful page; and `e2e_armed_window_status()` coerces string booleans via
`_settings_bool` (`app/allai/agents/sysadmin/monitors.py:41`).

```yaml lifecycle
last_refresh_session: S1165
last_refresh_commit: 02e3830f638a8aadf6ed863c82149ea2e6be1d96
last_refresh_date: "2026-07-12T00:00:00Z"
owner_agent: sysadmin
refresh_triggers:
  - change to SysAdmin verified capabilities, bind probes, or CapabilityOutput schema
  - change to health contract failure classes, severities, cadence, or remediation policy
  - change to monitor_unavailable handling, escalation fingerprinting, or E2E armed-window coercion
scheduled_cadence: 90d
last_harness_pass_rate: 0.0
last_harness_date: "2026-07-12T00:00:00Z"
first_staleness_detected_at: null
```

## §K. Conformance

Source citations in this runbook were checked against ai-market-backend commit
`02e3830f638a8aadf6ed863c82149ea2e6be1d96`, specifically
`app/allai/agents/sysadmin/agent.py` and `app/allai/agents/sysadmin/monitors.py`. Live status was
reported `HEALTHY` after the monitor-binding fix; the prior false `DEGRADED`/P0
`mcp_server_unhealthy` behavior is fixed.

```yaml conformance
linter_version: 1.0.0
last_lint_run: "S1165 / 2026-07-12T00:00:00Z"
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
