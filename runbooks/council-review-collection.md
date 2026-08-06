---
runbook_id: council-review-collection
domain: council-operations
status: ACTIVE
authoritative_for:
  - topic: council-review-collection
    section: §C. Architecture & Interactions
aliases:
  - council-verdict-collection
  - gate-recording
error_signatures:
  - signature: dispatch_sha_invalid
    section: §E. Operate
  - signature: review_preload_unresolved
    section: §E. Operate
  - signature: completion_truncated
    section: §E. Operate
  - signature: cc_verdict_parse_failure
    section: §E. Operate
  - signature: glm_page_path_hallucination
    section: §E. Operate
  - signature: gate_status_not_flipped
    section: §E. Operate
  - signature: peer_msg_silent_dedupe
    section: §E. Operate
  - signature: mp_lane_held
    section: §E. Operate
supersedes: []
superseded_by: []
owner: mars
last_verified_at: 2026-08-06
system_name: council-review-collection
purpose_sentence: Operating authority for collecting Council review verdicts reliably, folding mandates, recording gate results in Living State, and coordinating the shared MP builder lane between peer instances.
owner_agent: mars
escalation_contact: vulcan
lifecycle_ref: §J
authoritative_scope: |
  The mechanics of running a review round on the live CC/Kimi/GLM panel: per-reviewer dispatch traps and their at-dispatch mitigations, verdict collection and repair, mandate folding into gate revisions, recording gate outcomes on build:bq-* entities (including the leaf-patch requirement for gateN.status), and peer-bus lane coordination for the single MP builder. NOT gate selection or the four-gate lifecycle itself; see council-gate-process.md. NOT roster composition or model pins; infra:council-comms in Living State is canonical for the live roster, models, cost caps, and per-agent activation state. NOT dispatch transport internals; see agent-dispatch.md.
linter_version: 1.0.0
---

# Council Review Collection, Gate Recording, and Lane Coordination

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Kimi review dispatch (read-only at-SHA) | SHIPPED | `tools/agents.py` | `provider_readonly_review` harness tests | 2026-07-30 |
| GLM review dispatch (read-only at-SHA) | SHIPPED | `council_dispatch_middleware/` | live proof S1369 task ff0f2f67 | 2026-07-30 |
| CC review dispatch (agentic audit) | SHIPPED | `council_hall/agent_adapters.py` | live use through S1407 | 2026-07-30 |
| Gate result recording on BQ entities | SHIPPED | `state_service.py` | live use through S1407 | 2026-07-30 |
| Peer-bus lane coordination | SHIPPED | `peer_bus.py` | live use through S1408 | 2026-07-30 |
| Verdict-collection automation of this runbook as executable checks | PLANNED | — | — | 2026-07-30 |

Backing-code paths are relative to the koskadeux-mcp repository root.

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Review dispatcher | council_request(agent=..., mode=review) | dispatch receipts | koskadeux-mcp gateway | dispatch_sha resolves against cwd or the server process cwd; see E-01 |
| Kimi reviewer | Kimi Code subscription transport via the shared provider_readonly_review harness | evidence ledger per dispatch | read_file_at_sha, list_dir_at_sha, grep_at_sha, git_show | Verify plan endpoint/model in the live receipt and registry; exact model match mandatory; fails closed on coverage gaps |
| GLM reviewer | OpenRouter pinned endpoint via the same harness | evidence ledger per dispatch | the same read-only tool set | USD 5 authorized live max; exact model match mandatory |
| CC reviewer | council dispatch path, agentic | structured_payload in receipt | repo checkout at SHA | raw structured_payload is authoritative over legacy coercion |
| Gate recorder | `state_request(action=bq_update)` | build:bq-* entities, Event Ledger | Living State | Set `gate_status_update=true` to update `body.gateN.status`; see E-02. |
| Peer bus | peer_msg_send and peer_msg_inbox | peer_messages table | both instances | silent dedupe on (from, to, kind, ref_entity); see E-03 |
| MP builder lane | dispatch_mp_build | MP mutex, Living State claims | single Codex CLI on Titan-1 | one lane; claim on the bus before dispatch and use the live required payload; see E-03 |

