---
runbook_id: council-roster-quirks
domain: boot-kernel
status: ACTIVE
authoritative_for:
  - topic: council-member-interaction-policy
    section: §C. Architecture & Interactions
  - topic: council-member-mp
    section: §C.1 MP — mandatory builder
  - topic: council-member-cc
    section: §C.2 CC — read-only voter
  - topic: council-member-kimi
    section: §C.3 Kimi — read-only voter
  - topic: council-member-glm
    section: §C.4 GLM — read-only voter
  - topic: inactive-council-backend-ag
    section: §C.5 AG — inactive backend
  - topic: inactive-council-backend-deepseek
    section: §C.6 DeepSeek — inactive retired backend
aliases:
  - how-to-use-mp
  - how-to-use-cc
  - how-to-use-kimi
  - how-to-use-glm
  - why-ag-is-inactive
  - why-deepseek-is-inactive
  - ag-do-not-dispatch
  - deepseek-do-not-dispatch
  - council-member-interactions
error_signatures:
  - signature: stale_roster_snapshot
    section: §F. Isolate
  - signature: council_schema_contract_mismatch
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: vulcan
last_verified_at: 2026-08-02
system_name: council-roster-quirks
purpose_sentence: This companion gives one grounded interaction card for every active Council role and explicit do-not-dispatch cards for inactive AG and DeepSeek, while stopping dispatch when the connected schema disagrees with the signed deployed contract.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Delivery companion for Council roles, provider and tool lookup, dispatch-time behavioral quirks, and voter validation; the signed deployed contract and measured source identity own current callable facts, while CORE owns stable role constraints.
linter_version: 1.0.0
---

# Council Roster and Quirks

## §A. Header

The frontmatter is authoritative for this companion's catalog identity.
**Authority: delivery companion.** Full CORE and the Boot Kernel prevail over
this document in every conflict. Current callable members, models, providers,
modes, limits, and schema fields come only from the signed deployed gateway
contract bound to its exact release SHA. The large historical
`infra:council-comms` value is not a safe first-read authority because the
current state response truncates it mid-JSON; copied fragments and the obsolete
`config:council` value are discovery leads only.

**Fetch trigger:** automatically before every Council dispatch, build, review,
or voter validation. The dispatcher injects the member card; callers do not
name a runbook or pass runbook references.

**Source constitution:** CORE v9.13, SHA-256 `a8b4fa86b5cebc2c704e72219a0adfd8d63c84efd6dce60e6f7198161782e268`, sections 4 and 5. Normative extracts below name their CORE section and source SHA.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Monolithic live roster lookup | DEPRECATED | `infra:council-comms` | Current 49,999-character truncation must not be interpreted as complete JSON | 2026-08-02 |
| Stable Council role constraints | SHIPPED | `docs/core/CORE.md` | Source-SHA cross-walk and strict lint | 2026-07-17 |
| Monolithic provider/quirk lookup | DEPRECATED | `infra:council-comms` | Replaced by the signed compact runtime projection and member cards after cutover | 2026-08-02 |
| Signed compact Council runtime projection | PLANNED | `contracts/deployed-tool-contract.pin.json` | Schema-digest and exact-member smoke tests required before SHIPPED | 2026-08-02 |
| Automatic member-card delivery | PLANNED | `koskadeux-mcp/tools/agents.py` | Each agent+mode receives the matching immutable section before provider launch | 2026-08-02 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Signed Runtime Contract | exact deployed-contract pin and release identity | immutable signed artifact; compact runtime projection after cutover | Council dispatch gateway | Canonical for callable members, roles, models, providers, modes, caps, and tool-schema digest. A connected-schema mismatch blocks dispatch. |
| Stable Role Frame | `docs/core/CORE.md` sections 4 and 5 | Git and `infra:constitution` | Live Roster | CORE wins if stable role constraints conflict with live prose. |
| Dispatch Surface | `council_request` | backend intent, terminal result, and exact candidate-ref evidence | MP builder; CC, Kimi, GLM voters | The common boundary classifies the exact agent+mode, injects this card automatically, validates the signed schema digest, and rejects AG/DeepSeek as inactive. |

The interaction changed for one reason: remembered roster prose and connector
descriptions drift independently. A signed compact contract makes the machine
facts testable, while member cards explain how and why to use those facts. A
card never overrides the signed schema, and a schema never replaces the card's
human operating context.

