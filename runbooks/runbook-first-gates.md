---
runbook_id: runbook-first-gates
domain: runbook-operations
status: ACTIVE
authoritative_for:
  - topic: runbook-first-session-planning
    section: §E. Operate
  - topic: runbook-impact-and-obligations
    section: §C. Architecture & Interactions
  - topic: runbook-content-activation
    section: §E. Operate
aliases:
  - runbook-maintenance
  - runbook-authoring
  - update-runbook-after-work
  - documentation-obligation
  - runbook-close
  - no-runbook-update-needed
  - read-runbooks-before-starting-work
  - preserve-successful-build
  - old-runbook-obligation
error_signatures:
  - signature: runbook_library_unavailable
    section: §F. Isolate
  - signature: runbook evidence unavailable
    section: §F. Isolate
  - signature: runbook_context_delivery_unavailable
    section: §F. Isolate
  - signature: runbook_impact_evidence_unavailable
    section: §F. Isolate
  - signature: runbook obligation due before behavior change
    section: §F. Isolate
  - signature: candidate ref missing or deleted
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: mars
last_verified_at: 2026-08-02
system_name: runbook-first-gates
purpose_sentence: Keep operational guidance accurate, findable, and useful by delivering it automatically before work and deriving maintenance obligations from backend-observed evidence.
owner_agent: mars
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Current procedure for automatic runbook delivery, evidence-based maintenance obligations, work preservation, and separate content and activation commits.
linter_version: 1.0.0
---

# Runbook-First Gates

## §A. Header

The first accepted `kd_session_plan` response automatically contains the
runbook context selected for the task. Submit ordinary objectives and a routing
strategy; do not supply a filename, section, citation, consultation ID,
attestation, waiver, or desired documentation outcome. Read the delivered
context before calling work tools. If it changes the approach, amend the plan
before acting. Child build, author, and review dispatches receive their relevant
context automatically through the shared dispatch boundary.

A runbook is a map to evidence, not evidence that its own claims are true.
Verify every load-bearing instruction against the source that owns it: exact
code and tests, a committed schema or migration, deployed configuration
readback, provider state, or a safe live probe. Preserve the commit, resource
identity, and result needed to repeat the check. An `ACTIVE` catalog entry means
that its bytes passed integrity checks; it does not make an operational claim
true or authorize an action. Pending or archived search results are discovery
leads only, and archived results are historical-only.

Runbook maintenance is decided from server-observed work, not from agent prose.
The backend distinguishes changing an operating contract from executing the
current contract. Source, schema, configuration, policy, deployment, tool, and
process changes are `REQUIRED` by default. A known provider-observed routine
transaction—such as recording a message, event, review, queue transition, or
business record under unchanged code and configuration—is `NOT_REQUIRED`.
Unknown mutations are `UNCERTAIN`, not silently harmless. Tests-only,
deterministically generated, and formatting-only repository changes may be
`NOT_REQUIRED` only when the backend proves that exact class; a passing test or
build does not make a source/process diff behavior-preserving. A successful
repository-writing action must still leave a backend-observed remote
candidate ref created or updated during the session; a default branch head,
local dirty tree, local commit, or claimed SHA does not preserve work. Provider,
deployment, configuration, and database mutations likewise require trusted
backend or provider evidence.

`REQUIRED` without a verified update and semantically `UNCERTAIN` work create or
refresh one visible, deduplicated, nonblocking obligation. They do not prevent a
truthful close and never justify filler. A useful runbook update satisfies an
obligation only after the backend verifies its exact content and activation
commits, changed paths and sections, claim-level owning evidence, independent
truth-focused review when required, remote ancestry, and live activation. A
signed `approved` string and structurally valid bytes are insufficient: every
material current-state claim must bind a typed reproducible observation or be
marked `UNKNOWN` with an owner and evidence gap. Satisfaction revalidates the
exact current served source bytes and catalog identity; a later edit, revert,
or replacement revokes coverage unless the reviewed claim and byte identities
still match. A runbook change is not itself a new obligation merely because it
writes the runbooks repository.

An OPEN obligation does constrain the next change to the same component. The
backend refuses a later behavior-changing action until the obligation is
satisfied. Read/search/test diagnostics and runbook remediation, review,
coverage, and activation remain allowed. Urgent continuation requires a fresh,
one-use Max authorization bound to the exact obligation and action. This keeps
close recoverable without allowing documentation debt to compound forever.

