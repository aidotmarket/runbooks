# S1413 — All-corpus runbook discovery before authority promotion

Status: **BINDING IMPLEMENTATION CONTRACT — REVISION 6**

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
- Revision 3 was published at
  `bef1ca06f6c35753cb451e566b3d3e4e169366a0`. Independent CC review
  `d0fe03f6` returned raw **REJECT** because the verification-cardinality,
  aggregate, and whole-response arithmetic could not satisfy the contract.
  Mandatory MP review `0e98a3a8` independently returned raw **REVISE**,
  confirmed the wire arithmetic defect, and identified the state/digest
  contradiction; it found no unsafe authority expansion.
- Revision 4 folds those binding findings by making the first-plan projection
  compact, moving the complete verification bundle to a bounded read-only
  fetch, publishing executable serializer vectors, making the compatibility
  omission counter exact, and separating state-neutral retrieval identity from
  state-dependent policy and response identities. It claims no implementation,
  review approval, benchmark pass, gateway delivery, merge, deployment, or
  activation.
- Revision 5 is the bounded integration correction discovered by independent
  exact-source tracing. It permits only crash-safe authenticated Kóska
  session-control writes before business-authority writes, makes the short
  lead and bundle values opaque handles backed by immutable server claims,
  defines quota bytes as the canonical content placed in MCP
  `TextContent.text`, and assigns first-plan integration to the actual Kóska
  owner. It changes no pre-existing closed payload field, field maximum, vector
  input, or digest rule, so the Revision-4 byte counts and vector digests remain
  the binding vectors; it adds the closed confirmation and compact-replay
  variants required for exact session accounting. It claims no implementation,
  review approval, benchmark pass, gateway delivery, merge, deployment, or
  activation.
- Revision 6 folds the four binding mandates from exact-identity CC review
  `a72644d6`: issuer-valid handle vectors, an acyclic mint/serialize/persist
  order, terminal confirmation-receipt transitions, and atomic concurrent
  byte/slot admission predicates. The three additional editorial findings from
  that review are nonbinding. Revision 6 changes no production field or byte
  maximum; it republishes only the SHA-256 vectors whose fixed 192-J handle
  fixture bytes changed. It claims no implementation, review approval,
  benchmark pass, gateway delivery, merge, deployment, or activation.

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
| `verify_against` | 1..3 items; 120 canonical string bytes each and 120 aggregate |
| normal corpus excerpt | 2,400 canonical string bytes per item |
| initial mandatory corpus excerpt | min(full source, 600 canonical string bytes) |
| supplemental excerpt | 300 canonical string bytes |
| exact production response | 40,000 UTF-8 bytes including final newline |
| production two-objective worst-case proof | at most 32,000 UTF-8 bytes |

There is no separate character ceiling and no 2,048 raw-byte
`verify_against` boundary. `serialized_bytes` and every `U` response measure
mean `len(text.encode("utf-8"))` for the exact canonical serializer output,
including its final newline, placed byte-for-byte in MCP `TextContent.text`.
JSON-RPC, HTTP, MCP-envelope, request-ID, and other outer transport framing are
not part of this deterministic delivered-content quota. Outer framing may wrap
the text but MUST NOT prefix, truncate, re-encode, or otherwise modify
`TextContent.text`. Optional early raw checks may reject only values
that necessarily violate a binding limit; they are not acceptance boundaries.
Exact-limit and limit-plus-one tests target each binding measure and failure
stage once.

This release freezes manifest/mapping schema version 2 at one through three
`verify_against` items per record. All 102 baseline records conform: 101 have
exactly two, `bq-124-retro-verification.md` has exactly three, none has more
than three, and the largest aggregate canonical JSON-string payload is 120 J.
A future record requiring a fourth item or more requires a separately reviewed
schema version and exact byte proof; it MUST NOT silently widen version 2.

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
batch, its requirement count, its verification-bundle digest, and an
authenticated bounded bundle reference. The warning precedes quoted document
text at non-instruction precedence. The first-plan response does not inline
verification prose or adapter data.

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

The authenticated Kóska session-control store is the sole state-writing
exception before runbook-first delivery. Search and delivery perform zero
Living State, Event Ledger, runbook-debt, waiver, plan-acceptance, intent, or
other business-authority writes before the corpus payload is fixed and
admitted. The control store MAY atomically reserve quota and persist immutable
opaque-reference claims, delivery accounting, fetch state, and replay state
needed by this contract. Those records grant no runbook authority, are never
populated from or overridden by raw caller fields, and have bounded TTL,
authenticated-session binding, crash-safe compare-and-swap, and idempotent
recovery. The server recomputes the objective digest from the validated
normalized objective and derives every remaining claim from its selected
immutable corpus state; caller verification prose, adapter data, paths, IDs, or
claimed digests are never claim sources.

The closed control-store records contain exactly the fields below; unlisted
fields fail. Every digest is lowercase 64-hex SHA-256, every time is canonical
UTC RFC-3339, every integer is non-negative, and `expires_at` is no later than
the authenticated session expiry or 86,400 seconds after `created_at`, whichever
comes first. Every record has `schema_version=1`.

- `session_quota_v1`: `schema_version`, authenticated `session_binding`, an
  ordered array `objective_slots` of at most eight closed objects containing
  `objective_digest`, `reservation_count`, and `admitted`, plus
  `reserved_content_bytes`, `delivered_content_bytes`, `created_at`,
  `expires_at`, and `cas_revision`;
- `delivery_reservation_v1`: `schema_version`, server `delivery_id`,
  `request_idempotency_digest`, `session_binding`, `response_kind`,
  ordered-unique `objective_digests`, exact canonical `payload_digest`,
  `payload_bytes`, ordered-unique `new_objective_digests`,
  `state` (`reserved`, `admitted`, or `released`), `created_at`, state-consistent
  nullable `admitted_at` and `released_at`, `expires_at`, and CAS revision. This
  record also distinguishes an idempotent retry of one delivery from a later
  logical replay, which receives a new `delivery_id` and byte reservation;
- `opaque_reference_claim_v1`: `schema_version`, `claim_kind` (`lead` or
  `bundle`), `handle_digest`, `nonce_digest`, `mac_key_id`, `session_binding`,
  `objective_digest`, `catalog_sha` (the runbooks search SHA), `inventory_sha`,
  `manifest_sha256`, `activation_digest`, `source_blob_oid`,
  `discovery_digest`, `retrieval_digest`, `excerpt_digest`, `discovery_rank`,
  `requirement_count`, exact `verification_bundle_digest`, ordered
  `requirement_set_digest`, `issuing_delivery_id`, bundle-only
  `linked_lead_handle_digest`, `state` (`issued`, `fetched`, `confirmed`,
  `expired`, or `revoked`), `created_at`, `expires_at`, and `cas_revision`.
  `linked_lead_handle_digest` is absent for a lead claim; `fetched` is
  bundle-only and `confirmed` is lead-only;
- `bundle_fetch_receipt_v1`: `schema_version`, `session_binding`,
  `bundle_handle_digest`, `lead_handle_digest`, exact
  `verification_bundle_digest`, canonical `payload_digest`, `payload_bytes`,
  admitting `delivery_id`, `fetched_at`, `confirmation_state` (`unconfirmed`,
  `confirmed`, `contradicted`, or `insufficient`), `created_at`, `expires_at`,
  and `cas_revision`; and
- `verification_receipt_v1`: `schema_version`, `receipt_id_digest`,
  `nonce_digest`, `mac_key_id`, `session_binding`, `objective_digest`,
  `activation_digest`, `source_blob_oid`, `discovery_digest`,
  `retrieval_digest`, exact `verification_bundle_digest`, ordered
  `requirement_set_digest`,
  `evidence_digest`, `outcome` (`confirmed_for_objective`, `contradicted`, or
  `insufficient`), `created_at`, `expires_at`, and `cas_revision`.

Claim payload fields are immutable after creation. Legal claim transitions are
bundle `issued` to `fetched`, lead `issued` to `confirmed`, or any live claim to
`expired`/`revoked`; no transition reverses. Every
`bundle_fetch_receipt_v1.confirmation_state` starts as `unconfirmed` and one
successful proof-consuming CAS may move it exactly once to `confirmed`,
`contradicted`, or `insufficient`. Those three outcomes are terminal: a second
confirmation attempt fails closed as `disallowed-replay`, and no outcome may
reverse or change to another outcome. Receipt identity and digest fields are
immutable; only an explicitly legal state transition and its `cas_revision`
may move. A `verification_receipt_v1` has no post-creation transition, so every
field, including its initial `cas_revision`, remains immutable until terminal
audit-TTL deletion.

