---
runbook_id: branch-landed-verification
domain: build-queue
status: ACTIVE
authoritative_for:
  - topic: branch-landed-verification
    section: §C. Architecture & Interactions
aliases: []
error_signatures:
  - signature: stale_build_base
    section: §F. Isolate
  - signature: unlanded_branch_believed_landed
    section: §F. Isolate
  - signature: push_failed_but_landed
    section: §F. Isolate
  - signature: clean_tree_read_as_current
    section: §F. Isolate
supersedes: []
superseded_by: []
owner: mars
last_verified_at: 2026-07-27
system_name: branch-landed-verification
purpose_sentence: Establish the base a build is briefed from against the remote, and establish whether a branch has actually landed, using measured evidence rather than the local checkout or a dispatcher's printed result.
owner_agent: mars
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Pre-dispatch base selection and post-build landing verification for every repository an instance briefs, merges, or reports on.
linter_version: 1.0.0
---

# Branch Landed Verification

## §A. Header

The frontmatter is authoritative for catalog identity. **Authority: operational procedure.** Full CORE and the Boot Kernel prevail. Repository SHAs, branch positions, and landing state come from git against the remote at the moment of use, never from this file, never from a handoff, and never from a session summary.

**Fetch trigger:** any of — writing a base SHA into a build brief; merging or pushing; reporting that work has landed; reading a dispatcher result that claims a push failed; reconciling a Build Queue item against code.

**Harness status, measured S1374.** The legibility harness was run against this runbook on 2026-07-27T23:09:41Z and returned INFRASTRUCTURE_FAILURE with aggregate 0.0 because `KOSKADEUX_MCP_URL` is not configured in this environment. No legibility score has been measured for this document. The §J pass rate is the pending-tooling constant, not a result.

**Governing CORE clauses:** §S4 (builders MUST push to main after tests pass; Council gates are the quality check) and §S16 (build status is canonical in Living State, code is canonical in Git).

**Why this exists.** In S1372 a build base was written into an MP brief from local `main` at `526dd85` without checking `origin/main`, which was two commits ahead at `01250a1`. MP branched faithfully from the stale base and re-added footer legal links Max had deliberately deleted under T-2026-000279. The tree was clean and the branch was correct; the base was wrong. It self-corrected only because a later `git reset --soft origin/main` during a squash reparented the commit. That is luck, not process. This runbook is the S1371-D1 and S1371-D2 obligation.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Remote-authoritative base selection | SHIPPED | `git rev-parse origin/main` | Pre-dispatch check | 2026-07-27 |
| Ahead and behind measurement of a checkout | SHIPPED | `git rev-list --left-right --count` | Pre-dispatch check | 2026-07-27 |
| SHA-ancestry landing test | SHIPPED | `git merge-base --is-ancestor` | Post-build check | 2026-07-27 |
| Patch-equivalence landing test | SHIPPED | `git cherry` | Post-build check | 2026-07-27 |
| Content landing test, squash and rebase safe | SHIPPED | `git diff --stat` | Post-build check | 2026-07-27 |
| Remote branch position readback | SHIPPED | `git ls-remote` | Post-push check | 2026-07-27 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Remote reference | `git fetch origin` then `origin/main` | Remote refs in the local checkout | Every brief, merge, and report | Stale until fetched. A checkout that has not fetched has no opinion worth acting on. |
| Working checkout | `git rev-parse HEAD` | Local refs and working tree | Base selection | Local `main` is a cached copy of a remote branch, not the remote branch. |
| Divergence measure | `git rev-list --left-right --count origin/main...HEAD` | Derived | Base selection | Left is behind, right is ahead. Both zero is the only "in sync". |
| Landing test | `git merge-base --is-ancestor`, `git cherry`, content diff | Derived | Completion reporting, BQ reconciliation | Three tests, different failure modes. See §E-03. |
| Dispatcher result | MP or Codex build envelope | Dispatch record | Post-build verification | The envelope's push outcome is a claim, not evidence. Verify against the remote. |

### The four states a branch can be in

1. **Not pushed.** Nothing on the remote. `git ls-remote` returns nothing.
2. **Pushed, not landed.** On the remote as a branch, not an ancestor of `origin/main`. Work exists but no customer has it.
3. **Landed by merge or fast-forward.** An ancestor of `origin/main`. SHA-ancestry proves it.
4. **Landed by squash or rebase.** The content is on `origin/main` but the original SHA is not an ancestor and the patches are not equivalent. Only the content test proves it.