The retired caller-attestation gate is physically absent. There is no local
SQLite or HMAC close authority, warning-mode selector, emergency shell fallback,
or configuration switch that can restore it. A failed immutable-library fetch,
trusted evidence collector, or close transaction is an infrastructure failure:
stop and retry after repair rather than falling back to stale content or a
caller-authored declaration.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Immutable all-corpus search with separate ACTIVE candidates and discovery leads | SHIPPED | `runbook_tools/catalog/search.py` | Catalog search, validator, and fixed-Git poison tests | 2026-08-02 |
| Automatic first-plan context before plan and authority writes | PLANNED | `koskadeux-mcp/tools/runbook_delivery.py` | Gateway exact-retry, poison-environment, zero-prior-write, and response-budget tests | 2026-08-02 |
| Automatic child context through every dispatch route | PLANNED | `koskadeux-mcp/tools/agents.py` | Direct/public/indirect dispatch route-matrix tests | 2026-08-02 |
| Backend-owned session baseline, action evidence, impact evaluation, obligations, and close transaction | PLANNED | `ai-market-backend/app/services/runbook_close_v2_service.py` | Collector poison, crash/retry, remote-ref, obligation, and transaction tests | 2026-08-02 |
| Signed coverage receipt and monotonic exact-pin activation | PLANNED | `ai-market-backend/app/services/runbook_close_v2_service.py` | Signature, replay, ancestry, section, independent-review, and activation-CAS tests | 2026-08-02 |
| Legacy gate, debt, waiver, local journal, and fallback removal | PLANNED | `koskadeux-mcp/tools/session.py` | No-old-symbol, no-old-file, launcher, restart, and fresh-client schema tests | 2026-08-02 |

`PLANNED` in the S1413 rows means the reviewed branch is not operating authority
yet. Before this document's activation pin is served, change each such row to
`SHIPPED` and replace its verification claim with the exact reviewed
commit, deployment, and test evidence. Never serve a runbook that describes a
branch as if it were already production behavior.

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Immutable corpus reader | `runbook_tools.catalog.search:search_catalog_delivery` | Exact Git commit, catalog, manifest, inventory, source blobs, and canonical response bytes | Gateway first-plan and dispatch delivery | Uses fixed Git execution and a validated full-SHA worktree. ACTIVE and discovery lanes remain distinct even when merged by relevance rank. |
| First-plan delivery | `kd_session_plan` gateway handler | Backend activation/open-obligation snapshot and immutable delivery identity | Corpus reader, paginated exact section/full-runbook fetch, and canonical plan transition | Searches objectives plus relevant OPEN obligation subjects. One ordinary request returns accepted plan plus useful context and continuation; unchanged retry is byte-identical. |
| Child delivery | Shared Council/agent dispatch provider boundary | Parent session, exact task digest, dispatch identity, and immutable delivery identity | Every public, direct, and indirect child launch | Context is injected by the provider boundary. Callers cannot supply or suppress runbook references. |
| Session and action evidence | Backend runbook close-v2 collectors and service | Session activation/obligation snapshot, lazy action-scoped Git/provider baselines, intents/outcomes, provider audit evidence | GitHub, Railway, database/outbox, configuration, deploy, and other registered providers | Open does not scan every repository. First action intent captures the exact target baseline; PREPARE/COMMIT recheck only bound resources. Gateway and agent fields are hints only. |
| Impact evaluator | Backend runbook close-v2 evaluator | Static action registry, observed evidence, component ownership, behavior roots | Close PREPARE | Produces backend-owned `REQUIRED`, `NOT_REQUIRED`, or `UNCERTAIN`. Passing tests or builds cannot erase a source/process behavior change. |
| Close transaction | Backend PREPARE and COMMIT service | Canonical session, immutable close request, evidence freeze, handoff, obligations, outbox, committed receipt | Trusted collectors and gateway close adapter | Collector outage writes nothing. COMMIT revalidates remote/provider truth under lock and atomically closes even when semantic obligations remain OPEN. |
| Obligation ledger | Backend close-v2 obligation model | Stable component/contract/subject/evidence identity and occurrence rows | Action intent gate, evaluator, coverage verifier, close receipt | Identity excludes volatile session IDs and timestamps. Close is nonblocking, but the next behavior-changing action for that component waits for satisfaction or exact Max authorization. |
| Coverage and activation | Backend coverage verifier, signer, and activation service | Signed claim/evidence set, reviewer receipt, exact current C/M bytes, monotonic active pin | GitHub, owning providers, and public cutover status | Structural approval cannot certify operational truth. Satisfaction rechecks typed evidence and current served bytes; authors and the gateway cannot mint or select trust. |
| Legacy gate retirement | Gateway launcher, public schemas, and absence tripwires | No compatibility authority or local fallback state | Backend signed cutover status and frozen legacy database state | Startup validates the signed status unconditionally. Source, schema, storage, and selector tests prove the retired implementation is physically absent. |