Canonical live-roster reference: `state_request(action=get, key=infra:council-comms)`. Read it before any Council work in a session; this runbook does not restate roster, model pins, or cost caps.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| mars | dispatch reviews, collect verdicts, record gates, coordinate lane | council_request, state_request, peer_msg tools | full operator | COMPLETE |
| vulcan | same as mars (symmetric peer) | same | full operator | COMPLETE |
| mp | builder only; excluded from reviewing its own work | dispatch_mp_build | build lane | COMPLETE |
| cc, kimi, glm | review-only voters | per infra:council-comms | read-only at SHA | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: Dispatching a Kimi or GLM review of a commit, including commits in repos other than koskadeux-mcp.
  pre_conditions:
    - dispatch SHA is a full 40-hex commit reachable in a local checkout
    - the checkout has fetched the SHA
    - the connected client council_request enum contains the selected required voter; if upstream and client differ, refresh or reconnect before dispatch
    - review scoped within the reviewer cost cap; for Kimi 3-page deltas use max_tokens 20000 plus a summary word cap; for GLM multi-page reads quote the file path on its own line and instruct re-issuing identical args changing only offset
    - turn budget sized to the width of the read, NOT left at defaults. GLM and Kimi read the pinned checkout themselves and spend a turn per small batch of reads. Defaults are max_turns 8 and max_calls_per_turn 4, and there is a hard ceiling of 24 turns that a caller CANNOT raise. A reviewer that reaches the ceiling is terminated mid-investigation and its entire evidence trail is discarded with no verdict. Raise max_calls_per_turn so the same reads finish in far fewer turns; that is the only lever a caller actually has
  tool_or_endpoint: council_request(agent=<kimi|glm>, mode=review, task=<review_prompt>, dispatch_sha=<SHA>, cwd=<repo_root_containing_SHA>, max_calls_per_turn=<batch_size>, max_turns=<<=24>, timeout_s=<bound>)
  argument_sourcing:
    review_prompt: derive from the exact gate/spec questions and changed-file coverage, with explicit read-only scope
    cwd: absolute path of the repo checkout that contains the dispatch SHA; the resolver uses args.cwd or the server process cwd, and review_sources entries do NOT satisfy it (root-caused S1407, verified live on backend SHA 00a45639)
    max_calls_per_turn: size from the number of files the reviewer must open. 16 is a sound default for a multi-file review; the default of 4 is only adequate for a narrow one. Observed live in S1443, a GLM review made 39 reads at roughly 1.6 calls per turn, consumed 25 turns and was killed at the ceiling (task fc0315e6)
    max_turns: may be raised up to 24 and no further; hard_max_turns is a literal in the dispatcher. Setting it higher is silently ineffective, so never treat a raised max_turns as the mitigation on its own
    review_sources.required_paths: mandatory evidence AND inlined into the material context, so they count against the shared inline limit. List only the fold files; name large anchors in the prose and let the reviewer open them with read-only tools. The repo and SHA in review_sources authorise the whole tree, not just required_paths (proven S1442)
  idempotency: IDEMPOTENT
  expected_success:
    shape: dispatch receipt with a running task id, preloaded review context, complete coverage, exact model match, and cost within cap
    verification: receipt shows the dispatch SHA resolved, every changed file read completely at SHA, and a parsed terminal verdict
  expected_failures:
    - signature: dispatch_sha_invalid
      cause: cwd omitted on a non-koskadeux-mcp SHA; the resolver falls back to the server cwd and cannot find the commit
    - signature: review_preload_unresolved
      cause: no dispatch_sha, head, or branch ref supplied at all, or the SHA is not fetched in the target checkout
    - signature: completion_truncated
      cause: default token budget too small for a Kimi 3-page delta; the terminal response is cut before the verdict
    - signature: glm_page_path_hallucination
      cause: on page 3 and later of long filenames GLM re-types and mutates the path, so the read fails or reads the wrong file
    - signature: reviewer_turn_ceiling_exhausted
      cause: the reviewer was reading the required files correctly but ran out of turns and was terminated mid-investigation. Receipt shows stop_reason tool_use, turns_used at or above 24, a healthy tool_calls list and a generic process-failed error code. NOT a filesystem, provider, model or cost fault, and NOT fixed by retrying unchanged
    - signature: review_material_inline_limit_exceeded
      cause: review_sources.required_paths are inlined; large mandatory paths breach the shared inline limit before the reviewer starts
  next_step_success: record the verdict per E-02
  next_step_failure: apply the matching mitigation (pass cwd, raise max_tokens with a word cap, quote the path with the offset-only protocol, raise max_calls_per_turn, or move large paths out of required_paths) and re-dispatch; two malformed terminal attempts fail closed and a verdict resting on incomplete coverage is invalid. Read the receipt before retrying, because a retry with unchanged arguments after a turn-ceiling termination will fail identically and burn the round
