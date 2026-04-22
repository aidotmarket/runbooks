# BQ-RUNBOOK-STANDARD — Gate 2 Chunk 2 (R1)

**Parent BQ:** `build:bq-runbook-standard`
**Chunk:** Gate 2 Chunk 2 — Gate 1 §9 Deliverables D4 + D5
**Chunk 1 contract:** `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md` @ commit `ea70326`
**Gate 1 frozen standard:** `specs/BQ-RUNBOOK-STANDARD.md` @ commit `365c198`
**Revision:** R1
**Author:** Vulcan
**Authored session:** S489

---

## 1. Purpose

This chunk specifies how the first two first-party runbooks under the system-wide Runbook Standard are authored and verified:

- **D4 — Infisical runbook** (Gate 1 §9 step 4). The initial reference implementation. Authored by Vulcan from scratch using only the frozen standard plus Infisical system evidence. Validated by the Chunk 1 tooling and the Vulcan-authored §I scenario set.
- **D5 — AIM Node runbook** (Gate 1 §9 step 5). The G4 falsifiability test. Authored by Vulcan against the frozen standard with no access to the D4 runbook content. Evaluated against an externally-authored hidden scenario set produced under the Gate 1 §7 G4 protocol (MP + AG authoring, MP + AG reconciliation, XAI correspondence challenger, AG scoring).

Chunk 2 is a design-level Gate 2 specification. It does not contain the runbook content itself — runbook authoring is the Chunk 2 Gate 3 build. What this spec contains is the authoring contract, the isolation mechanism, the G4 integration shape on the runbook side, the verification contract Gate 3 will check, and the sequencing between D4 and D5.

Chunk 2 does NOT re-open Gate 1 of the parent BQ. The frozen standard is unchanged. Chunk 2 also does not modify Chunk 1 tooling; if Chunk 2 authoring exposes a Chunk 1 gap, the defect is filed as a follow-on BQ rather than smuggled into Chunk 2.

---

## 2. Scope boundary

**In scope for Gate 2 Chunk 2:**
- Authoring contract for `infisical.md` (new filename) per D4
- Authoring contract for `aim-node.md` (existing filename, content replaced) per D5
- Sequencing between D4 and D5 authoring
- Isolation mechanism enforcing "no D4 read during D5 authoring"
- G4 attempt lifecycle integration on the runbook-author (Vulcan) side
- Verification contract that Chunk 2 Gate 3 will check per deliverable
- Pre-Gate-3 preflight (both runbooks pass Chunk 1 linter on draft before MP / G4 dispatch)
- Handling of existing pre-standard files (`infisical-secrets.md`, `aim-node.md`)

**Out of scope for Gate 2 Chunk 2:**
- Koskadeux-side G4 machinery (`g4_attempt_id` issuance, attempt-registry / attempt-manifest entity writes, stall escalation timers). Gate 1 §7 assigns this to Koskadeux; it is a prerequisite dependency, not this chunk's build target. Filed as `BQ-KOSKADEUX-G4-PROTOCOL` (see §10 open questions if not already filed).
- XAI correspondence-check instructions (those live in Koskadeux as XAI dispatch prompts, not in this spec).
- CRM retrofit content (Gate 1 §9 step 6 — Chunk 3 or child BQ).
- Celery retrofit content (Gate 1 §9 step 7 — Chunk 4 or child BQ).
- Any change to Chunk 1 tooling design or to the Gate 1 frozen standard.
- AIM Node Phase 2 adapter types, multi-protocol support, or anything outside the AIM Node §A–§K runbook content. The runbook reflects the system AS IT IS; system changes are separate BQs.

**Deferred to Chunk 2 Gate 3 (build):**
- Actual authoring of `infisical.md` (D4 runbook content)
- Actual authoring of `aim-node.md` (D5 runbook content)
- Actual §I scenario sets per runbook (Vulcan-authored for D4, Vulcan-authored-for-self-assertion + externally-authored-for-G4 for D5)
- Evidence of runbook-lint PASS on both runbooks
- Evidence of Vulcan-authored harness score ≥ 0.80 on the D4 runbook's §I set
- Evidence of the full G4 attempt lifecycle completing with terminal status `passed` on the D5 runbook

---