### Decision boundary

The agent collects evidence and writes useful guidance; it does not select the
outcome that makes close succeed.

- `REQUIRED`: update the existing runbook whose declared scope owns the changed
  behavior. Create a new canonical document only when no existing identity owns
  that scope.
- `NOT_REQUIRED`: do not create a documentation-only commit. This outcome is
  valid only for backend-observed routine execution under an unchanged contract
  or an exactly verified tests-only, generated, formatting, or other explicit
  no-behavior class.
- `UNCERTAIN`: identify the missing owning evidence and allow the canonical
  obligation to remain open. Never translate uncertainty into no-change prose.

Search the complete pinned corpus before choosing an edit target. Merge ACTIVE
candidates and discovery leads by their shared relevance rank. If the globally
best result is discovery-only, `authoritative_gap` remains true even when a
weaker ACTIVE result exists. Use the lead to find owning evidence; never copy it
into current operating guidance without verification.

Runbook content and activation have separate identities. Content commit C
contains only the grounded document set. Its direct child M contains only
`CORPUS-MANIFEST.yaml`, `CATALOG.json`, `TOPIC-ROUTER.md`, and `README.md`.
The prior M remains served until the backend verifies C, M, review and evidence,
then atomically advances the exact pin.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Task agent | Read automatically delivered context, verify instructions, perform scoped work, and preserve remote candidate refs | First `kd_session_plan`, normal work tools, automatic child delivery | User-authorized task scope; no documentation-decision authority | COMPLETE |
| Runbook author | Correct an owned page or draft a unique missing scope | Full-corpus search, `runbook-new`, editor, `runbook-lint` | Runbook source content only; cannot mint evidence, review, or activation | COMPLETE |
| Independent reviewer | Challenge every material operational claim, its typed evidence, and explicit UNKNOWN gaps | Exact C claim set and backend review receipt | Read-only and independent of the author when required; cannot approve unsupported prose | COMPLETE |
| Backend evaluator | Observe work, classify impact, maintain obligations, verify coverage, and commit close | Close-v2 service, collectors, database functions, GitHub and provider APIs | Narrow service role; no migration-owner credential at runtime | COMPLETE |
| Gateway | Deliver immutable context and transport backend results | Plan, dispatch, close, and status adapters | Transport only; no local authority or fallback store | COMPLETE |
| Max | Authorize an exact high-risk deferral or genuine policy fork | Expiring obligation-bound authorization | Named decision only; no inferred approval | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: A session has opened and the agent is declaring the task before doing work.
  pre_conditions: [authenticated_session_open, first_plan_not_yet_accepted, objectives_known]
  tool_or_endpoint: kd_session_plan(session_id=<session>, objectives=<ordinary objectives>, delegation_strategy=<routing>, work_type=<class>, tool_budget=<estimate>)
  argument_sourcing: {objectives: use the assigned outcome without adding filenames citations or desired impact decisions, routing: describe direct work and bounded delegation, class: derive from the real work rather than lowering risk, estimate: use the expected tool count}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: exact canonical request digest plus session plan revision
  expected_success: {shape: one accepted-plan response containing immutable context for objectives and relevant OPEN obligations plus exact delivery identity and bounded continuation/fetch controls, verification: read quick-start stop and verify guidance fetch complete owning sections when required page every relevant obligation and preserve catalog/response digests before work tools}
  expected_failures: [{signature: runbook_library_unavailable, cause: the exact catalog manifest inventory source objects runtime contract or serializer could not be verified}, {signature: plan request changed after retry, cause: a retry did not reproduce the original canonical request}]
  next_step_success: Read the context, verify load-bearing guidance, and amend the plan before acting if the evidence changes the approach.
  next_step_failure: Stop; repair the immutable delivery dependency or retry the byte-identical request without supplying caller evidence.
