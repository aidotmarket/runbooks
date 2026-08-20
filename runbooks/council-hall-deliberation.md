---
runbook_id: council-hall-deliberation
domain: council-operations
status: ACTIVE
authoritative_for:
  - topic: council-hall-deliberation
    section: §C. Architecture & Interactions
aliases: []
error_signatures:
  - signature: duplicate_deliberation
    section: §E. Operate
  - signature: participant_config_missing
    section: §E. Operate
  - signature: late_arriver
    section: §E. Operate
  - signature: open_response_schema_mismatch
    section: §E. Operate
  - signature: premature_cross_poll
    section: §E. Operate
  - signature: biased_synthesis
    section: §E. Operate
supersedes: []
superseded_by: []
owner: vulcan
last_verified_at: 2026-08-20
system_name: council-hall-deliberation
purpose_sentence: Council Hall deliberation process for unbiased multi-agent assessment, synthesis, and cross-pollination across the participant set explicitly bound when each Hall starts.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: |
  Stable mechanics, reasoning, and repair patterns for the Council Hall deliberation slice. Deployed council_hall VALID_AGENTS and DEFAULT_AGENTS govern participant validation/defaulting. Current model frontiers, gate review order, cost caps, and retired-agent policy are tracked in infra:council-comms; that entity does not currently expose a canonical Hall participant-selection field.

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
| Consensus summarization | PARTIAL | `koskadeux-mcp/council_hall.py:summarize` | Summary support exists; final decision quality still requires orchestrating-peer/operator verification | 2026-04-29 |
| Open-ended Hall-participant deliberation dispatch | SHIPPED | `koskadeux-mcp/tools/agents.py:council_request mode=open_response` | Open-response mode covers non-review-schema deliberation prompts | 2026-04-29 |
| Redis Streams deliberation transport | PLANNED | — | Not implemented; the orchestrating peer/operator currently coordinates dispatch and polling | 2026-04-29 |

## §C. Architecture & Interactions

Council Hall is a deliberation workflow, not a generic dispatch tool. It is used when independent reviews leave a strategic, architectural, process, or policy decision unresolved. The slice has three phases: Phase 1 independent assessment, Phase 2 collection and synthesis, and Phase 3 cross-pollination. Cross-pollination may iterate up to a HARD CAP of 4 rounds (Max-S726 directive). The orchestrating peer/operator produces a final decision record after those phases; if consensus has not emerged after 4 cross-poll rounds, the orchestrator STOPS and escalates the decision to Max rather than looping further.

Strategic why: the three-phase pattern exists to preserve independent reasoning before consensus pressure appears. Independent assessment comes first because showing one agent another agent's answer creates anchoring and role bias. Collection/synthesis comes second because the orchestrating peer/operator needs a faithful comparison table before deciding whether the disagreement is real or just wording. Cross-pollination comes after synthesis because agents should respond to concrete competing claims, not to vague disagreement summaries.

The `agents` argument on `council_hall(action=start, ...)` selects Hall participants and the deployed Hall code validates it against `VALID_AGENTS`. If `agents` is omitted, the deployed `DEFAULT_AGENTS` applies. The live tool schema currently accepts `mp`, `ag`, `glm`, `deepseek`, and `cc`; backend support is not the same as current policy authorization. The last code-bound record in `infra:council-comms` (S1153, commit `c49fa6c9`) reports `VALID_AGENTS={mp,ag,glm,deepseek,cc}` and `DEFAULT_AGENTS=[mp,ag,glm]`. Verify the deployed code or start receipt before relying on those defaults after a Hall configuration change. Do not invent a participant list from an absent Living State field.

For the rest of a Hall, use the participant set bound by the successful start call. Read it from the returned/status state when that surface exposes it; otherwise retain the exact explicit input or verified deployed default with the deliberation record. Never reconstruct membership from examples, old session notes, or gate-voter constants.

S1321 supersedes the S528-era roster snapshot. For gate voting, `REQUIRED_MEMBERS` and `VALID_MEMBER_IDS` are both exactly `{cc, kimi, glm}`: DeepSeek is retired from valid gate voting, AG is paused, and MP is the builder rather than a voter. Those gate facts constrain gate review; they do not independently define a Hall's participant list.

