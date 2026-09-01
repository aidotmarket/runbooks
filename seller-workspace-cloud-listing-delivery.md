---
title: ai.market Seller Workspace Cloud Listing and Delivery
owner: vulcan
last_verified: '2026-08-31'
aliases:
  - Seller Workspace
  - browser-only cloud seller
  - cloud listing
  - workspace_connection
error_signatures:
  - seller_workspace_disabled
  - seller_workspace_aws_connect_disabled
  - workspace_connection_authorization_unavailable
  - workspace_connection_binding_mismatch
  - workspace_connection_assume_role_denied
  - workspace_connection_provider_outcome_unknown
  - workspace_connection_credential_unavailable
  - workspace_connection_rotation_conflict
  - workspace_connection_revoked
---

# ai.market Seller Workspace Cloud Listing and Delivery

This is the frozen W1 architecture and contract for browser-only sellers whose data is already in a supported cloud. It is a clean-sheet ai.market capability, not Hosted AIM Data. Installed AIM Data remains the path for local directories, private networks, and sellers who require processing in their own infrastructure.

The two products provide equivalent marketplace outcomes through stable contracts. They do not share a runtime, Docker deployment, local database, filesystem, installation identity, or user interface.

Status: W2 candidate, unmerged and undeployed. AWS connect is the only implemented W2 stage in this candidate. The master and AWS provider-stage flags remain off by default, so this document makes no production capability claim. W3 profiling, W5 delivery, Cloudflare R2, and any AIM Data runtime integration remain out of scope and unavailable. Existing `legacy_serial` behavior is unchanged, and the new workspace feature remains off.

## Decisions frozen by W1

1. The browser experience lives in the existing ai.market Seller Workspace.
2. `ai-market-frontend` owns browser presentation. `ai-market-backend` owns durable state, authorization, provider adapters, orchestration, publication, entitlement, audit, and revocation.
3. Profiling runs from the backend repository as a separately deployed, isolated worker on a dedicated queue. It does not run in the web process and does not import the AIM Data runtime.
4. Cloud-provider authority is held only in encrypted server-side references. It is never placed in listing JSON, prompts, URLs, logs, analytics, browser storage, public samples, or buyer grants.
5. New browser sellers use a `workspace_connection` delivery authority and a random, server-stored, per-connection AWS ExternalId. Existing listings keep `legacy_serial` unchanged.
6. allAI receives normalized bounded evidence, not provider credentials, broker authority, or unbounded source content. It may propose; the seller approves the exact first public listing and sample.
7. Before approval, sample bytes are transient. Approval creates only a bounded, immutable, content-addressed public artifact. The full dataset is never persistently copied into or proxied through ai.market.
8. Normal purchased bytes flow directly from the seller's cloud to the entitled buyer. ai.market authorizes the grant but does not proxy the dataset.
9. Provider capabilities are exposed by one backend-owned capability response. The frontend and allAI must not make independent support claims.
10. W2 may implement only the AWS connection foundation described here. R2 implementation remains blocked on the W6 OAuth and authority spike.

## Customer journeys

### Browser seller

1. The authenticated active seller opens Seller Workspace.
2. The seller chooses a provider and completes its one-time authorization ceremony.
3. The backend verifies the delegation and creates an owner-bound connection.
4. The seller selects a bucket and immutable object scope: prefix, explicit objects, or manifest.
5. An isolated job reads only bounded ranges and produces normalized evidence.
6. allAI proposes a simple listing. The seller may optionally use advanced presentation controls.
7. The seller selects a public sample and reviews the exact inert render.
8. The seller confirms a hash-bound listing, sample artifact, price, license, ownership, and privacy declaration.
9. The backend publishes an immutable listing/disclosure/source version.
10. The seller may supersede, pause, withdraw, reconnect, rotate, or disconnect from the browser.

The seller never installs AIM Data and never receives a fabricated AIM Data serial or install token.

### Buyer direct delivery

1. The existing marketplace order route verifies order, buyer, listing version, refund/dispute state, and entitlement.
2. The fulfillment resolver reads the immutable authority kind on that listing version.
3. `legacy_serial` follows the existing path unchanged. `workspace_connection` resolves an owner-bound connection and immutable object scope.
4. The broker mints a short-lived, least-privilege grant or presigned object URL.
5. The buyer downloads directly from the seller's provider. Browser download is the default; a generated command or manifest may be offered for very large purchases.

The buyer never receives the seller's connection authority and cannot ask the broker to broaden a scope.

## State machines

| Resource | States | Required transitions |
|---|---|---|
| Cloud connection | `pending_authorization`, `expired`, `verified`, `disabled`, `revoked`, `error` | Only a verified connection can select or read objects. An initial pending connection whose authorization deadline passes enters the single terminal `expired` state: it cannot verify or be disconnected into another cause, its authorization material is unavailable, and recovery creates a new pending connection. Otherwise, disconnect enters `revoked`, blocks new use immediately, and truthfully reports any residual provider-token lifetime. A revoked record is never revived. |
| Profile job | `queued`, `running`, `succeeded`, `failed`, `cancelled`, `expired` | A lease and immutable input bind every run. Terminal states trigger cleanup. Retry creates a recorded attempt; it cannot broaden scope. |
| Listing/disclosure | `draft`, `ready_for_review`, `approved`, `published`, `paused`, `superseded`, `withdrawn` | Approval is bound to exact hashes. Any material change creates a new draft/version and invalidates prior approval. Pause is reversible discoverability/sale disablement of the same immutable version; withdrawal is terminal for that version. |
| Public sample | transient candidate, approved artifact, superseded, withdrawn | Approval creates an immutable artifact. Mutation of the provider source cannot mutate it. Withdrawal removes public bytes but retains redacted audit hashes and metadata. |

