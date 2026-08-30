---
title: Infrastructure Discovery
owner: sysadmin
last_verified: '2026-07-17'
aliases: []
error_signatures:
- credential_exposed
- infrastructure_locator_guessed
- secret_disclosure
---

# Infrastructure Discovery

## Overview


**Fetch trigger:** locating any repository, service, secret, config, or deploy surface.

**Source constitution:** CORE v9.11, SHA-256 `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`, sections 3 and 4.

## Capabilities

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Living State resource registry | SHIPPED | `config:resource-registry` | Operator route verification | 2026-07-17 |
| Runbook index | SHIPPED | `INDEX.md`, `ERRORS.md` | `scripts/index.py` freshness check | 2026-08-30 |
| Inward machine discovery surface | SHIPPED | `/api/v1/ops/infra.llms.txt` | Inward endpoint smoke verification | 2026-07-17 |

## Architecture & interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Resource Registry | `state_request(action=get, key=config:resource-registry)` | Living State | SysAdmin and operational tools | Canonical infrastructure paths, services, configs, deploy surfaces, and secret identifiers. |
| Runbook pages | `INDEX.md`, `ERRORS.md`, or direct Markdown search | Git | Human and agent operators | Explain route order without copying locators. |
| Inward Discovery Surface | `/api/v1/ops/infra.llms.txt` | Backend-generated operational inventory | Internal agents | Machine-readable inward route; never a public secret disclosure surface. |

### Required three-surface route

1. **State authority:** read `config:resource-registry` for the current locator candidate.
2. **Runbook procedure:** read `runbooks/infrastructure-discovery.md` for the workflow and failure handling.
3. **Inward machine surface:** query `/api/v1/ops/infra.llms.txt` for internal agent discovery and verify it agrees with registry authority.

Registry authority does not make an unobserved resource real. Before a build,
deployment, credential change, or other mutation, verify the candidate on the
execution host and prove its identity with the resource's own read-only surface
(for example, filesystem existence plus Git remote and exact HEAD for a
checkout). An agent report, prior-session note, or remembered path is not that
proof. If the registry cannot be read safely, the candidate is absent, or the
identity differs, discovery is unresolved and the mutation must not start.

Do not hardcode repository, service, secret, configuration, or deploy locators into this page. Use `INDEX.md` only to find documentation; use `config:resource-registry` for current infrastructure locators.

### Normative projection — CORE §4, Infrastructure

Source SHA: `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`.

> For any operational query (service health, deploy status, repo locations, infrastructure config), check Living State.

> `state_get("config:resource-registry")` — canonical paths for repos, services, configs

> The SysAdmin agent maintains these entities. GitHub tools are also available via MCP — use `tool_search` to discover them.

The projection above is retained as source provenance because it uses legacy
tool spelling. Its current operational equivalent is to read
`config:resource-registry` with
`state_request(action=get, key=config:resource-registry)` and write through
`state_request(action=patch, ...)`. `state_get`, `state_patch`, and `runbook_get`
are not separate current gateway tools.

### Normative projection — CORE §3, Data and Security

Source SHA: `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`.

> MUST NOT commit secrets, tokens, or credentials. Infisical is the only secret store.

The registry and inward surface may identify secret names and approved retrieval routes; neither may expose secret values.

## Agent capabilities

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Any operator | Resolve current infrastructure locator | `state_request action=get` | Living State read | COMPLETE |
| SysAdmin | Maintain registry accuracy | `state_request action=patch` | Registry write with optimistic version | COMPLETE |
| Internal agent | Read machine discovery inventory | `/api/v1/ops/infra.llms.txt` | Internal authenticated read | COMPLETE |

## How to operate