State 4 is why SHA-ancestry alone is not a sufficient landing test, and why "not an ancestor" must never be reported as "not landed" without the content check.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan or Mars | Establish the base before briefing, and verify landing after | `shell_request action=exec` | Repository read | COMPLETE |
| MP | Build from the base named in the brief | `dispatch_mp_build` | Approved repository scope | COMPLETE — MP does not choose the base; the briefing instance does |
| Council reviewer | Review at the dispatched SHA only | `council_request` | Read at SHA | COMPLETE |
| Max | Decide whether unlanded work is abandoned or landed | Human decision | Final authority | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: A base SHA is about to be written into a build brief, spec, or review dispatch.
  pre_conditions: [repository_path_known, network_available]
  tool_or_endpoint: shell_request action=exec
  argument_sourcing: {command: "git -C <repo> fetch origin --quiet && git -C <repo> rev-parse origin/main"}
  idempotency: IDEMPOTENT
  expected_success: {shape: forty-character SHA read from the remote-tracking ref after a fetch, verification: re-run and compare; the value in the brief must equal this value}
  expected_failures:
    - {signature: stale_build_base, cause: the SHA was read from local HEAD or local main instead of origin/main, or was read before fetching}
  next_step_success: Write that SHA into the brief verbatim and name the branch it will be cut from.
  next_step_failure: Do not dispatch. Re-read against the remote and correct the brief.
- id: E-02
  trigger: A working checkout is about to be used as the base, or reported as current.
  pre_conditions: [fetch_completed]
  tool_or_endpoint: shell_request action=exec
  argument_sourcing: {command: "git -C <repo> rev-list --left-right --count origin/main...HEAD"}
  idempotency: IDEMPOTENT
  expected_success: {shape: two integers, behind then ahead, verification: only 0 and 0 means the checkout equals the remote line}
  expected_failures:
    - {signature: clean_tree_read_as_current, cause: a clean working tree and zero commits ahead were treated as up to date while the checkout was behind the remote}
  next_step_success: If behind is non-zero, fast-forward or cut from origin/main before briefing.
  next_step_failure: Report the divergence; never silently rebase a peer's branch.
- id: E-03
  trigger: A branch must be established as landed or not landed.
  pre_conditions: [fetch_completed, branch_or_sha_known]
  tool_or_endpoint: shell_request action=exec
  argument_sourcing: {command: "git -C <repo> merge-base --is-ancestor <sha> origin/main; git -C <repo> cherry origin/main <branch>; git -C <repo> diff --stat origin/main..<branch>"}
  idempotency: IDEMPOTENT
  expected_success: {shape: ancestry exit status, cherry lines marked + for unlanded and - for patch-equivalent, and a content diff, verification: an empty content diff is landing evidence even when ancestry says no}
  expected_failures:
    - {signature: unlanded_branch_believed_landed, cause: landing was inferred from a dispatcher envelope, a handoff line, or a session summary rather than measured against the remote}
  next_step_success: Record the SHA and which of the three tests proved it.
  next_step_failure: Treat the work as unlanded and preserve the branch; do not re-dispatch until §E-04 is run.
