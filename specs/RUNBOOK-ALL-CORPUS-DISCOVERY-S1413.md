# S1413 — All-corpus runbook discovery before authority promotion

Status: **BINDING IMPLEMENTATION CONTRACT**

Date: 2026-08-01

Repository baseline: `73ae00e4ae6760e40e00e6cea585d4b6d4399fac`

This contract amends `specs/RUNBOOK-ORGANIZATION-PLAN-S1387.md`. Where that
plan delays discovery until documents are promoted, or describes grandfathered
documents as reachable only by explicit path, this contract supersedes it.

It does **not** create two tiers of authority. There is still one authority set:
the entries in `CATALOG.json`. The earlier sentence
“indexed-but-not-authoritative is rejected” is superseded **for retrieval**:
pending and archived material now enters search as labeled evidence leads. It
remains binding for catalog admission and action authority. This contract adds
those non-authoritative discovery leads so an agent can find existing knowledge
before it acts.

## 1. Problem proved at the baseline

The exact `CORPUS-MANIFEST.yaml` at the baseline records:

- 102 operational documents;
- 20 ACTIVE documents;
- 81 grandfathered documents with `status: pending_verification`; and
- 1 archived document.

Every record has a pinned Git blob OID. The 20 ACTIVE manifest paths exactly
match the 20 catalog entries.

Current catalog search scans only the 20 ACTIVE entries. At the exact baseline,
these four market-work probes returned no intended operational document among
the returned top results:

1. `deploy backend and run a database schema migration`
2. `publish a seller dataset through AIM Data`
3. `restore Qdrant after data loss`
4. `debug signup and two-factor authentication`

The excluded corpus already contains directly relevant pending documents,
including `ai-market-backend.md`,
`aim-data-seller-publish-journey.md`, `qdrant.md`,
`backup-and-recovery.md`, `auth-signup-flow.md`, and
`two-factor-auth.md`.

Ranking also overweights generic section intent. In
`runbook_tools/catalog/search.py` at the baseline, a weak lexical match can
receive an independent intent weight of 80 for words such as `run` or
`restore`, while excerpt and structured-literal evidence receive weights 2
and 7. That made unrelated process material outrank domain-specific market
material.

A gate cannot be runbook-first when the useful runbooks are absent from its
search surface.

## 2. Binding outcome

A search at one immutable runbooks commit MUST inspect all 102 manifest records.
The same search response MUST distinguish authority from discovery:

- ACTIVE catalog sections remain the only authority candidates.
- Grandfathered sections are discovery leads that require ground-truth
  verification.
- Archived sections are historical discovery leads and are never current
  operating instructions.

A relevant pending document MUST be findable before it is rewritten or
promoted. Promotion remains a separate, evidence-bound workflow.

## 3. Immutable corpus loading

Search MUST load `CATALOG.json`, `CORPUS-MANIFEST.yaml`, and document blobs
from Git objects, never from a mutable working tree.

For one full 40-character search SHA, the loader MUST:

1. invoke Git with replacement objects disabled;
2. load the catalog and manifest from that exact commit;
3. validate the manifest before indexing;
4. require the manifest ACTIVE path set to equal the catalog path set;
5. resolve each document path at the pinned snapshot;
6. require a regular-file Git mode;
7. recompute and match every declared `git_blob_oid`; and
8. fail closed on a missing object, path mismatch, state mismatch, duplicate
   path, unsupported mode, malformed manifest, or blob mismatch; and
9. emit at least one deterministic searchable unit for every record. When no
   body section qualifies, index a document-level fallback derived from path
   and H1/title. An H1-only file such as `session-lifecycle.md` MUST remain
   retrievable and MUST NOT be counted as searched without an indexable unit.

The response MUST bind the catalog SHA, manifest digest, inventory SHA, and
document blob OID. Fetch failure is an infrastructure error, not permission to
read a stale checkout.

## 4. Search and response model

The implementation MUST preserve the existing ACTIVE `candidates` lane for
backward compatibility and add a separate top-level `discovery_leads` lane.
Both lanes are produced by the same query and the same immutable snapshot.
Non-ACTIVE material MUST NOT be inserted into `candidates`: existing status,
eligibility, digest, counter, allocator, and client behavior assumes that lane
contains catalog candidates.