Illegal transitions fail closed and emit a redacted audit event.

Pending-connection expiry is fail-closed at the recorded deadline: authorization retrieval and verification refuse once the deadline has passed, even before cleanup is persisted. W2 performs the atomic cleanup synchronously at every connection lifecycle entry rather than through a background sweeper: set `expired`, destroy the encrypted ExternalId and any unconsumed ceremony material, and keep retrieval and verification unavailable. Retain only the owner/resource identifiers, provider, terminal status, timestamps, immutable binding hashes, and redacted audit references under the existing audit-retention policy; exclude the record from active connections. When that retention expires, the normal retention cleanup may delete the terminal record and non-required redacted references. Cleanup never recreates or redisplays authorization material. A rotation deadline is separate: it discards only that connection's unactivated replacement ExternalId and leaves its previously verified value authoritative.

A published `workspace_connection` listing is sellable only while its referenced connection is `verified`. `disabled`, `error`, and `revoked` make it delivery-unavailable before purchase and prevent new grants; recovery requires reverification or a new connection and a new listing/source version. Existing `legacy_serial` availability continues to use its current rules.

## Contract ownership and physical placement

| Contract or component | Owner | Placement | Failure boundary and test seam |
|---|---|---|---|
| Seller Workspace UI | Frontend | `ai-market-frontend` existing seller dashboard | Browser route and API-contract tests; no provider secret in DOM, storage, telemetry, or error text. |
| Capability registry | Backend | `ai-market-backend` config and API | Provider-stage flags default off. Frontend/allAI render only the backend response. |
| Connection registry and broker | Backend | `ai-market-backend` models, routes, services | Transactional ownership checks, provider adapter fakes, two-seller adversarial tests. |
| Credential custody | Backend security boundary | Envelope-encrypted database fields plus managed/rotatable master key | Ciphertext-only database assertions, key-version rotation, log/trace scans, forced decryption failure. |
| Profiling orchestration | Backend | `ai-market-backend` Celery/Redis control plane | Dedicated queue, leases, idempotency, cancellation, worker-death and cleanup tests. |
| Profiling execution | Backend worker deployment | Isolated container/process, one job per child | Ephemeral tenant/job directory, OS/container resource limits, network allowlist, no web-process temp reuse. |
| Normalized evidence | Backend | Versioned schema and content-addressed evidence record | Deterministic parser fixtures, quota tests, source/data separation, no raw credential fields. |
| allAI preparation | Backend/allAI integration | Existing allAI boundary with a new validated evidence adapter | Schema-constrained output, injection corpus, source-versus-AI attribution, no publication authority. |
| Listing, disclosure, public sample | Backend | Existing listing/version concepts, extended contracts | Exact render/content hashes, immutable version tests, withdrawal and source-mutation tests. |
| Native table presentation | Frontend | TanStack Table bundled into application code if W4 acceptance confirms it | Accessibility, supported-type, safe-cell, bundle, and no-external-service tests. |
| Publication and entitlement | Backend | Existing marketplace services and routes | Dual-authority regression tests, immutable version resolution, existing AIM Data compatibility. |
| Provider delivery | Backend broker plus provider | Short-lived provider grant, direct buyer/provider network path | Entitlement, prefix, expiry, refund, revocation, and direct-network proof. |
| AIM Data | AIM Data team | Existing customer-installed product | No W1/W2 runtime dependency. Only deliberately selected algorithms or test vectors may be ported. |
| Operational documentation | Runbooks | `runbooks` | Updated with the same change as behavior; commit-qualified discovery and failure signatures. |

## Versioned logical records

Field names below are the minimum semantic contract. W2 may choose database syntax but may not weaken ownership, immutability, versioning, or custody.

### `CloudConnection`

- `id`, `seller_id`, `provider`, `status`, authorization expiry, rotation substate, and optimistic `version`.
- Provider account, jurisdiction/region, allowed bucket, and allowed prefix/object ceiling.
- `credential_ref`, credential kind, provider authorization metadata, created/verified/rotated/revoked timestamps.
- Redacted health and last verification result; never a plaintext secret.

### `CloudConnectionCredential`

- Connection and seller binding, provider credential kind, key version, expiry, and rotation timestamps.
- A per-record data-encryption key protected by a managed, rotatable master key; authenticated ciphertext, nonce, and tag only in the database.
- Plaintext may exist only in the minimum server process memory for the authorized provider operation, then is discarded.

The existing global `SECRET_KEY`-derived Fernet helper is not sufficient for new customer OAuth refresh credentials without a versioned envelope-encryption and rotation design.

### `CloudObjectSelector`

- `seller_id`, `connection_id`, bucket, prefix and/or explicit keys, region/jurisdiction.
- Provider version ID or ETag where available, sizes, manifest hash, and selector version.
- Immutable after a job, approval, publication, or grant references it. A changed source creates a new selector/version.

### `ProfileJob`

- Seller, job, connection, selector, explicit purpose, parser profile, state, attempt, lease owner/expiry, quotas, and evidence reference.
- Created/started/finished/expired timestamps and a redacted failure code.
- Idempotency key and immutable input hash. A retry cannot silently change inputs or limits.

### `ListingEvidence`