<!-- catalog:historical -->
Historical roster snapshots only: S528 described DeepSeek as a graduated full voter, and S726 described an MP/AG/DeepSeek/CC four-voter default. Both snapshots are superseded by S1321 and must not be used to select live Hall participants.
<!-- /catalog:historical -->

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Hall Session | `koskadeux-mcp/council_hall.py:start` | Hall state keyed by returned `deliberation_id` | Living State, orchestrator, selected participant backends | Validates the explicit `agents` input or applies the deployed default, then creates the topic and phase state. |
| Independent Assessment | `koskadeux-mcp/tools/agents.py:council_request` | Hall response state | Participant set bound at Hall start | Sends the same neutral prompt before any participant sees another response. |
| Response Collection | `koskadeux-mcp/council_hall.py:record_response` | `responses.independent`, `responses.cross_poll` | Orchestrating peer/operator, Living State | Records each assessment and tracks late or missing participants. |
| Synthesis Pass | `koskadeux-mcp/council_hall.py:status` | phase, response counts, synthesis notes | Orchestrating peer/operator, Max | Produces agreement, disagreement, differentiator, and evidence-gap views. |
| Cross-Poll Bundle | `koskadeux-mcp/council_hall.py:get_cross_poll_bundle` | phase, bundle transcript | Participant set bound at Hall start | Builds the original prompt plus all independent assessments for Phase 3. |
| Consensus Summary | `koskadeux-mcp/council_hall.py:summarize` | consensus, dissent, decision pointer | Orchestrating peer/operator, Max, Living State | Classifies consensus, majority-plus-dissent, or no-consensus escalation. |
| Open Response Dispatch | `koskadeux-mcp/tools/agents.py:council_request mode=open_response` | dispatch task records | Start-bound participant backends | Allows deliberation answers that do not fit a strict review verdict schema. |

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Start-bound participant | Independent assessment and cross-poll response when selected by explicit `agents` or the verified deployed default | Backend selected through `council_request` | Read-oriented Hall evidence scope | COMPLETE |
| Hall orchestrator | Neutral prompt construction, participant binding, synthesis, escalation | MCP tools and Living State | Gateway, Living State, evidence repositories | COMPLETE |
| Current gate-voter panel | Gate review outside Hall deliberation for the S1321 `{cc, kimi, glm}` panel | Current voter backend from `infra:council-comms` | Read-only gate evidence scope | COMPLETE |
| MP | Mandatory builder; not a gate voter | Builder backend from `infra:council-comms` | Repository write only through authorized build flow | COMPLETE |
| AG | Paused; no current gate-voting authority | Paused backend metadata in `infra:council-comms` | None for current gates | COMPLETE |
| DeepSeek | Retired from valid gate voting | Retained historical backend metadata | None for current gates | COMPLETE |

The capability map reports role boundaries; it is not a participant-selection source. At Hall start, pass an explicit policy-authorized `agents` list or deliberately accept the verified deployed default. After start, use only that bound set.

## §E. Operate

> **S1582 SUPERSESSION NOTICE.** Every `council_hall(...)` tool_or_endpoint in this
> section refers to a service that **no longer exists in the deployed tree**: the
> `council_hall/` package, its plist, and its orchestrator were deliberately deleted
> in `koskadeux-mcp` commit `d393224d95` ("refactor: make council review file-only",
> 2026-08-12). The three-phase deliberation **protocol** below (frozen neutral prompt,
> independent Phase 1, cross-poll only the disagreements, synthesis) remains the
> governing procedure; the *automation* is retired. Execute it manually per §N.
> The `council_request(mode=open_response)` dispatch shape in E-02 is still literally
> correct; the `council_hall(action=start|record_response|get_cross_poll_bundle)` steps
> are procedure descriptions only — perform their intent by hand as mapped in §N.