- id: E-04
  trigger: A dispatcher or push reports failure.
  pre_conditions: [branch_name_known]
  tool_or_endpoint: shell_request action=exec
  argument_sourcing: {command: "git -C <repo> ls-remote origin 'refs/heads/<branch>' && git -C <repo> fetch origin --quiet && git -C <repo> merge-base --is-ancestor <sha> origin/main"}
  idempotency: IDEMPOTENT
  expected_success: {shape: remote ref line with a SHA, or no output, verification: no output means genuinely not pushed; a SHA means the push succeeded whatever the envelope said}
  expected_failures:
    - {signature: push_failed_but_landed, cause: the printed error was believed and correct work was re-dispatched, re-committed, or discarded}
  next_step_success: If the work is on the remote, stop. Do not repair, re-dispatch, or re-commit.
  next_step_failure: Only then treat the push as genuinely failed and retry.
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | A build faithfully re-introduces something that was deliberately removed. | The brief named a base that was behind the remote, so the removal was not in the tree the builder saw. Measured in S1372. | Compare the base SHA in the brief against `origin/main` at brief time; run `git log <base>..origin/main`. | G-01 | CONFIRMED |
| F-02 | A checkout is reported as current while work is missing from it. | Clean tree and zero commits ahead were read as up to date; nobody measured behind. Measured in S1374 on three repositories. | `git rev-list --left-right --count origin/main...HEAD`. | G-02 | CONFIRMED |
| F-03 | Work is reported as landed but is absent from `origin/main`. | Landing was inferred from a dispatch envelope, a handoff, or a session summary. | Run all three tests in §E-03. | G-03 | CONFIRMED |
| F-04 | A dispatcher prints a push failure while the commit is on the remote. | The guardrail refusing an automated main push surfaced as `error_type=push_failed` with every gate passed. A correct build was discarded this way in S1324. | `git ls-remote origin 'refs/heads/<branch>'` before any repair action. | G-04 | CONFIRMED |
| F-05 | SHA-ancestry says not landed but the change is visibly on `origin/main`. | The branch was squash-merged or rebased, so neither the SHA nor the patches survive. | `git diff --stat origin/main..<branch>`; empty means the content is already there. | G-03 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Remote reference
  root_cause: The base SHA entered the brief from the local checkout rather than from the remote.
  repair_entry_point: The build brief, before dispatch.
  change_pattern: Fetch, re-read origin/main, rewrite the base in the brief, and re-cut the branch. If the build already ran, diff the delivered branch against origin/main and strip any hunk that reverses a deliberate change rather than blaming the builder.
  rollback_procedure: Abandon the branch cut from the stale base; the correct base is always recoverable from the remote.
  integrity_check: The brief's base SHA equals origin/main as read after a fetch, and git log <base>..origin/main is empty.
- id: G-02
  symptom_ref: F-02
  component_ref: Divergence measure
  root_cause: Cleanliness was mistaken for currency.
  repair_entry_point: The checkout, before it is used or reported.
  change_pattern: Fetch, measure behind and ahead, then fast-forward if behind is non-zero and ahead is zero. If both are non-zero the checkout has diverged and needs an owner decision, not an automatic rebase.
  rollback_procedure: None required for a fast-forward; a diverged checkout is left untouched pending the owner.
  integrity_check: rev-list --left-right --count returns 0 and 0, or the divergence is recorded and owned.
- id: G-03
  symptom_ref: F-03
  component_ref: Landing test
  root_cause: Landing was asserted from a claim rather than measured against the remote.
  repair_entry_point: Any completion report, BQ update, or handoff line asserting that work landed.
  change_pattern: Run ancestry, cherry, and content diff. Report which test proved it and at which SHA. Correct the BQ entity and the handoff if the assertion was wrong.
  rollback_procedure: Withdraw the completion claim and restore the item's prior status; never delete the branch on the strength of an unverified landing.
  integrity_check: The reported SHA is reproducible from the remote by a second party running the same three commands.
- id: G-04
  symptom_ref: F-04
  component_ref: Dispatcher result
  root_cause: A printed error was treated as evidence of the world's state.
  repair_entry_point: The moment before any repair, re-dispatch, or re-commit.
  change_pattern: Read the remote first. If the work is there, stop and report it as landed. If it is not, retry the push once and read the remote again.
  rollback_procedure: If work was already discarded, recover it from the reflog or the remote branch before doing anything else.
  integrity_check: No re-dispatch occurs without a remote read taken after the reported failure.