The existing synthetic repository-authoring guidance derived from `README.md`
is not an ACTIVE catalog candidate and MUST NOT remain in `candidates`. If
retained for compatibility, it MUST be returned in a separate
`supplemental_guidance` lane with explicit false candidate, action-authority,
authority-admission, and semantic-verification flags. It does not count as one
of the 102 manifest records, cannot satisfy candidate or discovery breadth, and
cannot unlock planning or action. Its source identity MUST still bind to the
same immutable snapshot. Concretely, it MUST set
`candidate_id_eligible: false`, `action_authority_eligible: false`,
`authority_admission: false`, and `semantic_verification: false`; omit
`candidate_digest`, `discovery_digest`, `discovery_lead_id`, `runbook_id`,
authority keys, owner, and `last_verified_at`; and use a distinct
`guidance_digest` bound to the exact snapshot SHA, README blob OID, and excerpt
digest.

Supplemental guidance is excluded from corpus `relevance_rank` and top-three
benchmark evaluation. A gateway may display it only after the globally merged
corpus results, and it MUST NOT displace a candidate or discovery lead. It MUST
be preceded by a separate non-truncatable warning:
**SUPPLEMENTAL GUIDANCE — NOT RUNBOOK AUTHORITY**. Its excerpt remains quoted
evidence at non-instruction precedence and MUST NOT be translated into action
steps.

Every item in both lanes MUST receive a global `relevance_rank` computed
without using catalog state, authority eligibility, risk, or promotion status
as a relevance signal. A gateway presenting results to an agent MUST merge the
two lanes by `relevance_rank`; the separate lanes are a policy boundary, not
a presentation hierarchy.

Global ranking MUST use a common feature projection available to every corpus
state: path, H1/title, Markdown heading, and document/section text. Catalog-only
aliases, topics, authority declarations, owner, verification date, risk,
status, and promotion metadata MUST NOT contribute to the global score. The
legacy ACTIVE score may remain inside `candidates` for compatibility, but it
MUST NOT determine cross-lane presentation order. A state-flip equivalence test
MUST prove that changing only catalog state and catalog-only metadata cannot
change the common relevance score or order.

For avoidance of doubt, a “declared topic” or structured literal used for
common qualification means one present in the state-neutral document
projection itself. A topic or literal supplied only by `CATALOG.json` may
contribute to the legacy ACTIVE score, but it MUST NOT qualify or rank a result
in the common cross-lane projection.

A grandfathered lead MUST include at least:

- `candidate_kind: grandfathered_discovery_lead`;
- `catalog_state: grandfathered`;
- `status: pending_verification`;
- `candidate_id_eligible: false`;
- `action_authority_eligible: false`;
- `authority_admission: false`;
- `semantic_verification: false`;
- `requires_ground_truth_verification: true`;
- `historical_only: false`;
- exact snapshot SHA, manifest SHA-256, inventory SHA, and source blob OID;
- a `discovery_digest`, never a `candidate_digest`;
- path and bounded excerpt identity;
- heading, section identity, and line bounds only when section evidence exists;
- manifest risk and batch; and
- a bounded, verbatim projection of the manifest's `verify_against` list.

The archived lead has the same prohibitions and additionally MUST include:

- `candidate_kind: archived_discovery_lead`;
- `catalog_state: archived`; and
- `historical_only: true`.

A path/title-only match MUST be returned as a document-level lead; it MUST NOT
fabricate a heading or section identifier. A non-ACTIVE lead MUST omit
`runbook_id`, authority keys, owner, and `last_verified_at` because those
catalog semantics were never admitted for it.

The search library supplies `discovery_digest`. The gateway MUST wrap a
delivered lead in a distinct, non-authoritative `discovery_lead_id` bound to
session ID, objective digest, exact runbooks SHA, manifest digest, document blob
OID, excerpt digest, and delivery expiry. It MUST be an authenticated
server-issued token or receipt; caller-minted IDs and prose are invalid. It is
never accepted where a consultation candidate ID is required.

A non-ACTIVE lead MUST NOT mint or satisfy a consultation candidate ID, unlock
an action gate, discharge runbook debt, prove a procedure true, create a waiver,
or be auto-promoted. It is a precise pointer to knowledge that the agent must
verify against the named ground truth before operational use.