```yaml operate
- id: E-01
  trigger: A strategic or architectural decision has material disagreement after ordinary review.
  pre_conditions: [decision_question_written, evidence_refs_available, explicit_participants_or_verified_deployed_default, no_agent_has_seen_peer_answers]
  tool_or_endpoint: council_hall(action=start, topic=<topic>, prompt=<neutral_prompt>, agents=<participants>)
  argument_sourcing:
    topic: use the blocking decision title from the BQ, spec, or operator request
    neutral_prompt: include background, proposal, decision dimensions, and requested structured output without assigning roles
    participants: pass an explicit policy-authorized list accepted by the live tool schema, or omit only when deliberately accepting the verified deployed DEFAULT_AGENTS
    evidence_refs: include specs, commits, transcripts, and Living State keys that every agent can inspect
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: hash(topic + prompt_digest + sorted(evidence_refs))
  expected_success:
    shape: deliberation_id plus phase=independent and empty response slots
    verification: Confirm the returned deliberation id and independent phase; if status exposes participants, compare them with the explicit input or verified deployed default before dispatch
  expected_failures:
    - {signature: duplicate_deliberation, cause: same topic and prompt already have an active Hall}
    - {signature: participant_config_missing, cause: explicit agents are invalid or the deployed DEFAULT_AGENTS cannot be verified}
  next_step_success: Dispatch the identical neutral prompt to each participant for independent assessment.
  next_step_failure: Repair via F-01 or fall back to ordinary independent reviews until participant config is corrected.
- id: E-02
  trigger: The Hall has started and each participant must provide a Phase 1 answer.
  pre_conditions: [deliberation_id_exists, phase_is_independent, neutral_prompt_frozen, dispatch_backends_healthy]
  tool_or_endpoint: council_request(agent=<start_bound_participant_id>, mode=open_response, task=<neutral_prompt>, cwd=<repo>)
  argument_sourcing:
    agent: use the participant set bound by the successful start call and verified from its input, receipt, or status evidence
    mode: use open_response for open-ended deliberation; do not force a strict review schema onto a Hall response
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
  next_step_success: Record each response with council_hall(action=record_response, deliberation_id=<id>, agent=<id>, phase=independent, verdict=<approve|reject|conditional>, confidence=<high|medium|low>, key_claims=<list>, objections=<list>, content=<raw_answer>).
  next_step_failure: Isolate F-02 or F-05 and decide whether to wait, redispatch, or synthesize with quorum.
- id: E-03
  trigger: Independent assessments are collected and disagreement remains material.
  pre_conditions: [quorum_met, independent_responses_recorded, synthesis_identifies_disagreements, max_or_gate_requires_resolution]
  tool_or_endpoint: council_hall(action=get_cross_poll_bundle, deliberation_id=<id>)
  argument_sourcing:
    deliberation_id: read from the active Hall session
    disagreement_set: derive from the orchestrating peer/operator's synthesis of independent assessments
    bundle: include original prompt, every independent assessment, and explicit agreement or disagreement questions
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: deliberation_id + cross_poll_bundle_version
  expected_success:
    shape: bundle containing all Phase 1 assessments and targeted response instructions
    verification: Confirm every participant response is represented exactly once
  expected_failures:
    - {signature: premature_cross_poll, cause: bundle built before quorum or before late-arriver decision}
    - {signature: biased_synthesis, cause: the orchestrating peer/operator summarized positions in a way that changes agent claims}
  next_step_success: Dispatch the cross-poll bundle to participants and then summarize the final positions.
  next_step_failure: Repair via F-03 or F-06 before any cross-poll dispatch.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | No quorum after Hall start | Participant backend unavailable, dispatch failed, participant set includes retired or unreachable agent | Compare the explicit input or verified default with Hall status and dispatch records; do not assume an undocumented state-key shape | G-01 | CONFIRMED |
| F-02 | Late-arriver response after synthesis began | The orchestrating peer/operator moved to synthesis before timeout policy resolved, backend completed after expected window, duplicate dispatch returned late | Check timestamps on response record, synthesis note, and dispatch task id | G-02 | CONFIRMED |
| F-03 | Premature cross-pollination | Cross-poll bundle generated before independent responses reached quorum or before late-arriver decision was recorded | Inspect phase, response counts, and bundle transcript for missing independent answers | G-03 | CONFIRMED |
| F-04 | Agent-disagreement deadlock | Participants disagree on value judgment, evidence is incomplete, or no decision owner was named | Compare final positions, evidence gaps, confidence levels, and Max escalation criteria | G-04 | CONFIRMED |
| F-05 | Open-ended Hall answer fails strict review parsing | A participant was dispatched through review mode instead of `mode=open_response` | Inspect dispatch arguments and parser error; confirm prompt was deliberative rather than review-verdict shaped | G-05 | CONFIRMED |
| F-06 | Synthesis misrepresents an agent position | The orchestrating peer/operator over-editorialized, compressed a caveat away, or merged two distinct claims | Compare synthesis bullets against raw responses and require claim-level citations | G-06 | HYPOTHESIZED |

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
  root_cause: A response arrived after the orchestrating peer/operator began synthesis or after the Hall moved past independent assessment.
  repair_entry_point: koskadeux-mcp/council_hall.py:record_response
  change_pattern: Attempt the normal flattened `record_response` call only if the current phase permits it. If the tool rejects a late write, preserve the answer as external late-arriver evidence; restart synthesis only through a separately verified supported operator/state procedure, never a fabricated `transition` argument.
  rollback_procedure: If the late response belongs to a duplicate dispatch, mark it superseded and keep the first valid response.
  integrity_check: Confirm the final decision record states whether the late response was included or excluded.
- id: G-03
  symptom_ref: F-03
  component_ref: Cross-Poll Bundle
  root_cause: Cross-pollination began before independent assessment was complete enough to avoid anchoring.
  repair_entry_point: koskadeux-mcp/council_hall.py:get_cross_poll_bundle
  change_pattern: Do not dispatch the premature bundle. Resolve quorum or late-arriver state; if the deployed tool exposes no phase-reset action, start a replacement Hall with the same neutral prompt and explicit participant/evidence binding rather than inventing one.
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
  change_pattern: Redispatch the same start-bound Hall participant with `mode=open_response`, keep the same neutral prompt, and record the parser failure as superseded evidence.
  rollback_procedure: Exclude the failed strict-schema artifact from synthesis while preserving it in the transcript for audit.
  integrity_check: Confirm the replacement answer is free-form, cites evidence, and can be compared with the other start-bound participants' positions.
- id: G-06
  symptom_ref: F-06
  component_ref: Synthesis Pass
  root_cause: The orchestrating peer/operator compressed or rewrote an agent position enough to alter the meaning.
  repair_entry_point: synthesis evidence returned by council_hall status/summarize and its verified owning state record
  change_pattern: Rebuild synthesis with claim-level bullets, cite each agent next to each claim, and separate agreement from the orchestrator's assessment.
  rollback_procedure: Mark the biased synthesis superseded and do not use it as the basis for cross-pollination.
  integrity_check: Confirm each summarized claim maps to one raw response passage or is labeled as orchestrator assessment.
```

