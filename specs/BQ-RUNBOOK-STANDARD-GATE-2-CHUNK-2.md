# BQ-RUNBOOK-STANDARD — Gate 2 Chunk 2 (R2)

**Parent BQ:** `build:bq-runbook-standard`
**Chunk:** Gate 2 Chunk 2 — Gate 1 §9 Deliverables D4 + D5
**Chunk 1 contract:** `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md` @ commit `ea70326`
**Gate 1 frozen standard:** `specs/BQ-RUNBOOK-STANDARD.md` @ commit `365c198`
**Revision:** R3 (addresses MP R2 task `8fa9c9b0` REQUEST_CHANGES: 1H+1M+1L; R1 task `4f2740a0` addressed in R2)
**Author:** Vulcan
**Authored sessions:** R1 S489 (7c41edf), R2 S489 (b8ae9ab), R3 S489

---

## 1. Purpose

This chunk specifies how the first two first-party runbooks under the system-wide Runbook Standard are authored and verified:

- **D4 — Infisical runbook** (Gate 1 §9 step 4). The initial reference implementation. Authored by Vulcan from scratch using only the frozen standard plus Infisical system evidence. Validated by the Chunk 1 tooling and a Vulcan-authored §I scenario set.
- **D5 — AIM Node runbook** (Gate 1 §9 step 5). The G4 falsifiability test. Authored by Vulcan against the frozen standard with no access to D4 content. Evaluated against an externally-authored hidden scenario set produced under the Gate 1 §7 G4 protocol (MP + AG authoring, MP + AG reconciliation, XAI correspondence challenger, AG scoring).

Chunk 2 is a design-level Gate 2 specification. It does not contain the runbook content itself — runbook authoring is the Chunk 2 Gate 3 build. What this spec contains is the authoring contract, the isolation mechanism, the G4 integration shape on the runbook side, the verification contract Gate 3 will check, and the sequencing between D4 and D5.

Chunk 2 does NOT re-open Gate 1 of the parent BQ. The frozen standard is unchanged. Chunk 2 also does not modify Chunk 1 tooling directly; instead, R2 files two explicit prerequisite BQs (§6.3) that close intentional Chunk 1 scope boundaries necessary for this chunk to be mechanically satisfiable.

---

## 2. Scope boundary

**In scope for Gate 2 Chunk 2:**
- Authoring contract for `infisical.md` (new filename) per D4
- Authoring contract for `aim-node.md` (existing filename, content replaced) per D5
- Sequencing between D4 and D5 authoring
- Isolation mechanism for D5 with explicit forbidden-surface enumeration and fresh-session requirement
- G4 attempt lifecycle integration on the runbook-author (Vulcan) side including timeout recovery
- Verification contract that Chunk 2 Gate 3 will check per deliverable
- Pre-Gate-3 preflight (both runbooks generate cleanly via `runbook-new` before MP / G4 dispatch)
- Handling of existing pre-standard files (`infisical-secrets.md`, `aim-node.md`)
- Explicit prerequisite-BQ dependencies for Koskadeux-side G4 machinery and harness production wiring

**Out of scope for Gate 2 Chunk 2:**
- Koskadeux-side G4 machinery — spec authoring, implementation, and testing (P0 prerequisite filed as `build:bq-koskadeux-g4-protocol`, see §6.3)
- Harness production wiring (MP dispatch + external-scenario-set mode) — spec authoring and implementation (P0 prerequisite filed as `build:bq-runbook-harness-production-wiring`, see §6.3)
- XAI correspondence-check dispatch prompts (live in Koskadeux as part of `BQ-KOSKADEUX-G4-PROTOCOL` scope).
- CRM retrofit content (Gate 1 §9 step 6 — Chunk 3 or child BQ).
- Celery retrofit content (Gate 1 §9 step 7 — Chunk 4 or child BQ).
- Any change to Chunk 1 tooling design or to the Gate 1 frozen standard.
- AIM Node Phase 2 adapter types, multi-protocol support, or anything outside the AIM Node §A–§K runbook content. The runbook reflects the system AS IT IS; system changes are separate BQs.

**Deferred to Chunk 2 Gate 3 (build):**
- Actual authoring of `infisical.md` (D4 runbook content)
- Actual authoring of `aim-node.md` (D5 runbook content)
- Actual §I scenario sets per runbook (Vulcan-authored for D4; Vulcan-authored self-assertion set for D5 plus externally-authored hidden G4 set via the harness external-scenario-set mode)
- Evidence of `runbook-lint` PASS on both runbooks
- Evidence of Vulcan-authored harness score ≥ 0.80 on the D4 runbook's §I set
- Evidence of the full G4 attempt lifecycle completing with terminal status `passed` on the D5 runbook

---

## 3. Repository layout (post-Gate 3 Chunk 2)

Chunk 2 adds runbook content to an existing tooling scaffold. It does not relocate the tooling.

```
aidotmarket/runbooks/
├── README.md                             # Chunk 1 index (updated in Chunk 2 to mark Infisical + AIM Node as Adopted)
├── runbook_tools/                        # Chunk 1 + prerequisite harness wiring BQ
├── harness/                              # Chunk 1 scaffold (extended by prerequisite harness wiring BQ)
├── schemas/                              # Chunk 1 (unchanged)
├── templates/                            # Chunk 1 (unchanged)
├── tests/                                # Chunk 1 (extended by prerequisite BQs)
├── infisical.md                          # Chunk 2 D4 — NEW file, replaces infisical-secrets.md
├── aim-node.md                           # Chunk 2 D5 — CONTENT REPLACED
├── specs/
│   ├── BQ-RUNBOOK-STANDARD.md            # Gate 1 (frozen at 365c198)
│   ├── BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md  # Chunk 1 (frozen at ea70326)
│   └── BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-2.md  # THIS SPEC
└── (other pre-standard .md files at repo root)  # untouched in Chunk 2
```

