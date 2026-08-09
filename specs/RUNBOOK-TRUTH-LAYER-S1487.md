# Runbook Truth Layer — Gate 1 design

Authored: mars / S1487, 2026-08-09. **Revision 2**, folding the unanimous CC/Kimi/GLM
round-1 mandates. Measured at `origin/main` `6eed2d7055dc0edabf71d1cd31e98241d5cd001f`.
Authority: Max directive S1487, recorded verbatim at `config:runbook-programme-exclusive-focus` v2.
Round 1: CC `b74ebc42`, Kimi `74ec6af1`, GLM `1883970f` — all three approve the spine, all three
mandate revision. Every mandate is folded or answered below; §10 records the disposition.

> "I consider finished when all our runbooks are indexed and easily find, update and
> create, and able to be checked against ground truth by our Agents and orchestrators,
> with a clear process for doing these things"

## §0 What changed, and why this supersedes rather than amends

The approved S1413 Gate 1 design and the S1487 accuracy-gate draft both make verification
the **admission condition** for entering the catalog. Under the directive above that is
wrong at the root, so both are re-authored here rather than patched.

**Indexing is decoupled from authority.** The catalog is a card catalogue, not a seal of
approval. Every page is findable. Verification is a capability that can be run against any
page at any time by any agent or orchestrator, and its result is *displayed beside the page*,
never used to hide it.

Two of the six conditions the CC/Kimi/GLM panel raised against the gate design
(`hall-65898c9003bae`) are genuinely dissolved by this change: silent omission, closed by AC1+AC4's
exact-count assertion, and the conformance/blanket bars, which were objections to an admission gate
that no longer exists.

**Pin-versus-deployed staleness is NOT dissolved — it is converted, and the residual risk is
retained and named.** All three reviewers made this point independently. AC16 turns a hard gate into
a displayed fact, which is the right move under index-everything, but the original risk survives: an
agent can act on a page that is stale-but-`VERIFIED`, and nothing stops it. The mitigation is
display plus cadence (AC16, AC18b), and it depends on every consumer honouring `last_checked_at`.
Recorded here as a standing residual risk rather than filed as a solved problem.

Three conditions survive and get sharper, because the check is now the product rather than a hurdle.
They are carried as binding constraints at AC3, AC13 and AC19.

## §1 Measured starting state

All figures read from the tree at `6eed2d7`, not asserted.

| Fact | Value |
|---|---|
| Markdown anywhere in the repository | 157 |
| Of which: `tests/` (mostly deliberately-broken linter fixtures) | 32 |
| Of which: `specs/`, `templates/`, `audits/`, `contracts/`, `archive/` | 20 |
| Markdown at repository root | 83 (includes generated `README.md`, `TOPIC-ROUTER.md`) |
| Markdown under `runbooks/` | 22 |
| **Corpus in scope (root minus generated, plus `runbooks/`)** | **103** |
| `CATALOG.json` entries | 21 |
| Catalog entries whose path is under `runbooks/` | 21 |
| Catalog entries whose path is at root | 0 |
| Root pages carrying `runbook_id` | 0 |
| Root pages carrying `status: ACTIVE` | 0 |
| Root pages with no frontmatter at all | 60 |
| `runbooks/` pages carrying `runbook_id` + `status: ACTIVE` | 21 of 22 |
| `TOPIC-ROUTER.md` rows | 112 |

**Finding 1 — exclusion is location plus opt-in, not template.** Every excluded page is at the
root *and* declares no `runbook_id` *and* declares no `status: ACTIVE`. Sixty have no frontmatter
to read. So "all indexed" is mostly a generator change — stop requiring a page to opt in and stop
requiring it to sit in one directory — not a new gate.

**Finding 2 — indexing a page is not the same as indexing its content, and this is the bigger
failure.** Measured in S1484 against eight real error strings from a live session: the catalog
scored 0 of 8. Three of the eight *are* documented, and all three are in `runbooks/agent-dispatch.md`,
which is one of the 21 already indexed. The index failed on content it already held, because it
indexes a hand-curated `error_signatures` list rather than the page body. The catalog declares
roughly 72 signatures across all 21 pages; `agent-dispatch.md` alone contains 171 distinct
snake_case identifiers. **Hand-curation is the bottleneck.** Making the other 83 visible without
fixing this would raise the score from 0 of 8 to 0 of 8.

