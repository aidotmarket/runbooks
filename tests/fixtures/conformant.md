---
system_name: infisical-secrets
purpose_sentence: Centralized secret storage and distribution for ai.market services and deployment automation.
owner_agent: sysadmin
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Secret values, access policies, rotation schedule, and deployment environment sync for ai.market systems.
linter_version: 1.0.0
---

# Infisical Secrets

## §A. Header

The YAML frontmatter above defines the authoritative §A header values for this runbook.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Secret read via CLI | SHIPPED | `infisical/cli.py:read_secret` | `tests/test_infisical_cli.py::test_read_secret` | 2026-04-20 |
| Secret sync audit | PARTIAL | `infisical/audit.py:sync_audit` | `tests/test_infisical_audit.py::test_sync_audit` | 2026-04-19 |
| Automated secret rotation UI | PLANNED | — | — | — |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| CLI | `infisical/cli.py:main` | local config, ephemeral stdout buffer | Infisical API, operator shell | Primary operator entry point for read and audit flows. |
| Sync Worker | `infisical/sync.py:run_sync` | secret snapshot cache, deployment state ledger | Infisical API, deploy pipeline | Pushes approved secret material to target environments. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| sysadmin | read secret | `Koskadeux:shell_request -> infisical secrets get` | service-account-readonly | COMPLETE |
| mp | inspect sync drift | `Koskadeux:shell_request -> infisical audit sync` | service-account-readonly | PARTIAL — add drift summarizer for multi-env comparisons |

## §E. Operate

```yaml operate
- id: E-01
  trigger: Support ticket reports a missing production frontend secret.
  pre_conditions:
    - user_authenticated
    - infisical_reachable
  tool_or_endpoint: infisical secrets get --project-id <id> --env prod --path <path>
  argument_sourcing:
    project_id: constant from environment inventory
    env: constant prod
    path: from support ticket body
  idempotency: IDEMPOTENT
  expected_success:
    shape: Plaintext secret value returned to secure stdout
    verification: Compare returned value with deployment environment at the same commit SHA
  expected_failures:
    - signature: "secret not found"
      cause: path typo or wrong environment selected
  next_step_success: Return the value over the approved secure channel and log completion
  next_step_failure: Escalate to §F-01 symptom isolation
- id: E-02
  trigger: Release preparation requires confirmation that a secret is present in staging.
  pre_conditions:
    - release_window_open
    - staging_access_granted
  tool_or_endpoint: infisical secrets get --project-id <id> --env staging --path <path>
  argument_sourcing:
    project_id: constant from release inventory
    env: constant staging
    path: from release checklist
  idempotency: IDEMPOTENT
  expected_success:
    shape: Secret value or masked presence check output
    verification: Match against the release checklist entry and current Infisical environment
  expected_failures:
    - signature: "permission denied"
      cause: role lacks staging read scope
  next_step_success: Confirm readiness in the release record
  next_step_failure: Escalate to §F-02 symptom isolation
- id: E-03
  trigger: Deployment automation must refresh the sync audit before rollout.
  pre_conditions:
    - deploy_pipeline_running
    - infisical_reachable
  tool_or_endpoint: infisical audit sync --project-id <id> --env prod
  argument_sourcing:
    project_id: constant from deployment configuration
    env: constant prod
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: sync-audit-prod
  expected_success:
    shape: Audit report describing secret sync state
    verification: Confirm the report contains the target environment and zero drift entries
  expected_failures:
    - signature: "timeout contacting api"
      cause: transient Infisical API outage or network partition
  next_step_success: Attach the audit report to the rollout record
  next_step_failure: Escalate to §F-02 symptom isolation
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | "secret not found" in a prod retrieval flow | path typo, wrong environment, missing sync | Run `infisical secrets list` for the reported path and compare prod versus staging | §G-01 | CONFIRMED |
| F-02 | sync audit reports unexpected drift | stale cache, failed worker run, incorrect environment mapping | Re-run the sync audit and compare worker logs for the same project and environment | §G-02 | HYPOTHESIZED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: CLI
  root_cause: Operator supplied an incorrect path or environment flag during retrieval.
  repair_entry_point: infisical/cli.py:resolve_secret_target
  change_pattern: Normalize path and environment arguments before issuing the read call.
  rollback_procedure: Revert the normalization change and restore the previous flag parser.
  integrity_check: Re-run the failing retrieval and confirm the expected secret is returned.
- id: G-02
  symptom_ref: F-02
  component_ref: Sync Worker
  root_cause: Cached sync state drifted from the authoritative environment snapshot.
  repair_entry_point: infisical/sync.py:run_sync
  change_pattern: Invalidate stale cache entries before recomputing environment sync status.
  rollback_procedure: Revert the cache invalidation patch and restart the worker with previous settings.
  integrity_check: Re-run the sync audit twice and confirm both reports show identical zero-drift state.
```

