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

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01, §D, council:I-12]
    scenario: |
      id: E-01. trigger: A BQ architecture choice has conflicting ordinary review advice and needs unbiased Hall deliberation. pre_conditions: neutral decision question, evidence refs, branch, BQ entity, and infra:council-comms Hall participant defaults are available; no participant has seen peer answers. tool_or_endpoint: council_hall(action=start, topic=<topic>, prompt=<neutral_prompt>, agents=[mp, ag, deepseek]). argument_sourcing: topic from the blocking decision; neutral_prompt from shared evidence and decision dimensions; agents from Hall defaults. idempotency: IDEMPOTENT_WITH_KEY on topic + prompt_digest + sorted(evidence_refs). expected_success: deliberation_id with phase=independent and empty mp/ag/deepseek response slots. expected_failures: duplicate_deliberation, participant_config_missing, or biased prompt. next_step_success: dispatch the identical neutral prompt to each participant. next_step_failure: repair participant or prompt state before any answer is collected.
    expected_answers:
      - kind: tool_call
        tool: council_hall
        argument_keys: [action, topic, prompt, agents]
        argument_values:
          action: start
          agents: [mp, ag, deepseek]
    weight: 0.06666666666666667
  - id: I-02
    type: operate
    refs: [E-02, §D]
    scenario: |
      id: E-02. trigger: MP returns the first independent assessment for an active Hall. pre_conditions: deliberation_id exists, phase=independent, MP was dispatched with the frozen neutral prompt, and the answer includes verdict, confidence, claims, objections, and caveats. tool_or_endpoint: council_hall(action=record_response, deliberation_id=<id>, agent=mp, phase=independent, response=<structured_answer>). argument_sourcing: deliberation_id from Hall start; agent from response owner; key_claims, objections, verdict, confidence, and caveats from the raw answer. idempotency: IDEMPOTENT_WITH_KEY on deliberation_id + agent + phase. expected_success: MP slot is populated without advancing to cross-poll and without exposing the answer to AG or DeepSeek. expected_failures: duplicate response, missing required fields, or answer references another participant. next_step_success: continue collecting AG and DeepSeek independent responses. next_step_failure: isolate parser or phase issues before synthesis.
    expected_answers:
      - kind: tool_call
        tool: council_hall
        argument_keys: [action, deliberation_id, agent, phase, response]
        argument_values:
          action: record_response
          agent: mp
          phase: independent
    weight: 0.06666666666666667
  - id: I-03
    type: operate
    refs: [E-03, F-03, G-03]
    scenario: |
      id: E-03. trigger: MP, AG, and DeepSeek have all recorded independent assessments and material disagreement remains. pre_conditions: quorum is met, independent responses are recorded exactly once, synthesis has identified disagreement questions, and no cross-poll bundle exists yet. tool_or_endpoint: council_hall(action=get_cross_poll_bundle, deliberation_id=<id>, phase=cross_poll). argument_sourcing: deliberation_id from Hall session; phase from current state; disagreement_set from synthesis notes; included assessments from response slots. idempotency: IDEMPOTENT_WITH_KEY on deliberation_id + cross_poll_bundle_version. expected_success: bundle contains original prompt, all three independent assessments, and targeted instructions for cross-poll response. expected_failures: premature_cross_poll, missing eligible response, or biased synthesis. next_step_success: dispatch the bundle to participants for Phase 3. next_step_failure: apply G-03 and regenerate the bundle only after phase state is repaired.
    expected_answers:
      - kind: tool_call
        tool: council_hall
        argument_keys: [action, deliberation_id, phase]
        argument_values:
          action: get_cross_poll_bundle
          phase: cross_poll
    weight: 0.06666666666666667
  - id: I-04
    type: operate
    refs: [E-03, G-04, G-06]
    scenario: |
      id: E-04. trigger: Cross-poll responses have been recorded and Vulcan needs a final synthesis for the decision record. pre_conditions: independent and cross-poll response sets are available, synthesis notes preserve claim-level attribution, and unresolved evidence gaps are named. tool_or_endpoint: council_hall(action=summarize, deliberation_id=<id>). argument_sourcing: consensus candidates from cross-poll answers; dissent from remaining objections; evidence gaps from raw responses; escalation owner from policy boundary. idempotency: IDEMPOTENT_WITH_KEY on deliberation_id + final_response_set_hash. expected_success: summary classifies consensus, majority-plus-dissent, or no-consensus and names the next action. expected_failures: synthesis misrepresents a claim, hides dissent, or treats a policy choice as agent-resolvable. next_step_success: attach the final decision or escalation record to the BQ. next_step_failure: repair with G-04 or G-06 before closing the Hall.
    expected_answers:
      - kind: tool_call
        tool: council_hall
        argument_keys: [action, deliberation_id]
        argument_values:
          action: summarize
    weight: 0.06666666666666667
  - id: I-05
    type: isolate
    refs: [F-04, G-04, council:I-12]
    scenario: |
      id: F-04. trigger: Final Hall positions are split 2-1, with MP and DeepSeek accepting the architecture while AG rejects it on maintainability risk. pre_conditions: all independent and cross-poll responses are recorded, each verdict has confidence and objections, and Vulcan synthesis shows a real value judgment rather than missing evidence. tool_or_endpoint: council_hall(action=summarize, deliberation_id=<id>). argument_sourcing: majority view from MP/DeepSeek; dissent from AG; unresolved predicates from synthesis; owner from escalation policy. idempotency: READ_ONLY_DIAGNOSTIC until a final decision owner acts. expected_success: classify as agent-disagreement deadlock or majority-plus-dissent, preserve AG dissent, and escalate to Max if the value judgment blocks the BQ. expected_failures: calling it full concurrence, dropping dissent, or rerunning agents indefinitely. next_step_success: use G-04 to record majority, dissent, evidence gap, and decision owner. next_step_failure: keep the Hall open with no promotion.
    expected_answers:
      - kind: human_action
        verb: classify
        object: 2-1 Hall verdict divergence
        target: F-04 then G-04
    weight: 0.06666666666666667
  - id: I-06
    type: isolate
    refs: [F-02, G-02]
    scenario: |
      id: F-02. trigger: AG returns an independent answer after Vulcan has already begun synthesis from MP and DeepSeek. pre_conditions: AG dispatch task, synthesis timestamp, response timestamp, and current Hall phase are available. tool_or_endpoint: council_hall(action=record_response, deliberation_id=<id>, agent=ag, phase=independent, response=<late_answer>). argument_sourcing: agent and response from AG task; phase from Hall state; timestamps from dispatch and synthesis records. idempotency: IDEMPOTENT_WITH_KEY on deliberation_id + agent + phase + dispatch_task_id. expected_success: classify as late_arriver phase desync and record whether the late answer is included, excluded, or triggers synthesis restart. expected_failures: silently overwriting synthesis or pretending the response arrived on time. next_step_success: apply G-02 and preserve both original synthesis and late-arriver handling. next_step_failure: escalate only if inclusion materially changes the decision and no owner is defined.
    expected_answers:
      - kind: human_action
        verb: classify
        object: late-arriver phase desync
        target: F-02 then G-02
    weight: 0.06666666666666667
  - id: I-07
    type: isolate
    refs: [F-01, G-01, agent-dispatch:F-01]
    scenario: |
      id: F-01. trigger: A Hall remains stuck in phase=independent because DeepSeek has no recorded response while MP and AG have answered. pre_conditions: participant list, response slots, dispatch task ids, timeout policy, and backend health are available. tool_or_endpoint: council_hall(action=status, deliberation_id=<id>). argument_sourcing: response counts from Hall state; missing agent from empty slots; dispatch state from council_request records; timeout from infra:council-comms. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify as no quorum or missing participant response, not a deliberation disagreement. expected_failures: generating cross-poll early or diagnosing a policy deadlock before quorum. next_step_success: use G-01 to verify health, redispatch once, or record a quorum exception. next_step_failure: keep independent phase blocked until the absent participant decision is explicit.
    expected_answers:
      - kind: human_action
        verb: inspect
        object: independent phase response slots
        target: F-01 then G-01
    weight: 0.06666666666666667
  - id: I-08
    type: isolate
    refs: [F-03, G-03]
    scenario: |
      id: F-03. trigger: get_cross_poll_bundle returns an empty bundle for a Hall that was just started. pre_conditions: deliberation_id exists, phase is independent, and no agent response slots are populated. tool_or_endpoint: council_hall(action=get_cross_poll_bundle, deliberation_id=<id>). argument_sourcing: phase and response slots from Hall state; bundle transcript from the attempted call. idempotency: READ_ONLY_DIAGNOSTIC for diagnosis; do not dispatch the empty bundle. expected_success: classify as premature cross-pollination caused by no recorded independent responses. expected_failures: treating the empty bundle as valid or filling it manually from memory. next_step_success: cancel the bundle, restore independent phase, and collect responses through E-02. next_step_failure: invalidate any cross-poll dispatch that used the empty bundle.
    expected_answers:
      - kind: human_action
        verb: reject
        object: empty cross-poll bundle
        target: F-03 then G-03
    weight: 0.06666666666666667
  - id: I-09
    type: repair
    refs: [G-01, F-01, agent-dispatch:F-01]
    scenario: |
      id: G-01. trigger: DeepSeek is the only missing Hall participant after the independent-response timeout. pre_conditions: original neutral prompt, evidence refs, missing dispatch task id, and changed-file diff are available. tool_or_endpoint: council_request(agent=deepseek, mode=open_response, task=<diff_only_retry_prompt>, context_refs=<changed_files>). argument_sourcing: changed_files from git diff --name-only or the BQ evidence list; retry prompt from the original neutral prompt plus "answer only for these diffs"; dispatch cap from infra:council-comms. idempotency: IDEMPOTENT_WITH_KEY on deliberation_id + agent + retry_prompt_digest. expected_success: missing reviewer returns a bounded independent assessment suitable for record_response. expected_failures: retry prompt exposes peer answers, uses strict review schema, or expands beyond the diff-only scope. next_step_success: record_response for DeepSeek and resume synthesis. next_step_failure: record a named quorum exception and proceed only if policy allows.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, context_refs]
        argument_values:
          agent: deepseek
          mode: open_response
    weight: 0.06666666666666667
  - id: I-10
    type: repair
    refs: [G-02, F-02]
    scenario: |
      id: G-02. trigger: A late AG independent response should be included because it raises a material evidence gap before cross-poll dispatch. pre_conditions: late response, prior synthesis note, current phase, and dispatch timestamps are preserved. tool_or_endpoint: council_hall(action=record_response, deliberation_id=<id>, agent=ag, phase=independent, response=<late_answer>, transition=synthesis_restart). argument_sourcing: response from AG transcript; transition reason from Vulcan materiality check; timestamps from Hall state. idempotency: IDEMPOTENT_WITH_KEY on deliberation_id + agent + phase + dispatch_task_id. expected_success: the late response is added as late-arriver evidence and phase is manually returned to synthesis before a new cross-poll bundle is generated. expected_failures: overwriting the prior synthesis without trace or advancing directly to cross-poll. next_step_success: rebuild synthesis with the AG claim included and preserve the original synthesis timestamp. next_step_failure: exclude duplicate late evidence and document why.
    expected_answers:
      - kind: tool_call
        tool: council_hall
        argument_keys: [action, deliberation_id, agent, phase, response]
        argument_values:
          action: record_response
          agent: ag
          phase: independent
    weight: 0.06666666666666667
  - id: I-11
    type: repair
    refs: [G-04, F-01, council-gate-process:F-04]
    scenario: |
      id: G-04. trigger: MP and DeepSeek responded, AG is absent, and the gate owner asks for an explicit partial-response summary instead of waiting another cycle. pre_conditions: quorum exception is allowed, absent agent is named, MP and DeepSeek raw responses are available, and the BQ risk of delay is recorded. tool_or_endpoint: council_hall(action=summarize, deliberation_id=<id>, include_partial=true). argument_sourcing: participating agents from response slots; absent agent from Hall participant list; quorum exception from operator or gate owner; risk note from BQ state. idempotency: IDEMPOTENT_WITH_KEY on deliberation_id + partial_response_set_hash. expected_success: summary names the partial response set, absent AG, confidence reduction, dissent status, and whether council-gate-process repair is needed. expected_failures: presenting partial concurrence as full Hall consensus or hiding the missing reviewer. next_step_success: attach partial summary to the gate record and route any gate-blocking issue through council-gate-process:F-04. next_step_failure: keep the Hall open and redispatch the missing reviewer.
    expected_answers:
      - kind: tool_call
        tool: council_hall
        argument_keys: [action, deliberation_id, include_partial]
        argument_values:
          action: summarize
          include_partial: true
    weight: 0.06666666666666667
  - id: I-12
    type: evolve
    refs: [§H, §H.2, §H.3]
    scenario: |
      id: H-01. trigger: A proposal changes the normal Hall pattern from three voters to four by adding CC as a default voter, not just a fallback perspective. pre_conditions: proposed participant list, quorum math, cost cap, auth scope, and infra:council-comms patch are available. tool_or_endpoint: infra:council-comms participant-set patch plus runbook update. argument_sourcing: current defaults from Living State; new role from proposal; quorum and escalation effects from §H invariants. idempotency: CHANGE_REVIEW_REQUIRED. expected_success: classify as BREAKING because the default deliberation participant set and consensus math change. expected_failures: calling it SAFE because CC already appears in the capability map. next_step_success: open a Council config change review before using the four-voter pattern. next_step_failure: continue using MP, AG, and DeepSeek defaults.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.06666666666666667
  - id: I-13
    type: evolve
    refs: [§H, §H.3]
    scenario: |
      id: H-02. trigger: A proposal changes Hall verdict values from free-form approve/reject style labels to approve, reject, and conditional. pre_conditions: current response contract, parser behavior, summarize logic, and gate concurrence expectations are known. tool_or_endpoint: council_hall response contract update plus runbook update. argument_sourcing: current output fields from E-02; summary classifications from E-04; gate expectations from council-gate-process. idempotency: CHANGE_REVIEW_REQUIRED. expected_success: classify as REVIEW because the response contract changes while preserving the three-phase Hall invariant. expected_failures: treating the enum change as prompt wording only or deploying it without summary/gate interpretation. next_step_success: review parser, summary, and gate mapping before accepting conditional as a new value. next_step_failure: keep the prior verdict contract.
    expected_answers:
      - kind: classification
        label: REVIEW
    weight: 0.06666666666666667
  - id: I-14
    type: evolve
    refs: [§H, §H.3, E-03]
    scenario: |
      id: H-03. trigger: A proposal changes the cross-poll bundle from one prompt plus all independent assessments to per-agent customized bundles that omit each agent's original answer. pre_conditions: proposed bundle schema, anchoring analysis, transcript storage, and compatibility with get_cross_poll_bundle are available. tool_or_endpoint: council_hall(action=get_cross_poll_bundle) schema change. argument_sourcing: current bundle contract from E-03; proposed fields from design patch; integrity requirements from §H invariants. idempotency: CHANGE_REVIEW_REQUIRED. expected_success: classify as REVIEW because the public cross-poll contract changes and must prove it still preserves eligible assessments exactly once. expected_failures: calling it SAFE formatting or losing auditability of what each agent saw. next_step_success: require schema review and transcript tests before rollout. next_step_failure: keep the existing bundle structure.
    expected_answers:
      - kind: classification
        label: REVIEW
    weight: 0.06666666666666667
  - id: I-15
    type: ambiguous
    refs: [F-04, G-04, council-gate-process:F-04, council:I-12]
    scenario: |
      id: AMB-01. trigger: AG returns verdict=conditional while MP and DeepSeek return approve, and the operator asks whether the Hall has concurrence. pre_conditions: AG condition text, MP and DeepSeek approvals, gate status, and cross-poll responses are available. tool_or_endpoint: council_hall(action=summarize, deliberation_id=<id>) followed by council-gate-process repair if the condition blocks gate promotion. argument_sourcing: conditional predicate from AG response; concurrence requirement from gate process; dissent and evidence gaps from Hall synthesis. idempotency: READ_ONLY_DIAGNOSTIC until gate repair is selected. expected_success: classify as ambiguous Hall concurrence, not automatic approval; summarize as majority-plus-condition or no-consensus depending on whether the condition is satisfied, then redirect gate-blocking repair to council-gate-process:F-04. expected_failures: counting conditional as unconditional concurrence, or changing the Hall verdict enum ad hoc. next_step_success: either prove the condition satisfied and record it, or route through the cross-review gate repair pattern. next_step_failure: escalate to Max when the condition is a policy judgment.
    expected_answers:
      - kind: human_action
        verb: classify
        object: conditional Hall verdict
        target: ambiguous concurrence then council-gate-process:F-04 repair
    weight: 0.06666666666666667
