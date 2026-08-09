---
system_name: builder-controls
purpose_sentence: Indexed reference of every control on the MP/Codex builder path in koskadeux-mcp - what each control is, where it lives, what it does, why it exists, how often it has actually fired, and its status under the S1455 minimal-bridge rebuild - so a future builder knows exactly what is there and why.
owner_agent: vulcan
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: |
  The control surface between "dispatch a build" and "get a diff back": dispatch-time gates, in-flight bounds, and post-build/pre-push gates on the MP (Codex) builder path. Anchors cite koskadeux-mcp main @ 96c62109 (2026-08-06). Fire counts come from the full stored dispatch corpus in /var/tmp/koskadeux/cc_tasks (3,024 task records; 254 MP dispatches). Dispatch mechanics, model pinning and CLI quirks are codex-mp.md; Council review mechanics are agent-dispatch.md and council-gate-process.md; this runbook is the controls inventory.
linter_version: 1.0.0
---

# Builder Controls

## §A. Header

The YAML frontmatter above defines the §A header. This runbook exists by Max directive (S1455): a reference for future builders on exactly what controls surround the build and why. It is the companion to the S1455 minimal-bridge rebuild (specs/BQ-MINIMAL-BUILDER-BRIDGE-S1455-GATE1.md in koskadeux-mcp), whose Gate 1 R1 passed unanimously with mandates folded at 9cc065fc.

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| FIFO single-slot build queue (Phase 0) | SHIPPED | `koskadeux-mcp codex_cli_bridge.py queue` | Two live serialization proofs S1453 (593s wait, zero loss) | 2026-08-06 |
| Pre-push gate composition (12 terminal sites) | SHIPPED (scheduled for replacement) | `tools/agents.py ~6211-6520` | Exercised on every MP dispatch | 2026-08-06 |
| Builder-output manifest verification | SHIPPED (scheduled for removal) | `koskadeux_mcp/builder_output_verification.py` | 10 corpus fires, false-negative class | 2026-08-06 |
| Output-envelope schema repair | SHIPPED (scheduled for removal from build path) | `council_dispatch_middleware/schema_repair.py` | 25 corpus fires, all-false-negative hit list | 2026-08-06 |
| Minimal bridge (transport + preservation) | DESIGNED, Gate 1 R2 in review | `specs/BQ-MINIMAL-BUILDER-BRIDGE-S1455-GATE1.md @ 9cc065fc` | AC1-AC10 specified, directional | 2026-08-06 |

## §C. Architecture & Interactions

The build path is: `dispatch_mp_build` / `council_request(mode=build)` handler in `tools/agents.py` → dispatch-time gates → FIFO slot queue → `codex_cli_bridge.py` runs the Codex CLI → output-envelope parsing/repair → post-build pre-push gate composition in `tools/agents.py` (`run_pre_push_gate` region, twelve terminal return sites ~6211-6520) → push → result persistence to `/var/tmp/koskadeux/cc_tasks`. Total control surface at 96c62109: 21,186 lines (`tools/agents.py` 11,682; `codex_cli_bridge.py` 3,318; `koskadeux_mcp/structural_gate.py` 2,222; `structural_gate_runtime.py` 1,675; `claude_code_client.py` 1,528; `tools/agent_usage_log.py` 381; `tools/owned_child_exec.py` 380).

Ground truth on effectiveness, measured S1455 across all 254 stored MP dispatches (97 succeeded, 154 failed, 3 running): ~90 of the 154 failures were caused by the control surface or its bookkeeping, not by the builder's code. Exactly 1 was a genuine correctness catch (CI). That measurement is why the S1455 rebuild flips the burden of proof: a control survives only on a demonstrated real catch.

## §D. Agent Capability Map

Operators (Vulcan/Mars): dispatch builds, read every control's verdict, salvage preserved work. MP (Codex): the only builder, and it may edit ANY file on this control surface including `codex_cli_bridge.py` and `tools/agents.py`. Council (CC/Kimi/GLM): owns correctness adjudication at Gate 3 - the controls below were never a substitute for review and the rebuild makes that explicit.