## §H. Evolve

### §H.1 Invariants

- Independent assessment must happen before any participant sees another participant's answer.
- Cross-pollination must use a bundle that contains every eligible independent assessment exactly once.
- The orchestrating peer/operator's synthesis must separate agent positions from the orchestrator's own assessment.
- At Hall start, the explicit `agents` argument or verified deployed `DEFAULT_AGENTS` binds membership; `infra:council-comms` supplies policy and backend context but currently has no canonical Hall participant-selection field.
- After start, use the bound participant set from the start receipt/status evidence or the retained exact input; do not infer membership from prose.
- Gate voter constants are not Hall participant defaults and must not be used to reconstruct a Hall session.
- Cross-pollination is capped at 4 rounds; persistent no-consensus after round 4 escalates to Max and does not loop further.

### §H.2 BREAKING predicates

- Removing the independent phase is BREAKING because it destroys the anti-anchoring property of the Hall.
- Changing deployed `VALID_AGENTS`, `DEFAULT_AGENTS`, start-bound membership, or quorum semantics without a Council config review is BREAKING.
- Enabling write-mode during Hall deliberation for a session participant is BREAKING because deliberation is read-oriented.
- Dispatching a paused or retired member without explicit current authorization is BREAKING because role and reliability assumptions change.

### §H.3 REVIEW predicates

- Adding a new agent to deployed Hall `VALID_AGENTS` or `DEFAULT_AGENTS` requires REVIEW.
- Changing a configured Hall participant's model frontier requires REVIEW.
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

A config default is a deployed `council_hall.py` participant/quorum default or a model frontier, cost cap, timeout, or retired-agent policy read from its actual owning source. Do not infer a Hall participant default from `infra:council-comms` unless that entity gains and documents such a field.

### §H.6 Adjudication

When two agents classify a Hall change differently, use the more restrictive class. Max resolves changes that affect membership, auth scope, money/security behavior, quorum policy, or final decision authority.

