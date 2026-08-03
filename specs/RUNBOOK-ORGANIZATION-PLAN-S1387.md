# RUNBOOK-ORGANIZATION-PLAN-S1387

Status: AUTHORIZED FOR IMPLEMENTATION by Max in S1413. This document, including the S1413 amendment in §12, is the Gate 1 amendment input to BQ-RUNBOOK-CATALOG-VALIDATOR-S1229 and BQ-RUNBOOK-FIRST-ENFORCEMENT-S1146; it does not open a new umbrella item. Author: Mars, S1387; implementation amendment: Mars, S1413. Original measurement base: runbooks main 3d4f018a, koskadeux-mcp main 645018f3. S1413 implementation base: runbooks main a6d7534a35d921138c139bdf69aaeddd0faec100, koskadeux-mcp main 8e2bc8b9345f06c37d769421e67a3daf1a90a2eb.

**Current-reading rule:** §12 is the only active implementation contract in
this file. §§1–11 preserve the measured problem, rejected approaches, and
historical proposal; their caller attestations, waiver flow, local gate,
runbook-commit shortcut, phased pin mechanics, and authority assumptions are
not current instructions. When §12 and earlier prose differ, follow §12 and
`specs/RUNBOOK-ALL-CORPUS-DISCOVERY-S1413.md` Revision 8.

## 1. What this is

Max asked for a deep think on organizing our runbooks so our AI instances can discover them, understand them, and update them, including the best indexing solution, delivered as an implementable plan. This document is that plan. It inherits the decisions Max has already made and does not relitigate them:

- S1330, verbatim intent: the documents are to be written to our specification and then indexed properly. No two-tier catalog. Indexed-but-not-authoritative is rejected and is not to be revived.
- S1370, verbatim: "scrap the automated exam, but we still need to fix the index." The LLM-graded conformance exam is dead. Deterministic checks stay.
- The canonical template already exists: specs/BQ-RUNBOOK-STANDARD.md, sections A through K plus ten frontmatter fields.
- The agreed sequence stands: merge the duplicate (done, landed via S1348), triage, promote, advance the pin.
- Max's acceptance test, recorded at S1330: a session can cite any surviving runbook at plan time and have it resolve, and no_entry_found attestations become rare rather than routine.

What this plan adds is the missing design layer: why discovery keeps failing even for runbooks that exist, what the index has to look like so it cannot rot again, and how updating becomes cheaper than waiving.

## 2. Ground truth, measured

Numbers at runbooks main 3d4f018a (2026-07-28):

| Fact | Value |
|---|---|
| Runbook documents at repo root | 83 (86 .md minus generated README, TOPIC-ROUTER, task_state) |
| Runbook documents in runbooks/ subdir | 15 |
| Catalog entries (ACTIVE, indexed) | 17 |
| Estate coverage by the index | roughly 17 of 98 |
| Boot kernel catalog pin | 039d3162, minted S1266, more than 32 commits behind main |
| Entries a booting session actually sees | 12 |
| Root documents declaring ACTIVE frontmatter | 3 |
| Live git worktrees on the runbooks repo | 24, many from closed sessions |
| Strict lint at last measurement (S1348) | fail=1 warn=14, and it had been silently selecting zero targets while catalog drift stood |

Two incidents from today, S1387, both fresh evidence:

1. The plan gate rejected a citation of runbooks/agent-dispatch.md section X.6. The section exists on main. It failed because the gate resolves references against the working tree of the shared checkout at /Users/max/Projects/ai-market/runbooks, and that checkout was parked on an S1382 spec branch that predates the section, while the main branch itself was held hostage by a stale worktree from S1345. The reference was true and the gate said it was false.
2. Section X.5 of the same runbook covers session-open peer-bus drain exactly. I still attested no_entry_found for that subject, honestly, because no discovery surface maps the task language "peer bus drain at session open" to that section: it is not a catalog topic, not an error signature, and X sections are invisible to the index entirely.

These are the two halves of the whole problem: resolution that depends on machine state instead of git truth, and discovery that only works if you already know the answer. The pattern repeats in the record: S1330 both instances manufactured false no_entry_found attestations the same day; S1350 measured three of four attestations false; the tripwire ledger carries roughly 57 distinct waiver subjects, several waived repeatedly for subjects that have runbooks.

## 3. Why agents fail to find runbooks

Six distinct failure modes, each needing its own fix. Fixing any one alone will not move Max's metric.

1. Coverage. 81 of 98 documents are outside the index. No index improvement helps a document the index does not know.
2. Pin rot. The boot envelope pins the catalog at a hardcoded SHA in two coupled places (tools/boot_kernel_v2.py line 21 and boot_kernel/v2/manifest). Nothing advances them, so doing nothing looks safe and the boot view silently ages.
3. Working-tree resolution. The ref resolver reads files from a shared checkout that sessions and dispatches park on arbitrary branches. Git truth and gate truth diverge.
4. Granularity. The index knows topics and error signatures declared in frontmatter, at whole-lifecycle-section granularity. Operational lessons live in heading-level sections the index cannot see.
5. The task-language gap. Agents think in task descriptions ("stale-base merge re-review", "recover an MP dispatch whose task id was never written"). The index matches exact topic keys and signature strings. Nothing translates between the two, even though we run a semantic search stack (allAI plus Qdrant) as a product capability.
6. Update friction. Landing a runbook change requires worktree mechanics, regeneration, named-ref push rules, and a bare-SHA close declaration. The waiver ledger shows 34 runbook_exit waivers. When the compliant path is fiddly, sessions waive, and the estate falls further behind reality.

