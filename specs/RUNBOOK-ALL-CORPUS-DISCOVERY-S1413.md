# S1413 — All-corpus runbook discovery before authority promotion

Status: **BINDING IMPLEMENTATION CONTRACT — REVISION 3**

Date: 2026-08-02

Repository baseline: `73ae00e4ae6760e40e00e6cea585d4b6d4399fac`

Revision history:

- Revision 2 was published at `6549cf5a68de351529f5708ba6fd6389efdcce15`.
- The controlling independent CC review `6aeccda7` returned raw verdict
  **REVISE**. A secondary wrapper's `APPROVED_WITH_MANDATES` label did not
  change that verdict. Gate 1 therefore entered `REQUEST_CHANGES`.
- AG review `a5c8f292` returned `APPROVE_WITH_NITS`; its max=2 nit is folded
  below. DeepSeek did not participate because its provider key was absent.
  GLM's initial request and sole retry produced no verdict. Neither is review
  evidence.
- Revision 3 folds the binding mandates without claiming implementation,
  benchmark acceptance, gateway delivery, activation, or approval.

This contract amends `specs/RUNBOOK-ORGANIZATION-PLAN-S1387.md`. Where that
plan delays discovery until documents are promoted, or makes grandfathered
documents reachable only by explicit path, this contract supersedes it for
retrieval. It does not create a second authority set. Only ACTIVE entries in
`CATALOG.json` may be authority candidates. Pending and archived documents are
labeled evidence leads and never gain operating authority merely by retrieval.

## 1. Baseline and binding outcome

At the baseline, `CORPUS-MANIFEST.yaml` contains exactly 102 operational
records: 20 ACTIVE, 81 `pending_verification`, and 1 archived. Every record has
a pinned Git blob OID, and the ACTIVE manifest paths equal the 20 catalog paths.
The complete 20/81/1 separation is binding.

Current ACTIVE-only search misses the intended operational material for these
representative market-work probes:

1. `deploy backend and run a database schema migration`
2. `publish a seller dataset through AIM Data`
3. `restore Qdrant after data loss`
4. `debug signup and two-factor authentication`

The excluded corpus contains directly relevant documents such as
`ai-market-backend.md`, `aim-data-seller-publish-journey.md`, `qdrant.md`,
`backup-and-recovery.md`, `auth-signup-flow.md`, and `two-factor-auth.md`.
The current ranker also lets generic intent words dominate domain evidence.

One search at one immutable runbooks commit MUST inspect all manifest records,
rank ACTIVE and discovery material in one state-neutral global order, and then
separate delivery into policy lanes:

- `candidates` contains only ACTIVE catalog results;
- `discovery_leads` contains pending and archived results; and
- `supplemental_guidance` may contain bounded repository guidance, but is not
  corpus, authority, or benchmark material.

A relevant pending document MUST be findable before rewrite or promotion.
Promotion remains a separate evidence-bound operation.

## 2. Immutable corpus, history, validation stages, and refresh

The canonical search service and acceptance harness MUST possess the complete
commit graph and objects needed to resolve the base, inventory, activation, and
search commits and to check ancestry, with Git replacement objects disabled.
They MUST load `CATALOG.json`, `CORPUS-MANIFEST.yaml`, and document blobs from
Git objects, never from a mutable checkout. A shallow, missing, grafted, or
rewritten graph returns typed `corpus_history_unavailable`; it never falls back
to a checkout. The operator remedy is to fetch the exact full-history objects,
verify their remote identities, and retry the same immutable SHA.

For one lowercase full 40-hex search SHA, the loader MUST:

1. disable Git replacement objects for every object and ancestry operation;
2. resolve the search SHA and load catalog and manifest from it;
3. parse YAML syntax, then validate the well-formed manifest before indexing;
4. require the manifest ACTIVE path set to equal the catalog path set;
5. require `inventory.base_sha` and `inventory.inventory_sha` to be full
   lowercase commit SHAs, base to be an ancestor of inventory, and inventory
   to be an ancestor of or equal to the search SHA;
6. define `effective_inventory_path` as `inventory_path` when present and
   `path` otherwise, and enforce the reviewed 192 UTF-8-byte portable-path
   limit on both;
7. resolve every effective path at the inventory SHA and every current path at
   the search SHA as the same declared regular-file blob;
8. preflight object sizes, then recompute every `git_blob_oid`;
9. reject missing objects, path/state/identity mismatch, duplicate paths,
   unsupported modes, invalid ancestry, malformed fields, or blob mismatch;
10. charge each record/path independently, including duplicate OIDs; and
11. emit at least one searchable unit per record. When no body section
    qualifies, emit a document unit from path and H1/title. H1-only
    `session-lifecycle.md` therefore remains retrievable.

Failure stages are normative. YAML syntax failures return typed
`manifest_parse_failed` during parse. Well-formed size, count, identity, mode,
OID, ancestry, and schema violations return their typed validation error after
parse and before indexing, retrieval, partial results, or state writes. Caller
batch/query failures occur before catalog, manifest, README, or document reads.
Git object sizes are rejected before materialization. No validation error may
be reported as a successful empty search.

`inventory_sha` is the immutable content snapshot named by
`inventory.inventory_sha`; it is distinct from the search/catalog SHA and the
manifest digest. Responses bind all of: exact search/catalog SHA, manifest
SHA-256, inventory SHA, and source blob OID.

Inventory refresh is mandatory after every document content or path-set
change, promotion, merge, archive, move, or addition:

- For a content or path-set change, first create an unactivated and unpinned
  content snapshot commit C containing the final document set. Then create an
  activation commit M whose `inventory_sha=C`, whose records bind every path
  and blob at C, and for which C is an ancestor of M. Pushing M necessarily
  publishes C; C MUST NOT be called unpublished. M changes only the manifest
  plus corresponding catalog/generated identity metadata required for
  activation and contains no document-content change.
- For a pure catalog/manifest promotion or archive with an identical document
  tree, C MAY be the previously validated immutable content snapshot. No empty
  content commit is required. M is the sole new activation-metadata commit.
- Validate M completely, verify exact remote objects and the expected old pin,
  then move the deployed pin from old-M to new-M by atomic compare-and-swap.
  Never activate C. CAS loss, a failed or stale M, or remote-object mismatch
  leaves old-M serving.
- A stale record returns typed `corpus_inventory_stale`, names every changed
  path within the bounded error schema, states the refresh obligation, and
  searches no partial new snapshot.

## 3. Binding measures and frozen resource accounting