`discovery_lead_id` and `verification_bundle_ref` are authenticated opaque
handles, not self-contained claim tokens. Their closed lexical form is 67..192
J of unpadded base64url ASCII `[A-Za-z0-9_-]`, excluding lengths congruent to 1
modulo 4; the 192-J maximum vector therefore remains valid. Every
issuer-produced decoded value is a versioned
binary container with a handle-kind discriminator, at least a 16-byte
cryptographically random server nonce, a 32-byte HMAC-SHA-256 authentication
tag, and optional authenticated opaque padding within the lexical maximum. The
MAC is domain-separated by version and handle kind and binds the encoded
version, kind, nonce, padding, and authenticated session (all container bytes
other than the tag). The server record supplies the key ID and all claims. The
handle carries no caller-readable or caller-selected claim.

The gateway handshake remains server-bound and has four steps:

1. The first-plan search returns server-selected results and derives every
   server claim except the opaque handle bytes. Kóska then mints the lead and
   bundle handle bytes and supplies them as inputs to the pure runbooks
   serializer. After that serializer fixes the canonical payload and every
   digest, but before any corpus text is emitted, Kóska atomically reserves its
   objective slots and canonical delivered-content bytes and persists the
   immutable lead and bundle claim records for those already-minted handles. A
   discovery result
   receives a `discovery_lead_id` whose server record binds session, objective
   digest, `catalog_sha` (the runbooks search SHA), inventory SHA, manifest
   digest, blob, discovery digest,
   retrieval digest, excerpt digest, discovery rank, exact bundle digest, and
   expiry. Its compact warning contains `requirement_count`,
   `verification_bundle_digest`, and a separate `verification_bundle_ref`
   whose record binds that same session, objective, catalog SHA, inventory SHA,
   manifest digest, source blob, discovery lead, bundle digest, and expiry.
   Neither handle accepts verification prose or adapter data or grants
   authority.
2. A separate bounded server call accepts only the exact opaque
   `verification_bundle_ref`. It validates the MAC and session, resolves the
   immutable record, and revalidates expiry, state, objective, activation,
   source, lead, and bundle digest before returning the complete ordered
   one-to-one bundle described in section 6.5. It returns all one through three
   requirements in one closed response. Omission, truncation, paraphrase,
   caller substitution, and pagination are forbidden. Only after the complete
   bundle payload is durably admitted for delivery may CAS create the
   server-owned `bundle_fetch_receipt_v1`. A failed or partial fetch creates no
   fetched state. While a selected discovery lead is unconfirmed, the session
   permits only this bounded fetch and registered production-safe verification.
3. A dedicated confirmation call accepts the lead handle, the exact fetched
   `verification_bundle_digest`, immutable `requirement_id` values, and adapter
   receipts. It resolves and revalidates the lead claim. The exact live
   `bundle_fetch_receipt_v1`, not possession of either handle, MUST prove that
   the matching bundle was completely admitted and validated for the same
   session and activation before any receipt is evaluated. The call validates
   exact requirement bindings, freshness, remote identity, evidence policy,
   and one distinct result per requirement. Missing, expired, disallowed-replay,
   wrong-session, wrong-objective, mismatched-digest, stale-activation, or
   ambiguous claim records fail closed. It returns an authenticated server-owned
   `discovery_verification_receipt_id` with outcome
   `confirmed_for_objective`, `contradicted`, or `insufficient`.
4. Confirmation requires fresh sufficient trusted evidence for every mapped
   requirement, no unmapped item, and no missing, stale, reused, substituted,
   contradicted, or insufficient outcome. The receipt is usable only for its
   bound session, objective, activation identity, blob, retrieval digest,
   bundle digest, requirement IDs, and excerpt.

Archived leads can never be confirmed as current instructions. Contradicted or
insufficient leads expose the authoritative gap and remain read-only.

## 6. Normative production canonical-content schema and maxima

This section is the production contract, not an implementation note. The exact
serializer is `json.dumps(envelope, ensure_ascii=True, sort_keys=True,
separators=(",", ":")) + "\n"`. Its complete output is the canonical payload
placed unchanged in MCP `TextContent.text`; its UTF-8 length is `U` and
`serialized_bytes`. Outer transport framing is excluded as defined in section
3. Objects are closed: a field not listed below is forbidden. There are no
wildcard rows, caller-provided maps, or unbounded strings/lists. `J` means
canonical string bytes from section 3. Integers are canonical non-negative
JSON integers with no leading zeros. Fixed enums are serialized exactly as
listed.

Digest bindings form two explicit layers:

- `delivery_digest`: SHA-256 of the final canonical content envelope with that
  value replaced by 64 ASCII zeroes;
- `retrieval_digest`: a domain-separated SHA-256 of only the state-neutral
  retrieval projection: source blob, path, unit kind and unit identity,
  qualification and match evidence, common score, global rank/order, exact
  delivered excerpt bytes and depth/truncation coordinates, and title/heading
  identities. It excludes catalog commit, manifest/activation identity,
  catalog state, status, owner, declarations, authority eligibility/admission,
  warnings, ACTIVE/discovery kind, kind-specific identities, and every other
  policy-derived field;
- `candidate_digest`, `discovery_digest`, and `warning_id`: domain-separated
  state-dependent digests binding the retrieval digest plus exact catalog SHA,
  manifest digest, inventory activation identity, catalog state/status,
  authority booleans, warning policy, and every applicable kind-specific field;
- `corpus_response_digest`: SHA-256 of the finalized state-dependent corpus-only
  objective projection, including its retrieval and policy/result digests but
  excluding supplemental guidance and whole-response size/digest;
- `objective_digest`: SHA-256 of the versioned normalized objective;
- `verification_bundle_digest`, requirement IDs, and mapping digests:
  domain-separated SHA-256 over the exact closed ordered bundle or identity
  named in sections 5 and 6.5; `guidance_digest` binds only the immutable README
  identity and supplemental projection; and
- all `*_sha256` fields: lowercase 64-hex SHA-256 of the exact named bytes.

No state-dependent digest is valid under a different activation identity or
catalog state, even when its retrieval digest is unchanged. A policy/result
digest from an old authority state MUST fail under the new state.

### 6.1 Envelope and objective fields

| Literal field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Bound by | Production source of truth |
|---|---|---:|---|---|---|---|
| `schema_version` | integer `4` | 1 digit | mandatory once | no | delivery | frozen gateway schema |
| `catalog_sha` | lowercase hex string | 40 J | mandatory once | no | delivery + corpus | resolved immutable search commit |
| `manifest_sha256` | lowercase hex string | 64 J | mandatory once | no | delivery + corpus | manifest blob bytes |
| `inventory_sha` | lowercase hex string | 40 J | mandatory once | no | delivery + corpus | validated manifest inventory |
| `results` | array of objective objects | 1..2 items | mandatory once | no | delivery + corpus | validated request order |
| `searched_entry_count` | integer 0..102 | 3 digits | mandatory once | no | delivery + corpus | validated snapshot |
| `searched_section_count` | integer 0..999999 | 6 digits | mandatory once | no | delivery + corpus | emitted searchable units |
| `complete` | boolean, always true on success | 4 bytes | mandatory once | no | delivery + corpus | allocator |
| `response_budget_bytes` | integer `40000` | 5 digits | mandatory once | no | delivery | frozen limits singleton |
| `response_budget_truncated` | boolean | 5 bytes | mandatory once | no | delivery + corpus | corpus allocator only |
| `dropped_candidate_count` | integer 0..1999998 | 7 digits | mandatory once; deprecated compatibility counter | no | delivery + corpus | exact equation below |
| `serialized_bytes` | integer 0..40000 | 5 digits | mandatory once | no | delivery | exact canonical `TextContent.text` UTF-8 bytes |
| `delivery_digest` | lowercase hex string | 64 J | mandatory once | no | self rule above | exact canonical `TextContent.text` |