Discovery MUST NOT change the legacy ACTIVE `status` or eligibility counters.
When pending material matches but ACTIVE material does not, the response keeps
`status: no_positive_candidate_in_active_catalog` and additionally reports
`discovery_status: discovery_leads_returned_unverified` and
`authoritative_gap: true`.

## 5. Ranking correction

Generic intent tokens such as `run`, `operate`, `repair`, `restore`,
`verify`, and `debug` MUST NOT independently qualify a result or contribute
a dominating score.

Intent evidence may only act as a bounded tie-breaker after domain evidence
qualifies a section. Domain qualification MUST require one of: an exact safe
`path:` query; a multi-token exact phrase or structured literal; or at least
`max(2, ceil(0.4 * subject_query_token_count))` distinct non-stop subject
tokens matched in path, title, heading, declared topic/literal, or excerpt.
The implementation MUST return an honest no-relevant-result status when the
domain threshold is not met.

Authority state MUST NOT boost or suppress relevance. Policy eligibility is
evaluated after retrieval.

## 6. Bounded delivery

The existing serialized response ceiling remains binding. Allocation MUST:

1. reserve enough space to report integrity and omission counters honestly;
2. preserve bounded ACTIVE breadth;
3. return at least one qualifying discovery lead for each query that has one;
4. allocate remaining bytes by global relevance and query breadth before
   excerpt depth; and
5. truncate excerpts, never identity, authority labels, verification flags, or
   integrity evidence.

The implementation MUST publish one deterministic configured maximum batch
size. That maximum MUST be proved against a worst-case bounded envelope that
includes integrity evidence, counters, and one compact ACTIVE identity plus one
compact discovery identity per query when both qualify. Optional supplemental
guidance MUST NOT consume mandatory corpus breadth. The implementation may
lower the configured maximum while it is being built, but it MUST NOT shrink or
partially execute a submitted batch. A submitted batch larger than the
published maximum MUST be rejected atomically before immutable loading or
retrieval, with no partial results. It MUST NOT silently violate per-query
breadth, drop policy labels, or emit an oversized response.

The response MUST separately report searched and omitted document/section counts
for ACTIVE, grandfathered, and archived states. `searched_entry_count` MUST be
102 for a complete baseline snapshot even if response-budget truncation omits
most candidates.

## 7. Runbook-first gateway behavior

The first planning interaction for a session MUST search the complete pinned
corpus for every objective and deliver the globally ordered excerpts before the
agent is allowed to act.

Caller-authored paths, section names, attestations, `no_entry_found` prose,
or free-text waivers MUST NOT substitute for server-selected search results.

Before every pending or archived discovery-lead excerpt, the gateway MUST
render a non-truncatable warning:
**DISCOVERY ONLY — NOT VERIFIED OPERATING AUTHORITY**. The warning MUST precede
the document text and show catalog state, manifest risk,
`requires_ground_truth_verification`, and the bounded `verify_against`
requirements. The excerpt is quoted evidence, not an executable instruction:
it MUST NOT be injected at system/developer precedence or automatically
translated into action steps. This ordering is required because pending
documents can contain destructive or internally contradictory procedures.

Selecting an ACTIVE candidate follows the authority policy in force for that
candidate. A grandfathered lead enters this server-bound handshake:

1. The first plan call returns `discovery_lead_id` plus structured verification
   requirements derived from the manifest and performs zero state writes. The
   session remains PLANNING.
2. While PLANNING, the gateway permits only bounded read-only inspection and
   production-safe verification tools needed by those requirements. It blocks
   builds, writes, deploys, and operational mutation.
3. A dedicated verification call accepts the server-issued lead ID and exact
   evidence receipts from trusted Git, schema, test, health, or probe adapters.
   Free-text claims, paths, reviewer names, and caller-authored attestations are
   not evidence.
4. The server validates binding, freshness, remote object identity, and the
   requirement-specific evidence. It returns a signed
   `discovery_verification_receipt_id` with outcome
   `confirmed_for_objective`, `contradicted`, or `insufficient`.
5. A second plan call may transition to OPERATIONAL only with a fresh
   `confirmed_for_objective` receipt bound to the same session, objective,
   runbooks SHA, blob, and excerpt. The receipt authorizes reliance only for
   that objective; it does not promote the document or grant general authority.