`canonical_string_bytes(value)` means the RFC-8259 ASCII JSON-string payload
excluding quotes, exactly
`json.dumps(value, ensure_ascii=True)[1:-1].encode("ascii")`. Batch IDs,
queries, every `verify_against` prose element and its aggregate, excerpts, and
supplemental text use this measure. Git/manifest/document/aggregate objects use
bytes. Paths and effective paths use UTF-8 bytes. Complete responses use the
UTF-8 byte length of the exact production serialization. A portable Git path
contains only `[A-Za-z0-9._/-]`, has no leading slash, empty component, `.` or
`..` component, or trailing slash, and is therefore byte-identical under UTF-8
and the production JSON string encoding.

The following production constants are reviewed, frozen, and non-configurable:

| Resource | Binding production limit |
|---|---:|
| pinned manifest blob | 2,000,000 bytes |
| each pinned corpus document blob | 2,000,000 bytes |
| aggregate pinned corpus input, charged once per record/path | 64,000,000 bytes |
| `path`, `effective_inventory_path` | 192 UTF-8 bytes each; portable ASCII Git-path alphabet |
| manifest batch ID | 128 canonical string bytes |
| objective query | 4,000 canonical string bytes |
| `verify_against` | 1..8 items; 512 canonical string bytes each; 1,024 aggregate |
| normal corpus excerpt | 2,400 canonical string bytes per item |
| initial mandatory corpus excerpt | min(full source, 600 canonical string bytes) |
| supplemental excerpt | 1,200 canonical string bytes |
| exact production response | 40,000 UTF-8 bytes including final newline |
| production two-objective worst-case proof | at most 32,000 UTF-8 bytes |

There is no separate character ceiling and no 2,048 raw-byte
`verify_against` boundary. Optional early raw checks may reject only values
that necessarily violate a binding limit; they are not acceptance boundaries.
Exact-limit and limit-plus-one tests target each binding measure and failure
stage once.

Aggregate resource accounting MUST charge each manifest record/path once even
when two paths legally name the same OID. Transport may materialize one OID
once, but deduplication MUST NOT lower accounting or searchable-record counts.

Production entrypoints MUST construct and assert one frozen limits singleton.
No environment variable, CLI flag, request, config file, plugin, manifest, or
caller value may alter it. Implementation MAY expose a private pure
resource-accounting/serializer harness with an explicit immutable limits object
only to committed unit and build-proof tests. Every production entrypoint MUST
refuse a non-default object. Tests use the seam for duplicate-OID one-versus-two
copy charging, exact object/aggregate boundaries, mandatory-fields-do-not-fit,
and a synthetic 32,001-byte fault without giant fixtures. These are build/fault
proofs, not API rejection boundaries. The real production two-objective proof
uses the frozen singleton and remains separate.

## 4. Retrieval, qualification, and global ordering

All corpus states use the same state-neutral feature projection: normalized
path basename/stem, document H1/title, Markdown heading, document/section text,
and structured literals present in that document text. Catalog-only aliases,
topics, declarations, owner, verification date, risk, status, and promotion
metadata MUST NOT qualify or rank a global result. They may retain a bounded
legacy ACTIVE score only for compatibility.

Generic intent tokens include at least `run`, `operate`, `repair`, `restore`,
`verify`, and `debug`. Every generic token alone and every generic-only phrase
or structured literal is an honest miss. Generic intent is only a bounded
tie-breaker after independent domain qualification.

Subject tokens are normalized query tokens after stop-word and frozen-generic
removal. Qualification is exactly one of:

- an exact validated `path:` query;
- an exact multi-token phrase or document structured literal containing at
  least one non-generic subject token;
- at least `max(2, ceil(0.4 * subject_query_token_count))` distinct subject
  tokens matched in the state-neutral projection; or
- the single-strong-token route below.

Exactly one non-generic normalized subject token may qualify only by exact
token equality in normalized path basename/stem, H1, or title. Substrings,
arbitrary body text, headings below H1, catalog-only metadata, and intent tokens
do not qualify this route. A single token with multiple qualifying paths
remains ambiguous and is globally ranked; it is not promoted to an exact-path
lookup. `qdrant` or `sysadmin` is the intended class of strong domain query.

Every qualifying corpus result receives a state-neutral `relevance_rank`.
Ordering is deterministic by common score and immutable tie-break identities;
catalog state and authority eligibility never boost or suppress it. Changing
only state or catalog metadata cannot change scores, ranks, or qualification.

For each objective, deliver all qualifying globally ordered corpus results
through rank 3, or all when fewer than three qualify. If both ACTIVE and
discovery classes qualify and one class is absent from ranks 1..3, also deliver
the highest-ranked result of the missing class without changing any global
rank. Mandatory delivery is therefore at most four corpus results per
objective. The first `min(3, qualifying_count)` global results are exactly the
top-three benchmark projection. Supplemental guidance never counts.

## 5. Authority separation and verification semantics

ACTIVE sections remain the only authority candidates. Their authority policy
is evaluated after retrieval. A pending result is a
`grandfathered_discovery_lead`; an archived result is an
`archived_discovery_lead` with `historical_only=true`. Neither may mint or
satisfy a consultation candidate ID, unlock planning or action, discharge
runbook debt, prove a procedure true, create a waiver, or be auto-promoted.

Section evidence uses real heading, section, and line fields. Document evidence
uses `unit_kind=document` plus the document title identity and MUST omit, not
fabricate, every section/heading/line field marked section-only in section 6.

Each discovery lead carries the exact non-truncatable warning
`DISCOVERY ONLY — NOT VERIFIED OPERATING AUTHORITY`, its manifest risk and
batch, and the complete ordered `verify_against` projection. The warning
precedes quoted document text at non-instruction precedence.

Free prose is preserved verbatim, ordered, and one-to-one but is not executable
verification. Manifest schema version 2 MUST author and review a structured
mapping for each prose ordinal. Each immutable `verification_requirement`
binds schema version, ordinal, exact prose and digest, mapping digest,
server-owned adapter type, typed adapter parameters, and evidence policy.
Mappings are manifest data; agents and callers do not infer or author them at
delivery time.

The release-frozen adapter allowlist is:

- `git_object_v1`: exact repository, commit, path, and expected object digest;
- `json_schema_v1`: exact repository, commit, path, JSON pointer, and expected
  value digest;
- `health_probe_v1`: registered service and probe IDs plus maximum evidence age;
- `test_result_v1`: repository, commit, registered test ID, and report digest;
- `state_read_v1`: registered namespace, entity key, field path, and expected
  value digest;
- `production_probe_v1`: registered service and production-safe probe ID plus
  maximum evidence age; and
- `unmapped_prose`: no parameters and a forced `insufficient` outcome.

An absent mapping projects to `unmapped_prose`. An unknown adapter, wrong
parameter shape, substituted parameter, or mapping-digest mismatch fails
manifest validation. `unmapped_prose` never contributes to
`confirmed_for_objective`; an action relying on that lead stays read-only.
This does not veto a separately selected ACTIVE candidate that passes existing
authority policy without relying on the unmapped lead. No human-judgement shim,
reviewer name, attestation, caller prose, or free-form evidence may manufacture
a mapping. Future mappings require immutable manifest/schema review and remain
one-to-one and digest-bound.