| Literal objective field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Bound by | Production source of truth |
|---|---|---:|---|---|---|---|
| `objective_ordinal` | integer 1..2 | 1 digit | mandatory once/objective | no | delivery + corpus | request order |
| `objective_digest` | lowercase hex string | 64 J | mandatory once/objective | no | delivery + corpus | normalized objective |
| `status` | enum: `candidates_returned_unverified`, `no_positive_candidate_in_active_catalog`, `no_usable_corpus_result_response_budget`, `no_relevant_result` | 39 J | mandatory once/objective | no | delivery + corpus | authority policy + allocator |
| `discovery_status` | enum: `discovery_leads_returned_unverified`, `no_qualifying_discovery_lead` | 35 J | mandatory once/objective | no | delivery + corpus | discovery lane |
| `authoritative_gap` | boolean | 5 bytes | mandatory once/objective | no | delivery + corpus | ACTIVE/discovery qualification |
| `qualifying_result_count` | integer 0..999999 | 6 digits | mandatory once/objective | no | delivery + corpus | ranker |
| `eligible_candidate_count` | integer 0..333333 | 6 digits | mandatory once/objective | no | delivery + corpus | ACTIVE policy evaluator |
| `eligible_candidates_returned` | integer 0..4 | 1 digit | mandatory once/objective | no | delivery + corpus | allocator |
| `eligible_candidates_omitted_by_limit` | integer 0..333333 | 6 digits | mandatory once/objective | no | delivery + corpus | allocator |
| `eligible_candidates_omitted_by_response_budget` | integer 0..333333 | 6 digits | mandatory once/objective | no | delivery + corpus | allocator |
| `active_searched_count` | integer 0..20 | 2 digits | mandatory once/objective | no | delivery + corpus | snapshot/ranker |
| `active_qualifying_count` | integer 0..333333 | 6 digits | mandatory once/objective | no | delivery + corpus | ranker |
| `active_returned_count` | integer 0..4 | 1 digit | mandatory once/objective | no | delivery + corpus | allocator |
| `active_omitted_count` | integer 0..333333 | 6 digits | mandatory once/objective | no | delivery + corpus | allocator |
| `grandfathered_searched_count` | integer 0..81 | 2 digits | mandatory once/objective | no | delivery + corpus | snapshot/ranker |
| `grandfathered_qualifying_count` | integer 0..333333 | 6 digits | mandatory once/objective | no | delivery + corpus | ranker |
| `grandfathered_returned_count` | integer 0..4 | 1 digit | mandatory once/objective | no | delivery + corpus | allocator |
| `grandfathered_omitted_count` | integer 0..333333 | 6 digits | mandatory once/objective | no | delivery + corpus | allocator |
| `archived_searched_count` | integer 0..1 | 1 digit | mandatory once/objective | no | delivery + corpus | snapshot/ranker |
| `archived_qualifying_count` | integer 0..333333 | 6 digits | mandatory once/objective | no | delivery + corpus | ranker |
| `archived_returned_count` | integer 0..1 | 1 digit | mandatory once/objective | no | delivery + corpus | allocator |
| `archived_omitted_count` | integer 0..333333 | 6 digits | mandatory once/objective | no | delivery + corpus | allocator |
| `candidates` | array of ACTIVE result objects | 0..4 items | mandatory once/objective | items no | delivery + corpus | global results filtered ACTIVE |
| `discovery_leads` | array of discovery result objects | 0..4 items | mandatory once/objective | items no | delivery + corpus | global results filtered non-ACTIVE |
| `supplemental_guidance` | array of supplemental objects | 0..1 item | mandatory once/objective | whole item may be omitted | delivery only | residual allocator |
| `supplemental_guidance_returned` | boolean | 5 bytes | mandatory once/objective | no | delivery only | residual allocator |
| `supplemental_guidance_omitted_by_response_budget` | boolean | 5 bytes | mandatory once/objective | no | delivery only | residual allocator |
| `corpus_response_digest` | lowercase hex string | 64 J | mandatory once/objective | no | delivery + corpus | frozen state-dependent corpus serialization |

The two lane arrays have a joint maximum of four corpus results per objective;
neither array's individual maximum permits more than four in their union. The
validated request `query` is deliberately not echoed by the final canonical
content; its 4,000-J input boundary is enforced before reads and
`objective_digest` is the delivered-content identity.

For objective `o`, each state obeys
`state_omitted_count = state_qualifying_count - state_returned_count`, and
`qualifying_result_count` equals the sum of the three state qualifying counts
and is at most 999,999. The envelope compatibility field is exactly
`dropped_candidate_count = sum_o(active_omitted_count +
grandfathered_omitted_count + archived_omitted_count)`. Its true two-objective
maximum is 1,999,998. It MUST NOT be clamped, saturated, approximated, or
disagree with any per-state counter. Zero, 1,999,998, and 1,999,999 overflow
are exact tests.

The ACTIVE compatibility counters also obey
`eligible_candidate_count = eligible_candidates_returned +
eligible_candidates_omitted_by_limit +
eligible_candidates_omitted_by_response_budget`; neither omission field may
double-count an ACTIVE result.

### 6.2 Common corpus result and evidence fields

Every corpus result has the following closed common object. Section-only fields
are all present for `unit_kind=section` and all absent for
`unit_kind=document`.

| Literal field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Bound by | Production source of truth |
|---|---|---:|---|---|---|---|
| `retrieval_digest` | lowercase hex string | 64 J | mandatory once/result | no | retrieval self digest + policy result + corpus response | state-neutral projection above |
| `relevance_rank` | integer 1..999999 | 6 digits | mandatory once/result | no | retrieval + corpus response | state-neutral ranker |
| `path` | portable ASCII Git-path string | 192 UTF-8 bytes | mandatory once/result | no | retrieval + corpus response | validated manifest/catalog path |
| `candidate_kind` | enum: `active_catalog_section`, `active_catalog_document`, `grandfathered_discovery_lead`, `archived_discovery_lead` | 28 J | mandatory once/result | no | policy result + corpus response | catalog/manifest state + unit |
| `catalog_state` | enum `ACTIVE`, `grandfathered`, `archived` | 13 J | mandatory once/result | no | policy result + corpus response | validated catalog/manifest |
| `status` | enum `ACTIVE`, `pending_verification`, `archived` | 20 J | mandatory once/result | no | policy result + corpus response | validated catalog/manifest |
| `action_authority_eligible` | boolean | 5 bytes | mandatory once/result | no | policy result + corpus response | catalog policy; false for discovery |
| `authority_admission` | boolean | 5 bytes | mandatory once/result | no | policy result + corpus response | catalog policy; false for discovery |
| `candidate_id_eligible` | boolean | 5 bytes | mandatory once/result | no | policy result + corpus response | catalog policy; false for discovery |
| `catalog_declared` | boolean | 5 bytes | mandatory once/result | no | policy result + corpus response | exact section declaration match |
| `declaration_kinds` | ordered unique enum array of `topic`, `error_signature` | 0..2 items; 27 U | mandatory once/result | no | policy result + corpus response | catalog declarations |
| `integrity_only` | boolean | 5 bytes | mandatory once/result | no | policy result + corpus response | catalog policy; true for discovery |
| `integrity_status` | enum `integrity_pass_unverified` | 25 J | mandatory once/result | no | policy result + corpus response | immutable loader |
| `semantic_verification` | boolean | 5 bytes | mandatory once/result | no | policy result + corpus response | catalog/verification policy |
| `unit_kind` | enum `section`, `document` | 8 J | mandatory once/result | no | retrieval + corpus response | parser |
| `document_title` | string | 64 J | mandatory once/result | longest source-faithful prefix allowed | retrieval + corpus response | exact H1/title |
| `document_title_sha256` | lowercase hex string | 64 J | mandatory once/result | no | retrieval + corpus response | full untruncated H1/title |
| `document_title_truncated` | boolean | 5 bytes | mandatory once/result | no | retrieval + corpus response | title bounding |
| `heading` | string | 64 J | section-only once | longest source-faithful prefix allowed | retrieval + corpus response | exact Markdown heading |
| `heading_sha256` | lowercase hex string | 64 J | section-only once | no | retrieval + corpus response | full heading |
| `heading_truncated` | boolean | 5 bytes | section-only once | no | retrieval + corpus response | heading bounding |
| `heading_line` | integer 1..999999 | 6 digits | section-only once | no | retrieval + corpus response | Markdown parser |
| `section_id` | string | 64 J | section-only once | deterministic prefix+digest allowed | retrieval + corpus response | catalog ID or frozen derivation |
| `section_id_source` | enum `catalog`, `legacy-derived` | 14 J | section-only once | no | retrieval + corpus response | catalog/parser |
| `excerpt_start_line` | integer 1..999999 | 6 digits | mandatory once/result | no | retrieval + corpus response | source line map |
| `excerpt_end_line` | integer 1..999999 | 6 digits | mandatory once/result | no | retrieval + corpus response | source line map |
| `excerpt_end_column_exclusive` | integer 1..999999 | 6 digits | mandatory once/result | no | retrieval + corpus response | source line map |
| `excerpt` | string | initial 600 J; residual growth to 2,400 J | mandatory once/result | source-faithful prefix only | retrieval + corpus response | pinned source blob |
| `excerpt_sha256` | lowercase hex string | 64 J | mandatory once/result | no | retrieval + corpus response | delivered excerpt bytes |
| `excerpt_truncated` | boolean | 5 bytes | mandatory once/result | no | retrieval + corpus response | excerpt allocator |
| `match_evidence` | array of match-evidence objects | 0..1 item | mandatory once/result | list may truncate only after qualification; flag per object | retrieval + corpus response | production scorer |
| `relevance_evidence` | array of enum `path`, `title`, `heading`, `phrase`, `structured_literal`, `token_threshold`, `single_strong_token` | 1..7 items; 96 U | mandatory once/result | no | retrieval + corpus response | state-neutral qualifier |
| `score` | JSON number 0..999999.999999, max 6 decimals | 13 bytes | mandatory once/result | no | retrieval + corpus response | common scorer |
| `source_blob_oid` | lowercase SHA-1 or SHA-256 hex | 64 J | mandatory once/result | no | retrieval + policy result + corpus response | validated Git object |

