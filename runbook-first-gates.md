---
system_name: runbook-first-gates
purpose_sentence: Operate, diagnose, and evolve the runbook-first enforcement gates that block session plans, Council dispatches, and session closes lacking valid runbook references, attestations, or exit declarations.
owner_agent: vulcan
escalation_contact: Max (enforce-mode flips, routine-class edits, disputed adjudications); either instance (Vulcan/Mars) operates this runbook
lifecycle_ref: §J
authoritative_scope: The three Phase-1 enforcement gate points (kd_session_plan runbook_consultation, council_request runbook_refs, kd_session_close runbook_exit), the shared ref resolver, the RUNBOOK_* error-code contract, the runbook-debt ledger, the waiver accumulator and its plan-time bite, the routine fast path, and the gate config. NOT authoritative for general session open/close mechanics (session-open-protocol.md, session-close-protocol.md), MP/Council dispatch mechanics (codex-mp.md, agent-dispatch.md), the runbook authoring standard itself (specs/BQ-RUNBOOK-STANDARD.md), or the queued Phase 2/3 enforcement surfaces (owner BQ-RUNBOOK-FIRST-ENFORCEMENT-S1146).
linter_version: 1.0.0
---

# Runbook-First Gates

> The system-enforced version of CORE §4 "Runbooks": a session cannot submit a plan, hand work to a builder, or close without pointing at the manual page that governs the work — or explicitly attesting no page exists, which creates dischargeable debt. Shipped as Phase 1 of `BQ-RUNBOOK-FIRST-ENFORCEMENT-S1146` (chunks C1/C3/C4/C5), Council-gated, live in BLOCK mode since S1150 on Max GO. Phase 2/3 (bq_complete evidence, BQ-gate hard blocking, ticket §F citation gate, CI paired-change check, drift/coverage program) are PLANNED under the same BQ.

## §A. Header

YAML frontmatter above is authoritative for the §A header fields.

### M1 — Dependencies & Credentials / Source-of-Truth

| Dependency | What it provides | Where it lives | Owning service |
|---|---|---|---|
| `config:runbook-gate-config` (Living State) | `enforce_mode` (warn/block) + `routine_classes` allowlist | Living State via Koskadeux gateway; no credential — gateway auth | Koskadeux MCP |
| `config:runbook-waivers` (Living State) | Append-only waiver rows (single canonical shape `body.waivers` list) | Living State | Koskadeux MCP (`tools/session.py:_append_runbook_waiver`) |
| `config:resource-registry` (Living State) | Canonical local path of the `aidotmarket/runbooks` clone — the ONLY way the gates locate the repo | Living State; path must be a DIRECTORY (S1150 defect: file paths in the registry broke every `git -C`) | Koskadeux MCP |
| `infra:session-status:{session_id}:role={role}` (Living State) | Per-session `runbook_debt` ledger (`{sid}-D{n}` entries) | Living State | Koskadeux MCP |
| Event Ledger (`runbook_gate` events) | Audit trail of every gate evaluation (plan, dispatch, close) | Living State events, `entity_key=session:{sid}` | Koskadeux MCP |
| `aidotmarket/runbooks` local clone | Files and section headings the resolver checks refs against | `~/Projects/ai-market/runbooks` (resolved via `config:resource-registry`, never hardcoded); git over SSH, Titan-1 keys | GitHub `aidotmarket/runbooks` |

## §B. Capability Matrix

| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Shared ref resolver: path + section resolution, best-effort 5s fetch, 90-day freshness warnings, gate-event emission | SHIPPED | `koskadeux-mcp tools/runbook_ref.py:RunbookRefResolver` | `tests/unit/test_runbook_ref_resolver.py` (9 tests) + CI paths 16/16 | 2026-07-11 |
| Plan gate: `kd_session_plan` requires `runbook_consultation` covering every objective (RunbookRef or Attestation), incident synthesis, routine fast path, waiver-subject bite | SHIPPED | `koskadeux-mcp tools/session.py:_runbook_plan_gate` | C1/C2 chunk tests; live block-mode reject+recover verified S1177 (organic) and S1180 | 2026-07-11 |
| Dispatch gate: `council_request` requires resolved `runbook_refs` for `mode=build/author` and incident-class review; injects cited sections (60-line cap) into the task; attestations/disputes append debt | SHIPPED | `koskadeux-mcp tools/agents.py:_runbook_dispatch_gate` | live structural build 7ad740a4 full gate chain (S1150 flip evidence) | 2026-07-08 |
| Close gate: touched-repo detection, runbooks-commit author-match, `runbook_exit` validation (bare-SHA verification for commit/created), debt discharge, waiver append | SHIPPED | `koskadeux-mcp tools/session.py:_runbook_close_gate` | S1150 discharge-path exercise; T-2026-000203 author-match fix `d9f4509d` verified post-kickstart | 2026-07-10 |
| Waiver accumulator + plan-time bite (subject with ≥2 undischarged waivers named in objectives rejects the plan) | SHIPPED | `koskadeux-mcp tools/session.py:_waiver_subject_bite_error / _append_runbook_waiver` | C4/C5 chunk tests (Gate 3 approved) | 2026-07-08 |
| Routine fast path: `triviality=routine` + allowlisted `routine_class` skips per-objective coverage | SHIPPED | `koskadeux-mcp tools/session.py:_is_routine_fast_path / _routine_class_error` | C1 chunk tests | 2026-07-08 |
| Boot tripwires: waiver subjects surfaced in the `kd_session_open` standup | SHIPPED | `koskadeux-mcp tools/session.py (open payload runbook_tripwires)` | observed live every open incl. S1180 | 2026-07-11 |
| Phase 2/3: bq_complete runbook evidence, BQ Gate-1/2 hard blocking, ticket §F citation gate, CI paired-change check, drift/coverage program | PLANNED | `specs/BQ-RUNBOOK-FIRST-ENFORCEMENT-S1146-GATE1.md:§2 (chunks queued)` | n/a | 2026-07-11 |

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Ref resolver | `tools/runbook_ref.py:RunbookRefResolver.resolve` | reads `config:resource-registry`; writes `runbook_gate` events | git (`fetch`, `log`) against the runbooks clone; all three gates call it | Validates each `RunbookRef {path, section}`: path must be a file inside the repo, section must match a `§X` token or a markdown heading (exact text or normalized anchor). Attestations/disputes skip file checks. Emits one event per evaluation. |
| Plan gate | `tools/session.py:_runbook_plan_gate` | reads gate config + waivers; appends attestation debt to `infra:session-status:{sid}:role={role}` | `kd_session_plan` (and `amendment=true` resubmissions); resolver | Every 1-based objective must be covered by some entry's `covers` list (an entry without `covers` defaults to covering the objective at its own list position; 0 coerces to 1; out-of-range values are ignored and reported). `work_type=incident` additionally requires a non-empty `synthesis` on every RunbookRef that does NOT verbatim-match a source line. |
| Dispatch gate | `tools/agents.py:_runbook_dispatch_gate` | appends attestation/dispute debt to session-status | `council_request`; resolver; injects `_runbook_dispatch_context_block` into the task | Required when `mode` is `build` or `author`, and for `mode=review` with `dispatch_class=incident`. Optional refs on other modes are still resolved and evented. Accepts a third type, `RunbookDispute {runbook_disputed: true, ref, reason}` — appends a `disputed: true` debt row. On RESOLVED required dispatches, cited sections (max 60 lines each) are prepended to the builder task. |
| Close gate | `tools/session.py:_runbook_close_gate` | reads/patches session-status `runbook_debt`; appends to `config:runbook-waivers` | `kd_session_close`; git (`status --porcelain`, `log --since`, `cat-file -e`) | Detects in-scope repos touched since `started_at` (dirty tree or new commits). If any and no runbooks commit is detected and no `runbook_exit` declared → reject. `runbook_exit {kind, ref_or_reason, discharges[]}`; kinds `commit`/`created` verify `ref_or_reason` verbatim via `git cat-file -e` — it MUST be a bare SHA, no prose. `kind=waiver` appends one waiver row per discharged subject. Discharge only touches THIS session's debt IDs. |
| Debt ledger | `tools/session.py:_persist_runbook_session_status_update` | `infra:session-status:{sid}:role={role}` `body.runbook_debt` | plan gate, dispatch gate, close gate | Entries `{id: "{sid}-D{n}", subject, reason, attested_at, instance, discharged_by, disputed?}`. `disputed=true` debt cannot be discharged by `kind=no_change_needed`. Undischarged entries at close → `RUNBOOK_DEBT_OPEN`. |
| Waiver store + bite | `tools/session.py:_append_runbook_waiver / _waiver_subject_bite_error` | `config:runbook-waivers` `body.waivers` (append-only list; do NOT add `subjects`/`counts` dict shapes — double count) | close gate (writer); plan gate (bite reader); boot standup (tripwire) | Bite: subject with ≥2 rows and no `discharged_by.kind` in `{created, commit}` that appears case-insensitively in the joined objectives text rejects the plan — unless an objective containing both `runbook-coverage` and the subject is itself covered. |
| Gate config | `tools/session.py:_runbook_gate_enforce_mode` | `config:runbook-gate-config` (`enforce_mode`, `routine_classes`) | all three gates | `warn` logs everything, never rejects; `block` rejects on any error. Unreadable config defaults to `warn`. Live: BLOCK since S1150 (v2, decision event bba08b07). |

