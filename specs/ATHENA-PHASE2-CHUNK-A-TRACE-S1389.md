# ATHENA-PHASE2-CHUNK-A-TRACE-S1389

Status: IN PROGRESS  
Owner: Athena  
Session: S1389  
Branch: 'docs/athena-phase2-chunk-a-s1389'  
Base: 'origin/main' at '4d0934b4b810ef5d09742bc3a82b95042c5495ef'  
Signed Phase 1 decision: '792442c3-da41-4b64-ba8f-b0551fba14ff'

## 1. Purpose

This is the Phase 2 Chunk A containment and truth-preservation record. The
frozen manifest contains six sources:

1. 'session-open-protocol.md' merges into
   'runbooks/session-operations.md'.
2. 'session-close-protocol.md' merges into
   'runbooks/session-operations.md'.
3. 'session-registry-recovery.md' rewrites as
   'runbooks/session-registry-recovery.md'.
4. 'peer-instance-discipline.md' rewrites as
   'runbooks/peer-instance-discipline.md'.
5. 'work-checkout.md' merges into peer discipline, with landed-proof material
   routed to 'runbooks/branch-landed-verification.md'.
6. 'vulcan-configuration.md' merges into peer discipline and the boot companion
   set.

This first promotion commit drafts only the destination for items 1 and 2. It
does not retire, move, or modify any source.

## 2. Binding controls

- The signed M3/M4 disposition authorizes post-containment retirement, not
  immediate removal.
- Every non-blank source line must be accounted for, including historical lines.
- A drop is allowed only when enumerated and justified.
- Conflicts are preserved and flagged.
- Claims are checked against readable ground truth or marked unverified.
- The destination remains DRAFT and outside generated catalog surfaces until
  containment, strict lint, clean references, and non-author review are recorded.
- Athena must not call 'kd_session_close' while the identity defect remains live.

## 3. Ground-truth delta ledger

| Claim in source | Read-only finding on 2026-07-29 | Treatment in draft |
|---|---|---|
| Trusted peer roster is only Vulcan and Mars. | 'config:instance-registry' v2 lists Vulcan, Mars, and Athena active. | Roster-driven language replaces the superseded two-peer claim. |
| Every identity surface accepts Athena. | Open and explicit shell identity work; peer messaging returns HTTP 422 with 'instance must be one of: mars, vulcan'. | Capability is PARTIAL; exact defect appears in §§A, D, F, and I. |
| Every registered instance can close independently. | Athena close/handoff can address the wrong instance; s1374 still carries the defect. | Athena close is BROKEN and prohibited pending independent verification. |
| 'docs/instance-opening-prompt.md' exists here. | The path does not exist at the branch base. | Not promoted as an operating reference; unresolved below. |
| Boot budget is currently 64,000 JSON characters. | Supported by source; implementation not inspected under docs-only charter. | Preserved as source-supported and implementation-unverified. |
| Manual Primary/Worker close and direct lock edits remain valid fallback. | The source itself marks that block historical; current roster is instance-keyed. | Preserved as historical provenance only. |

## 4. Session-open source coverage

Source word count: 1,282. Source line count: 109. These ranges partition every
numbered line, including blanks. A mechanical range check confirmed the exact union
1–109 with no gaps or overlaps.

| Source lines | Disposition | Destination or justification |
|---:|---|---|
| 1–4 | Rewrite | Title, §A scope, and §J ownership; hard-coded peer count is superseded. |
| 5–12 | Preserve and rewrite | §C open/plan components and §E-01/E-02. |
| 13–20 | Preserve and rewrite | §E-03 carries consultation forms, one-based covers, and honest attestation. Silent coercion details remain unverified. |
| 21–32 | Preserve, rewrite, flag | §§C/H retain instance independence and reject role aliases. Two-instance wording is superseded. Scratch remains conditional because implementation was not inspected. |
| 33–41 | Preserve with scope correction | Post-§E paragraph keeps review-first and queue-priority intent; historical S612 detail is not current queue truth. |
| 42–48 | Route | §§F/G plus 'session-registry-recovery.md'; direct SQL is not an ordinary repair. |
| 49–51 | Preserve as invariant | §H rejects role locks and parent-session mechanics. |
| 52–69 | Historical provenance | Retired Memory #29 record stays in source pending archival and is not current procedure. |
| 70–72 | Unresolved reference | 'docs/instance-opening-prompt.md' does not exist; no replacement is invented. |
| 73–78 | Preserve and generalize | §C/§E describe briefing and health without asserting old thresholds. |
| 79–90 | Historical provenance | Five S612 BQ names remain acknowledged but not a current priority list. |
| 91–99 | Preserve with label | §B and post-§E note retain budget, trimming, telemetry, and lean-handoff claims as implementation-unverified. |
| 100–105 | Rewrite | §C routes recovery and peer discipline; new file unifies open/close. |
| 106–109 | Preserve and correct | §J retains lifecycle ownership; live config owns reviewer roster. |