## 3. Repository layout (post-Gate 3 Chunk 2)

Chunk 2 adds runbook content to an existing tooling scaffold. It does not relocate the tooling.

```
aidotmarket/runbooks/
├── README.md                             # Chunk 1, index (updated in Chunk 2 to mark Infisical + AIM Node as Adopted)
├── runbook_tools/                        # Chunk 1 (unchanged)
├── harness/                              # Chunk 1 scaffold (unchanged)
├── schemas/                              # Chunk 1 (unchanged)
├── templates/                            # Chunk 1 (unchanged)
├── tests/                                # Chunk 1 (unchanged)
├── infisical.md                          # Chunk 2 D4 — NEW file, replaces infisical-secrets.md
├── aim-node.md                           # Chunk 2 D5 — CONTENT REPLACED
├── specs/
│   ├── BQ-RUNBOOK-STANDARD.md            # Gate 1 (frozen at 365c198)
│   ├── BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md  # Chunk 1 (frozen at ea70326)
│   └── BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-2.md  # THIS SPEC
└── (other pre-standard .md files at repo root)  # untouched in Chunk 2
```

**Handling of existing pre-standard files:**

- `infisical-secrets.md` (3570 bytes, authored S357, pre-standard). **Deleted** in the Chunk 2 Gate 3 build PR that lands `infisical.md`. Rationale: the old file predates the standard and is replaced end-to-end by the new conformant runbook. Git history preserves it. No archive copy needed because it is not a retrofit of a legacy whose structure is being preserved — it is pre-standard scrap.
- `aim-node.md` (12115 bytes, authored S392-ish, pre-standard). **Content replaced wholesale** in the Chunk 2 Gate 3 build PR that lands the new version. The filename stays (already correct). The old content is in git history.
- All other pre-standard `.md` files at the repo root remain untouched in Chunk 2. They are Gate 1 §9 steps 6-8 work (CRM, Celery, remaining systems) or documentation not yet in the standard's adoption scope.

**README.md index update (Chunk 2):**

Gate 3 Chunk 2 updates the "Adoption status" section of `README.md` to move Infisical and AIM Node from their current statuses to `Adopted`, with the relevant metadata (linter_version, last_lint_run, last_harness_date, harness_score) per Gate 1 §6.

---

## 4. D4 — Infisical runbook authoring contract

### 4.1 Classification

- **Runbook type:** from-scratch authoring (not retrofit)
- **§K.retrofit field:** `null` (no `trace_matrix`, no `word_count_delta`, no `mp_orphan_review`, no `procedural_coverage_matrix`)
- **Authoring agent:** Vulcan
- **Scope:** all of Infisical as deployed at `https://secrets.ai.market` per the current system state, including machine identities, environments, secret rotation, Railway integration, and SMTP configuration

### 4.2 System evidence Vulcan MAY use during authoring

- The frozen standard (`specs/BQ-RUNBOOK-STANDARD.md` @ `365c198`)
- Chunk 1 tooling outputs (runbook-lint errors on drafts, schema validation errors)
- The existing pre-standard `infisical-secrets.md` (for content reference, not structure)
- Live Infisical dashboard and Infisical CLI invocations (read-only where possible)
- `config:resource-registry` Living State entity for canonical resource identifiers
- `infra:council-comms` Living State entity where relevant to machine identity policy
- Railway project configuration for projects that depend on Infisical (read-only)

### 4.3 Required coverage

The runbook MUST cover, at minimum, these real capabilities and incident types (the §B Capability Matrix must enumerate all of them with status ∈ `{Live, PARTIAL, Planned}`):

| Capability | Required coverage |
|---|---|
| Secret read (CLI, API, web) | §E Operate scenarios |
| Secret write (dashboard, CLI, API) | §E Operate scenarios |
| Secret rotation | §E Operate + §G Repair scenarios |
| Machine identity creation | §E Operate |
| Machine identity rotation | §G Repair |
| Environment promotion (dev→staging→prod) | §E Operate |
| Railway env var sync discipline | §E Operate + §F Isolate (drift detection) |
| SMTP (Resend) configuration | §E Operate + §F Isolate |
| Infisical service outage | §F Isolate + §G Repair |
| Admin account lockout | §F Isolate + §G Repair (Emergency Kit PDF) |
| Token auth failure from machine identity | §F Isolate + §G Repair |
| Migration from Doppler | §H Evolve (if still in flight) or §K Conformance note (if fully retired) |