**Finding 3 — the machinery indexed its own paperwork and left the business undocumented.** The
21 indexed and 83 unindexed pages have zero filename overlap and the split is not random. The
indexed set is almost entirely about how the AI machinery runs itself: council, gates, dispatch,
policy, review collection. Every page describing the actual business — AWS, Qdrant, the backend,
the frontend, Cloudflare, CRM, AIM Data, the seller publish journey, schema migration, the trust
channel — is in the invisible 83. Search can reach our paperwork and not our product.

## §2 All indexed (`1_all_indexed`)

**AC1 — the corpus is defined by name, and "everything" means everything IN IT.** The corpus is
exactly: markdown at the repository root, plus markdown under `runbooks/`. Currently 103 pages.
Excluded by name and for stated reason, not by quality judgement:

| Excluded | Count | Reason |
|---|---|---|
| `README.md`, `TOPIC-ROUTER.md`, `CATALOG.json` | 3 | Generated index artifacts; indexing the index is circular |
| `tests/**` | 32 | Deliberately-broken linter fixtures, including the false pages AC17 itself creates. Indexing these routes search to anti-content |
| `specs/**` | 16 | Design documents, not operating instructions. A separate question, deliberately deferred and named as deferred |
| `templates/**`, `audits/**`, `contracts/**`, `archive/**` | 4 | Not operating instructions; `archive/**` is the historical layer AC8a keeps separate |

Within the corpus, **no page is excluded** for location, missing frontmatter, missing `runbook_id`,
missing `status`, or template non-conformance. *(Kimi M1, blocking. Round 1 said "every `*.md` in
the repository", which would have produced ~150 entries including the test suite's deliberately
false pages, while every figure in the document counted 103. The exact-count assertion in AC4 would
have passed on a corpus containing planted lies.)*

**AC2.** Each entry carries `id_provenance: declared | derived`. When `runbook_id` is present
it is used and marked `declared`. When absent, the id is derived from the path slug and marked
`derived`. A derived id is a real id; it is not a placeholder and does not degrade the entry.

**AC2a — ids are pinned at first index and survive relocation.** A derived id is written back and
never recomputed. When a page moves under §7's later relocation, the id is unchanged and the old
path is retained as an alias. Otherwise a move orphans every citation, the page's own check history,
and its fixtures — for exactly the root pages most likely to be moved. *(Kimi M6.)*

**AC3.** Each entry carries `authority`, and `authority` is **derived from the page only**.
If the page declares `authoritative_for` or `error_signatures`, the catalog carries them. If it
declares none, the catalog carries none. The catalog may never assert authority a page does not
claim for itself.

> **RETRACTION, recorded rather than quietly edited.** Revision 1 justified this rule with a
> `builder-controls.md` example — that the page is a fully routed catalog member whose own
> frontmatter declares nothing. **That is false.** All three reviewers checked it independently and
> the author re-verified: at `6eed2d7` the page is at the repository root, absent from
> `CATALOG.json`, absent from `TOPIC-ROUTER.md`, and its frontmatter does declare `system_name`,
> `purpose_sentence`, `owner_agent` and `authoritative_scope`. It is one of the invisible 81, not a
> routed entry. The claim was inherited from an S1485 handoff and repeated as measured.
>
> This is the second time this exact failure has hit this programme: `build:bq-runbook-truth-layer-s1482`
> already carries an S1484 correction retracting a comparable inherited claim about
> `schema-migration.md`. Two occurrences, both caught only by a machine reading the tree, both in
> documents arguing for checking claims against the tree. It is the strongest available evidence for
> AC12–AC18 and it is left in the open where the next author will see it.
>
> AC3 stands on its own reasoning as a preventive rule. No live instance of the defect is claimed.
> If the first corpus-wide run (AC18) surfaces a real one, it is recorded then.

**AC4.** Post-build assertion: `catalog entry count == corpus file count`, exact. A page that
cannot be parsed still gets an entry, with `parse_error` recorded on it. Nothing is ever
silently dropped.

## §3 Easy to find (`2_easy_to_find`)

