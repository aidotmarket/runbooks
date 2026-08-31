---
title: ai.market Seller Workspace Cloud Listing and Delivery
owner: vulcan
last_verified: '2026-08-31'
aliases:
  - Seller Workspace
  - browser-only cloud seller
  - cloud listing
  - workspace_connection
error_signatures: []
---

# ai.market Seller Workspace Cloud Listing and Delivery

This is the frozen W1 architecture and contract for browser-only sellers whose data is already in a supported cloud. It is a clean-sheet ai.market capability, not Hosted AIM Data. Installed AIM Data remains the path for local directories, private networks, and sellers who require processing in their own infrastructure.

The two products provide equivalent marketplace outcomes through stable contracts. They do not share a runtime, Docker deployment, local database, filesystem, installation identity, or user interface.

Status: W1 candidate. No production or database change is authorized by this document. AWS and Cloudflare R2 remain independently disabled and must not be advertised until their provider-specific production gates pass.

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
| Cloud connection | `pending_authorization`, `verified`, `disabled`, `revoked`, `error` | Only a verified connection can select or read objects. Disconnect enters `revoked`, blocks new grants immediately, and truthfully reports any residual provider-token lifetime. |
| Profile job | `queued`, `running`, `succeeded`, `failed`, `cancelled`, `expired` | A lease and immutable input bind every run. Terminal states trigger cleanup. Retry creates a recorded attempt; it cannot broaden scope. |
| Listing/disclosure | `draft`, `ready_for_review`, `approved`, `published`, `superseded`, `withdrawn` | Approval is bound to exact hashes. Any material change creates a new draft/version and invalidates prior approval. |
| Public sample | transient candidate, approved artifact, superseded, withdrawn | Approval creates an immutable artifact. Mutation of the provider source cannot mutate it. Withdrawal removes public bytes but retains redacted audit hashes and metadata. |

Illegal transitions fail closed and emit a redacted audit event.

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

- `id`, `seller_id`, `provider`, `status`, and optimistic `version`.
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

### Cloudflare R2 decision boundary

R2 remains capability-off until W6 proves the exact public OAuth client, scopes, resource binding, token lifecycle, temporary credentials or presigning behavior, and revocation model with a synthetic account. No stored bucket token fallback is authorized without Max's explicit decision.

The OAuth design must cover unique state, exact redirect binding, Authorization Code flow, PKCE versus server-side client-secret choice, one-time code consumption, token audience/TTL, encrypted refresh-token custody, replay denial, seller/account/bucket binding, rotation, disconnect deletion, provider outage recovery, and truthful residual access. A server-side confidential client is the preferred starting hypothesis because ai.market can protect a client secret; W6 must verify it rather than assume it.

## Capability registry and routes

The backend is the single source of truth at `GET /api/v1/seller-workspace/capabilities`. Its response reports each provider and each independently gated stage: `connect`, `profile`, `publish`, and `delivery`, plus a reason/status suitable for truthful UI. All stages default off outside an explicit test environment.

Backend configuration starts with a master `SELLER_WORKSPACE_ENABLED` and explicit provider-stage controls such as `SELLER_WORKSPACE_AWS_CONNECT_ENABLED` and `SELLER_WORKSPACE_R2_DELIVERY_ENABLED`. The response projects those controls and any operational disablement. Frontend code must not infer support from route presence.

Seller routes live under `/api/v1/seller-workspace`:

- `GET /capabilities`;
- `POST|GET /connections`;
- `POST /connections/{id}/verify`, `/rotate`, and `/disconnect`;
- `GET /connections/{id}/objects` with server-enforced pagination and scope;
- `POST|GET /profile-jobs` and `POST /profile-jobs/{id}/cancel`;
- `POST|GET|PATCH /listing-drafts`;
- `POST /public-samples/approve` and `/public-samples/{id}/withdraw`;
- `POST /publish`.

All mutations require an active seller capability, resource ownership, an idempotency key, and an audit event. Buyer delivery remains on the existing order/download surface and calls the dual-authority resolver internally.

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