### Normative projection — CORE §4

Source SHA: `a8b4fa86b5cebc2c704e72219a0adfd8d63c84efd6dce60e6f7198161782e268`.

<!-- catalog:historical -->
> Each Council brain has different tools, behavioral defaults, and quirks. **This document names the roles; the live roster and current models live in `infra:council-comms` and the model registry — CORE does not pin model versions, because they change.** Before dispatching any Council task, check `state_get("infra:council-comms")` for the canonical reference.
<!-- /catalog:historical -->

The projection above is retained as source provenance because it uses a legacy
tool spelling. The callable current equivalent is
`state_request(action=get, key=infra:council-comms)`; `state_get` is not a
separate current gateway tool.

### Normative projection — CORE §5

Source SHA: `a8b4fa86b5cebc2c704e72219a0adfd8d63c84efd6dce60e6f7198161782e268`.

> The gate voter panel is exactly **CC, Kimi, GLM** — three voters. All voters evaluate independently across all dimensions. No assigned specialties — strengths emerge from debate. Frontier models only, always. Current model strings and the active roster live in `infra:council-comms`, not here.

> Vulcan and Mars are two cooperating frontier-model instances (current model strings live in the registry, not here), **peers of equal authority** over shell, git, dispatch, and Living State.

Stable dispatch roles carried from CORE §§4–5:

- MP is the mandatory builder and cannot vote on its own work.
- CC, Kimi, and GLM are the gate voters; a valid gate requires the policy-defined complete panel.
- DeepSeek is inactive and retired; it is absent from ordinary Council dispatch and Hall schemas.
- AG is inactive; it is absent from ordinary Council dispatch and Hall schemas.
- Vulcan and Mars orchestrate and synthesize as peers; neither is a gate voter.
- Max is final authority, not a Council voter.

These bullets are companion synthesis, not a new source of constitutional authority.

**Current safe posture (2026-08-02):** the target Council has MP as the sole
builder role and `{cc, kimi, glm}` as the exact active voter/Hall set. AG and
DeepSeek are inactive. Measured deployed source identity `48996d8` and the
connected schema do not yet satisfy that target: the connector omits Kimi and
misdescribes roles/providers, while ordinary source schemas still expose
inactive backends. Council gate and Hall work stays blocked until the exact
release removes that drift. Never replace Kimi, count AG/DeepSeek, or
reinterpret CC as a builder to make a call pass.

### §C.1 MP — mandatory builder

**How to use MP as a Council member:** use MP only to build or author the
approved change under an exact target and preserved candidate ref.

- **Role:** active mandatory builder; never a reviewer, gate voter, or Council
  Hall participant.
- **Interaction:** use the signed schema's MP build/author route with the exact
  target repository, task, BQ, session, instance, and candidate branch. The
  common boundary injects task-relevant runbook context; the caller supplies no
  runbook fields. Substantial work is background work and is complete only when
  the terminal record and exact non-default remote candidate ref are preserved
  and independently resolved.
- **Current model fact:** the measured deployed runtime uses `gpt-5.6-sol`;
  future dispatches use the signed runtime value, not this remembered string.
- **Why:** separating build authority from voting prevents self-approval, while
  remote-ref preservation prevents a healthy build being discarded when a
  wrapper or parent process exits.
- **Stop:** a connector that calls MP a mandatory reviewer, asks for caller
  runbook references, or cannot return the exact candidate ref is incoherent.

### §C.2 CC — read-only voter

**How to use CC as a Council member:** send CC an exact-SHA read-only review
after someone else has built the candidate.

- **Role:** active independent gate voter; not a BQ or development builder.
- **Interaction:** dispatch a read-only review bound to the exact review SHA,
  base/head when required, spec, round, and verdict target. CC runs against the
  pinned checkout and returns asynchronously; poll the task and accept only the
  deployed terminal verdict schema (`APPROVE`, `APPROVED_WITH_MANDATES`, or
  `REJECT`). Verify cited evidence at the pinned SHA.
- **Why:** a pinned read-only checkout makes the vote independent of the author
  and prevents review of a moving or locally modified tree.
- **Stop:** a schema describing CC as a background builder, allowing writes, or
  advertising a different verdict vocabulary fails contract coherence.

### §C.3 Kimi — read-only voter

**How to use Kimi as a Council member:** use the signed exact-SHA read-only
provider route and its runtime-owned evidence limits.