Prose: the flow is symmetric at all three gate points — parse typed refs, resolve against the live repo, emit a `runbook_gate` event, then reject (block) or log (warn). The resolver's `git fetch` is best-effort with a 5-second timeout; failure degrades to resolving against the local checkout and adds a `stale_fetch` warning, never a reject. Freshness uses frontmatter `last_refresh_date` when present, else the file's last git commit date; older than 90 days adds a `stale_runbook` warning.

## §D. Agent Capability Map

| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan/Mars | Submit plans through the plan gate | `kd_session_plan(runbook_consultation=[...])` | gateway session | COMPLETE |
| Vulcan/Mars | Dispatch builds/reviews through the dispatch gate | `council_request(runbook_refs=[...])` | gateway session | COMPLETE |
| Vulcan/Mars | Close through the close gate | `kd_session_close(runbook_exit={...})` | gateway session | COMPLETE |
| Vulcan/Mars | Discharge cross-session debt / clear waiver subjects | `state_request patch` on the owning session-status entity or `config:runbook-waivers` (set `discharged_by` to kind created/commit with the bare SHA) | gateway session + optimistic version | COMPLETE — manual by design; the close gate only discharges its own session's IDs (§E-05) |
| MP/AG/DeepSeek/GLM/CC | Receive injected cited runbook sections in build/author tasks | automatic (`_runbook_dispatch_context_block`) | n/a (read-only context) | PARTIAL — injection fires only for required modes with RESOLVED refs; extending to any RESOLVED optional refs is a recorded follow-up (C3 GLM mandate adjudication) |
| Max | Flip `enforce_mode`; edit `routine_classes` | ledgered `state_request patch` on `config:runbook-gate-config` + decision event | Max authority (§H.1) | COMPLETE |

## §E. Operate

