---
title: Gate Procedure
owner: vulcan
last_verified: '2026-07-27'
aliases: []
error_signatures:
- gate_eligibility_unknown
---

# Gate Procedure

## Overview


**Fetch trigger:** authoring, review, build dispatch, or gate recovery.

**Source constitution:** CORE v9.13, SHA-256 `a8b4fa86b5cebc2c704e72219a0adfd8d63c84efd6dce60e6f7198161782e268`, section 5.

## Capabilities

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Gate 1 design authority | SHIPPED | `build:bq-*.gate1` | Gate state readback | 2026-07-17 |
| Gate 2 bounded implementation spec | SHIPPED | `specs/BQ-*-GATE2.md` | Spec review and dispatch gate | 2026-07-17 |
| Gate 3 independent post-build audit | SHIPPED | `build:bq-*.gate3` | Commit-bound reviewer evidence | 2026-07-17 |
| Gate 4 production verification | SHIPPED | `build:bq-*.gate4` | Customer-perspective verification | 2026-07-17 |
| Council rounds and thresholds | SHIPPED | `infra:constitution` | Verdict-set validation | 2026-07-17 |
| Author dispatch tokens and leases | SHIPPED | `council_request` | Binding and expiry validation | 2026-07-17 |
| Server-selected all-corpus first-plan delivery (staged; inactive by default) | PLANNED | `koskadeux-mcp/tools/runbook_delivery.py` | `koskadeux-mcp/tests/test_runbook_first_delivery_s1413.py`, `tools/session.py:_handle_kd_session_plan`, and runbooks discovery-vector tests | 2026-08-02 |
| Backend runbook-authority write boundary (staged rollout prerequisite) | PLANNED | `ai-market-backend/app/services/runbook_compat.py` | `ai-market-backend/tests/test_runbook_authority_write_boundary_s1413.py` plus guarded state-write and atomic-write coverage | 2026-08-02 |

## Architecture & interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Gate 1 Design | `build:bq-*.gate1` | Problem, scope, verdicts, mandates | Gate 2 authoring | No implementation plan proceeds without approved design authority. |
| Gate 2 Specification | `specs/BQ-*-GATE2.md` | Chunk scope, files, ACs, risks, tests | MP build dispatch | Approval binds the implementation surface. |
| Build Dispatch | `council_request mode=build agent=mp` | Dispatch binding, builder, branch | Gate 3 Audit | Eligibility fails closed on any unknown operand. |
| Gate 3 Audit | `build:bq-*.gate3` | Commit-bound independent verdicts | Gate 4 Verification | Builder is excluded; REVISE or REJECT returns to Gate 2. |
| Gate 4 Verification | `state_request action=bq_complete` | Production and customer evidence | Completion | Nothing completes without production verification and non-builder evidence. |
| Council Rounds | `council_request` and Council Hall | Positions, debate, final verdicts | Gate records | At most three rounds; full valid panel precedes threshold evaluation. |
| Author Binding | `dispatch_id` and `dispatch_token` | Bound dispatch id and gate lease | Author mode | UUIDv7 id, signed credential, target gate, start, expiry, and extension count are explicit. |

Caller prose grants no authority in this mode. Caller-supplied `runbook_consultation`, paths, references, attestations, waivers, and `no_entry_found` text are ignored for admission and cannot block the plan, mint a server reference, prove reading, or discharge debt. The old classifier runs only after durable server-selected admission, as non-blocking telemetry, and its output is not persisted as accepted consultation. This separation is the point of the rollout: the server finds relevant material first; an agent is never asked to invent documentation evidence merely to pass a gate.

Do not enable this path until both prerequisites are true: the exact reviewed `runbook-tools` package and full-SHA catalog pin are installed, and backend A1's independent `RUNBOOK_AUTHORITY_WRITE_MODE=contain|reject` boundary is deployed and verified on every protected state/event route. The default backend mode is `contain`; `reject` is the stricter diagnostic mode. The legacy rollback is explicit: restore `KOSKADEUX_RUNBOOK_DELIVERY_MODE=legacy` and restart the gateway through the normal drained restart procedure. That rollback restores the old caller-evidence gate; it does not make caller prose trustworthy.

Enabled mode fails closed. Operators should search logs and returned errors by the exact codes `runbook_delivery_mode_invalid`, `runbook_library_unavailable`, `runbook_reference_key_unavailable`, `runbook_catalog_pin_unavailable`, `runbook_library_contract_invalid`, `runbook_search_failed`, `response_budget_exceeded`, `session_objective_budget_exceeded`, `session_wire_budget_exceeded`, and the sanitized fallback `runbook_first_delivery_failed`. Bundle fetch, confirmation, and replay are not exposed in this staged slice; never simulate any of them or treat possession of an opaque handle as confirmation.