- **Role:** active independent gate voter.
- **Interaction:** dispatch through the deployed exact-SHA provider loop. Kimi
  reads only the bounded at-SHA tools exposed by the signed contract; use the
  runtime-owned model, token, cost, and `max_tokens` limits. Do not replace this
  with a caller-preloaded diff or mutable checkout fallback.
- **Why:** Kimi's bounded repository tools and limits are part of the evidence
  envelope. Keeping them machine-owned avoids silently dropping files or
  fabricating a complete review from a truncated prompt.
- **Stop:** if Kimi or `max_tokens` is absent from the connected schema, the
  required voter panel is unavailable. Refresh/reconnect; do not substitute.

### §C.4 GLM — read-only voter

**How to use GLM as a Council member:** use the signed direct-z.ai read-only
route, page every incomplete repository view, and bind the vote to the exact SHA.

- **Role:** active independent gate voter.
- **Interaction:** dispatch through the exact-SHA read-only provider loop using
  the signed model and runtime-owned caps. The measured deployed provider is
  direct z.ai, not OpenRouter. Page repository paths through the provider tools
  when the result says more data remains; never infer that one page is complete.
- **Why:** provider identity, pagination, and caps determine what evidence GLM
  actually saw. Recording them prevents a plausible verdict from being counted
  against the wrong transport or an incomplete file set.
- **Stop:** an OpenRouter description, a prose-only cost cap, or an unpaged
  partial repository view fails contract coherence.

### §C.5 AG — inactive backend

**Why AG is inactive and must not be dispatched:** ordinary technical
reachability must not silently grant Council policy authority.

- **Role:** inactive; not a Council member, Hall participant, voter, builder, or
  quorum source.
- **Interaction:** do not dispatch AG through ordinary Council or Hall tools.
  If a separately authorized compatibility experiment is ever needed, it must
  live outside Council schemas and be structurally unable to emit or persist a
  Council verdict.
- **Why:** leaving a paused backend in ordinary enums lets technical
  reachability quietly become policy authority and makes the current Council
  ambiguous.
- **Stop:** any ordinary schema, default, route, or receipt that accepts AG is
  release drift and blocks Council work.

### §C.6 DeepSeek — inactive retired backend

**Why DeepSeek is inactive and must not be dispatched:** historical voter
status must not reactivate itself through a leftover route or enum.

- **Role:** inactive and retired; not a Council member, Hall participant,
  voter, builder, or quorum source.
- **Interaction:** do not dispatch DeepSeek through ordinary Council or Hall
  tools. Historical results remain audit evidence only. Any retained
  compatibility endpoint must be separately named outside Council and cannot
  emit, persist, normalize, or count a Council verdict.
- **Why:** separating technical reachability from policy authority prevents old
  full-voter/model-tier instructions from reactivating themselves.
- **Stop:** any ordinary schema, default, route, or receipt that accepts
  DeepSeek is release drift and blocks Council work.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan or Mars | Resolve the signed runtime and card; connected mismatch blocks gate work | deployed-contract verification plus automatic context | Immutable contract read | PARTIAL — close by deploying and smoking the signed compact projection |
| MP | Build approved work; connected description still needs correction | `council_request agent=mp` | Exact dispatch-scoped repository write and non-default candidate ref | COMPLETE |
| CC | Review and vote; connected description still needs correction | `council_request agent=cc mode=review` | Pinned-SHA read-only review | COMPLETE |
| Kimi | Review and vote; currently missing from connected schema | `council_request agent=kimi mode=review` | Bounded exact-SHA read-only provider tools | GAP — close by reconnecting a schema that exposes Kimi and max_tokens |
| GLM | Review and vote; connected provider description still needs correction | `council_request agent=glm mode=review` | Direct-z.ai exact-SHA read-only review | COMPLETE |
| AG | Inactive; ordinary dispatch and Hall calls must reject it | no Council tool | None | GAP — close by removing it from every ordinary enum/default/route and proving rejection |
| DeepSeek | Inactive and retired; ordinary dispatch and Hall calls must reject it | no Council tool | None | GAP — close by removing it from every ordinary enum/default/route and proving rejection |

## §E. Operate