The gateway handshake remains server-bound:

1. The first plan search returns server-selected results and performs zero
   state writes. A discovery result receives an authenticated
   `discovery_lead_id` bound to session, objective digest, runbooks SHA,
   manifest digest, blob, excerpt digest, and expiry.
2. While a selected discovery lead is unconfirmed, the session permits only
   bounded read-only inspection and registered production-safe verification.
3. A dedicated call accepts the lead ID and adapter receipts. It validates
   exact requirement bindings, freshness, remote identity, evidence policy,
   and one distinct result per requirement.
4. It returns a signed `discovery_verification_receipt_id` with outcome
   `confirmed_for_objective`, `contradicted`, or `insufficient`.
5. Confirmation requires fresh sufficient trusted evidence for every mapped
   requirement, no unmapped item, and no missing, stale, reused, substituted,
   contradicted, or insufficient outcome. The receipt is usable only for its
   bound session, objective, snapshot, blob, and excerpt.

Archived leads can never be confirmed as current instructions. Contradicted or
insufficient leads expose the authoritative gap and remain read-only.

## 6. Normative production gateway wire schema and maxima

This section is the production contract, not an implementation note. The exact
serializer is `json.dumps(envelope, ensure_ascii=True, sort_keys=True,
separators=(",", ":")) + "\n"`. Objects are closed: a field not listed below
is forbidden. There are no wildcard rows, caller-provided maps, or unbounded
strings/lists. `J` means canonical string bytes from section 3; `U` means total
UTF-8 bytes in the exact serializer. Integers are canonical non-negative JSON
integers with no leading zeros. Fixed enums are serialized exactly as listed.

Digest bindings are:

- `delivery_digest`: SHA-256 of the final wire envelope with that value replaced
  by 64 ASCII zeroes;
- `corpus_projection_digest`: SHA-256 of the finalized corpus-only objective
  projection, excluding supplemental guidance and whole-response size/digest;
- `objective_digest`: SHA-256 of the versioned normalized objective;
- `candidate_digest`, `discovery_digest`, `guidance_digest`, warning IDs,
  requirement IDs, and mapping digests: domain-separated SHA-256 over every
  identity named for that object in this contract; and
- all `*_sha256` fields: lowercase 64-hex SHA-256 of the exact named bytes.

### 6.1 Envelope and objective fields

| Literal field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Bound by | Production source of truth |
|---|---|---:|---|---|---|---|
| `schema_version` | integer `3` | 1 digit | mandatory once | no | delivery | frozen gateway schema |
| `catalog_sha` | lowercase hex string | 40 J | mandatory once | no | delivery + corpus | resolved immutable search commit |
| `manifest_sha256` | lowercase hex string | 64 J | mandatory once | no | delivery + corpus | manifest blob bytes |
| `inventory_sha` | lowercase hex string | 40 J | mandatory once | no | delivery + corpus | validated manifest inventory |
| `results` | array of objective objects | 1..2 items | mandatory once | no | delivery + corpus | validated request order |
| `searched_entry_count` | integer 0..102 | 3 digits | mandatory once | no | delivery + corpus | validated snapshot |
| `searched_section_count` | integer 0..999999 | 6 digits | mandatory once | no | delivery + corpus | emitted searchable units |
| `complete` | boolean, always true on success | 4 bytes | mandatory once | no | delivery + corpus | allocator |
| `response_budget_bytes` | integer `40000` | 5 digits | mandatory once | no | delivery | frozen limits singleton |
| `response_budget_truncated` | boolean | 5 bytes | mandatory once | no | delivery + corpus | corpus allocator only |
| `dropped_candidate_count` | integer 0..8 | 1 digit | mandatory once; deprecated compatibility counter | no | delivery + corpus | sum of omitted corpus results |
| `serialized_bytes` | integer 0..40000 | 5 digits | mandatory once | no | delivery | exact final wire |
| `delivery_digest` | lowercase hex string | 64 J | mandatory once | no | self rule above | exact final wire |

| Literal objective field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Bound by | Production source of truth |
|---|---|---:|---|---|---|---|
| `objective_ordinal` | integer 1..2 | 1 digit | mandatory once/objective | no | delivery + corpus | request order |
| `objective_digest` | lowercase hex string | 64 J | mandatory once/objective | no | delivery + corpus | normalized objective |
| `status` | enum: `candidates_returned_unverified`, `no_positive_candidate_in_active_catalog`, `no_usable_corpus_result_response_budget`, `no_relevant_result` | 44 J | mandatory once/objective | no | delivery + corpus | authority policy + allocator |
| `discovery_status` | enum: `discovery_leads_returned_unverified`, `no_qualifying_discovery_lead` | 37 J | mandatory once/objective | no | delivery + corpus | discovery lane |
| `authoritative_gap` | boolean | 5 bytes | mandatory once/objective | no | delivery + corpus | ACTIVE/discovery qualification |
| `qualifying_result_count` | integer 0..999999 | 6 digits | mandatory once/objective | no | delivery + corpus | ranker |
| `eligible_candidate_count` | integer 0..999999 | 6 digits | mandatory once/objective | no | delivery + corpus | ACTIVE policy evaluator |
| `eligible_candidates_returned` | integer 0..4 | 1 digit | mandatory once/objective | no | delivery + corpus | allocator |
| `eligible_candidates_omitted_by_limit` | integer 0..999999 | 6 digits | mandatory once/objective | no | delivery + corpus | allocator |
| `eligible_candidates_omitted_by_response_budget` | integer 0..999999 | 6 digits | mandatory once/objective | no | delivery + corpus | allocator |
| `active_searched_count` | integer 0..20 | 2 digits | mandatory once/objective | no | delivery + corpus | snapshot/ranker |
| `active_qualifying_count` | integer 0..999999 | 6 digits | mandatory once/objective | no | delivery + corpus | ranker |
| `active_returned_count` | integer 0..4 | 1 digit | mandatory once/objective | no | delivery + corpus | allocator |
| `active_omitted_count` | integer 0..999999 | 6 digits | mandatory once/objective | no | delivery + corpus | allocator |
| `grandfathered_searched_count` | integer 0..81 | 2 digits | mandatory once/objective | no | delivery + corpus | snapshot/ranker |
| `grandfathered_qualifying_count` | integer 0..999999 | 6 digits | mandatory once/objective | no | delivery + corpus | ranker |
| `grandfathered_returned_count` | integer 0..4 | 1 digit | mandatory once/objective | no | delivery + corpus | allocator |
| `grandfathered_omitted_count` | integer 0..999999 | 6 digits | mandatory once/objective | no | delivery + corpus | allocator |
| `archived_searched_count` | integer 0..1 | 1 digit | mandatory once/objective | no | delivery + corpus | snapshot/ranker |
| `archived_qualifying_count` | integer 0..999999 | 6 digits | mandatory once/objective | no | delivery + corpus | ranker |
| `archived_returned_count` | integer 0..1 | 1 digit | mandatory once/objective | no | delivery + corpus | allocator |
| `archived_omitted_count` | integer 0..999999 | 6 digits | mandatory once/objective | no | delivery + corpus | allocator |
| `candidates` | array of ACTIVE result objects | 0..4 items | mandatory once/objective | items no | delivery + corpus | global results filtered ACTIVE |
| `discovery_leads` | array of discovery result objects | 0..4 items | mandatory once/objective | items no | delivery + corpus | global results filtered non-ACTIVE |
| `supplemental_guidance` | array of supplemental objects | 0..1 item | mandatory once/objective | whole item may be omitted | delivery only | residual allocator |
| `supplemental_guidance_returned` | boolean | 5 bytes | mandatory once/objective | no | delivery only | residual allocator |
| `supplemental_guidance_omitted_by_response_budget` | boolean | 5 bytes | mandatory once/objective | no | delivery only | residual allocator |
| `corpus_projection_digest` | lowercase hex string | 64 J | mandatory once/objective | no | delivery + corpus | frozen corpus serialization |