## 5. Session-close source coverage

Source word count: 1,416. Source line count: 158. These ranges partition every
numbered line, including blanks. A mechanical range check confirmed the exact union
1–158 with no gaps or overlaps.

| Source lines | Disposition | Destination or justification |
|---:|---|---|
| 1–7 | Rewrite and flag | §§A/C/H preserve instance-keyed independence. Equal authority applies to Vulcan/Mars, not scoped Athena. |
| 8–18 | Preserve with exception | §E-04 keeps authorization, repo/handoff readiness, and instance verification. §E-05 records Athena hold. |
| 19–21 | Route | Live Council roster remains owned by 'infra:council-comms'. |
| 22–30 | Historical provenance | Historical marker/purpose remain in source pending archival. |
| 31–38 | Preserve and rewrite | §E-04 keeps close authority and no close merely because one work unit finished; old thresholds are not asserted. |
| 39–59 | Historical provenance | Primary/Worker and host-routing detail stay in source; §H makes restoration BREAKING. |
| 60–76 | Rewrite with conflict flag | §E-04 keeps repo accounting, handoff, close, audit intent, and verification. Atomic rollback is not claimed because later lines describe partial completion. |
| 77–85 | Historical provenance | Role-conditional close is retired. |
| 86–93 | Preserve safety rule | §§E/G prohibit blind retry. Old manual-close directions are not generalized. |
| 94–102 | Historical provenance | Nine-clear recurrence and direct lock-patch schema remain historical. |
| 103–110 | Enumerated drop from current procedure | Manual close fallback is unsafe for current model and not promoted; source remains preserved. |
| 111–118 | Rewrite | §E-04 requires verified instance-scoped close status. |
| 119–129 | Preserve semantically | §E-04 handoff sourcing retains priorities, blockers, refs, health, and directives without retired roles. |
| 130–142 | Historical provenance | Worker audit and worker-dead incident stay in historical source. |
| 143–148 | Preserve stop condition | §§F/G retain no_active_session_for_id, partial-state diagnosis, and no blind retry. |
| 149–153 | Rewrite | §C routes recovery and peer discipline and unifies open/close. |
| 154–158 | Preserve and correct | §J retains lifecycle ownership; current promotion review follows charter and live config. |

## 6. Coverage-accounting verification state

The range tables are exhaustive by construction:

- open: 1–4, 5–12, 13–20, 21–32, 33–41, 42–48, 49–51, 52–69,
  70–72, 73–78, 79–90, 91–99, 100–105, 106–109;
- close: 1–7, 8–18, 19–21, 22–30, 31–38, 39–59, 60–76, 77–85,
  86–93, 94–102, 103–110, 111–118, 119–129, 130–142, 143–148,
  149–153, 154–158.

No line is authorized for deletion by this table. Historical and enumerated-drop
material remains in the source or future recoverable archive, not deleted from
Git history.

This is machine-verified coverage accounting, not final destination-content
containment. At exact commit ae7195407a2c79a6a1bf834f397ac256d27eaaee,
the source blobs were independently re-read: session-open-protocol.md blob
a8c7441c03db0025e54d5c99cf77aac861a7752b has 109 lines, 82 non-blank lines,
and 1,282 words; session-close-protocol.md blob
82e0e4268caf21e8812b56058cf98245069f28a9 has 158 lines, 124 non-blank lines,
and 1,416 words. Those measurements match §§4-5. Final retirement still requires
a machine comparison proving every non-blank source line is present in a
surviving destination or listed as a permitted historical/archive disposition.

## 7. Reference scan state

The promotion-gate scan was rerun at
'32afa122cd951c757e9f95767729244ae424293c' after refreshing origin/main to
'4d0934b4b810ef5d09742bc3a82b95042c5495ef'. The branch was three commits ahead
and zero behind. Excluding archive and specs, ten current Markdown files contain
session-open, session-close, registry-recovery, or peer-discipline references:

| Classification | Current files | Promotion effect |
|---|---|---|
| Sources intentionally retained | 'session-open-protocol.md', 'session-close-protocol.md' | Resolve today; cannot retire until containment and all consumers move. |
| Future Chunk A authorities, root sources plus DRAFT destinations | 'session-registry-recovery.md', 'peer-instance-discipline.md', 'runbooks/session-registry-recovery.md', 'runbooks/peer-instance-discipline.md' | Both referenced 'runbooks/' paths now exist as content-preserving DRAFT copies. Neither appears in CATALOG.json. ACTIVE remains blocked. |
| Current operational consumers of old paths | 'gateway-transport.md', 'runbook-first-gates.md', 'max-reporting.md', 'ai-market-backend.md', 'operator-telegram-notifications.md' | Resolve to retained root sources today; classify and rewrite with the relevant authority promotion rather than breaking them early. |
| Draft destination | 'runbooks/session-operations.md' | Its source citations resolve; its two future 'runbooks/' forward paths do not. |