CORRECTION, Max ruling S1488 (event 6005ec17-14e5-41f5-850e-d9b9c7eaf469, actor=max, trust_tier=human). This section previously said MP never edits `codex_cli_bridge.py` or `tools/agents.py` on a "bootstrap hazard" and that operators author every live-file edit. That rule was never Max's. It was written into this runbook by Vulcan in commit 280d701 and attributed to "decision event a03efd33", which on inspection is `a03efd33-86cb-4350-80ed-900c85960c6a`, actor=vulcan, trust_tier=system - an agent-authored record, not a human ruling. Max's verbatim S1488 ruling: "the only rule I have ever made about codex is that it cannot review its own code as a council member." That single rule stands and is already CORE S4: **the builder cannot review its own work.** A review exclusion is not an editing exclusion; the two were conflated here. MP building on this surface is governed by the same Gate 3 Council review as any other build, which is where correctness is actually adjudicated. Do not reintroduce an editing ban without a human-tier decision event.

## §E. Operate - the indexed control inventory

Each entry: WHAT it is / WHERE it lives / WHAT it does / WHY it exists / FIRES in the corpus / STATUS under S1455.

### E.1 Dispatch-time controls (before the builder runs)

- **C-01 FIFO slot queue (Phase 0).** `codex_cli_bridge.py`; `CODEX_SLOT_COUNT=1` is a hard-pinned invariant. Serializes the single Codex slot across both operators. Exists because the original defect was outright dispatch refusal after 600s when the slot was busy. Fires: routine; two live proofs S1453 of correct queueing with zero loss. STATUS: KEEP unchanged.
- **C-02 Peer-claim coordination.** `tools/agents.py:932` `_dispatch_coordination_instance`; requires `caller_instance` and honors BQ claims. Prevents the two operators double-building one item. STATUS: KEEP (lives above the bridge).
- **C-03 Build Queue reconciliation gate.** Dispatch handler; blocks build dispatch on BQ/git drift unless `auto_reconcile`/`bypass_reconcile`. Exists so state and git cannot silently diverge. Known false-block: reconciler `git_fetch_failed` tooling defect (T-2026-000490). STATUS: outside bridge scope; simplification candidate.
- **C-04 Runbook-refs gate.** `mode=build`/`author` dispatches require `runbook_refs` (runbook-first enforcement, BQ s1146). STATUS: KEEP (policy layer, not bridge).
- **C-05 CI-workflow presence check.** Structural dispatches verify the CI workflow exists; `skip_ci_check` is the audited bypass. STATUS: retires with the legacy stack; CI relocates to Gate 3 (see C-15).
- **C-06 Git preconditions.** `tools/agents.py` ~6232/6235/6244 (payloads 6686, 6779, 6886, 6914): `pre_build_workspace_dirty`, `pre_build_branch_ahead`, `dispatch_git_evidence_unavailable`, `dispatch_base_remote_mismatch`. Protect the peer's uncommitted work and guarantee an exact recorded base. Fires: 10, mostly the T-490 tooling defect; dirty/ahead essentially never falsely. STATUS: KEEP; per-dispatch worktrees make the shared-clone cases moot.
- **C-07 Structural stash immutable-record.** `structural_gate.py` family; records a shared artifact stash before structural dispatch and BLOCKS on record failure. Fires: 10, all bookkeeping blockers. STATUS: REMOVE as blocker (best-effort record).
- **C-08 Default cwd resolution.** Lane-a `default_cwd` shorthand. WHY IT IS A HAZARD, not a control: it has twice put a builder in the wrong repository (S1429 misdispatch; build 06ea928f ran a koskadeux-mcp deletion with cwd inside the backend clone). STATUS: eliminated by construction - bridge worktrees derive from `repo`, never from ambient cwd (AC7).

### E.2 In-flight bounds

- **C-09 Hard timeout.** `codex_cli_bridge.py:1026` `MP_HARD_UPPER_BOUND_S`; per-dispatch `timeout_s` capped by `MP_EXPLICIT_HARD_CEILING_S`. Bounds a runaway builder. Fires: 13 `hard_timeout` in the MP corpus plus the live 8741f4ba specimen (2026-08-06: timed out at 1800s leaving 23 files of correct work uncommitted in the tree; Mars salvaged by hand). Defect: expiry truncates AND abandons uncommitted work. STATUS: KEEP as a bound; the bridge preserves on expiry; ceilings become data-driven per dispatch_class once ≥30 outcome rows exist.
- **C-10 No-progress window.** `progress_window_s`, `stuck_no_progress`. A liveness bound. STATUS: KEEP as bound-with-preserve, never a verdict.
- **C-11 max_turns.** Turn budget treated as a build failure. It is a budget cap, not a correctness gate; it truncates mid-flight work and discards it. STATUS: REMOVE as a failure condition on the build path.
- **C-12 Output-envelope schema + repair.** `council_dispatch_middleware/schema_repair.py:76`, `exceptions.py:20` (`RepairExhaustedError`). Parses/repairs the builder's structured output envelope; exists to honor CORE S7 structured AI-to-AI output. Fires: 25, an all-false-negative hit list - repeatedly reported FAILURE on builds whose commits were correct, pushed and independently verified, including an 88-line one-file spec (disproving size as trigger). STATUS: REMOVE from the build path. Git is the output; S7 continues to govern reviewer/Council interchange where it belongs.

