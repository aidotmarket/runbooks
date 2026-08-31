# Plan: ai.market Seller Workspace for cloud-hosted data

Author: Vulcan, S1642 (2026-08-31). Status: DETAILED PLAN CANDIDATE. The architectural direction is approved; W1 becomes authorized only when GLM and Kimi sign off on the exact candidate commit. Standalone project. No implementation has started.

## 1. Executive decision

Build the browser-only cloud seller experience as part of the **ai.market Seller Workspace**.

This is a clean-sheet product and architecture. It starts from the capabilities a seller needs and the best browser experience. It is not “Hosted AIM Data,” does not run AIM Data in the cloud, and is not constrained by AIM Data’s Docker runtime, local database, local filesystem, routes, or internal ownership model.

Installed AIM Data remains the product for local directories, on-premises systems, private networks, and sellers who require processing on their own infrastructure. Existing AIM Data is reference material only. An AIM Data component may be reused only when a deliberate comparison shows that reuse is safer, simpler, and easier to support than a clean implementation in the Seller Workspace.

The two experiences must provide equivalent customer outcomes and meet at stable ai.market marketplace contracts. They do not need code, runtime, deployment, or user-interface parity.

Max approved these assumptions on 2026-08-31:

1. The Seller Workspace may transiently inspect bounded sample bytes selected by the seller, provided those bytes are not persistently stored as an unapproved copy.
2. Cloudflare OAuth is preferred. Storing a bucket-scoped customer credential is a fallback that requires Max’s explicit approval.
3. Browser-only delivery may offer an optional command-line path for very large purchases, but neither the seller nor an ordinary buyer may be required to install AIM Data.

Decision evidence: Event Ledger `ba01c046-7b79-4dc6-a133-cd703aa82aa2` records Max's approved direction, the three assumptions, and the instruction that detailed-plan sign-off requires GLM and Kimi, not CC.

## 2. Required customer capabilities

The clean-sheet design must make these outcomes easy:

1. Sign in to ai.market and open the Seller Workspace.
2. Connect a supported cloud account without installing software.
3. Select a bucket, prefix, object set, dataset, and public sample.
4. Inspect the selection safely with bounded reads and enforced resource limits.
5. Have allAI prepare a useful listing and sample presentation from the approved evidence.
6. Use a very simple default listing flow or optional advanced controls.
7. Review the exact public listing and exact public sample before first publication.
8. Publish, update, version, pause, withdraw, reconnect, and revoke from the browser.
9. Deliver purchased data directly from the seller’s cloud to the entitled buyer.
10. Diagnose connection, profiling, listing, publication, and delivery failures from clear evidence and runbooks.

Installed AIM Data must continue to provide equivalent marketplace outcomes for local and private sources, without being pulled into the new browser implementation.

## 3. Ground truth at plan authoring

Pinned planning baselines; every implementation session must refresh them before acting:

- `aidotmarket/aim-data@2998304e555c278fd9da61ec7f2a4ec619b7ce51`
- `aidotmarket/ai-market-backend@da395b690e0022cad3076ddfc659cbd5d367c23d`
- `aidotmarket/ai-market-frontend@f4e6d4356587d71732386fe2a296d60e8c785177`
- `aidotmarket/runbooks@a700431033c8b7879e3e761251cc62a16e3d1dca`

Verified planning facts at the pinned baselines:

- AIM Data is a customer-hosted, Docker-based, single-tenant product. Some ownership checks rely on the installation itself as the tenant boundary. Evidence: `aim-data/app/models/state.py:219`, `app/models/raw_file.py:27`, and `app/models/raw_listing.py:25` at `2998304e...`.
- AIM Data’s current S3 registration path can download a complete object into its local workspace. Evidence: `aim-data/app/routers/s3_connections.py:693` and `:748` at `2998304e...`. That path is unsuitable for central cloud profiling.
- The current AWS marketplace path delegates access through role ARN, bucket, prefix, and an activated serial; ai.market assumes the role and issues temporary credentials or presigned URLs while AIM Data is offline. Evidence: `ai-market-backend/app/services/s3_fulfillment.py:21`, `sts_assumer.py:45`, and `s3_presigner.py:11` at `da395b69...`.
- The current delivery identity is installation-bound: `s3_fulfillment.py:29` requires an activated, seller-owned serial, and `serial_service.py:118` activates it through the AIM Data installation lifecycle. A browser-only seller therefore needs a new delivery-authority path; this is an explicit W1/W2 contract change.
- Repository documentation and earlier live read-only production evidence show Sergey uses the legacy AWS role/bucket/prefix/serial path and that ai.market holds delegated capability rather than his AWS access key. Treat this as a compatibility requirement and refresh it before W2 and W5; do not use the plan text itself as production proof.
- The current AIM Data Cloudflare feature is a tunnel for exposing a local installation. Evidence: `aim-data/app/services/tunnel_service.py:1` at `2998304e...`. It is unrelated to the required R2 seller connection.
- Current official Cloudflare documentation describes OAuth authorization-code flows, R2 API tokens, bucket/path-scoped temporary credentials, and single-object presigned URLs. Whether an ai.market public OAuth client can obtain the exact required R2 resource authority remains unverified until W6.
- TanStack Table is not present in the pinned frontend. If selected in W1, it will be a new open-source dependency bundled into our application code, not an outside service. Accessibility and bundle impact remain acceptance questions.