### 4.4 §I scenario set requirements

Per Gate 1 §4 §I and Gate 1 §7 G3:

- **Minimum count:** ≥ 10 scenarios
- **Distribution:** per Gate 1 §4 §I diversity rules (operate / isolate / repair / success / failure across the enumerated capabilities)
- **Authoring:** Vulcan
- **Weighting:** equal-weight default unless explicit per-scenario justification is written into the §I YAML block per Gate 1 §4 §I
- **Target weighted score:** ≥ 0.80 on the Chunk 1 harness when AG dispatches the stateless-agent harness run against this runbook

The §I scenarios are Vulcan-authored and land in the runbook itself. They are NOT the G4-style hidden eval — D4 is the reference implementation on the normal path.

### 4.5 Gate 3 verification contract for D4

Chunk 2 Gate 3 Acceptance Criteria for D4:

1. `runbook-lint infisical.md` exits 0 (all 20 checks PASS); linter_version and all §A/§J metadata fields populated per §K.0 and §J.
2. `runbook-harness --runbook infisical.md --answer-key infisical.md --section I` produces a weighted total ≥ 0.80.
3. §I scenario count ≥ 10 with distribution matching Gate 1 §4 §I rules.
4. All 11 agent forms (§A–§K) present and validating against their Chunk 1 schemas.
5. `infisical-secrets.md` deleted in the same PR (single transaction).
6. `README.md` Adoption Status table updated: Infisical row moves to `Adopted`.
7. MP first-pass design review on the authored runbook: verdict `APPROVE` or `APPROVE_WITH_NITS`.

### 4.6 D4 out of scope

- G4 protocol does NOT apply to D4. D4 is the reference implementation on the normal path.
- XAI correspondence challenger does NOT run on D4 (no externally-authored eval set; nothing to correspondence-bias against).
- Doppler decommission itself is not in scope — the runbook describes current-state Infisical.

---

## 5. D5 — AIM Node runbook authoring contract (G4 falsifiability)

### 5.1 Classification

- **Runbook type:** from-scratch authoring (not retrofit)
- **§K.retrofit field:** `null`
- **Authoring agent:** Vulcan, in G4 frozen-standard mode
- **Scope:** AIM Node peer-to-peer data plane, provider + consumer modes, wire protocol, session lifecycle, security model, adapter contracts (Phase 1 HTTP/JSON only), and documented edge cases per the aim-node.md pre-standard content's scope as of `365c198` freeze.
- **G4 frozen_commit_sha:** `365c198` (from `build:bq-runbook-standard` entity, `gate1.approved_commit`)

### 5.2 G4 attempt lifecycle (runbook-author side)

Per Gate 1 §7 G4 steps 2 and 3, before Vulcan writes a single line of `aim-node.md` content, the following attempt-open sequence runs:

1. **Vulcan generates `request_nonce`** (UUID v4, fresh per open).
2. **Vulcan emits Living State event** `event_type=g4-attempt-opened`, `entity_key=build:bq-runbook-standard`, payload:
   ```json
   {
     "frozen_commit_sha": "365c198",
     "opened_by": "vulcan",
     "retry_case": null,
     "prior_attempt_id": null,
     "request_nonce": "<uuid_v4>"
   }
   ```
3. **Vulcan polls** the per-frozen-commit manifest at `state:bq-runbook-standard:g4:aim-node:365c198:attempt-manifest` for an entry whose `request_nonce` matches step 1. Poll is exponential-backoff from 100ms, capped at 10 seconds total. On match, Vulcan reads `g4_attempt_id` out of the matched manifest entry.
4. **Vulcan reads per-attempt registry** at `state:bq-runbook-standard:g4:aim-node:365c198:{g4_attempt_id}:attempt-registry` to confirm authoritative state.
5. **Vulcan begins authoring** only after registry read confirms `status: 'active'`.

Retry cases (Case A/B/C/D per Gate 1 §7 step 8) each reopen via a new `g4-attempt-opened` event with appropriate `retry_case` and `prior_attempt_id`. Each retry gets a new `g4_attempt_id`; prior artifacts preserved under old namespaces.