- Selector/source hash, parser and scanner versions, schema, safe aggregates, sample candidates, deterministic sensitive-data findings, warnings, and provenance.
- Bounded, versioned, content-addressed, and free of provider credentials.
- Raw cells and transient bytes are not logs and are deleted on every terminal path.

### `PublicSampleArtifact`

- Seller/listing/disclosure version, provider/account/connection, bucket/key, provider version or ETag, byte range, source size and hash.
- Approved content hash, artifact size, media type, encoding, parser/render versions, render hash, approval time, withdrawal time, and immutable storage reference.
- The approved bytes are the sole public-custody exception. Withdrawal removes their public reachability; audit preserves hashes and metadata only.

### `ListingDraft` and `DisclosureApproval`

- Seller-owned draft/version, evidence version, source selector, proposed and seller-edited fields, presentation settings, and validation findings.
- Clear attribution of source-derived facts, deterministic computations, allAI proposals, and seller assertions.
- Approval records the exact listing payload hash, exact render hash, public sample hash, disclosure version, price, license, ownership/privacy assertions, actor, and time.

### `DeliveryAuthority` and `ProviderDeliveryGrant`

- Authority kind is exactly `legacy_serial` or `workspace_connection`.
- A workspace authority binds seller, connection, listing/source version, immutable object scope, status, and a random per-connection ExternalId that rotates independently.
- A grant binds order, buyer, listing/version, authority, permitted objects/prefix/actions, issue/expiry time, refund/dispute/revocation state, and one-time/idempotency controls.
- No credential, connection identifier, or broader bucket authority is exposed to the buyer beyond what the chosen provider grant protocol strictly requires.

### `AuditEvent`

- Immutable event ID, time, actor kind/ID, seller, connection, job, listing/version, order/grant, purpose, operation, scope hash, decision, outcome, and redacted evidence reference.
- Credentials, tokens, raw cells, sample contents, and provider responses containing secrets are prohibited.

## Typed broker principals and authorization envelope

| Principal | Allowed operation | Mandatory binding |
|---|---|---|
| Seller connection manager | Connect, verify, list permitted objects, rotate, disconnect | Authenticated active seller and, only during connect, a one-time authorization result bound to state and redirect. |
| Profiling job | Head and read bounded ranges | Seller, job, verified connection, immutable selector, explicit purpose, quotas, lease, and expiry. |
| Marketplace fulfillment service | Mint an entitled delivery grant | Seller, connection, listing/source version, order, buyer, object scope, allowed actions, expiry, and live refund/revocation check. |
| Audit reader | Read redacted evidence | Authenticated support/operator identity, explicit support purpose, and audited resource scope. |
| allAI | Propose listing content | Normalized evidence only. No broker method and no provider authority. |

Every request envelope includes actor kind/ID, owning seller, connection, purpose, operation, immutable scope, expiry, and idempotency key. The broker denies missing, mixed-owner, expired, disabled, revoked, mutable, or broader-than-registered envelopes.

## Provider adapter contract

Adapters implement only:

- connect/verify/disconnect;
- list permitted objects and head one object;
- read a bounded range;
- mint temporary entitled access or presign one object;
- disable/revoke and report residual lifetime.

They return normalized errors and redacted evidence. Provider SDK objects, tokens, and raw errors do not cross into frontend or allAI contracts.

### AWS decision

- Use AssumeRole, exact trust policy, a cryptographically random per-connection ExternalId, and the narrowest feasible role and session policy.
- Bind connection ownership, provider account, role, bucket, prefix, and region at verification. Never accept arbitrary replacements on later operations.
- Preserve the current `legacy_serial` algorithm and listings unchanged. Do not derive the new ExternalId from an AIM Data serial or global application secret.
- Rotation creates a controlled overlap/reverification window for that connection only. Disconnect blocks new assumes immediately.

The W2 trust bootstrap ceremony is fixed as follows:

1. An authenticated active seller creates a pending AWS connection. The backend generates the ExternalId with a CSPRNG, binds it to that seller and connection, records a short authorization deadline, and stores it under the same versioned envelope-encryption boundary as provider credentials. The seller never supplies the ai.market principal or ExternalId.
2. While the connection is pending, an authenticated, owner-only, `Cache-Control: no-store` ceremony response supplies the configured exact ai.market AWS principal, exact trust-policy JSON shape, that connection's generated ExternalId, and a conservative server-derived remaining lifetime. The frontend renders the setup values as copy-only, memory-only text and starts a monotonic countdown from the request start; it does not trust the browser wall clock, chains deadlines beyond the browser's maximum single timeout, and rechecks on visibility and focus after sleep or backgrounding. It clears the values on navigation, completion, expiry, or disconnect. They are prohibited from browser persistence, service workers, URLs, analytics, logs, traces, task payloads/results, prompts, listings, samples, support screens, and buyer grants. If the ceremony cannot be recovered safely, the seller starts a new pending connection.
3. The seller configures the role, then submits role ARN, bucket, prefix, and region to that pending connection exactly once. The prefix must be non-root and bounded and must reject IAM wildcard or variable syntax (`*`, `?`, and `${...}`). The backend derives the AWS account from the role ARN, does not accept a principal or ExternalId from the seller, and assumes only with the principal and generated ExternalId already bound to that connection.
4. Verification pins the configured ai.market principal plus seller, AWS account, role, bucket, prefix, and region as one immutable binding. It changes the connection to `verified` and permanently closes the browser-retrievable bootstrap response. The active ExternalId remains envelope-encrypted server-side for authorized AssumeRole calls and is never redisplayed. Later operations accept only the connection ID and cannot replace any binding; a requested change creates a new pending connection.
   A definitive provider denial records a redacted deny result and permits the browser to use a new idempotency key for a corrected retry. A provider transport, timeout, throttle, or transient service outcome is distinct and unknown: it leaves connection version, lifecycle state, and definitive audit evidence unchanged, returns a fixed no-store response, and keeps the same browser idempotency key. If a same-key retry succeeds, later same-key replays return the committed result without another provider call.