## §I. Scenario Set

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01, §D]
    scenario: |
      id: E-01. trigger: A BQ architecture choice has conflicting ordinary review advice and needs unbiased Hall deliberation. pre_conditions: neutral decision question, evidence refs, branch, BQ entity, and a policy-authorized participant choice are available; no participant has seen peer answers. tool_or_endpoint: council_hall(action=start, topic=<topic>, prompt=<neutral_prompt>, agents=<explicit_participant_list>). argument_sourcing: topic from the blocking decision; neutral_prompt from shared evidence and decision dimensions; agents from an explicit choice accepted by the live tool schema, or omit only when intentionally accepting the verified deployed DEFAULT_AGENTS. idempotency: IDEMPOTENT_WITH_KEY on topic + prompt_digest + sorted(evidence_refs). expected_success: a deliberation_id with phase=independent; when the receipt or status exposes membership, it agrees with the explicit input or verified default. expected_failures: duplicate_deliberation, invalid participant id, or biased prompt. next_step_success: dispatch the identical neutral prompt only to the participant set bound at start. next_step_failure: repair participant or prompt state before any answer is collected.
    expected_answers:
      - kind: tool_call
        tool: council_hall
        argument_keys: [action, topic, prompt, agents]
        argument_values:
          action: start
    weight: 0.06666666666666667
  - id: I-02
    type: operate
    refs: [E-02, §D]
    scenario: |
      id: E-02. trigger: The first start-bound Hall participant returns an independent assessment. pre_conditions: deliberation_id exists, phase=independent, the responding agent belongs to the participant set bound by the successful start call, the frozen neutral prompt was used, and the answer includes verdict, confidence, claims, objections, and content. tool_or_endpoint: council_hall(action=record_response, deliberation_id=<id>, agent=<start_bound_participant_id>, phase=independent, verdict=<approve|reject|conditional>, confidence=<high|medium|low>, key_claims=<list>, objections=<list>, content=<raw_answer>). argument_sourcing: deliberation_id from start; bound agent IDs from the explicit input or verified default and any receipt/status evidence; agent from response owner; verdict, confidence, key_claims, objections, and content from the raw answer. idempotency: IDEMPOTENT_WITH_KEY on deliberation_id + agent + phase. expected_success: that participant's response is recorded without advancing to cross-poll or exposing it to any other participant. expected_failures: duplicate response, agent absent from the bound set, missing required fields, or answer references another participant. next_step_success: continue collecting independent responses from the remaining bound participants. next_step_failure: isolate parser, membership, or phase issues before synthesis.
    expected_answers:
      - kind: tool_call
        tool: council_hall
        argument_keys: [action, deliberation_id, agent, phase, verdict, confidence, key_claims, objections, content]
        argument_values:
          action: record_response
          phase: independent
    weight: 0.06666666666666667
  - id: I-03
    type: operate
    refs: [E-03, F-03, G-03]
    scenario: |
      id: E-03. trigger: The start-bound Hall participants have recorded enough independent assessments for the configured quorum and material disagreement remains. pre_conditions: quorum is met against the participant set bound by the successful start call, eligible independent responses are recorded exactly once, synthesis has identified disagreement questions, and no cross-poll bundle exists yet. tool_or_endpoint: council_hall(action=get_cross_poll_bundle, deliberation_id=<id>, phase=cross_poll). argument_sourcing: deliberation_id from start; participant set from the explicit input or verified deployed default plus any receipt/status evidence; phase from current state; disagreement_set from synthesis notes; included assessments from eligible response records. idempotency: IDEMPOTENT_WITH_KEY on deliberation_id + cross_poll_bundle_version. expected_success: bundle contains the original prompt, every eligible independent assessment exactly once, and targeted instructions for cross-poll response. expected_failures: premature_cross_poll, missing eligible response, or biased synthesis. next_step_success: dispatch the bundle only to the start-bound participants for Phase 3. next_step_failure: apply G-03 and regenerate the bundle only after phase state is repaired.
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
      id: E-04. trigger: Cross-poll responses have been recorded and the Hall orchestrator needs a final synthesis for the decision record. pre_conditions: independent and cross-poll response sets are available, synthesis notes preserve claim-level attribution, and unresolved evidence gaps are named. tool_or_endpoint: council_hall(action=summarize, deliberation_id=<id>). argument_sourcing: consensus candidates from cross-poll answers; dissent from remaining objections; evidence gaps from raw responses; escalation owner from policy boundary. idempotency: IDEMPOTENT_WITH_KEY on deliberation_id + final_response_set_hash. expected_success: summary classifies consensus, majority-plus-dissent, or no-consensus and names the next action. expected_failures: synthesis misrepresents a claim, hides dissent, or treats a policy choice as agent-resolvable. next_step_success: attach the final decision or escalation record to the BQ. next_step_failure: repair with G-04 or G-06 before closing the Hall.
    expected_answers:
      - kind: tool_call
        tool: council_hall
        argument_keys: [action, deliberation_id]
        argument_values:
          action: summarize
    weight: 0.06666666666666667
  - id: I-05
    type: isolate
    refs: [F-04, G-04]
    scenario: |
      id: F-04. trigger: Final positions in a three-participant Hall are split 2-1, with two participants accepting the architecture while the third rejects it on maintainability risk. pre_conditions: the three IDs belong to the start-bound participant set, all independent and cross-poll responses are recorded, each verdict has confidence and objections, and orchestrator synthesis shows a real value judgment rather than missing evidence. tool_or_endpoint: council_hall(action=summarize, deliberation_id=<id>). argument_sourcing: majority and dissent from recorded responses; participant membership from start evidence; unresolved predicates from synthesis; owner from escalation policy. idempotency: READ_ONLY_DIAGNOSTIC until a final decision owner acts. expected_success: classify as agent-disagreement deadlock or majority-plus-dissent, preserve the dissenting participant's position, and escalate to Max if the value judgment blocks the BQ. expected_failures: calling it full concurrence, dropping dissent, or rerunning agents indefinitely. next_step_success: use G-04 to record majority, dissent, evidence gap, and decision owner. next_step_failure: keep the Hall open with no promotion.
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
      id: F-02. trigger: A start-bound Hall participant returns an independent answer after the orchestrator has begun synthesis from the responses already received. pre_conditions: the late participant's dispatch task, start-bound membership evidence, parsed verdict/confidence/claims/objections/content, synthesis timestamp, response timestamp, and current Hall phase are available. tool_or_endpoint: council_hall(action=record_response, deliberation_id=<id>, agent=<start_bound_participant_id>, phase=independent, verdict=<value>, confidence=<value>, key_claims=<list>, objections=<list>, content=<late_answer>). argument_sourcing: flattened response fields from the dispatch answer, membership from start input/default evidence, phase from Hall state, and timestamps from dispatch and synthesis records. idempotency: IDEMPOTENT_WITH_KEY on deliberation_id + agent + phase + dispatch_task_id. expected_success: either the supported call records the late response or returns an explicit phase rejection; no undocumented transition is attempted. expected_failures: silently overwriting synthesis, pretending the response arrived on time, or inventing a phase-reset argument. next_step_success: apply G-02 and preserve both original synthesis and late-arriver handling. next_step_failure: escalate only if inclusion materially changes the decision and no supported recovery exists.
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
      id: F-01. trigger: A Hall remains stuck in phase=independent because one start-bound participant has no recorded response while the others have answered. pre_conditions: start membership evidence, response records, dispatch task ids, timeout policy, and backend health are available. tool_or_endpoint: council_hall(action=status, deliberation_id=<id>). argument_sourcing: response counts from Hall status; missing participant by comparing those records with the explicit input or verified default; dispatch state from council_request records; timeout from its owning configuration. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify as no quorum or missing participant response, not a deliberation disagreement. expected_failures: generating cross-poll early or diagnosing a policy deadlock before quorum. next_step_success: use G-01 to verify health, redispatch once, or record a quorum exception. next_step_failure: keep independent phase blocked until the absent participant decision is explicit.
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
      id: G-01. trigger: One start-bound participant is still missing after the independent-response timeout. pre_conditions: original neutral prompt, start membership evidence, evidence refs, missing dispatch task id, changed-file diff, and repository root are available. tool_or_endpoint: council_request(agent=<start_bound_participant_id>, mode=open_response, task=<prompt_with_changed_file_refs>, cwd=<repo>). argument_sourcing: agent by comparing response records with the explicit start input or verified default; changed_files from git diff --name-only or the BQ evidence list and embedded in task; retry prompt from the original neutral prompt plus "answer only for these diffs"; cwd from the repository root; dispatch cap from its owning configuration. idempotency: IDEMPOTENT_WITH_KEY on deliberation_id + agent + retry_prompt_digest. expected_success: the missing participant returns a bounded independent assessment suitable for record_response. expected_failures: agent is not in the bound set, retry prompt exposes peer answers, uses strict review schema, or expands beyond the diff-only scope. next_step_success: record the response and resume synthesis. next_step_failure: record a named quorum exception and proceed only if policy allows.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, cwd]
        argument_values:
          mode: open_response
    weight: 0.06666666666666667
  - id: I-10
    type: repair
    refs: [G-02, F-02]
    scenario: |
      id: G-02. trigger: A late response from a start-bound Hall participant should be considered because it raises a material evidence gap before cross-poll dispatch. pre_conditions: flattened late-response fields, start membership evidence, prior synthesis note, current phase, and dispatch timestamps are preserved. tool_or_endpoint: council_hall(action=record_response, deliberation_id=<id>, agent=<start_bound_participant_id>, phase=independent, verdict=<value>, confidence=<value>, key_claims=<list>, objections=<list>, content=<late_answer>). argument_sourcing: response fields from the participant transcript; agent from the explicit input or verified default; timestamps from Hall state. idempotency: IDEMPOTENT_WITH_KEY on deliberation_id + agent + phase + dispatch_task_id. expected_success: the response is recorded only if the deployed phase rules permit it; otherwise the rejection and external late evidence are preserved. expected_failures: agent is not in the bound set, overwriting prior synthesis, or sending nonexistent transition/reset arguments. next_step_success: rebuild synthesis only through a separately verified supported procedure and preserve the original timestamp. next_step_failure: exclude the late response from tool state, retain it as audit evidence, and document why.
    expected_answers:
      - kind: tool_call
        tool: council_hall
        argument_keys: [action, deliberation_id, agent, phase, verdict, confidence, key_claims, objections, content]
        argument_values:
          action: record_response
          phase: independent
    weight: 0.06666666666666667
  - id: I-11
    type: repair
    refs: [G-04, F-01, council-gate-process:F-04]
    scenario: |
      id: G-04. trigger: Some start-bound Hall participants responded, one is absent, and the gate owner asks for an explicit partial-response summary instead of waiting another cycle. pre_conditions: quorum exception is allowed, the absent participant is derived from start evidence and response records, available raw responses are preserved, and the BQ risk of delay is recorded. tool_or_endpoint: council_hall(action=summarize, deliberation_id=<id>). argument_sourcing: participating and absent agents from start membership evidence plus response records; quorum exception from operator or gate owner; risk note from BQ state. idempotency: IDEMPOTENT_WITH_KEY on deliberation_id + partial_response_set_hash. expected_success: if deployed phase rules allow summary, the record explicitly names the partial response set, absent participant, confidence reduction, dissent status, and whether council-gate-process repair is needed. expected_failures: tool rejects summary before full participation, partial concurrence is presented as full consensus, or the missing participant is hidden. next_step_success: attach the explicitly partial summary to the gate record and route any gate-blocking issue through council-gate-process:F-04. next_step_failure: preserve the status/response evidence, keep the Hall open, and redispatch the missing participant; do not invent include_partial.
    expected_answers:
      - kind: tool_call
        tool: council_hall
        argument_keys: [action, deliberation_id]
        argument_values:
          action: summarize
    weight: 0.06666666666666667
  - id: I-12
    type: evolve
    refs: [§H, §H.2, §H.3]
    scenario: |
      id: H-01. trigger: A proposal adds another participant to deployed Hall VALID_AGENTS or DEFAULT_AGENTS. pre_conditions: current deployed constants, proposed values, quorum math, cost cap, auth scope, and gateway code patch are available. tool_or_endpoint: council_hall.py configuration patch plus runbook update. argument_sourcing: current values from the deployed source/receipt rather than Living State inference; new role from proposal; quorum and escalation effects from §H invariants. idempotency: CHANGE_REVIEW_REQUIRED. expected_success: classify as BREAKING because accepted/default membership and consensus math change. expected_failures: calling it SAFE because the backend already appears in a capability inventory. next_step_success: review and deploy the gateway configuration before starting a Hall with the new selection. next_step_failure: continue using the verified deployed behavior, never a roster copied from this scenario.
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
    refs: [F-04, G-04, council-gate-process:F-04]
    scenario: |
      id: AMB-01. trigger: One start-bound Hall participant returns verdict=conditional while the other responding participants return approve, and the operator asks whether the Hall has concurrence. pre_conditions: the conditional response, approvals, start membership evidence, gate status, and cross-poll responses are available. tool_or_endpoint: council_hall(action=summarize, deliberation_id=<id>) followed by council-gate-process repair if the condition blocks gate promotion. argument_sourcing: conditional predicate and approvals from recorded responses belonging to start-bound participants; concurrence requirement from gate process; dissent and evidence gaps from Hall synthesis. idempotency: READ_ONLY_DIAGNOSTIC until gate repair is selected. expected_success: classify as ambiguous Hall concurrence, not automatic approval; summarize as majority-plus-condition or no-consensus depending on whether the condition is satisfied, then redirect gate-blocking repair to council-gate-process:F-04. expected_failures: counting conditional as unconditional concurrence, accepting an unbound participant, or changing the Hall verdict enum ad hoc. next_step_success: either prove the condition satisfied and record it, or route through the cross-review gate repair pattern. next_step_failure: escalate to Max when the condition is a policy judgment.
    expected_answers:
      - kind: human_action
        verb: classify
        object: conditional Hall verdict
        target: ambiguous concurrence then council-gate-process:F-04 repair
    weight: 0.06666666666666667