```

## §H. Evolve

### §H.1 Invariants

A base is what the remote says it is at the moment of briefing, and landing is what the remote says it is at the moment of reporting. Neither may be asserted from a local checkout, a dispatcher envelope, a handoff, or a prior session's summary.

### §H.2 BREAKING predicates

Removing any of the three landing tests, permitting a base SHA to be sourced from a local ref, or allowing a completion report to assert landing without a remote read is BREAKING.

### §H.3 REVIEW predicates

Review changes to the dispatch brief schema, the push guardrail, squash-on-dispatch practice, and any tooling that reads or caches remote refs on the instance's behalf.

### §H.4 SAFE predicates

Adding further evidence, clearer output, or automation that performs these same reads is safe, provided the remote read still happens and its result is still what is reported.

### §H.5 Boundary definitions

#### module

Git remote refs, the working checkout, the build brief, the dispatch envelope, and the completion report.

#### public contract

The base SHA written into a brief, and the landed-or-not verdict written into a Build Queue entity, a ticket, or a handoff.

#### runtime dependency

Network reachability to the git remote, and a fetch that completed before the read.

#### config default

An unreachable remote yields no verdict. Absent evidence is reported as absent, never as landed and never as clean.

### §H.6 Adjudication

Where the remote and any record disagree, the remote wins and the record is corrected. Where the three landing tests disagree, the content test decides, because it is the only one that survives squash and rebase.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - {id: I-01, type: operate, refs: [E-01], scenario: A base SHA is needed for a build brief and the checkout was last fetched yesterday., expected_answers: [{kind: human_action, verb: fetch, object: origin, target: repository before reading the base}], weight: 0.0769230769}
  - {id: I-02, type: operate, refs: [E-01], scenario: Local main and origin main differ and the brief already contains local main., expected_answers: [{kind: classification, label: STALE_BUILD_BASE}], weight: 0.0769230769}
  - {id: I-03, type: operate, refs: [E-02], scenario: A checkout has a clean working tree and zero commits ahead of the remote., expected_answers: [{kind: human_action, verb: measure, object: commits behind, target: rev-list --left-right --count}], weight: 0.0769230769}
  - {id: I-04, type: operate, refs: [E-03], scenario: A branch must be reported as landed or not landed., expected_answers: [{kind: human_action, verb: run, object: ancestry cherry and content tests, target: origin/main}], weight: 0.0769230769}
  - {id: I-05, type: operate, refs: [E-04], scenario: A dispatcher returns push_failed with all gates passed., expected_answers: [{kind: human_action, verb: read, object: remote branch ref, target: git ls-remote before any repair}], weight: 0.0769230769}
  - {id: I-06, type: isolate, refs: [F-01], scenario: A delivered build re-adds links that were deliberately deleted two commits ago., expected_answers: [{kind: classification, label: STALE_BUILD_BASE}], weight: 0.0769230769}
  - {id: I-07, type: isolate, refs: [F-04], scenario: A push error was believed and the work was re-dispatched without reading the remote., expected_answers: [{kind: classification, label: PUSH_FAILED_BUT_LANDED}], weight: 0.0769230769}
  - {id: I-08, type: isolate, refs: [F-02], scenario: A checkout is clean and zero ahead but three commits behind the remote., expected_answers: [{kind: classification, label: CLEAN_TREE_READ_AS_CURRENT}], weight: 0.0769230769}
  - {id: I-09, type: repair, refs: [G-03], scenario: A handoff asserts that a branch landed and no SHA is given., expected_answers: [{kind: human_action, verb: withdraw, object: completion claim, target: build queue entity and handoff}], weight: 0.0769230769}
  - {id: I-10, type: repair, refs: [G-01], scenario: A build already ran from a base that was behind the remote., expected_answers: [{kind: human_action, verb: strip, object: hunks reversing a deliberate change, target: delivered branch before merge}], weight: 0.0769230769}
  - {id: I-11, type: evolve, refs: [§H], scenario: A proposal drops the content test and keeps only SHA ancestry., expected_answers: [{kind: classification, label: BREAKING}], weight: 0.0769230769}
  - {id: I-12, type: evolve, refs: [§H], scenario: A proposal adds tooling that performs the same remote reads automatically., expected_answers: [{kind: classification, label: SAFE}], weight: 0.0769230769}
  - {id: I-13, type: ambiguous, refs: [§H.6], scenario: Ancestry says not landed while the change is visibly present on origin/main., expected_answers: [{kind: human_action, verb: decide, object: landing verdict, target: content diff as the deciding test}], weight: 0.0769230772}
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1374
last_refresh_commit: 61a7258
last_refresh_date: 2026-07-27T23:00:00Z
owner_agent: mars
refresh_triggers: [dispatch brief schema changes, push guardrail behaviour changes, squash-on-dispatch practice changes, git remote access mechanism changes]
scheduled_cadence: 30d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-07-27T23:09:41Z
first_staleness_detected_at: null
```

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1374 / 2026-07-27T23:00:00Z
last_lint_result: PASS
retrofit: false
trace_matrix_path: runbooks/boot-kernel-companion-crosswalk.md
word_count_delta: null
```