### 5.3 Authoring isolation — "no D4 read during D5 authoring"

The central G4 integrity requirement for the runbook-author side: Vulcan MUST NOT read or otherwise reference the D4 Infisical runbook content during D5 AIM Node authoring.

**R1-proposed enforcement stack** (layered; R2 will refine based on MP feedback on which layers are necessary):

1. **Session-plan declaration.** The Vulcan session that authors D5 declares in its `kd_session_plan` objectives that it is authoring against G4 frozen standard `365c198` with attempt `{g4_attempt_id}` and will not read `infisical.md`. This is the promise.

2. **Operational discipline.** Vulcan does not invoke any tool call that reads `infisical.md` (shell `cat`, `view`, `grep` against it, `web_fetch` of a URL containing its content, or indirect read via agent dispatch that surfaces it). Vulcan also does not dispatch any agent task that instructs the agent to summarize or reference `infisical.md`.

3. **Post-hoc session-transcript audit.** After D5 authoring session closes, a non-Vulcan auditor (proposed: MP via a read-only audit task) reviews the session's tool-call log for any read of `infisical.md`. A single confirmed read fails the G4 attempt (Case A if the read was required to author, Case B if it was incidental and the runbook can be re-authored cleanly).

4. **(R2 CANDIDATE, not commitment for R1)** A Koskadeux-side denied-paths wrapper for Vulcan's shell and view tools during the D5 authoring session, driven by a session-plan flag `g4_authoring_session=true`. Would physically block reads of `infisical.md`. Touches Koskadeux surface and is proposed as a follow-on `BQ-KOSKADEUX-G4-AUTHORING-ISOLATION`. Not a Chunk 2 blocker; the three layers above are sufficient for R1.

### 5.4 D5 harness / scenario model (dual-purpose)

The D5 AIM Node runbook has TWO scenario sets that both run against the harness, for distinct purposes:

| Set | Authors | Location | Purpose | Gate 3 AC |
|---|---|---|---|---|
| **Self-assertion §I set** | Vulcan | inside `aim-node.md` §I fenced YAML block | runbook template completeness + Vulcan's own claim of coverage | runbook-lint validates count ≥ 10 and distribution; harness runs it; score tracked but not the G4 AC |
| **G4 hidden eval set** | MP + AG (reconciled) | Living State `state:bq-runbook-standard:g4:aim-node:365c198:{g4_attempt_id}:answer-key` | externally-authored correctness check for G4 | AG-scored weighted total ≥ 0.80 per Gate 1 §7 G4 step 7 |

The two sets are independent. Vulcan does not see the G4 hidden set. MP + AG do not need to match the self-assertion set. The G4 pass criterion in Gate 1 §7 G4 step 7 is measured against the hidden set, not the self-assertion set.

**R2 open question:** Is there any harness-run configuration gap between "runbook-lint §I set" (Chunk 1 default) and "G4 hidden set" (runtime-supplied answer-key)? Chunk 1 §6.2 defines the expected-answer key format and §6.3 defines MP dispatch. Confirm the harness runner accepts a `--answer-key` override path for G4 or needs a follow-on BQ.

### 5.5 Gate 3 verification contract for D5

Chunk 2 Gate 3 Acceptance Criteria for D5:

1. **Attempt opened.** `g4-attempt-opened` event logged; attempt-registry status `active` at authoring start.
2. **Isolation invariant held.** Post-hoc audit of Vulcan's D5 authoring session shows zero reads of `infisical.md`. Auditor: MP via a dedicated read-only audit task.
3. **Runbook passes lint.** `runbook-lint aim-node.md` exits 0.
4. **Self-assertion harness ≥ 0.80.** Standard harness run against §I self-assertion set produces weighted total ≥ 0.80.
5. **G4 hidden eval-set authoring complete.** MP + AG each authored a ≥ 10-scenario draft independently; reconciled into a single set; reconciliation transcript logged to `…:reconciliation-transcript` (create-only); final answer-key logged to `…:answer-key` (create-only).
6. **XAI correspondence verdict.** XAI dispatched with the `(answer-key, aim-node.md)` pair; verdict ∈ `{CLEAN, MINOR_OVERLAP}` (not `SUSPECT_OVERFITTING`). Verdict logged to `…:xai-correspondence-verdict`.
7. **MP first-pass design review.** Verdict ∈ `{APPROVE, APPROVE_WITH_NITS}`. Runs in a session separate from MP's G4 eval-set-authoring session (reviewer-independence constraint per Gate 1 §7 G4 step 6).
8. **AG harness score ≥ 0.80.** AG scores the runbook against the G4 answer-key. Weighted total ≥ 0.80. Score logged to `…:harness-result`.
9. **Attempt-registry status transitions to `passed`.** Koskadeux patches status on harness-result write per Gate 1 §7 G4 step 9 state machine.
10. **README.md updated.** AIM Node row moves to `Adopted`.