5. Rotation generates and ceremony-displays a new envelope-encrypted ExternalId for that connection only. The seller temporarily permits old and new values, the backend verifies the new value against the same immutable account, role, bucket, prefix, region, seller, and principal, then atomically activates it. Until activation, the old value remains authoritative; after activation, the backend destroys and cannot use or redisplay it. A separate rotation substate records pending verification, old-value removal, completion, or failure. An overlap deadline fails closed, destroys the unactivated replacement, and never affects another connection.
6. If initial authorization expires first, cleanup enters terminal `expired`, destroys its authorization material, and makes both authorization retrieval and verification unavailable. Disconnect cannot replace that terminal cause; the seller must create a new pending connection. Otherwise, disconnect revokes and destroys only the selected connection's active and pending authorization material; it never rotates, revokes, or broadens another connection.

The ExternalId is an owning-seller-visible confidential operational identifier, not a buyer secret or listing field. Two-seller, foreign/revoked-connection, ceremony replay, redaction-scan, rotation-isolation, and unchanged-`legacy_serial` tests are mandatory in W2. The exact ai.market AWS principal is deployment configuration and must be included in deployed-environment verification; it may never be inferred from seller input.

### Cloudflare R2 decision boundary

R2 remains capability-off until W6 proves the exact public OAuth client, scopes, resource binding, token lifecycle, temporary credentials or presigning behavior, and revocation model with a synthetic account. No stored bucket token fallback is authorized without Max's explicit decision.

The OAuth design must cover unique state, exact redirect binding, Authorization Code flow, PKCE versus server-side client-secret choice, one-time code consumption, token audience/TTL, encrypted refresh-token custody, replay denial, seller/account/bucket binding, rotation, disconnect deletion, provider outage recovery, and truthful residual access. A server-side confidential client is the preferred starting hypothesis because ai.market can protect a client secret; W6 must verify it rather than assume it.

## Capability registry and routes

The backend is the single source of truth at `GET /api/v1/seller-workspace/capabilities`. Its response reports each provider and each independently gated stage: `connect`, `profile`, `publish`, and `delivery`, plus a reason/status suitable for truthful UI. In this W2 candidate, only AWS `connect` can become enabled, and only when both the master flag and AWS-connect flag are explicitly on and the connection runtime is ready. `profile`, `publish`, `delivery`, and every R2 stage report `unavailable` with reason `not_implemented`. All stages default off.

Backend configuration starts with master `SELLER_WORKSPACE_ENABLED=false` and provider-stage `SELLER_WORKSPACE_AWS_CONNECT_ENABLED=false`. The response projects those controls and any operational disablement. Frontend code and allAI must not infer support from route presence. R2 controls and later-stage controls remain off and are not W2 implementation scope.

The W2 API surface lives under `/api/v1/seller-workspace`:

| Method and path | W2 behavior |
|---|---|
| `GET /capabilities` | Return the backend-owned stage response. It contains no authorization material and never treats route presence as availability. |
| `POST /connections` | Owner-scoped AWS-only create. Generate a new pending connection, ExternalId, expiry, and exact-principal trust ceremony server-side; accept no seller-supplied principal or ExternalId. |
| `GET /connections` | List only the authenticated seller's connections with redacted health and status. Never return ExternalIds, ciphertext, trust JSON, provider raw errors, or another seller's existence. |
| `GET /connections/{id}/authorization` | Return the owner-only trust ceremony only for a live `pending_authorization` connection or pending rotation. Return unavailable after verification, consumption, expiry, or disconnect. |
| `POST /connections/{id}/verify` | Owner-only initial submission of role ARN, bucket, prefix, and region. Derive and pin the account, verify AssumeRole with the connection's generated ExternalId and configured exact principal, then atomically mark the initial connection verified and close browser retrieval. |
| `POST /connections/{id}/rotate` | Accept `start` to begin an owner-only, connection-local replacement ExternalId ceremony and `complete` to verify and atomically activate it only against the existing immutable binding. The active value remains authoritative until completion succeeds. |
| `POST /connections/{id}/disconnect` | Owner-only, connection-local revocation. Block new use first, destroy this connection's authorization material, preserve redacted audit, and never affect `legacy_serial` or another connection. |

Every mutation requires the active seller capability, authenticated ownership, an idempotency key, optimistic version protection, and a redacted audit event. Foreign IDs receive the same non-enumerating denial as absent IDs. Ceremony-bearing create, authorization, and rotation responses use `Cache-Control: no-store`; the frontend keeps them only in volatile memory and must not persist them in local/session storage, IndexedDB, Cache API/service workers, URLs, telemetry, or error reporting. Connection secrets use versioned envelope encryption at rest and exist in plaintext only for the minimum authorized server operation.

Object listing and W3 profile jobs, W4 listing/sample preparation, W5 publication/delivery, and all R2 routes remain future frozen-contract surfaces, not implemented or available in this W2 candidate. Buyer delivery remains unchanged on the existing `legacy_serial` path; no `workspace_connection` publication or grant issuance is enabled.

## allAI and human authority