The two lane arrays have a joint maximum of four corpus results per objective;
neither array's individual maximum permits more than four in their union. The
validated request `query` is deliberately not echoed by the final gateway; its
4,000-J input boundary is enforced before reads and `objective_digest` is the
wire identity.

### 6.2 Common corpus result and evidence fields

Every corpus result has the following closed common object. Section-only fields
are all present for `unit_kind=section` and all absent for
`unit_kind=document`.

| Literal field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Bound by | Production source of truth |
|---|---|---:|---|---|---|---|
| `relevance_rank` | integer 1..999999 | 6 digits | mandatory once/result | no | result digest + corpus | state-neutral ranker |
| `path` | portable ASCII Git-path string | 192 UTF-8 bytes | mandatory once/result | no | result digest + corpus | validated manifest/catalog path |
| `candidate_kind` | enum: `active_catalog_section`, `active_catalog_document`, `grandfathered_discovery_lead`, `archived_discovery_lead` | 32 J | mandatory once/result | no | result digest + corpus | catalog/manifest state + unit |
| `catalog_state` | enum `ACTIVE`, `grandfathered`, `archived` | 13 J | mandatory once/result | no | result digest + corpus | validated catalog/manifest |
| `status` | enum `ACTIVE`, `pending_verification`, `archived` | 20 J | mandatory once/result | no | result digest + corpus | validated catalog/manifest |
| `action_authority_eligible` | boolean | 5 bytes | mandatory once/result | no | result digest + corpus | catalog policy; false for discovery |
| `authority_admission` | boolean | 5 bytes | mandatory once/result | no | result digest + corpus | catalog policy; false for discovery |
| `candidate_id_eligible` | boolean | 5 bytes | mandatory once/result | no | result digest + corpus | catalog policy; false for discovery |
| `catalog_declared` | boolean | 5 bytes | mandatory once/result | no | result digest + corpus | exact section declaration match |
| `declaration_kinds` | ordered unique enum array of `topic`, `error_signature` | 0..2 items; 31 U | mandatory once/result | no | result digest + corpus | catalog declarations |
| `integrity_only` | boolean | 5 bytes | mandatory once/result | no | result digest + corpus | catalog policy; true for discovery |
| `integrity_status` | enum `integrity_pass_unverified` | 27 J | mandatory once/result | no | result digest + corpus | immutable loader |
| `semantic_verification` | boolean | 5 bytes | mandatory once/result | no | result digest + corpus | catalog/verification policy |
| `unit_kind` | enum `section`, `document` | 8 J | mandatory once/result | no | result digest + corpus | parser |
| `document_title` | string | 160 J | mandatory once/result | longest source-faithful prefix allowed | result digest + corpus | exact H1/title |
| `document_title_sha256` | lowercase hex string | 64 J | mandatory once/result | no | result digest + corpus | full untruncated H1/title |
| `document_title_truncated` | boolean | 5 bytes | mandatory once/result | no | result digest + corpus | title bounding |
| `heading` | string | 160 J | section-only once | longest source-faithful prefix allowed | result digest + corpus | exact Markdown heading |
| `heading_sha256` | lowercase hex string | 64 J | section-only once | no | result digest + corpus | full heading |
| `heading_truncated` | boolean | 5 bytes | section-only once | no | result digest + corpus | heading bounding |
| `heading_line` | integer 1..999999 | 6 digits | section-only once | no | result digest + corpus | Markdown parser |
| `section_id` | string | 96 J | section-only once | deterministic prefix+digest allowed | result digest + corpus | catalog ID or frozen derivation |
| `section_id_source` | enum `catalog`, `legacy-derived` | 14 J | section-only once | no | result digest + corpus | catalog/parser |
| `excerpt_start_line` | integer 1..999999 | 6 digits | mandatory once/result | no | result digest + corpus | source line map |
| `excerpt_end_line` | integer 1..999999 | 6 digits | mandatory once/result | no | result digest + corpus | source line map |
| `excerpt_end_column_exclusive` | integer 1..999999 | 6 digits | mandatory once/result | no | result digest + corpus | source line map |
| `excerpt` | string | initial 600 J; residual growth to 2,400 J | mandatory once/result | source-faithful prefix only | excerpt digest + result + corpus | pinned source blob |
| `excerpt_sha256` | lowercase hex string | 64 J | mandatory once/result | no | result digest + corpus | delivered excerpt bytes |
| `excerpt_truncated` | boolean | 5 bytes | mandatory once/result | no | result digest + corpus | excerpt allocator |
| `match_evidence` | array of match-evidence objects | 0..4 items; 512 U aggregate | mandatory once/result | list may truncate only after qualification; flag per object | result digest + corpus | production scorer |
| `relevance_evidence` | array of enum `path`, `title`, `heading`, `phrase`, `structured_literal`, `token_threshold`, `single_strong_token` | 1..7 items; 128 U | mandatory once/result | no | result digest + corpus | state-neutral qualifier |
| `score` | JSON number 0..999999.999999, max 6 decimals | 13 bytes | mandatory once/result | no | result digest + corpus | common scorer |
| `catalog_sha` | lowercase hex string | 40 J | mandatory once/result | no | result digest + corpus | envelope search SHA |
| `manifest_sha256` | lowercase hex string | 64 J | mandatory once/result | no | result digest + corpus | envelope manifest digest |
| `inventory_sha` | lowercase hex string | 40 J | mandatory once/result | no | result digest + corpus | envelope inventory SHA |
| `source_blob_oid` | lowercase SHA-1 or SHA-256 hex | 64 J | mandatory once/result | no | result digest + corpus | validated Git object |