If any of criteria 2-8 fail, the attempt fails under the relevant retry Case per Gate 1 §7 G4 step 8. Chunk 2 Gate 3 does not pass until an attempt reaches `passed`.

### 5.6 D5 review-role separation

Per Gate 1 §7 G4 step 6:
- **MP authors** part of the hidden eval set (with AG) AND does the first-pass design review. These MUST be two different MP dispatch sessions.
- **AG authors** part of the hidden eval set (with MP) AND runs the harness scorer. These MUST be two different AG dispatch sessions.
- **XAI** runs correspondence challenger only; does not score.
- **Vulcan** does not see the hidden eval set before or during authoring.

Each role's dispatch is a separate task in Koskadeux's task-id registry with session attribution recorded in the logged artifact (`mp_session`, `ag_session`, `scored_session`, etc. per Gate 1 §7 step 4).

### 5.7 D5 out of scope

- Koskadeux-side implementation of attempt issuance, entity writes, status-transition patches, and stall-escalation timers. Prerequisite dependency.
- XAI prompt engineering for correspondence-bias detection. Koskadeux-side.
- AG harness-scorer runtime infrastructure. Chunk 1 tooling handles the scoring algorithm; dispatch orchestration is Koskadeux.

---

## 6. Sequencing & dependencies

### 6.1 D4 before D5

D4 authoring completes (runbook lands, runbook-lint PASS, self-authored harness ≥ 0.80, MP design review APPROVE) BEFORE any D5 `g4-attempt-opened` event is emitted.

Rationale:
- D4 proves the standard + Chunk 1 tooling work end-to-end on the normal path before the G4 falsifiability test. If D4 cannot be authored cleanly, the standard has a non-falsifiability defect (Case A-analog at the Chunk 2 level) that must be resolved before the G4 test runs.
- D5's "no D4 read" constraint is easier to enforce once D4 is frozen at a known commit SHA than when it is an in-flight draft.
- Gate 1 §9 lists D4 before D5.

### 6.2 D4 and D5 in a single Chunk 2 Gate 3 build vs two sub-builds

**R1 proposal:** Two sub-builds within Chunk 2 Gate 3.

- **Chunk 2 Gate 3 Build 1 (G3-B1):** D4 Infisical. Lands `infisical.md`, deletes `infisical-secrets.md`, updates README index, lint PASS, harness ≥ 0.80, MP design-review APPROVE. Single PR.
- **Chunk 2 Gate 3 Build 2 (G3-B2):** D5 AIM Node. Full G4 attempt. Lands replacement `aim-node.md` content, updates README index, full G4 attempt lifecycle terminates `passed`. Single PR (plus the Living State attempt-scoped entity writes, which are out-of-repo).

G3-B1 and G3-B2 are sequenced (B1 before B2 per §6.1). Each has its own MP review round and its own commit on main. The parent BQ stays in `gate3_in_progress` until G3-B2 terminates `passed`.

**Alternative considered:** single atomic PR containing both runbooks. Rejected because:
- G4 attempt lifecycle is stateful across multiple dispatches over hours-to-days; cannot cleanly pack into a single PR commit.
- D4 authoring review cycle and D5 G4 review cycle have different agent participation and verdict shapes; merging them into one review obscures failure attribution.

### 6.3 Dependency on Koskadeux-side G4 machinery

Gate 1 §7 G4 assigns the following to Koskadeux:
- `g4_attempt_id` issuance
- Per-attempt registry entity create-only writes
- Per-frozen-commit manifest patch with optimistic locking
- Attempt-registry `status` transitions (`active` → `stalled` → `superseded` / `aborted` / `passed` / `failed`)
- 48h stall detection + 72h escalation event emission