```yaml operate
- id: E-01
  trigger: An operator needs a repository, service, config, or deploy locator.
  pre_conditions: [resource_subject_known, living_state_available]
  tool_or_endpoint: state_request(action=get, key=config:resource-registry)
  argument_sourcing: {action: use get, key: use the canonical registry entity key}
  idempotency: IDEMPOTENT
  expected_success: {shape: current canonical locator candidate and metadata, verification: at the action boundary prove the resource exists on the execution host and its own read-only identity matches the registry entry}
  expected_failures: [{signature: infrastructure_locator_guessed, cause: a remembered, copied, or agent-reported path was used without registry resolution}, {signature: registry_locator_unreal, cause: the registry candidate is absent on the execution host or identifies a different resource}, {signature: registry_payload_unsafe, cause: reading the registry would disclose credential material instead of identifier-only metadata}]
  next_step_success: Use the identity-proven locator for the bounded operational task.
  next_step_failure: Stop before mutation and isolate registry safety, availability, identity drift, or missing ownership.
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
  tool_or_endpoint: state_request(action=patch, key=config:resource-registry, body=<verified_patch>, updated_by=<actor>, source_ref=<evidence>, expected_version=<version>)
  argument_sourcing: {patch: supply only the verified locator field, actor_and_source: derive from the active operator and evidence, expected_version: use the version from the immediately preceding read}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(resource_id + expected_version + locator_digest)
  expected_success: {shape: updated registry entity, verification: read back registry and inward surface then compare}
  expected_failures: [{signature: registry_version_conflict, cause: another writer changed the registry first}]
  next_step_success: Regenerate or refresh derived discovery surfaces.
  next_step_failure: Re-read ownership and version before retrying without overwrite.
```

## When it breaks

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | A locator works only from one checkout, is absent on the execution host, or was reported without direct evidence. | The path was guessed, copied, hardcoded, or accepted from an agent narrative without resolving and proving the registry candidate. | Read `config:resource-registry` only through a value-safe projection, then directly prove existence and resource identity on the execution host; inspect the caller for copied locators or unsupported claims. | G-01 | CONFIRMED |
| F-02 | The inward discovery endpoint disagrees with Living State. | Derived inventory is stale or generated from a different source. | Compare the endpoint entry with the same resource in `config:resource-registry`. | G-02 | CONFIRMED |
| F-03 | A credential value appears in a registry response or full process-environment diagnostic. | A credential-bearing URL was stored as locator metadata, or an unredacted diagnostic returned injected secret values. | Do not fetch, quote, fingerprint in public output, or repeat the value. Record only the affected credential name, owner boundary, and exposure surface; treat the credential as compromised and open a no-secret incident record. | G-03 | CONFIRMED |

## Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Resource Registry
  root_cause: The operation bypassed canonical resource discovery or treated a locator claim as proof of a live resource.
  repair_entry_point: config:resource-registry
  change_pattern: Resolve the resource by identity, verify existence and native identity on the execution host, and remove copied locator assumptions or unsupported agent reports from the caller. If a registry read cannot avoid returning credential material, stop and repair its projection before using it.
  rollback_procedure: Stop using the unverified locator and leave the registry unchanged.
  integrity_check: A fresh value-safe registry read resolves the same resource whose existence and native identity were observed directly in the intended environment.
- id: G-02
  symptom_ref: F-02
  component_ref: Inward Discovery Surface
  root_cause: The generated inward inventory drifted from registry authority.
  repair_entry_point: /api/v1/ops/infra.llms.txt generator
  change_pattern: Regenerate the inward surface from current registry data without embedding secret values.
  rollback_procedure: Disable reliance on the stale derived entry and route directly to registry authority.
  integrity_check: Endpoint and registry identify the same resource and approved locator.
- id: G-03
  symptom_ref: F-03
  component_ref: Resource Registry
  root_cause: Discovery metadata or an unrestricted environment inspection crossed the identifier-only boundary and disclosed a live credential value.
  repair_entry_point: The credential's authoritative secret owner, the affected registry projection, and the diagnostic caller that emitted the value.
  change_pattern: Treat the exposed credential as compromised; coordinate revoke and rotation through its verified owning procedure, restart only its declared consumers, replace plaintext registry material with a non-secret identifier or retrieval route, and restrict diagnostics to key names or explicitly redacted status. Never copy the exposed value into tickets, events, runbooks, chat, or test fixtures.
  rollback_procedure: Roll back only the projection or diagnostic code if service verification regresses; never restore the exposed credential as an active value.
  integrity_check: The old credential is rejected, declared consumers pass redacted least-privilege probes with the replacement, and fresh registry and diagnostic output contains no credential value.
