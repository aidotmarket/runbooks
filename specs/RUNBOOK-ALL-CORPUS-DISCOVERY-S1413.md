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

For one lowercase full 40-character search SHA, the loader MUST:

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

`inventory_sha` means the lowercase full 40-character commit recorded at
`inventory.inventory_sha` in `CORPUS-MANIFEST.yaml`. It is the commit that froze
the exhaustive inventory; it is not the search SHA, the manifest digest, or a
working-tree state. With Git replacement objects disabled, the loader MUST
require `inventory.base_sha` and `inventory.inventory_sha` to each match
`[0-9a-f]{40}` and resolve to a commit, `inventory.base_sha` to be an ancestor
of `inventory.inventory_sha`, and `inventory.inventory_sha` to be an ancestor
of or equal to the immutable search SHA. For each record, define
`effective_inventory_path` as `inventory_path` when present and `path`
otherwise. At `inventory_sha`, every `effective_inventory_path` MUST resolve to
the declared regular-file blob. At the search SHA, every current `path` MUST
resolve to that same declared blob. A response MUST bind these as distinct
identities: the search/catalog SHA, manifest SHA-256, inventory SHA, and source
blob OID.

The current release has these binding, reviewed resource constants; they MUST
NOT be silently configurable:

- pinned manifest blob: at most 2,000,000 bytes;
- each pinned corpus document blob: at most 2,000,000 bytes;
- aggregate pinned corpus input: at most 64,000,000 bytes;
- each manifest `path` and `effective_inventory_path`: at most 512 UTF-8 bytes;
- manifest batch identifier: at most 128 UTF-8 bytes and at most 128 bytes in
  its ASCII JSON-string payload;
- `verify_against`: 1 through 8 entries, each at most 512 UTF-8 bytes and 512
  ASCII JSON-wire bytes, with aggregates of at most 2,048 UTF-8 bytes and 1,024
  ASCII JSON-wire bytes;
- each query: at most 4,000 characters and at most 4,000 characters/bytes in
  its ASCII JSON-string payload;
- normal corpus excerpt: at most 2,400 JSON-wire characters;
- optional supplemental-guidance excerpt: at most 1,200 JSON-wire characters;
- complete serialized response: at most 40,000 UTF-8 bytes and at most 40,000
  characters; and
- published mandatory two-objective worst-case envelope: at most 32,000
  serialized bytes, preserving reserve below the 40,000-byte response ceiling.

Every ASCII JSON-wire measurement is the RFC 8259 ASCII-escaped string payload,
excluding its surrounding quotes, exactly matching
`json.dumps(value, ensure_ascii=True)[1:-1].encode("ascii")`. The complete
response and the 32,000-byte envelope MUST be measured with the exact production
serializer. Caller query and objective-batch limits MUST fail before any
immutable catalog, manifest, README, or document read. Git object sizes MUST be
preflighted before blob materialization. Malformed manifest content, including
an invalid manifest batch identifier, necessarily fails during parsing, before
indexing, retrieval, partial results, or state writes.

Aggregate corpus-byte, memory, preflight, and resource accounting MUST charge
each manifest record/path once, including when distinct paths legally declare
the same blob OID. Transport MAY materialize an OID once, but deduplication MUST
NOT reduce accounting or the searchable-record count: the paths remain
independently indexed and reported.

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

Supplemental guidance is state-neutral. Enabling, returning, dropping, or
disabling it MUST NOT change corpus relevance ranks, candidates, discovery
leads, statuses, the authoritative-gap result, or any ACTIVE, grandfathered, or
archived searched, qualifying, returned, omitted, eligible, or dropped-corpus
counter. It MUST NOT consume mandatory breadth. Only supplemental-specific
fields and deterministic whole-response size or cryptographic
delivery/integrity fields that bind the complete serialization may differ.

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
- a complete, verbatim, ordered projection of the manifest's `verify_against`
  list.

The archived lead has the same prohibitions and additionally MUST include:

- `candidate_kind: archived_discovery_lead`;
- `catalog_state: archived`; and
- `historical_only: true`.

