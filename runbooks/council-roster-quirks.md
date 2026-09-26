---
title: Council Roster and Quirks
owner: vulcan
last_verified: '2026-09-21'
aliases: []
error_signatures:
- stale_roster_snapshot
---

# Council Roster and Quirks

## Overview


**Fetch trigger:** before Council dispatch or voter validation.

> **ACTIVE OVERRIDE - Max S1738, Event Ledger `d50cbd80` (2026-09-25 to 2026-10-05):** Gemini is not dispatched for any review. CC holds the third voting seat with GLM and DeepSeek; the full panel remains unanimous. Apply the option A package standard and option C tiering and raiser-only fold re-review in `runbooks/council.md` ACTIVE OVERRIDE to the older roster and dispatch text below.
>
> **CURRENT ROSTER - S1721, CORE §5. This block supersedes older roster statements on this page, subject to the d50cbd80 active override above.**
> **S1721 base roster, subject to the d50cbd80 ACTIVE OVERRIDE above:** the Council is GLM, DeepSeek and Gemini. During the override CC takes Gemini's seat without a Gemini dispatch; use `runbooks/council.md` for the current gate. The base rule requires unanimous 3/3 valid votes, with an unusable vote rerun once.
> **CC is not a Council member.** `council_request agent=cc` remains as an explicit non-Council second opinion: never counted, cannot unlock completion. **Kimi is removed entirely** (code, launcher credential, issue-channel health source). AG is retired in code. There are no shadow reviewers (`SHADOW_REVIEWERS` is exported and empty).
> Cross-review completion is an allowlist: an independent mp/vulcan/mars peer, or all required voters with none of them the builder or author.
> Code truth: `council_reviewers.py` (`REQUIRED_REVIEWER_ORDER = ("glm", "deepseek", "gemini")`), `tools/agents.py` (`NON_COUNCIL_REVIEW_AGENTS = ("cc",)`, live `council_request` enum `mp, glm, deepseek, gemini, cc`), `council_orchestrator.py` (fail-closed consensus, rerun once). Model pins: `infra:council-comms` `body.model_policy`.
> Authority: Max S1721 - Event Ledger 47804cc4 (three voters), 51786409 (CC loses its seat, Kimi removed), c7edc37f (CC non-Council path), d3018462 (rerun once), 312e17d4 (Gemini model).
> Text below that names CC as a voter, Kimi as a comparison seat, or a CC/GLM/DeepSeek panel is history. Gemini member setup: `runbooks/council.md`, section "Gemini member".

**Source:** CORE §§4–5. Normative extracts below name their CORE section.

## Capabilities

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Live roster lookup | SHIPPED | `infra:council-comms` | Catalog resolution and operator verification | 2026-07-17 |
| Stable Council role constraints | SHIPPED | `docs/core/CORE.md` | Source-SHA cross-walk and strict lint | 2026-07-17 |
| Provider and behavioral quirk lookup | SHIPPED | `infra:council-comms` | Dispatch preflight verification | 2026-07-17 |

## Architecture & interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Live Roster | `state_request(action=get, key=infra:council-comms)` | Living State and model registry | Council dispatch gateway | Canonical for current models, active members, tools, and prompt quirks. |
| Stable Role Frame | `docs/core/CORE.md` sections 4 and 5 | Git and `infra:constitution` | Live Roster | CORE wins if stable role constraints conflict with live prose. |
| Dispatch Surface | `council_request` | Dispatch records | MP builder; GLM, DeepSeek, Gemini voters; CC non-Council second opinion; AG retired | Validate agent, mode, model, roster eligibility, and read/write scope before accepting a result. AG is retired and Kimi is removed; CC is a non-Council second opinion only. |

### Normative projection — CORE §4

Source: CORE §4.

> Each Council brain has different tools, behavioral defaults, and quirks. **This document names the roles; the live roster and current models live in `infra:council-comms` and the model registry — CORE does not pin model versions, because they change.** Before dispatching any Council task, check `state_get("infra:council-comms")` for the canonical reference.

The projection above is retained as source provenance because it uses a legacy
tool spelling. The callable current equivalent is
`state_request(action=get, key=infra:council-comms)`; `state_get` is not a
separate current gateway tool.

### Normative projection — CORE §5

Source: CORE §5.

> **S1721 base roster, subject to the d50cbd80 ACTIVE OVERRIDE in `runbooks/council.md`:** GLM, DeepSeek and Gemini form the base panel. Through 2026-10-05 CC holds Gemini's seat, Gemini is not dispatched, and unanimity applies. Kimi is removed. All voters evaluate independently across all dimensions. No assigned specialties — strengths emerge from debate. Frontier models only, always. Current model strings and dispatch configuration live in `infra:council-comms`.