| Decision | allAI | Seller |
|---|---|---|
| Propose title, description, category, tags, column labels/order, presentation, and warnings from normalized evidence | May propose | May edit or reject |
| Explain deterministic schema, quality, and disclosure findings | May explain without changing the finding | Reviews |
| Connect storage, broaden scope, rotate, or disconnect | Prohibited | Explicit action required |
| Select what becomes public | May suggest candidates | Explicit selection required |
| Assert ownership, privacy status, license, price, or contractual facts | May ask and draft clearly marked text | Must provide/confirm |
| Approve a public sample or first publication | Prohibited | Exact hash-bound confirmation required |
| Publish a material replacement | Prohibited | New version and confirmation required |
| Mint buyer delivery authority | Prohibited | Marketplace entitlement service only, following seller publication |

Source text remains data. It is never concatenated into system/developer instructions. The allAI adapter sends structured, size-limited evidence with field allowlists and validates the returned schema before storing a proposal.

## Security and custody acceptance matrices

### Cross-tenant authorization

Every W2-W5 test suite must use at least two sellers and foreign IDs for connection, selector, job, evidence, draft, approval, sample, listing version, order, grant, object-list cache, profile-result cache, and response memoization. Test list, read, update, cancel, approve, publish, rotate, disconnect, and grant. Required outcome is a uniform denial with no existence, timing, error-text, audit-detail, pagination, cache-key, cache-hit, or stale-response leak. Every cache key and invalidation path includes the owning seller and immutable resource version.

Support/operator access is separately authorized, purpose-bound, redacted, and audited. Administrator status is not an implicit provider-credential reader.

Connection creation, bootstrap retrieval, verification, and rotation have seller, source-IP/risk, and global rate/concurrency limits plus pending-connection quotas and short expiry. Repeated ceremonies cannot create an unbounded credential, database, provider-call, or audit-log workload. Rate-limit responses do not disclose whether a foreign connection exists.

### Bounded processing

The feature remains off until load tests establish explicit numeric ceilings for objects, bytes, rows, columns, archive members, compression ratio, nesting, CPU, memory, wall time, concurrency per seller/global, retries, and provider spend. These are enforced in the broker and worker, not merely in UI.

One job runs per worker child. Each job has an isolated ephemeral directory, hard resource limits, a lease/timeout, and cleanup on success, parser failure, cancellation, timeout, and worker death. Archives, recursive containers, sparse files, malformed encodings, oversized cells, and decompression bombs fail closed. The web process never reuses profiling temp space.

### Prompt and data injection

- Deterministic format detection, parsing, sensitive-data scanning, and quotas precede allAI.
- Filenames, cells, metadata, READMEs, schemas, archives, and charts are untrusted data.
- Prompts separate instructions from structured evidence; raw source instructions cannot request tools or authority.
- Output is allowlisted, size-limited, schema-validated, provenance-tagged, and never executed.
- Adversarial fixtures include instruction-like cells, tool syntax, data exfiltration requests, Unicode controls, HTML/Markdown, formulas, and overlong content.

### Browser rendering and downloads

- Render seller content as text by default. Sanitize Markdown/HTML with an allowlist; prohibit scripts, event attributes, embeds, raw SVG, active charts, CSS escape channels, and unsafe URL schemes.
- External links require an allowlist policy, visible destination, `noopener`/`noreferrer`, and no automatic navigation.
- Table cells are inert text. Generated CSV neutralizes spreadsheet formula prefixes. Filenames are normalized and cannot contain paths or control characters.
- Downloads set an allowlisted MIME type, safe `Content-Disposition`, `X-Content-Type-Options: nosniff`, size limits, and normalized names. Archives are rejected until an explicit safe archive contract exists.
- Generated shell commands are built from structured argument arrays and a reviewed quoting library, with explicit shell/platform variants. Tests cover quotes, newlines, backslashes, metacharacters, command substitutions, Unicode controls, and overlong arguments. No raw provider value is interpolated into executable text.
- A presigned GET URL is a bearer credential and can normally be replayed until provider expiry; one-time issuance by ai.market is not a claim of provider-enforced one-time use. W5 sets a short maximum TTL, redacts the complete URL from every log/trace/referrer, uses safe response-header overrides and browser cache/referrer policy, defines download-count semantics, and truthfully shows the residual replay window. Tests cover capture/replay before and after expiry.

### Credential and audit custody

- Use versioned envelope encryption and authenticated ciphertext. Decryption is restricted by typed service identity and purpose.
- Do not expose credentials to browser JavaScript, allAI, buyers, analytics, traces, error aggregators, logs, database dumps in plaintext, or support screens.
- Redaction tests scan structured logs, task payloads/results, traces, errors, audit events, and generated artifacts.
- Rotation is independently testable. Loss of the master-key service fails closed and leaves existing provider credentials unreadable, not bypassed.

### Public sample retention and mutation

- Transient candidate bytes use tenant/job isolation, encryption, short TTL, and backup/log exclusion.
- Approval copies only the bounded selected artifact into immutable content-addressed public storage and records source and render hashes.
- Provider mutation, deletion, permission loss, version drift, ETag/hash mismatch, or region change cannot alter an approved artifact. A replacement requires new evidence, disclosure, and approval.
- Withdrawal immediately removes origin authorization and new listing references and triggers CDN purge. It does not claim erasure of copies already downloaded or held in browser/intermediary caches. W4 freezes storage/CDN cache-control and maximum-age values, proves purge behavior, and states the residual cache window truthfully. Audit retains hashes, reasons, actors, and timestamps, not withdrawn sample contents.
- A takedown path can block public access without needing provider authority and preserves legally required redacted evidence under a separately documented retention policy.
- W4 evaluates storage-layer immutability/WORM for approved artifacts. Adoption must preserve the distinction between immutable retained bytes and immediate removal of public reachability; application credentials alone must not be able to overwrite an approved content address.