Every returned discovery lead and every gateway warning MUST carry every
declared `verify_against` entry verbatim and in manifest order. Truncation,
omission, merge, paraphrase, or substitution is forbidden. If the complete list
cannot fit, the system MUST return a typed non-success and mint no usable lead
or receipt. For every returned lead, the gateway MUST derive exactly one stable
requirement record for each list element, never one combined record per
document. Each record MUST bind path, list ordinal, exact requirement-text
digest, manifest digest, source blob, excerpt, objective, session, and runbooks
SHA. Each element record MUST receive a separate server-validated outcome; one
result cannot satisfy multiple records. A requirement MAY have a bounded
evidence bundle, but the final receipt MUST enumerate every requirement and
outcome.

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

Subject tokens are searchable query tokens after removing stop words and a
committed, release-frozen generic-intent set. That set MUST include at least
`run`, `operate`, `repair`, `restore`, `verify`, and `debug`. Except for an
exact validated `path:` query, every query, phrase, structured-literal, and
token-threshold qualification MUST contain at least one non-generic subject
token. Thus a generic-only multi-token phrase or literal such as `run restore`
cannot qualify even when it appears verbatim. Intent evidence may act only as a
bounded tie-breaker after independent domain evidence qualifies a section.
Domain qualification MUST require one of: an exact safe `path:` query; a
multi-token exact phrase or structured literal that satisfies the non-generic
rule; or at least `max(2, ceil(0.4 * subject_query_token_count))` distinct
non-stop, non-generic subject tokens matched in path, title, heading, declared
topic/literal, or excerpt. The implementation MUST return an honest
no-relevant-result status when the domain threshold is not met.

Authority state MUST NOT boost or suppress relevance. Policy eligibility is
evaluated after retrieval.

## 6. Bounded delivery

The API accepts a batch of exactly one or two objectives and publishes
`maximum=2`. Allocation MUST:

1. reserve enough space to report integrity and omission counters honestly;
2. preserve bounded ACTIVE breadth;
3. return at least one qualifying discovery lead for each query that has one;
4. allocate remaining bytes by global relevance and query breadth before
   excerpt depth; and
5. truncate excerpts, never identity, authority labels, verification flags, or
   integrity evidence; and
6. never emit a response over 40,000 UTF-8 bytes or 40,000 characters under the
   exact production serializer. If mandatory identity, policy, integrity, or
   complete verification-projection fields cannot fit, return a typed
   non-success and mint no usable lead or receipt.

An over-bound source excerpt MUST be truncated deterministically to the longest
source-faithful prefix whose canonical ASCII JSON-wire payload is at or below
the applicable 2,400- or 1,200-character bound, with a truthful truncation
flag. It MUST NOT be padded, embellished, or rejected merely because no source
prefix lands on the exact byte boundary.

The mandatory two-objective worst-case proof MUST use the production serializer
and include per-objective integrity and counters plus, for each objective, one
compact ACTIVE identity and one compact discovery identity with maximum-size
mandatory verification metadata. That exact configured worst case MUST fit
within 32,000 serialized bytes. A synthetic one-byte-over construction MUST
fail the build/acceptance proof; it is not an API input rejection. Optional
supplemental guidance MUST NOT consume mandatory corpus breadth. Exactly three
objectives MUST be rejected atomically before catalog, manifest, README, or
document loading, retrieval, partial results, or state writes. The
implementation MUST NOT shrink or partially execute a submitted batch, silently
violate per-objective breadth, drop policy labels, or emit an oversized
response.

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
`requires_ground_truth_verification`, and the complete `verify_against`
requirements. The excerpt is quoted evidence, not an executable instruction:
it MUST NOT be injected at system/developer precedence or automatically
translated into action steps. This ordering is required because pending
documents can contain destructive or internally contradictory procedures.

Selecting an ACTIVE candidate follows the authority policy in force for that
candidate. A grandfathered lead enters this server-bound handshake:

1. The first plan call returns `discovery_lead_id` plus structured verification
   requirements derived from the manifest and performs zero state writes. Every
   discovery lead and its gateway warning carries every declared
   `verify_against` entry verbatim and in order, without truncation, omission,
   merge, paraphrase, or substitution. If the full list cannot fit, the gateway
   returns a typed non-success and mints no usable lead or receipt. The session
   remains PLANNING.
