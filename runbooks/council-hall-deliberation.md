---
system_name: council-hall-deliberation
purpose_sentence: Council Hall deliberation process for unbiased multi-agent assessment, synthesis, and cross-pollination across MP, AG, DeepSeek, CC, and Vulcan.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: |
  Stable mechanics, reasoning, and repair patterns for the Council Hall deliberation slice. Live config (current model frontiers, dispatch participants, review order, cost caps, retired-agent state) is canonically tracked in infra:council-comms Living State entity.

  Cross-runbook reference convention: file-qualified IDs `<file-stem>:<id>` for references outside this file, such as `agent-dispatch:F-01`. Same-file references retain bare `<id>` form.
linter_version: 1.0.0
---

# Council Hall Deliberation

## §A. Header

The YAML frontmatter above defines the §A header. This runbook documents the Council Hall deliberation pattern: independent assessment, collection/synthesis, and cross-pollination for decisions where one review pass is insufficient.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Council Hall session start | SHIPPED | `koskadeux-mcp/council_hall.py:start` | Council Hall state flow smoke coverage | 2026-04-29 |
| Independent assessment response recording | SHIPPED | `koskadeux-mcp/council_hall.py:record_response` | Response capture exercised by deliberation transcript tests | 2026-04-29 |
| Collection and synthesis status tracking | SHIPPED | `koskadeux-mcp/council_hall.py:status` | State phase checks exercised by Council Hall flow tests | 2026-04-29 |
| Cross-pollination bundle generation | SHIPPED | `koskadeux-mcp/council_hall.py:get_cross_poll_bundle` | Bundle-generation path exercised by deliberation tests | 2026-04-29 |
| Consensus summarization | PARTIAL | `koskadeux-mcp/council_hall.py:summarize` | Summary support exists; final decision quality still requires Vulcan verification | 2026-04-29 |
| Open-ended DeepSeek deliberation dispatch | SHIPPED | `koskadeux-mcp/tools/agents.py:council_request mode=open_response` | Open-response mode covers non-review-schema deliberation prompts | 2026-04-29 |
| Redis Streams deliberation transport | PLANNED | — | Not implemented; Vulcan currently coordinates dispatch and polling | 2026-04-29 |

## §C. Architecture & Interactions

Council Hall is a deliberation workflow, not a generic dispatch tool. It is used when independent reviews leave a strategic, architectural, process, or policy decision unresolved. The slice has three phases: Phase 1 independent assessment, Phase 2 collection and synthesis, and Phase 3 cross-pollination. A final decision record is produced after those phases by Vulcan, with Max escalation when no consensus emerges.

Strategic why: the three-phase pattern exists to preserve independent reasoning before consensus pressure appears. Independent assessment comes first because showing one agent another agent's answer creates anchoring and role bias. Collection/synthesis comes second because Vulcan needs a faithful comparison table before deciding whether the disagreement is real or just wording. Cross-pollination comes after synthesis because agents should respond to concrete competing claims, not to vague disagreement summaries. DeepSeek is now a full voter because S528 graduation showed 94 dispatches with `success_rate=1.0`, `verdict_agreement_with_primary=1.0`, `fabricated_line_reference_rate=0.0`, and statistical record floor crushed 4.7x; it participates in open-ended deliberation through `mode=open_response` rather than the stricter review schema.

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Hall Session | `koskadeux-mcp/council_hall.py:start` | `council:hall:{deliberation_id}` | Vulcan, MP, AG, DeepSeek, CC | Creates the topic, neutral prompt, participant list, and phase state. |
| Independent Assessment | `koskadeux-mcp/tools/agents.py:council_request` | `responses.independent.{agent}` | MP, AG, DeepSeek, CC | Sends the same neutral prompt before any agent sees another response. |
| Response Collection | `koskadeux-mcp/council_hall.py:record_response` | `responses.independent`, `responses.cross_poll` | Vulcan, Living State | Records each assessment and tracks late or missing participants. |
| Synthesis Pass | `koskadeux-mcp/council_hall.py:status` | phase, response counts, synthesis notes | Vulcan, Max | Produces agreement, disagreement, differentiator, and evidence-gap views. |
| Cross-Poll Bundle | `koskadeux-mcp/council_hall.py:get_cross_poll_bundle` | phase, bundle transcript | MP, AG, DeepSeek, CC | Builds the original prompt plus all independent assessments for Phase 3. |
| Consensus Summary | `koskadeux-mcp/council_hall.py:summarize` | consensus, dissent, decision pointer | Vulcan, Max, Living State | Classifies consensus, majority-plus-dissent, or no-consensus escalation. |
| Open Response Dispatch | `koskadeux-mcp/tools/agents.py:council_request mode=open_response` | dispatch task records | DeepSeek, AG, MP | Allows deliberation answers that do not fit a strict review verdict schema. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| MP | independent assessment and cross-poll response | Codex CLI / GPT-5.5 | repo read, optional full repo write only outside Hall review | COMPLETE |
| AG | independent assessment and cross-vote reasoning | Gemini CLI / Gemini 3.1 Pro | repo read | COMPLETE |
| DeepSeek | full-voter open-response deliberation | DeepSeek API / deepseek-v4-pro | repo read | COMPLETE |
| CC | fallback builder perspective and implementation-risk assessment | Claude Code / Opus | repo read for Hall, full repo write only after Hall decision | COMPLETE |
| Vulcan | orchestration, neutral prompt construction, synthesis, escalation | Anthropic API / MCP tools | gateway, Living State, all repos | COMPLETE |