### Revocation and rollback

- Disconnect disables new profile jobs and buyer grants before provider cleanup begins.
- Existing short-lived grants cannot be recalled beyond provider capability; their maximum residual lifetime and count are displayed truthfully.
- A provider outage never converts to cached broad authority. Operations fail closed and retry only within original scope/idempotency rules.
- Global or provider-stage flags can stop connect, profile, publish, or delivery independently.
- W5 rollback disables new `workspace_connection` publication and grant issuance while preserving every existing `legacy_serial` fulfillment path. It does not rewrite listing authority kinds or require customer migration.

## Reuse, adapt, replace

| Existing component | Decision | Reason and boundary |
|---|---|---|
| Backend seller `require_capability` gate | Reuse | Apply to every Seller Workspace route, then add owner/resource authorization. |
| Backend `Listing` and `ListingVersion` concepts | Adapt | Preserve marketplace identity/versioning; normalize provider connection, source, disclosure, and authority references instead of accepting arbitrary credential metadata. |
| Backend `DisclosureSnapshot` approval hash/version concept | Adapt | Extend to the exact render and content-addressed public sample contract. |
| Existing order, entitlement, refund, and download authorization | Adapt | Preserve buyer surface; insert explicit dual-authority resolver and new grant checks. |
| STS assumer, S3 presigner, session-policy helpers | Adapt | Reuse proven algorithms behind typed broker inputs; remove serial-only assumptions from the new path without changing legacy behavior. |
| Backend Celery/Redis infrastructure | Reuse | Add a dedicated queue and separately deployed isolated worker; do not run untrusted profiling in shared web/task children. |
| Frontend seller dashboard shell | Reuse | Seller Workspace is part of the existing product and identity. |
| React Markdown plus sanitizer | Adapt | Enforce the W1 content allowlist; do not treat current defaults as sufficient evidence. |
| TanStack Table | New bundled dependency, conditional | It is internal application code, not an outside service. W4 adoption requires accessibility, supported-type, safe-cell, and bundle acceptance. |
| AIM Data deterministic parser/scanner algorithms and fixtures | Port selectively | Compare each candidate against the reuse test; copy only bounded, multi-tenant-safe algorithms/tests with provenance. No runtime dependency. |
| AIM Data Docker UI/runtime, local database/filesystem, and installation tenant boundary | Replace | These conflict with the clean-sheet browser service and real multi-tenancy. |
| AIM Data full-object S3 registration | Replace | Central profiling must use bounded ranges/streams and no whole-object persistence. |
| Serial activation for new browser sellers | Replace | Use `workspace_connection`; keep legacy listings unchanged. |
| Existing global-secret HMAC ExternalId for new connections | Replace | Use random, stored, per-connection values with independent rotation. Legacy derivation remains untouched. |
| AIM Data Cloudflare tunnel | Do not reuse | It exposes a local installation and is unrelated to R2 account authorization. |
| Global `SECRET_KEY` Fernet for customer OAuth custody | Replace for this purpose | Use managed, versioned envelope encryption and rotation rather than a single application-secret derivation. |

## Work-unit gates

| Unit | Capability claim allowed only after | Rollback |
|---|---|---|
| W2 AWS foundation | Exact schema/static tests, migration tests, two-seller authorization, encrypted-custody checks, reconnect/rotate/disconnect browser proof, and legacy regression proof | Disable AWS connect; legacy path unchanged. |
| W3 profiling | Numeric quotas from load/adversarial tests, deterministic CSV/JSON/Parquet evidence, injection fixtures, isolated cleanup including worker death, and no whole-object custody proof | Disable profile; retain verified connection management. |
| W4 listing assistant | Safe-render/download/command corpus, allAI authority tests, simple and advanced seller browser proof, exact approval hash, source-mutation and withdrawal tests | Disable generated preparation/presentation; retain manual listing. |
| W5 AWS publication/delivery | Exact deployed SHA, fresh no-install seller journey, entitled buyer direct-storage network proof, negative entitlement/revocation/refund/prefix tests, and existing seller legacy proof | Disable new workspace publication/grants; preserve `legacy_serial`. |
| W6 R2 spike | Synthetic OAuth evidence for every lifecycle/threat row and exact R2 resource authority | No product state; R2 stays off. |
| W7 R2 product | Exact W2-W5-equivalent tests and independent deployed production seller/buyer proof | Disable R2 stages independently; AWS and legacy paths unchanged. |

Static review, tests, migration success, deployment identity, seller browser proof, buyer browser proof, and direct provider/network proof are independent and conjunctive. Queue labels, code presence, API output, or one successful provider cannot substitute for another proof.

Each implementation candidate requires the Max-authorized reviewers to review the same exact digest. The W2 foundation candidate used GLM and Kimi, with CC excluded. For the S1648 Gate 4 issue-channel health repair only, Max explicitly changed the reviewer set to CC and GLM because Kimi was unavailable. Every behavior change updates this runbook and any provider-specific error signatures in the same candidate.

## S1648 Gate 4 evidence and health repair