The exact lifecycle repair reference is
'build:bq-agent-identity-n-peer-roster-s1374'. Its Gate 3 state was independently
read as 'REPAIR_BUILD_TIMED_OUT_WIP_PRESERVED': MP task '336bd316' timed out
after 1,800 seconds with no builder commit, and the preserved WIP is not a Gate 3
candidate or authorized for review, merge, activation, or deployment. The draft
now uses that exact entity key instead of the ambiguous label 's1374'.

Pinned resolver calls for session-registry-recovery, peer-instance-discipline,
and session-operations all failed closed before resolution because inherited
agent-dispatch §X.2 drift makes CATALOG.json and TOPIC-ROUTER.md invalid at this
SHA. Catalog files remain untouched. T-2026-000476 is also still NEW, so the
normal strict-lint wrapper has not supplied a valid promotion verdict.

The scan is complete and every current hit is classified. The two missing
'runbooks/' paths are resolved as DRAFT documents, but the promotion gate is
still closed. M3/M4 retirement remains blocked; historical audit/spec
provenance must not be rewritten as if the old paths never existed.

## 8. Remaining Chunk A gates

- [x] Record destination word-count delta: reviewed head 32afa122 was 3,287 words (+21.83%); the current gate-preparation draft is 3,322 words against 2,698 source words (+23.13%).
- [x] Execute all 21 strict lint checks directly: 0 FAIL, 0 WARN, 0 INFO. The CLI wrapper separately returned 'Parser must be a string or character stream, not NoneType'; no tooling file was changed.
- [x] Mechanical exact-range check passed for 1–109 and 1–158.
- [x] Materialize 'runbooks/session-registry-recovery.md' as a DRAFT
  content-preserving copy; ACTIVE promotion remains pending.
- [x] Materialize 'runbooks/peer-instance-discipline.md' as a DRAFT
  content-preserving copy; M5/M6 containment and ACTIVE promotion remain pending.
- [x] Run full reference scan and classify every active hit at 32afa122; §7 records the unresolved promotion paths and inherited catalog-validator failure.
- [x] Resolve the filesystem paths 'runbooks/session-registry-recovery.md' and
  'runbooks/peer-instance-discipline.md'. T-2026-000476, M5/M6 containment,
  catalog validation, and the DRAFT-to-ACTIVE switch remain separate gates.
- [ ] Regenerate catalog surfaces with existing tooling only.
- [x] Complete Chunk A review at 32afa122: CC task 40075d11 APPROVE, GLM task b31c4448 APPROVE_WITH_NITS, no mandates; Mars recorded event 53dac93e. Exact-promotion-SHA review remains a separate ACTIVE gate.
- [ ] Retire sources only after every prerequisite above is complete.


## 9. Chunk A review fold

The exact review target was 72d119fb88b9de5f4c0e9e16f23f8ec49c8630c3.
CC task 83cafa22 returned APPROVED_WITH_MANDATES; GLM task 897cfe23 returned
APPROVE with no findings. This fold addresses CC's four minor findings and major
mandate without changing generated catalog files.

| Review item | Disposition in this fold |
|---|---|
| Minor: the §B close row labels the whole feature BROKEN when the deployed defect is Athena-specific. | Split the matrix into Vulcan/Mars PARTIAL and Athena BROKEN rows. No Athena close path is opened. |
| Minor: forward references may dangle until the other Chunk A runbooks are promoted. | Added an explicit §C forward-reference warning and retained the full reference scan as an ACTIVE gate. |
| Minor: reviewed §K said PASS although the wrapper crashed. | Already corrected at ae719540: §K now says FAIL and §K.1 points to T-2026-000476; direct checks remain diagnostic only. |
| Minor: range tables were internally exhaustive but the review diff did not re-collate sources. | Renamed §6 as coverage accounting, recorded exact source blob/line/nonblank/word measurements, and explicitly kept final content containment pending before retirement. |
| Major M1: prove populated authority/supersedes metadata on DRAFT cannot become canonical prematurely. | Discharged by specs/ATHENA-DRAFT-CATALOG-ISOLATION-PROOF-S1389.md at evidence commit ae719540. The proof cites generator, validator, and resolver behavior plus an in-memory/committed-catalog probe. |