CC coverage is `COMPLETE` for the operation named in the row: implementation-risk assessment when Hall scope needs a fallback-builder read. CC is not required for every Hall. MP, AG, and DeepSeek are the normal deliberation voters. Vulcan is not a peer voter; Vulcan preserves neutrality, collects evidence, synthesizes faithfully, and escalates unresolved policy choices to Max.

## §E. Operate

```yaml operate
- id: E-01
  trigger: A strategic or architectural decision has material disagreement after ordinary review.
  pre_conditions: [decision_question_written, evidence_refs_available, participants_selected_from_living_state, no_agent_has_seen_peer_answers]
  tool_or_endpoint: council_hall(action=start, topic=<topic>, prompt=<neutral_prompt>, agents=<participants>)
  argument_sourcing:
    topic: use the blocking decision title from the BQ, spec, or operator request
    neutral_prompt: include background, proposal, decision dimensions, and requested structured output without assigning roles
    participants: read Hall participants from infra:council-comms dispatch patterns
    evidence_refs: include specs, commits, transcripts, and Living State keys that every agent can inspect
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(topic + prompt_digest + sorted(evidence_refs))
  expected_success:
    shape: deliberation_id plus phase=independent and empty response slots
    verification: Check Living State council:hall:{deliberation_id} contains topic, prompt, agents, and session_id
  expected_failures:
    - {signature: duplicate_deliberation, cause: same topic and prompt already have an active Hall}
    - {signature: participant_config_missing, cause: infra:council-comms does not define a usable participant set}
  next_step_success: Dispatch the identical neutral prompt to each participant for independent assessment.
  next_step_failure: Repair via F-01 or fall back to ordinary independent reviews until participant config is corrected.
- id: E-02
  trigger: The Hall has started and each participant must provide a Phase 1 answer.
  pre_conditions: [deliberation_id_exists, phase_is_independent, neutral_prompt_frozen, dispatch_backends_healthy]
  tool_or_endpoint: council_request(agent=<mp|ag|deepseek|cc>, mode=open_response, task=<neutral_prompt>, cwd=<repo>)
  argument_sourcing:
    agent: use the participant list stored on the Hall session
    mode: use open_response for open-ended deliberation; do not force strict review schema for DeepSeek
    task: use the exact frozen prompt for every participant
    cwd: use the repo or evidence root named in the deliberation context
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: deliberation_id + agent + phase
  expected_success:
    shape: independent assessment with verdict, confidence, key claims, objections, and caveats
    verification: Confirm no response references another participant's answer
  expected_failures:
    - {signature: late_arriver, cause: one participant has not answered before synthesis is due}
    - {signature: open_response_schema_mismatch, cause: dispatch path used review schema for an open-ended prompt}
  next_step_success: Record each response with council_hall(action=record_response).
  next_step_failure: Isolate F-02 or F-05 and decide whether to wait, redispatch, or synthesize with quorum.
- id: E-03
  trigger: Independent assessments are collected and disagreement remains material.
  pre_conditions: [quorum_met, independent_responses_recorded, synthesis_identifies_disagreements, max_or_gate_requires_resolution]
  tool_or_endpoint: council_hall(action=get_cross_poll_bundle, deliberation_id=<id>)
  argument_sourcing:
    deliberation_id: read from the active Hall session
    disagreement_set: derive from Vulcan synthesis of independent assessments
    bundle: include original prompt, every independent assessment, and explicit agreement or disagreement questions
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: deliberation_id + cross_poll_bundle_version
  expected_success:
    shape: bundle containing all Phase 1 assessments and targeted response instructions
    verification: Confirm every participant response is represented exactly once
  expected_failures:
    - {signature: premature_cross_poll, cause: bundle built before quorum or before late-arriver decision}
    - {signature: biased_synthesis, cause: Vulcan summarized positions in a way that changes agent claims}
  next_step_success: Dispatch the cross-poll bundle to participants and then summarize the final positions.
  next_step_failure: Repair via F-03 or F-06 before any cross-poll dispatch.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | No quorum after Hall start | Participant backend unavailable, dispatch failed, participant list includes retired or unreachable agent | Compare Hall participant list, dispatch task records, and response slots in `council:hall:{deliberation_id}` | G-01 | CONFIRMED |
| F-02 | Late-arriver response after synthesis began | Vulcan moved to synthesis before timeout policy resolved, backend completed after expected window, duplicate dispatch returned late | Check timestamps on response record, synthesis note, and dispatch task id | G-02 | CONFIRMED |
| F-03 | Premature cross-pollination | Cross-poll bundle generated before independent responses reached quorum or before late-arriver decision was recorded | Inspect phase, response counts, and bundle transcript for missing independent answers | G-03 | CONFIRMED |
| F-04 | Agent-disagreement deadlock | Participants disagree on value judgment, evidence is incomplete, or no decision owner was named | Compare final positions, evidence gaps, confidence levels, and Max escalation criteria | G-04 | CONFIRMED |
| F-05 | Open-ended DeepSeek answer fails strict review parsing | DeepSeek was dispatched through review mode instead of `mode=open_response` | Inspect dispatch arguments and parser error; confirm prompt was deliberative rather than review-verdict shaped | G-05 | CONFIRMED |
| F-06 | Synthesis misrepresents an agent position | Vulcan over-editorialized, compressed a caveat away, or merged two distinct claims | Compare synthesis bullets against raw responses and require claim-level citations | G-06 | HYPOTHESIZED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Hall Session
  root_cause: The Hall cannot proceed because the configured participant set did not produce enough independent responses.
  repair_entry_point: koskadeux-mcp/council_hall.py:status
  change_pattern: Verify participant health, redispatch missing agents once, then either wait or record an explicit quorum exception with the absent participant named.
  rollback_procedure: Mark duplicate or superseded dispatch task ids as failed evidence without deleting the Hall session.
  integrity_check: Confirm the synthesis names participating agents, absent agents, and the quorum rule used.
- id: G-02
  symptom_ref: F-02
  component_ref: Response Collection
  root_cause: A response arrived after Vulcan began synthesis or after the Hall moved past independent assessment.
  repair_entry_point: koskadeux-mcp/council_hall.py:record_response
  change_pattern: Add the late response as late-arriver evidence, restart synthesis if it changes material conclusions, and preserve the original synthesis timestamp.
  rollback_procedure: If the late response belongs to a duplicate dispatch, mark it superseded and keep the first valid response.
  integrity_check: Confirm the final decision record states whether the late response was included or excluded.
- id: G-03
  symptom_ref: F-03
  component_ref: Cross-Poll Bundle
  root_cause: Cross-pollination began before independent assessment was complete enough to avoid anchoring.
  repair_entry_point: koskadeux-mcp/council_hall.py:get_cross_poll_bundle
  change_pattern: Cancel the bundle, restore phase to independent or synthesis, resolve quorum or late-arriver state, then generate a new bundle version.
  rollback_procedure: Mark any cross-poll dispatch from the premature bundle invalid and keep it out of consensus scoring.
  integrity_check: Confirm the accepted bundle includes all eligible independent assessments exactly once.
- id: G-04
  symptom_ref: F-04
  component_ref: Consensus Summary
  root_cause: The agents are blocked on a value judgment, missing evidence, or authority boundary that deliberation cannot resolve.
  repair_entry_point: koskadeux-mcp/council_hall.py:summarize
  change_pattern: Classify the result as no-consensus or majority-plus-dissent, list the unresolved predicates, and escalate the decision to Max when policy or priority is required.
  rollback_procedure: Do not retry indefinitely; preserve the dissent and close the Hall only after the escalation path is recorded.
  integrity_check: Confirm the decision record contains the majority view, dissent, evidence gap, and named owner for the final call.
- id: G-05
  symptom_ref: F-05
  component_ref: Open Response Dispatch
  root_cause: The dispatch path forced a review schema onto an open-ended deliberation prompt.
  repair_entry_point: koskadeux-mcp/tools/agents.py:council_request mode=open_response
  change_pattern: Redispatch DeepSeek with `mode=open_response`, keep the same neutral prompt, and record the parser failure as superseded evidence.
  rollback_procedure: Exclude the failed strict-schema artifact from synthesis while preserving it in the transcript for audit.
  integrity_check: Confirm the replacement DeepSeek answer is free-form, cites evidence, and can be compared with MP and AG positions.
- id: G-06
  symptom_ref: F-06
  component_ref: Synthesis Pass
  root_cause: Vulcan compressed or rewrote an agent position enough to alter the meaning.
  repair_entry_point: synthesis note attached to council:hall:{deliberation_id}
  change_pattern: Rebuild synthesis with claim-level bullets, cite each agent next to each claim, and separate agreement from Vulcan assessment.
  rollback_procedure: Mark the biased synthesis superseded and do not use it as the basis for cross-pollination.
  integrity_check: Confirm each summarized claim maps to one raw response passage or is labeled as Vulcan assessment.
```