```yaml operate
- id: E-01
  trigger: Opening a session — kd_session_plan must pass the plan gate
  pre_conditions:
    - kd_session_open succeeded (boot gate PLANNING)
    - objectives drafted (1-5 items)
    - TOPIC-ROUTER.md consulted for each objective's owning runbook
  tool_or_endpoint: "kd_session_plan(session_id, objectives, delegation_strategy, runbook_consultation=[RunbookRef {path, section, synthesis?, covers?} | Attestation {no_entry_found: true, subject, reason, covers?}], work_type?, triviality?, routine_class?)"
  argument_sourcing:
    path_and_section: from TOPIC-ROUTER.md and the owning runbook's actual headings — section must be an exact heading text, its anchor, or a §X token present in the file
    covers: 1-based objective numbers each entry governs; omit to cover the objective at the entry's own list position
    synthesis: required only when work_type=incident — your own one-line paraphrase of the cited section, NOT a copied line
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: session_id (resubmission after a reject re-evaluates; amendment=true appends objectives to a live session and re-runs the gate)
  expected_success:
    shape: '"Plan accepted. ... Tools unlocked." — attestations persisted as {session_id}-D{n} debt rows on infra:session-status'
    verification: "state_request get infra:session-status:{sid}:role={role} shows runbook_debt entries for each attestation"
  expected_failures:
    - signature: 'Error: RUNBOOK_REF_MISSING ... 9 validation errors'
      cause: wrong entry shape (see §F-01)
    - signature: 'Error: RUNBOOK_REF_UNRESOLVED ... section'
      cause: cited heading does not exist in the file (§F-02)
    - signature: subject X has N accumulated runbook waivers
      cause: waiver bite (§F-07)
  next_step_success: proceed to work; every attestation is debt you must discharge or waive at close
  next_step_failure: fix per §G-01/§G-02 and resubmit — the gate is stateless per call
- id: E-02
  trigger: Dispatching build/author work (or an incident-class review) to a Council agent
  pre_conditions:
    - plan accepted (tools unlocked)
    - owning runbook section identified for the work being dispatched
  tool_or_endpoint: "council_request(agent, mode, task, runbook_refs=[RunbookRef | Attestation | RunbookDispute {runbook_disputed: true, ref, reason}], dispatch_class?)"
  argument_sourcing:
    runbook_refs: same sourcing as E-01; a RunbookDispute cites a ref you believe is WRONG and says why — it dispatches but appends disputed debt
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: dispatch proceeds; for required modes with RESOLVED refs the cited sections (60-line cap each) are auto-prepended to the builder task; runbook_gate event logged
    verification: event ledger runbook_gate gate_point=council_request outcome=RESOLVED for this session
  expected_failures:
    - signature: runbook gate rejected council_request RUNBOOK_REF_MISSING
      cause: mode=build/author (or review+incident) with no runbook_refs (§F-01)
    - signature: runbook gate rejected council_request RUNBOOK_REF_UNRESOLVED
      cause: bad path or section (§F-02)
  next_step_success: normal build/review flow (codex-mp.md, agent-dispatch.md)
  next_step_failure: fix refs per §G-02; attestation is the fallback when no runbook exists — it creates debt, use it honestly
- id: E-03
  trigger: Closing a session that touched in-scope repos
  pre_conditions:
    - all runbook updates for this session's shipped work committed and PUSHED to runbooks origin/main (the gate verifies against origin/main and the local object store)
    - "open debt IDs known (state_request get infra:session-status:{sid}:role={role})"
  tool_or_endpoint: "kd_session_close(session_id, summary, reason, handoff_content, runbook_exit={kind: commit|created|no_change_needed|waiver, ref_or_reason, discharges: [debt ids]})"
  argument_sourcing:
    ref_or_reason: for kind=commit/created this is passed VERBATIM to `git cat-file -e` — it must be a BARE commit SHA, no surrounding prose; for no_change_needed/waiver it is the justification text
    discharges: this session's own {sid}-D{n} ids the exit covers
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: session_id (close is fail-closed on the handoff write and retryable)
  expected_success:
    shape: close proceeds; discharged debt rows get discharged_by set; kind=waiver appends rows to config:runbook-waivers
    verification: kd_session_close_status gate result; config:runbook-waivers / session-status reflect the exit
  expected_failures:
    - signature: RUNBOOK_EXIT_MISSING in-scope repo work detected without a runbooks commit or runbook_exit declaration
      cause: repos touched, nothing declared (§F-03)
    - signature: RUNBOOK_EXIT_MISSING runbook_exit commit SHA was not verified on the runbooks remote
      cause: prose around the SHA, unpushed commit, or stale local clone (§F-03)
    - signature: "RUNBOOK_DEBT_OPEN open runbook debt: S…-D…"
      cause: undischarged debt (§F-04)
  next_step_success: session closed; handoff carries any deferred runbook follow-ups
  next_step_failure: repair per §G-03/§G-04 and retry the close — the session stays open/reclaimable
- id: E-04
  trigger: Debt exists that genuinely warrants no runbook change this session
  pre_conditions:
    - an honest reason exists (read the accumulated-waiver history first — repeated waivers on one subject trigger the §F-07 bite at ≥2)
  tool_or_endpoint: "kd_session_close(..., runbook_exit={kind: waiver, ref_or_reason: <reason>, discharges: [ids]})"
  argument_sourcing:
    reason: plain statement of why no page changed; it is copied onto every appended waiver row
  idempotency: NOT_IDEMPOTENT
  expected_success:
    shape: one waiver row per discharged subject appended to config:runbook-waivers; debt rows marked discharged_by kind=waiver
    verification: config:runbook-waivers body.waivers tail shows the rows
  expected_failures:
    - signature: RUNBOOK_DEBT_OPEN failed to persist runbook waiver
      cause: optimistic-version conflict on the waiver entity — retry at the returned version
  next_step_success: subject now counts toward the ≥2 bite; schedule the real runbook if the subject recurs
  next_step_failure: retry; if the store is unreachable this is a Living State outage (CORE §1 degraded mode)
- id: E-05
  trigger: Discharging ANOTHER session's open debt, or clearing a waiver subject from the bite, after the covering runbook lands
  pre_conditions:
    - the covering runbook is committed and pushed (bare SHA in hand)
    - "owning entity located (debt on infra:session-status:{owning sid}:role={role}; waiver rows on config:runbook-waivers)"
  tool_or_endpoint: "state_request(action=patch, key=<owning entity>, body with the debt/waiver rows' discharged_by set to {kind: created|commit, ref_or_reason: <bare sha>, session_id, instance}, expected_version=<current>)"
  argument_sourcing:
    current_version: state_request get on the entity immediately before patching; on conflict retry at the version in the error
  idempotency: IDEMPOTENT_WITH_KEY
  idempotency_key: entity version (optimistic lock)
  expected_success:
    shape: debt rows carry discharged_by; bite counting drops the subject (only kinds created/commit clear it)
    verification: re-get the entity; next kd_session_open standup no longer tripwires the subject
  expected_failures:
    - signature: version_conflict
      cause: concurrent writer — re-get and retry
  next_step_success: log a state event referencing the discharge for the audit trail
  next_step_failure: retry with fresh version; two failures on the same patch = 2-strike, escalate
```

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `RUNBOOK_REF_MISSING` at plan or dispatch (schema/coverage) | (a) entry shape wrong — RunbookRef needs `{path, section}`, Attestation needs `{no_entry_found: true, subject, reason}` (pydantic union errors list both); (b) no refs at all on a required call; (c) all-Attestation consultation leaving objectives uncovered; (d) `covers` gaps — some 1-based objective number covered by nothing | read the error detail — it lists the uncovered objective numbers and any ignored out-of-range covers values | §G-01 | CONFIRMED |
| F-02 | `RUNBOOK_REF_UNRESOLVED` with failed_check `path`, `section`, or `registry` | path: file missing or outside the repo; section: cited heading/§-token not present in the file (resolver matches exact heading text, normalized anchor, or a literal `§X` token — a RANGE like `§A–§K` is not a heading and will not resolve); registry: `config:resource-registry` lacks a directory path for aidotmarket/runbooks (S1150: registry file-paths inside repo dicts break every `git -C`) | grep the target file for the exact heading; `state_request get config:resource-registry` and confirm the runbooks path is a directory | §G-02 | CONFIRMED |
| F-03 | `RUNBOOK_EXIT_MISSING` at close | (a) in-scope repos touched with no runbooks commit and no `runbook_exit`; (b) kind=commit/created with `ref_or_reason` that is not a bare SHA (verbatim `git cat-file -e` — prose fails it); (c) SHA valid but not present locally/on origin (unpushed, or local clone behind); historic (fixed `d9f4509d`, T-2026-000203): author-match short-circuit never set `declared_sha_verified` for instance-authored commits | run `git -C ~/Projects/ai-market/runbooks cat-file -e <exact ref_or_reason string>` yourself — rc 0 is what the gate needs | §G-03 | CONFIRMED |
| F-04 | `RUNBOOK_DEBT_OPEN` at close listing `{sid}-D{n}` ids | attestation/dispute debt appended at plan or dispatch time was never discharged; note `disputed=true` debt cannot be discharged by kind=no_change_needed | `state_request get infra:session-status:{sid}:role={role}` and read `runbook_debt` rows with `discharged_by: null` | §G-04 | CONFIRMED |
| F-05 | `stale_fetch` warning on every resolve | resolver's best-effort `git fetch origin main` (5s timeout) failing — network, SSH agent, or in-server git slowness (known, parked under the owner BQ) | run the fetch manually in the runbooks clone and read the error; warnings never block — degraded resolve against the local checkout is BY DESIGN | §G-05 | CONFIRMED |
| F-06 | `RUNBOOK_ROUTINE_CLASS_UNKNOWN` on a `triviality=routine` plan | `routine_class` missing or not in the `config:runbook-gate-config` allowlist (live set: version bump, affirm pass, LS bookkeeping, handoff write) | `state_request get config:runbook-gate-config` and compare `routine_classes` | §G-06 | CONFIRMED |
| F-07 | Plan rejected: `subject X has N accumulated runbook waivers` | the waiver bite — X has ≥2 undischarged waiver rows and appears (case-insensitive) in your objectives text | count rows for the subject in `config:runbook-waivers` lacking `discharged_by.kind` in {created, commit} | §G-07 | CONFIRMED |
| F-08 | Incident plan rejected: `…#… missing synthesis` or `synthesis matches source line` | `work_type=incident` requires a synthesis on every RunbookRef, and it must be your own words — an exact copy of any line in the cited file is rejected as non-evidence of reading | diff your synthesis string against the cited file's lines | §G-08 | CONFIRMED |
| F-09 | Boot standup tripwires a waiver subject you believe is handled | subject cleared only by discharge kinds `created`/`commit` — waiver-on-waiver or no_change_needed never clears it; or the covering runbook landed but nobody patched `discharged_by` | check the subject's rows in `config:runbook-waivers` for a `discharged_by` field | §G-07 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: Plan gate
  root_cause: consultation/refs block malformed or not covering every objective
  repair_entry_point: the failing kd_session_plan / council_request call arguments (no code change)
  change_pattern: "use exact field names — RunbookRef {path, section, synthesis?, covers?}, Attestation {no_entry_found: true, subject, reason, covers?}; ensure the union of covers (with position defaults) spans 1..N objectives; when no runbook exists, attest honestly rather than forcing a bogus ref — the attestation IS the sanctioned path and creates dischargeable debt"
  rollback_procedure: n/a — resubmit; the gate is stateless per call
  integrity_check: plan/dispatch accepted; attestation debt visible on session-status