Chunk 2 cannot complete Gate 3 without this machinery existing. R1 proposes filing (or confirming filed) a P0 dependency BQ: `BQ-KOSKADEUX-G4-PROTOCOL`. Chunk 2 Gate 3 G3-B2 dispatch is blocked on that BQ reaching `gate3_approved`.

**Open question for R2:** is this dependency already in the Living State entity graph, or does R1 need to file it?

---

## 7. Pre-Gate-3 preflight (Chunk 2 Gate 2 acceptance scope)

Chunk 2 Gate 2 (this spec) does NOT author the runbooks. It authors the contract. Gate 2 AC is MP APPROVE + AG cross-vote APPROVE on this spec document.

However, to reduce Gate 3 rework cost, R1 proposes a **pre-Gate-3 preflight** at Gate 2 approval:

1. Vulcan runs `runbook-new infisical.md` (Chunk 1 template scaffold) and confirms the placeholder template lands WITH zero `FAIL` lint placeholders, only `WARN` placeholders requiring Gate 3 content. Purpose: confirm the Chunk 1 template validator covers D4's shape.
2. Vulcan runs `runbook-new aim-node.md` (overwrite permission required since file exists) and confirms same. Purpose: confirm the template covers D5's shape.

If either preflight uncovers a Chunk 1 template gap (a section where the placeholder shape does not match the Gate 1 form grammar), a defect is filed as a follow-on BQ against Chunk 1 rather than fixed in Chunk 2. This protects the Chunk 1 freeze.

**R2 open question:** should the preflight be a Gate 2 AC (blocks Gate 2 APPROVE until it passes) or a Gate 3 pre-dispatch check (blocks G3-B1 dispatch)? R1 proposes the latter — Gate 2 AC is design approval; preflight is build-readiness.

---

## 8. Test suite — Gate 3 acceptance criteria summary

Consolidation of §4.5 + §5.5 for reviewer convenience:

| # | AC | Deliverable | Source of truth |
|---|---|---|---|
| 1 | `runbook-lint infisical.md` exits 0 | D4 | CI workflow + local invocation |
| 2 | Harness weighted total ≥ 0.80 on §I | D4 | Chunk 1 harness runner |
| 3 | §I scenario count ≥ 10, distribution per §I rules | D4 | runbook-lint |
| 4 | MP design review APPROVE / APPROVE_WITH_NITS | D4 | MP dispatch task |
| 5 | `infisical-secrets.md` deleted in same PR | D4 | git diff |
| 6 | README Adoption table updated | D4 | git diff |
| 7 | `g4-attempt-opened` event logged | D5 | Living State event ledger |
| 8 | Zero `infisical.md` reads in D5 authoring session | D5 | MP audit of session transcript |
| 9 | `runbook-lint aim-node.md` exits 0 | D5 | CI workflow + local invocation |
| 10 | Self-assertion harness ≥ 0.80 | D5 | Chunk 1 harness runner |
| 11 | G4 eval-set authored + reconciled + logged | D5 | MP + AG dispatches; Living State artifacts |
| 12 | XAI correspondence verdict ∈ {CLEAN, MINOR_OVERLAP} | D5 | XAI dispatch task |
| 13 | MP first-pass design review APPROVE / APPROVE_WITH_NITS | D5 | MP dispatch task (separate session from eval-authoring) |
| 14 | AG-scored G4 harness ≥ 0.80 | D5 | AG dispatch task |
| 15 | Attempt-registry terminal status `passed` | D5 | Living State attempt-registry read |
| 16 | README Adoption table updated | D5 | git diff |

---

## 9. Gate boundaries (Gate 2 vs Gate 3 for this chunk)