Each `match_evidence` object is closed and contains every field below. It
repeats at most once.

| Literal match-evidence field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Digest binding | Production source of truth |
|---|---|---:|---|---|---|---|
| `kind` | enum `path`, `title`, `heading`, `excerpt`, `structured_literal`, `intent`, `legacy_active` | 18 J | mandatory once | no | retrieval + corpus response | production scorer |
| `matched_tokens` | array of strings | 0..4 strings; 24 J/item and 96 J aggregate | mandatory once | items no | retrieval + corpus response | normalized query/source token intersection |
| `matched_tokens_truncated` | boolean | 5 bytes | mandatory once | no | retrieval + corpus response | scorer evidence bounder |
| `value` | string | 96 J | mandatory once | longest source-faithful prefix | retrieval + corpus response | pinned source/scorer evidence |
| `weight` | JSON number 0..9999.999999, max 6 decimals | 11 bytes | mandatory once | no | retrieval + corpus response | frozen common scorer |

### 6.3 ACTIVE-only fields

| Literal field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Bound by | Production source of truth |
|---|---|---:|---|---|---|---|
| `candidate_digest` | lowercase hex string | 64 J | mandatory once/ACTIVE result | no | state-dependent candidate self digest + corpus response | immutable ACTIVE policy identity |
| `runbook_id` | string | 64 J | mandatory once/ACTIVE result | no | candidate + corpus response | validated catalog |
| `owner` | enum `vulcan`, `mars`, `kd`, `mp`, `max` | 6 J | mandatory once/ACTIVE result | no | candidate + corpus response | validated catalog |
| `last_verified_at` | RFC-3339 full-date string | 10 J | mandatory once/ACTIVE result | no | candidate + corpus response | validated catalog |
| `authority_keys` | ordered unique string array | 0..2; each 64 J; 128 J aggregate | mandatory once/ACTIVE result | entries/prefixes may truncate with flag | candidate + corpus response | catalog declarations |
| `authority_keys_truncated` | boolean | 5 bytes | mandatory once/ACTIVE result | no | candidate + corpus response | authority-key bounding |
| `rank` | integer 1..999999 or null | 6 digits | mandatory once/ACTIVE result; legacy within-lane rank | no | candidate + corpus response | compatibility ranker |

ACTIVE results MUST omit all discovery-only fields.

### 6.4 Compact discovery warning and identity fields

Each discovery result contains exactly one compact nested `warning`. It carries
the bundle identity and reference but no verification prose, adapter type,
adapter parameters, evidence policy, receipt, or caller field.

| Literal field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Bound by | Production source of truth |
|---|---|---:|---|---|---|---|
| `discovery_digest` | lowercase hex string | 64 J | mandatory once/discovery | no | state-dependent discovery self digest + corpus response | immutable discovery policy identity |
| `discovery_lead_id` | authenticated opaque handle | 192 J | mandatory once/delivered discovery | no | discovery + corpus response | Kóska session-control claim issuer |
| `requires_ground_truth_verification` | boolean, always true | 4 bytes | mandatory once/discovery | no | discovery + corpus response | fixed policy |
| `historical_only` | boolean | 5 bytes | mandatory once/discovery | no | discovery + corpus response | manifest state |
| `manifest_risk` | enum `P0`, `P1`, `P2`, `P3` | 2 J | mandatory once/discovery | no | discovery + corpus response | manifest record |
| `manifest_batch` | string | 128 J | mandatory once/discovery | no | discovery + corpus response | manifest record |
| `warning` | closed compact warning object below | 1 item | mandatory once/discovery | no | warning + discovery + corpus response | gateway policy renderer |

The compact warning object contains every listed field and no others:

| Literal warning field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Bound by | Production source of truth |
|---|---|---:|---|---|---|---|
| `warning_id` | lowercase hex string | 64 J | mandatory once/warning | no | state-dependent warning self digest + discovery + corpus response | gateway renderer |
| `code` | enum `DISCOVERY_ONLY_NOT_VERIFIED` | 27 J | mandatory once/warning | no | warning + discovery + corpus response | fixed policy |
| `message` | exact `DISCOVERY ONLY — NOT VERIFIED OPERATING AUTHORITY` | 54 J | mandatory once/warning | no | warning + discovery + corpus response | fixed policy |
| `catalog_state` | enum `grandfathered`, `archived` | 13 J | mandatory once/warning | no | warning + discovery + corpus response | parent discovery result |
| `manifest_risk` | enum `P0`, `P1`, `P2`, `P3` | 2 J | mandatory once/warning | no | warning + discovery + corpus response | manifest record |
| `requires_ground_truth_verification` | boolean true | 4 bytes | mandatory once/warning | no | warning + discovery + corpus response | fixed policy |
| `requirement_count` | integer 1..3 | 1 digit | mandatory once/warning | no | warning + bundle + discovery + corpus response | validated manifest list count |
| `verification_bundle_digest` | lowercase hex string | 64 J | mandatory once/warning | no | warning + discovery + corpus response | closed ordered bundle projection |
| `verification_bundle_ref` | authenticated opaque handle | 192 J | mandatory once/warning | no | warning + discovery + corpus response | Kóska session-control claim issuer using section 5 |

Discovery results MUST omit `candidate_digest`, `runbook_id`, `owner`,
`last_verified_at`, `authority_keys`, `authority_keys_truncated`, `rank`, and
the full `verification_requirements` array. The compact reference and digest
are not verification evidence and grant no authority.

### 6.5 Complete bounded verification-bundle response

The bundle-fetch response uses the same exact canonical-content serializer as
the first-plan response and is placed unchanged in `TextContent.text`. It is a
separate closed envelope with a hard maximum of 8,192 U, including its final
newline. It contains every field below and no first-plan, supplemental,
control, receipt, or unknown field:

| Literal bundle-envelope field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Digest binding | Production source of truth |
|---|---|---:|---|---|---|---|
| `schema_version` | integer `1` | 1 digit | mandatory once | no | delivery + bundle | frozen bundle canonical-content schema |
| `response_kind` | exact `verification_bundle` | 19 J | mandatory once | no | delivery + bundle | fixed server value |
| `catalog_sha` | lowercase hex string | 40 J | mandatory once | no | delivery + bundle | resolved immutable opaque-reference claim |
| `manifest_sha256` | lowercase hex string | 64 J | mandatory once | no | delivery + bundle | resolved immutable opaque-reference claim |
| `inventory_sha` | lowercase hex string | 40 J | mandatory once | no | delivery + bundle | resolved immutable opaque-reference claim |
| `objective_digest` | lowercase hex string | 64 J | mandatory once | no | delivery + bundle | resolved immutable opaque-reference claim |
| `source_blob_oid` | lowercase Git OID | 64 J | mandatory once | no | delivery + bundle | resolved immutable opaque-reference claim |
| `discovery_digest` | lowercase hex string | 64 J | mandatory once | no | delivery + bundle | resolved immutable opaque-reference claim |
| `discovery_lead_id` | authenticated opaque handle | 192 J | mandatory once | no | delivery + bundle | resolved immutable opaque-reference claim |
| `verification_bundle_ref_sha256` | lowercase hex string | 64 J | mandatory once | no | delivery + bundle | exact presented authenticated reference bytes |
| `verification_bundle_digest` | lowercase hex string | 64 J | mandatory once | no | delivery + bundle self projection | rule below |
| `requirement_count` | integer 1..3 | 1 digit | mandatory once | no | delivery + bundle | exact array length |
| `verification_requirements` | ordered array of closed objects below | 1..3 items | mandatory once | no | delivery + bundle | validated immutable manifest mapping |
| `serialized_bytes` | integer 0..8192 | 4 digits | mandatory once | no | delivery | exact canonical `TextContent.text` UTF-8 bytes |
| `delivery_digest` | lowercase hex string | 64 J | mandatory once | no | digest rule in section 6 | exact canonical `TextContent.text` |

Every requirement contains all fields below. The ordered array has a 120-J
aggregate prose cap. No requirement or subobject truncates.

The `verification_bundle_digest` is the domain-separated SHA-256 of the exact
ordered requirements plus `schema_version`, `response_kind`, catalog SHA,
manifest digest, inventory SHA, objective digest, source blob, discovery digest,
and discovery lead ID. It excludes itself, the authenticated-reference digest,
`serialized_bytes`, and `delivery_digest`; the authenticated reference then
binds that already-finalized bundle digest. This order is acyclic and makes the
compact and fetched digest byte-identical.