- id: E-02
  trigger: A build, author, or review child is needed.
  pre_conditions: [parent_plan_accepted, child_task_bounded, target_identity_known]
  tool_or_endpoint: the ordinary Council or agent dispatch call without runbook_refs
  argument_sourcing: {task: derive from the approved scope and verified evidence, target: use the exact repository branch commit or artifact required by the dispatch contract, runbook_context: do not supply it because the shared provider derives and injects it}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: parent session plus canonical child task and target digest
  expected_success: {shape: child receives complete pinned context before work instructions through every dispatch route, verification: inspect the dispatch receipt and child envelope identity rather than trusting caller prompt text}
  expected_failures: [{signature: runbook child delivery unavailable, cause: the provider could not verify or fit the immutable context envelope}]
  next_step_success: Let the child verify the supplied guidance and execute only its bounded task.
  next_step_failure: Do not launch the child through a direct or legacy path; repair the common provider boundary.
- id: E-03
  trigger: Work may modify a repository or another durable system.
  pre_conditions: [action_registered_before_execution, component_and_target_resolved, user_authority_covers_the_action, no_due_component_obligation_blocks_behavior_change]
  tool_or_endpoint: normal registered work tool; repository writers must publish a session-bound candidate ref
  argument_sourcing: {intent: derive from the exact backend action registry and canonical arguments and let it capture the target-specific baseline, repository_candidate: create or update a dedicated remote candidate ref after that action baseline, provider_identity: use the backend-owned actor and audit identity}
  idempotency: NOT_IDEMPOTENT
  expected_success: {shape: backend-observed intent and outcome plus remote ref or provider audit evidence sufficient to recover the work, verification: query backend evidence and independently resolve the remote candidate rather than relying on local status or agent prose}
  expected_failures: [{signature: runbook obligation due before behavior change, cause: this component has an OPEN obligation from prior observed work}, {signature: candidate ref missing or deleted, cause: repository-writing work has no backend-observed recoverable remote ref}, {signature: trusted provider evidence unavailable, cause: the action outcome cannot be observed authoritatively}]
  next_step_success: Keep the candidate ref until canonical merge or explicit recoverable retirement and continue verification.
  next_step_failure: Stop further mutation, preserve or republish the candidate if possible, and repair the trusted collector before close.
- id: E-04
  trigger: The requested work is complete and the session is ready to close.
  pre_conditions: [peer_inbox_drained, owned_work_preserved, final_remote_and_provider_state_stable, handoff_prepared]
  tool_or_endpoint: kd_session_close(session_id=<session>, instance=<self>, summary=<result>, reason=<reason>, handoff_content=<handoff>)
  argument_sourcing: {summary: state the verified outcome without a documentation decision, reason: use the real close reason, handoff: include recoverable refs open obligations and next safe action; omit runbook_exit impact claims citations waivers and debt IDs}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: backend close_request_id and immutable canonical request digest
  expected_success: {shape: signed immutable COMMITTED receipt with typed obligation outcomes, verification: read the backend receipt and public status; confirm session handoff obligations and outbox committed together}
  expected_failures: [{signature: runbook evidence unavailable, cause: a trusted GitHub Railway database or provider collector failed before PREPARE}, {signature: remote state changed during close, cause: COMMIT revalidation differs from the frozen PREPARE evidence}]
  next_step_success: Report the committed result and any visible nonblocking obligation; never manufacture a runbook edit after close.
  next_step_failure: Leave the session open and retry only after the mechanical evidence or provider outage is resolved; a failed PREPARE creates no freeze obligation or close writes.