## §H. Evolve

### §H.1 Invariants

- Independent assessment must happen before any participant sees another participant's answer.
- Cross-pollination must use a bundle that contains every eligible independent assessment exactly once.
- Vulcan synthesis must separate agent positions from Vulcan's own assessment.
- Live participant sets, model names, cost caps, and retired-agent state remain authoritative in `infra:council-comms`.

### §H.2 BREAKING predicates

- Removing the independent phase is BREAKING because it destroys the anti-anchoring property of the Hall.
- Changing Hall participants from MP, AG, and DeepSeek defaults without a Council config review is BREAKING.
- Enabling write-mode during Hall deliberation for AG or DeepSeek is BREAKING because deliberation is read-oriented.
- Reintroducing XAI as an active Hall participant is BREAKING because retired-agent state and reliability assumptions change.

### §H.3 REVIEW predicates

- Adding a new agent to Hall deliberation requires REVIEW.
- Changing model frontiers for MP, AG, DeepSeek, or CC requires REVIEW.
- Changing the quorum rule, late-arriver policy, or cross-poll trigger requires REVIEW.
- Increasing the per-dispatch cost cap for deliberation requires REVIEW when it changes who may be included by default.
- Replacing `mode=open_response` with another open-ended response contract requires REVIEW.

### §H.4 SAFE predicates