> Vulcan and Mars are two cooperating frontier-model instances (current model strings live in the registry, not here), **peers of equal authority** over shell, git, dispatch, and Living State.

Stable dispatch roles carried from CORE §§4–5:

- MP is the mandatory builder and cannot vote on its own work.
- GLM, DeepSeek, and Gemini are the gate voters; a valid gate requires the policy-defined complete panel.
- CC is callable by explicit name as a non-Council second opinion only; its technically callable dispatch path does not confer voting authority. Kimi is removed.
- AG (Gemini) is RETIRED IN CODE 2026-08-11 (koskadeux-mcp f0c3eab03c, 'Retire DeepSeek AG and XAI integrations'): ag_server.py and antigravity_client.py are gone, `council_request` has no `ag` member, and nothing listens on 8766 (verified S1721, 2026-09-19). Reinstating Gemini is new work: a fourth `council_dir.py` member, not a revival of the AG server.
- Vulcan and Mars orchestrate and synthesize as peers; neither is a gate voter.
- Max is final authority, not a Council voter.

These bullets are companion synthesis, not a new source of constitutional authority.

## Agent capabilities

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan or Mars | Resolve roster before dispatch | `state_request action=get` | Living State read | COMPLETE |
| MP | Build approved work | `council_request agent=mp` | Repository write per dispatch | COMPLETE |
| GLM, DeepSeek, Gemini | Review and vote | `council_request` | Read-only review envelope | COMPLETE |
| CC | Non-Council second opinion by explicit name; never counted | `council_request agent=cc` | Read-only, non-voting | COMPLETE |
| AG | Retired 2026-08-11 (f0c3eab03c); not dispatchable | — | — | RETIRED |

## How to operate

```yaml operate
- id: E-01
  trigger: A Council build or review dispatch is about to be issued.
  pre_conditions: [task_scope_known, live_state_available]
  tool_or_endpoint: state_request(action=get, key=infra:council-comms)
  argument_sourcing: {entity: use the canonical live roster key}
  idempotency: IDEMPOTENT
  expected_success: {shape: current roster and tool quirks, verification: compare the intended agent and mode with live membership}
  expected_failures: [{signature: stale_roster_snapshot, cause: dispatch used a copied model or membership value instead of live state}]
  next_step_success: Dispatch with the live agent, mode, tool, and model constraints.
  next_step_failure: Stop dispatch and use F-01 to restore an authoritative roster read.
- id: E-02
  trigger: A returned gate vote must be accepted or discarded.
  pre_conditions: [dispatch_record_available, expected_voter_known]
  tool_or_endpoint: council_request result envelope
  argument_sourcing: {evidence: "use recorded agent, model, mode, target SHA, and permission scope"}
  idempotency: IDEMPOTENT
  expected_success: {shape: validated independent vote, verification: confirm voter membership, model, target, and read-only scope}
  expected_failures: [{signature: invalid_voter_envelope, cause: the result used the wrong model, target, mode, or voter}]
  next_step_success: Add the valid vote to the gate record.
  next_step_failure: Discard the vote and redispatch under the live roster.
- id: E-03
  trigger: A provider-specific behavioral quirk changes dispatch construction.
  pre_conditions: [live_roster_read, task_payload_bounded]
  tool_or_endpoint: council_request
  argument_sourcing: {prompt: apply only quirks currently recorded in infra:council-comms}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(agent + mode + target_sha + prompt_digest)
  expected_success: {shape: one dispatch bound to the intended task, verification: inspect the dispatch transcript and returned identity}
  expected_failures: [{signature: quirk_contract_mismatch, cause: stale prompt syntax or unsupported tool assumptions changed the request}]
  next_step_success: Continue with the validated result.
  next_step_failure: Refresh live state and retry only with a corrected dispatch contract.
```

## When it breaks

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Dispatch targets a paused member or stale model. | A copied roster snapshot replaced the live registry read. | Read `infra:council-comms` and compare member, provider, model, tool, and mode with the dispatch record. | G-01 | CONFIRMED |
| F-02 | A review result cannot count as an independent vote. | Builder identity, write access, wrong target, or model mismatch invalidated the envelope. | Inspect the recorded builder, reviewer, permissions, target SHA, and model verification. | G-02 | CONFIRMED |

## Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Live Roster
  root_cause: The dispatch relied on stale companion prose or remembered roster values.
  repair_entry_point: infra:council-comms
  change_pattern: Refresh live state and reconstruct the dispatch from current membership and quirks.
  rollback_procedure: Cancel or disregard the stale dispatch without changing roster state.
  integrity_check: The new dispatch identity and model match the live registry.
