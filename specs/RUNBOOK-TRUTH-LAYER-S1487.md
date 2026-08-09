# Runbook Truth Layer — Gate 1 design

Authored: mars / S1487, 2026-08-09. Measured at `origin/main` `6eed2d7055dc0edabf71d1cd31e98241d5cd001f`.
Authority: Max directive S1487, recorded verbatim at `config:runbook-programme-exclusive-focus` v2.

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

This dissolves three of the six conditions the CC/Kimi/GLM panel raised against the gate
design (`hall-65898c9003bae`): silent omission, pin-versus-deployed staleness, and the
conformance/blanket bars. They were careful answers to a question this design no longer asks.
Three survive and get sharper, because the check is now the product rather than a hurdle.
They are carried as binding constraints in §5 and §1.4.

## §1 Measured starting state

All figures read from the tree at `6eed2d7`, not asserted.

| Fact | Value |
|---|---|
| Markdown at repository root | 83 (includes `README.md`, `TOPIC-ROUTER.md`) |
| Markdown under `runbooks/` | 22 |
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

**AC1.** The catalog generator enumerates every `*.md` in the repository except generated
index artifacts (`README.md`, `TOPIC-ROUTER.md`, `CATALOG.json`) and `archive/**`. No page is
excluded for location, missing frontmatter, missing `runbook_id`, missing `status`, or
template non-conformance.

**AC2.** Each entry carries `id_provenance: declared | derived`. When `runbook_id` is present
it is used and marked `declared`. When absent, the id is derived from the path slug and marked
`derived`. A derived id is a real id; it is not a placeholder and does not degrade the entry.

**AC3.** Each entry carries `authority`, and `authority` is **derived from the page only**.
If the page declares `authoritative_for` or `error_signatures`, the catalog carries them. If it
declares none, the catalog carries none. The catalog may never assert authority a page does not
claim for itself. *(Council M4, all three reviewers. This is the live `builder-controls.md`
defect: on main that page is a fully routed catalog member carrying aliases, domain,
`authoritative_for` and `error_signatures` while its own frontmatter declares none of them.)*

**AC4.** Post-build assertion: `catalog entry count == corpus file count`, exact. A page that
cannot be parsed still gets an entry, with `parse_error` recorded on it. Nothing is ever
silently dropped.

## §3 Easy to find (`2_easy_to_find`)

**AC5.** Topics, aliases and error signatures are **derived from the page body on every page,
always** — headings, the filename slug, and every literal error string, exception name and
refusal identifier that occurs in the text. Declared frontmatter is merged in as an addition,
never as the sole source and never as a ceiling. Finding 2 is the reason: hand-curation, not
visibility, is what produced a 0-of-8 canary score on pages the catalog already held. A design
that indexes only what an author remembered to declare reproduces that score with more pages.

**AC5a.** Extraction is literal and verifiable: every emitted signature must occur verbatim in
the file it is attributed to, and the generator asserts this. Nothing is invented.

**AC6.** Derived signals are marked `derived` and are never presented as declared.

**AC7.** Verification state may **rank** search results. It may never filter them. There is no
query that hides an unchecked or contradicted page; a contradicted page is shown with its
contradiction, because knowing a page is wrong is more useful than not finding it.

**AC8.** Measured, not assumed: a fixed retrieval set of at least 30 real questions drawn from
this session and prior handoffs, each with the page a human judges correct, run against the
router and the search index. Baseline is recorded before the change and the same set is re-run
after. The acceptance figure is recall on that set, reported honestly, not "the page exists".

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

**AC12 — the unit is the claim, and the claim is a literal.** A claim is an assertion naming
something checkable in a system we control: a file path, a symbol, an error string, an
environment variable, a command, a config pin, a port, a model string, or a line anchor.
A claim resolves against a named system at a named commit and returns exactly one of:

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

**AC15 — output is per-claim and evidence-bearing.** Every claim reports its verdict, the
literal it looked for, the system and commit it looked in, and the location it found or failed
to find. A verdict without a citation is a defect.

**AC16 — freshness is displayed, never enforced.** Each entry records `last_checked_at`,
`checked_against` (system + commit), and whether that commit is the currently deployed one.
A stale check is shown as stale. Staleness never removes a page and never blocks anything.
*(Council M3 asked for pin-equals-deployed as a gate; under index-everything the honest
answer is to show the gap rather than fail closed on it.)*

**AC17 — the checker is proven against pages that must fail.** A fixture set of deliberately
false pages — wrong symbol, right symbol wrong literal, moved anchor, retired env var — each
of which the checker must return `CONTRADICTED` for. The checker ships with this suite or it
does not ship. *(Kimi objection 2: the mechanism is one manual run over 31 controls; its
trustworthiness equals its precision and recall, and nothing has measured either.)*

**AC18 — corpus-wide first run.** The checker runs over the entire corpus once and the result
is published: how many pages carry checkable claims, how many verified, how many contradicted,
how many are pure prose. That number is the honest starting picture of how true our written
knowledge is, and nobody currently knows it.

**AC18a — one page proves it live, on a schedule, by being broken.** At least one runbook
carries a claim check that runs on a schedule and visibly marks the page stale when it fails.
Proof of delivery is not that the check runs; it is that the claim is deliberately broken and
the page visibly goes stale, then is repaired and visibly recovers. Standing acceptance criterion
on `build:bq-runbook-truth-layer-s1482`.

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

1. Catalog entries equal corpus files, exact. Today 21 of 105.
2. Retrieval recall on the fixed 30-question set, before and after, reported as a number.
3. `runbook new` produces an indexed page in one command, demonstrated.
4. A page edited with no template work stays indexed, demonstrated.
5. `runbook check` runs from the CLI and from the MCP tool, same output, demonstrated on the
   same page from both.
6. The false-page fixture suite passes: every deliberately wrong page returns `CONTRADICTED`.
7. The corpus-wide first-run figures are published.
8. `runbooks/runbooks.md` exists, is indexed, and its own check result is published.
9. Verified from outside, legacy path removed, runbook indexed — Max's DONE, S1459.

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

## §9 Open for the Council

1. Derived topics for 60 frontmatter-less pages: does content derivation reach a useful
   precision, or does it flood the router with noise and make finding *harder*? AC8 is the
   only honest test and it must run before this is called done.
2. Line anchors rot fastest and GLM flagged them as a likely source of false `CONTRADICTED`.
   Proposal: anchors are advisory and never produce `CONTRADICTED` on their own — only the
   symbol or literal they point at can. Confirm or reject.
3. `authoritative_for` is self-declared, which Kimi notes creates an incentive to declare less
   and verify less while the index routes broadly anyway. AC3 forbids the index from adding
   authority, but nothing forces a page to claim what it is in fact used for. Is that a gap
   worth closing now, or after the first corpus-wide run tells us whether it happens?