2. While PLANNING, the gateway permits only bounded read-only inspection and
   production-safe verification tools needed by those requirements. It blocks
   builds, writes, deploys, and operational mutation.
3. A dedicated verification call accepts the server-issued lead ID and exact
   evidence receipts from trusted Git, schema, test, health, or probe adapters.
   Free-text claims, paths, reviewer names, and caller-authored attestations are
   not evidence.
4. For every returned lead, the gateway derives exactly one stable requirement
   record for each declared `verify_against` list element, not one combined
   record per document. Each record is bound to path, list ordinal, exact
   requirement-text digest, manifest digest, source blob, excerpt, objective,
   session, and runbooks SHA. Verification yields one separately
   server-validated outcome for every element record; one result cannot satisfy
   multiple requirements. A requirement may carry a bounded evidence bundle,
   but the final receipt enumerates every requirement and its outcome.
5. The server validates binding, freshness, remote object identity, and the
   requirement-specific evidence. It returns a signed
   `discovery_verification_receipt_id` with outcome
   `confirmed_for_objective`, `contradicted`, or `insufficient`.
6. A second plan call may transition to OPERATIONAL only with a fresh
   `confirmed_for_objective` receipt bound to the same session, objective,
   runbooks SHA, blob, and excerpt. The receipt authorizes reliance only for
   that objective; it does not promote the document or grant general authority.

`confirmed_for_objective` is permitted only when every projected requirement
has fresh, sufficient, trusted evidence and none is missing, stale, duplicated,
caller-substituted, contradicted, or insufficient. Otherwise the session MUST
remain read-only and MUST NOT unlock OPERATIONAL.

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

The implementation fixture is distinct from independent acceptance evidence.
The committed `tests/fixtures/catalog/discovery_benchmark.yaml` MUST contain at
least 12 unique cases. Each case MUST have a stable unique ID, market-area
label, exact query, machine-readable expected current path or accepted-path
set, expected policy class, historical-path exclusions where applicable, and
an evaluation-split/provenance label. It MUST cover the four baseline probes
plus AIM Data publishing, dataset-card responses, data-request validation, SEO
readiness/cache behavior, CRM briefings, support quarantine, Qdrant outbox
recovery, and account teardown. Every required current path MUST rank in the
global top three; generic/title-only or archived results cannot satisfy a
current label.

Every benchmark report MUST bind the exact implementation commit, fixture path,
replacement-disabled Git blob OID, and recomputed fixture SHA-256. Automated
tests and author prose are regression evidence only. Acceptance additionally
requires authenticated independent-review evidence from a reviewer who
authored neither the implementation nor the fixture. That evidence MUST bind
the same implementation SHA and fixture blob OID/SHA-256, reviewer/task
identity, raw verdict, and measured per-case results.

The independent evidence MUST also include a separately digested,
independently authored held-out evaluation set that was not used to tune
ranking before the implementation SHA froze. Before execution, it MUST have a
fixed authenticated digest and immutable expected paths, policy classes, and
exclusions. It MUST contain at least 8 unique cases across at least 6 market
areas and have no exact query overlap with the committed fixture. Every held-out
per-case top-three, policy-class, and exclusion result MUST be bound to the
implementation and evaluator receipt; labels cannot change after results are
viewed.

Implementation is not complete until the following are proved at a committed
snapshot:

1. exactly 102 records participate: 20 ACTIVE, 81 grandfathered, 1 archived;
2. every source blob and inventory identity is verified and a mismatch fails
   closed; a fixture with two distinct manifest paths sharing one OID keeps two
   searchable records and, with an aggregate limit strictly between the
   one-copy and two-copy charge, loading fails because the blob size is charged
   once per path;