| Literal requirement field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Digest binding | Production source of truth |
|---|---|---:|---|---|---|---|
| `schema_version` | integer `2` | 1 digit | mandatory once/requirement | no | requirement + mapping + bundle | frozen manifest mapping schema |
| `ordinal` | integer 1..3 | 1 digit | mandatory once/requirement | no | requirement + mapping + bundle | manifest list position |
| `prose` | string | 120 J/item and 120 J/array | mandatory once/requirement | no | prose digest + requirement + bundle | verbatim `verify_against` item |
| `prose_sha256` | lowercase hex string | 64 J | mandatory once/requirement | no | requirement + bundle | exact prose bytes |
| `requirement_id` | lowercase hex string | 64 J | mandatory once/requirement | no | requirement self digest + bundle | path/ordinal/prose/manifest/blob/objective/session/catalog/inventory |
| `mapping_digest` | lowercase hex string | 64 J | mandatory once/requirement | no | mapping self digest + requirement + bundle | adapter type, parameters, policy, schema |
| `adapter_type` | frozen enum from section 5 | 19 J | mandatory once/requirement | no | mapping + requirement + bundle | reviewed manifest mapping |
| `adapter_parameters` | adapter-specific closed object below | one object | mandatory once/requirement | no | mapping + requirement + bundle | reviewed manifest mapping |
| `evidence_policy` | closed object below | one object | mandatory once/requirement | no | mapping + requirement + bundle | reviewed manifest mapping |

Adapter parameter objects are closed by type; each listed string maximum uses
J and each integer maximum is inclusive:

| `adapter_type` | Exact literal fields, types, and maxima | Presence | Truncation | Digest binding | Production source of truth |
|---|---|---|---|---|---|
| `git_object_v1` | `repository`: string <=64; `commit_sha`: 40-J lowercase hex; `path`: portable ASCII string <=192 bytes; `expected_object_oid`: 64-J lowercase hex | every field mandatory once | no | mapping + requirement + bundle | reviewed manifest mapping |
| `json_schema_v1` | `repository`: string <=64; `commit_sha`: 40-J lowercase hex; `path`: portable ASCII string <=192 bytes; `json_pointer`: string <=128 J; `expected_value_sha256`: 64-J lowercase hex | every field mandatory once | no | mapping + requirement + bundle | reviewed manifest mapping |
| `health_probe_v1` | `service_id`: string <=64 J; `probe_id`: string <=96 J; `max_age_seconds`: integer 0..86400 | every field mandatory once | no | mapping + requirement + bundle | reviewed manifest mapping |
| `test_result_v1` | `repository`: string <=64 J; `commit_sha`: 40-J lowercase hex; `test_id`: string <=128 J; `report_sha256`: 64-J lowercase hex | every field mandatory once | no | mapping + requirement + bundle | reviewed manifest mapping |
| `state_read_v1` | `namespace`: string <=64 J; `entity_key`: string <=128 J; `field_path`: string <=128 J; `expected_value_sha256`: 64-J lowercase hex | every field mandatory once | no | mapping + requirement + bundle | reviewed manifest mapping |
| `production_probe_v1` | `service_id`: string <=64 J; `probe_id`: string <=96 J; `max_age_seconds`: integer 0..86400 | every field mandatory once | no | mapping + requirement + bundle | reviewed manifest mapping |
| `unmapped_prose` | no fields; exact object `{}` | mandatory empty object | no | mapping + requirement + bundle | deterministic fallback for absent mapping |

The evidence-policy object is closed and contains every field below:

| Literal evidence-policy field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Digest binding | Production source of truth |
|---|---|---:|---|---|---|---|
| `minimum_receipts` | integer 1..4 | 1 digit | mandatory once | no | mapping + requirement + bundle | reviewed manifest mapping |
| `maximum_receipts` | integer 1..4 and >= minimum | 1 digit | mandatory once | no | mapping + requirement + bundle | reviewed manifest mapping |
| `freshness_seconds` | integer 0..86400 | 5 digits | mandatory once | no | mapping + requirement + bundle | reviewed manifest mapping |
| `allowed_evidence_kinds` | ordered unique array of enums `git`, `schema`, `health`, `test`, `state`, `probe` | 1..4 items; 35 U | mandatory once | no | mapping + requirement + bundle | reviewed manifest mapping |
| `require_remote_identity` | boolean | 5 bytes | mandatory once | no | mapping + requirement + bundle | reviewed manifest mapping |
| `require_distinct_sources` | boolean | 5 bytes | mandatory once | no | mapping + requirement + bundle | reviewed manifest mapping |

The minimum legal vector is 1/1/0, one `git` kind, and both booleans false; the
maximum legal vector is 4/4/86400, the four longest allowed enum strings in
frozen enum order, and both booleans true. Section 6.8 proves both policies for
three maximal instances of every adapter shape. The largest proven response is
below 8,192 U; a fourth item, 121-J aggregate prose, omission, pagination, or
unknown field fails closed before any bundle delivery.

### 6.5.1 Closed confirmation and compact-replay content

Confirmation and compact replay use the section-6 serializer and canonical
`TextContent.text` rule. They do not use an informal acknowledgement, generic
map, or outer transport size. Each is one of the following two closed variants;
fields from the other variant and every unknown field fail before admission.
Both have a hard 1,024-U maximum including the final newline.

The `activation_digest` is a domain-separated SHA-256 over catalog SHA,
manifest digest, inventory SHA, source blob OID, discovery digest, and retrieval
digest. `requirement_set_digest` binds the ordered immutable requirement IDs.
The receipt ID is an authenticated server-owned opaque base64url value of at
most 192 J. It uses the section-5 versioned container and authentication rules
with handle kind `receipt` and resolves only to `verification_receipt_v1`; it
does not carry caller-selected claims. The compact replay `reference_value` is the exact
already-issued lead, bundle, or verification-receipt value named by
`reference_kind`; it creates no new authority or fetch state.

| Literal field | Confirmation receipt | Compact replay receipt | Maximum | Truncation | Production source of truth |
|---|---|---|---:|---|---|
| `schema_version` | integer `1`, mandatory | integer `1`, mandatory | 1 digit | no | frozen canonical-content schema |
| `response_kind` | exact `discovery_verification_receipt` | exact `compact_replay_receipt` | 30 J | no | fixed Kóska value |
| `session_binding_sha256` | lowercase hex, mandatory | lowercase hex, mandatory | 64 J | no | authenticated session |
| `objective_digest` | lowercase hex, mandatory | lowercase hex, mandatory | 64 J | no | immutable session-control claim |
| `activation_digest` | lowercase hex, mandatory | forbidden | 64 J | no | rule above |
| `verification_bundle_digest` | lowercase hex, mandatory | forbidden | 64 J | no | fetched bundle receipt |
| `requirement_set_digest` | lowercase hex, mandatory | forbidden | 64 J | no | ordered requirement IDs |
| `outcome` | enum `confirmed_for_objective`, `contradicted`, `insufficient`, mandatory | forbidden | 23 J | no | verification evaluator |
| `discovery_verification_receipt_id` | authenticated opaque value, mandatory | forbidden | 192 J | no | `verification_receipt_v1` issuer |
| `replay_of_delivery_digest` | forbidden | lowercase hex, mandatory | 64 J | no | admitted cached delivery |
| `reference_kind` | forbidden | enum `discovery_lead_id`, `verification_bundle_ref`, `discovery_verification_receipt_id`, mandatory | 33 J | no | cached response kind |
| `reference_value` | forbidden | authenticated opaque value, mandatory | 192 J | no | exact cached server value |
| `serialized_bytes` | integer 0..1024, mandatory | integer 0..1024, mandatory | 4 digits | no | exact canonical `TextContent.text` UTF-8 bytes |
| `delivery_digest` | lowercase hex, mandatory | lowercase hex, mandatory | 64 J | no | section-6 zero-substitution rule |

A compact replay is legal only when the cached response exposes exactly one of
the listed server values; otherwise replay returns the full cached canonical
payload and is charged at full size. A confirmation receipt is emitted only
after the exact fetched-state and evidence checks in section 5. Both variants
are independently quota-reserved and charged exactly once by their
`delivery_id`.

### 6.6 Supplemental guidance fields and production exclusions

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
| `excerpt` | string | 300 J | mandatory once | source-faithful prefix | excerpt + guidance + delivery | README section |
| `excerpt_sha256` | lowercase hex string | 64 J | mandatory once | no | guidance + delivery | delivered excerpt |
| `excerpt_truncated` | boolean | 5 bytes | mandatory once | no | guidance + delivery | residual allocator |
| `guidance_digest` | lowercase hex string | 64 J | mandatory once | no | self + delivery | SHA, README OID, excerpt digest |
| `warning_id` | lowercase hex string | 64 J | mandatory once | no | guidance + delivery | warning identity |
| `warning_code` | exact `SUPPLEMENTAL_GUIDANCE_NOT_AUTHORITY` | 35 J | mandatory once | no | guidance + delivery | fixed policy |
| `warning_message` | exact `SUPPLEMENTAL GUIDANCE — NOT RUNBOOK AUTHORITY` | 50 J | mandatory once | no | guidance + delivery | fixed policy |