The fold was reviewed at exact head
'32afa122cd951c757e9f95767729244ae424293c'. CC task '40075d11' returned
APPROVE with no mandates. GLM task 'b31c4448', dispatched by Mars at S1394,
returned APPROVE_WITH_NITS with no mandates and independently reproduced the
committed-catalog isolation check at that head; event '53dac93e' records it on
the s1229 entity. The two nits are carried without reopening Chunk A: this
trace's destination word count is corrected above, and the isolation probe must
be rerun and recorded at the actual promotion SHA.

## 10. S1389 continuation: forward-path resolution

At base '2c64af5d66ef2a4c6b9ea1b39404232852ab5db2', the branch and
Living State both recorded two dangling future paths. This continuation
materializes them without claiming promotion:

- 'runbooks/session-registry-recovery.md' preserves the root document body and
  adds only catalog-shaped DRAFT metadata plus an explicit non-authority notice.
- 'runbooks/peer-instance-discipline.md' preserves the root document body and
  adds only catalog-shaped DRAFT metadata plus an explicit notice that M5/M6
  containment is not yet claimed.
- The root sources remain present and unchanged.
- 'CATALOG.json', 'TOPIC-ROUTER.md', and the generated README inventory remain
  untouched.

Mechanical multiset verification found zero missing non-blank source lines:
364 source lines for session-registry-recovery and 265 for peer-instance
discipline are all present in their DRAFT destinations. 'git diff --check' is
clean.

Direct current-source strict checks leave 'runbooks/session-operations.md'
clean, but report 49 inherited conformance failures across the two newly
materialized DRAFT copies. The failures are concentrated in the source
documents' pre-current-schema §A/§C/§E/§H/§I/§J/§K forms; they are not hidden or
treated as a pass. These are DRAFT paths, not promoted authorities.

This resolves path existence for the already-reviewed session-operations draft.
It does not satisfy M5/M6 containment, strict-wrapper integrity, catalog
validation, exact-promotion-SHA isolation proof, or final non-author review.

## 11. Catalog-drift repair proposal — specification only

Commit 'f557bc67adb9cb5b0735f6dbce05eeb0070b772c' added section §X.2 to
'runbooks/agent-dispatch.md', then hand-edited 'CATALOG.json' and
'TOPIC-ROUTER.md' to register these three signatures:

- 'repository_tool_call_batch_empty'
- 'repository_tool_call_limit_exceeded'
- 'repository_tool_call_limit_violation_exhausted'

That made derived output disagree with frontmatter. The signatures are
operationally documented in §X.2, but §X.2 is not a section form that the current
generator resolves from frontmatter. Regeneration therefore removes the
hand-added signatures and exposes the drift.

The repair must make the signatures frontmatter-true. The frontmatter owner,
Vulcan, chooses one of two valid designs:

1. Teach the generator and resolver to recognize X.2-style subsections, then add
   all three signatures to agent-dispatch frontmatter with a resolvable §X.2
   section reference.
2. Relocate the three signature definitions to a section the current generator
   already resolves, then add all three frontmatter entries pointing to that
   section.

Either design must satisfy the same acceptance conditions:

- Each signature appears exactly once in agent-dispatch frontmatter.
- Each declared section resolves at the pinned commit.
- 'runbook-catalog generate' produces 'CATALOG.json', 'TOPIC-ROUTER.md', and the
  README inventory from frontmatter without a hand-edit.
- 'runbook-catalog check' reports the generated surfaces current.
- The signature meanings recorded at §X.2 are preserved; a relocation must not
  invent or broaden operational behavior.

Athena does not choose between the designs and does not edit
'runbooks/agent-dispatch.md' or any generated catalog surface.

## 12. S1398 inherited-DRAFT conformance round

The current-source strict pass initially reported exactly 49 findings across
the three DRAFT targets:

- 'runbooks/session-operations.md': 0 findings.
- 'runbooks/session-registry-recovery.md': 6 findings caused by one unquoted
  colon making the inherited §G YAML block unparsable; the scalar was changed to
  a folded form without changing its text.
- 'runbooks/peer-instance-discipline.md': 43 findings from pre-current-schema
  §A, §C, §E, §H, §I, §J, and §K forms.

The peer-discipline conversion preserves source-supported truth:

- Five newly required verification fields and fourteen failure-cause fields are
  explicitly 'Unknown' because the inherited source did not supply them.
- The four §H.5 boundary fields and the §H.6 formal adjudication procedure stay
  explicitly unknown.
- The eleven inherited scenarios keep their prompts, prescribed first actions,
  and weights; only their schema representation and IDs changed.
- The singleton lifecycle owner is Vulcan, matching existing frontmatter owner
  metadata; peer equality remains stated in the body.
- Harness status is pending rather than presented as a measured score.

All 21 strict checks then returned zero findings on all three DRAFT files.
'git diff --check' is clean. This is a local documentation conformance commit,
not ACTIVE promotion: source documents remain, generated catalog surfaces are
untouched, M5/M6 containment remains open, and no merge or build is authorized.