- id: E-05
  trigger: A REQUIRED or UNCERTAIN obligation needs a useful grounded runbook correction.
  pre_conditions: [canonical_obligation_visible, full_corpus_searched, owning_document_or_unique_gap_identified, typed_claim_level_evidence_available]
  tool_or_endpoint: edit the owning runbook or runbook-new <id>; then runbook-lint <changed path> --mode strict --format github
  argument_sourcing: {target: use the existing authoritative scope when one exists, claims: bind each material current-state statement to an exact typed owning observation and mark unsupported detail UNKNOWN with owner and evidence gap, metadata: use truthful current ownership aliases topics signatures and verification date, secrets: never place credentials or values in content}
  idempotency: NOT_IDEMPOTENT
  expected_success: {shape: grounded source-only content commit C plus a closed material-claim evidence set with no generated identity edits, verification: exact C diff contains only the intended operational document set and every load-bearing claim is reproducible from its bound observation}
  expected_failures: [{signature: refusing to overwrite existing file, cause: the proposed identity already has a canonical owner}, {signature: deterministic conformance check failed, cause: structure placeholders references or scenario forms are invalid}]
  next_step_success: Obtain independent truth-focused review of the exact claim/evidence set and prepare mechanical activation child M.
  next_step_failure: Correct the existing owner or keep the obligation open; do not create a competing alias or unsupported detail.
- id: E-06
  trigger: Reviewed content commit C is ready for mechanical activation.
  pre_conditions: [HEAD_equals_full_C, worktree_clean, typed_claim_evidence_and_truth_review_available, prior_live_pin_known]
  tool_or_endpoint: python -m runbook_tools.corpus_manifest --refresh-from <full-C-sha>; then runbook-catalog generate
  argument_sourcing: {full_C: require exact checked-out 40-hex commit, protected_adjudication: use backend-verified evidence and review rather than author prose, generated_outputs: accept only repository-tool output, old_pin: read from signed public cutover status}
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: full C SHA plus coverage evidence fingerprint and prior activation pin
  expected_success: {shape: direct child M changing only CORPUS-MANIFEST.yaml CATALOG.json TOPIC-ROUTER.md and README.md plus a backend-signed claim-level coverage receipt and monotonic exact-M activation, verification: run manifest catalog selection lint full tests exact-M validation representative search remote ancestry signature current-served-byte claim-evidence freshness and public cutover-status checks}
  expected_failures: [{signature: refresh source document set mismatch, cause: C and the manifest source inventory disagree}, {signature: activation compare-and-swap lost, cause: another valid activation moved the live pin first}]
  next_step_success: Confirm ordinary task-language queries find understandable current guidance and the obligation becomes satisfied without creating a recursive runbook obligation.
  next_step_failure: Keep the previous M serving; never amend published C/M identities or bypass evidence review signature or compare-and-swap checks.