### E.3 Post-build / pre-push gates (`tools/agents.py` composition, twelve terminal sites ~6211-6520)

- **C-13 Exactly-one-commit invariant.** Emits `post_build_no_commit` (:8911) and `post_build_multiple_commits` (:8918); restores via `_restore_after_post_build_failure`. Exists for review hygiene. Fires: 11 multi-commit + 10 no-commit; the multi-commit class discarded completed correct folds whose only sin was arriving as two commits (s1315 defect 2). STATUS: REMOVE the discard; squash at merge is trivial for an operator.
- **C-14 SHA claim check.** `post_build_sha_mismatch` (~6326). Verifies the builder's claimed head matches git. STATUS: superseded - the bridge reports git directly instead of checking claims about it.
- **C-15 CI gate.** ~6355 via `_gate_failure_payload`, discard via `_discard_ci_failed_build`; `ci_regression` classes at 7423/7445/7469/7511. Exists for CORE S4 tests-before-completion. Fires: 1 - THE ONLY genuine correctness catch in the corpus. STATUS: RELOCATED, not dropped: tests run and are reported by the bridge (never gate), and CI re-runs at Gate 3 review, which is a hard prerequisite for any merge (spec §7, AC10).
- **C-16 Builder-output manifest verification.** `koskadeux_mcp/builder_output_verification.py:65` `verify_builder_output`, `:127` `builder_output_claim_mismatch`; restored via `_restore_after_post_build_failure`. Verifies the builder's line-anchor claims about its own diff. Fires: 10; the false-negative-by-regex specimen (`FAILED_FALSE_NEGATIVE_OUTPUT_MANIFEST_REGEX`) is durably recorded on Living State entity `build:bq-concurrent-build-capacity-s1214`, field `s1401_c5_canary_r10`. A build was failed by a regex. STATUS: REMOVE; Gate 3 reviews the actual diff, not claims about it.
- **C-17 Git-ref producer completion gate.** ~6449; discard via `_discard_to_recorded_base` (:8969, a `git reset --hard`). Bookkeeping persistence of the completed range, failing which the build is destroyed. Fires: 11 - each destroyed work that had ALREADY passed commit-count, SHA, CI and manifest gates (s1398 FINDING A). STATUS: REMOVE the discard; bookkeeping failure must never destroy work.
- **C-18 Push gate + shared-branch CAS.** ~6471-6494; `push_failed`, `shared_branch_cas_rejected`; local commit preserved, recovery guidance attached. Protects shared branches from clobbering. Fires: 13 "push failed after all pre-push gates passed" - work preserved, cycle lost. STATUS: KEEP the preserve behavior; bridge adds fast-forward-only pushes, unique retry branches, 3x backoff, and a `pushed`/`preserved` split.
- **C-19 work_preserved / commits_created telemetry.** `tools/agents.py` ~5801: `work_preserved = commits_created > 0`. Defects, both live-confirmed: reports work lost while it sits uncommitted in the tree (s1315 defect 1; 8741f4ba on 2026-08-06), and `commits_created` reports WHOLE-HISTORY DEPTH, never a per-build figure (2726 specimen, execution-confirmed via `git rev-list --count`). Treat both fields as labels, not evidence. STATUS: replaced by the bridge's `preserved`/`pushed`/`push_status` report.
- **C-20 Before-reap persistence requirement.** Result persistence failure after child drain reported as a BUILD failure. Fires: 20 - pure wrapper bookkeeping presented as build outcome. STATUS: persistence errors demote to warnings, never verdicts.
- **C-21 Per-dispatch commit identity.** `GIT_AUTHOR_NAME/EMAIL` + `GIT_COMMITTER_NAME/EMAIL` injected per dispatch (s1346 clause 5). Exists because ambient identity is not evidence: a repo-local `[user]` block misattributed builder commits to an operator for weeks (identity_rca_s1400). STATUS: KEEP; AC6 makes it directional.
- **C-22 Emergency bypasses.** `skip_ci_check`, `skip_output_verification` - audited structural-only bypasses. STATUS: die with the gates they bypass.
- **C-23 guard_direction_evidence completion gate.** `bq_complete` path: `requires_directional_evidence` returns True on any `entity_state` other than `present`, so a failed entity FETCH fails the gate shut; the only unlock is declaring `guard_class=trust`, which non-guard builds must never do. STATUS: defect, in the S1455 removal scope.