**Handling of existing pre-standard files:**

- `infisical-secrets.md` (3570 bytes, authored S357, pre-standard). **Deleted** in the Chunk 2 Gate 3 B1 PR that lands `infisical.md`. Rationale: the old file predates the standard and is replaced end-to-end by the new conformant runbook. Git history preserves it. No archive copy needed because it is not a retrofit of a legacy whose structure is being preserved — it is pre-standard scrap. Pre-PR grep verification (performed in R2): zero inbound references outside this repo's own spec/test fixtures, so deletion is safe.
- `aim-node.md` (12115 bytes, pre-standard). **Content replaced wholesale** in the Chunk 2 Gate 3 B2 PR that lands the new version. The filename stays (already correct). The old content is in git history. Pre-PR grep (R2): zero `aim-node.md#<anchor>` fragment references; one plain-link reference in `aim-node-release-process.md` (line 83) that must be sanity-checked but does not depend on specific section IDs.
- All other pre-standard `.md` files at the repo root remain untouched in Chunk 2.

**README.md index update (Chunk 2):**

Gate 3 Chunk 2 updates the "Adoption status" section of `README.md` to move Infisical and AIM Node from their current statuses to `Adopted`, with the relevant metadata (linter_version, last_lint_run, last_harness_date, harness_score) per Gate 1 §6.

---

## 4. D4 — Infisical runbook authoring contract

### 4.1 Classification

- **Runbook type:** from-scratch authoring (not retrofit).
- **§K representation of "from-scratch":** `retrofit: false` (or omit the `retrofit` key; default is `false` per `schemas/section_k_conformance.schema.json`). `trace_matrix_path: null`. `word_count_delta: null`. The two nullable fields ARE null; `retrofit` is a boolean, not nullable. (R1 inverted this.)
- **Authoring agent:** Vulcan
- **Scope:** all of Infisical as deployed at `https://secrets.ai.market` per the current system state, including machine identities, environments, secret rotation, Railway integration, and SMTP configuration.

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