Round 1 correctly split what Revision 1 conflated. A literal error string and a conceptual topic
are different signal types and need different precision. One extraction rule for both was the
design's most likely failure mode. *(GLM M3, Kimi's flood finding, CC's index/router split.)*

**AC5 — error signatures: exhaustive, literal, every page, always.** Every literal error string,
exception name and refusal identifier occurring in the body becomes a searchable key. Declared
frontmatter is merged in as an addition, never as the sole source and never as a ceiling. Finding 2
is the reason: hand-curation, not visibility, produced a 0-of-8 canary on pages the catalog already
held, and indexing only what an author remembered to declare reproduces that score with more pages.

**AC5a.** Extraction is literal and verifiable: every emitted signature must occur verbatim in
the file it is attributed to, and the generator asserts this. Nothing is invented.

**AC5b — topics and aliases: conservative.** Derived from headings, the filename slug and the
purpose sentence only. NOT from every `snake_case` token in the body. Cross-page duplicates are
deduplicated, and a term appearing on many pages is a weaker signal, not a stronger one.

**AC5c — derived ranks below declared.** Every signal records its provenance and declared signals
outrank derived ones in ranking. Provenance is never presented as declaration.

**AC6.** Derived signals are marked `derived` and are never presented as declared.

**AC7.** Verification state and signal provenance may **rank** search results. Neither may ever
filter them. There is no query that hides an unchecked or contradicted page; a contradicted page is
shown with its contradiction, because knowing a page is wrong is more useful than not finding it.

**AC7a — two surfaces, different jobs.** The machine index optimises recall: everything derived,
every literal searchable. The human-readable router optimises precision: only declared and
high-confidence topics are promoted into it. A precision failure then degrades ranking rather than
drowning the router. *(CC and Kimi converged on this independently as the answer to §9 Q1.)*

**AC8 — measured, with a pre-registered bar.** A fixed retrieval set of at least 30 real questions
drawn from this session and prior handoffs, each with the page a human judges correct, run against
the router and the search index. Baseline recorded before the change; the same set re-run after.

Two numbers, both required, both pre-registered before the run:
- **Recall must not fall below baseline.** A measured regression fails the gate. It is not enough to
  report it honestly.
- **Precision@5 is reported alongside.** Recall alone is gameable by flooding, which is precisely the
  risk AC5b exists to contain.

*(All three reviewers raised this independently. Round 1 said the figure would be "reported
honestly", with no threshold — which would have allowed a measured regression in the directive's
core verb to ship as done. This was the weakest criterion in the design and it guarded the riskiest
change in it.)*

**AC8a — runbooks never blend with the archive.** A runbook answers "what is true now"; a
session log or build note answers "what happened once". A runbook result must always outrank and
be visually distinct from an archive result, with provenance and recency on every row. This is a
standing Max constraint from S1482: semantic search over history confidently returns superseded
material, and mixing the two destroys the only property that makes a runbook worth having.
Measured today: `allai_search` for the production database access recipe returned five results,
all session logs and build notes, zero runbooks.

## §4 Easy to update, easy to create (`3_easy_to_update`, `4_easy_to_create`)

**AC9.** Updating a page is editing the file. No template conformance is required to remain
indexed, and no promotion ceremony is required to publish a correction. The ~25 deterministic
conformance checks are removed as an admission condition. *(A page may still choose the A–K
shape; it is a convention, not a gate.)*

**AC10.** `runbook new <slug>` scaffolds a page with the minimum viable frontmatter — id,
one-line purpose, and the systems it describes — and nothing else mandatory.

**AC11.** Creating and updating are both documented in the runbook runbook (§6) and that page
is itself indexed, so the answer to "how do I write one" is reachable by the same search that
finds everything else. Today it is not: the standard lives in `specs/BQ-RUNBOOK-STANDARD.md`,
which is a spec and not indexed, and `runbook-first-gates.md` sits at the root, is therefore
unroutable, and its own header declares it legacy.

## §5 Checkable against ground truth (`5_checkable_against_ground_truth`)

This is the new capability and the core of the build.

**AC12 — the claim grammar. A claim is recognised by FORM, not by guesswork.** Round 1's blocking
mandate was that the design said what a claim is but not how the checker finds one, which is the
hard part of the build. A literal is a claim if and only if it appears in one of these forms:

| Form | Example | Binds to |
|---|---|---|
| Backticked path | `` `tools/agents.py` `` | the system that owns that path |
| Backticked symbol with a path in the same sentence or table row | `` `_council_agent_mode_rejection` `` | that path in that system |
| Backticked literal introduced by a naming verb — *returns, raises, emits, is named, is set to* | returns `` `checkout_not_pinned` `` | the system named in scope |
| Frontmatter `error_signatures` / `authoritative_for` entry | declared row | the declaring page's system |
| Explicit pin — `system @ sha`, `MODEL=x`, `PORT=n` | `koskadeux-mcp main @ 96c62109` | that system at that commit |
| Fenced block tagged with a system | ```` ```yaml operate ```` | the tagged system |

Everything else is prose and resolves `UNKNOWN`. Bare words, unbackticked mentions and narrative are
never claims. **The system a claim binds to is resolved from, in order:** an explicit pin on the
claim; the page's frontmatter `system_name` or `authoritative_scope`; the nearest preceding heading
that names a system. If none resolves, the claim is `UNKNOWN` with reason `unbound_system` — never
guessed. *(CC M2, blocking.)*

A claim resolves against its bound system at a named revision and returns exactly one of:

- `VERIFIED` — the **claimed literal** is present at the cited location.
- `CONTRADICTED` — the cited location exists and the literal is absent or different.
- `UNKNOWN` — not mechanically checkable (prose, rationale, judgement, intent).

**AC13 — existence is not accuracy.** `VERIFIED` requires the exact claimed literal, not that
a same-named symbol resolves somewhere. A page claiming an error string must have that string
present verbatim; a page claiming a config pin must have that value present. *(Council M1, all
three reviewers, blocking.)*

**AC14 — the checker is a capability, invoked two ways.** A CLI for orchestrators
(`runbook check <page|--all>`) and an MCP tool for agents and allAI. Same engine, same output,
no privileged path. Read-only. It never edits a page and never changes catalog membership.

**AC14a — resolving systems that are not this repository.** Most real claims are not local.
`builder-controls.md` cites `koskadeux-mcp main @ 96c62109`; nothing of that exists in this checkout.
Resolution is by a named system registry mapping a system name to how it is read:
- **Git systems** — resolved by read-only fetch of the pinned commit into a bare cache. If the pin is
  ungettable, the claim is `UNKNOWN` with reason `revision_unavailable`. Never `CONTRADICTED`.
- **Live systems** — AWS, Qdrant, Cloudflare, the CRM, the deployed backend. These have no commit.
  They are read by an explicit read-only probe, and the probe's response is recorded as evidence per
  AC15 with the timestamp standing in for the revision.
- **Anything with no registry entry** — `UNKNOWN`, reason `system_unregistered`.

*(CC M3 and Kimi M4. Kimi's version is the sharper one and it is stated plainly here: Finding 3 says
the missing knowledge is the business — AWS, Qdrant, Cloudflare, CRM, the publish journey — and
those are live systems with no commit. A checker that models only git would prove the machinery's
paperwork and leave the pages that motivated this design reading UNKNOWN. Live-system probes are
therefore in scope, not a later phase.)*

**AC15 — output is per-claim and evidence-bearing.** Every claim reports its verdict, the
literal it looked for, the system and commit it looked in, and the location it found or failed
to find. A verdict without a citation is a defect.

**AC16 — freshness is displayed, never enforced.** Each entry records `last_checked_at`,
`checked_against` (system + commit), and whether that commit is the currently deployed one.
A stale check is shown as stale. Staleness never removes a page and never blocks anything.
**This is a conversion, not a resolution, and the residual risk is retained.** An agent can act on
a page that is stale-but-`VERIFIED`. Display plus cadence (AC18b) is the mitigation; it depends on
consumers honouring `last_checked_at`. Named here rather than filed as solved. *(All three
reviewers, round 1.)*

**AC17 — the checker is proven against pages that must fail.** A fixture set of deliberately
false pages — wrong symbol, right symbol wrong literal, moved anchor, retired env var — each
of which the checker must return `CONTRADICTED` for. The checker ships with this suite or it
does not ship. *(Kimi objection 2: the mechanism is one manual run over 31 controls; its
trustworthiness equals its precision and recall, and nothing has measured either.)*

**AC17b — the dual fixture set: claims the checker must FIND.** A set of known-true claims the
checker must return `VERIFIED` for, not `UNKNOWN`, producing a claim-detection recall number
published alongside the CONTRADICTED recall from AC17. Without it, a checker that shrugs `UNKNOWN` at
95% of real claims passes AC17 trivially on five planted lies, and AC18's prose count would then read
a broken checker as "our knowledge is mostly prose, fine". `UNKNOWN` is not allowed to be an
unmeasured dumping ground. *(CC M4.)*

**AC18 — corpus-wide first run.** The checker runs over the entire corpus once and the result
is published: how many pages carry checkable claims, how many verified, how many contradicted,
how many are pure prose. That number is the honest starting picture of how true our written
knowledge is, and nobody currently knows it.

**AC18a — one page proves it live, on a schedule, by being broken. POST-BUILD, not Gate 1.**
This is proof of delivery for the built system and cannot be demonstrated at Gate 1, because §8b
blocks the build until the gateway bounces. Explicitly out of scope for Gate 1 approval; explicitly
in scope for the gate that follows. *(GLM M5.)* At least one runbook
carries a claim check that runs on a schedule and visibly marks the page stale when it fails.
Proof of delivery is not that the check runs; it is that the claim is deliberately broken and
the page visibly goes stale, then is repaired and visibly recovers. Standing acceptance criterion
on `build:bq-runbook-truth-layer-s1482`.

**AC18b — re-check cadence.** The whole corpus is re-checked on a schedule, not just the one page
in AC18a. Without it every verdict ages into permanent staleness and the freshness display in AC16
becomes fiction. The cadence is stated in the runbook runbook and is itself a checkable claim.
*(Kimi M5.)*

**AC19 — what the checker does not claim.** It verifies references, not reasoning. A page whose
every claim is `VERIFIED` may still prescribe a destructive or wrongly ordered procedure. Risk
of the *action* is a separate concern from accuracy of the *references*, and this design does
not conflate them. *(All three reviewers.)*

## §6 The process, and the runbook runbook (`sixth_thing`)

**AC20.** Create `runbooks/runbooks.md` — the runbook runbook — covering the four verbs: find,
update, create, check. Indexed in `CATALOG.json` and `TOPIC-ROUTER.md` in the same change.

**AC21.** It is the first page checked under AC12–AC18, and its own result is published. If the
page describing how pages earn their place cannot itself pass the check, the check is wrong and
that is the cheapest possible place to find out.

**AC22.** `runbook-first-gates.md` is superseded by it. That page declares itself legacy in its
own header; it is retired to `archive/` in the same change, not left at the root as a second,
contradictory answer.

## §7 Removed

Removed as admission conditions, per the directive: template conformance for catalog entry;
`§K` as the mandatory evidence carrier; coverage keyed to `MATERIAL_SECTION_LETTERS`; canonical
location under `runbooks/` as a condition of being indexed; frontmatter opt-in as a condition of
being indexed; and the blanket bar in `validate_corpus_manifest(promotion_bar=True)` that fails
every `catalog_state: active` document unconditionally.

**Retained.** `runbooks/` stays the canonical *destination* for new pages — a convention the
scaffolder follows and the checker reports on, enforced by nothing. Root pages are indexed where
they are and may be relocated later by a separate, deliberate move.

## §8 Acceptance, measured

1. Catalog entries equal corpus files, exact, against the AC1 scope. Today 21 of 103.
2. Retrieval on the fixed 30-question set: recall must not fall below baseline, precision@5 reported.
3. `runbook new` produces an indexed page in one command, demonstrated.
4. A page edited with no template work stays indexed, demonstrated.
5. `runbook check` runs from the CLI and from the MCP tool, same output, demonstrated on the same
   page from both.
6. Both fixture suites pass and both numbers are published: false pages return `CONTRADICTED`
   (AC17), known-true claims return `VERIFIED` rather than `UNKNOWN` (AC17b).
7. The corpus-wide first-run figures are published, including the count of claims that resolved
   `UNKNOWN` and why.
8. `runbooks/runbooks.md` exists, is indexed, and its own check result is published.
9. Verified from outside, legacy path removed, runbook indexed — Max's DONE, S1459.

Out of scope for Gate 1 and owed at the next gate: AC18a's break-it-and-recover proof, blocked by §8b.

## §8a Delegation boundary

The bulk extraction pass — title, one-line purpose, the system each page describes, and every
error string literally present in the body — is mechanical and delegable, and it is mechanically
verifiable per AC5a. Three things are never delegated to any model: deciding whether a page is
still *true* (only a call to the live system settles that, and a model asked to make a page
useful will smooth over staleness, which is worse than a page that plainly looks old); authoring
content to fill a gap (five of the eight canary error strings are documented nowhere, and an
invented recipe for AWS or the money path is worse than a blank page); and deleting anything.

## §8b Known operational blocker

MP cannot build in `aidotmarket/runbooks` until the gateway bounces. The repo-registration fix
is merged to koskadeux-mcp main at `7018dfa623`, but the running gateway is older and the
reloader correctly defers the bounce while any session is live. Earliest possible build start is
after both instances have closed. Do not hand-restart to force it while the peer is live.

## §9 Settled by the panel

Round 1 posed three questions the author could not settle. All three are now answered, with CC and
Kimi converging independently on each, and GLM confirming the second.

**Q1 — derived topics on frontmatter-less pages: useful, or a flood?** Do not pre-decide, and do not
gate indexing on it. Split the surfaces (AC7a): the machine index takes everything for recall, the
human router takes only declared and high-confidence topics for precision. Rank derived below
declared (AC5c) and runbooks above archive (AC8a). Let AC8's recall floor and precision figure be the
arbiter before done is called.

**Q2 — line anchors.** Confirmed and now binding. An anchor is positional metadata, not a claim. It
may never be the sole basis of a `CONTRADICTED`; only the symbol or literal it points at can be. A
moved anchor whose symbol is present elsewhere is `VERIFIED` with a drift warning. Line numbers are
the highest-churn, lowest-value anchor we have, and this also protects every cross-repo claim, where
drift is guaranteed.

**Q3 — self-declared authority and the incentive to under-declare.** Defer, with a named trigger
rather than a vague intention. Do not add a declaration gate now; that would reintroduce the
admission condition this whole design removes. AC18's first corpus run explicitly reports the gap
between what pages are routed for and what they declare. If systematic under-declaration shows up,
the answer is usage-derived authority displayed as derived and never merged into declared (AC3).

## §10 Round-1 mandate disposition

Fifteen mandates across three reviewers, deduplicated to eleven distinct items. All folded; none
deferred or argued away.

| Raised by | Mandate | Disposition |
|---|---|---|
| CC M1, GLM M1, Kimi M3 | AC3's `builder-controls.md` example is false | Retracted in full and the retraction left visible in AC3, with the prior occurrence of the same failure named |
| Kimi M1 (blocking) | Corpus scope undefined; would index the test suite's false fixtures | AC1 rewritten: corpus named explicitly, exclusions tabulated with reasons, all figures reconciled to 103 |
| CC M2 (blocking) | No claim-extraction mechanism | AC12 rewritten as a claim grammar with a binding table and an ordered system-resolution rule |
| CC M3, Kimi M4 | No cross-repo resolution; no non-git ground truth | AC14a: system registry covering git pins, live-system read-only probes, and explicit `UNKNOWN` reasons |
| CC M5, GLM M2, Kimi M2 | No recall floor; a regression could ship as done | AC8: recall must not regress, precision@5 required, both pre-registered |
| CC M4 | `UNKNOWN` is an unmeasured dumping ground | AC17b: dual fixture set and a published claim-detection recall figure |
| CC finding, Kimi finding | Staleness converted, not dissolved | §0 and AC16 restate it as a retained, named residual risk |
| GLM M3, Kimi finding | One extraction rule for two signal types | AC5/AC5b/AC5c split; conservative topics, exhaustive signatures, derived ranked below declared |
| Kimi M5 | No corpus re-check cadence | AC18b |
| Kimi M6 | Derived ids do not survive relocation | AC2a: pinned at first index, old path retained as alias |
| GLM M4, GLM M5 | Dangling `§1.4` reference; AC18a scope vs §8b | Reference removed; AC18a explicitly scoped out of Gate 1 |