```

## Changes and maintenance

### H.1 Invariants

Discovery has three routes: plain Markdown for procedures, `config:resource-registry` for infrastructure locators, and the inward machine surface. A locator is only a candidate until the execution host and the resource's native read-only surface prove existence and identity at the action boundary.

### H.2 BREAKING predicates

Hardcoded locators, credential-bearing URLs or secret values in discovery output, unrestricted process-environment dumps, public exposure of the inward endpoint, or companion overrides of CORE are BREAKING.

### H.3 REVIEW predicates

Review changes to registry schema, resource identity, endpoint authentication, generator inputs, or catalog resolution.

### H.4 SAFE predicates

Explanatory examples are safe when they contain no live locator or secret value.

### H.5 Boundary definitions

#### module

The registry entity, this cataloged runbook, and the inward discovery endpoint generator.

#### public contract

Only the runbook id is public catalog metadata; the inward endpoint remains internal.

#### runtime dependency

Living State, runbook catalog resolution, internal backend authentication, and SysAdmin ownership.

#### config default

Unknown, unsafe, unavailable, absent, or identity-mismatched locator authority fails closed; no remembered path or agent report is a fallback.

### H.6 Adjudication

CORE governs safety, the registry governs current infrastructure locators, and this runbook governs the lookup workflow.

## Acceptance criteria

```yaml acceptance
scenario_set:
  - {id: I-01, type: operate, refs: [E-01], scenario: An operator needs the current path of a repository before a build., expected_answers: [{kind: tool_call, tool: state_request, argument_keys: [action, key], argument_values: {action: get, key: config:resource-registry}}, {kind: human_action, verb: prove, object: candidate resource existence and native identity, target: execution host}], weight: 0.0909090909}
  - {id: I-02, type: operate, refs: [E-02], scenario: An internal agent needs the inward infrastructure index., expected_answers: [{kind: tool_call, tool: GET /api/v1/ops/infra.llms.txt, argument_keys: []}], weight: 0.0909090909}
  - {id: I-03, type: operate, refs: [E-03], scenario: SysAdmin must correct a verified stale registry locator., expected_answers: [{kind: tool_call, tool: state_request, argument_keys: [action, key, body, updated_by, source_ref, expected_version], argument_values: {action: patch, key: config:resource-registry}}], weight: 0.0909090909}
  - {id: I-04, type: isolate, refs: [F-01], scenario: A deploy script uses a checkout-specific absolute path., expected_answers: [{kind: classification, label: GUESSED_LOCATOR}], weight: 0.0909090909}
  - {id: I-05, type: isolate, refs: [F-02], scenario: The inward endpoint and registry show different service URLs., expected_answers: [{kind: classification, label: DERIVED_SURFACE_DRIFT}], weight: 0.0909090909}
  - {id: I-06, type: isolate, refs: [F-01], scenario: A secret value appears inside discovery documentation., expected_answers: [{kind: classification, label: SECRET_DISCLOSURE}], weight: 0.0909090909}
  - {id: I-07, type: repair, refs: [G-01], scenario: An agent reports a canonical repository path that does not exist on the execution host., expected_answers: [{kind: human_action, verb: stop, object: mutation, target: unresolved discovery}, {kind: human_action, verb: verify, object: registry candidate existence and native identity, target: execution host}], weight: 0.0909090909}
  - {id: I-08, type: repair, refs: [G-02], scenario: Generated inward discovery data is stale., expected_answers: [{kind: human_action, verb: regenerate, object: inward discovery surface, target: current registry data}], weight: 0.0909090909}
  - {id: I-09, type: evolve, refs: [Changes and maintenance], scenario: A proposal embeds all live repository paths in this runbook., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.0909090909}
  - {id: I-10, type: evolve, refs: [Changes and maintenance], scenario: A registry schema adds an owner field for each resource., expected_answers: [{kind: classification, label: REVIEW}], weight: 0.0909090909}
  - {id: I-11, type: ambiguous, refs: [H.6], scenario: A runbook example conflicts with the current resource registry., expected_answers: [{kind: human_action, verb: prefer, object: current registry locator, target: bounded operation}], weight: 0.090909091}
```

## Maintenance

```yaml lifecycle
last_refresh_session: S1266
last_refresh_commit: e4d2057
last_refresh_date: 2026-07-17T22:00:00Z
owner_agent: sysadmin
refresh_triggers: [CORE infrastructure discovery changes, config:resource-registry schema changes, inward endpoint route or authentication changes]
scheduled_cadence: 30d
first_staleness_detected_at: null
```