## §F. Isolate

Error signature → control: `RepairExhaustedError` / `schema repair exhausted` → C-12 (verify the work at git before believing the failure). `post_build_multiple_commits` / `post_build_no_commit` → C-13. `builder_output_claim_mismatch` → C-16. `hard_timeout` → C-09 (inspect the worktree for uncommitted work). `push_failed` / `shared_branch_cas_rejected` → C-18 (commit exists locally). "BQ git-ref producer did not persist" → C-17 (work destroyed; check origin for a pushed copy first). "before-reap persistence failed" → C-20 (build likely fine; check git). `commits_created` absurdly large → C-19 (history depth, ignore). Wrong-repo build → C-08. `dispatch_git_evidence_unavailable` on a healthy repo → C-03/T-2026-000490 tooling defect, not your dispatch.

## §G. Repair

The standing salvage procedure when any control reports failure: (1) never redispatch blind; (2) `git ls-remote` the expected branch - pushed work survives C-13/C-12 fires; (3) if unpushed, inspect the build worktree/clone for commits (`git log`) and uncommitted modifications (`git status`) - C-09/C-19 fires leave correct work in the tree; (4) tarball off-tree before touching anything, then commit with an honest rescue message stating it is an operator salvage, not builder output and not evidence of correctness (Mars S1454 precedent); (5) verdicts of correctness come from Council review of the actual diff, never from the wrapper's report.

## §H. Evolve

The S1455 programme replaces E.2-E.3 with a minimal bridge (target <600 lines): fresh worktree at exact base derived from `repo`, per-dispatch identity, run Codex with no envelope/schema/turn-failure, preserve on every observed exit (honoring .gitignore, secret-scan as the ONE permitted push block), fast-forward-only verified push, tests as report, one outcome row per dispatch, honest `{branch, head_sha, diffstat, tests, duration, terminal_status, preserved, pushed}`. Cutover behind `KD_MINIMAL_BRIDGE_ENABLED` (default false); routing fork operator-authored, Council-reviewed, never MP; legacy stack is the rollback target during soak; ONE post-soak removal item deletes the legacy stack and the Lane B lane model together. Update this runbook's §B/§E statuses in the same change as each stage lands.

## §I. Acceptance Criteria

- AC-R1: every control on the live build path appears in §E with file:line anchor, purpose, corpus fire count, and S1455 status; a control found in code but absent here is a runbook defect.
- AC-R2: fire counts cite their measurement (S1455 full-corpus join of /var/tmp/koskadeux/cc_tasks, 254 MP dispatches) so future counts are comparable, not vibes.
- AC-R3: §G salvage procedure is executable by a fresh operator with no other context.
- AC-R4: statuses in §B/§E are updated in the same change as any bridge-programme stage lands (KEEP/REMOVE claims must match the deployed tree).

## §J. Lifecycle

Created S1455 (2026-08-06) by Max directive, anchors verified at koskadeux-mcp 96c62109. Refresh trigger: any merge touching `tools/agents.py` gate composition, `codex_cli_bridge.py`, `builder_output_verification.py`, `structural_gate*.py`, or the minimal-bridge module. Owner re-verifies anchors at each refresh; stale anchors are a §K conformance failure.

## §K. Conformance

This runbook conforms to the §A-§K standard and is registered in CATALOG.json and TOPIC-ROUTER.md in the same change that created it. Fire counts and anchors are evidence-cited, not asserted. The inventory's burden-of-proof rule mirrors the programme it documents: a control claimed here as justified must show its real catch.