- id: G-02
  symptom_ref: F-02
  component_ref: Ref resolver
  root_cause: cited path/section absent from the live repo, or the resource registry misconfigured
  repair_entry_point: your ref arguments; or config:resource-registry via state_request patch
  change_pattern: cite an EXACT existing heading (copy it from the file) or a bare §-token like "§F-03"; never a range or paraphrase. For failed_check=registry, patch config:resource-registry so the aidotmarket/runbooks entry carries a directory path (~/Projects/ai-market/runbooks), not a file path
  rollback_procedure: revert the registry patch (optimistic-versioned)
  integrity_check: re-run the call; resolver returns RESOLVED
- id: G-03
  symptom_ref: F-03
  component_ref: Close gate
  root_cause: exit declaration missing, or commit/created SHA unverifiable verbatim
  repair_entry_point: kd_session_close runbook_exit argument; the runbooks clone for push state
  change_pattern: declare the exit that is TRUE — commit (runbook updated, bare SHA), created (new runbook, bare SHA), no_change_needed (reason), waiver (reason, counts toward the bite). For commit/created — push first, then pass ONLY the 40-char (or unambiguous short) SHA with zero surrounding prose; if cat-file still fails, `git fetch origin main` in the clone
  rollback_procedure: n/a — the close simply retries; session stays open
  integrity_check: git cat-file -e <ref_or_reason> rc 0; close gate accepts