```

## §J. Lifecycle

Lifecycle metadata records the S1265 content-conformance refresh and registered scenario-harness pass.

```yaml lifecycle
last_refresh_session: S1265
last_refresh_commit: 03cd4c0
last_refresh_date: 2026-07-17T20:00:00Z
owner_agent: vulcan
refresh_triggers:
  - Council hall phase flow or synthesis policy changes
  - independent assessment, cross-pollination, or dissent handling changes
  - participating agent capability or availability changes
  - runbook-lint or runbook-harness schema changes
scheduled_cadence: 90d
last_harness_pass_rate: 0.2
last_harness_date: 2026-07-18T08:36:20.840312Z
first_staleness_detected_at: null
```

The Council Hall scenario set is registered under `tests/fixtures/harness_scenarios/council-hall-deliberation/` and passed the S1265 conformant harness.

## §K. Conformance

Conformance fields for the S1265 content refresh.

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1265 / 2026-07-17T20:00:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```

The §K block records the strict-lint result; harness state is authoritative in §J.


<!-- catalog:historical -->
## §M — S533 Operational Updates

Historical S533 snapshot only. S1321 supersedes every gate roster, voter, model-frontier, and dispatch-eligibility statement in this appendix; consult each field's current owning source, and use the explicit input or verified deployed default bound by an active Hall start.