The production Kóska adapter MUST use an explicit closed allowlist and test
that these current library-fragment compatibility fields are not serialized in
the final canonical content: objective field `query`; repeated objective fields
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
canonical `TextContent.text`. No generic passthrough is permitted.

### 6.7 Typed non-success envelope

A non-success serializes this separate closed envelope and no success-envelope
field, objective, warning, corpus result, excerpt, lead ID, or receipt. It is
also subject to the exact production serializer and delivery-digest rule.

| Literal field | Type / canonical encoding | Maximum | Presence / repeats | Truncation | Bound by | Production source of truth |
|---|---|---:|---|---|---|---|
| `schema_version` | integer `4` | 1 digit | mandatory once | no | delivery | frozen gateway schema |
| `status` | exact string `fail` | 4 J | mandatory once | no | delivery | gateway control path |
| `error_code` | enum `batch_size_invalid`, `query_limit_exceeded`, `manifest_parse_failed`, `manifest_validation_failed`, `corpus_history_unavailable`, `corpus_inventory_stale`, `mandatory_corpus_envelope_too_large`, `response_budget_exceeded`, `session_objective_budget_exceeded`, `session_wire_budget_exceeded`, `invalid_limits_override` | 35 J | mandatory once | no | delivery | typed failing stage |
| `message` | fixed server-owned message selected by error code | 256 J | mandatory once | no | delivery | frozen error catalog |
| `changed_paths` | ordered unique portable-path array | 0..102 items; 192 UTF-8 bytes/item; 20,000 U aggregate | mandatory only for `corpus_inventory_stale`; otherwise absent | no | delivery | immutable old/new inventory diff |
| `serialized_bytes` | integer 0..24000 | 5 digits | mandatory once | no | delivery | exact canonical control-content bytes |
| `delivery_digest` | lowercase hex string | 64 J | mandatory once | no | digest-binding rule in section 6 | exact canonical control content |

The control envelope is at most 24,000 U and contains no caller prose. The
192-byte portable-path and 102-record bounds make the complete changed-path set
fit; the serializer never emits a partial path list or corpus result.

### 6.8 Executable exact-serializer proof vectors

These vectors were constructed and measured atomically with exactly
`json.dumps(envelope, ensure_ascii=True, sort_keys=True,
separators=(",", ":")) + "\n"`; each table digest is SHA-256 of those final
serialized bytes. Digest-valued fields occupy 64 lowercase hex bytes, SHA
fields occupy their exact length, integers use the maximum value permitted by
the concrete shape and cross-field equations, portable paths are 192 bytes, and
canonical-J strings use escape-bearing input whose serialized payload reaches
the exact maximum, except that opaque handle fields use the valid base64url
fixtures pinned below. Returned ranks are the valid distinct top three plus the
missing-class rank rather than duplicated numeric maxima. Standalone result
vectors use the 2,400-J residual excerpt maximum. Objective and response
vectors use the mandatory 600-J corpus excerpt, all other shape-permitted field
maxima, the exact counter equations, and one maximal 300-J strictly residual
supplemental item per objective. Each three-item bundle uses a total of 120 J
of prose (40 J per ordinal), one maximal adapter shape repeated three times,
and the named minimum or maximum legal evidence policy. Delivery digests are
populated by the section-6 zero-substitution rule before the final vector
digest is measured.

Revision 5 changed no pre-existing payload field or maximum. Revision 6 changes
only the opaque-handle vector fixture bytes so the proof inputs are values a
conforming issuer can mint; every published U count is unchanged and every
affected SHA-256 below is remeasured. The handle fixture key is 32 ASCII `K`
bytes, the session binding is 64 ASCII `a` bytes, and the HMAC input is ASCII
`runbook-reference-vector-v1`, one NUL byte, the version and kind bytes as
domain discriminators, that session binding, then the 112-byte body. The body
is version byte `0x01`, kind byte `0x01` for a lead, `0x02` for a bundle, or
`0x03` for a verification receipt, a 16-byte repeated seed, and 94 bytes of
`0x4c` for a lead, `0x52` for a bundle, or `0x56` for a receipt. Appending the
32-byte HMAC-SHA-256 tag and unpadded
base64url-encoding the resulting 144 bytes produces exactly 192 J. Standalone
discovery, bundle, confirmation-receipt, and compact receipt-replay vectors use
seed `0x01`; objective vectors use seed
`objective_ordinal * 8 + discovery_ordinal_within_lane`. This algorithm pins
every handle byte, preserves uniqueness within a response, and excludes handle
fields from the generic escape-bearing filler rule. A handle is inserted before
the enclosing delivery is finalized, so zero substitution recomputes that
delivery's inner `delivery_digest` as well as the table's outer SHA-256.

The two added session-control vectors use all applicable field maxima. In both,
session binding is 64 `a` bytes and objective digest is 64 `b` bytes. The
confirmation vector uses 64 `c`, `d`, and `e` bytes for activation, bundle, and
requirement-set digests respectively and the receipt-kind fixture above for the
receipt ID. The compact-replay vector uses 64 `c` bytes for the replayed
delivery digest, the longest reference-kind enum, and that same receipt-kind
fixture for its value. Each
`serialized_bytes` value is its exact final length; each delivery digest is
populated by zero substitution before the final SHA-256 is measured.

| Concrete vector | Exact U | SHA-256 test-vector digest |
|---|---:|---|
| maximum ACTIVE result | 4,803 | `b46d0e477dc25cc475c2568ee7df359419992f0a31526820efa21b1dbf8ff3f6` |
| maximum compact discovery result | 5,585 | `c167e7c24d58211e4b00197633632a2d8020e8a08ce0aac8b20b2be83a3f6c99` |
| objective: 3 ACTIVE + 1 discovery | 14,920 | `8bf3bfcab5edecf2a51fcf7838d25ba91fff02473856e351aaefa4bd739fefc7` |
| objective: 1 ACTIVE + 3 discovery | 16,484 | `f44dc11fb8a260a6f1efca5d3ddbdfb55e836ff7ecc8831e02f8fdc16a666526` |
| two objectives: 3A+1D then 1A+3D | 31,921 | `1961dfb06102805e7b9d81b067c09217ec056526c2db14fdaea919e3f32d707e` |
| two objectives: 1A+3D then 3A+1D | 31,921 | `2445942c4f41ce01a0fbcd78955d033e9d0ef561b53d5d6b1f73bab186bbc8ab` |
| maximum changed-path control response | 20,375 | `30208ccc9817934c1e61dd323760cf145c2921c2721af62bd9208983cf4281ac` |
| maximum confirmation receipt | 898 | `472a8520b4cbea98859ac4f2c47583f8373568c65843a5b5be80018331e22cc6` |
| maximum compact replay receipt | 709 | `a1a7c43c0e2a3dc0ffc640e3450ac4057dc74aa8141ba36322b595ea4ce95601` |
| private exact 32,001-U fault object | 32,001 | `c6133529150ae7de4b5502e9e2540df52aea1cdb433cc03b2e70362edf739cc8` |
| bundle `git_object_v1`, minimum policy | 4,080 | `b54e6df2ec9c5621a653c8726f0828ca1a9dd4ed74d21b97edd8b4a88c2ac8a3` |
| bundle `git_object_v1`, maximum policy | 4,170 | `290dc856d8f8c9a8bc84ca9a3185668c42d694cc314fdf2317d7713782bdb043` |
| bundle `json_schema_v1`, minimum policy | 4,527 | `21811e027c38424c835dbf655cf0796bd8ffdbf4b8c72446d0959ca8b17b1963` |
| bundle `json_schema_v1`, maximum policy (largest bundle) | 4,617 | `33dee72ed6c01415e7cb81b909ee11fa6ffcc7094fced749b8bdbd888c51ca1d` |
| bundle `health_probe_v1`, minimum policy | 3,447 | `b5f5ea43cf2675cd1e3d57c6347afef38289af7f2c09e9aab3e3d309b56966e3` |
| bundle `health_probe_v1`, maximum policy | 3,537 | `21086708e29dbe74f5103af297a1919744152b5d9b3348ebd10d8b652a7a5f14` |
| bundle `test_result_v1`, minimum policy | 3,882 | `196e4cdd9fb9404e5e70f9c8d1af2756e64f6ee54a9e546ba5a99610170808c7` |
| bundle `test_result_v1`, maximum policy | 3,972 | `cea36500629a389da5a498af736c599dc140b800cf83ee74a475ea2372f9e64b` |
| bundle `state_read_v1`, minimum policy | 4,173 | `0bcf41e35ecbc7e3a5b11f613bb7dfed1756ae481c3aaf981c3fa283bec5b2c1` |
| bundle `state_read_v1`, maximum policy | 4,263 | `7960fed7ce2ac3ac076e6021daac4a56293c7d35a7b8183cb673262f26094a85` |
| bundle `production_probe_v1`, minimum policy | 3,459 | `8fdb0321446d6751a2b44c083bd22e1500cfcd395c2d69c46897dbc82f507c8e` |
| bundle `production_probe_v1`, maximum policy | 3,549 | `0681a5c0873f59328c89b433116974388074995efc66daa3a43aaac96fed3808` |
| bundle `unmapped_prose`, minimum policy | 2,805 | `0ee5d589be02c30197e70efa20f89f1e28be7cd5535394d3c590c6ed5a365cff` |
| bundle `unmapped_prose`, maximum policy | 2,895 | `bded71010fd823b8bf0e2d44e282643cd9a5b330e3ea08c4626b180b1c20e095` |