Each `match_evidence` object is closed and contains exactly: `kind` (enum
`path`, `title`, `heading`, `excerpt`, `structured_literal`, `intent`, or
`legacy_active`, max 18 J); `matched_tokens` (0..12 strings, each max 32 J and
256 J aggregate); `matched_tokens_truncated` (boolean); `value` (max 160 J,
source-faithful prefix truncation allowed); and `weight` (JSON number
0..9999.999999, max 11 bytes). It repeats at most four times and is bound by
the result digest and corpus projection.

### 6.3 ACTIVE-only fields

| Literal field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Bound by | Production source of truth |
|---|---|---:|---|---|---|---|
| `candidate_digest` | lowercase hex string | 64 J | mandatory once/ACTIVE result | no | domain-separated self digest + corpus | immutable ACTIVE identity |
| `runbook_id` | string | 96 J | mandatory once/ACTIVE result | no | candidate + corpus | validated catalog |
| `owner` | enum `vulcan`, `mars`, `kd`, `mp`, `max` | 6 J | mandatory once/ACTIVE result | no | candidate + corpus | validated catalog |
| `last_verified_at` | RFC-3339 full-date string | 10 J | mandatory once/ACTIVE result | no | candidate + corpus | validated catalog |
| `authority_keys` | ordered unique string array | 0..8; each 128 J; 512 J aggregate | mandatory once/ACTIVE result | entries/prefixes may truncate with flag | candidate + corpus | catalog declarations |
| `authority_keys_truncated` | boolean | 5 bytes | mandatory once/ACTIVE result | no | candidate + corpus | authority-key bounding |
| `rank` | integer 1..999999 or null | 6 digits | mandatory once/ACTIVE result; legacy within-lane rank | no | candidate + corpus | compatibility ranker |

ACTIVE results MUST omit all discovery-only fields.

### 6.4 Discovery warning, identity, and verification fields

Each discovery result contains exactly one nested `warning`; because the
warning is part of the lead object, its one canonical requirement projection
is carried by both the warning and lead without byte-duplicating prose.

| Literal field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Bound by | Production source of truth |
|---|---|---:|---|---|---|---|
| `discovery_digest` | lowercase hex string | 64 J | mandatory once/discovery | no | domain-separated self digest + corpus | immutable discovery identity |
| `discovery_lead_id` | authenticated string | 192 J | mandatory once/delivered discovery | no | server signature + corpus | gateway issuer |
| `requires_ground_truth_verification` | boolean, always true | 4 bytes | mandatory once/discovery | no | discovery + corpus | fixed policy |
| `historical_only` | boolean | 5 bytes | mandatory once/discovery | no | discovery + corpus | manifest state |
| `manifest_risk` | enum `P0`, `P1`, `P2`, `P3` | 2 J | mandatory once/discovery | no | discovery + corpus | manifest record |
| `manifest_batch` | string | 64 J | mandatory once/discovery | no | discovery + corpus | manifest record |
| `warning` | closed warning object below | 1 item | mandatory once/discovery | no | discovery + corpus | gateway policy renderer |

The warning object contains every listed field and no others:

| Literal warning field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Bound by | Production source of truth |
|---|---|---:|---|---|---|---|
| `warning_id` | lowercase hex string | 64 J | mandatory once/warning | no | warning self digest + corpus | gateway renderer |
| `code` | enum `DISCOVERY_ONLY_NOT_VERIFIED` | 27 J | mandatory once/warning | no | warning + corpus | fixed policy |
| `message` | exact `DISCOVERY ONLY — NOT VERIFIED OPERATING AUTHORITY` | 54 J | mandatory once/warning | no | warning + corpus | fixed policy |
| `catalog_state` | enum `grandfathered`, `archived` | 13 J | mandatory once/warning | no | warning + corpus | parent discovery result |
| `manifest_risk` | enum `P0`, `P1`, `P2`, `P3` | 2 J | mandatory once/warning | no | warning + corpus | manifest record |
| `requires_ground_truth_verification` | boolean true | 4 bytes | mandatory once/warning | no | warning + corpus | fixed policy |
| `verification_requirements` | ordered array of closed objects below | 1..8 items; 5,120 U aggregate | mandatory once/warning | no | warning + discovery + corpus | manifest mappings |

Every `verification_requirement` contains all fields below. The array preserves
the exact manifest order. Its prose aggregate is independently capped at 1,024
J, adapter-parameter aggregate at 1,280 U, evidence-policy aggregate at 768 U,
and whole requirement-array aggregate at 5,120 U per discovery result.

| Literal requirement field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Bound by | Production source of truth |
|---|---|---:|---|---|---|---|
| `schema_version` | integer `1` | 1 digit | mandatory once/requirement | no | requirement + mapping | frozen mapping schema |
| `ordinal` | integer 1..8 | 1 digit | mandatory once/requirement | no | requirement + mapping | manifest list position |
| `prose` | string | 512 J; 1,024 J array aggregate | mandatory once/requirement | no | prose digest + requirement | verbatim `verify_against` item |
| `prose_sha256` | lowercase hex string | 64 J | mandatory once/requirement | no | requirement + mapping | exact prose bytes |
| `requirement_id` | lowercase hex string | 64 J | mandatory once/requirement | no | self + warning + discovery | path/ordinal/prose/manifest/blob/objective/session/SHA |
| `mapping_digest` | lowercase hex string | 64 J | mandatory once/requirement | no | self + requirement | adapter type, params, policy, schema |
| `adapter_type` | frozen enum from section 5 | 19 J | mandatory once/requirement | no | mapping + requirement | reviewed manifest mapping |
| `adapter_parameters` | adapter-specific closed object | 640 U/item; 1,280 U array aggregate | mandatory once/requirement | no | mapping + requirement | reviewed manifest mapping |
| `evidence_policy` | closed object below | 256 U/item; 768 U array aggregate | mandatory once/requirement | no | mapping + requirement | reviewed manifest mapping |

Adapter parameter objects are closed by type:

| `adapter_type` | Exact literal parameter fields and maxima |
|---|---|
| `git_object_v1` | `repository` string <=64 J; `commit_sha` 40 J lowercase hex; `path` portable ASCII <=192 UTF-8 bytes; `expected_object_oid` 40 or 64 J lowercase hex |
| `json_schema_v1` | `repository` <=64 J; `commit_sha` 40 J; `path` portable ASCII <=192 UTF-8 bytes; `json_pointer` <=128 J; `expected_value_sha256` 64 J |
| `health_probe_v1` | `service_id` <=64 J; `probe_id` <=96 J; `max_age_seconds` integer 0..86400 |
| `test_result_v1` | `repository` <=64 J; `commit_sha` 40 J; `test_id` <=128 J; `report_sha256` 64 J |
| `state_read_v1` | `namespace` <=64 J; `entity_key` <=128 J; `field_path` <=128 J; `expected_value_sha256` 64 J |
| `production_probe_v1` | `service_id` <=64 J; `probe_id` <=96 J; `max_age_seconds` integer 0..86400 |
| `unmapped_prose` | no fields; exact object `{}` |