3. a dirty checkout and Git replacement refs cannot change results;
4. catalog/manifest ACTIVE-set drift fails closed;
5. an ACTIVE and grandfathered mixed query returns both policy classes;
6. a grandfathered-only hit is a discovery result, not `no_entry_found`;
7. an archived hit is visibly `historical_only`;
8. non-ACTIVE results cannot pass consultation or action-authority validation;
9. batched results are deterministic, and numeric-boundary fixtures accept the
   exact limit and reject
   limit plus one for every rejectable caller field; every raw UTF-8 and ASCII
   JSON-wire manifest field limit; `verify_against` count and aggregate limits;
   pinned manifest and document Git-object limits; and aggregate corpus input.
   Caller failures precede immutable reads, object sizes are rejected before
   materialization, and malformed manifest data fails during parsing before
   indexing, retrieval, partial results, or state writes. Over-bound excerpts
   become the longest source-faithful canonical JSON-wire prefix at or below
   their bound with a truthful truncation flag and no padding, embellishment, or
   exact-boundary rejection. The production serializer never emits over 40,000
   bytes or characters and returns typed non-success if mandatory fields cannot
   fit. The exact mandatory worst case fits 32,000 serialized bytes, while a
   synthetic one-byte-over construction fails the proof rather than masquerading
   as an API input rejection;
10. each of `run`, `operate`, `repair`, `restore`, `verify`, and `debug` alone,
    and multiple generic-only exact phrase and structured-literal combinations,
    produce an honest miss despite verbatim text; only an exact validated
    `path:` query is exempt, and generic intent is merely a bounded tie-breaker
    after independent non-generic domain qualification;
11. the four probes in section 1 each return a directly relevant document in
    the first three globally ordered results;
12. the committed benchmark has the required identity, labels, coverage, and
    per-case results, and authenticated independent review also executes the
    fixed held-out set. Only a raw `PASS` or `APPROVE` for which every expected
    fixture and held-out top-three, policy-class, and exclusion result succeeds
    can satisfy this clause. `REJECT`, `REVISE`, `ERROR`, partial, missing,
    mixed, self-authored, unbound, or prose-only evidence cannot satisfy it;
13. the first-plan gateway response includes pinned excerpts and performs zero
    state writes;
14. grouped exact `path:` probes prove that every one of the 102 manifest
    records contributes at least one searchable unit and is retrievable,
    including the H1-only `session-lifecycle.md`, with the archived record
    labeled historical;
15. changing only state and catalog-only metadata leaves common relevance
    scores and order unchanged;
16. a grandfathered-only objective returns a lead and authoritative-gap label,
    remains read-only, and rejects a caller-minted lead ID or prose receipt.
    Tests prove the complete ordered projection and exactly one stable record
    and separate server outcome per `verify_against` element; missing one,
    truncating the list, reusing one result for multiple elements, or
    substituting caller prose cannot mint a usable lead/receipt or unlock
    action. Only a valid bound receipt with fresh, sufficient, trusted evidence
    for every requirement permits `confirmed_for_objective`;
17. every pending/archived excerpt is preceded by the non-truncatable discovery
    warning and remains quoted evidence at non-instruction precedence;
18. repository guidance outside the manifest is absent from `candidates` and,
    when returned, appears only in the non-authoritative
    `supplemental_guidance` lane, carries all false eligibility flags, omits all
    candidate, discovery, runbook, and authority identifiers, binds its distinct
    guidance digest to the immutable README excerpt, cannot satisfy breadth or
    unlock planning/action, and is warned and displayed only after corpus
    results. On the same snapshot and query, enabled-versus-disabled results
    MUST be identical for corpus results, corpus counters, rankings, statuses,
    and corpus-bound digests after excluding only the supplemental lane and
    derived whole-response size/digest fields;
19. the published maximum is exactly 2: one and two objectives are accepted,
    and the production-serialized two-objective worst case proves per-objective
    integrity/counters plus compact ACTIVE-and-discovery breadth with
    maximum-size mandatory verification metadata fit within 32,000 bytes.
    Exactly three objectives are rejected atomically before catalog, manifest,
    README, or document loading, retrieval, partial results, or state writes.

For the four probes, acceptable direct matches include the named domain
documents in section 1 or a subsequently promoted replacement that demonstrably
owns the same procedure. Merely matching words such as `run`, `data`,
`restore`, or `two` is not a pass.

The existing process-heavy ACTIVE benchmark remains a compatibility fixture;
it is not sufficient acceptance evidence for market findability.

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
