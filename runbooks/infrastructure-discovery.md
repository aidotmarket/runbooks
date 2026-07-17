---
runbook_id: infrastructure-discovery
domain: boot-kernel
status: ACTIVE
authoritative_for:
  - topic: infrastructure-discovery
    section: §C. Architecture & Interactions
aliases: []
error_signatures:
  - signature: infrastructure_locator_guessed
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: sysadmin
last_verified_at: 2026-07-17
system_name: infrastructure-discovery
purpose_sentence: This companion provides the required three-surface route for locating repositories, services, secrets, configuration, and deploy surfaces.
owner_agent: sysadmin
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Delivery companion for infrastructure discovery through Living State, this cataloged runbook, and the inward operations discovery endpoint.
linter_version: 1.0.0
---

# Infrastructure Discovery

## §A. Header

The frontmatter is authoritative for catalog identity. **Authority: delivery companion.** Full CORE and the Boot Kernel prevail. This runbook routes discovery; it does not duplicate resource locators. Runbook locators remain generated in `CATALOG.json`, and infrastructure locators remain in `config:resource-registry`.

**Fetch trigger:** locating any repository, service, secret, config, or deploy surface.

**Source constitution:** CORE v9.11, SHA-256 `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`, sections 3 and 4.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Living State resource registry | SHIPPED | `config:resource-registry` | Operator route verification | 2026-07-17 |
| Cataloged discovery runbook | SHIPPED | `CATALOG.json` | Catalog validation and pinned retrieval | 2026-07-17 |
| Inward machine discovery surface | SHIPPED | `/api/v1/ops/infra.llms.txt` | Inward endpoint smoke verification | 2026-07-17 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Resource Registry | `state_get("config:resource-registry")` | Living State | SysAdmin and operational tools | Canonical infrastructure paths, services, configs, deploy surfaces, and secret identifiers. |
| Discovery Runbook | `runbook_get("infrastructure-discovery")` | SHA-pinned runbooks catalog | Human and agent operators | Explains route order without copying locators. |
| Inward Discovery Surface | `/api/v1/ops/infra.llms.txt` | Backend-generated operational inventory | Internal agents | Machine-readable inward route; never a public secret disclosure surface. |

### Required three-surface route

1. **State authority:** read `config:resource-registry` for the current locator.
2. **Runbook authority:** fetch `infrastructure-discovery` through the SHA-pinned `CATALOG.json` for the workflow and failure handling.
3. **Inward machine surface:** query `/api/v1/ops/infra.llms.txt` for internal agent discovery and verify it agrees with registry authority.

Do not hardcode repository, service, secret, configuration, or deploy locators into this companion. `CATALOG.json` is the locator authority for catalog members; `config:resource-registry` is the locator authority for infrastructure.

### Normative projection — CORE §4, Infrastructure

Source SHA: `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`.

> For any operational query (service health, deploy status, repo locations, infrastructure config), check Living State.

> `state_get("config:resource-registry")` — canonical paths for repos, services, configs

> The SysAdmin agent maintains these entities. GitHub tools are also available via MCP — use `tool_search` to discover them.

### Normative projection — CORE §3, Data and Security

Source SHA: `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`.

> MUST NOT commit secrets, tokens, or credentials. Infisical is the only secret store.

The registry and inward surface may identify secret names and approved retrieval routes; neither may expose secret values.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Any operator | Resolve current infrastructure locator | `state_get` | Living State read | COMPLETE |
| SysAdmin | Maintain registry accuracy | `state_patch` | Registry write with optimistic version | COMPLETE |
| Internal agent | Read machine discovery inventory | `/api/v1/ops/infra.llms.txt` | Internal authenticated read | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: An operator needs a repository, service, config, or deploy locator.
  pre_conditions: [resource_subject_known, living_state_available]
  tool_or_endpoint: state_get("config:resource-registry")
  argument_sourcing: {key: use the canonical registry entity key}
  idempotency: IDEMPOTENT
  expected_success: {shape: current canonical locator and metadata, verification: confirm the resource identity before use}
  expected_failures: [{signature: infrastructure_locator_guessed, cause: a remembered or copied path was used without registry resolution}]
  next_step_success: Use the resolved locator for the bounded operational task.
  next_step_failure: Stop and isolate registry availability or missing ownership.
- id: E-02
  trigger: An internal agent needs an infrastructure-oriented machine index.
  pre_conditions: [internal_auth_available, inward_endpoint_reachable]
  tool_or_endpoint: GET /api/v1/ops/infra.llms.txt
  argument_sourcing: {scope: request only the inward operational discovery surface}
  idempotency: IDEMPOTENT
  expected_success: {shape: machine-readable infrastructure discovery text, verification: cross-check selected locator with config:resource-registry}
  expected_failures: [{signature: inward_discovery_drift, cause: the inward surface and registry disagree}]
  next_step_success: Continue using registry-confirmed locator data.
  next_step_failure: Treat the registry as locator authority and repair the derived inward surface.