## 4. Product and custody invariants

Every implementation unit must preserve all of these:

1. **Seller Workspace, not a second product.** The browser journey is a normal ai.market seller capability.
2. **Outcome parity, not implementation parity.** Installed AIM Data and the Seller Workspace meet at versioned marketplace contracts.
3. **No persistent full-dataset custody.** The seller’s complete dataset remains in the seller’s cloud and is not persistently copied into or proxied through ai.market.
4. **Explicit bounded inspection.** Transient reads are limited by bytes, objects, rows, columns, decompression, CPU, memory, time, concurrency, retries, and spend. Temporary material is tenant-isolated, encrypted, TTL-deleted, and excluded from logs and backups.
5. **Direct delivery.** Normal buyer bytes flow from the seller’s S3 or R2 account directly to the buyer. ai.market authorizes the grant but does not proxy the dataset.
6. **Real multi-tenancy.** Every connection, reference, job, temporary artifact, listing draft, approval, version, delivery grant, and audit event is seller-owned and checked on every read and mutation.
7. **Least privilege and revocation.** Provider access is restricted to the narrowest practical bucket, prefix, object, action, seller, and lifetime. Disconnect blocks new grants immediately; any residual temporary lifetime is short and displayed truthfully.
8. **Untrusted source content.** Filenames, schemas, cells, metadata, README text, and archives are data, never instructions. Deterministic parsing and scanning precede allAI.
9. **Exact first-publish approval.** The seller confirms a hash-bound render of the exact listing and exact public sample. Any material change invalidates that approval.
10. **Truthful capability claims.** AWS and R2 support remain independently disabled and unadvertised until their own deployed production journeys pass.
11. **Approved public-sample snapshot.** Before approval, sample bytes are transient. On explicit approval, ai.market may persist only the bounded public sample as an immutable, content-addressed disclosure artifact. This is an approved public copy, not full-dataset custody. Withdrawal removes public access; audit retains hashes and metadata, not the sample contents.

These requirements explicitly carry forward the earlier Kimi concerns: do not reuse single-install ownership assumptions in a multi-tenant service; enforce hard resource limits; isolate untrusted data from allAI instructions; and bind the first-publication confirmation to the exact rendered listing and sample.

## 5. Clean-sheet logical architecture

```text
Seller browser
    |
    v
ai.market Seller Workspace
    |
    +--> Seller control service
    |       - connection registry
    |       - listing drafts and versions
    |       - approvals, audit, revocation
    |
    +--> Capability broker
    |       - AWS adapter
    |       - Cloudflare R2 adapter
    |       - short-lived read and delivery grants
    |
    +--> Isolated profiling jobs
    |       - bounded reads
    |       - deterministic parsing and safety checks
    |       - normalized listing evidence
    |
    +--> allAI listing assistant
    |       - simple listing draft
    |       - optional advanced presentation
    |       - no provider credentials or unbounded raw data
    |
    +--> Marketplace publication and entitlement contracts
            - listing and disclosure versions
            - purchases and delivery authorization
            - direct seller-cloud delivery
```

These are logical components, not predetermined repositories or services. W1 selects their physical placement only after the contracts, failure boundaries, deployment costs, and ownership are reviewed.

The provider adapter contract should remain deliberately small:

```text
connect / verify / disconnect
list_objects
head_object
read_bounded_range
mint_temporary_access
presign_object
revoke_or_disable
```

The broker uses typed principals rather than treating every caller as the seller:

| Principal | Allowed purpose | Required scope |
|---|---|---|
| Seller connection manager | Create, verify, select, rotate, disconnect | Authenticated seller plus one-time verified delegation input during registration |
| Profiling job | Read bounded evidence | Tenant, job, connection, immutable object selector, byte/row/time quota, expiry |
| Marketplace fulfillment service | Mint an entitled buyer grant | Seller, connection, listing/version, order, buyer, permitted objects/prefix, expiry, refund/revocation state |
| Audit reader | Read redacted operational evidence | Explicit operator/support purpose; never provider credentials or sample contents |
| allAI | Prepare listing content | Normalized evidence only; no broker or provider authority |

Every broker request carries actor kind, actor ID, owning seller, connection ID, purpose, operation, immutable object scope, and expiry. Authorization is deny-by-default. Buyers never receive the seller's connection authority and do not call the broker as the seller.

Initial connection registration is the only operation that may accept a one-time role ARN or OAuth authorization result before a connection ID exists. After verification, callers use the persisted owner-bound connection ID and cannot submit arbitrary provider credentials or mix-and-match role, account, bucket, prefix, and key values.

Browser-only delivery uses a new `workspace_connection` delivery authority, not a fabricated AIM Data installation serial. The marketplace contract supports two explicit authority kinds:

- `legacy_serial` preserves Sergey and existing installed AIM Data listings unchanged.
- `workspace_connection` binds a seller-owned cloud connection to a random, server-stored, per-connection ExternalId that can rotate independently.

The fulfillment resolver selects the authority kind from immutable listing/version metadata and applies the same owner, entitlement, scope, expiry, and revocation checks. No browser-only path requires an install token or an AIM Data activation event.

The approved public-sample contract binds provider, account/connection, bucket, key, provider version or ETag, byte range, size, content hash, media type, encoding, parser profile, approved render hash, and disclosure version. Before approval, the sample remains transient. Approval creates an immutable content-addressed public disclosure artifact under explicit sample-size limits. Source mutation, deletion, permission loss, region change, or hash mismatch cannot silently alter that artifact; a replacement requires a new disclosure version and exact approval.

## 6. Component reuse decision

No AIM Data component is presumed reusable. During W1, each candidate is marked `reuse`, `adapt`, or `replace` using the same test:

1. Does it implement a stable marketplace contract rather than a Docker/local-runtime assumption?
2. Is its ownership model explicitly multi-tenant and deny-by-default?
3. Can it operate with bounded streaming/range reads and without whole-object persistence?
4. Is reuse smaller and easier to support than a clean implementation?
5. Can it be tested and deployed independently without coupling browser sellers to installed AIM Data releases?
6. Does it preserve existing AIM Data behavior without a risky shared refactor?

Likely reusable references include the existing AWS delivery contract, listing/publication schemas, entitlement rules, and selected deterministic profiling logic. Likely replacements include the Docker UI/runtime boundary, local filesystem/database assumptions, installation-as-tenant checks, full-object S3 registration, and Cloudflare tunnel code. These are hypotheses to verify, not architecture decisions.

## 7. Two-phase listing experience

### Simple default

The seller connects storage, selects the dataset and public sample, and asks allAI to prepare the listing. The system detects format and schema, computes safe bounded evidence, proposes title, description, category, tags, license prompts, sample presentation, and warnings, then presents one exact review-and-confirm step.

The target is that a cooperative seller can point allAI at a public sample and allAI performs the listing preparation correctly. allAI may prepare and revise; the seller remains responsible for the exact first public disclosure.

### Optional advanced controls

Sophisticated providers may control column visibility, ordering, labels, formats, statistics, notes, filters, charts, downloadable sample artifacts, and disclosure choices. Advanced controls extend the same listing model; they do not create a second workflow.

TanStack Table is the default implementation candidate for tabular presentation because it is application code under our control, but the W1 architecture decision must still confirm accessibility, supported data types, bundle impact, and the boundary between table rendering and deterministic data profiling.

## 8. Work plan by session

Each work unit is a safe session boundary. A later unit does not absorb unfinished work from an earlier unit. Every session refreshes ground truth, freezes scope, works on dedicated branches/worktrees, runs focused tests, records exact evidence, updates affected runbooks in the same change, and closes only with Max’s consent.

### W0 — Immutable detailed-plan approval (current step; no implementation)