The 640-U per-item cap still applies; therefore a syntactically valid object
whose listed maxima combine above 640 U is rejected during manifest validation,
not truncated. The evidence-policy object contains exactly:
`minimum_receipts` (integer 1..4), `maximum_receipts` (integer 1..4 and not less
than minimum), `freshness_seconds` (integer 0..86400),
`allowed_evidence_kinds` (ordered unique array of 1..4 enums `git`, `schema`,
`health`, `test`, `state`, `probe`, 40 U aggregate),
`require_remote_identity` (boolean), and `require_distinct_sources` (boolean).

Discovery results MUST omit `candidate_digest`, `runbook_id`, `owner`,
`last_verified_at`, `authority_keys`, `authority_keys_truncated`, and `rank`.

### 6.5 Supplemental guidance fields and production exclusions

Supplemental guidance is one closed object:

| Literal field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Bound by | Production source of truth |
|---|---|---:|---|---|---|---|
| `candidate_kind` | exact `repository_authoring_guidance` | 29 J | mandatory once | no | guidance + delivery | fixed policy |
| `supplemental` | boolean true | 4 bytes | mandatory once | no | guidance + delivery | fixed policy |
| `candidate_id_eligible` | boolean false | 5 bytes | mandatory once | no | guidance + delivery | fixed policy |
| `action_authority_eligible` | boolean false | 5 bytes | mandatory once | no | guidance + delivery | fixed policy |
| `authority_admission` | boolean false | 5 bytes | mandatory once | no | guidance + delivery | fixed policy |
| `semantic_verification` | boolean false | 5 bytes | mandatory once | no | guidance + delivery | fixed policy |
| `path` | exact `README.md` | 9 J | mandatory once | no | guidance + delivery | immutable README |
| `catalog_sha` | lowercase hex string | 40 J | mandatory once | no | guidance + delivery | search SHA |
| `source_blob_oid` | lowercase Git OID | 64 J | mandatory once | no | guidance + delivery | immutable README blob |
| `excerpt` | string | 1,200 J | mandatory once | source-faithful prefix | excerpt + guidance + delivery | README section |
| `excerpt_sha256` | lowercase hex string | 64 J | mandatory once | no | guidance + delivery | delivered excerpt |
| `excerpt_truncated` | boolean | 5 bytes | mandatory once | no | guidance + delivery | residual allocator |
| `guidance_digest` | lowercase hex string | 64 J | mandatory once | no | self + delivery | SHA, README OID, excerpt digest |
| `warning_id` | lowercase hex string | 64 J | mandatory once | no | guidance + delivery | warning identity |
| `warning_code` | exact `SUPPLEMENTAL_GUIDANCE_NOT_AUTHORITY` | 35 J | mandatory once | no | guidance + delivery | fixed policy |
| `warning_message` | exact `SUPPLEMENTAL GUIDANCE — NOT RUNBOOK AUTHORITY` | 50 J | mandatory once | no | guidance + delivery | fixed policy |

The production gateway adapter MUST use an explicit closed allowlist and test
that these current library-fragment compatibility fields are not serialized in
the final gateway envelope: objective field `query`; repeated objective fields
`catalog_sha`, `searched_entry_count`, and `searched_section_count` (normalized
once to the envelope); and supplemental fields `candidate_digest`,
`discovery_digest`,
`discovery_lead_id`, `runbook_id`, `authority_keys`,
`authority_keys_truncated`, `owner`, `last_verified_at`, `rank`, `score`,
`section_id`, `section_id_source`, `heading`, `heading_line`,
`heading_sha256`, `heading_truncated`, `catalog_declared`,
`declaration_kinds`, `integrity_only`, `integrity_status`, and
`match_evidence`, `excerpt_start_line`, `excerpt_end_line`, and
`excerpt_end_column_exclusive`. The adapter proof serializes a library object containing
sentinel values for every excluded literal and asserts none reaches the final
gateway wire envelope. No generic passthrough is permitted.

### 6.6 Typed non-success envelope

A non-success serializes this separate closed envelope and no success-envelope
field, objective, warning, corpus result, excerpt, lead ID, or receipt. It is
also subject to the exact production serializer and delivery-digest rule.

| Literal field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Bound by | Production source of truth |
|---|---|---:|---|---|---|---|
| `schema_version` | integer `3` | 1 digit | mandatory once | no | delivery | frozen gateway schema |
| `status` | exact string `fail` | 4 J | mandatory once | no | delivery | gateway control path |
| `error_code` | enum `batch_size_invalid`, `query_limit_exceeded`, `manifest_parse_failed`, `manifest_validation_failed`, `corpus_history_unavailable`, `corpus_inventory_stale`, `mandatory_corpus_envelope_too_large`, `response_budget_exceeded`, `session_objective_budget_exceeded`, `session_wire_budget_exceeded`, `invalid_limits_override` | 36 J | mandatory once | no | delivery | typed failing stage |
| `message` | fixed server-owned message selected by error code | 256 J | mandatory once | no | delivery | frozen error catalog |
| `changed_paths` | ordered unique portable-path array | 0..102 items; 192 UTF-8 bytes/item; 20,000 U aggregate | mandatory only for `corpus_inventory_stale`; otherwise absent | no | delivery | immutable old/new inventory diff |
| `serialized_bytes` | integer 0..24000 | 5 digits | mandatory once | no | delivery | exact control wire |
| `delivery_digest` | lowercase hex string | 64 J | mandatory once | no | self rule in 6.0 | exact control wire |

The control envelope is at most 24,000 U and contains no caller prose. The
192-byte portable-path and 102-record bounds make the complete changed-path set
fit; the serializer never emits a partial path list or corpus result.

## 7. Deterministic allocation and strictly residual guidance

For one or two objectives, the allocator MUST first build and finalize the
entire corpus result exactly as if supplemental guidance were disabled. This
includes selected identities, global order, all policy/integrity/verification
fields, warnings, initial and residual excerpt depths, truncation flags,
counters, statuses, and every corpus-bound digest. That corpus serialization
then becomes immutable.

Every mandatory corpus result first receives the longest source-faithful prefix
that fits `min(full excerpt, 600 canonical string bytes)`. A shorter source is
returned in full. No mandatory result may be shortened below that allocation to
fit another field or guidance. After all at-most-eight mandatory batch results,
identities, warnings, verification projection, counters, and response bindings
fit, allocate remaining corpus headroom deterministically by objective order
and global relevance rank to grow excerpts, each at most 2,400 J. The 2,400-J
limit is only a per-item residual-growth cap. If mandatory fields and initial
excerpts do not fit, return typed `mandatory_corpus_envelope_too_large`, emit no
corpus text, and mint no usable ID or receipt.