### Normative projection — CORE §5, CCP

Source SHA: `a8b4fa86b5cebc2c704e72219a0adfd8d63c84efd6dce60e6f7198161782e268`.

> CCP is the **full-ceremony gate flow, reserved for expensive-to-reverse work** (schema, auth, money, customer data) per the Charter's risk sizing. Low-risk reversible internal work does not run the full CCP — it gets one reviewer, one round.

> **Voters:** CC, Kimi, GLM — exactly three. The two instances orchestrate and synthesize; never voters. Max is final authority, not a voter. MP builds; it never votes on its own work.

> - **Round 1 (Positions):** voters evaluate independently, full position, each sees only the spec.
> - **Round 2 (Debate):** voters see Round 1 positions; react, challenge, concede, or hold.
> - **Round 3 (Final — only if needed):** unresolved disagreement only.
> - **Synthesis:** the orchestrating instance synthesizes, flags disagreements, presents to Max. Unresolved splits go to Max.
> - **Hard limit:** 3 rounds.

> **Decision rules:** majority (2/3) for standard items, and only after all three voters return valid verdicts (3/3 valid participation); unanimous (3/3) REQUIRED for security, auth, money flows, production data, and customer data; missing, failed, malformed, or model-mismatched voters fail the gate closed — no builder substitution, no reduced quorum, no fallback voter; any voter CRITICAL veto halts and escalates to Max; mandatory dissent record; Kimi guaranteed a seat on every code review (conflicts surface to Max).

> **Max supersession.** Max supersedes the Council. When Max explicitly states that he is superseding it, his statement stands in place of the Council's approval for the matter he names, including the amendment gate in CORE's closing clause. The statement must name what is being superseded and be recorded in the Event Ledger. No agent may infer supersession.

### Normative projection — CORE §5, Build Gates

Source SHA: `a8b4fa86b5cebc2c704e72219a0adfd8d63c84efd6dce60e6f7198161782e268`.

> - **Gate 1 (Design):** architecture review. APPROVED → build. APPROVED_WITH_MANDATES → Gate 2. REJECT → redesign.
> - **Gate 2 (Spec):** verify mandates addressed. APPROVED → build unblocked. REJECT → fix spec.
> - **Build:** MP executes — the mandatory builder for both instances. Compliance gate blocks dispatch if Gate 2 not passed.
> - **Gate 3 (Audit):** post-build review by the gate voter panel (CC, Kimi, GLM; builder excluded). PASS → deploy. REVISE/REJECT → back to Gate 2, never Gate 1.
> - **Gate 4 (Production Verification):** deployed and verified working. Nothing is done until Gate 4 passes. Cross-review required (reviewer ≠ builder).

### Selection and eligibility

- Select Gate 1 when no approved design authority exists or the proposal materially changes it.
- Select Gate 2 for implementation specification/fold, or after Gate 3 returns REVISE or REJECT without a design change.
- Select Gate 3 for post-build audit and Gate 4 for deployed production verification.
- Build dispatch requires approved required design, approved Gate 2 when required, no reconciliation/claim/runbook/compliance blocker, MP as builder, and builder exclusion from its review.
- If any eligibility operand is unknown or unavailable, dispatch is ineligible.

The selection and eligibility bullets are companion synthesis of the approved kernel design, not a replacement for CORE or the kernel constraint block.

### Author token, lease, and syntax

Author mode binds a UUIDv7 `dispatch_id`, signed `dispatch_token`, `target_gate`, and `bound_dispatch_id` to the intended BQ/gate. The gate lease records `lease_started_at`, `lease_expires_at`, `extension_count`, and `extended_at`; extensions update optimistic state rather than silently renewing. Review uses `mode=review` and explicit read-only scope. Build uses `mode=build`, `agent=mp`, BQ code, branch/worktree, approved spec reference, and acceptance manifest. These mechanics cannot relax gate approval or reviewer independence.

The Capabilities author-dispatch-token-and-lease row and this machinery are companion synthesis of the shipped live gate tooling fields exposed by the koskadeux-mcp `state_request` and `council_request` author-mode parameters, not CORE-derived rules. If this description diverges from the live tool schema, the live tool schema prevails.