- Commit this plan as an immutable candidate with exact repository, base, candidate, file, diff, environment, and verification evidence.
- Give GLM and Kimi the same candidate commit and the same numbered failure-mode questions.
- Incorporate every blocking concern and repeat review if the candidate changes.
- Do not involve CC; Max explicitly selected GLM and Kimi as the required sign-off set.

Acceptance: GLM and Kimi each sign off on the same exact plan commit and state that it is safe and sufficiently complete to begin W1. Dispatch success, a partial review, or approval of an earlier digest is not acceptance.

### W1 — Capability architecture and contract freeze (one session)

- Map the required customer outcomes and both seller journeys without using AIM Data internals as the starting point.
- Define versioned contracts for cloud connection, typed broker principals, immutable object selection, bounded evidence, approved public-sample snapshot, listing draft, disclosure approval, publication, provider delivery authority, revocation, and audit.
- Freeze the installation-less seller identity: `workspace_connection` delivery authority with random, server-stored, per-connection ExternalId and independent rotation; preserve `legacy_serial` for existing listings.
- Define failure boundaries, data classification, retention, ownership, and the allAI/human authority matrix.
- Freeze public-sample mutation, withdrawal, takedown, retention, provider-version, hash-revalidation, region-change, and immutable-artifact behavior.
- Produce an OAuth lifecycle threat matrix covering state, redirect binding, PKCE versus server-side client secret, one-time code use, token audience, refresh-token custody and replay, seller/account/bucket binding, disconnect deletion, rotation, and provider outage recovery.
- Define safe browser-rendering and artifact-download rules for HTML/Markdown, links, SVG/charts, spreadsheet formulas, filenames, MIME types, content disposition, sniffing, and archives.
- Apply the reuse decision test to current AIM Data, backend, and frontend components.
- Select logical component placement, repository ownership, service boundaries, and feature flags.
- Produce cross-tenant, resource-limit, prompt-injection, custody, revocation, rollback, and capability-claim acceptance matrices.
- Submit the resulting specification to GLM and Kimi for independent review. CC is not required for this project unless Max later changes the reviewer set.

Acceptance: Max receives one reviewed architecture package that names every resource, authorization decision, contract owner, repository, test seam, failure mode, rollout gate, and reuse/replacement decision. No production or schema change.

### W2 — Seller Workspace and AWS connection foundation (one session)

- Build the browser Seller Workspace shell and owner-bound connection lifecycle selected in W1.
- Implement AWS connect, verify, select bucket/prefix, reconnect, rotate, and disconnect around AssumeRole.
- Implement the `workspace_connection` delivery authority and random per-connection ExternalId without creating an AIM Data serial or install token; keep `legacy_serial` compatibility.
- Keep provider authority in server-side encrypted references; never put credentials in listing JSON, prompts, URLs, logs, analytics, or browser storage.
- Add immutable redacted audit events and adversarial two-seller authorization tests.
- Preserve Sergey’s current listing and fulfillment path without a manual customer rewrite.

Acceptance: two synthetic sellers cannot enumerate or use each other’s connections; a seller with no AIM Data installation or activation event can connect and revoke S3 entirely in the browser; rotating one connection's ExternalId does not affect any other connection; existing AWS delivery remains unchanged.

Rollback: disable the Seller Workspace AWS flag and retain the existing fulfillment path.

### W3 — Isolated bounded profiling and evidence (one session)

- Implement ephemeral, tenant-isolated profiling jobs that read only bounded ranges/streams.
- Enforce object, byte, row, column, archive, decompression, CPU, memory, time, concurrency, retry, and spend limits.
- Produce one normalized evidence bundle for schema, safe statistics, sample candidates, provenance, hashes, warnings, and deterministic sensitive-data findings.
- Prove cleanup on success, failure, timeout, cancellation, and worker death.
- Keep source content separated from instructions and exclude credentials, sample content, and raw cells from logs.

Acceptance: supported CSV, JSON, and Parquet samples produce deterministic bounded evidence; hostile and oversized inputs fail safely; no whole object or cross-tenant artifact persists.

Rollback: disable cloud profiling while retaining connection management and existing marketplace behavior.

### W4 — allAI listing assistant and two-phase presentation (one session)

