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

The initial repository scan found live references to old session paths in
'peer-instance-discipline.md', 'work-checkout.md',
'session-registry-recovery.md', 'mcp-gateway.md', 'max-reporting.md',
'runbook-first-gates.md', 'gateway-transport.md', audit records, and specs.

M3/M4 retirement is therefore blocked. Current operational references must move
or remain intentional archive citations. Audit/spec provenance must not be
rewritten as if historical paths never existed.

## 8. Remaining Chunk A gates

- [x] Record destination word-count delta: 2,698 source words to 2,802 draft words, +3.85%.
- [x] Execute all 21 strict lint checks directly: 0 FAIL, 0 WARN, 0 INFO. The CLI wrapper separately returned 'Parser must be a string or character stream, not NoneType'; no tooling file was changed.
- [x] Mechanical exact-range check passed for 1–109 and 1–158.
- [ ] Promote 'session-registry-recovery.md'.
- [ ] Promote 'peer-instance-discipline.md' and contain M5/M6.
- [ ] Run full reference scan and classify every active hit.
- [ ] Change destinations from DRAFT to ACTIVE only when boundaries are coherent.
- [ ] Regenerate catalog surfaces with existing tooling only.
- [x] Obtain initial non-author review at 72d119fb: CC approved with mandate M1 and GLM approved. The mandate fold requires CC follow-up at its exact new SHA.
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

No GLM follow-up is required because the proof documents existing catalog
selection semantics and does not change the operational procedure. CC follow-up
must review the exact fold SHA.