```

## §J. Lifecycle

Lifecycle metadata records the final Gate 2 conformance refresh state. Harness scoring remains pending on compact-form §I loader support tracked by `BQ-RUNBOOK-HARNESS-COMPACT-IO`.

```yaml lifecycle
last_refresh_session: S530
last_refresh_commit: 8929cbf
last_refresh_date: 2026-04-29T00:00:00Z
owner_agent: vulcan
refresh_triggers:
  - Council hall phase flow or synthesis policy changes
  - independent assessment, cross-pollination, or dissent handling changes
  - participating agent capability or availability changes
  - runbook-lint or runbook-harness schema changes
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-04-29T00:00:00Z
first_staleness_detected_at: null
```

Initial conformance status is `provisional` per Gate 1 §10 until C5c finalizes lifecycle telemetry after the Infisical cutover constraint is cleared. This status is documented in prose only because runbook-lint v1.0.0 rejects `conformance_status` inside §K YAML.

## §K. Conformance

Final AC12 conformance fields for Gate 2 Chunk C5c.

```yaml conformance
linter_version: 1.0.0
last_lint_run: S530 / 2026-04-29T21:30:45Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```

`conformance_status: provisional` is the intended C5c state under Gate 1 §10; the runbook-lint v1.0.0 §K YAML schema rejects that additional key, so it remains prose-only until BQ-RUNBOOK-LINT-FRESHNESS-FIELDS v1.1.0 accepts freshness fields.


## §M — S533 Operational Updates

### M.1 — DeepSeek review-mode bypass (S533 R3)

`deepseek_server.py:run_deepseek_task` branches on `mode == "review"` BEFORE instantiating `DeepSeekNativeAgenticLoop`. Review tasks route through `DeepSeekClient.run_council_review()` which:

1. Forces `response_format={"type": "json_object"}` API-side
2. Constrains the verdict enum (`APPROVE | APPROVE_WITH_NITS | APPROVE_WITH_MANDATES | REVISE | REQUEST_CHANGES | REJECT`) and finding-object schema in the prompt
3. Returns a complete envelope shape that `tools/agents.py:_normalize_deepseek_review_response` fast-paths

Rationale: `response_format=json_object` is mutually exclusive with `tools`/`tool_choice="auto"` on the DeepSeek API. The agentic loop uses tools, so it cannot also force structured JSON output. Bypass restores deterministic JSON envelopes for review-mode calls.

The agentic loop remains unchanged for `build` and `author` modes. DS has no tool/file access in review-mode bypass — inline the spec content into the task body.

### M.2 — XAI retired from active Council (S528)

XAI is no longer an active Council voter. The frontier-only policy retired XAI in S528 per Max directive. `xai_client.py` and `grok_cli_bridge.py` are preserved in repo for reactivation. Reactivation runbook is at `infra:council-comms.retired_agents.xai`. Active voters: MP (mandatory), AG (cross-vote), DeepSeek (guaranteed +1).

### M.3 — AG progress-guard ≤4-file workaround for review-mode

`antigravity_cli_bridge.py` enforces a "15-turn no-file-changes" progress guard intended for build-mode dispatches. In review-mode this guard kills AG before it can return its envelope when the task asks AG to read many files. Pattern observed in S533: a review task with 8 file reads + analysis hit 15 turns before envelope return.

Workaround until `BQ-COUNCIL-AG-PROGRESS-GUARD-FIX` Gate 3 closes: cap AG review-mode tasks at **≤4 file reads** total. Phrase the task with explicit "STRICT BUDGET: ≤N file reads then return JSON envelope" and "Do not read additional files." This keeps AG well under the 15-turn limit.

If a review genuinely needs broader code survey, do the survey work Vulcan-direct via `shell_request`, then dispatch AG with the findings inlined for verdict-only judgment.

### M.4 — Restart procedure matrix

Which process to restart when code changes land on disk:

| Code change in | Restart |
|---|---|
| `deepseek_client.py` (review-mode envelope, prompt, response_format) | `deepseek_server.py` (port 8768) AND `koskadeux_server.py` (port 8765) — both import in-process |
| `deepseek_server.py` (agentic loop, review-mode bypass logic) | `deepseek_server.py` (port 8768) only |
| `antigravity_client.py` / `ag_server.py` | `ag_server.py` (port 8766) only — separate process |
| `tools/agents.py` (council_request handlers) | `koskadeux_server.py` (port 8765) — MCP gateway |

`launchd` plists exist for `ag_server`, `deepseek_server`, and `koskadeux_server`/`gateway_server`. Auto-restart is enabled with KeepAlive=true. ThrottleInterval backoff applies — if a process is killed within 10s of a previous restart, `launchctl kickstart -k gui/$(id -u)/com.koskadeux.<service>` clears throttle, or `launchctl bootout && bootstrap` for a clean reload. The MCP gateway (`koskadeux_server.py`) restart breaks any active Claude.ai connector session and requires manual reconnect.

### M.5 — DeepSeek model tiers (S533 verified empirically)

DeepSeek currently exposes exactly two models per `/v1/models`:
- `deepseek-v4-pro` — top tier (used for all Council reviews today)
- `deepseek-v4-flash` — cheaper tier

`deepseek-v4-pro-max` does NOT exist at the provider. S533 direct probe of the chat completions endpoint with `model="deepseek-v4-pro-max"` returns HTTP 400: *"The supported API model names are deepseek-v4-pro or deepseek-v4-flash, but you passed deepseek-v4-pro-max."* Probes against `deepseek-r1`, `deepseek-r1-pro`, `deepseek-v3`, `deepseek-v4`, `deepseek-v4-max` all return 400 invalid. `deepseek-reasoner` and `deepseek-coder` are accepted aliases but resolve to `deepseek-v4-flash` (the cheaper tier).

So `deepseek-v4-pro` IS the canonical code-review tier today. There is no higher tier to upgrade to.

**Mandate: when DeepSeek announces a new tier higher than `deepseek-v4-pro`, this section, the user memory note about Council models, and the in-code whitelist `DEEPSEEK_ALLOWED_MODELS = frozenset({"deepseek-v4-pro", "deepseek-v4-flash"})` at `koskadeux-mcp/deepseek_client.py:34` (plus the `DEEPSEEK_PRICING` table directly below it) MUST all be updated together in the same commit.** Add a line to this section linking to the new model's pricing source and a sample chat probe confirming the model name resolves at the API.