Every W2-W5 test suite must use at least two sellers and foreign IDs for connection, selector, job, evidence, draft, approval, sample, listing version, order, and grant. Test list, read, update, cancel, approve, publish, rotate, disconnect, and grant. Required outcome is a uniform denial with no existence, timing, error-text, audit-detail, or pagination leak.

Support/operator access is separately authorized, purpose-bound, redacted, and audited. Administrator status is not an implicit provider-credential reader.

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

### Credential and audit custody

- Use versioned envelope encryption and authenticated ciphertext. Decryption is restricted by typed service identity and purpose.
- Do not expose credentials to browser JavaScript, allAI, buyers, analytics, traces, error aggregators, logs, database dumps in plaintext, or support screens.
- Redaction tests scan structured logs, task payloads/results, traces, errors, audit events, and generated artifacts.
- Rotation is independently testable. Loss of the master-key service fails closed and leaves existing provider credentials unreadable, not bypassed.

### Public sample retention and mutation

- Transient candidate bytes use tenant/job isolation, encryption, short TTL, and backup/log exclusion.
- Approval copies only the bounded selected artifact into immutable content-addressed public storage and records source and render hashes.
- Provider mutation, deletion, permission loss, version drift, ETag/hash mismatch, or region change cannot alter an approved artifact. A replacement requires new evidence, disclosure, and approval.
- Withdrawal immediately removes public reachability and new listing references. Audit retains hashes, reasons, actors, and timestamps, not withdrawn sample contents.
- A takedown path can block public access without needing provider authority and preserves legally required redacted evidence under a separately documented retention policy.

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

Each implementation candidate requires GLM and Kimi review of the same exact digest. CC is not part of this project unless Max changes the reviewer set. Every behavior change updates this runbook and any provider-specific error signatures in the same candidate.

## Provider references verified for W1

- AWS STS `AssumeRole`: <https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html>
- Cloudflare OAuth client registration: <https://developers.cloudflare.com/fundamentals/oauth/create-an-oauth-client/>
- Cloudflare R2 API tokens: <https://developers.cloudflare.com/r2/api/tokens/>
- Cloudflare R2 temporary credentials: <https://developers.cloudflare.com/r2/api/s3/temporary-credentials/>
- Cloudflare R2 presigned URLs: <https://developers.cloudflare.com/r2/api/s3/presigned-urls/>

These references establish current provider primitives, not product proof. W6 must refresh and verify Cloudflare behavior against a synthetic live account before any R2 claim.

## When it breaks

Start with the failing resource and state: connection, profile job, evidence, draft/approval, public sample, publication, entitlement, or delivery grant. Record the exact deployed commit, provider, seller-safe resource IDs, purpose, operation, immutable scope hash, feature-stage response, normalized error code, and audit event ID.

1. Confirm the backend capability response. A disabled stage is not a provider failure and must not be bypassed from frontend or allAI.
2. Confirm actor, seller ownership, typed principal, connection status, immutable selector/version, purpose, expiry, idempotency key, and revocation/refund state. Never troubleshoot by substituting another seller or broadening scope.
3. For profiling, inspect the job lease, quota that fired, parser/scanner version, redacted evidence reference, and cleanup result. Do not fetch the full object or copy it into the web process.
4. For publication, compare listing payload, render, public artifact, disclosure, selector, and approval hashes. A mismatch requires a new version and seller approval; never mutate the approved record.
5. For delivery, resolve the explicit authority kind. `legacy_serial` and `workspace_connection` have different identity inputs and neither may silently fall back to the other.
6. For provider failures, use normalized broker evidence and provider request IDs after redaction. Do not print, paste, or send credentials to allAI.
7. On suspected leakage, disable the affected provider stage, revoke/rotate the connection, preserve redacted audit evidence, and follow the incident process. State residual grant lifetime truthfully.
8. On rollback, disable only the failing new stages. Preserve existing `legacy_serial` delivery and do not rewrite customer listings.

This W1 document defines contracts and diagnosis boundaries. Provider-specific operational error signatures must be added when W2/W6 establish real failure codes.