The 31,921-U real two-objective maximum is below the 32,000-U build target and
the 40,000-U production cap. The largest full bundle is 4,617 U, below its
8,192-U cap. Eventual implementation acceptance MUST commit the exact vector
generator and assert every byte count and digest above so the serializer,
tables, and tests cannot drift. The temporary R4 authoring generator is not a
repository artifact.

## 7. Deterministic allocation and strictly residual guidance

For one or two objectives, the allocator MUST first build the state-neutral
retrieval projection exactly as if catalog state and supplemental guidance were
absent. Every mandatory corpus result receives the longest source-faithful
prefix that fits `min(full excerpt, 600 canonical string bytes)`. A shorter
source is returned in full. No mandatory result may be shortened below that
allocation to fit another field or guidance.

Residual excerpt depth is also state-neutral: the allocator charges the larger
of the frozen ACTIVE and compact-discovery policy wrappers for every selected
retrieval result, regardless of its current state, then allocates remaining
32,000-U build-proof headroom deterministically by objective order and global
rank, each excerpt at most 2,400 J. It records the resulting depth and
`retrieval_digest` before reading catalog state. Therefore a metadata-only state
flip cannot change excerpts or retrieval identity. A real policy wrapper may
consume less than its conservative charge but never reallocates the released
bytes to corpus text. After policy evaluation, the allocator finalizes compact
bundle digest/reference projections, counters, statuses, warnings, policy
digests, and `corpus_response_digest`. If the conservatively charged mandatory
fields and initial excerpts do not fit, it returns typed
`mandatory_corpus_envelope_too_large`, emits no corpus text, and mints no usable
ID, reference, or receipt.

Only after the corpus serialization and `corpus_response_digest` are fixed
may the allocator attempt supplemental guidance in strictly residual response
headroom. Guidance is all-or-nothing with its warning and fields. If it does not
fit, omit it. It may never shorten or reallocate a corpus excerpt or change any
corpus identity, result, counter, digest, rank, status, or truncation flag. The
only allowed enabled/disabled differences outside the supplemental lane are
deterministic whole-response `serialized_bytes` and `delivery_digest`.

The exact production serializer vectors in section 6.8 prove both maximum
four-result shapes: 3 ACTIVE plus the highest-ranked missing discovery class,
and 1 ACTIVE plus 3 discovery results. The proof swaps the shapes through both
objective positions. Every variable field uses its normative maximum, strings
exercise canonical escaping, compact warnings are complete, and every
mandatory result receives 600 J. The actual two-objective maximum MUST remain
at or below 32,000 U and the production cap remains 40,000 U. The separate
bundle response, not the first-plan result, carries the complete one-to-one
projection before verification. Neither the 600-J allocation,
top-three-plus-missing-class breadth, bundle fetch, nor response caps may be
weakened.

## 8. Gateway batch and authenticated session bounds

The stateless library has no hidden session state and accepts exactly one or
two objectives. It publishes `maximum=2`. It rejects zero and every size above
two atomically before catalog, manifest, README, or document reads, retrieval,
partial results, or state writes. There is no shrink or partial execution.

The gateway independently enforces both current-release authenticated session
ceilings, whichever would be reached first:

- at most 8 distinct objective digests; and
- at most 120,000 UTF-8 bytes of canonical payload admitted unchanged as MCP
  `TextContent.text`, including each payload's final newline.

There is no response-count ceiling. Every first-plan, bundle-fetch, replay,
control, and verification/confirmation delivery charges exactly
`len(TextContent.text.encode("utf-8"))` once to the same authenticated-session
ceiling. Outer transport framing is never charged. Splitting a complete bundle
into its bounded call does not reset or create a ceiling. Exact same-session
objective-digest replay consumes no new digest slot, but returns either the
closed compact replay envelope in section 6.5.1 at no more than 1,024 U and
charges those canonical content bytes, or a full cached canonical payload and
charges its full content bytes. There is no free full replay. The compatibility
error literal `session_wire_budget_exceeded` means this canonical-content
ceiling and does not make outer framing chargeable.

After the exact payload is fixed and before any corpus text is emitted, Kóska
atomically creates `delivery_reservation_v1` and reserves prospective objective
slots and canonical content bytes, or returns a bounded control error containing
no corpus result. The reservation CAS succeeds only when both prospective
predicates are true in the same authenticated-session record:

- `delivered_content_bytes + reserved_content_bytes + payload_bytes <= 120000`;
  and
- the cardinality of distinct objective digests whose slot is admitted or has
  `reservation_count > 0`, after unioning every absent digest in
  `new_objective_digests`, is at most 8.

An idempotent reuse of the same live reservation adds neither bytes nor slots.
Every other concurrent request is tested against the already-reserved bytes and
slots, so in-flight work cannot overshoot either ceiling. Durable admission of
the complete unchanged payload is the single charge point: CAS changes that
reservation from `reserved` to `admitted` and moves its bytes from reserved to
delivered exactly once. The same CAS
decrements each slot's reservation count and marks newly admitted digests;
release decrements the count, removes only an unadmitted zero-count slot, and
revokes every never-admitted claim with the same `issuing_delivery_id`. A
serialization or admission failure CAS-releases it. Recovery after a crash
before reservation finds no record; after reservation it checks the durable
admission record and either completes the exact charge or releases the
reservation; after admission it observes an already charged delivery and
cannot charge it again.

For bundle fetch, `bundle_fetch_receipt_v1` is created only after that bundle's
complete payload is durably admitted. A crash between admission and receipt
creation is reconciled from the admitted `delivery_id` by idempotent CAS; a
crash before admission cannot create fetched state. An idempotent retry with the
same request digest and `delivery_id` reuses the terminal state without another
charge. A later compact or full logical replay receives a new `delivery_id`, is
reserved and charged for its own canonical content, and cannot alter the
original fetch receipt. Expiry recovery applies these same transitions and may
delete only released or terminal records after their bounded audit TTL. Caller
prose, batch splitting, compact versus full replay, or new lead IDs cannot reset
either ceiling. These ceilings are separate from the library's batch=2 and
per-response 40,000-U contract.

## 9. Gateway presentation and operating boundary

Ownership and order in this section are normative for this release. The
runbooks repository owns immutable object loading, all-corpus search, ranking,
closed serialization, and its pure acceptance harness; it owns no authenticated
session state. Kóska owns runbook selection, opaque-reference issuance, quota
accounting, bundle/fetch/replay control state, and first-plan injection in
`tools/session.py:_handle_kd_session_plan`. The backend MAY enforce a separate
contain-or-reject boundary for business-authority writes, but MUST NOT duplicate
the corpus, choose or serialize the first-plan corpus response, sign
caller-selected corpus payloads, or mint its session references.

For every first plan, `_handle_kd_session_plan` MUST authenticate and normalize
the objectives, invoke immutable runbooks search and server-claim derivation,
have Kóska mint the opaque handles, supply those handles to the pure runbooks
serializer, fix the exact canonical payload and digests, atomically persist the
claim records with the session-control quota reservation, and durably admit the
canonical `TextContent.text` before invoking
`_runbook_plan_gate`, `_compute_and_record_runbook_plan_impact_signal`,
`_persist_runbook_plan_acceptance`, any plan-file write, or any intent write.
Those business operations remain after successful runbook-first delivery. A
failure before admission performs no Living State, Event Ledger, runbook-debt,
waiver, plan-acceptance, intent, or other business-authority write and follows
the reservation recovery rules in section 8.