- **Minimum count:** ≥ 10 scenarios.
- **Type distribution** (per Chunk 1 §4.4.9 check #11): ≥ 3 `operate`, ≥ 3 `isolate`, ≥ 2 `repair`, ≥ 2 `evolve`, ≥ 1 `ambiguous`.
- **Weighting:** equal-weight default (`1/N`) unless an `### §I.1 Weight Justification` subsection explains each non-default weight per Chunk 1 check #12/#13.
- **§I↔per-file YAML mirror:** required per Chunk 1 loader. For D4 (normal harness path), the runbook author (Vulcan) creates both §I and `harness/scenarios/infisical/*.yaml` and ensures they mirror exactly.
- **Target weighted score:** ≥ 0.80 on the Chunk 1 harness after `BQ-RUNBOOK-HARNESS-PRODUCTION-WIRING` lands (the wiring unblocks actual MP dispatch for scoring).

The §I scenarios are Vulcan-authored for D4. D4 does NOT use external-scenario mode — it is the normal-path reference implementation.

### 4.5 Gate 3 verification contract for D4

Chunk 2 Gate 3 Acceptance Criteria for D4 (six ACs):

1. `runbook-lint infisical.md` exits 0. All 20 checks PASS; all 11 agent-form schemas (§A–§K) validate; `linter_version` and §J / §K metadata populated.
2. `runbook-harness --runbook infisical.md --mode conformant --session <g3-b1-session>` produces a weighted total ≥ 0.80 on the §I scenario set. (Command shape per `runbook_tools/cli.py:122` — actual CLI flags. Requires `BQ-RUNBOOK-HARNESS-PRODUCTION-WIRING` D1 landed.)
3. §I scenario count ≥ 10 with type distribution per §4.4 (covered by lint check #11 but called out separately because it is the central G3 AC per Gate 1 §7 G3).
4. MP first-pass design review on the authored runbook: verdict ∈ `{APPROVE, APPROVE_WITH_NITS}`.
5. `infisical-secrets.md` deleted in the same PR.
6. `README.md` Adoption Status table updated: Infisical row moves to `Adopted` with the run metadata per Gate 1 §6.

### 4.6 D4 out of scope

- G4 protocol does NOT apply to D4. D4 is the reference implementation on the normal path.
- XAI correspondence challenger does NOT run on D4 (no externally-authored eval set; nothing to correspondence-bias against).
- Doppler decommission itself is not in scope — the runbook describes current-state Infisical.

---

## 5. D5 — AIM Node runbook authoring contract (G4 falsifiability)

### 5.1 Classification

- **Runbook type:** from-scratch authoring (not retrofit).
- **§K representation of "from-scratch":** `retrofit: false` (or omit). `trace_matrix_path: null`. `word_count_delta: null`. Same correction as §4.1.
- **Authoring agent:** Vulcan, in G4 frozen-standard mode.
- **Scope:** AIM Node peer-to-peer data plane, provider + consumer modes, wire protocol, session lifecycle, security model, adapter contracts (Phase 1 HTTP/JSON only), and documented edge cases per the AIM Node system as it exists at `365c198` freeze.
- **G4 frozen_commit_sha:** `365c198` (from `build:bq-runbook-standard` entity, `gate1.approved_commit`).

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
4. **Timeout recovery (verbatim from Gate 1 §7 G4 step 2(c)):** if `request_nonce` is not found after 10 seconds, Vulcan treats the open as failed and re-emits the `g4-attempt-opened` event with a **fresh `request_nonce`**. Nonce reuse across retry opens is forbidden; the retry event generates a new UUID v4 and repeats step 3. Successive timeouts without manifest advance after 3 consecutive re-emits escalate to Max via Living State event `g4-attempt-open-stalled` with payload `{frozen_commit_sha, nonces_attempted: [...], total_wait_seconds}`.
5. **Vulcan reads per-attempt registry** at `state:bq-runbook-standard:g4:aim-node:365c198:{g4_attempt_id}:attempt-registry` to confirm authoritative state.
6. **Vulcan begins authoring** only after registry read confirms `status: 'active'`.

Retry cases (Case A/B/C/D per Gate 1 §7 step 8) each reopen via a new `g4-attempt-opened` event with appropriate `retry_case` and `prior_attempt_id`. Each retry gets a new `g4_attempt_id` and a new `request_nonce`; prior artifacts preserved under old namespaces.

### 5.3 Authoring isolation — forbidden D4-equivalent surfaces and fresh-session requirement

The central G4 integrity requirement for the runbook-author side (restating Gate 1 §7 G4 step 3 intent): **Vulcan MUST NOT consume any D4 Infisical runbook content as input during D5 authoring, through any surface.**

"D4 content" is defined as the text of `infisical.md` at any commit on or after Chunk 2 G3-B1 lands, or any derivative of that text (summaries, quoted excerpts, diffs, rephrasings).

**Forbidden D4-equivalent surfaces** (enumerated — any consumption is a Gate 3 AC 8 FAIL):

1. **Direct file read** — `cat infisical.md`, `view` / `read_file` on it, `grep` / `awk` / `sed` that returns matching content.
2. **Git history inspection of D4 content** — `git show <sha>:infisical.md`, `git log -p infisical.md`, `git blame infisical.md`, `git diff` touching `infisical.md` hunks.
3. **PR / code-review diff views** — GitHub PR web UI, `gh pr diff`, diff attachments, email notifications that include D4 hunks.
4. **Copied or quoted excerpts in other artifacts** — D4 text pasted into another file in this repo or any other repo, into session scratchpads, or into prompts to other agents.
5. **Agent dispatch tasks that reference, summarize, paraphrase, or include D4 content** — a task prompt to MP/AG/XAI that requests, contains, paraphrases, summarizes, or quotes D4 / Infisical-runbook content, whether or not the filename `infisical.md` is named literally. The MP audit classifier operates on the full dispatch prompt text, not just filename tokens. Broader rule: if the operative effect of the dispatch is that D4 content reaches the D5 authoring context (directly or via the agent's response flowing back to Vulcan), it is TAINTED. Redacted / incomplete / unavailable logs on this surface are also TAINTED by default (fail-safe).
6. **Living State reads of D4-derived artifacts** — entities whose body fields contain D4 text or summaries, including any post-authoring-session transcripts that quoted D4.
7. **Web fetches of D4 content** — D4 published to a URL (not expected but enumerated for completeness).

**Fresh-session requirement.** The Vulcan session that authors D5 MUST be a new `kd_session_open` (new session number) with no context carryover from the D4 authoring session. Session context is presumed to include D4 content during and shortly after D4 authoring, so a fresh session is the minimum-viable boundary. This is R2's primary tightening over R1 (MP R1 MEDIUM #2).

**R1 three-layer stack (retained, now with tightened scope):**

1. **Session-plan declaration.** The D5 authoring session declares in its `kd_session_plan` objectives that (a) it authors against G4 frozen standard `365c198` with attempt `{g4_attempt_id}`, (b) it will not consume any D4-equivalent surface per this §5.3 enumeration, and (c) it is a fresh session with no D4 authoring context.

2. **Operational discipline.** Vulcan refrains from invoking tool calls that touch any of the seven forbidden surfaces. Session plan serves as the self-commitment; discipline is measured in the session transcript.

3. **Post-hoc session-transcript audit (MP).** After D5 authoring session closes, MP is dispatched in a dedicated read-only audit task to review Vulcan's session tool-call log against the seven-surface enumeration. Audit output: a verdict `{CLEAN, TAINTED}` with per-call classification. A single TAINTED call fails the G4 attempt — Case A if the read was required to produce the runbook, Case B if incidental and the runbook can be cleanly re-authored.

**Layer 4 (future defense in depth, not required for Gate 2).** A Koskadeux-side denied-paths wrapper on Vulcan's shell/view/read tools during sessions flagged `g4_authoring_session=true` would physically block direct file reads and git-history reads of `infisical.md`. Filed as a follow-on `BQ-KOSKADEUX-G4-AUTHORING-ISOLATION` (see §10 Q3). It would NOT fully close surfaces 3-6, which are outside Koskadeux's direct enforcement surface; those remain on the post-hoc audit. Layer 4 is a hardening, not a substitute for layers 1-3.

### 5.4 D5 harness / scenario model (dual set via external-scenario mode)

Per Gate 1 §7 G4 step 4, MP and AG each independently author a ≥10-scenario evaluation set; reconciliation produces a single hidden answer-key; AG scores the runbook against that hidden set. The Chunk 1 harness treats the runbook's own §I as authoritative and enforces an §I↔per-file YAML mirror (loader.py lines ~55-95) — this is incompatible with a hidden externally-authored eval set. The systemic resolution is a Chunk 1 follow-on BQ: `build:bq-runbook-harness-production-wiring` (§6.3) adds `--external-scenario-set <path>` mode that bypasses the §I mirror and treats the external set as authoritative.

D5 has TWO scenario sets that serve distinct purposes:

| Set | Authors | Location | Harness mode | Purpose | Gate 3 AC |
|---|---|---|---|---|---|
| **Self-assertion §I set** | Vulcan | inside `aim-node.md` §I + mirrored `harness/scenarios/aim-node/*.yaml` | normal (default) | runbook template completeness + Vulcan's own claim of coverage | lint PASS + self-assertion harness ≥ 0.80 |
| **G4 hidden eval set** | MP + AG (reconciled) | Living State `state:bq-runbook-standard:g4:aim-node:365c198:{g4_attempt_id}:answer-key`, with scenario YAMLs materialized to a temp directory for harness input | external-scenario mode (`--external-scenario-set`) | externally-authored correctness check for G4 | AG-scored weighted total ≥ 0.80 |

**Hidden-set artifact shape (for `BQ-RUNBOOK-HARNESS-PRODUCTION-WIRING` D4):** MP+AG's reconciled eval set is stored in the `answer-key` Living State entity as a `scenarios` array. Each scenario object is a full `schemas/scenario.schema.json`-conformant object — including the required `runbook: aim-node.md` field (per the Chunk 1 scenario schema; not optional), plus `id`, `type`, `refs`, `scenario` prose, `expected_answers`, and `weight`. Attempt-scoped metadata (`authored_session`, `mp_session`, `ag_session`, `reconciled_at`, `frozen_commit_sha`, `g4_attempt_id`) lives OUTSIDE the `scenarios` array at the top level of the `answer-key` entity body. The AG scoring session materializes the `scenarios` array to YAML files in a temp directory (preserving the `runbook` field and all other required schema fields), invokes `runbook-harness --runbook aim-node.md --external-scenario-set <temp_dir> --mode conformant --session <g4-scoring-session>`, and captures the weighted-total result.

The §I self-assertion set does NOT need to align with the hidden G4 set — these are independent evidence streams testing different questions (self-assertion: "does Vulcan's claim of coverage hold?"; G4: "does the runbook actually serve an externally-authored set of questions?").

### 5.5 Gate 3 verification contract for D5

Chunk 2 Gate 3 Acceptance Criteria for D5 (ten ACs):

1. **Attempt opened.** `g4-attempt-opened` event logged; attempt-registry reads `status: active` before Vulcan begins authoring.
2. **Isolation invariant held.** Post-hoc MP audit of D5 authoring session returns verdict `CLEAN` against the seven forbidden D4-equivalent surfaces in §5.3. The audit includes: D5 authoring session ID, fresh-session confirmation (session number > the D4 authoring session number, no shared context carryover), per-tool-call classification, and the verdict.
3. **Runbook passes lint.** `runbook-lint aim-node.md` exits 0.
4. **Self-assertion harness ≥ 0.80.** `runbook-harness --runbook aim-node.md --mode conformant --session <self-assert-session>` weighted total ≥ 0.80 on the §I self-assertion set. (Requires `BQ-RUNBOOK-HARNESS-PRODUCTION-WIRING` D1 landed.)
5. **G4 hidden eval-set authored + reconciled + logged.** MP and AG each authored a ≥ 10-scenario draft independently (separate sessions, no shared access). **Reconciled answer-key `scenarios` array MUST remain ≥ 10 scenarios** — deduplication during reconciliation cannot collapse the set below this floor. If MP+AG reconciliation would produce < 10 scenarios (e.g., because most draft scenarios overlapped), the reconciliation session MUST commission additional scenarios (jointly authored in the reconciliation session) to restore the ≥ 10 floor. Reconciliation transcript logged at `…:reconciliation-transcript` (create-only, `expected_version=0`). Final reconciled answer-key logged at `…:answer-key` (create-only) with top-level fields `{authored_session, mp_session, ag_session, reconciled_at, frozen_commit_sha, g4_attempt_id, scenarios: [<full schemas/scenario.schema.json-conformant objects, each including runbook: aim-node.md>]}`. Reconciled set must also satisfy the full §I type distribution (≥ 3 operate, ≥ 3 isolate, ≥ 2 repair, ≥ 2 evolve, ≥ 1 ambiguous) and weight-sum (= 1.0 ± 0.001) constraints per `schemas/scenario.schema.json`.
6. **XAI correspondence verdict.** XAI dispatched with the `(answer-key, aim-node.md)` pair; verdict ∈ `{CLEAN, MINOR_OVERLAP}` (not `SUSPECT_OVERFITTING`). Verdict logged at `…:xai-correspondence-verdict`.
7. **MP first-pass design review.** Verdict ∈ `{APPROVE, APPROVE_WITH_NITS}`. Runs in a session separate from MP's G4 eval-set-authoring session (reviewer-independence constraint per Gate 1 §7 G4 step 6).
8. **AG harness score ≥ 0.80.** AG runs the external-mode harness (`BQ-RUNBOOK-HARNESS-PRODUCTION-WIRING` D2-D4) against the G4 answer-key. Weighted total ≥ 0.80. Score logged at `…:harness-result`.
9. **Attempt-registry terminal status `passed`.** Koskadeux (`BQ-KOSKADEUX-G4-PROTOCOL`) patches status on harness-result write per Gate 1 §7 G4 step 9 state machine.
10. **README.md updated.** AIM Node row moves to `Adopted`.

If any of criteria 2-8 fail, the attempt fails under the relevant retry Case per Gate 1 §7 G4 step 8. Chunk 2 Gate 3 B2 does not pass until an attempt reaches terminal status `passed`.

### 5.6 D5 review-role separation

Per Gate 1 §7 G4 step 6:
- **MP authors** part of the hidden eval set (with AG) AND does the first-pass design review. These MUST be two different MP dispatch sessions with different session IDs recorded in the logged artifacts (`answer-key.mp_session` vs the design-review task session).
- **AG authors** part of the hidden eval set (with MP) AND runs the external-mode harness scorer. These MUST be two different AG dispatch sessions.
- **XAI** runs correspondence challenger only; does not score.
- **Vulcan** does not see the hidden eval set before or during authoring.

Each role's dispatch is a separate task in Koskadeux's task-id registry with session attribution recorded in the logged artifact (`mp_session`, `ag_session`, `scored_session`, etc. per Gate 1 §7 step 4).

### 5.7 D5 out of scope

- Koskadeux-side implementation of attempt issuance, entity writes, status-transition patches, and stall-escalation timers — owned by `BQ-KOSKADEUX-G4-PROTOCOL`.
- Harness production wiring and external-scenario-set mode — owned by `BQ-RUNBOOK-HARNESS-PRODUCTION-WIRING`.
- XAI prompt engineering for correspondence-bias detection — owned by `BQ-KOSKADEUX-G4-PROTOCOL`.

---

## 6. Sequencing & dependencies

### 6.1 D4 before D5

D4 authoring completes (runbook lands, `runbook-lint` PASS, self-authored harness ≥ 0.80, MP design review APPROVE) BEFORE any D5 `g4-attempt-opened` event is emitted.

Rationale:
- D4 proves the standard + Chunk 1 tooling work end-to-end on the normal path before the G4 falsifiability test. If D4 cannot be authored cleanly, the standard has a non-falsifiability defect that must be resolved before the G4 test runs.
- D5's "no D4 read" constraint is easier to enforce once D4 is frozen at a known commit SHA than when it is an in-flight draft.
- Gate 1 §9 lists D4 before D5.
- Fresh-session requirement in §5.3 is only meaningful after D4 authoring is complete and contextually closed.

### 6.2 Two sub-builds within Chunk 2 Gate 3

- **Chunk 2 Gate 3 Build 1 (G3-B1):** D4 Infisical. Lands `infisical.md`, deletes `infisical-secrets.md`, updates README index, lint PASS, harness ≥ 0.80, MP design-review APPROVE. Single PR.
- **Chunk 2 Gate 3 Build 2 (G3-B2):** D5 AIM Node. Full G4 attempt. Lands replacement `aim-node.md` content in a PR; the G4 attempt lifecycle (eval-set authoring, scoring, attempt status transitions) is out-of-repo (Living State) and sequences around the PR.

The split is maintained because the G4 attempt lifecycle is stateful across multiple dispatches over hours-to-days and does not fit a single PR commit; and because D4 authoring review cycle and D5 G4 review cycle have different agent participation and verdict shapes.

### 6.3 Prerequisite dependencies (P0)

Chunk 2 Gate 3 cannot complete without the following two prerequisite BQs landed at Gate 3 APPROVED:

1. **`build:bq-koskadeux-g4-protocol`** (P0, filed S489). Implements Gate 1 §7 G4 attempt issuance, per-attempt registry + per-frozen-commit manifest writes with optimistic locking, attempt-registry state machine transitions, stall detection + 72h escalation, correspondence + multi-predicate adjudication event emitters. Blocks Chunk 2 G3-B2 (D5). Does not block G3-B1.

2. **`build:bq-runbook-harness-production-wiring`** (P0, filed S489). Closes the intentional Chunk 1 scaffold-only scope boundary: (D1) wires `council_request_fn` to real Koskadeux MP dispatch so the harness can actually score, and (D2-D4) adds `--external-scenario-set` mode for G4 hidden-eval-set runs. Blocks BOTH G3-B1 (D1 required for D4 scoring) and G3-B2 (D2-D4 required for D5 external-mode scoring).

**Dependency graph:**

```
bq-runbook-harness-production-wiring (P0, new)
    └─ D1 wire MP dispatch ────────┐
    └─ D2-D4 external-mode ────┐    │
                                │    ▼
                                │   G3-B1 (D4 Infisical)
                                │    ▲
                                │    │ before
                                ▼    │
                                G3-B2 (D5 AIM Node)
                                ▲
                                │
bq-koskadeux-g4-protocol (P0, new) ─┘
```

### 6.4 Standing of R1 residuals

R1 proposed deferring the Koskadeux-side G4 machinery filing as an open question. R2 closes that question by filing the BQ and naming its Living State key here. R1's "option B" for the harness incompatibility (reuse runbook §I for hidden set) is rejected — it breaks Gate 1 §7 G4 step 4's reviewer-independence constraint by forcing Vulcan to author scenario prompts that MP+AG would then "independently" populate. The external-scenario-mode BQ is the correct systemic fix.

---

## 7. Pre-Gate-3 preflight (Chunk 2 Gate 3 pre-dispatch check)

Chunk 2 Gate 2 (this spec) does NOT author the runbooks. Gate 2 AC is MP APPROVE + AG cross-vote APPROVE on this spec document.

**Preflight** is a Gate 3 pre-dispatch check (not a Gate 2 AC). Before Chunk 2 G3-B1 or G3-B2 is dispatched, Vulcan runs:

- `runbook-new infisical` (system-name argument per `runbook_tools/cli.py:98`; NOT a filename) in a clean working directory to confirm the template scaffold lands with only `WARN`-level placeholders. Purpose: confirm Chunk 1 template validator shape covers D4 before the build dispatches.
- `runbook-new aim-node --dry-run` in the repo root. Dry-run emits the scaffold to stdout without writing (since `aim-node.md` already exists and `runbook-new` refuses to overwrite). Purpose: confirm Chunk 1 template validator shape covers D5 before the build dispatches.

If either preflight uncovers a Chunk 1 template gap (a section where the placeholder shape does not match the Gate 1 form grammar), a defect is filed as a follow-on BQ against Chunk 1 rather than fixed in Chunk 2. This protects the Chunk 1 freeze.

---

## 8. Test suite — Gate 3 acceptance criteria summary

Consolidation of §4.5 (6 ACs) + §5.5 (10 ACs) = **16 ACs total**.

| # | AC | Deliverable | Source of truth |
|---|---|---|---|
| 1 | `runbook-lint infisical.md` exits 0 (all 20 checks PASS; 11 forms validate) | D4 | CI workflow + local invocation |
| 2 | `runbook-harness --runbook infisical.md --mode conformant` weighted total ≥ 0.80 | D4 | Chunk 1 harness (wired via `bq-runbook-harness-production-wiring` D1) |
| 3 | §I count ≥ 10 with type distribution per §4.4 | D4 | runbook-lint check #11 |
| 4 | MP design review APPROVE / APPROVE_WITH_NITS | D4 | MP dispatch task |
| 5 | `infisical-secrets.md` deleted in same PR | D4 | git diff |
| 6 | README Adoption table updated | D4 | git diff |
| 7 | `g4-attempt-opened` event logged; registry reads `status: active` | D5 | Living State event ledger + attempt-registry |
| 8 | Post-hoc MP audit verdict `CLEAN` against seven forbidden D4 surfaces | D5 | MP audit dispatch task |
| 9 | `runbook-lint aim-node.md` exits 0 | D5 | CI workflow + local invocation |
| 10 | Self-assertion harness ≥ 0.80 on §I (normal mode) | D5 | Chunk 1 harness (wired) |
| 11 | G4 hidden eval-set authored (MP + AG indep) + reconciled + logged | D5 | MP + AG dispatches; Living State artifacts |
| 12 | XAI correspondence verdict ∈ {CLEAN, MINOR_OVERLAP} | D5 | XAI dispatch task |
| 13 | MP first-pass design review APPROVE / APPROVE_WITH_NITS (separate session from eval-authoring) | D5 | MP dispatch task |
| 14 | AG external-mode harness score ≥ 0.80 against G4 answer-key | D5 | AG dispatch task (external-mode harness run) |
| 15 | Attempt-registry terminal status `passed` | D5 | Living State attempt-registry read |
| 16 | README Adoption table updated | D5 | git diff |

---

## 9. Gate boundaries (Gate 2 vs Gate 3 for this chunk)

**Gate 2 (this spec) delivers design:**
- Authoring contract for D4 (from-scratch, Vulcan-authored ≥ 10 §I scenarios, `§K.retrofit=false`)
- Authoring contract for D5 (G4 frozen-standard, Vulcan-authored runbook + MP+AG-authored hidden eval set in external-mode)
- Isolation mechanism for D5: seven-surface forbidden-content enumeration + fresh-session requirement + three-layer enforcement stack (session-plan declaration + operational discipline + post-hoc MP audit) + layer-4 defense-in-depth flagged as follow-on
- G4 attempt lifecycle integration on the Vulcan side (event + manifest poll + timeout recovery + registry read)
- Verification contract enumerating 16 Gate 3 ACs
- Sequencing: D4 before D5; two sub-builds (G3-B1, G3-B2); parent BQ stays in gate3_in_progress through both
- Pre-Gate-3 preflight with correct CLI syntax (`runbook-new <system-name>` + `--dry-run`)
- Explicit prerequisite-BQ filings: `bq-koskadeux-g4-protocol` (P0) and `bq-runbook-harness-production-wiring` (P0)

**Gate 3 (build, post-approval, post-prerequisite-completion) delivers:**
- G3-B1: `infisical.md` authored, `infisical-secrets.md` deleted, README updated, all 6 D4 ACs met. Blocks on `bq-runbook-harness-production-wiring` D1 (wired MP dispatch).
- G3-B2: `aim-node.md` authored under G4 attempt, all 10 D5 ACs met, attempt status `passed`. Blocks on both prerequisite BQs reaching Gate 3 APPROVED.

**Gate 4 (production verification, post-build):**
- First post-adoption lint-cycle on both runbooks comes back clean in nightly CI.
- First scheduled staleness detection for the Infisical runbook emits the correct `first_staleness_detected_at` row (seeded by altering a §J field). Evidence: commit diff.
- A third-party system change (e.g., a new machine identity added) is correctly identified as a §H change class by a runbook re-review agent using only the runbook's §H decision tree. Evidence: dispatch transcript.

---

## 10. Open questions for reviewers (R2 status)

R1 open questions triaged per MP R1 R2-ask summary, then updated based on R2 work:

1. **Infisical filename rename** (`infisical-secrets.md` → `infisical.md`). **CLOSED R2.** Adopted: new filename is `infisical.md` per Gate 1 §6 short-name convention. Pre-PR grep (R2) shows zero inbound references outside this repo's specs/tests, so deletion + rename is safe. Reversible if R3 AG cross-vote prefers retention.
2. **`BQ-KOSKADEUX-G4-PROTOCOL` filing status.** **CLOSED R2.** Filed as `build:bq-koskadeux-g4-protocol` v1 (S489) per §6.3. P0, Gate 0. Spec-authoring yet to start.
3. **Isolation layer 4 — Koskadeux denied-paths wrapper.** **CLOSED R2 (as NOT Gate-2 blocking).** §5.3's three-layer stack is tightened (seven forbidden surfaces + fresh-session + MP audit against them) — that is the Gate-2-required isolation discipline. Layer 4 filed as follow-on `BQ-KOSKADEUX-G4-AUTHORING-ISOLATION` (to file before G3-B2 authoring, not before Gate 2 APPROVE).
4. **Harness `--answer-key` / external-scenario override for D5 G4 run.** **CLOSED R2.** Resolved by `build:bq-runbook-harness-production-wiring` §6.3. The external-mode CLI flag is part of that BQ's D2 deliverable.
5. **Atomic vs split PR for Chunk 2 G3.** **CLOSED R2 as split.** G3-B1 then G3-B2 per §6.2; rationale holds unchanged from R1.
6. **Preflight as Gate 2 AC vs Gate 3 pre-dispatch check.** **CLOSED R2 as Gate 3 pre-dispatch check.** Gate 2 is spec design; preflight is build-readiness. §7 re-written with correct CLI syntax.
7. **§I self-assertion vs hidden-set overlap for D5.** **CLOSED R2.** Fully resolved by the external-scenario-mode design in §5.4 + the `bq-runbook-harness-production-wiring` BQ. Self-assertion runs normal mode (§I authoritative, mirror-checked); G4 runs external mode (hidden set authoritative, §I bypassed). Sets are independent evidence streams.
8. **Retry case reopening authority (Case A — spec revision).** **R3-deferrable.** For Case A, Gate 1 reopens and a new `frozen_commit_sha` is pinned on re-approval. Max authorizes the Gate 1 reopen; Koskadeux issues the new `g4_attempt_id` under the new SHA per Gate 1 §7 G4 step 8 Case A. No further Chunk 2 design required.
9. **Deletion of `infisical-secrets.md` — inbound references.** **CLOSED R2.** Pre-PR grep (R2): zero hits outside this repo's own specs/tests/fixtures. Safe to delete. Converted to explicit pre-PR checklist item for G3-B1: re-run grep immediately before the G3-B1 PR lands to confirm still-zero hits.
10. **Deletion of pre-standard `aim-node.md` content — inbound references.** **CLOSED R2.** Pre-PR grep (R2): zero `aim-node.md#<anchor>` fragment references; one plain-link reference in `aim-node-release-process.md` that does not depend on section IDs. Converted to pre-PR checklist item for G3-B2.

**R2-authored open questions — all CLOSED in R3 per MP R2 answers:**

R2-1. **CLOSED R3.** External-scenario-set artifact shape is sufficient without extending `schemas/scenario.schema.json`. Hidden-set scenario objects MUST include the required `runbook: aim-node.md` field (per the Chunk 1 scenario schema) in addition to `id`, `type`, `refs`, `scenario` prose, `expected_answers`, and `weight`. Attempt-scoped metadata stays at top level of the `answer-key` entity body, outside the `scenarios` array. See §5.4.

R2-2. **CLOSED R3.** Per-tool-call audit granularity is defensible. Classifier MUST catch paraphrases, summaries, and quotes of D4 content — not just literal mentions of the filename. Redacted / incomplete / unavailable log surfaces default to TAINTED (fail-safe, not CLEAN). See §5.3 surface 5.

R2-3. **CLOSED R3.** Reconciled hidden eval-set MUST be ≥ 10 scenarios as a normative AC — not just "Gate 1 per-draft minimum confirmed." If MP+AG reconciliation would collapse below 10 via dedup, reconciliation MUST commission additional jointly-authored scenarios to restore the floor. See §5.5 AC 5.

---

## 11. Non-goals

- This chunk does not specify the actual runbook content — Gate 3 builds do that.
- This chunk does not modify Chunk 1 tooling directly; it files two prerequisite BQs that close intentional Chunk 1 scope boundaries.
- This chunk does not re-open the Gate 1 frozen standard.
- This chunk does not specify CRM or Celery retrofits (Gate 1 §9 steps 6-7).
- This chunk does not specify Koskadeux-side G4 machinery internals; `bq-koskadeux-g4-protocol` owns that.

---

## 12. Review Targets

**MP R3 (primary review, read-only).** Verify R2 findings closed:

- R2 HIGH #1 (`bq-runbook-harness-production-wiring` D1 dispatch contract mismatch): Living State entity `build:bq-runbook-harness-production-wiring` patched to v2 with D1 scope matching Chunk 1 §6.3 exact contract: `council_request(agent='mp', task=..., allowed_tools=['Read','Grep','Glob','LS'])` with NO `mode` parameter, 180s harness-side wall-clock timeout, prompt-based tool-restriction on Codex CLI primary path (per BQ-COUNCIL-ALLOWED-TOOLS-CODEX-CLI P2 follow-on). Verify the v2 entity body reflects the real contract.
- R2 MEDIUM #1 (reconciled hidden-set floor): §5.5 AC 5 now requires reconciled `scenarios` array ≥ 10 as a normative AC; reconciliation MUST commission additional jointly-authored scenarios if dedup collapses below the floor. Verify.
- R2 LOW #1 (Appendix D diff-stat stale): Appendix D now reflects actual `+201/-152` for R1→R2 diff and adds a fresh R2→R3 diff-stat entry.

Plus R2-1 / R2-2 / R2-3 answers applied (§5.4, §5.3 surface 5, §5.5 AC 5 respectively; §10 open questions closed R3).

**R3 is expected to land at APPROVE or APPROVE_WITH_NITS.** The R3 diff is narrow and targeted; no new design is introduced.

**AG cross-vote (after MP R3 APPROVE).** Consumer-first framing. Does the contract actually produce runbooks readable by stateless agents (Gate 1 §3 consumer model)? Is the external-mode split (§5.4) coherent — do Vulcan's self-assertion §I and MP+AG's hidden set both test the agent-consumable property from complementary angles? Is the fresh-session + seven-surface-audit isolation discipline (§5.3) operationally enforceable in a reasonable Vulcan session?

**R1/R2 findings (historical reference, all closed before R3):**
- R1 HIGH #1 §K.retrofit, R1 HIGH #2 harness contract, R1 MEDIUMs #1-#4, R1 LOWs #1-#2 all closed in R2 (see Appendix D R1→R2 change log).
- R2 findings carried forward to R3 above.

---

## Appendix A: Mapping Chunk 2 deliverables to Gate 1 §9 order

| Gate 1 §9 Deliverable | Chunk 2 Section | Repo Artifact |
|---|---|---|
| D4 Infisical reference runbook | §4 | `infisical.md` (new) |
| D5 AIM Node G4 falsifiability runbook | §5 | `aim-node.md` (content replaced) |

## Appendix B: Dependencies on Gate 1 spec sections

| Chunk 2 Section | Gate 1 Spec Dependency |
|---|---|
| §4 D4 classification | Gate 1 §4 §K (retrofit boolean), §9 step 4 |
| §4.3 D4 coverage | Gate 1 §4 §B (Capability Matrix required-form) |
| §4.4 D4 §I set | Gate 1 §4 §I (scenario rules, weighting, adjudication), §7 G3 (≥ 10 scenarios) |
| §4.5 D4 Gate 3 AC | Gate 1 §7 G3 (Infisical AC) |
| §5 D5 classification | Gate 1 §9 step 5 (G4 falsifiability), §7 G4 |
| §5.2 D5 attempt lifecycle | Gate 1 §7 G4 step 2 (request_nonce + manifest poll + registry read + timeout recovery) |
| §5.3 D5 isolation | Gate 1 §7 G4 step 3 ("only the frozen standard as input") |
| §5.4 D5 dual scenario sets | Gate 1 §7 G4 step 4 (hidden eval set authoring) + §4 §I (runbook §I set) |
| §5.5 D5 Gate 3 AC | Gate 1 §7 G4 step 7 (pass criteria) |
| §5.6 D5 role separation | Gate 1 §7 G4 step 6 (review role split) |
| §6.3 prerequisite BQs | Gate 1 §7 G4 step 2 (Koskadeux issuance), step 9 (state machine); Chunk 1 §6 (harness dispatch + loader mirror) |

## Appendix C: Dependencies on Chunk 1 spec sections

| Chunk 2 Section | Chunk 1 Spec Dependency |
|---|---|
| §3 repo layout | Chunk 1 §3 (post-Gate-2 Chunk 1 layout as baseline) |
| §4.5 / §5.5 lint ACs | Chunk 1 §4 (runbook-lint CLI + checks 1-20) |
| §4.5 / §5.5 harness ACs | Chunk 1 §6 (harness runner + scorer) + `bq-runbook-harness-production-wiring` (wiring + external mode) |
| §5.4 external scenario mode | `bq-runbook-harness-production-wiring` D2-D4 |
| §7 preflight | Chunk 1 §5 (template validator) + `runbook_tools/cli.py:98` (CLI syntax) |

## Appendix D: R1 → R2 change log

MP R1 task `4f2740a0` returned REQUEST_CHANGES with 2 HIGH + 4 MEDIUM + 2 LOW findings. R2 closed all 8:

| Finding | Severity | R2 fix location |
|---|---|---|
| §K.retrofit=null schema-invalid | HIGH #1 | §4.1, §5.1: retrofit=false/omit; nullable fields are trace_matrix_path + word_count_delta |
| Harness contract incompatible with 705f8b8 | HIGH #2 | §4.5 AC 2, §5.5 AC 4+8+14: correct CLI; §6.3: filed `bq-runbook-harness-production-wiring` as P0 prerequisite |
| §5.2 timeout recovery omitted | MEDIUM #1 | §5.2 step 4: verbatim Gate 1 text + 3-consecutive-timeout escalation |
| Isolation scope too narrow | MEDIUM #2 | §5.3: seven forbidden D4-equivalent surfaces + fresh-session requirement + AC 8 rescoped |
| Koskadeux-side prerequisite absent | MEDIUM #3 | §6.3: filed `bq-koskadeux-g4-protocol` as P0 prerequisite, key cited |
| §7 preflight commands invalid | MEDIUM #4 | §7: `runbook-new <system-name>` + `--dry-run`; no overwrite attempts |
| §8 AC count inconsistent (16 vs 17) | LOW #1 | §8: reconciled to 16 by merging §A-§K forms lint AC into AC 1 |
| Q9/Q10 narrowable with grep | LOW #2 | §3 + §10 Q9/Q10: pre-PR grep outcomes captured; converted to pre-PR checklist items for G3-B1/B2 |

R1 → R2 diff stat (corrected per MP R2 LOW #1): **+201 / -152** across §4.1, §5.1, §5.2, §5.3, §5.4, §5.5, §6.3, §6.4 (new), §7, §8, §10, Appendix D (new). Line count change: R1 = 435 lines → R2 = 484 lines (net +49 because removals include invalid preflight examples and stale R1 open-question triage text).

## Appendix E: R2 → R3 change log

MP R2 task `8fa9c9b0` returned REQUEST_CHANGES with 1 HIGH + 1 MEDIUM + 1 LOW, plus answers to R2-1 / R2-2 / R2-3. R3 closes all 3 findings + applies all 3 R2-question answers:

| Finding / ask | Severity | R3 fix location |
|---|---|---|
| `bq-runbook-harness-production-wiring` D1 dispatch contract mismatch | HIGH #1 | Living State entity v2 patch (out of spec, cited in §6.3 + §12); D1 now `council_request(agent='mp', task=..., allowed_tools=['Read','Grep','Glob','LS'])` no `mode` param, 180s harness-side timeout |
| Reconciled hidden-set floor missing | MEDIUM #1 | §5.5 AC 5: normative ≥ 10 reconciled-set floor + commissioning rule if dedup collapses below |
| Appendix D diff-stat stale | LOW #1 | Appendix D updated to `+201/-152` with accurate line-count delta |
| R2-1 external-set artifact shape | R2 question | §5.4 hidden-set shape paragraph: cites `schemas/scenario.schema.json` explicitly; requires `runbook: aim-node.md` field |
| R2-2 audit granularity surface 5 | R2 question | §5.3 surface 5: classifier catches paraphrase/summary/quote; incomplete-log TAINTED (fail-safe) |
| R2-3 reconciled-set floor | R2 question | §5.5 AC 5 (same location as MEDIUM #1) — one change closes both |

R2 → R3 diff stat: small targeted edits in §5.3, §5.4, §5.5, §10, §12, Appendix D, Appendix E (new), header revision line. No structural changes; no new sections beyond Appendix E.