```

Representative exact-M searches must cover at least:

```text
update the runbook after completing work
I changed code but I do not know whether documentation needs updating
the previous session left an old runbook obligation
what should an agent read before starting a task
how do I preserve a successful build before session close
activate a reviewed runbook content commit
```

The intended ACTIVE procedure must appear in the useful top results without the
agent knowing its filename. Inspect the excerpt and `authoritative_gap`, not just
the title. Misleading aliases added only to win ranking are a defect.

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | The accepted first plan has no understandable quick-start/stop/verify guidance, omits relevant obligations, cannot fetch the complete owning section, is truncated, or changes on an unchanged retry. | Exact corpus/runtime validation failed, obligation paging or bundle/section fetch is disabled, a response budget was violated, cache identity is incomplete, or the retry key excludes a semantic field. | Compare request bytes/digests, objective and obligation queries, plan revision, page cursors, fetch identities, catalog/manifest/inventory/source identities, response byte count/digest, dependency lock and import origins. | G-01 | CONFIRMED |
| F-02 | The best result is discovery-only or an ACTIVE instruction conflicts with current ground truth. | No current ACTIVE owner exists, ranking surfaced historical terminology, or an ACTIVE page is stale. | Merge both result lanes by relevance rank, inspect `authoritative_gap` and historical flags, then reproduce the claim from its owning source. | G-02 | CONFIRMED |
| F-03 | A good build exists locally but close cannot prove it is recoverable. | No session-bound candidate ref was published, the ref was deleted, only default head was observed, or the wrapper cleaned an unpreserved worktree. | Compare the backend session-open remote inventory with current heads/tags and provider audit history; independently resolve the candidate commit and branch. | G-03 | CONFIRMED |
| F-04 | Close cannot collect action-bound GitHub, Railway, database, or provider evidence. | Trusted collector outage, credential scope failure, target-specific rate limit, bound remote drift, or runtime DB role defect. Unrelated repositories/providers must not be queried or block. | Preserve the typed collector failure, inspect the exact action-bound resource set, and prove the failed attempt wrote no freeze, obligation, occurrence, handoff, receipt, outbox, or close state. | G-04 | CONFIRMED |
| F-05 | An agent is writing citations, waivers, no-change prose, or unrelated documentation solely to make close pass. | Caller text is still being treated as impact authority or a legacy input/fallback remains callable. | Inspect the live tool schema, gateway files and symbols, backend evaluator inputs, and candidate diff; determine whether any author-controlled field changes the outcome. | G-05 | CONFIRMED |
| F-06 | An obligation remains OPEN after an update, or coverage remains SATISFIED after the reviewed bytes were later changed. | Claim evidence is absent/stale, structural approval replaced truth review, current served bytes differ, C/M ancestry or sections fail, or the live pin has not advanced. | Verify typed claim observations, reviewer claim-set digest, exact current served source/catalog bytes, remote C/M direct-child relationship, activation status, and obligation fingerprint. | G-06 | CONFIRMED |
| F-07 | Content C contains generated identities, M contains operational prose, or C was amended after review. | The content/activation boundary was skipped or a published identity was rewritten. | Compare exact parentage and `git diff --name-only` for C and M with the allowlists in §C and §E. | G-07 | CONFIRMED |
| F-08 | A retired field, file, table, selector, or fallback can still reactivate the old gate. | The rollout disabled rather than deleted compatibility code, launcher behavior is conditional, or a database writer remains reachable. | Run no-old-symbol/file/schema tests; inspect a freshly listed client schema, unconditional startup status check, runtime grants, and failed-status launch behavior. | G-08 | CONFIRMED |
| F-09 | A later behavior-changing action is refused because the component has an OPEN runbook obligation. | Prior REQUIRED or semantic UNCERTAIN work closed truthfully but its useful documentation gap remains unsatisfied. | Read the canonical obligation, due trigger, component and evidence fingerprint; verify the proposed action is not a read/search/test or runbook-remediation operation. | G-09 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: First-plan delivery
  root_cause: The immutable corpus runtime request identity or complete response could not be reproduced.
  repair_entry_point: gateway runbook delivery adapter and pinned runbook-tools runtime
  change_pattern: Keep the session non-operational; repair the exact package lock import origin catalog object budget or request-digest defect; rerun poison and byte-identical retry tests from a clean process.
  rollback_procedure: Keep the previous exact M and gateway deployment serving only if they remain the signed active pair; never select stale checkout content or caller references.
  integrity_check: One ordinary request returns useful canonical objective/obligation context before authority writes complete owning sections remain fetchable with bounded pagination all relevant obligations are pageable and an unchanged lost-response retry returns identical bytes.
- id: G-02
  symptom_ref: F-02
  component_ref: Immutable corpus reader
  root_cause: Search found only a discovery lead or current guidance failed owning-source verification.
  repair_entry_point: owning code schema configuration provider state and runbook source content
  change_pattern: Use the lead to locate ground truth, correct the existing owner or draft the unique missing scope in C, and activate only through verified M.
  rollback_procedure: Stop using the disputed instruction and keep the obligation visible while the gap is unresolved.
  integrity_check: A context-free agent can find the corrected section with task language and reproduce every load-bearing claim independently.
- id: G-03
  symptom_ref: F-03
  component_ref: Session and action evidence
  root_cause: Repository-writing work was not durably published under a backend-observed session-bound candidate ref.
  repair_entry_point: structural build wrapper and GitHub remote-ref collector
  change_pattern: Before cleanup publish or recover the exact commit to an allowed candidate branch update it after later writes and retain the ref until merge or explicit recoverable retirement; make terminal wrapper cleanup conditional on verified preservation.
  rollback_procedure: If the original worktree still exists stop cleanup and preserve it; otherwise recover from the wrapper artifact or remote object before continuing.
  integrity_check: Backend remote enumeration proves the created or updated ref and exact commit relative to the session-open inventory; deleted and default-head-only poison cases fail.
- id: G-04
  symptom_ref: F-04
  component_ref: Close transaction
  root_cause: A trusted collector or least-privilege runtime boundary cannot establish mechanical truth.
  repair_entry_point: named backend collector credential route or database role
  change_pattern: Repair the read scope or provider outage and rerun PREPARE from the still-open session; keep all transaction and obligation tables unchanged on each failed attempt.
  rollback_procedure: No semantic rollback is required because the failed PREPARE must have made zero writes; revoke any accidentally broadened credential.
  integrity_check: Trusted evidence succeeds under the narrow runtime identity and crash probes still show zero partial state.
- id: G-05
  symptom_ref: F-05
  component_ref: Impact evaluator
  root_cause: A caller-controlled declaration retired compatibility path or overbroad routine-action rule can influence impact or close.
  repair_entry_point: gateway public schemas handlers launcher and backend evaluator boundary
  change_pattern: Delete the field path store and selector; derive outcomes only from the static backend registry and observed evidence; require operating-contract changes by default classify known unchanged-contract routine transactions as NOT_REQUIRED and keep unknown mutations UNCERTAIN.
  rollback_procedure: Keep activation blocked; do not restore the retired implementation even as an emergency fallback.
  integrity_check: Poisoned agent claims do not change outcome and no fresh client or filesystem/runtime path exposes the retired contract.
- id: G-06
  symptom_ref: F-06
  component_ref: Coverage and activation
  root_cause: The candidate does not bind every material claim to trusted evidence and current served bytes or has not become the exact live pin.
  repair_entry_point: backend coverage verifier reviewer receipt and activation service
  change_pattern: Correct unsupported claims or mark them UNKNOWN bind fresh typed observations obtain truth-focused review derive a new immutable C and direct child M and let the backend reverify current served bytes remote ancestry sections and activation.
  rollback_procedure: Leave the obligation OPEN and the previous M served; never edit or reuse a signed receipt for different bytes.
  integrity_check: Public status selects exact M and the signed coverage receipt independently resolves every obligation component material-claim evidence current source/catalog byte identity and section hash.
- id: G-07
  symptom_ref: F-07
  component_ref: Coverage and activation
  root_cause: Source and generated identities were mixed or immutable reviewed commits were rewritten.
  repair_entry_point: C and M commit boundary
  change_pattern: Recreate a clean source-only C then generate a new direct child M from exact C without amending any reviewed or published object.
  rollback_procedure: Keep the previous valid M active and discard the malformed unpublished candidate branch.
  integrity_check: C excludes all four generated identity paths M changes only those four paths and M has exact C as its parent.
- id: G-08
  symptom_ref: F-08
  component_ref: Legacy gate retirement
  root_cause: Compatibility code or authority remained selectable after the one-way cutover.
  repair_entry_point: gateway launcher schemas session dispatch close modules and backend legacy-state migration
  change_pattern: Remove the path physically add an absence tripwire make public signed status validation unconditional and preserve the database freeze while moving forward only.
  rollback_procedure: Roll back to a known-good version-2 deployment that still honors the freeze; never deploy or select the retired gate.
  integrity_check: Source AST filesystem schema database-role fresh-client and failed-status-startup tests all prove the old gate cannot execute or reappear.
- id: G-09
  symptom_ref: F-09
  component_ref: Obligation ledger
  root_cause: The due trigger correctly prevents another behavior-changing action from compounding an unresolved documentation gap.
  repair_entry_point: owning runbook content coverage review and activation flow
  change_pattern: Use allowed diagnostics to ground the gap complete E-05 and E-06 and retry only after backend satisfaction; for a genuine emergency obtain a fresh one-use Max authorization bound to this exact obligation and action.
  rollback_procedure: Keep the new behavior-changing action blocked; close and ordinary read/remediation work remain available.
  integrity_check: Satisfaction resolves exact obligation component subject and evidence fingerprint or the authorization verifies exact action once and cannot replay.
```