The exact Gate 3 candidates were merged through the protected repository workflow as backend `a00195534d70357772ea46c341042a58dd47ad58`, frontend `260d37ef83f0157d8ae4fad1656a56e924a882a1`, and runbooks `af12cd3c04d6227afbebfc89752ec378aa684237`. Their reviewed candidate commits remain ancestors of those merge commits. Backend and frontend deployments succeeded with every Seller Workspace and provider flag still off. Focused post-merge verification passed 80 Seller Workspace backend tests, 55 unchanged legacy-delivery tests, 50 frontend tests, TypeScript, ESLint, and all 114 runbook checks.

Production later advanced to backend main `5da8736efa183e9e9ae63c249c1cf229e3406001`, which retains the Seller Workspace merge as an ancestor. At that deployed commit, Alembic reported `s1646_payin_primary_identity` as both current and head, but `/health` was degraded because all six model-owned `issue_channel` tables were absent: `canonical_issues`, `source_records`, `safe_raw_records`, `safe_quarantine_records`, `safe_snapshot_records`, and `dispatch_intents`. The application database confirmed zero tables in that schema. Gate 4 therefore remained in progress even though the automated open-items board called the retained W2 branches certified.

The authorized repair is the forward-only Alembic revision `s1648_issue_channel_repair`. It replays the exact earlier `s1511_issue_channel_queue` definition when the schema is wholly absent, and independently replays the exact later `t2026_000727_provider_num_turns` expansion when that column is absent. The loader pins each historical file's SHA-256, revision identity, and ancestry. An unexpected partial schema or unexpected relation kind stops deployment with a catalog-qualified diagnostic. The repair uses a five-second lock timeout, verifies all six postconditions plus `provider_num_turns`, preserves the original isolated-role ACL matrix, and is idempotent for an already-complete database. Downgrade is intentionally nondestructive because removing a repaired evidence schema could destroy queue state.

Production applies this repair through the normal container entrypoint, `sh scripts/run_alembic_startup.sh && exec uvicorn ...`. Before mutation, the deploy must confirm the existing `AUTHOR_DISPATCH_DATABASE_URL` schema-owner connection and `ISSUE_CHANNEL_APPLICATION_DB_ROLE` role-name inputs are present; the latter must differ from `issue_channel_watcher` and `issue_channel_queue_api`. The migration helper scopes the owner connection to Alembic and preserves the role-name input. Missing, malformed, or dedicated-role input aborts before replay DDL; a nonexistent or superuser application role aborts later inside the same transaction and rolls back all transient DDL. Alembic failure or timeout now aborts application startup; the removed ORM `create_all` fallback cannot create a partial schema. After a successful entrypoint migration, the application's second Alembic check is an at-head no-op.

The first production deployment of the reviewed repair, backend merge `e766f097c77c97b4dfb3db1d4c2a063edbf466a8` / Railway deployment `6567197c-e994-441d-92d7-be1ce3392db3`, failed closed before READY. The production driver returned ordinary-table relation kinds as byte values (`b'r'`), while the round-3 guard compared their string rendering to `r`/`p` and therefore reported all six existing relations as unexpected. The serving predecessor remained active. The follow-up candidate decodes byte-valued `relkind` before the existing allowlist comparison and adds direct acceptance and rejection regressions; it does not broaden accepted PostgreSQL relation kinds.

Health inspection now loads `app.models.issue_channel` through the deterministic model registry and compares schema-qualified model identities against base and partitioned tables in `pg_catalog`. Unlike `information_schema.tables`, that catalog path remains observable through the intentionally privilege-revoked application role. The executed PostgreSQL regression proves the application role has no `issue_channel` schema usage, cannot select from `dispatch_intents`, still reports a complete six-table schema with false drift, and continues to report a missing public model table. The four unrelated registry-inventory omissions (`data_verification`, `data_verification_payin`, `version_notification_outbox`, and `lifecycle_email_send`) remain explicitly outside this repair; Mars-owned data-verification files were not changed.

Round-1 exact-candidate review used only the Max-authorized CC and GLM set. CC returned `APPROVE_WITH_NITS`; GLM returned `REQUEST_CHANGES` because the health query was public-only, startup could fall back to ORM table creation, executed commands were not fully reproducible, and replayed file content was not pinned. Round 2 at backend `4161ffe5023e7d9d488d6bff054dd45d52e59256` was not merged: GLM returned `REQUEST_CHANGES` because privilege-filtered `information_schema.tables` hid the repaired tables from the application role and the lifespan handler still swallowed a raised migration error; its CC review was still queued when the candidate was superseded. Round 3 backend candidate `3d9c1c30e531e21fa4b8742e7b253369b555922a` uses privilege-independent catalog discovery and places migrations outside the tolerant seed/bootstrap boundary. It requires fresh exact-SHA approval from both CC and GLM before merge.

Builder verification for the round-3 candidate uses the repository Python 3.12 environment and these non-secret inputs: `DATABASE_URL=postgresql://test:test@localhost:5432/test` from the test harness and `SERIAL_TOKEN_SECRET=synthetic-s1648-test-only-secret` for legacy token tests. The focused health, repair, startup, and entrypoint selection passed 36 tests with one known inventory test deselected; the guarded-DDL plus repair selection passed 55 with one environment skip; and the Seller Workspace plus legacy delivery/serial selection passed 152 with 57 deselected. Ruff passed on every changed backend file with the repository's inherited `app/main.py` E402 exceptions ignored. `git diff --check` was clean. A wider migration selection had one inherited hard-coded-head assertion expecting `s1599_agent_audit_repair`; a wider VZ serial selection required an unavailable local `test` database role. Neither failure is in the changed behavior, and neither was silently repaired.