- id: G-02
  symptom_ref: F-02
  component_ref: Dispatch Surface
  root_cause: The returned result violated voter independence or target-binding requirements.
  repair_entry_point: council_request
  change_pattern: Discard the invalid result and issue a corrected read-only review to an eligible voter.
  rollback_procedure: Remove the invalid vote from the pending gate record.
  integrity_check: Builder and reviewer differ and the result binds to the intended target SHA.
```

## Changes and maintenance

### H.1 Invariants

Full CORE and the Boot Kernel prevail; current roster facts always come from `infra:council-comms` and the model registry.

### H.2 BREAKING predicates

Treat any change that makes companion prose override CORE, permits a builder to vote on its work, or replaces a required voter with an ineligible role as BREAKING.

### H.3 REVIEW predicates

Review changes to role descriptions, dispatch modes, voter-validation fields, or the live roster key.

### H.4 SAFE predicates

Spelling and examples are safe when they do not encode volatile model or membership facts.

### H.5 Boundary definitions

#### module

This catalog member and its resolver metadata.

#### public contract

The catalog id, authority boundary, fetch trigger, live-state route, and stable role frame.

#### runtime dependency

Living State, the model registry, and the Council dispatch gateway.

#### config default

No roster default exists; failure to read current authority fails dispatch closed.

### H.6 Adjudication

If CORE, the kernel, this companion, and live roster prose disagree, apply source precedence: CORE for stable obligations and live registry state for volatile roster values.

## Acceptance criteria

```yaml acceptance
scenario_set:
  - {id: I-01, type: operate, refs: [E-01], scenario: A reviewer dispatch needs the current Council member and model., expected_answers: [{kind: tool_call, tool: state_request, argument_keys: [action, key], argument_values: {action: get, key: infra:council-comms}}], weight: 0.0909090909}
  - {id: I-02, type: operate, refs: [E-02], scenario: A completed vote must be validated against its dispatch envelope., expected_answers: [{kind: classification, label: VALIDATE_VOTER_ENVELOPE}], weight: 0.0909090909}
  - {id: I-03, type: operate, refs: [E-03], scenario: A provider quirk changes the safe prompt shape for a review., expected_answers: [{kind: tool_call, tool: council_request, argument_keys: [agent, mode, task]}], weight: 0.0909090909}
  - {id: I-04, type: isolate, refs: [F-01], scenario: A dispatch names a member that live state marks paused., expected_answers: [{kind: classification, label: STALE_ROSTER}], weight: 0.0909090909}
  - {id: I-05, type: isolate, refs: [F-02], scenario: A builder appears in the reviewer set for its own commit., expected_answers: [{kind: classification, label: INVALID_INDEPENDENCE}], weight: 0.0909090909}
  - {id: I-06, type: isolate, refs: [F-02], scenario: A vote cites a different target SHA from the gate record., expected_answers: [{kind: classification, label: INVALID_TARGET}], weight: 0.0909090909}
  - {id: I-07, type: repair, refs: [G-01], scenario: A copied model string disagrees with the model registry., expected_answers: [{kind: human_action, verb: refresh, object: live roster, target: infra:council-comms}], weight: 0.0909090909}
  - {id: I-08, type: repair, refs: [G-02], scenario: A write-capable review result was mistakenly recorded as valid., expected_answers: [{kind: human_action, verb: replace, object: invalid vote, target: read-only eligible voter result}], weight: 0.0909090909}
  - {id: I-09, type: evolve, refs: [Changes and maintenance], scenario: A proposal lets companion prose pin current model versions., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.0909090909}
  - {id: I-10, type: evolve, refs: [Changes and maintenance], scenario: A role description changes while preserving CORE and live authority., expected_answers: [{kind: classification, label: REVIEW}], weight: 0.0909090909}
  - {id: I-11, type: ambiguous, refs: [H.6], scenario: CORE and live state appear to disagree on a Council role., expected_answers: [{kind: human_action, verb: separate, object: stable and volatile claims, target: CORE and live roster authorities}], weight: 0.090909091}
```

## Maintenance

```yaml lifecycle
last_refresh_session: S1369
last_refresh_commit: fa23332
last_refresh_date: 2026-07-27T21:45:44Z
owner_agent: vulcan
refresh_triggers:
  - CORE council role or voter constraint changes
  - infra:council-comms schema or roster route changes
  - Council dispatch identity or mode validation changes
scheduled_cadence: 30d
first_staleness_detected_at: null
```