Only after the corpus serialization and `corpus_projection_digest` are fixed
may the allocator attempt supplemental guidance in strictly residual response
headroom. Guidance is all-or-nothing with its warning and fields. If it does not
fit, omit it. It may never shorten or reallocate a corpus excerpt or change any
corpus identity, result, counter, digest, rank, status, or truncation flag. The
only allowed enabled/disabled differences outside the supplemental lane are
deterministic whole-response `serialized_bytes` and `delivery_digest`.

The exact production serializer MUST prove both maximum four-result shapes in
each objective position: 3 ACTIVE plus the highest-ranked missing discovery
class, and 1 ACTIVE plus 3 discovery results. The proof suite swaps the shapes
through both positions and includes the combined one-of-each maximum response.
All variable fields are set to the table maxima, all
warnings and verification metadata are complete, and every mandatory excerpt
receives 600 J. This must serialize at or below 32,000 U. If it cannot, only
repeated parent bindings may be normalized or reviewed field maxima tightened;
the 600-J allocation, top-three-plus-missing-class breadth, 40,000-U production
cap, and complete ordered verification projection MUST NOT be weakened.

## 8. Gateway batch and authenticated session bounds

The stateless library has no hidden session state and accepts exactly one or
two objectives. It publishes `maximum=2`. It rejects zero and every size above
two atomically before catalog, manifest, README, or document reads, retrieval,
partial results, or state writes. There is no shrink or partial execution.

The gateway independently enforces both current-release authenticated session
ceilings, whichever would be reached first:

- at most 8 distinct objective digests; and
- at most 120,000 actual serialized wire bytes delivered.

There is no response-count ceiling. Each delivery charges its actual wire
bytes. Exact same-session objective-digest replay consumes no new digest slot,
but returns either a compact cached receipt/reference of at most 1,024 wire
bytes and charges those bytes, or a full cached payload and charges the full
payload. There is no free full replay.

Before any corpus text is emitted, the gateway atomically reserves prospective
digest slots and delivery bytes or returns a bounded control error containing
no corpus result. Caller prose, batch splitting, compact versus full replay, or
new lead IDs cannot reset either ceiling. These ceilings are separate from the
library's batch=2 and per-response 40,000-U contract.

## 9. Gateway presentation and operating boundary

The first planning interaction for a session searches the complete pinned
corpus for every objective and delivers the globally ordered excerpts before
action. Caller-authored paths, sections, attestations, `no_entry_found` prose,
waivers, or lead IDs cannot substitute for server selection.

The gateway merges `candidates` and `discovery_leads` by `relevance_rank` for
display while preserving their separate policy lanes. Discovery warnings
precede their excerpts. Supplemental guidance, when present, displays after all
corpus results and at non-instruction precedence. The boot payload SHOULD expose
the exact pin and 20/81/1 counts but SHOULD NOT inline the corpus.

When pending material matches but ACTIVE material does not, `status` remains
`no_positive_candidate_in_active_catalog`, `discovery_status` is
`discovery_leads_returned_unverified`, and `authoritative_gap=true`.

## 10. Benchmark evidence

The committed fixture `tests/fixtures/catalog/discovery_benchmark.yaml` MUST
contain at least 12 unique cases with stable ID, taxonomy version and tuple,
market area, exact query, expected current path or accepted set, expected policy
class, historical exclusions where applicable, and split/provenance. It covers
the four baseline probes plus AIM Data publishing, dataset-card responses,
data-request validation, SEO readiness/cache behavior, CRM briefings, support
quarantine, Qdrant outbox recovery, and account teardown. Required current
paths must rank in the global top three; generic/title-only or archived results
cannot satisfy a current label.

Every report binds implementation commit, fixture path, replacement-disabled
fixture blob OID, recomputed SHA-256, and measured per-case wire results.
Implementation-authored tests and prose are regression evidence only.

Held-out acceptance requires three distinct authenticated identities:
implementation/fixture author, held-out-set author/custodian, and
evaluator/reviewer. No later than implementation-SHA freeze, an authenticated
append-only record registers the held-out set's exact sealed blob digest,
expected labels, exclusions, taxonomy version, every fixture and held-out
classification, and all anti-duplication checks. Contents stay sealed from the
implementation/fixture author until that SHA is immutable. The evaluator then
reveals and verifies the registered blob. No relabeling or replacement follows.

The frozen versioned semantic taxonomy contains at least market area,
resource, operation/failure intent, and expected policy/path. The set has at
least 8 cases across at least 6 market areas. A machine check rejects any case
whose semantic tuple and expected outcome equals a fixture; the distinct
evaluator also rejects materially equivalent paraphrases under that taxonomy.
Token Jaccard is additional lexical evidence, not the semantic test.

Every held-out case MUST pass all of:

- no `path:` query;
- the whole query is not an exact filename, basename, H1, or title;
- no exact normalized query overlap with a fixture;
- normalized non-generic-token Jaccard similarity with every fixture query is
  at most 0.5;
- no same expected-path/policy case formed only by adding or removing stop or
  generic tokens; and
- a declared, machine-checked difficulty class from the frozen taxonomy.

Across the set, at least four queries contain no exact expected basename/H1/
title token, at least two are ambiguous with at least two qualifying corpus
paths, and at least one is a strong single-token market-domain query. Benchmark
judgments grant no operating authority. Only complete authenticated raw
`PASS`/`APPROVE` evidence counts.

## 11. Acceptance clauses

Implementation is not accepted until all exactly nineteen clauses pass at one
committed snapshot:

1. **Corpus and policy split.** Exactly 102 records participate: 20 ACTIVE, 81
   grandfathered, and 1 archived. Every source and inventory identity verifies;
   ACTIVE alone can enter `candidates`; pending/archived results remain labeled,
   non-authoritative discovery.
2. **History, stages, and limits.** Complete replacement-disabled history
   resolves base/inventory/search ancestry. Shallow history, rewritten graph,
   missing commit/object, syntax-invalid YAML, and each well-formed limit,
   identity, mode, OID, ancestry, and schema violation return the correct typed
   error at the parse or validation stage before indexing, retrieval, partial
   output, or writes. Exact/+1 tests cover each binding measure once. The private
   harness proves manifest/document/aggregate boundaries and duplicate-OID
   between-one-and-two-copy charging without production overrides.
3. **Immutable loading and refresh.** Dirty checkout and replace refs cannot
   change results. Content-changing C→M refresh, metadata-only reuse of C,
   staged unactivated C, exact remote-object verification, and old-pin CAS are
   exercised; intermediate C is never activated or called unpublished.