## Agent capabilities

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan or Mars | Select gate and orchestrate rounds | State and Council tools | Gate state and dispatch | COMPLETE |
| MP | Build approved chunks | `council_request mode=build` | Repository write | COMPLETE |
| CC, Kimi, GLM | Review and vote independently | `council_request mode=review` | Read-only | COMPLETE |
| Max | Decide genuine forks and approve constitutional changes | Human decision | Final authority | COMPLETE |

## How to operate

```yaml operate
- id: E-01
  trigger: A BQ needs design authority before implementation planning.
  pre_conditions: [problem_written, scope_known, bq_exists]
  tool_or_endpoint: state_request(action=bq_update, bq_code=<code>, gate=1, status=<status>, note=<verdict_and_mandate_refs>, session_id=<session>, gate_status_update=true, expected_version=<version>)
  argument_sourcing: {code: read from the BQ entity, status: derive from complete valid reviewer verdicts, note: preserve immutable verdict references and explicit unresolved mandates, session: active registered session, version: immediately preceding entity read}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(bq + gate1 + verdict_set_digest)
  expected_success: {shape: approved design or explicit mandates or rejection, verification: read back Gate 1 and mandate text}
  expected_failures: [{signature: unresolved_design_authority, cause: problem or scope is missing or mandates remain unresolved}]
  next_step_success: Author Gate 2 only when the approved design requires it.
  next_step_failure: Return to design evidence without dispatching build work.
- id: E-02
  trigger: Approved design needs a bounded implementation specification.
  pre_conditions: [gate1_approved, files_known, tests_known]
  tool_or_endpoint: specs/BQ-*-GATE2.md plus state_request(action=bq_update, bq_code=<code>, gate=2, status=<status>, note=<spec_review_refs>, session_id=<session>, gate_status_update=true, expected_version=<version>)
  argument_sourcing: {spec: derive chunks and acceptance from approved design, code: read from the BQ entity, status: derive from complete spec review, note: bind the committed spec and panel receipts, session: active registered session, version: immediately preceding entity read}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(bq + gate2 + spec_commit)
  expected_success: {shape: reviewed chunk spec with files risks tests and ACs, verification: compare BQ Gate 2 state with committed spec}
  expected_failures: [{signature: gate_eligibility_unknown, cause: required approval, scope, claim, or compliance evidence is missing}]
  next_step_success: Dispatch the eligible chunk to MP.
  next_step_failure: Keep dispatch blocked and repair the missing operand.
- id: E-03
  trigger: A committed chunk needs independent audit then production verification.
  pre_conditions: [commit_known, builder_recorded, gate2_approved]
  tool_or_endpoint: council_request(agent=<cc|kimi|glm>, mode=review, task=<audit_prompt>, cwd=<repo>, dispatch_sha=<sha>) once for each active voter, then state_request(action=bq_complete, bq_code=<code>, summary=<summary>, gate=4, evidence_links=<links>, session_id=<session>, verification=<production_evidence>)
  argument_sourcing: {agent: exact deployed voter projection with no substitutions, audit_prompt: bind Gate 3 to commit and approved specs, repo: repository containing the full commit SHA, code: BQ entity, summary: measured completion result, links: immutable Gate 3 and Gate 4 evidence, session: active registered session, production_evidence: customer-perspective verification}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(bq + commit + gate3_verdicts + gate4_evidence)
  expected_success: {shape: Gate 3 pass followed by Gate 4 verified completion, verification: confirm reviewer minus builder is non-empty and evidence is production-facing}
  expected_failures: [{signature: invalid_gate_promotion, cause: audit is tainted, mandates remain, or production evidence is absent}]
  next_step_success: Complete and record the BQ evidence.
  next_step_failure: Return REVISE or REJECT to Gate 2 or obtain valid Gate 4 evidence.
```

## When it breaks

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Build dispatch eligibility cannot be proven. | A gate, claim, reconciliation, runbook, compliance, builder, or independence operand is unknown. | Read the BQ, approved specs, claim state, reconciliation result, runbook refs, and dispatch envelope. | G-01 | CONFIRMED |
| F-02 | Gate 3 review changed files or used the builder. | Review mode or reviewer independence was violated. | Compare git status, dispatch mode, builder list, reviewer list, and target SHA. | G-02 | CONFIRMED |

## Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Build Dispatch
  root_cause: At least one dispatch eligibility operand is absent or contradictory.
  repair_entry_point: BQ gate state and dispatch preflight
  change_pattern: Resolve the missing evidence at its owning surface and rerun eligibility from all operands.
  rollback_procedure: Leave build dispatch blocked without bypassing an unknown gate.
  integrity_check: Every required operand is explicit and true before MP dispatch.