- id: E-02
  trigger: A complete valid panel has been collected and the gate outcome must be recorded on the BQ entity.
  pre_conditions:
    - every required voter is terminal with exact model match
    - reviewer is not the builder
    - for CC verdicts, the raw JSON envelope parsed. CC now self-repairs prose-before-JSON. Its path re-prompts the model to reformat its own completion and re-validates, recorded as terminal_normalization_attempted and terminal_normalization_succeeded on the receipt. GLM and Kimi have NO equivalent retry and hard-fail the whole completion on the same condition, so a substantively complete GLM or Kimi verdict can be discarded outright. Never scrape a verdict out of prose on any provider
  tool_or_endpoint: "state_request(action=bq_update, bq_code=<code>, gate=<N>, status=<canonical>, note=<panel_refs>, session_id=<session>, gate_status_update=true, expected_version=<version>); issue a separate bq_update with gate_status_update=false only when top-level lifecycle status must also change"
  argument_sourcing:
    expected_version: read the entity immediately before patching; optimistic lock
    status: canonical vocabulary only (REQUEST_CHANGES, AUTHORING_IN_FLIGHT, AUTHORED_PENDING_REVIEW, APPROVED, REJECTED); free text is not recognized by middleware
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: entity key + gate number + verdict commit SHA
  expected_success:
    shape: entity version bumps; gateN.status shows the canonical word; the note carries panel task ids and the dispatch SHA
    verification: state_request(action=get, key=build:bq-*) and confirm gateN.status actually changed
  expected_failures:
    - signature: gate_status_not_flipped
      cause: omitting gate_status_update=true updates only the top-level lifecycle path and leaves body.gateN.status unchanged
    - signature: cc_verdict_parse_failure
      cause: CC emitted prose before the JSON block, so the envelope parser rejected a round that looked complete
  next_step_success: fold mandates per G-04 notes if the verdict carries them, then continue the gate flow per council-gate-process.md
  next_step_failure: re-read the entity, repeat bq_update with gate_status_update=true and the fresh expected_version, and verify again; for a parse failure, re-dispatch CC with the raw-JSON instruction