## §H. Evolve

### §H.1 Invariants

- Secret reads must always resolve against an explicitly named environment.
- Sync audit output must remain reproducible for the same project and environment inputs.

### §H.2 BREAKING predicates

- Any change that alters secret path resolution semantics across environments is BREAKING.
- Any change that removes a currently supported operator entry point is BREAKING.

### §H.3 REVIEW predicates

- Any change that adds a new integration target for secret sync requires REVIEW.
- Any change that changes operator-visible error wording for retrieval failures requires REVIEW.

### §H.4 SAFE predicates

- Documentation-only changes with no behavior changes are SAFE.
- Internal refactors preserving arguments, outputs, and environment mapping are SAFE.

### §H.5 Boundary definitions

#### module

The module boundary is one deployable Infisical integration unit such as the CLI or sync worker.

#### public contract

The public contract is the supported command surface, required arguments, output shape, and environment semantics exposed to operators or automation.

#### runtime dependency

A runtime dependency is any external API, credential source, service endpoint, or execution substrate required for the runbook flow to succeed.

#### config default

A config default is a fallback environment or path behavior that changes execution without the caller explicitly setting the value.

### §H.6 Adjudication

When a proposed change touches more than one boundary class, classify it at the highest-risk class and document the reasoning in the change review.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: Support needs the first action for a missing production frontend secret.
    expected_answers:
      - kind: tool_call
        tool: infisical secrets get
        argument_keys: [project-id, env, path]
    weight: 0.08333333333333333
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: Release prep needs confirmation that a staging secret exists before rollout.
    expected_answers:
      - kind: tool_call
        tool: infisical secrets get
        argument_keys: [project-id, env, path]
    weight: 0.08333333333333333
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: Deployment automation needs the first step to refresh the production sync audit.
    expected_answers:
      - kind: tool_call
        tool: infisical audit sync
        argument_keys: [project-id, env]
    weight: 0.08333333333333333
  - id: I-04
    type: operate
    refs: [E-01]
    scenario: An operator asks how to validate the path before returning a requested secret.
    expected_answers:
      - kind: tool_call
        tool: infisical secrets list
        argument_keys: [project-id, env, path]
    weight: 0.08333333333333333
  - id: I-05
    type: isolate
    refs: [F-01]
    scenario: The response shows secret not found and the operator must verify whether the path is wrong.
    expected_answers:
      - kind: tool_call
        tool: infisical secrets list
        argument_keys: [project-id, env, path]
    weight: 0.08333333333333333
  - id: I-06
    type: isolate
    refs: [F-02]
    scenario: The sync audit reports drift and the next action must identify whether the cache is stale.
    expected_answers:
      - kind: tool_call
        tool: infisical audit sync
        argument_keys: [project-id, env]
    weight: 0.08333333333333333
  - id: I-07
    type: isolate
    refs: [F-01]
    scenario: A responder must distinguish between an environment mistake and a missing secret.
    expected_answers:
      - kind: human_action
        verb: compare
        object: environment selection
        target: prod versus staging request context
    weight: 0.08333333333333333
  - id: I-08
    type: repair
    refs: [G-01]
    scenario: A fix is needed for repeated wrong-environment retrieval failures in the CLI.
    expected_answers:
      - kind: human_action
        verb: patch
        object: argument normalization
        target: infisical/cli.py:resolve_secret_target
    weight: 0.08333333333333333
  - id: I-09
    type: repair
    refs: [G-02]
    scenario: The worker must be corrected so stale cache entries stop causing sync drift.
    expected_answers:
      - kind: human_action
        verb: patch
        object: cache invalidation
        target: infisical/sync.py:run_sync
    weight: 0.08333333333333333
  - id: I-10
    type: evolve
    refs: [§H]
    scenario: A proposal adds a new sync target and needs classification against the evolve predicates.
    expected_answers:
      - kind: classification
        label: REVIEW
    weight: 0.08333333333333333
  - id: I-11
    type: evolve
    refs: [§H]
    scenario: A proposal changes default environment selection when the caller omits env.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.08333333333333333
  - id: I-12
    type: ambiguous
    refs: [E-03, F-02, G-02, §H]
    scenario: A deploy-time drift alert might indicate either transient infra issues or a real sync bug and needs careful classification.
    expected_answers:
      - kind: human_action
        verb: investigate
        object: drift alert
        target: sync worker plus environment state
    weight: 0.08333333333333333
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S487
last_refresh_commit: ea70326
last_refresh_date: 2026-04-21T17:30:00Z
owner_agent: sysadmin
refresh_triggers:
  - bq_completion
  - gate_approval
  - incident
scheduled_cadence: 90d
last_harness_pass_rate: 1.0
last_harness_date: 2026-04-20T02:00:00Z
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S487 / 2026-04-21T17:35:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