- Editing prompt examples is SAFE when the neutral-prompt invariant and required output fields remain intact.
- Adding a symptom row or repair pattern is SAFE when existing IDs and component names remain stable.
- Tightening synthesis formatting is SAFE when the decision record shape does not change.
- Increasing a timeout for the same participant set is SAFE when cost cap and quorum policy do not change.

### §H.5 Boundary definitions

#### module

The module boundary is the Council Hall deliberation slice: session state, response collection, synthesis, cross-poll bundle generation, consensus summary, and open-response dispatch use.

#### public contract

The public contract is the operator-facing Hall workflow: neutral topic and prompt, participant list, deliberation_id, phase state, response slots, cross-poll bundle, consensus classification, and escalation record.

#### runtime dependency

A runtime dependency is any agent backend, MCP gateway endpoint, Living State store, response parser, or provider token required to dispatch and record Hall responses.

#### config default

A config default is any participant set, quorum rule, model frontier, cost cap, timeout, or retired-agent flag read from `infra:council-comms`.

### §H.6 Adjudication

When two agents classify a Hall change differently, use the more restrictive class. Max resolves changes that affect membership, auth scope, money/security behavior, quorum policy, or final decision authority.

## §I. Scenario Set

C4 placeholder: the deliberation scenario set is populated in C5a.4. That chunk must add at least 5 scenarios scoped to Council Hall deliberation with at least 2 operate scenarios, 1 isolate scenario, 1 repair scenario, and 1 evolve or ambiguous-symptom scenario.

## §J. Lifecycle

C4 provisional lifecycle metadata is present to keep owner and refresh intent explicit. C5c populates final lifecycle telemetry after scenario authoring and harness execution.

```yaml lifecycle
last_refresh_session: S530
last_refresh_commit: b22d069
last_refresh_date: 2026-04-29T00:00:00Z
owner_agent: vulcan
refresh_triggers:
  - bq_completion
  - council_hall_flow_change
  - infra_council_comms_drift
  - scheduled_cadence
scheduled_cadence: 90d
last_harness_pass_rate: 0.0
last_harness_date: 2026-04-29T00:00:00Z
first_staleness_detected_at: null
```

Initial conformance status is `provisional` per Gate 1 §10 until C5c finalizes lifecycle telemetry after the Infisical cutover constraint is cleared. This status is documented in prose only because runbook-lint v1.0.0 rejects `conformance_status` inside §K YAML.

## §K. Conformance

C4 placeholder: C5c populates final conformance fields after C5a.4 scenario authoring and C5b harness execution. This chunk intentionally leaves §I as a placeholder, so one §I placeholder lint failure is expected.

```yaml conformance
linter_version: 1.0.0
last_lint_run: S530 / 2026-04-29T00:00:00Z
last_lint_result: FAIL
trace_matrix_path: null
word_count_delta: null
```

`conformance_status: provisional` is the intended C5c state under Gate 1 §10; the runbook-lint v1.0.0 §K YAML schema rejects that additional key, so it remains prose-only until BQ-RUNBOOK-LINT-FRESHNESS-FIELDS v1.1.0 accepts freshness fields.