- id: E-03
  trigger: An instance needs the peer bus for a follow-up message or wants the single MP builder lane.
  pre_conditions:
    - peer bus drained this cycle (at open, before dispatch, before merge, before close)
    - for a lane request, no unacked lane claim from the peer
  tool_or_endpoint: peer_msg_send(to=<peer>, kind=claim, ref_entity=<entity>, body=<lane_claim>) followed by dispatch_mp_build(task=<bounded_build_task>, cwd=<absolute_repo>, bq_code=<code>, caller_instance=<self>, dispatch_class=structural) once the lane is known free
  argument_sourcing:
    ref_entity: vary it with a session or round marker on follow-ups, or change kind, because the bus silently dedupes identical (from, to, kind, ref_entity) tuples
    bounded_build_task: derive from the approved BQ/spec and include the expected output manifest
    absolute_repo: resolve from config:resource-registry and verify the clean isolated checkout/base before dispatch
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: persisted row returned with a new message id; a lane claim is acked or uncontested; the build dispatches without mutex contention
    verification: the returned row id differs from any earlier message; no mp_busy error on dispatch
  expected_failures:
    - signature: peer_msg_silent_dedupe
      cause: identical tuple to an earlier message; the send returns success but no new message is delivered
    - signature: mp_lane_held
      cause: the peer's build is in flight on the single Codex lane; the mutex or dispatcher refuses
  next_step_success: proceed with the build and send a release status at completion
  next_step_failure: resend with a varied ref_entity or kind; for the lane, wait for the peer's lane-free status and verify ground truth with git status before any redispatch, because a silent task past 300 seconds may still have delivered
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | Kimi or GLM review fails instantly citing an unresolvable or invalid SHA | cwd omitted for a non-default repo; SHA not fetched locally | run git cat-file -e on the SHA in the intended repo; re-check the dispatch args for cwd | G-01 | CONFIRMED |
| F-02 | Reviewer output ends mid-sentence with no verdict | token budget exhausted on a Kimi multi-page delta | receipt shows a truncation or max-token stop reason | G-02 | CONFIRMED |
| F-03 | CC envelope rejected though a verdict is visible in the text | prose preceded the JSON block | inspect the raw terminal message; JSON is not at the first byte | G-03 | CONFIRMED |
| F-04 | Gate dashboard still shows the old gate status after recording | `bq_update` omitted `gate_status_update=true` | `state_request(action=get, key=build:bq-*)` and compare body.gateN.status against the note | G-04 | CONFIRMED |
| F-05 | Peer never reacted to a follow-up bus message | silent dedupe swallowed it | check peer_messages for a new row id after the send | G-05 | HYPOTHESIZED |
| F-06 | MP dispatch refused or times out while the peer session is live | lane held by the peer, or the task silently completed | drain the bus for claims; check git status in the target repo before redispatch | G-06 | HYPOTHESIZED |
| F-07 | Reviewer fails after several minutes of apparently healthy work, generic process-failed error, no verdict | turn ceiling reached while reading; work discarded | receipt shows stop_reason tool_use, turns_used at or above 24, and a populated tool_calls list of successful reads | G-07 | CONFIRMED |
| F-08 | A complete, high-quality GLM or Kimi verdict is rejected as schema-invalid | the model wrote prose before the JSON and that provider has no normalization retry | compare the receipt against a CC receipt for the same condition: CC shows terminal_normalization_succeeded, GLM and Kimi show a bare schema-invalid error | G-08 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Review dispatcher
  root_cause: dispatch_sha resolves against args.cwd or the server process cwd, and review_sources entries do not satisfy the resolver
  repair_entry_point: re-dispatch with cwd set to the repo root containing the SHA, fetching the SHA first if absent
  change_pattern: dispatch-argument correction only; no code change
  rollback_procedure: none needed; failed dispatches make no state change
  integrity_check: fresh receipt shows the SHA resolved and review context preloaded
- id: G-02
  symptom_ref: F-02
  component_ref: Kimi reviewer
  root_cause: default token budget too small for a 3-page delta review
  repair_entry_point: re-dispatch with max_tokens 20000 and an explicit summary word cap in the prompt
  change_pattern: dispatch-argument correction only; never hand-repair a truncated verdict
  rollback_procedure: none; failed dispatches make no state change
  integrity_check: terminal verdict present, coverage complete, cost within cap
- id: G-03
  symptom_ref: F-03
  component_ref: CC reviewer
  root_cause: CC emitted prose before the JSON envelope and the parser is strict by design
  repair_entry_point: re-dispatch instructing raw JSON, no preamble, no markdown fences
  change_pattern: prompt correction only; do not scrape a verdict out of prose
  rollback_procedure: none; failed dispatches make no state change
  integrity_check: structured_payload parses on the fresh receipt
- id: G-04
  symptom_ref: F-04
  component_ref: Gate recorder
  root_cause: The bq_update call omitted gate_status_update=true, so it targeted top-level lifecycle state instead of body.gateN.status.
  repair_entry_point: state_request(action=bq_update) with gate_status_update=true and expected_version
  change_pattern: repeat the bounded gate-status update using canonical vocabulary and the fresh entity version
  rollback_procedure: issue the same bounded update with the prior canonical status and the next expected_version
  integrity_check: state_request(action=get) shows the intended gateN.status and a version bump
- id: G-05
  symptom_ref: F-05
  component_ref: Peer bus
  root_cause: silent dedupe on the (from, to, kind, ref_entity) tuple
  repair_entry_point: resend with a varied ref_entity or a different kind
  change_pattern: coordination-message correction; messages are append-only
  rollback_procedure: none; messages are append-only
  integrity_check: a new message row id is returned and the peer acks