```yaml operate
- id: E-01
  trigger: A Council build or review dispatch is about to be issued.
  pre_conditions: [task_scope_known, signed_deployed_contract_available, connected_schema_digest_matches, automatic_runbook_context_service_available]
  tool_or_endpoint: ordinary council_request(agent=<member>, mode=<mode>, task=<task>, target fields from the signed schema)
  argument_sourcing: {member_and_mode: use the signed runtime role card, target: use the exact repository SHA or build candidate branch, runbook_context: do not supply it because the common boundary injects this member card}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(session + agent + mode + canonical_arguments + target_identity)
  expected_success: {shape: dispatch identity bound to signed runtime revision and automatic member context, verification: compare recorded member model provider mode schema digest and target with the signed contract}
  expected_failures: [{signature: council_schema_contract_mismatch, cause: connected tool description or enum differs from the signed deployed source}]
  next_step_success: Continue under the matching member card and inspect the provider-observed terminal result.
  next_step_failure: Stop; refresh or reconnect the schema and repeat the exact coherence smoke without substituting a member.
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
  trigger: An MP build reaches terminal state.
  pre_conditions: [dispatch_identity_known, target_repo_validated, signed_runtime_revision_bound]
  tool_or_endpoint: council_request terminal build envelope
  argument_sourcing: {evidence: use the backend-observed terminal result and exact session-action-bound non-default remote candidate ref}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(session + dispatch_id + canonical_arguments + candidate_ref)
  expected_success: {shape: exact candidate ref and publication SHA preserved before cleanup, verification: independently resolve the remote ref and verify the terminal publication belongs to this action}
  expected_failures: [{signature: worktree_retirement_ambiguous, cause: provider work completed but durable parent lifetime or remote preservation could not be proved}]
  next_step_success: Review the preserved candidate SHA; do not rebuild it.
  next_step_failure: Retain the original worktree and recovery locator and use F-03.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Connected schema omits Kimi, calls CC a builder, calls GLM OpenRouter, or advertises DeepSeek as active Council. | Connector cache or deployed-description drift. | Compare the connected enum, descriptions, modes, caps, provider, and schema digest with the signed deployed contract and exact release source. | G-01 | CONFIRMED |
| F-02 | A review result cannot count as an independent vote. | Builder identity, write access, wrong target, or model mismatch invalidated the envelope. | Inspect the recorded builder, reviewer, permissions, target SHA, and model verification. | G-02 | CONFIRMED |
| F-03 | MP completed work but no usable candidate remains. | The wrapper retired an ephemeral common Git parent or cleaned before remote preservation. | Resolve the recorded candidate ref and inspect the retained worktree/common-dir recovery receipt without pruning or rebuilding. | G-03 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Signed Runtime Contract
  root_cause: The connected schema was generated from a different release or stale cache.
  repair_entry_point: gateway connector reload and deployed-contract publication
  change_pattern: Regenerate from the exact deployed source, publish the signed schema digest, reconnect, smoke MP plus CC/Kimi/GLM, and prove ordinary dispatch and Hall reject AG and DeepSeek.
  rollback_procedure: Keep Council dispatch blocked; never restore the stale schema as fallback.
  integrity_check: Required voters and Hall members equal {cc, kimi, glm}; MP is builder/non-voter; AG and DeepSeek are absent and rejected; CC is read-only; GLM is direct z.ai.
- id: G-02
  symptom_ref: F-02
  component_ref: Dispatch Surface
  root_cause: The returned result violated voter independence or target-binding requirements.
  repair_entry_point: council_request
  change_pattern: Discard the invalid result and issue a corrected read-only review to an eligible voter.
  rollback_procedure: Remove the invalid vote from the pending gate record.
  integrity_check: Builder and reviewer differ and the result binds to the intended target SHA.
- id: G-03
  symptom_ref: F-03
  component_ref: Dispatch Surface
  root_cause: Cleanup outran durable Git-parent and remote-candidate preservation.
  repair_entry_point: retained worktree recovery locator and exact candidate ref journal
  change_pattern: Preserve the original inode and common Git directory, repair registration only under the repo lock, publish the exact non-default candidate ref, then revalidate it before any cleanup.
  rollback_procedure: Leave the retained worktree and recovery journal intact; do not prune, delete, or rebuild.
  integrity_check: The candidate ref resolves remotely to the action publication SHA and the retained worktree remains a valid worktree after the caller parent exits.
```

## §H. Evolve

### §H.1 Invariants

Full CORE and the Boot Kernel prevail; current callable facts come from the
signed exact-release contract. Member cards explain the contract but do not
override it.