- Implement the simple “select, prepare, review, confirm” flow.
- Add optional advanced controls without making them prerequisites.
- Add the native TanStack Table sample presentation if W1 confirms it.
- Constrain allAI to normalized evidence and validated outputs.
- Add deterministic sensitive-data and statistical-disclosure checks, prompt-injection containment, exact render hashing, and explicit first-publish confirmation.
- Persist only the explicitly approved bounded public sample as an immutable content-addressed disclosure artifact; bind its source/version/hash/parser/render metadata and implement withdrawal and replacement behavior.
- Render seller-controlled content as inert data and make generated/downloadable artifacts safe against script, link, SVG, MIME-sniffing, filename, archive, and spreadsheet-formula attacks.

Acceptance: a seller-designated public sample produces a useful listing through the simple flow; advanced controls remain optional; every vector in the W1 prompt-injection and browser-content matrices fails closed; source mutation cannot change the approved public artifact; any replacement or material listing/sample change requires a new disclosure version and approval.

Rollback: disable generated preparation/presentation and retain manual listing editing; no published listing changes silently.

### W5 — Publication, AWS buyer delivery, and production proof (one or two sessions)

- Publish through the stable marketplace contract with exact listing, disclosure, source, and approval versions.
- Resolve `legacy_serial` and `workspace_connection` authority kinds explicitly; never make browser-only sellers pass an installation-serial check.
- Issue browser-compatible presigned downloads or manifests for ordinary purchases.
- Offer optional temporary credentials or generated commands for very large multi-object purchases.
- Enforce entitlement, version, prefix, expiry, refund/dispute, download limits, and revocation before each new grant.
- Prove AIM Data is offline and dataset bytes do not traverse or persist in ai.market during delivery.

Acceptance: a fresh synthetic seller with no AIM Data serial, install token, or activation event completes connect through publish in an authorized browser; an entitled buyer downloads directly from S3; expired, revoked, refunded, foreign, wrong-principal, and out-of-prefix access fails; Sergey’s existing legacy-serial delivery still works.

Exit gate: AWS may be described as browser-only only after exact deployed-SHA and independent production journey proof.

### W6 — Cloudflare OAuth/R2 authorization spike (one session, no product claim)

- Register a synthetic Cloudflare OAuth client and prove the authorization-code browser flow.
- Prove unique state and redirect binding, the selected PKCE/client-secret model, one-time code consumption, token audience and TTL, encrypted refresh-token custody, replay denial, rotation, disconnect deletion, and provider-outage recovery.
- Bind Cloudflare identity, account, bucket, and granted scope to the authenticated ai.market seller; reject wrong-account, wrong-bucket, foreign-seller, unsupported-scope, and account-wide fallback cases.
- Determine whether the granted OAuth authority can be restricted to the required R2 account/bucket resources and safely support the broker’s operations.
- Prove list, head, bounded range read, temporary credentials, presigned GET, disconnect, parent revocation, and residual-token behavior against a synthetic R2 bucket.
- Compare OAuth, an encrypted bucket-scoped parent token, and a seller-owned Worker/binding against custody, revocation, UX, and support requirements.
- Verify endpoints, jurisdiction behavior, CORS, pagination, rotation, audit, redaction, and failure messages.

Decision gate:

- Select OAuth only if the spike proves the required revocable least privilege.
- If it does not, stop and present the exact residual risk to Max.
- A stored bucket-scoped credential remains unauthorized until Max explicitly approves it.
- A seller-owned Worker/binding remains the strict-custody alternative.

Acceptance: a signed spike report with exact provider evidence and one selected authorization model; adversarial OAuth tests reject invalid state/redirect, replayed code/token, wrong account/scope/bucket, foreign seller, disconnected authority, and parent-token exposure. No public or internal claim that R2 is supported.

Current provider references:

- <https://developers.cloudflare.com/fundamentals/oauth/create-an-oauth-client/>
- <https://developers.cloudflare.com/r2/api/tokens/>
- <https://developers.cloudflare.com/r2/api/s3/temporary-credentials/>
- <https://developers.cloudflare.com/r2/api/s3/presigned-urls/>

### W7 — Cloudflare R2 seller and buyer journey (one or two sessions)

- Implement the approved R2 connection and capability-broker adapter.
- Reuse the provider-neutral Seller Workspace, profiling, evidence, listing, approval, publication, entitlement, delivery, audit, and revocation contracts.
- Mint exact-scope temporary credentials or presigned URLs; never expose parent authority to buyers, allAI, or browser storage.
- Add provider-specific endpoint, jurisdiction, CORS, pagination, retry, expiry, and revocation handling.