- id: G-02
  symptom_ref: F-02
  component_ref: Gate 3 Audit
  root_cause: A write-capable or non-independent dispatch was treated as review evidence.
  repair_entry_point: council_request mode=review
  change_pattern: Discard the tainted vote and redispatch an eligible non-builder with explicit read-only scope.
  rollback_procedure: Remove the invalid verdict from gate evidence.
  integrity_check: Replacement review changes no files and binds to the intended commit.
```

## Changes and maintenance

### H.1 Invariants

Gate selection is evidence-driven, dispatch fails closed, MP builds, builders do not review their work, and Gate 4 verifies production.

### H.2 BREAKING predicates

Removing a gate, reducing required valid participation, bypassing unanimous risk classes, or allowing unknown eligibility is BREAKING.

### H.3 REVIEW predicates

Review changes to token claims, lease fields, round transport, statuses, voter validation, or completion evidence.

### H.4 SAFE predicates

Adding examples is safe when it does not change gate meaning, thresholds, eligibility, or authority.

### H.5 Boundary definitions

#### module

Gate records, committed specs, dispatch bindings, review envelopes, and completion records.

#### public contract

Gate 1 design, Gate 2 spec, MP build, Gate 3 audit, Gate 4 verification, and accepted transitions.

#### runtime dependency

Living State, repository evidence, Council dispatch, current roster, and production verification surfaces.

#### config default

Unknown evidence fails closed; no token, lease, or roster default can manufacture approval.

### H.6 Adjudication

Apply CORE risk thresholds, approved design/spec authority, and current gate evidence; escalate only real unresolved forks to Max.

## Acceptance criteria

```yaml acceptance
scenario_set:
  - {id: I-01, type: operate, refs: [E-01], scenario: A new BQ has no approved design authority., expected_answers: [{kind: classification, label: SELECT_GATE_1}], weight: 0.0909090909}
  - {id: I-02, type: operate, refs: [E-02], scenario: Approved design requires a bounded implementation spec., expected_answers: [{kind: classification, label: SELECT_GATE_2}], weight: 0.0909090909}
  - {id: I-03, type: operate, refs: [E-03], scenario: A committed build is ready for independent audit., expected_answers: [{kind: classification, label: SELECT_GATE_3}], weight: 0.0909090909}
  - {id: I-04, type: isolate, refs: [F-01], scenario: Gate 2 status is missing before a required build dispatch., expected_answers: [{kind: classification, label: INELIGIBLE}], weight: 0.0909090909}
  - {id: I-05, type: isolate, refs: [F-02], scenario: The builder appears among its own Gate 3 reviewers., expected_answers: [{kind: classification, label: TAINTED_REVIEW}], weight: 0.0909090909}
  - {id: I-06, type: isolate, refs: [F-01], scenario: A gate lease expired before author-mode completion., expected_answers: [{kind: classification, label: LEASE_NOT_VALID}], weight: 0.0909090909}
  - {id: I-07, type: repair, refs: [G-01], scenario: A claim blocker makes build eligibility unknown., expected_answers: [{kind: human_action, verb: resolve, object: claim evidence, target: dispatch preflight}], weight: 0.0909090909}
  - {id: I-08, type: repair, refs: [G-02], scenario: A review dispatch wrote a verdict file and source changes., expected_answers: [{kind: human_action, verb: replace, object: tainted review, target: clean read-only review}], weight: 0.0909090909}
  - {id: I-09, type: evolve, refs: [Changes and maintenance], scenario: A proposal lets two of three returned votes count when one voter failed., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.0909090909}
  - {id: I-10, type: evolve, refs: [Changes and maintenance], scenario: A signed token gains an additive audit claim., expected_answers: [{kind: classification, label: REVIEW}], weight: 0.0909090909}
  - {id: I-11, type: ambiguous, refs: [H.6], scenario: Gate 3 rejects implementation without changing design authority., expected_answers: [{kind: classification, label: RETURN_TO_GATE_2}], weight: 0.090909091}
```

## Maintenance

```yaml lifecycle
last_refresh_session: S1369
last_refresh_commit: 91ebd40
last_refresh_date: 2026-07-27T21:55:39Z
owner_agent: vulcan
refresh_triggers: [CORE gate or consensus changes, author token or lease schema changes, BQ gate transition or completion changes]
scheduled_cadence: 30d
first_staleness_detected_at: null
```