### §H.2 BREAKING predicates

Treat any change that makes companion prose override CORE, permits a builder to vote on its work, or replaces a required voter with an ineligible role as BREAKING.

### §H.3 REVIEW predicates

Review changes to role descriptions, dispatch modes, voter-validation fields, or the live roster key.

### §H.4 SAFE predicates

Spelling and examples are safe when they do not encode volatile model or membership facts.

### §H.5 Boundary definitions

#### module

This catalog member and its resolver metadata.

#### public contract

The catalog id, authority boundary, fetch trigger, signed runtime route, member
cards, and stable role frame.

#### runtime dependency

The signed deployed-contract verifier, compact Council runtime projections,
automatic context service, provider adapters, and Council dispatch gateway.

#### config default

No prose or connector-cache roster default exists; failure to verify the signed
runtime and connected schema digest fails dispatch closed.

### §H.6 Adjudication

If CORE, the kernel, this companion, and runtime disagree, apply source
precedence: CORE for stable obligations and the signed exact-release contract
for volatile callable facts. Stop when those authorities cannot be reconciled;
do not promote companion prose or truncated state to authority.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - {id: I-01, type: operate, refs: [E-01], scenario: A reviewer dispatch needs the current member and model., expected_answers: [{kind: human_action, verb: verify, object: connected schema digest and automatic member card, target: signed exact-release Council contract}], weight: 0.0909090909}
  - {id: I-02, type: operate, refs: [E-02], scenario: A completed vote must be validated against its dispatch envelope., expected_answers: [{kind: classification, label: VALIDATE_VOTER_ENVELOPE}], weight: 0.0909090909}
  - {id: I-03, type: operate, refs: [E-03], scenario: MP reports success but its caller is exiting., expected_answers: [{kind: human_action, verb: preserve, object: exact non-default remote candidate ref and original recovery worktree, target: session-action-bound build result}], weight: 0.0909090909}
  - {id: I-04, type: isolate, refs: [F-01], scenario: The connector omits Kimi and calls CC a builder., expected_answers: [{kind: classification, label: COUNCIL_SCHEMA_CONTRACT_MISMATCH}], weight: 0.0909090909}
  - {id: I-05, type: isolate, refs: [F-02], scenario: A builder appears in the reviewer set for its own commit., expected_answers: [{kind: classification, label: INVALID_INDEPENDENCE}], weight: 0.0909090909}
  - {id: I-06, type: isolate, refs: [F-02], scenario: A vote cites a different target SHA from the gate record., expected_answers: [{kind: classification, label: INVALID_TARGET}], weight: 0.0909090909}
  - {id: I-07, type: repair, refs: [G-01], scenario: A connected provider description disagrees with the signed deployment., expected_answers: [{kind: human_action, verb: regenerate, object: connected Council schema and compact member projections, target: exact deployed source and signed schema digest}], weight: 0.0909090909}
  - {id: I-08, type: repair, refs: [G-03], scenario: A completed MP build lost its ephemeral caller parent., expected_answers: [{kind: human_action, verb: recover, object: retained durable worktree and exact candidate ref, target: original build without rebuilding}], weight: 0.0909090909}
  - {id: I-09, type: evolve, refs: [§H], scenario: A proposal lets companion prose pin current model versions., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.0909090909}
  - {id: I-10, type: evolve, refs: [§H], scenario: A role description changes while preserving CORE and the signed runtime., expected_answers: [{kind: classification, label: REVIEW}], weight: 0.0909090909}
  - {id: I-11, type: ambiguous, refs: [§H.6], scenario: CORE and the signed runtime appear to disagree on a Council role., expected_answers: [{kind: human_action, verb: separate, object: stable and volatile claims, target: CORE and signed runtime authorities}], weight: 0.090909091}
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1413
last_refresh_commit: fa23332
last_refresh_date: 2026-08-02T00:00:00Z
owner_agent: vulcan
refresh_triggers:
  - CORE council role or voter constraint changes
  - signed Council runtime schema or member projection changes
  - Council dispatch identity or mode validation changes
  - connected connector schema digest changes
scheduled_cadence: 30d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: null
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1413 / 2026-08-02T00:00:00Z
last_lint_result: PASS
retrofit: false
trace_matrix_path: runbooks/boot-kernel-companion-crosswalk.md
word_count_delta: null
```