4. **Fail-closed corpus coherence.** ACTIVE-set drift, stale records, changed
   path sets, blob mismatch, remote-object mismatch, CAS loss, and failed M leave
   old M serving. `corpus_inventory_stale` names changed paths and the refresh
   duty; no partial new snapshot is searched.
5. **Mixed policy query.** A qualifying mixed query returns ACTIVE and
   grandfathered classes in one unchanged global order, with all common and
   kind-specific immutable identities from the wire table.
6. **Discovery-only hit.** A grandfathered-only hit is a discovery result with
   authoritative gap, not `no_entry_found`, and cannot mint an ACTIVE candidate
   ID.
7. **Archive policy.** An archived hit is visibly `historical_only`, is warned,
   and cannot be confirmed as current instruction.
8. **Authority enforcement.** Non-ACTIVE results, supplemental guidance, caller
   paths/prose/IDs, attestations, and waivers cannot pass consultation or action
   authority validation, discharge debt, or promote content.
9. **Closed wire schema and allocator.** The final gateway envelope—not a
   library fragment—enumerates only section 6 fields, enforces every per-item,
   count, aggregate, path, heading, identifier, declaration, authority-key,
   match-evidence, warning, adapter, policy, counter, query, batch, object, and
   response maximum, and rejects unknown fields. Every production entrypoint
   constructs the frozen singleton, rejects a non-default limits object, and is
   proven unreachable from every environment, CLI, request, config, plugin, and
   caller override surface. Caller failures precede reads;
   object sizes fail before materialization; manifest validation follows parse.
   Excerpts are truthful canonical prefixes. Mandatory-fields-do-not-fit returns
   typed non-success. Production never exceeds 40,000 U; the real worst-case
   proof is <=32,000 U and the private 32,001-U fault fails as build proof.
10. **Generic and single-token qualification.** Each frozen generic token alone,
    generic-only phrase/literal cases, substring cases, body-only single-token
    cases, and ambiguous non-strong cases miss or remain honestly ambiguous.
    Exact-token `qdrant`, `sysadmin`, or equivalent unique-domain basename/H1/
    title fixtures qualify; exact validated `path:` remains the only generic
    exemption.
11. **Ranking and mandatory delivery.** The four section-1 probes return a
    directly relevant current or discovery document in the first three global
    results. For every objective, the first `min(3, qualifying_count)` results
    are delivered, plus the highest missing ACTIVE/discovery class when needed,
    at most four. Both 3-ACTIVE+1-discovery and 1-ACTIVE+3-discovery maximum
    shapes preserve ranks and initial 600-J excerpts.
12. **Fixture and genuinely held-out evidence.** The committed fixture meets
    its identity, labels, coverage, and top-three rules. The sealed held-out set
    meets three-way authenticated separation, pre-freeze registration,
    >=8/>=6 coverage, frozen taxonomy, semantic and lexical anti-duplication,
    difficulty, four no-title-token, two ambiguous, and one strong-single-token
    rules. The evaluator binds all results to the frozen implementation and
    registered blob. Only complete authenticated raw `PASS` or `APPROVE` for
    every expected top-three, policy, exclusion, and anti-duplication check
    satisfies this clause; revise/error/partial/missing/mixed/self-authored or
    prose-only evidence does not.
13. **First plan and session ceilings.** First-plan delivery includes pinned
    excerpts and performs zero state writes. Independent gateway tests cover
    8 objective digests exact/+1 and 120,000 actual wire bytes exact/+1, mixed
    cached+new batches, split batches, compact and full replay, and new lead IDs.
    Prospective overflow emits a bounded corpus-free control error.
14. **Every record is searchable.** Grouped exact `path:` probes prove all 102
    records contribute at least one searchable unit, including H1-only
    `session-lifecycle.md`, and that the archive is historical. The same harness
    covers staged refresh, shallow history, missing objects, stale records, and
    atomic pin behavior.
15. **State-flip neutrality.** Changing only catalog state or catalog-only
    metadata leaves qualification, common score, relevance evidence, global
    order, excerpts, and corpus-bound digests unchanged.
16. **Buildable verification and independent ACTIVE authority.** A discovery
    lead projects every prose item verbatim, ordered, one-to-one into the
    versioned structured schema. Mapped positive adapter evidence can confirm;
    unmapped prose, unknown adapter, parameter substitution, mapping-digest
    mismatch, missing-one, reused-result, stale evidence, or caller prose cannot.
    An unrelated independently selected ACTIVE candidate that passes existing
    authority policy remains usable without relying on the unmapped discovery
    result. Session digest/byte ceilings and replay accounting cannot be reset by
    prose, batch splitting, or new IDs.
17. **Warning and precedence.** Every pending/archived excerpt is preceded by
    its exact non-truncatable warning carrying catalog state, risk, ground-truth
    flag, and complete verification projection, and remains quoted evidence at
    non-instruction precedence.
18. **Strictly residual supplemental lane.** Repository guidance is absent from
    corpus lanes, has exactly the supplemental schema and exclusions, never
    satisfies breadth or authority, and appears last. Forced-fit and forced-omit
    single and batch tests prove byte-identical corpus projections—including
    result selection, order, fields, warnings, excerpt depths/truncation,
    counters, statuses, and corpus digests—with only supplemental fields and
    deterministic whole-response size/digest allowed to differ.
19. **Exact batch contract and production envelope.** The library accepts only
    sizes 1 and 2 and rejects 0, 3, 4, and a large batch atomically before any
    corpus/README read, retrieval, partial output, or write. The exact production
    serializer proves the two-objective maximum shapes, all variable fields at
    normative maxima, complete warnings/verification metadata, eight possible
    mandatory corpus identities, and 600-J initial excerpts fit <=32,000 U.
    Supplemental guidance is considered only after final corpus allocation.

For the four probes, acceptable direct matches include the named domain
documents in section 1 or a later promoted replacement demonstrably owning the
same procedure. Merely matching generic words is not a pass. The existing
process-heavy ACTIVE benchmark remains compatibility evidence, not sufficient
market-findability acceptance.

## 12. Rollout order

This order supersedes any earlier sequence postponing corpus discovery:

1. repair the structural build wrapper so verified builds are not discarded;
2. land immutable all-corpus search, the closed serializer, and ranking fixes;
3. wire zero-write server-selected discovery into the first plan response;
4. retire caller-authored gate/debt/waiver writers;
5. establish backend write freezes and receipts after zero-writer evidence;
6. perform the appropriate C→M or metadata-only inventory refresh, fully
   validate and verify remote objects, then atomically CAS old-M→new-M without
   activating C; and
7. promote, merge, or archive pending documents in risk order and restore
   narrowly scoped enforcement only after measured search quality, immutable
   evidence, and non-vacuous validation are in production.

The immediate search release is reversible and grants no new authority.