- id: G-04
  symptom_ref: F-04
  component_ref: Debt ledger
  root_cause: open debt at close
  repair_entry_point: runbook_exit.discharges, or the runbook work itself
  change_pattern: preferred — do the runbook work the debt names, then discharge with kind=created/commit; acceptable — kind=no_change_needed with a real reason (blocked for disputed debt); last resort — kind=waiver (feeds the bite). List every open {sid}-D{n} in discharges; the close gate only discharges ids it can see on THIS session's ledger — cross-session debt goes through §E-05
  rollback_procedure: discharge fields are plain state — re-patch discharged_by to null if set in error
  integrity_check: session-status runbook_debt has no rows with discharged_by null
- id: G-05
  symptom_ref: F-05
  component_ref: Ref resolver
  root_cause: git fetch degraded (network/agent/in-server slowness)
  repair_entry_point: runbooks clone remote config / SSH agent on Titan-1; ticket for the parked in-server slowness item (owner BQ next_action)
  change_pattern: fix the underlying fetch (ssh -T git@github.com, remote URL) if broken; if only slow, no action — stale_fetch is a warning and resolution against the local checkout is the designed degraded mode; keep the local clone reasonably fresh (git pull) so degraded resolves see new headings
  rollback_procedure: n/a
  integrity_check: manual git fetch under 5s; warnings disappear from gate responses
- id: G-06
  symptom_ref: F-06
  component_ref: Gate config
  root_cause: routine class not allowlisted
  repair_entry_point: config:runbook-gate-config body.routine_classes via state_request patch
  change_pattern: either drop triviality=routine and provide full coverage, or — for a genuinely recurring trivial class — add the class to routine_classes ONLY with a ledgered decision event naming Max approval (§H.1)
  rollback_procedure: remove the class in a follow-up ledgered patch
  integrity_check: plan with that routine_class accepted; decision event on the ledger
- id: G-07
  symptom_ref: F-07
  component_ref: Waiver store + bite
  root_cause: subject accumulated ≥2 undischarged waivers
  repair_entry_point: the covering runbook (create/update it), then config:runbook-waivers rows via §E-05
  change_pattern: "the bite exists to force the page into existence — author or update the owning runbook to standard, push, then patch the subject's waiver rows with discharged_by {kind: created|commit, ref_or_reason: <bare sha>}; the in-plan escape (an objective naming both \"runbook-coverage\" and the subject, itself covered) is for the session doing exactly that work"
  rollback_procedure: re-patch discharged_by to null
  integrity_check: next kd_session_plan naming the subject passes; boot tripwire drops it
- id: G-08
  symptom_ref: F-08
  component_ref: Plan gate
  root_cause: incident synthesis missing or copied verbatim
  repair_entry_point: the synthesis field on each incident-plan RunbookRef
  change_pattern: write one line in your own words stating what the cited section says to do for THIS incident — the check exists to prove the section was read, so a paraphrase that would not fool a reviewer is the bar
  rollback_procedure: n/a — resubmit
  integrity_check: incident plan accepted