### M.1 — DeepSeek review-mode bypass (S533 R3)

`deepseek_server.py:run_deepseek_task` branches on `mode == "review"` BEFORE instantiating `DeepSeekNativeAgenticLoop`. Review tasks route through `DeepSeekClient.run_council_review()` which:

1. Forces `response_format={"type": "json_object"}` API-side
2. Constrains the verdict enum (`APPROVE | APPROVE_WITH_NITS | APPROVE_WITH_MANDATES | REVISE | REQUEST_CHANGES | REJECT`) and finding-object schema in the prompt
3. Returns a complete envelope shape that `tools/agents.py:_normalize_deepseek_review_response` fast-paths

Rationale: `response_format=json_object` is mutually exclusive with `tools`/`tool_choice="auto"` on the DeepSeek API. The agentic loop uses tools, so it cannot also force structured JSON output. Bypass restores deterministic JSON envelopes for review-mode calls.

The agentic loop remains unchanged for `build` and `author` modes. DS has no tool/file access in review-mode bypass — inline the spec content into the task body.

### M.2 — XAI retired from active Council (S528)

At S528, the frontier-only policy retired XAI per Max directive. `xai_client.py` and `grok_cli_bridge.py` were preserved in the repository for reactivation, with the reactivation runbook at `infra:council-comms.retired_agents.xai`. That snapshot listed MP, AG, and DeepSeek as active voters; S1321 supersedes that list.