**Gate 2 (this spec) delivers design:**
- Authoring contract for D4 (from-scratch, Vulcan-authored, ≥ 10 §I scenarios)
- Authoring contract for D5 (G4 frozen-standard, Vulcan-authored, hidden eval set)
- Isolation mechanism for "no D4 read during D5 authoring" with a three-layer enforcement stack + a proposed R2 fourth layer
- G4 attempt lifecycle integration on the Vulcan (author) side (event + manifest poll + registry read)
- Verification contract enumerating 16 Gate 3 ACs
- Sequencing: D4 then D5; two sub-builds (G3-B1, G3-B2); parent BQ stays in gate3_in_progress through both
- Pre-Gate-3 preflight proposal (template shape check) against Chunk 1 scaffold
- Dependency on `BQ-KOSKADEUX-G4-PROTOCOL` for Koskadeux-side G4 machinery

**Gate 3 (build, post-approval) delivers:**
- G3-B1: `infisical.md` authored, `infisical-secrets.md` deleted, README updated, all 6 D4 ACs met
- G3-B2: `aim-node.md` authored under G4 attempt, all 10 D5 ACs met, attempt status `passed`

**Gate 4 (production verification, post-build):**
- First post-adoption lint-cycle on both runbooks comes back clean in nightly CI.
- First scheduled staleness detection for the Infisical runbook emits the correct `first_staleness_detected_at` row (seeded by altering a §J field). Evidence: commit diff.
- A third-party system change (e.g., a new machine identity added) is correctly identified as a §H change class by a runbook re-review agent using only the runbook's §H decision tree. Evidence: dispatch transcript.

---

## 10. Open questions for reviewers (R1 status)

1. **Infisical filename rename** (`infisical-secrets.md` → `infisical.md`). Rationale: Gate 1 §6 convention uses short system names. Counter-argument: retains continuity with other existing `*-secrets.md` patterns. R2 decision needed; easy to reverse.

2. **`BQ-KOSKADEUX-G4-PROTOCOL` filing status.** Gate 1 §7 G4 assigns attempt-id issuance + entity writes + state transitions to Koskadeux. Has a P0 BQ already been filed for the Koskadeux-side implementation, or does R1 need to file it? Chunk 2 Gate 3 G3-B2 blocks on it.

3. **Isolation layer 4 — Koskadeux denied-paths wrapper.** §5.3 layer 4 (physical block on `infisical.md` reads during D5 authoring) is proposed as a follow-on BQ rather than a Chunk 2 blocker. R2 needs to confirm that the three-layer discipline (session-plan declaration + operational discipline + post-hoc audit) is sufficient without physical enforcement for G4 integrity.

4. **Harness `--answer-key` override for D5 G4 run.** §5.4 R2 open question: confirm that the Chunk 1 harness runner (`runbook_tools/harness/`) already accepts a runtime-supplied answer-key path distinct from the runbook's own §I, OR file a Chunk 1 follow-on BQ for the capability.

5. **Atomic vs split PR for Chunk 2 G3.** §6.2 proposes two sub-builds (G3-B1, G3-B2). Alternative: single atomic PR covering both runbooks. R1 proposes split; R2 confirms.

6. **Preflight as Gate 2 AC vs Gate 3 pre-dispatch check.** §7 R2 open question.

7. **§I self-assertion vs hidden-set overlap for D5.** §5.4 notes the two sets are independent. R2: confirm there is no Gate 3 AC interaction (e.g., "self-assertion set must not have scenarios the hidden set also covers, to avoid double-counting"). R1 proposal: no such rule; sets are independent evidence streams.

8. **Retry case reopening authority.** Gate 1 §7 G4 step 8 says Koskadeux issues every `g4_attempt_id`. For Case A (spec revision), does Max need to explicitly authorize the retry, or does Vulcan self-open a new attempt under the new frozen_commit_sha? R2 clarification.

9. **Deletion of `infisical-secrets.md`.** §3 proposes deletion in the same PR as `infisical.md` landing. R2: confirm there are no inbound references elsewhere in the runbooks repo or in backend/frontend/aim-node code that would break. Pre-PR grep required.

10. **Deletion of pre-standard `aim-node.md` content.** §3 proposes wholesale content replacement. R2: confirm no inbound anchor links to specific section IDs in the old file exist elsewhere (e.g., in specs referencing `aim-node.md#security-model`). Pre-PR grep required.

---

## 11. Non-goals

