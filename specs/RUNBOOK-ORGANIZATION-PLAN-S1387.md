# RUNBOOK-ORGANIZATION-PLAN-S1387

Status: DRAFT for Max. On acceptance this becomes the Gate 1 amendment input to BQ-RUNBOOK-CATALOG-VALIDATOR-S1229 (per CORE S16 it amends the existing item, it does not open a new one). Author: Mars, S1387. Base: runbooks main 3d4f018a, koskadeux-mcp main 645018f3.

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