The Kóska adapter MUST carry this payload through a dedicated typed result from
`_handle_kd_session_plan` through `koskadeux_server.py` and
`gateway_server.py`. That route bypasses generic `safe_response` prefixing and
truncation and places the canonical payload byte-for-byte in MCP
`TextContent.text`. JSON-RPC, HTTP, MCP-envelope, and request-ID framing may wrap
it but cannot modify or enter its quota. End-to-end tests through all three
layers assert exact text equality, the final newline, no prefix, truncation,
double encoding, or fallback coercion, and one charge of
`len(text.encode("utf-8"))` for first-plan, full replay, bundle, confirmation,
compact replay, verification, and control payloads.

The first planning interaction for a session searches the complete pinned
corpus for every objective and delivers the globally ordered excerpts before
action. Caller-authored paths, sections, attestations, `no_entry_found` prose,
waivers, or lead IDs cannot substitute for server selection.

The gateway merges `candidates` and `discovery_leads` by `relevance_rank` for
display while preserving their separate policy lanes. Discovery warnings
precede their excerpts. Before any verification action for a lead, the gateway
performs and validates the complete bounded bundle fetch; it never asks the
agent to reconstruct requirements from the compact result. Supplemental
guidance, when present, displays after all corpus results and at non-instruction
precedence. The boot payload SHOULD expose the exact pin and 20/81/1 counts but
SHOULD NOT inline the corpus.

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
fixture blob OID, recomputed SHA-256, and measured per-case canonical-content results.
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
   kind-specific immutable identities from the canonical-content table.
6. **Discovery-only hit.** A grandfathered-only hit is a discovery result with
   authoritative gap, not `no_entry_found`, and cannot mint an ACTIVE candidate
   ID.
7. **Archive policy.** An archived hit is visibly `historical_only`, is warned,
   and cannot be confirmed as current instruction.
8. **Authority enforcement.** Non-ACTIVE results, supplemental guidance, caller
   paths/prose/IDs, attestations, and waivers cannot pass consultation or action
   authority validation, discharge debt, or promote content.
9. **Closed canonical-content schema and allocator.** The final canonical
   `TextContent.text`—not a library fragment or outer envelope—enumerates only
   section 6 fields, enforces every per-item,
   count, aggregate, path, heading, identifier, declaration, authority-key,
   match-evidence, warning, adapter, policy, counter, query, batch, object, and
   response maximum, and rejects unknown fields. Every production entrypoint
   constructs the frozen singleton, rejects a non-default limits object, and is
   proven unreachable from every environment, CLI, request, config, plugin, and
   caller override surface. Caller failures precede reads;
   object sizes fail before materialization; manifest validation follows parse.
   Excerpts are truthful canonical prefixes. Mandatory-fields-do-not-fit returns
   typed non-success. Production never exceeds 40,000 U; the real worst-case
   proof is exactly the section-6.8 31,921-U vector and the private 32,001-U
   fault fails as build proof. The omission counter equation passes zero,
   exact 1,999,998, and 1,999,999 overflow tests without clamping. End-to-end
   Kóska/server/gateway tests prove the dedicated typed path preserves every
   canonical payload exactly and bypasses `safe_response` mutation.
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
13. **First plan, control writes, and session ceilings.** First-plan delivery
    includes pinned excerpts and compact opaque bundle identities/references.
    Before its payload is fixed and admitted it performs no Living State, Event
    Ledger, runbook-debt, waiver, plan-acceptance, intent, or other
    business-authority write; only the closed authenticated Kóska session-control
    records may reserve quota and persist claims, accounting, fetch, and replay
    state. Exact-source tests prove `_handle_kd_session_plan` completes
    selection and claim derivation, opaque issuance, handle-supplied pure
    serialization, atomic claim/quota persistence, durable admission, and typed
    first-plan injection in that order before `_runbook_plan_gate`,
    `_compute_and_record_runbook_plan_impact_signal`,
    `_persist_runbook_plan_acceptance`, plan-file writes, and intent writes; the
    backend neither duplicates the corpus nor signs caller-selected payloads.
    Independent gateway tests cover 8 objective digests exact/+1 and
    120,000 canonical `TextContent.text` UTF-8 bytes exact/+1 across first-plan,
    bundle-fetch, verification, control, mixed cached+new batches, split
    batches, compact and full replay, and new lead IDs. Concurrent-reservation
    tests prove the atomic reserved-plus-delivered byte predicate and the
    reserved-or-admitted distinct-slot predicate at exact and +1 boundaries.
    Crash-before/after
    reservation, durable admission, fetch-receipt CAS, confirmation, and replay
    prove release/reconciliation, fetched-state ordering, and exactly-once
    charge per delivery ID. Confirmation tests prove the one legal
    `unconfirmed`-to-terminal CAS, rejection of a second attempt, and immutable
    verification receipts. Splitting the bundle never resets accounting.
    Prospective overflow emits a bounded corpus-free control error.
14. **Every record is searchable.** Grouped exact `path:` probes prove all 102
    records contribute at least one searchable unit, including H1-only
    `session-lifecycle.md`, and that the archive is historical. The same harness
    covers staged refresh, shallow history, missing objects, stale records, and
    atomic pin behavior.
15. **State-neutral retrieval and state-dependent policy.** A metadata-only
    ACTIVE↔grandfathered/archive flip preserves qualification, common score,
    relevance evidence, global rank/order, excerpt bytes/depth, source and unit
    identities, and `retrieval_digest`. It changes every applicable policy,
    candidate/discovery, warning, `corpus_response_digest`, and delivery digest.
    No digest or receipt from the old authority state validates under the new
    state; only the explicitly state-neutral retrieval digest survives.
16. **Buildable verification and independent ACTIVE authority.** A discovery
    lead projects the compact count, bundle digest, and authenticated opaque
    lead/bundle handles backed by complete immutable session-control claims;
    the bounded fetch then returns every 1..3 prose item verbatim, ordered,
    one-to-one in one closed <=8,192-U response before verification. Fetch state,
    created only after complete durable admission, its exact bundle digest, and
    immutable requirement IDs are mandatory for the receipt call; handle
    possession never infers a fetch. Wrong-session, wrong-objective, expired,
    replayed, digest-mismatched, stale-activation, ambiguous, or missing claim
    records fail closed. Mapped positive adapter evidence can confirm; unfetched or
    unmapped prose, unknown adapter, parameter substitution, mapping-digest
    mismatch, missing-one, reused-result, stale evidence, caller prose,
    truncation, omission, or pagination cannot. Every adapter maximum and both
    evidence-policy extremes match section-6.8 vectors. An unrelated
    independently selected ACTIVE candidate that passes existing authority
    policy remains usable without relying on the discovery result.
17. **Warning and precedence.** Every pending/archived excerpt is preceded by
    its exact non-truncatable warning carrying catalog state, risk, ground-truth
    flag, requirement count, bundle digest, and authenticated bundle reference,
    and remains quoted evidence at non-instruction precedence. No full
    requirement is duplicated in the first-plan warning.
18. **Strictly residual supplemental lane.** Repository guidance is absent from
    corpus lanes, has exactly the supplemental schema and exclusions, never
    satisfies breadth or authority, and appears last. Forced-fit and forced-omit
    single and batch tests prove byte-identical corpus projections—including
    result selection, order, fields, warnings, excerpt depths/truncation,
    counters, statuses, and `corpus_response_digest` values—with only supplemental fields and
    deterministic whole-response size/digest allowed to differ.
19. **Exact batch contract and production content.** The library accepts only
    sizes 1 and 2 and rejects 0, 3, 4, and a large batch atomically before any
    corpus/README read, retrieval, partial output, or write. The exact production
    serializer proves the two-objective maximum shapes in both orders, all
    variable fields at normative maxima, complete compact warnings, eight
    possible mandatory corpus identities, 600-J initial excerpts, and maximal
    residual guidance serialize to exactly 31,921 U. The separately committed
    vector generator also proves every bundle adapter/policy shape, maximum
    changed-path control response, 898-U confirmation receipt, 709-U compact
    replay receipt, standalone result, and 32,001-U fault digest. All dedicated
    paths reject unknown fields, and compact replay never exceeds 1,024 U.
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
3. in Kóska `tools/session.py:_handle_kd_session_plan`, land the authenticated
   session-control store, selection, opaque handles, quota accounting, and
   dedicated canonical `TextContent.text` path before the named gate, impact,
   acceptance, plan-file, and intent writes;
4. establish the backend's separate contain-or-reject business-authority write
   boundary without duplicating corpus, selection, serialization, or signing;
5. retire caller-authored gate/debt/waiver writers after exact ordering,
   byte-preservation, crash-recovery, fetch-state, and replay evidence passes;
6. perform the appropriate C→M or metadata-only inventory refresh, fully
   validate and verify remote objects, then atomically CAS old-M→new-M without
   activating C; and
7. promote, merge, or archive pending documents in risk order and restore
   narrowly scoped enforcement only after measured search quality, immutable
   evidence, and non-vacuous validation are in production.

The immediate search release is reversible and grants no new authority.