- This chunk does not specify the actual runbook content — Gate 3 builds do that.
- This chunk does not modify Chunk 1 tooling. Any perceived Chunk 1 gap uncovered during Chunk 2 is filed as a follow-on BQ.
- This chunk does not re-open the Gate 1 frozen standard.
- This chunk does not specify CRM or Celery retrofits (Gate 1 §9 steps 6-7).
- This chunk does not specify Koskadeux-side G4 machinery; that is a separate P0 dependency BQ.

---

## 12. Review Targets

**MP R1 (primary review, read-only).** Verify:
- Classification correctness: D4 and D5 both from-scratch, not retrofit; `§K.retrofit=null` is coherent with Gate 1 §4 §K as ratified.
- Isolation enforcement adequacy: are the three R1-proposed layers (plan declaration + operational discipline + post-hoc audit) sufficient for G4 integrity, or is the R2 Koskadeux-side denied-paths wrapper a Gate-2-blocking requirement?
- G4 attempt lifecycle integration: §5.2 matches Gate 1 §7 G4 step 2 protocol (request_nonce, manifest poll, registry read).
- Dual-scenario-set model for D5: is §5.4 coherent? Does it conflict with any Chunk 1 harness invariant?
- Sequencing: D4 before D5 for the stated reasons; split PR rationale stands.
- Verification contract: 16 ACs enumerated in §8 cover the Gate 1 §9 step-4 and step-5 acceptance criteria.
- Open questions (§10): which are R2-blocking, which can be closed in R1 by Vulcan, and which defer to R3+.

**AG cross-vote (after MP R1+ passes).** Consumer-first framing. Does the contract actually produce runbooks readable by stateless agents (Gate 1 §3 consumer model)? Are the self-assertion and G4 hidden eval-set models going to produce runbook content that is agent-consumable in both cases? Is the G4 protocol as specified on the Vulcan side executable (i.e., can a reasonable Vulcan session actually follow the §5.2 attempt-open sequence without ambiguity)?

---

## Appendix A: Mapping Chunk 2 deliverables to Gate 1 §9 order

| Gate 1 §9 Deliverable | Chunk 2 Section | Repo Artifact |
|---|---|---|
| D4 Infisical reference runbook | §4 | `infisical.md` (new) |
| D5 AIM Node G4 falsifiability runbook | §5 | `aim-node.md` (content replaced) |

## Appendix B: Dependencies on Gate 1 spec sections

| Chunk 2 Section | Gate 1 Spec Dependency |
|---|---|
| §4 D4 classification | Gate 1 §4 §K.retrofit (null case), §9 step 4 |
| §4.3 D4 coverage | Gate 1 §4 §B (Capability Matrix required-form) |
| §4.4 D4 §I set | Gate 1 §4 §I (scenario rules, weighting, adjudication), §7 G3 (≥ 10 scenarios) |
| §4.5 D4 Gate 3 AC | Gate 1 §7 G3 (Infisical AC) |
| §5 D5 classification | Gate 1 §9 step 5 (G4 falsifiability), §7 G4 |
| §5.2 D5 attempt lifecycle | Gate 1 §7 G4 step 2 (request_nonce + manifest poll + registry read) |
| §5.3 D5 isolation | Gate 1 §7 G4 step 3 ("only the frozen standard as input") |
| §5.4 D5 dual scenario sets | Gate 1 §7 G4 step 4 (hidden eval set authoring) + §4 §I (runbook §I set) |
| §5.5 D5 Gate 3 AC | Gate 1 §7 G4 step 7 (pass criteria) |
| §5.6 D5 role separation | Gate 1 §7 G4 step 6 (review role split) |
| §6.3 Koskadeux dependency | Gate 1 §7 G4 step 2 (Koskadeux issuance), step 9 (state machine) |

## Appendix C: Dependencies on Chunk 1 spec sections

| Chunk 2 Section | Chunk 1 Spec Dependency |
|---|---|
| §3 repo layout | Chunk 1 §3 (post-Gate-2 Chunk 1 layout as baseline) |
| §4.5 / §5.5 lint ACs | Chunk 1 §4 (runbook-lint CLI + checks 1-20) |
| §4.5 / §5.5 harness ACs | Chunk 1 §6 (harness runner + scorer) |
| §5.4 `--answer-key` override | Chunk 1 §6.2 (answer-key format) + §6.3 (MP dispatch) |
| §7 preflight | Chunk 1 §5 (template validator) |