## 4. Design principles

1. Files are the only source of truth. Every index, router, and embedding is generated from them and can be regenerated at any time. Hand-maintained indexes are forbidden (already the s1229 rule, kept).
2. Resolution follows git, never a working tree. A citation is true if the content exists at origin/main, full stop.
3. One authority per topic, no tiers. Every surviving document is ACTIVE and conformant, or it is in archive/. (Max's S1330 decision.)
4. Discovery must work at the point of need, in task language, without prior knowledge of the estate.
5. The freshness of every derived surface (catalog, boot pin, embeddings, router) is asserted by CI, not remembered by anyone.
6. Updating a runbook must be one tool call. If compliance costs more than a waiver, we get waivers.
7. Models stay swappable (CORE S6): embeddings are a derived discovery aid rebuilt from files, never an authority.

## 5. Target organization

**Layout.** One repo, aidotmarket/runbooks. All runbook documents live in runbooks/ (the subdir), one file per runbook, kebab-case filename equal to runbook_id. The three e2e runbooks move from root into runbooks/ (path convention violation today). specs/ holds specs, archive/ holds retired documents excluded from catalog and resolver, templates/ and runbook_tools/ as today. The repo root ends up holding only generated surfaces (CATALOG.json, TOPIC-ROUTER.md, README.md, llms.txt) and tooling. Domains stay metadata in frontmatter, not folders: folders freeze a taxonomy, metadata lets it evolve.

**Template.** BQ-RUNBOOK-STANDARD sections A through K, unchanged. Two additions to the standard, both cheap:

- Stable heading anchors. Every heading carries an explicit immutable anchor id. Content under a heading may change freely; the anchor may not disappear without a tombstone redirect. Citations become runbook_id#anchor and survive edits.
- A lessons policy for X sections. X sections (dated incident lessons) are an inbox, not a home. At each owner verification pass, X content is folded into the owning lifecycle section and the X entry is reduced to a pointer. This stops runbooks becoming append-only scrolls (runbooks/agent-dispatch.md is already 1,698 lines).

**Size bound.** Target under roughly 500 lines per runbook. Larger means the topic should split. An agent should be able to read the whole governing runbook cheaply, not archaeologically.

**Ownership and freshness.** Every runbook keeps an owner and last_verified_at (exists today). Add verified_ttl, default 45 days. Past TTL the generator marks the entry STALE and the boot standup surfaces stale runbooks exactly the way it surfaces stale BQs. Verification means the owner re-checks the procedure against ground truth and bumps the date in the same commit as any corrections.

## 6. The indexing solution

Five layers. The first two exist and are kept; the rest are the new design. Alternatives considered and rejected at the end.

**L0, the generated catalog (exists, extended).** CATALOG.json generated from frontmatter plus a heading scan, committed in the same change as the content, with CI failing on drift (runbook-catalog check, exists). Extension: the generator indexes every heading anchor, not just declared topics and signatures, so the catalog knows every citable section in the estate. Anchor uniqueness and tombstone rules enforced by lint.

**L1, git-truth resolution (small code change, high leverage).** The plan-gate and close-gate resolver stops reading the shared working tree. It resolves path and section against the fetched origin/main blob (git cat-file on origin/main after the existing best-effort fetch, falling back to last-fetched state with the existing stale_fetch warning). Section matching gains anchor matching. Effect: parked branches, stale worktrees, and half-finished checkouts can never again make a true citation false. This directly kills today's incident 1.

**L2, a boot pin that cannot rot.** Keep the constitutional shape (I6: one SHA-pinned catalog reference in the envelope) but make advancing it a machine's job. Recommended mechanism, option A: a CI job on runbooks main regenerates the pin triple (BOOT_KERNEL_V2_CATALOG_REF, manifest catalog_ref, catalog_digest_sha256, catalog_entries) and opens a small auto-commit to koskadeux-mcp through the normal review path, plus a pin-freshness assertion in koskadeux-mcp CI that fails when the pin trails runbooks main by more than N commits (N=5 suggested). Option B, cheaper but needing a Steward read: boot resolves the catalog at origin/main and records the resolved SHA in the envelope, treating I6's pin as recorded-at-boot rather than pre-registered. A records intent before boot and is the safer reading; B removes a moving part. Decision for Max, default A.

**L3, semantic discovery in task language.** Embed every catalog section (anchor-level chunks) into a dedicated Qdrant collection on our existing stack, rebuilt from files on every catalog change (derived, model-swappable, never authoritative). Two consumers:

- A runbook_search tool: natural-language query in, ranked runbook_id#anchor candidates out, for any agent at any time.
- Plan-gate assist: when a session submits a no_entry_found attestation, the gate answers with the top three semantic candidates and requires either adopting one or rejecting them with a stated reason. Attestation stops being a dead end and becomes assisted discovery. This directly kills today's incident 2, and it converts Max's metric into a self-correcting loop: every honest miss trains the gap list.

The historical waiver-subject ledger (57 subjects) becomes the free acceptance test set for this layer: the bar is that at least 80 percent of them resolve to a real section through search.

**L4, push and telemetry.** Error signatures already map to sections; extend so gateway and tool errors carrying a known signature return the runbook pointer inline in the error payload (discovery at the moment of failure, no diligence required). Log every resolved citation and every search miss. A nightly job aggregates no_entry_found subjects; any subject seen twice auto-files a runbook-gap ticket on the nearest domain owner. That makes T-2026-000328's one-time waiver audit continuous and gives us the curve on Max's metric instead of anecdotes.

**Rejected alternatives.** A hand-maintained index: already failed, that is how we got here. A wiki or external doc tool: breaks git truth, SHA pinning, and CI enforcement. Pure vector search as the index: non-deterministic, unauditable for a compliance gate, and couples authority to an embedding model against CORE S6. Folders-as-taxonomy: freezes judgement that should stay editable metadata. Two-tier catalog: rejected by Max at S1330, not revived.

## 7. The update path

**One-call commits.** A runbook_commit tool (koskadeux-mcp): takes runbook_id, anchor, patch text, and a message; applies the edit in a throwaway worktree, regenerates catalog and router, runs lint on the touched member, commits, pushes with the named-ref mechanics handled, cleans up its worktree, and returns the bare 40-char SHA in exactly the form the close gate wants. The 34 runbook_exit waivers are mostly friction; this removes the friction. Guardrails: refuses non-runbook paths, refuses lint-red results, normal review rules unchanged for anything beyond doc content.

**Worktree hygiene.** Session-created worktrees carry a TTL; a reaper surfaces and removes worktrees whose sessions have closed (24 live today, several weeks old, one of which was holding main hostage this morning). The X.4 restore-to-main discipline stays, but the design goal is that nothing load-bearing depends on it once L1 lands.

**Lessons fold.** At each TTL verification, the owner folds X-section lessons into the body per section 5. Verification, folding, and the date bump land as one commit through runbook_commit.

## 8. Migration programme

Sized honestly against the recorded precedent (S1265: one full A-through-K rewrite per MP dispatch hit the 1800s timeout with work complete; expect 4 to 8 documents per dispatch on lighter files).

**Phase 0, hygiene, days, no builder for most of it.**
- Advance the boot pin now to current main using the known catalog_pin_s1265 procedure, and land the CI pin-freshness assertion with it. Moves booting sessions from 12 to 17 entries immediately.
- Move the three e2e runbooks into runbooks/ and regenerate.
- Reap dead worktrees; record the reaper as a small recurring job.
- One MP dispatch: L1 git-truth resolution in tools/runbook_ref.py plus anchor matching. Small diff, big effect, routes through s1146 (it owns gate behavior).

**Phase 1, triage, judgement work, roughly a week of attention, no builder.** Sort the 81 unindexed documents into rewrite, merge, or archive before any rewriting is paid for. Mars and Vulcan propose per-domain kill lists; Max signs the archive list (some documents are his). Output: a frozen manifest per promotion chunk. The estate accumulated over months; a meaningful fraction is superseded notes, not runbooks, and archiving them first shrinks every later phase.

**Phase 2, promote to standard, the long pole, 10 to 20 MP dispatches plus reviews.** Chunked by domain with fixed per-chunk manifests. Every chunk brief carries the truth-preservation instruction that worked at S1265 and S1348: the controlling risk is invention, a rewrite may not assert operational detail the source does not support, unknowns stay explicitly unknown, and reviews are briefed for truth, not format. Strict lint green is the per-chunk exit. Frontmatter, anchors, and TTLs land with each chunk.

**Phase 3, discovery layer, 2 to 3 MP dispatches.** Qdrant collection and rebuild hook, runbook_search tool, plan-gate assist, inline error pointers. Ships after Phase 2 has enough of the estate promoted to be worth searching, but does not wait for all of it.

**Phase 4, update loop, 1 to 2 MP dispatches.** runbook_commit, waiver-to-ticket nightly job, TTL staleness in the boot standup, telemetry dashboard tile on ops.ai.market.

Sequencing against the rest of the queue is Max's call; nothing here preempts the P0 lane. Vulcan manages the builders through Phases 2 to 4 per Max's S1330 delegation, with MP as the mandatory builder (CORE S4).

## 9. Acceptance criteria

Max's own test leads, the rest support it:

1. no_entry_found attestations become rare rather than routine, measured weekly from L4 telemetry, target under one new subject per week by end of Phase 3.
2. Zero false attestations: no attestation for a subject an existing section covers, checked against the search layer.
3. A citation of any ACTIVE runbook section resolves at plan time regardless of local checkout state.
4. Boot pin never trails runbooks main beyond the CI threshold; catalog, router, README, and embeddings regenerate clean on every change.
5. At least 80 percent of the historical waiver-subject ledger resolves to a real section via runbook_search.
6. Strict lint green across the promoted estate; catalog covers 100 percent of ACTIVE documents; archive/ holds everything else.

## 10. Decisions needed from Max

1. Approve this as the Gate 1 amendment to BQ-RUNBOOK-CATALOG-VALIDATOR-S1229 (it formally records the S1330 supersession of the old no-backfill scope, which the entity already flags as owed a Gate 1 record).
2. Pin mechanism: option A (CI auto-advance commit, recommended) or option B (resolve-at-boot, needs a Steward read on I6).
3. Triage authority: confirm Mars and Vulcan propose, Max signs the archive list.
4. Scheduling: where Phases 1 and 2 sit relative to the current P0 lane.

## 11. Costs and risks

Builder time is the real cost: roughly 14 to 26 MP dispatches end to end, dominated by Phase 2, spread over weeks at normal cadence. Compute cost of the embedding layer is negligible at this corpus size. Main risks: invention during rewrites (mitigated by the S1265 truth-preservation brief and machine-verified content-containment where scripted merges apply); triage deleting something load-bearing (mitigated by archive/ being recoverable and excluded rather than deleted); and the standing risk of doing nothing, which the record shows compounds: false attestations in the permanent record, instruments that pass while testing nothing, and two operators repeatedly rediscovering the same lessons the estate already contains.

## 12. S1413 implementation amendment — truth before ceremony

Max authorized the recommendations from the S1413 gate/corpus audit for implementation through completion. This section resolves the decisions in §10 and supersedes any earlier requirement that a free-form plan or close attestation is, by itself, evidence of consultation or documentation quality.

### 12.1 Binding decisions

1. **Routine plan and close gates become assistive while the replacement rolls out.** They may warn, deliver context, and record telemetry, but may not block merely because an agent cannot name a runbook or because documentation impact is uncertain. Gateway/database unavailability and verified high-risk action protections remain fail closed.
2. **The gate proves delivery, not reading claims.** The server resolves one immutable `origin/main` snapshot, searches it using the task language, returns ranked section excerpts, and records which exact bytes were delivered. An agent must not be asked to guess a filename before receiving this result.
3. **Action-time protection remains blocking where harm is plausible.** Deploy, rollback, secrets, production-data mutation, migration, recovery, billing, authentication/authorization, and other explicitly configured high-risk operations require a delivered current section or an audited emergency override.
4. **Completion is behavior-impact based.** A runbook update is required only when work changes an operational contract, configuration default, deployment/recovery procedure, failure signature, ownership boundary, customer-visible behavior, or creates a durable function with no current owner. Tests-only changes, generated output, formatting, and behavior-preserving internal refactors do not require an update.
5. **Uncertainty creates one nonblocking obligation.** `required` without a landed update and `uncertain` produce or refresh one canonical obligation keyed by component plus behavior subject. Failed/retried plan submissions never create obligations. Obligation creation is transactional with the successful operation and idempotent.
6. **No author self-certification.** AI may rank, summarize, and propose documentation. Material current-state claims require `verified_against` evidence, and high-risk runbook changes require an independent truth-focused reviewer.
7. **Pin mechanism A is selected.** CI advances the coupled boot-pin triple through the normal reviewed path. A freshness check fails when the pin is more than five runbooks-main commits behind; the implementation target is exact current-main pinning.
8. **Unknown is better than invented.** The A-through-K structure remains the current standard, but unsupported operational detail must be explicitly `UNKNOWN` with an owner/evidence gap rather than filled speculatively. The automated LLM conformance exam remains retired.
9. **Executable guidance cannot outrun the deployed contract.** The gateway publishes an immutable machine-readable tool-and-Council contract for its exact deployed SHA. ACTIVE current guidance is validated against a pinned digest of that artifact; a connector cache, mutable `latest` response, shared checkout, or historical Living State prose is not contract evidence.

### 12.2 Authoritative automatic context record

The replacement planning flow is one ordinary request:

1. The first `kd_session_plan` call carries the normal ordered objectives,
   delegation strategy, work class, and other plan fields. It has no runbook
   path, section, consultation, gap, attestation, waiver, or desired impact
   field.
2. Before any plan, intent, debt, session-status, or business-authority write,
   the gateway resolves the backend-approved exact runbooks activation commit,
   validates the complete immutable corpus and runtime, and searches all
   objectives plus every relevant OPEN obligation subject against that single
   snapshot.
3. The same successful `PLAN_ACCEPTED` result contains the complete ranked
   context for every objective. It atomically binds the plan revision, exact raw
   request digest, search projection digest, catalog and inventory identities,
   delivered source/section/excerpt hashes, response bytes and digest, then
   moves the session from `PLANNING` to `OPERATIONAL`.
4. The agent reads that response before using work tools. If the delivered
   evidence changes the approach, it amends the plan before acting. An unchanged
   retry after a lost response returns byte-identical response content even
   after the session is operational; any changed semantic field is a different
   request and fails the retry binding.

The canonical request digest covers every behavior-affecting plan field: exact
ordered objective strings, instance, session, work type, amendment and plan
revision, delegation strategy, override reason, incident reference,
triviality/routine class, and any later semantic field. Search normalization has
a separate digest and cannot authorize changed raw input. The persisted delivery
record is session-, instance-, revision-, policy-, activation-, objective-, and
response-bound. It is backend/gateway-produced evidence of delivered bytes, not
an agent claim that the text was read or correct.

The complete context envelope must fit below the deployed transport's
50,000-character truncation boundary. The initial hard limit is 40,000 UTF-8
bytes and characters, including metadata, with `complete=true`, exact byte
count, and a canonical payload digest. The resolver drops lower-ranked
candidates deterministically before serialization. Multi-objective packing is
breadth-first: one fitting candidate per objective before any objective receives
a second or third. If positive candidates exist for an objective but no complete
useful envelope fits, the plan fails with the small typed
`RUNBOOK_CONTEXT_RESPONSE_TOO_LARGE` result and performs zero semantic writes.
Head/tail-truncated JSON is never accepted context. Natural runbook-authoring
tasks may also receive the pinned README authoring procedure, labeled
non-catalog context and never treated as semantic authority.

The first response prioritizes understandable quick-start, stop, and verify
guidance. Bounded excerpts are navigation, not a substitute for the procedure:
exact stable sections and full runbooks remain fetchable through immutable,
digest-bound pagination. All relevant OPEN obligations are page-addressable;
the server never silently truncates them to a fixed recent window. Fetch and
continuation retries are idempotent and bind the exact activation, source blobs,
session, objective/obligation query set, page cursor, and response digest.

The initial ranking implementation is deterministic and dependency-light: normalized token/phrase scoring over IDs, aliases, topics, error signatures, paths, and headings read from the pinned Git snapshot. All objectives are searched in one validated snapshot load. Catalog-declared `section_id` values are authoritative only when their adjacent anchors validate; other headings remain discoverable under an explicit `legacy-derived` identity until promoted. A raw anchor that is absent from catalog metadata never claims catalog identity. Semantic/vector ranking may be added as a derived reranker only after shadow evaluation; it is never the authority or a new blocking dependency.

Every child build, author, or review dispatch receives task-relevant context at
the lowest common provider boundary across public, direct, and indirect launch
paths. A caller cannot supply, suppress, or override that context. There is one
active protocol and no runtime mode selector: after activation the legacy input
fields, files, schemas, stores, database writers, and fallback branches are
physically absent.

### 12.3 Authoritative completion record

`kd_session_close` accepts the ordinary close fields only. It has no
`runbook_exit`, `runbook_impact`, decision, changed-component, evidence,
consultation, waiver, discharge, or no-change input. The backend derives this
record before close:

```yaml
session_snapshot: <backend-owned repository, provider, obligation, and activation baseline>
action_evidence:
  - intent: <backend-issued identity bound to canonical arguments and component>
    outcome: <trusted backend or provider observation>
    publication: <current session-bound remote candidate ref for repository writes>
impact_results:
  - decision: required | not_required | uncertain
    component: <canonical registry identifier>
    behavior_subject: <server-derived normalized contract subject>
    evidence_fingerprint: <stable digest of typed owning evidence>
coverage_results: [backend-verified obligation-bound coverage receipts]
```

At session open the backend captures the exact runbook activation, active
obligations, and security-relevant registry identity. It does not enumerate
every head/tag or provider in the market. Every write-capable action is
registered before execution, and first intent lazily captures the exact target
repository/provider baseline under the session actor. Repository-writing actions
receive a per-action publication binding tied to the session, intent, canonical
arguments, expected candidate ref and owning actor; PREPARE and COMMIT both
verify that a current allowed remote ref resolves to the observed result. One
earlier or unrelated push, a default branch head, an intermediate webhook SHA,
a deleted ref, local dirty state, caller-reported success, author identity, or
`git cat-file -e` existence cannot preserve or verify another action.

Non-Git mutations are backend-executed or reconciled against authoritative
database/outbox and provider audit records under session-bound actor
credentials. Agent and gateway outcomes are hints only. The static backend
registry distinguishes operating-contract changes from routine execution of an
unchanged contract. Source, schema, configuration, policy, deployment, tool,
and process changes default `required`; provider-observed queue transitions,
messages, events, reviews, session lifecycle, and business-record transactions
under unchanged code/configuration are `not_required`. Tests-only,
deterministically generated, and formatting-only repository changes are
`not_required` only when the backend proves that exact diff class. Unknown
mutations become scoped `uncertain`; a trusted collector or mechanical
integrity failure is a retryable blocker with zero close-side writes. Caller
work type, action label, outcome, or passing test/build never lowers the class.

A coverage receipt is valid only when the backend refetches remote ancestry and
diffs and verifies exact obligation, component and evidence fingerprint; base,
content C and activation M commits; changed runbook paths, IDs, section IDs and
section hashes; typed owning evidence; and an independent reviewer receipt bound
to the same digest when policy requires it. The backend signs the result with an
algorithm-fixed Ed25519 key. A later session may satisfy an older obligation
after exact M is live. Valid runbook coverage is a discharge artifact, not a
recursive behavior obligation.

The same distinction applies to catalog promotion. Syntax, placeholder removal,
`last_verified_at`, prose in `verify_against`, an `UNKNOWN` decoration, exact
blob identity, and an author-written test do not establish semantic truth. A
DRAFT's §K projection and `pin-evidence` command are preparatory bookkeeping for
a future claim-bound receipt, never local authority. Promotion is unavailable
for every risk class until a deployed verifier authenticates evidence-to-claim
bindings and an independent reviewer bound to the exact candidate digest, with
freshness and revocation checks. A receipt ID or unsigned file authored in this
repository is never a trust source.

Catalog and corpus validation reconstruct one self-consistent full-commit
snapshot: generated outputs, schemas, every operational source path and blob,
catalog-to-manifest membership, and base-to-inventory-to-search ancestry. Git
replacement objects and ambient Git/SSH/loader controls are disabled. A valid
new ACTIVE document may enter this integrity-only snapshot; the retired fixed
20-member projection and its mutable policy file are physically absent. The
backend activation service, never a repository author or gateway caller,
monotonically selects the reviewed live pin. Existing ACTIVE sources and
content changes still carry no semantic verification, authority admission, or
action authority merely because they validate. The corpus `--promotion-bar`
must stay NO-GO rather than rename empty or locally decorated evidence as
verified.

B0 remains one external deployment condition: the backend must provide the
claim-bound evidence verifier, independent-review authority, signing service,
and monotonic activation boundary bound to the exact candidate digest, using a
pinned trusted validator/schema/runtime package digest with freshness and
revocation checks. The gateway transports these results and cannot mint or
select them. Until all of B0 is deployed, promotion and all semantic or
action-authority flags remain false.

### 12.4 Obligation contract

The append-only free-text waiver pile is replaced by canonical obligations:

```yaml
obligation_id: sha256(version + component + contract_kind + normalized_subject + evidence_fingerprint)
component: <canonical component>
contract_kind: <versioned behavior or operating-contract class>
subject: <normalized behavior/documentation gap>
evidence_fingerprint: <stable typed owning-evidence identity>
status: open | satisfied | explicitly_deferred
first_seen_session: <session>
last_seen_session: <session>
occurrences: <integer>
owner: <agent or Max>
due_trigger: <condition, not invented calendar precision>
search_evidence: <catalog SHA, query, candidates>
satisfied_by: <verified runbooks commit, when complete>
```

Volatile session UUIDs and timestamps are excluded from identity. Retries update
the same record and a unique close-request occurrence prevents double counting.
Closing a session is never the mechanism that forces prose into a runbook.
Explicit deferral of a high-risk required update still needs an expiring,
one-use, exact-obligation-bound Max authorization, but the session transaction
remains recoverable and the obligation remains visible.

Close authority lives in one backend database transaction, not the local
registry, an in-memory fallback, gateway SQLite/HMAC state, a mutable upsert, or
a best-effort sequence of Living State calls. Trusted collection and mechanical
validation happen before the transaction and write nothing on outage,
unresolvable evidence, digest/policy mismatch, duplicate identity, invalid
ancestry/ref, or catalog/runtime integrity failure. Only then does `PREPARED`
atomically place the session in `CLOSING`, freeze exact evidence, and record the
immutable request digest.

`COMMIT` reacquires the session lock and revalidates only action-bound current
remote and provider truth before one transaction writes the database handoff, session state,
deduplicated obligation occurrences, outbox events, and immutable `COMMITTED`
receipt. Open `REQUIRED` or semantic `UNCERTAIN` obligations do not block this
commit. Constraints reject a reused request ID with a different digest, more
than one active close per instance/session, duplicate
`(obligation_id, close_request_id)` occurrences, mutation of a committed row,
and duplicate outbox delivery. Claims and role slots release only after commit.
Local files and registry rows are recoverable caches reconciled from backend
truth. Crash/retry at every boundary returns one receipt and one occurrence; a
failed prepare leaves the session open and obligations invisible.

Obligation identity uses versioned, delimited canonical input including the
server-derived component, contract kind, normalized subject, and evidence
fingerprint. A retry cannot increment occurrences twice. High-risk deferral is
accepted only through an expiring, exact-obligation-bound Max authorization.

Close remains nonblocking, but an obligation's due trigger is executable. Before
accepting the next behavior-changing action for the same component, the backend
requires the exact OPEN obligation to be satisfied. Read/search/test diagnostics
and runbook remediation, review, coverage, and activation actions remain
available. Urgent continuation requires a fresh one-use Max authorization bound
to both the exact obligation and the exact proposed action. This prevents
indefinite compounding without reviving close-time filler incentives.

### 12.5 Rollout order

1. **Install the backend compatibility floor:** deploy a code-only A1 release to every backend replica before adding a database rejection trigger. It normalizes the two legacy runbook event types before size, admission, ledger, and outbox handling; makes the waiver/debt/amendment compatibility writers exact no-ops or safe sibling-only updates; and prevents both new and already queued protected event text from reaching Qdrant. A1 does not rewrite historical canonical rows and does not claim protection from direct SQL.
2. **Install database and worker backstops:** only after A1 is proven on every replica, deploy A2 with exact protected-event shape checks, sanitized future history capture, a database backstop against waiver re-indexing, a worker claim-pause barrier, and canonical semantic-projection version/hash markers. History capture must ignore derivative-only Qdrant acknowledgements. Existing event, entity, and history evidence remains byte-equivalent.
3. **Remove unsafe semantic derivatives:** pause and drain worker claims through the database barrier, then use an idempotent dry-run/execute/verify operator job to neutralize replayable protected outbox rows, delete protected event and waiver points, and rebuild surviving entity points only from the shared sanitized projection. Absence of visible payload prose is not proof; verification requires the projection version and SHA-256 of the exact text sent for embedding. No network operation runs inside Alembic.
4. **Publish truthful schema coherence and retire gateway writers:** stage the signed, content-addressed version-2 contract as not active, make the proxy invalidate on its complete digest rather than tool-name changes, repair stale descriptions, and prove every callable Council member through upstream, proxy, and a newly listed client. Production activation requires the backend floor and a writer-retirement receipt. In the activation build physically remove failed-plan debt, waiver, `no_entry_found`, consultation/ref, impact-prose, generic `runbook_exit`, local journal/HMAC authority, and every direct or indirect fallback. No public legacy input or runtime selector survives the one-way cutover.
5. **Freeze the retired state only after zero-suppression proof:** exercise normal, retry, Council, BQ, close, and indirect telemetry paths and prove no legacy writer attempt reached canonical or derivative storage. Only then add the irreversible database freeze for protected legacy state mutations. Rollback must preserve the freeze and must never re-enable the retired writers.
6. **Establish Git truth:** use a locked service-owned bare mirror fetched from an allowlisted immutable remote URL. Disable hooks, alternates, and file protocol; preflight per-blob and aggregate sizes; record remote identity, `FETCH_HEAD`, full commit, catalog blob digest, and fetch time. Catalog, schemas, and excerpts come from that one object graph. Fetch/object failure is infrastructure failure, not an honest gap or stale fallback.
7. **Deliver discovery:** deterministic all-corpus search, one-call accepted-plan context, byte-identical lost-response retry, bounded complete envelopes, and automatic context injection at the common child-dispatch provider boundary.
8. **Protect and preserve actions:** add a static server-owned risk/effect registry for every tool and subaction. It distinguishes known routine execution from operating-contract changes and makes unknown mutations scoped uncertainty. Register intent before execution; enforce due OPEN obligations before the next component behavior change; bind repository writers to a per-action session/actor/canonical-argument candidate-ref challenge; observe non-Git outcomes through backend execution or authoritative provider audit state. High-risk emergency override is a signed exact-action Max authorization, not a boolean, and caller-supplied work or dispatch classes never lower risk.
9. **Replace close semantics:** remove caller impact inputs; use server-owned session baselines, action and provider evidence, per-action current remote refs, remote ancestry/path/section verification, canonical obligations, signed coverage receipts, and the backend PREPARE/COMMIT/outbox contract above. Keep only semantic obligations nonblocking; mechanical or trusted-integrity failures abort with zero writes.
10. **Repair the corpus controls:** current boot pin, complete critical-runbook registration, CI on PR and main push, zero lint-red ACTIVE members, and retirement or repair of the misleading harness. Corpus changes use a two-commit invariant: first commit the exact content/archive snapshot; then run the deterministic manifest refresher against that full checked-out `HEAD` and commit the validated ledger as its direct descendant. Agents never type blob IDs or select a stale inventory commit by hand.
11. **Shadow and sample:** relevance and impact decisions run in shadow and are independently sampled before activation. Semantic REQUIRED/UNCERTAIN outcomes remain nonblocking after activation; blocking is limited to immutable-context integrity, trusted evidence, recoverable-work preservation, high-risk action protection, and transaction correctness.

### 12.6 Deployed tool-and-Council contract

Every gateway build/deployment must publish a content-addressed, machine-readable contract artifact generated from the exact code and configuration being deployed. The artifact is pinned by both the full gateway commit/deployment identity and its SHA-256 digest; consumers must reject a missing artifact, a digest mismatch, an artifact naming a different deployed SHA, or an unpinned `latest` lookup. At minimum it contains:

- the artifact format version, full upstream handler SHA/release identity, full proxy release identity, policy/config revision, and schema digest;
- each exposed tool's exact name, title/description, input and output/result JSON Schemas, annotations, `_meta`, and server-owned effect/risk projection, including argument names, required keys, action/mode enums, agent/member enums, a multi-action discriminator where applicable, explicit action classifications, and a mutating/high-risk fallthrough for an unrecognized action;
- the deployed Council gate constants (`REQUIRED_MEMBERS` and `VALID_MEMBER_IDS`), Hall `VALID_AGENTS` and `DEFAULT_AGENTS`, and a machine-readable current role projection identifying builders, voters, paused members, and retired members; and
- a machine-readable runbook-lifecycle projection naming the plan/close tools and protocol family, one-call context delivery and exact-retry properties, immutable delivery binding, physical legacy absence, close receipt and obligation-transaction protocol, action evidence, and per-action publication/authorization receipts bound to exact canonical arguments; and
- source identifiers sufficient to reproduce every projected constant without reading a mutable working tree.

The artifact format is versioned. Version 2 requires `outputSchema` and effect
metadata for every tool. Effect and risk are separate: a whole-tool mutation may
be explicitly low, medium, or high risk, while a multi-action tool must classify
every advertised discriminator value and default any unrecognized/future value
to mutating/high risk. The effect projection states at both the tool default and
each action whether an exact-argument receipt is required. Under the target
lifecycle, every declared high-risk mutation and the default-high action
fallthrough requires it; explicitly classified low/medium plan and close
mutations do not acquire a circular pre-plan receipt requirement.

Council lifecycle labels describe callable reality. A member that is excluded
from voting but remains exposed by dispatch or Hall is `paused`, with the
limitation signed in the artifact; it is not `retired`. A `retired` member must
be absent from every callable enum and Hall surface. This prevents a role label
from concealing a still-operational compatibility path.

The version-2 target result contract is substantive rather than a discriminator
label. `kd_session_plan` exposes no runbook-evidence inputs. Its typed
`PLAN_ACCEPTED` result carries plan revision, session, instance, exact objective
and request digests, work type, exact activation/catalog/manifest/inventory
identities, singleton `complete=true`, a 0–40,000 exact byte count, delivery
digest, and a ranked context record for every objective. Every candidate carries
runbook and stable-section identities, path, heading, bounded excerpt/digest,
rank, policy lane, and match evidence. The contract also states that an
unchanged lost-response retry returns byte-identical content and a changed
request is rejected.

`kd_session_close` exposes no runbook decision or evidence input. Its
`COMMITTED` result carries singleton `COMMITTED` and `immutable=true`,
transaction-, close-request-, request-digest-, session-, evidence-freeze-, and
signature identities plus typed per-obligation outcomes. A schema that only
lists discriminator literals is not proof of these protocols; each outcome
conditionally requires its corresponding payload fields.

For each high-risk/default-high tool or action, the target input schema exposes
an optional, satisfiable non-empty string `action_receipt`, the output discriminator includes the zero-semantic-write
`ACTION_CONTEXT_REQUIRED` result, and `action_context` carries context identity,
canonical-argument digest, session, component, policy revision, and expiry. A
global action-receipt claim cannot compensate for a missing per-tool or
per-action binding.

Outcome-to-payload conditions must be exact and satisfiable. An `if` branch
with extra narrowing predicates, an enum that admits `complete=false` or
`immutable=false`, or required lifecycle fields typed as null is not rollout
evidence even when the corresponding field names are present.

Integrity and rollout readiness are distinct verdicts. A pre-cutover artifact
that still projects caller-authored `runbook_consultation`, `runbook_refs`,
legacy `runbook_exit`, local authority, or missing typed delivery/committed/action
receipts is `NOT_READY` even if its old signature verifies. Target readiness
requires coherent target plan/close schemas, automatic delivery marked required,
`legacy_protocol=absent`, a positive bounded context limit, all per-tool
high-risk bindings, and an unconditional signed cutover-status check. After
activation, neither the runtime nor the validator has a selector that can serve
the old artifact. A target label over legacy inputs, discriminator-only results,
or an unbound high-risk mutation is invalid. The deployment check invokes the
validator's explicit readiness requirement; a valid signature alone never
enables target behavior.

Artifact generation is part of deployment, not a documentation job. The gateway deployment check fails closed when a required gate member is absent from the callable dispatch schema, a role projection contradicts the deployed constants, or Hall defaults are not members of Hall `VALID_AGENTS`. A successful deployment publishes the artifact before its schema is treated as current; the runbooks repository advances its artifact SHA/digest pin through the normal reviewed path.

Artifact bytes use RFC 8785 JSON Canonicalization Scheme and an algorithm-fixed
Ed25519 signature envelope containing `kid`, issuer, audience, artifact digest,
and signing-key validity metadata. Verification is mandatory and has no
unsigned or optional-dependency fallback. Key rotation uses an explicit overlap
window and revocation list; an unknown/revoked key, noncanonical payload,
algorithm substitution, or signature mismatch is a hard contract failure. The
content-addressed artifact is immutable and is never recovered through a
mutable alias.

The upstream `/health` and `/api/tools` responses, proxy health and tool-list
responses, and boot/context envelope all expose the same handler SHA, proxy
release identity, and contract digest. Proxy cache identity is that complete
digest, not the set of tool names. Any digest change invalidates cached schemas
and emits `notifications/tools/list_changed`. A refresh or signature failure
puts the proxy in `SCHEMA_CONTRACT_STALE`: health is degraded, new sessions and
mutating calls fail closed, and the prior schema is never presented as current.
Accepted mutating calls bind the client-observed contract digest so a connection
that has not relisted cannot silently cross a schema change.

Runbooks CI on pull requests and main pushes validates every ACTIVE, non-historical executable example against that pinned artifact. The validation scope includes structured calls in §E and §I, their `expected_answers` tool calls, and any other example explicitly marked executable. Tool names and argument keys must exist; required keys must be represented; literal enum values must be accepted. Placeholders may defer only value validation, never validate an unknown argument. The same job validates current Council roster and role assertions in §C, §D, and operative scenarios against the artifact's structured Council projection. Current role claims must be represented in a deterministic machine-readable assertion/table shape; uncheckable current-role prose is a lint failure rather than silently trusted.

Content inside a balanced `<!-- catalog:historical -->` ... `<!-- /catalog:historical -->` span is explicitly exempt from deployed-contract comparison because it intentionally preserves obsolete calls and roster snapshots. Historical content still receives ordinary Markdown/structure checks, and an unbalanced or nested historical marker is a CI failure. The exemption never applies to frontmatter, §E current operations, §H current invariants, or the current scenario set unless those bytes are wholly enclosed by a valid historical span.

### 12.7 Promotion bar

- 100% of surviving operational documents are ACTIVE and cataloged; anything else is recoverably archived.
- Catalog, router, README, boot pin, and section index are generated and current.
- At least 90% top-three retrieval on a reviewed task-language benchmark; the historical waiver subjects are the initial corpus.
- Zero obligations from failed or retried plan calls; zero duplicate obligation IDs.
- Zero ACTIVE strict-lint failures.
- At least 95% one-call first-plan success with complete useful context.
- At least 90% precision and recall for `runbook update required` on an independently reviewed sample.
- Zero semantic false blocks; only trusted mechanical/integrity and high-risk protection failures block.
- Fresh-agent evaluations measure the correct first safe action after content delivery; they do not treat an author's self-written LLM exam as proof.
- The pinned deployed-contract artifact resolves to the running gateway SHA and digest, and its Council contract is internally coherent.
- The signed artifact is format version 2 and the deterministic runbook-lifecycle readiness check returns `READY`; legacy fields and selectors are absent and no pre-cutover artifact can be selected.
- 100% of ACTIVE non-historical executable tool examples and current Council roster/role assertions pass the deployed-contract CI check; historical spans are excluded only through balanced markers.
- Upstream, proxy, boot, and a freshly listed client report one contract digest; a description-only, enum-only, `_meta`-only, or policy-only change invalidates the cache and produces a relist notification.
- Contract signature/key-rotation negative tests, stale-cache mutation refusal, one-call context-before-write and byte-identical retry tests, response-size tests, and every close-transaction crash boundary pass against a disposable namespace.
- High-risk authorizations and repository publication bindings are proven one-use and exact-action/argument/ref/session-bound; unclassified mutations default impact-bearing, and rollback never re-enables legacy attestation/debt writers.