- id: E-03
  trigger: A missing or stale locator needs an ownership-safe correction.
  pre_conditions: [resource_owner_confirmed, current_entity_version_known]
  tool_or_endpoint: state_patch("config:resource-registry")
  argument_sourcing: {patch: supply only the verified locator field and expected version}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(resource_id + expected_version + locator_digest)
  expected_success: {shape: updated registry entity, verification: read back registry and inward surface then compare}
  expected_failures: [{signature: registry_version_conflict, cause: another writer changed the registry first}]
  next_step_success: Regenerate or refresh derived discovery surfaces.
  next_step_failure: Re-read ownership and version before retrying without overwrite.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | A locator works only from one developer checkout. | The path was guessed, copied, or hardcoded instead of resolved from the registry. | Read `config:resource-registry`, compare resource identity, and inspect the caller for copied locators. | G-01 | CONFIRMED |
| F-02 | The inward discovery endpoint disagrees with Living State. | Derived inventory is stale or generated from a different source. | Compare the endpoint entry with the same resource in `config:resource-registry`. | G-02 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Resource Registry
  root_cause: The operation bypassed canonical resource discovery.
  repair_entry_point: config:resource-registry
  change_pattern: Resolve the resource by identity and remove copied locator assumptions from the caller.
  rollback_procedure: Stop using the unverified locator and leave the registry unchanged.
  integrity_check: A fresh registry read resolves the same verified resource from the intended environment.
- id: G-02
  symptom_ref: F-02
  component_ref: Inward Discovery Surface
  root_cause: The generated inward inventory drifted from registry authority.
  repair_entry_point: /api/v1/ops/infra.llms.txt generator
  change_pattern: Regenerate the inward surface from current registry data without embedding secret values.
  rollback_procedure: Disable reliance on the stale derived entry and route directly to registry authority.
  integrity_check: Endpoint and registry identify the same resource and approved locator.
```

## §H. Evolve

### §H.1 Invariants

Discovery has three routes, but one locator authority per class: `CATALOG.json` for catalog documents and `config:resource-registry` for infrastructure.

### §H.2 BREAKING predicates

Hardcoded locators, secret values in discovery output, public exposure of the inward endpoint, or companion overrides of CORE are BREAKING.

### §H.3 REVIEW predicates

Review changes to registry schema, resource identity, endpoint authentication, generator inputs, or catalog resolution.

### §H.4 SAFE predicates

Explanatory examples are safe when they contain no live locator or secret value.

### §H.5 Boundary definitions

#### module

The registry entity, this cataloged runbook, and the inward discovery endpoint generator.

#### public contract

Only the runbook id is public catalog metadata; the inward endpoint remains internal.

#### runtime dependency

Living State, runbook catalog resolution, internal backend authentication, and SysAdmin ownership.

#### config default

Unknown or unavailable locator authority fails closed; no remembered path is a fallback.

### §H.6 Adjudication

CORE governs safety, the registry governs current infrastructure locators, and this runbook governs the lookup workflow.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - {id: I-01, type: operate, refs: [E-01], scenario: An operator needs the current path of a repository., expected_answers: [{kind: tool_call, tool: state_get, argument_keys: [key], argument_values: {key: config:resource-registry}}], weight: 0.0909090909}
  - {id: I-02, type: operate, refs: [E-02], scenario: An internal agent needs the inward infrastructure index., expected_answers: [{kind: tool_call, tool: GET /api/v1/ops/infra.llms.txt, argument_keys: []}], weight: 0.0909090909}
  - {id: I-03, type: operate, refs: [E-03], scenario: SysAdmin must correct a verified stale registry locator., expected_answers: [{kind: tool_call, tool: state_patch, argument_keys: [key, expected_version]}], weight: 0.0909090909}
  - {id: I-04, type: isolate, refs: [F-01], scenario: A deploy script uses a checkout-specific absolute path., expected_answers: [{kind: classification, label: GUESSED_LOCATOR}], weight: 0.0909090909}
  - {id: I-05, type: isolate, refs: [F-02], scenario: The inward endpoint and registry show different service URLs., expected_answers: [{kind: classification, label: DERIVED_SURFACE_DRIFT}], weight: 0.0909090909}
  - {id: I-06, type: isolate, refs: [F-01], scenario: A secret value appears inside discovery documentation., expected_answers: [{kind: classification, label: SECRET_DISCLOSURE}], weight: 0.0909090909}
  - {id: I-07, type: repair, refs: [G-01], scenario: A caller guessed a repository path that no longer exists., expected_answers: [{kind: human_action, verb: replace, object: guessed locator, target: registry-resolved locator}], weight: 0.0909090909}
  - {id: I-08, type: repair, refs: [G-02], scenario: Generated inward discovery data is stale., expected_answers: [{kind: human_action, verb: regenerate, object: inward discovery surface, target: current registry data}], weight: 0.0909090909}
  - {id: I-09, type: evolve, refs: [§H], scenario: A proposal embeds all live repository paths in this runbook., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.0909090909}
  - {id: I-10, type: evolve, refs: [§H], scenario: A registry schema adds an owner field for each resource., expected_answers: [{kind: classification, label: REVIEW}], weight: 0.0909090909}
  - {id: I-11, type: ambiguous, refs: [§H.6], scenario: A runbook example conflicts with the current resource registry., expected_answers: [{kind: human_action, verb: prefer, object: current registry locator, target: bounded operation}], weight: 0.090909091}
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1266
last_refresh_commit: e4d2057
last_refresh_date: 2026-07-17T22:00:00Z
owner_agent: sysadmin
refresh_triggers: [CORE infrastructure discovery changes, config:resource-registry schema changes, inward endpoint route or authentication changes]
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