- id: G-06
  symptom_ref: F-06
  component_ref: MP builder lane
  root_cause: single-builder lane contention, or a silently completed task mistaken for a failure
  repair_entry_point: wait for the peer's lane-free status; verify ground truth with git status before any redispatch
  change_pattern: coordination only; no forced release except a genuine stale-claim reconciliation
  rollback_procedure: none
  integrity_check: dispatch proceeds without mp_busy and no duplicate build lands
- id: G-07
  symptom_ref: F-07
  component_ref: Review dispatcher turn budget
  root_cause: max_turns defaults to 8 and hard_max_turns is a literal 24 that a caller cannot raise, while max_calls_per_turn defaults to 4. A reviewer reading many files spends turns faster than the ceiling allows and is terminated with its evidence trail discarded.
  repair_entry_point: re-dispatch with max_calls_per_turn raised to match the width of the read (16 for a multi-file review) and max_turns at 24; do NOT retry with unchanged arguments
  change_pattern: dispatch-argument correction only; no code change and no server restart
  rollback_procedure: none; failed dispatches make no state change
  integrity_check: fresh receipt shows turns_used well below 24 and a parsed terminal verdict
  known_limit: this is a mitigation, not a fix. The ceiling remains hard-coded and a wide enough review will still hit it. The durable repair is owned by BQ-COUNCIL-REVIEW-TRANSPORT-CONSOLIDATION-S1443 chunk C1.
- id: G-08
  symptom_ref: F-08
  component_ref: Per-provider verdict validators
  root_cause: the terminal-normalization retry exists only on the CC path. GLM and Kimi each make a single strict decode call and return failure on any exception, so a valid verdict wrapped in prose is destroyed.
  repair_entry_point: re-dispatch that seat instructing raw JSON as the first byte, no preamble and no markdown fences. FIRST recover EVERY discarded attempt with check_build on each exact task id, not only the most recent one. Attempts on the same head can differ in substance, and the older attempt is often the richer, so taking only the latest silently loses review content that nobody will know existed. Observed live in S1444 on head 41415ae2, where the first discarded Kimi attempt carried three minor findings and the second carried none, both APPROVE with zero mandates
  change_pattern: prompt correction only; NEVER relax strict validation, and never hand-transcribe a verdict
  rollback_procedure: none; failed dispatches make no state change
  integrity_check: structured_payload parses on the fresh receipt and the seat is recorded
  known_limit: mitigation only, and not a deterministic one. The retry mechanism already exists and is proven on CC; it is simply not wired to the other two transports. Prompt hardening measurably shrinks the prose prefix but does not eliminate it, so a re-dispatch is better than even odds rather than a guarantee. State that odds calibration before spending a round on it. Durable repair owned by BQ-COUNCIL-REVIEW-TRANSPORT-CONSOLIDATION-S1443 chunk C1.