A `contradicted` or `insufficient` result keeps the session in the
read-only verification phase and exposes the authoritative gap without
claiming that no document was found. The gateway may issue a separate,
evidence-bound ground-truth receipt for a corrected procedure; it MUST NOT use
a waiver or caller prose to unlock action.

An archived lead can supply historical context but can never receive
`confirmed_for_objective` as current operating instruction. It must resolve
to current ground truth or an ACTIVE candidate before operational action.

The boot payload SHOULD expose the exact runbooks pin and the
20/81/1 availability counts. It SHOULD NOT inline the full corpus; objective
search supplies the relevant excerpts.

## 8. Acceptance tests

Implementation is not complete until automated tests prove all of the
following at a committed snapshot:

1. exactly 102 records participate: 20 ACTIVE, 81 grandfathered, 1 archived;
2. every source blob identity is verified and a mismatch fails closed;
3. a dirty checkout and Git replacement refs cannot change results;
4. catalog/manifest ACTIVE-set drift fails closed;
5. an ACTIVE and grandfathered mixed query returns both policy classes;
6. a grandfathered-only hit is a discovery result, not `no_entry_found`;
7. an archived hit is visibly `historical_only`;
8. non-ACTIVE results cannot pass consultation or action-authority validation;
9. batched results are deterministic and remain within the response budget;
10. generic intent without domain evidence cannot dominate ranking;
11. the four probes in section 1 each return a directly relevant document in
    the first three globally ordered results;
12. an independently reviewed, representative benchmark covers market
    operations—not only session, Council, and runbook-process tasks; and
13. the first-plan gateway response includes pinned excerpts and performs zero
    state writes; and
14. grouped exact `path:` probes prove that every one of the 102 manifest
    records contributes at least one searchable unit and is retrievable,
    including the H1-only `session-lifecycle.md`, with the archived record
    labeled historical;
15. changing only state and catalog-only metadata leaves common relevance
    scores and order unchanged; and
16. a grandfathered-only objective returns a lead and authoritative-gap label,
    remains in the read-only planning phase, rejects a caller-minted lead ID or
    prose receipt, and unlocks action only with a valid bound verification
    receipt; and
17. every pending/archived excerpt is preceded by the non-truncatable discovery
    warning and remains quoted evidence at non-instruction precedence; and
18. repository guidance outside the manifest is absent from `candidates` and,
    when returned, appears only in the non-authoritative
    `supplemental_guidance` lane, carries all false eligibility flags, omits all
    candidate, discovery, runbook, and authority identifiers, binds its distinct
    guidance digest to the immutable README excerpt, cannot satisfy breadth or
    unlock planning/action, and is warned and displayed only after corpus
    results; and
19. the published maximum batch fits a worst-case envelope with integrity,
    counters, and compact ACTIVE-plus-discovery breadth for every query, while
    `maximum + 1` is rejected atomically before immutable loading or retrieval
    without partial results.

For the four probes, acceptable direct matches include the named domain
documents in section 1 or a subsequently promoted replacement that demonstrably
owns the same procedure. Merely matching words such as `run`, `data`,
`restore`, or `two` is not a pass.

The independent benchmark MUST also cover concrete product and failure language
across AIM Data publishing, dataset-card responses, data-request validation,
SEO readiness/cache behavior, CRM briefings, support quarantine, Qdrant outbox
recovery, and account teardown. The existing process-heavy ACTIVE benchmark
remains a compatibility fixture; it is not sufficient acceptance evidence for
market findability.

## 9. Rollout order

This order supersedes any earlier sequence that postpones corpus discovery:

1. repair the structural build wrapper so verified builds are not discarded;
2. land immutable all-corpus search and the ranking correction;
3. wire zero-write, server-selected discovery into the first plan response;
4. retire caller-authored gate/debt/waiver writers;
5. establish backend write freezes and receipts after zero-writer evidence;
6. promote, merge, or archive the 81 pending documents in risk order; and
7. restore narrowly scoped enforcement only after measured search quality,
   immutable evidence, and non-vacuous validation are in production.

The immediate search release is reversible and grants no new authority. It
delivers the corpus as evidence leads while the slower truth-verification and
promotion program proceeds.