```

## §H. Evolve

### §H.1 Invariants

- **The gate never reads memory:** refs resolve against the live `aidotmarket/runbooks` checkout located via `config:resource-registry` — never a hardcoded path, never a cached copy.
- **Attestations always create debt:** every `no_entry_found` and every `runbook_disputed` appends a dischargeable `{sid}-D{n}` row. No silent bypass exists or may be added.
- **Waiver store is append-only, single-shape:** `config:runbook-waivers` `body.waivers` list only; `subjects`/`counts` dict shapes are forbidden (double counting). Rows are never deleted — clearing is by `discharged_by` kinds `created`/`commit` only.
- **enforce_mode flips are ledgered Max decisions:** warn↔block only via a deliberate `config:runbook-gate-config` patch plus a decision event naming Max approval (precedent: S1150 flip, event bba08b07). Same rule for `routine_classes` edits.
- **Warnings never block:** `stale_fetch` and `stale_runbook` are informational in both modes; degraded resolve against the local checkout is the designed fallback.
- **Every gate evaluation is evented:** one `runbook_gate` event per plan/dispatch/close evaluation, both modes, pass or fail.
- **Design Charter sizing:** the gates are trusted-peer machinery — no signing, no lease tokens; optimistic versions and plain state fields only. Do not add adversary-grade mechanisms.

### §H.2 BREAKING predicates

BREAKING if ANY of (first match wins):
- Removing or bypassing any of the three gate points, or adding a bypass that skips debt creation for attestations/disputes.
- Changing the `RUNBOOK_*` error-code contract (codes, or which condition maps to which code) — callers and runbooks key off it.
- Changing the waiver-store shape or the debt-row `id` scheme (`{sid}-D{n}`).
- Making warnings blocking, or making block-mode rejects silent.
- Changing or removing any §H.1 invariant.

### §H.3 REVIEW predicates

REVIEW if ANY of (after BREAKING predicates fail):
- Adding a new gate point (Phase 2/3 surfaces: bq_complete, BQ gates, tickets, CI) — each is a spec'd chunk under the owner BQ with its own gate flow.
- Changing the bite threshold (≥2), the required-modes set (build/author + incident review), the 90-day freshness window, the 60-line injection cap, or the 5s fetch timeout.
- Extending section-cited injection to optional RESOLVED refs (recorded follow-up).
- Changing coverage semantics (`covers` defaults, coercion, range handling).

### §H.4 SAFE predicates

SAFE otherwise:
- Documentation and test additions; error-message wording that preserves the codes.
- Refreshing this runbook's §B/§J after verifications.

### §H.5 Boundary definitions

#### module

Per the standard, applied to `koskadeux-mcp`: immediate subdirectories of the source root (`tools/`, `runbook_tools/` in the runbooks repo). The gates live in `tools/` (session.py, agents.py, runbook_ref.py).

#### public contract

The `kd_session_plan` / `council_request` / `kd_session_close` MCP tool signatures (including `runbook_consultation`, `runbook_refs`, `runbook_exit` schemas) and the `RUNBOOK_*` error codes.

#### runtime dependency

`koskadeux-mcp` `pyproject.toml [project.dependencies]`. The gates added none (pydantic + git already present).

#### config default

Values shipping in `config:runbook-gate-config` (`enforce_mode`, `routine_classes`). Live values are state, but the warn default on unreadable config is code-shipped.

### §H.6 Adjudication

The more restrictive classification wins between disagreeing agents. Disputes unresolvable under the predicates escalate to Max; the ruling is added to §H.1 as a clarification.

## §I. Acceptance Criteria

```yaml acceptance
scenario_set:
  - id: I-01
    type: operate
    refs: [E-01]
    scenario: You are opening a session with three objectives and TOPIC-ROUTER shows an owning runbook for each. What does the runbook_consultation block contain?
    expected_answers:
      - kind: human_action
        action: one RunbookRef {path, section} per owning runbook with covers spanning objectives 1-3 (or positional defaults), sections copied as exact existing headings
    weight: 0.08333333
  - id: I-02
    type: operate
    refs: [E-02]
    scenario: Dispatching an MP build for which no runbook exists anywhere in the router. First action?
    expected_answers:
      - kind: tool_call
        tool: council_request
        arguments: "[agent, mode, task, runbook_refs containing an Attestation {no_entry_found: true, subject, reason}]"
      - kind: human_action
        action: dispatch with an honest no_entry_found Attestation in runbook_refs, accepting the dischargeable debt it creates
    weight: 0.08333333
  - id: I-03
    type: operate
    refs: [E-03]
    scenario: Closing a session that updated gateway-transport.md, committed and pushed as abc1234def. What is runbook_exit?
    expected_answers:
      - kind: human_action
        action: 'runbook_exit {kind: commit, ref_or_reason: the bare SHA abc1234def with no surrounding prose, discharges: [any open debt ids it covers]}'
    weight: 0.08333333
  - id: I-04
    type: isolate
    refs: [F-02]
    scenario: kd_session_plan rejected RUNBOOK_REF_UNRESOLVED section for {path codex-mp.md, section "§F timeouts and mutexes"}. First action?
    expected_answers:
      - kind: human_action
        action: grep codex-mp.md for the exact heading and cite it verbatim (or the bare §-token) — the resolver matches exact heading text, anchors, or §-tokens only
    weight: 0.08333333
  - id: I-05
    type: isolate
    refs: [F-03]
    scenario: 'Close rejected: runbook_exit commit SHA was not verified on the runbooks remote, but you did push the commit. First action?'
    expected_answers:
      - kind: human_action
        action: run git cat-file -e against the exact ref_or_reason string in the runbooks clone — prose around the SHA or a stale clone fails the verbatim check
    weight: 0.08333333
  - id: I-06
    type: isolate
    refs: [F-05]
    scenario: Every plan resolve carries a stale_fetch warning but plans are accepted. Is anything broken and what do you check?
    expected_answers:
      - kind: human_action
        action: nothing is blocked — warnings never reject; manually run git fetch in the runbooks clone to see the underlying network/SSH cause and keep the local clone fresh
    weight: 0.08333333
  - id: I-07
    type: isolate
    refs: [F-09]
    scenario: Boot standup tripwires waiver subject "e2e-testing-framework" although its runbook shipped last week. First action?
    expected_answers:
      - kind: human_action
        action: check the subject's rows in config:runbook-waivers — only discharged_by kind created/commit clears the bite; patch the rows with the covering runbook's bare SHA per §E-05
    weight: 0.08333333
  - id: I-08
    type: repair
    refs: [G-04]
    scenario: Close rejected RUNBOOK_DEBT_OPEN for S1200-D2, an attestation about a procedure you did in fact document this session at SHA 9f9f9f9. Fix?
    expected_answers:
      - kind: human_action
        action: 'retry close with runbook_exit {kind: created (or commit), ref_or_reason: 9f9f9f9 bare, discharges: [S1200-D2]}'
    weight: 0.08333333
  - id: I-09
    type: repair
    refs: [G-06]
    scenario: A plan tagged triviality=routine, routine_class="typo fix" is rejected RUNBOOK_ROUTINE_CLASS_UNKNOWN. Fix without Max?
    expected_answers:
      - kind: human_action
        action: drop the routine tag and provide full per-objective coverage — adding a class to the allowlist requires a ledgered decision naming Max approval
    weight: 0.08333333
  - id: I-10
    type: evolve
    refs: [§H.2]
    scenario: A proposed change maps the unresolved-section condition to a new error code RUNBOOK_SECTION_BAD for clarity. Classify.
    expected_answers:
      - kind: classification
        verdict: BREAKING
    weight: 0.08333333
  - id: I-11
    type: evolve
    refs: [§H.3]
    scenario: A proposed change raises the cited-section injection cap from 60 to 120 lines. Classify.
    expected_answers:
      - kind: classification
        verdict: REVIEW
    weight: 0.08333333
  - id: I-12
    type: ambiguous
    refs: [F-01, F-07]
    scenario: 'kd_session_plan rejected with detail listing BOTH "objectives uncovered (1-based): [3]" AND "subject account-teardown has 3 accumulated runbook waivers". What is the correct set of first actions?'
    expected_answers:
      - kind: human_action
        action: fix coverage for objective 3 AND address the bite — either add a covered runbook-coverage objective naming account-teardown, or first do/verify the covering runbook and discharge the waiver rows per §E-05; both errors must clear, either order
    weight: 0.08333333