```

## §H. Evolve

### §H.1 Invariants

- The builder never reviews its own work; MP is excluded from panels on MP-built SHAs.
- Security, auth, payments, production-data, and customer-data gates require the complete unanimous live panel; no reduced quorum, no substitute voter.
- A verdict resting on incomplete file coverage, a model mismatch, or a malformed unrepaired terminal response is invalid and fails closed.
- Gate status writes use the canonical vocabulary; free text is not a gate status.
- infra:council-comms is canonical for roster, models, caps, and quirk updates; this runbook defers to it.

### §H.2 BREAKING predicates

- Changing the required voter set or quorum for any gate class.
- Making any fail-closed verdict path fail-open.
- Allowing gate status recording without a complete valid panel.

### §H.3 REVIEW predicates

- Changing per-reviewer dispatch defaults (token budgets, turn caps, cwd resolution).
- Changing the peer-bus dedupe tuple or the claim/release protocol.

### §H.4 SAFE predicates

- Adding new error signatures or isolate rows from observed incidents.
- Tightening prompts or budgets within existing caps.

### §H.5 Boundary definitions

#### module

The review-collection procedures in this runbook plus the dispatch surfaces they name (council_request, state_request, peer bus tools).

#### public contract

The E-block operate entries and the canonical gate-status vocabulary.

#### runtime dependency

koskadeux-mcp gateway, Living State, the peer bus, and the provider endpoints named in infra:council-comms.

#### config default

Per-reviewer budgets and caps as recorded in infra:council-comms at dispatch time.

### §H.6 Adjudication

Ambiguity between this runbook and infra:council-comms resolves in favor of infra:council-comms for roster, model, and cap facts, and in favor of this runbook for collection procedure. Disputes escalate to the peer instance first, then to Max only for genuine forks.

## §I. Scenario Set

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01, §C]
    scenario: |
      id: E-01. trigger: Kimi review needed on an ai-market-backend SHA. pre_conditions: SHA fetched locally, exact review prompt prepared, review scoped within the cost cap. tool_or_endpoint: council_request(agent=kimi, mode=review, task=<review_prompt>, dispatch_sha=<SHA>, cwd=<backend_checkout>). argument_sourcing: task from exact gate/spec questions and changed files with read-only scope; cwd is the repo containing the SHA; review_sources does not satisfy the resolver. idempotency: IDEMPOTENT. expected_success: receipt with resolved SHA, preloaded context, complete coverage. expected_failures: dispatch_sha_invalid when cwd is omitted. next_step_success: collect the verdict and record per E-02. next_step_failure: pass cwd explicitly and re-dispatch.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, dispatch_sha, cwd]
        argument_values:
          agent: kimi
    weight: 0.09090909090909091
  - id: I-02
    type: operate
    refs: [E-02, F-04, G-04]
    scenario: |
      id: E-02. trigger: panel complete, gate outcome must be recorded. pre_conditions: complete valid panel, reviewer is not the builder. tool_or_endpoint: state_request(action=bq_update, bq_code=<code>, gate=<N>, status=<canonical>, note=<panel_refs>, session_id=<session>, gate_status_update=true, expected_version=<version>). argument_sourcing: expected_version from a fresh entity read; canonical status vocabulary; immutable panel references from the receipts. idempotency: IDEMPOTENT_WITH_KEY. expected_success: gateN.status flipped and verified by re-read. expected_failures: gate_status_not_flipped when gate_status_update is omitted. next_step_success: fold mandates if any. next_step_failure: repeat the bounded update with gate_status_update=true and a fresh expected_version.
    expected_answers:
      - kind: tool_call
        tool: state_request
        argument_keys: [action, bq_code, status, gate, note, session_id, gate_status_update, expected_version]
        argument_values:
          action: bq_update
          gate_status_update: true
    weight: 0.09090909090909091
  - id: I-03
    type: operate
    refs: [E-03, F-06, G-06]
    scenario: |
      id: E-03. trigger: MP build wanted while the peer session is live. pre_conditions: bus drained, no unacked peer claim, bounded task, absolute clean checkout, BQ code, and caller instance are known. tool_or_endpoint: peer_msg_send(to=<peer>, kind=claim, ref_entity=<entity>, body=<lane_claim>), then dispatch_mp_build(task=<bounded_build_task>, cwd=<absolute_repo>, bq_code=<code>, caller_instance=<self>, dispatch_class=structural) once the lane is known free. argument_sourcing: the claim body names the BQ and scope; follow-ups vary ref_entity because of silent dedupe; task comes from the approved BQ/spec; cwd from the verified isolated checkout; caller identity from the active registry session. idempotency: NOT_IDEMPOTENT. expected_success: dispatch without mp_busy and retain its task id. expected_failures: mp_lane_held, missing required task, stale base, or caller/schema mismatch. next_step_success: release status at completion. next_step_failure: wait for the lane-free status and verify git status before any redispatch.
    expected_answers:
      - kind: tool_call
        tool: peer_msg_send
        argument_keys: [to, kind, ref_entity, body]
        argument_values:
          kind: claim
      - kind: tool_call
        tool: dispatch_mp_build
        argument_keys: [task, cwd, bq_code, caller_instance, dispatch_class]
        argument_values:
          dispatch_class: structural
    weight: 0.09090909090909091
  - id: I-04
    type: isolate
    refs: [F-01, G-01, E-01]
    scenario: |
      id: F-01. trigger: a Kimi review of a backend commit fails immediately with an invalid-SHA error even though the SHA is valid and 40-hex. pre_conditions: dispatch args, the failing receipt, and the local checkouts are available. tool_or_endpoint: git cat-file -e on the SHA in each candidate repo plus inspection of the dispatch args. argument_sourcing: SHA from the failing dispatch; repo roots from the worktree list. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify as the cwd-resolution trap when the SHA exists in the backend checkout but the dispatch omitted cwd. expected_failures: patching the resolver as a workaround, or re-dispatching unchanged. next_step_success: apply G-01. next_step_failure: fetch the SHA first if it is genuinely absent locally.
    expected_answers:
      - kind: human_action
        verb: classify
        object: cwd-resolution trap on a non-default repo SHA
        target: G-01 re-dispatch with cwd
    weight: 0.09090909090909091
  - id: I-05
    type: isolate
    refs: [F-04, G-04, E-02]
    scenario: |
      id: F-04. trigger: the build-queue dashboard still shows the old gate status after a recording round that looked successful. pre_conditions: the BQ entity, the recording calls made, and the panel receipts are available. tool_or_endpoint: state_request(action=get, key=build:bq-*) comparing body.gateN.status against the recorded note. argument_sourcing: entity key from the BQ; expected status from the panel outcome. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify as the omitted-gate_status_update trap when the note is present but the leaf status never flipped. expected_failures: re-running the whole panel, or hand-editing the dashboard. next_step_success: apply G-04. next_step_failure: escalate to the peer if the entity version conflicts persist.
    expected_answers:
      - kind: human_action
        verb: compare
        object: body.gateN.status against the recorded panel note
        target: G-04 bounded gate-status update
    weight: 0.09090909090909091
  - id: I-06
    type: isolate
    refs: [F-05, G-05, E-03]
    scenario: |
      id: F-05. trigger: the peer never reacted to a follow-up bus message about an entity already discussed this cycle. pre_conditions: both message sends and the peer_messages table are inspectable. tool_or_endpoint: check the persisted rows for a new message id after the second send. argument_sourcing: the tuple (from, to, kind, ref_entity) from both sends. idempotency: READ_ONLY_DIAGNOSTIC. expected_success: classify as silent dedupe when the second send returned success but produced no new row. expected_failures: assuming the peer is ignoring the bus, or force-releasing peer-owned work. next_step_success: apply G-05. next_step_failure: raise a status message with a varied tuple and wait for the ack.
    expected_answers:
      - kind: human_action
        verb: classify
        object: silent dedupe on an identical message tuple
        target: G-05 varied resend
    weight: 0.09090909090909091
  - id: I-07
    type: repair
    refs: [G-02, F-02, E-01]
    scenario: |
      id: G-02. trigger: a Kimi 3-page delta review truncated before the verdict. pre_conditions: the truncated receipt, original task, repo root, SHA, and review scope are known. tool_or_endpoint: council_request(agent=kimi, mode=review, task=<same_review_prompt_with_summary_cap>, cwd=<repo>, dispatch_sha=<SHA>, max_tokens=20000). argument_sourcing: max_tokens from this runbook; task, cwd, SHA, and scope unchanged from the original dispatch except the explicit summary word cap. idempotency: IDEMPOTENT. expected_success: terminal verdict present with complete coverage and cost within the cap. expected_failures: hand-repairing the truncated output, or narrowing coverage to force completion. next_step_success: record per E-02. next_step_failure: two malformed terminal attempts fail closed; split the review scope instead.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, cwd, dispatch_sha, max_tokens]
        argument_values:
          agent: kimi
    weight: 0.09090909090909091
  - id: I-08
    type: repair
    refs: [G-03, F-03, E-02]
    scenario: |
      id: G-03. trigger: a CC review round was rejected by the envelope parser because prose preceded the JSON block. pre_conditions: the raw terminal message confirms a verdict exists inside prose, and the original repo root and SHA are known. tool_or_endpoint: council_request(agent=cc, mode=review, task=<same_review_prompt_with_raw_json_only_instruction>, cwd=<repo>, dispatch_sha=<SHA>). argument_sourcing: the same review scope, cwd, and SHA as the rejected round; task adds raw JSON with no preamble or markdown fences. idempotency: IDEMPOTENT. expected_success: structured_payload parses on the fresh receipt and the verdict records cleanly. expected_failures: scraping the verdict out of prose, or treating the parse failure as a reviewer rejection. next_step_success: record per E-02. next_step_failure: fail closed and escalate to the peer for adjudication.
    expected_answers:
      - kind: tool_call
        tool: council_request
        argument_keys: [agent, mode, task, cwd, dispatch_sha]
        argument_values:
          agent: cc
    weight: 0.09090909090909091
  - id: I-09
    type: evolve
    refs: [§H, E-02]
    scenario: |
      id: H-01. trigger: a proposal lets a two-of-three panel record a security-class gate when the third voter's provider is down. pre_conditions: the proposed rule text and the affected gate classes are described. tool_or_endpoint: runbook and gate-recording contract patch. argument_sourcing: current invariants from §H.1; quorum rule from the security gate contract. idempotency: CHANGE_REVIEW_REQUIRED. expected_success: classify as BREAKING because it changes the required voter set for a gate class. expected_failures: calling it operational resilience, or shipping it as a temporary exception without the amendment gate. next_step_success: route through full Council review plus Max approval. next_step_failure: keep the unanimous requirement unchanged.
    expected_answers:
      - kind: classification
        label: BREAKING
    weight: 0.09090909090909091
  - id: I-10
    type: evolve
    refs: [§H, E-01]
    scenario: |
      id: H-02. trigger: a proposal raises the default Kimi review token budget and turn protocol for all delta reviews. pre_conditions: the proposed defaults and the cost-cap impact are described. tool_or_endpoint: dispatch-default change in the review harness configuration. argument_sourcing: current defaults from this runbook and infra:council-comms; caps from the reviewer entries. idempotency: CHANGE_REVIEW_REQUIRED. expected_success: classify as REVIEW because it changes per-reviewer dispatch defaults without touching quorum or fail-closed behavior. expected_failures: treating it as SAFE because it is only a budget, or letting it silently raise spend past the cap. next_step_success: review the change and update this runbook plus infra:council-comms together. next_step_failure: keep current defaults.
    expected_answers:
      - kind: classification
        label: REVIEW
    weight: 0.09090909090909091
  - id: I-11
    type: ambiguous
    refs: [E-03, F-06, G-06]
    scenario: |
      id: AMB-01. trigger: an MP dispatch reports running past 300 seconds with no receipt update, while the peer bus shows no lane claim and the target repo shows a fresh unexplained commit. pre_conditions: dispatch receipt, peer bus history, and git log of the target repo are available. tool_or_endpoint: compare the dispatch task id, peer claims, and git status plus git log timestamps. argument_sourcing: task id from the receipt; claims from the bus; commits from the repo. idempotency: READ_ONLY_DIAGNOSTIC until the root cause is identified. expected_success: hold three hypotheses open - the task silently delivered and committed, the peer built without a claim, or a stale task record is masking a failure - and pick the evidence-backed one before acting. expected_failures: blind redispatch that double-lands a build, force-releasing a live peer claim, or reverting the unexplained commit without attribution. next_step_success: attribute the commit, reconcile the task record, and only then decide on redispatch. next_step_failure: leave the lane held and escalate to the peer for joint reconciliation.
    expected_answers:
      - kind: human_action
        verb: triage
        object: silent MP task against peer claims and repo ground truth
        target: evidence-backed redispatch decision
    weight: 0.09090909090909091
```

## §J. Lifecycle

Initial registration at S1408. No harness run has been executed against this scenario set yet.

```yaml lifecycle
last_refresh_session: S1408
last_refresh_commit: 601bf93
last_refresh_date: 2026-07-30T16:30:00Z
owner_agent: mars
refresh_triggers:
  - roster, model, or cap changes in infra:council-comms
  - dispatcher resolver or envelope-parser changes in koskadeux-mcp
  - peer-bus dedupe or claim protocol changes
  - runbook-lint or runbook-harness schema changes
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: null
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1408 / 2026-07-30T16:45:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```

The §K block records the strict-lint result; harness state is authoritative in §J.