## §H. Evolve

### §H.1 Invariants

- One ordinary first-plan call supplies complete immutable context before the
  agent uses work tools or the system writes plan/authority state.
- Every child receives task-relevant context through the common provider
  boundary; caller fields neither create nor suppress it.
- The backend, not gateway or agent prose, owns baselines, observations, impact,
  obligations, coverage, close, and activation. It distinguishes routine
  execution from changing the operating contract without trusting caller labels.
- Every repository-writing result has a backend-observed recoverable remote
  candidate ref; default head and local state are insufficient.
- Trusted collector failure causes zero close-side writes. Semantic uncertainty
  creates an OPEN nonblocking obligation and still permits atomic COMMIT.
- An OPEN obligation blocks the next behavior-changing action for its component,
  while diagnostics and documentation remediation remain possible.
- Runbook source C and activation M stay separate and immutable. Catalog
  integrity is never semantic or action authority.
- The legacy gate and every route that could restore it remain physically
  absent after cutover.

### §H.2 BREAKING predicates

A change is BREAKING if it admits caller-authored impact/evidence, weakens
trusted collection or remote preservation, blocks truthful close on semantic
uncertainty, permits partial close writes, merges C and M, lets discovery text
authorize action, restores a legacy path, or makes validation fail open.

### §H.3 REVIEW predicates