Acceptance: a fresh synthetic R2 seller completes the browser journey; an entitled buyer downloads directly from R2; AIM Data is not installed or running; disconnect blocks new grants; expired access fails; AWS and installed AIM Data regressions remain green.

Exit gate: only independent deployed production proof enables the R2/browser-only capability flag.

### W8 — Hardening, rollout, runbooks, and completion (one session)

- Run the full cross-provider, cross-tenant, hostile-input, resource-exhaustion, authorization, disclosure, delivery, audit, refund, expiry, revocation, and rollback suites.
- Include safe-render and safe-download cases for hostile HTML/Markdown, links, formulas, SVG/charts, filenames, MIME mismatches, content sniffing, and archives.
- Verify monitoring and customer-safe diagnostic messages without data or credential leakage.
- Rehearse provider-specific disablement and rollback without damaging installed AIM Data or existing listings.
- Confirm public copy and allAI only claim capabilities whose provider flags have passed production proof.
- Update the Seller Workspace, AWS, R2, listing, fulfillment, incident, and support runbooks to match the deployed revision.
- Reconcile the standalone project only after exact Git, deployment, browser, provider, and runbook evidence exists.

Acceptance: all completion evidence in section 10 passes and no critical security finding remains open.

## 9. Deliberate non-goals

- Rebuilding, cloud-hosting, or rebranding the AIM Data Docker product.
- Replacing installed AIM Data or forcing local/private sellers to migrate.
- Sharing a single AIM Data instance among multiple sellers.
- Refactoring AIM Data merely to make the two implementations look alike.
- Supporting GCS, Azure, arbitrary S3-compatible stores, databases, or private networks in this project.
- Persistently copying or proxying complete seller datasets through ai.market.
- Fully autonomous first publication without seller confirmation.
- Requiring AIM Data for browser sellers or ordinary buyer downloads.
- Advertising R2 support based only on documentation, provider primitives, or a prototype.

## 10. Evidence required for completion

Static review, deployment, and live journey proof are separate conjunctive requirements:

1. Exact candidate and merged Git SHAs with focused, regression, and adversarial test results.
2. Exact deployed SHAs and healthy schemas, services, queues, workers, and flags.
3. Provider proof of scope, expiry, revocation, and absence of broader permission.
4. Authorized seller browser proof from connection through publication for AWS and R2 independently.
5. Authorized buyer browser proof from purchase through direct download for AWS and R2 independently.
6. AIM Data-not-required proof for the cloud seller and ordinary buyer journeys.
7. Network and storage evidence that complete dataset bytes did not traverse or persist in ai.market.
8. Cross-tenant proof covering enumeration, reads, jobs, artifacts, prompts, drafts, approvals, publication, delivery, caches, retries, and stale jobs.
9. Resource-limit and hostile-content proof, including prompt-injection and decompression cases.
10. Hash-bound first-publication proof and invalidation on material change.
11. Audit evidence containing identity, purpose, scope, hashes, expiry, and outcome but no credentials or sample contents.
12. Disconnect, refund, expiry, and revocation proof with truthful residual-lifetime disclosure.
13. Updated runbooks and public capability copy at the deployed revisions.
14. Independent GLM and Kimi sign-off on the accepted architecture and security model, with any unresolved concern either fixed or explicitly decided by Max. CC is not required unless Max changes the reviewer set.

## 11. Definition of complete

The project is complete only when all of these are proven in production:

- Installed AIM Data still works and retains its local/private custody boundary.
- An AWS seller can connect, select, profile, generate, review, confirm, publish, update, disconnect, sell, and deliver using only the ai.market Seller Workspace.
- A Cloudflare R2 seller can complete the same outcome using the authorization model approved after W6.
- allAI can prepare a useful listing from a seller-designated public sample; the exact first public disclosure remains human-confirmed and hash-bound.
- The simple listing flow is sufficient for a normal seller; advanced controls are optional.
- Ordinary buyers download directly in the browser; large-data buyers may optionally use a generated command without AIM Data.
- The seller’s complete dataset is never persistently stored or proxied by ai.market.
- Cross-tenant, hostile-input, resource-limit, credential, audit, refund, expiry, and revocation controls pass.
- Provider claims shown to users and allAI match only capabilities proven for that provider.

Estimated execution: the current W0 approval step followed by eight bounded implementation units across approximately nine to twelve implementation sessions. W1 may change repository placement and implementation estimates, but not the approved customer capabilities, custody promise, or clean-sheet Seller Workspace decision without Max’s approval.