### M.3 — AG progress-guard ≤4-file workaround for review-mode

`antigravity_cli_bridge.py` enforces a "15-turn no-file-changes" progress guard intended for build-mode dispatches. In review-mode this guard kills AG before it can return its envelope when the task asks AG to read many files. Pattern observed in S533: a review task with 8 file reads + analysis hit 15 turns before envelope return.

Workaround until `BQ-COUNCIL-AG-PROGRESS-GUARD-FIX` Gate 3 closes: cap AG review-mode tasks at **≤4 file reads** total. Phrase the task with explicit "STRICT BUDGET: ≤N file reads then return JSON envelope" and "Do not read additional files." This keeps AG well under the 15-turn limit.

The S533 workaround assigned broader survey work Vulcan-direct via `shell_request` before an AG verdict-only dispatch. That was session-specific orchestration, not a standing authority rule; current work belongs to whichever peer/operator is orchestrating under the live contract.

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
<!-- /catalog:historical -->

## §N — S1582 Operational Update: council_hall service retired, manual procedure

The `council_hall` orchestration service was removed from `koskadeux-mcp` at commit
`d393224d95c35a45d83a2347d1fcedc99f67895e` (2026-08-12, "refactor: make council review
file-only"): package `council_hall/`, `com.koskadeux.council-hall.plist`, and related
middleware were deleted. There is no `council_hall` MCP tool. This page's protocol was
executed fully manually in S1581 (seller sales surface deliberation, T-2026-000687)
and that run is the reference for the mapping below.

| Retired automation | Manual equivalent (verified S1581) |
|---|---|
| `council_hall(action=start, ...)` | Write ONE frozen neutral prompt (background, proposal, decision dimensions, requested structure; no roles assigned). Freeze it before any dispatch; every participant gets the identical text. |
| Phase 1 dispatch | `council_request(agent=<cc\|kimi\|glm>, mode=open_response, task=<frozen prompt>)`, one call per participant, none shown another's answer. E-02 unchanged. |
| `council_hall(action=record_response, ...)` | Keep each returned response file (`/Users/max/council/<member>/response-*.md`) unmodified; reference the paths in the owning ticket or BQ entity so the record is durable. |
| `council_hall(action=get_cross_poll_bundle)` | Orchestrating peer builds a faithful comparison of the Phase 1 answers, then cross-polls ONLY the disagreements: a second `open_response` round carrying the original prompt plus every Phase 1 assessment verbatim. Do not cross-poll points already converged. Bias rules of E-03 (`premature_cross_poll`, `biased_synthesis`) still apply to the hand-built bundle. |
| Convergence/synthesis machinery | Orchestrating peer writes the synthesis; persist decision + binding constraints + open questions into the owning BQ entity, not only prose. |

The §E error signatures remain meaningful as protocol violations (e.g. `premature_cross_poll`
is now a mistake the orchestrating peer can make by hand); the `duplicate_deliberation` and
`participant_config_missing` signatures referred to service state and can no longer occur
mechanically — their intent survives as "do not run two deliberations on one question" and
"dispatch only the exact governed roster CC/Kimi/GLM".

If deliberation volume ever justifies re-automating this, that is a new Gate 1 design item,
not a restoration of the deleted code.