Review changes to corpus selection, ranking, budgets, runtime locks, plan or
dispatch delivery identity, action registry classifications, collectors,
component ownership, evaluator rules, obligation identity, coverage evidence,
signatures, close transaction boundaries, database grants, or activation.

### §H.4 SAFE predicates

A spelling or grounded example correction is SAFE only when it changes no
scope, selection/ranking behavior, evidence meaning, action classification,
obligation, transaction, signature, or activation behavior. Source byte changes
still use C then M.

### §H.5 Boundary definitions

#### module

Immediate packages below `runbook_tools/`, the gateway delivery/dispatch/close
adapters, and backend close-v2 service, collector, evaluator, model, schema, and
route packages are modules for this system.

#### public contract

Public contracts include plan/dispatch/close schemas and typed results, the
signed cutover status, action registry, obligation and coverage receipt shapes,
catalog/search response shapes and digests, corpus manifest, runtime lock, and
the C-to-M activation sequence.

#### runtime dependency

Runtime dependencies include the exact hash-locked Python interpreter and
packages used by immutable search, backend PostgreSQL, the GitHub and Railway
read collectors, the gateway/backend authenticated channel, and the Ed25519
verification keys. Ambient imports and local checkouts are not dependencies.

#### config default

There is no configuration default that restores legacy behavior. Unknown
mutations default `UNCERTAIN`, trusted evidence fails closed mechanically, and
the previous validated version-2 M remains active until a monotonic successor
passes verification.

### §H.6 Adjudication

Use exact deployed code, database schema and grants, signed status, remote Git
and provider state, immutable corpus identities, and reproducible receipts.
When evidence conflicts, keep the semantic result `UNCERTAIN`, preserve work,
and escalate the specific missing owner or policy decision. Max resolves genuine
forks explicitly; no agent infers approval or invents a fact.

## §I. Operational Examples

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: A new agent knows the task objective but does not know any runbook filename.
    expected_answers:
      - {kind: human_action, verb: submit, object: ordinary objective-bearing first plan without runbook fields, target: kd_session_plan}
  - id: I-02
    type: ambiguous
    refs: [§C]
    scenario: Tests pass and the agent believes a source refactor changed no documented behavior, but backend evidence is incomplete.
    expected_answers:
      - {kind: classification, label: UNCERTAIN_WITH_ONE_NONBLOCKING_OBLIGATION}
  - id: I-03
    type: isolate
    refs: [F-03, G-03]
    scenario: A build produced a valuable local commit but published no session-bound candidate branch.
    expected_answers:
      - {kind: human_action, verb: preserve, object: exact commit on a backend-observed remote candidate ref, target: allowed repository branch}
  - id: I-04
    type: isolate
    refs: [F-05, G-05]
    scenario: Close would pass if the agent writes a sentence saying no runbook update is required.
    expected_answers:
      - {kind: classification, label: CALLER_PROSE_IS_NOT_EVIDENCE}
  - id: I-05
    type: isolate
    refs: [F-07, G-07]
    scenario: A proposed content commit changes a runbook plus CATALOG.json and README.md.
    expected_answers:
      - {kind: classification, label: RECREATE_SOURCE_ONLY_C_THEN_DIRECT_CHILD_M}
  - id: I-06
    type: repair
    refs: [G-06]
    scenario: A prior-session obligation has a reviewed runbook correction but remains open.
    expected_answers:
      - {kind: human_action, verb: verify, object: exact C M section evidence reviewer receipt and live activation binding, target: backend coverage service}
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1413
last_refresh_commit: 017763a
last_refresh_date: 2026-08-02T12:30:00Z
owner_agent: mars
refresh_triggers:
  - plan dispatch action close obligation coverage or activation contract changes
  - runbook tool schema runtime lock or corpus selection changes
  - build preservation or trusted collector incident
  - representative task-language search stops finding understandable guidance
scheduled_cadence: 30d
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
retrofit: false
trace_matrix_path: null
word_count_delta: null
```