Candidate verification includes a real disposable-PostgreSQL replay with restricted-application-role health and ACL checks, a second idempotent upgrade, nondestructive downgrade proof, unexpected-relation refusal, the existing issue-channel migration suites, Alembic guarded-DDL suites, single-head verification, and focused Ruff. The broader model-registry inventory test has an unrelated current-main baseline failure for four modules, including Mars-owned data-verification modules; that baseline is disclosed and excluded from this narrow repair rather than silently changed.

Authorized Chrome reached Google consent and the operator approved identity transmission, but the ai.market OAuth callback returned HTTP 400 and the visible login surface reported `OAuth sign-in failed`. The authenticated connect/reconnect/rotate/disconnect journey and synthetic AWS ceremony therefore remain unproven. No public flag, capability claim, customer credential, or customer data is enabled by this repair.

## Provider references verified for W1

- AWS STS `AssumeRole`: <https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html>
- Cloudflare OAuth client registration: <https://developers.cloudflare.com/fundamentals/oauth/create-an-oauth-client/>
- Cloudflare R2 API tokens: <https://developers.cloudflare.com/r2/api/tokens/>
- Cloudflare R2 temporary credentials: <https://developers.cloudflare.com/r2/api/s3/temporary-credentials/>
- Cloudflare R2 presigned URLs: <https://developers.cloudflare.com/r2/api/s3/presigned-urls/>

These references establish current provider primitives, not product proof. W6 must refresh and verify Cloudflare behavior against a synthetic live account before any R2 claim.

## When it breaks

This candidate is unmerged and undeployed. Diagnose only its W2 AWS connection surface; do not interpret these signatures as production availability.

| Signature | Operator diagnosis | Safe action |
|---|---|---|
| `seller_workspace_disabled` | Master flag is off, its default state. | Confirm the candidate environment and flag source; do not bypass the capability response. |
| `seller_workspace_aws_connect_disabled` | Master may be on, but AWS connect is off or its runtime readiness is false. | Inspect the redacted capability reason and dependency health; leave later stages off. |
| `workspace_connection_authorization_unavailable` | The owner-only ceremony was consumed, the connection is not pending, or it reached terminal `expired`; a foreign ID is intentionally indistinguishable from absent. | Read owner-visible status and redacted audit only. An expired pending connection cannot verify; create a new pending connection. |
| `workspace_connection_binding_mismatch` | Submitted or observed account, role, bucket, prefix, region, seller, or configured principal differs from the immutable connection binding. | Refuse mutation. Correct the AWS role if the intended binding is unchanged; otherwise create a new pending connection. |
| `workspace_connection_assume_role_denied` | AWS refused the exact principal/generated-ExternalId trust ceremony or the least-privilege bucket scope. | Compare the configured principal, redacted role/account, and trust-policy shape. Never print or paste the ExternalId into logs or support channels. |
| `workspace_connection_provider_outcome_unknown` | AWS transport, timeout, TLS, DNS, endpoint handling, throttling, or a transient service error did not produce a definitive verification result. This is not an access denial. | Keep the connection and rotation state unchanged and retry with the same browser idempotency key. Never record the outcome as a definitive deny or expose raw SDK content. |
| `workspace_connection_credential_unavailable` | The versioned envelope key or authenticated ciphertext cannot be resolved or decrypted. | Fail closed; verify key-version/KMS readiness and redacted audit. Never fall back to a global secret or plaintext. |
| `workspace_connection_rotation_conflict` | Rotation state, overlap deadline, or optimistic version changed before activation. | Keep the old verified value authoritative, destroy an expired replacement, and retry only this connection. |
| `workspace_connection_revoked` | Disconnect has terminally revoked the connection and destroyed its authorization material. | Do not verify or revive it. Create a new pending connection; leave other connections and `legacy_serial` unchanged. |

For the frozen later stages, start with the failing resource and state: connection, profile job, evidence, draft/approval, public sample, publication, entitlement, or delivery grant. Record the exact deployed commit, provider, seller-safe resource IDs, purpose, operation, immutable scope hash, feature-stage response, normalized error code, and audit event ID.

1. Confirm the backend capability response. A disabled stage is not a provider failure and must not be bypassed from frontend or allAI.
2. Confirm actor, seller ownership, typed principal, connection status, immutable selector/version, purpose, expiry, idempotency key, and revocation/refund state. Never troubleshoot by substituting another seller or broadening scope.
3. For profiling, inspect the job lease, quota that fired, parser/scanner version, redacted evidence reference, and cleanup result. Do not fetch the full object or copy it into the web process.
4. For publication, compare listing payload, render, public artifact, disclosure, selector, and approval hashes. A mismatch requires a new version and seller approval; never mutate the approved record.
5. For delivery, resolve the explicit authority kind. `legacy_serial` and `workspace_connection` have different identity inputs and neither may silently fall back to the other.
6. For provider failures, use normalized broker evidence and provider request IDs after redaction. Do not print, paste, or send credentials to allAI.
7. On suspected leakage, disable the affected provider stage, revoke/rotate the connection, preserve redacted audit evidence, and follow the incident process. State residual grant lifetime truthfully.
8. On rollback, disable only the failing new stages. Preserve existing `legacy_serial` delivery and do not rewrite customer listings.

The approved W1 architecture continues to define the broader contracts and diagnosis boundaries. This W2 candidate adds only AWS-connection signatures; later-stage provider signatures must wait for their authorized work units.