```

## §J. Lifecycle

```yaml lifecycle
last_refresh_session: S1180
last_refresh_commit: 9916abf
last_refresh_date: 2026-07-11T09:30:00Z
owner_agent: vulcan
refresh_triggers:
  - any Phase 2/3 chunk of BQ-RUNBOOK-FIRST-ENFORCEMENT-S1146 landing (new gate points)
  - enforce_mode or routine_classes change on config:runbook-gate-config
  - any dev ticket rooted in a RUNBOOK_* gate behavior
  - changes to tools/runbook_ref.py, or to the gate functions in tools/session.py / tools/agents.py
scheduled_cadence: 90d
last_harness_pass_rate: PENDING_HARNESS_TOOLING (BQ-RUNBOOK-HARNESS-COMPACT-IO)
last_harness_date: 2026-07-11T09:30:00Z
first_staleness_detected_at: null
```

Refresh log:
- S1180 (2026-07-11): first authoring, against code ground truth read this session (tools/runbook_ref.py, tools/session.py plan/close gates, tools/agents.py dispatch gate) plus live entities (config:runbook-gate-config v2 block-mode, config:runbook-waivers v10). Discharges S1149-D1..D8 (subject runbook-first-gates) and clears the S1177-D1 boot-coordination waiver subject. `last_refresh_commit` references the pre-refresh main head (9916abf); this file lands in its child commit.

## §K. Conformance

```yaml conformance
linter_version: 1.0.0
last_lint_run: S1180 / 2026-07-11T09:30:00Z
last_lint_result: PASS
trace_matrix_path: null
word_count_delta: null
```
