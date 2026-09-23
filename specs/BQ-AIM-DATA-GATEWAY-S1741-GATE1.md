# BQ-AIM-DATA-GATEWAY-S1741: Gate 1, rebuild AIM Data as a minimal self-hosted gateway

**Build Queue entity:** `build:bq-aim-data-gateway-rebuild-s1741` (P0, owner Vulcan).
**Authority:** Max, S1741, 2026-09-23.
- Event Ledger `904bacc0`: AIM Data is narrowed to a gateway plus a Docker sandbox and rebuilt from scratch. MP reviews without a vote.
- Event Ledger `308570bd`: delivery goes through one seller-controlled inbound door, and the public release is licensed Apache 2.0.

Max's words: "The only important difference between AIM-DATA and our web based tools for listing on the site, is that AIM-DATA 1. allows a customer who wants to host their own data on their own infrastructure to have a gateway to serve the data., 2. Using docker it is a sandbox and I envision that a sophisticated organization like a pharmaceutical or other large company with a CIOSP will require a sandbox and their own security. I plan to open source it so they can see the code that will go inside the firewall. I want things otherwise to be as simple as possible for the seller to list and maintain their offerings." Then: "I 100% agree with your recommendation. I would be find starting over so we do not deal with legacy code and building it as you suggested."

**Risk class:** customer data, authentication and payments. Gate 1 needs unanimous approval from GLM, DeepSeek and Gemini. MP gives a non-voting review (Max S1741; CORE §4 already allows MP to be dispatched explicitly for review without a vote).

**Constitutional dependency:** this design contradicts current CORE §2 "AIM Data — The Conduit" (a desktop GUI, a developer CLI/SDK/MCP surface, all four marketplace functions, "outbound connections only", an encrypted relay) and the matching §9 frame. The amendment is in [AIM-DATA-GATEWAY-S1741-CORE-AMENDMENT.md](AIM-DATA-GATEWAY-S1741-CORE-AMENDMENT.md). It goes to the same three voters in the same round, and Gate 1 cannot pass unless the amendment passes too. Max has already given his direct approval to the direction (`904bacc0`) and approves the exact wording after the vote (`constitution-amendment.md` E-02).

**Pins (read 2026-09-23):**
- ai-market-backend `75c8be5031669bc807e567c1cfdae17c93bd17e7`
- aim-data `4f4cc98398e8dbcc332d3ac3cb698921c8fb43fb`
- runbooks `fc792e5d4190f154927efc6eef0a6a7559908e2e`
- CORE v9.20, sha256 `2916cb9dcaf162942763faac3db8b1e5e260ce9476da7d0b81b8184238939868`, which equals the boot kernel's `source_constitution_sha256`

**Folds in:** T-2026-000839, step 2 of `runbooks/data-delivery-p2p.md` (replacing the legacy trust-channel stream-to-disk delivery). The gateway's direct delivery replaces it.

## 1. Why

AIM Data exists for one seller: an organisation that keeps its data on its own infrastructure and will run third-party code inside its perimeter only in a sandbox its own security team has inspected. Any seller whose data is already in a supported cloud is served by the website (Seller Workspace, `seller-workspace-cloud-listing-delivery.md`). Current AIM Data at `4f4cc983` fails that seller on both counts that matter:

| Finding at the pin | Evidence |
| --- | --- |
| Too large to review | About 59,800 lines of Python under `app/`, 29,300 of frontend, 31 routers and about 120 service modules. They cover chat and credits, SQL query, PII scanning, OCR and document conversion, a buyer portal, data requests, billing and earnings, and auto-update. Most of it duplicates the website. |
| Host control by default | `docker-compose.aim-data.yml` mounts `/var/run/docker.sock` for one-click update (`app/services/update_service.py`) and adds `cap_add: SYS_PTRACE`. `Dockerfile.customer` has no `USER`, so the app runs as root. |
| Unpinned supply chain | 19 of 91 `requirements.txt` lines are exact pins. `cloudflared` is fetched from `releases/latest` at build time with no checksum. |
| Vendor-trusted cloud access | The S3 connector has the seller create an IAM role that trusts ai.market's AWS account (`AI_MARKET_AWS_ACCOUNT_ID` in compose; `docs/INSTALL.md` "Set up the S3 connector"). |
| Delivery passes through ai.market | Each order is streamed to the backend over the trust channel and written to `/tmp/fulfillment` (`fulfillment_service.py` on the aim-data side, `fulfillment_listener_service.py` `_legacy_handle_*` on the backend). This is the live path that `data-delivery-p2p.md` names as a violation to replace. |
| Not open source | `LICENSE` is Elastic License 2.0. |

Fixing each of these inside the current codebase costs more than rebuilding a gateway whose whole job fits in a few thousand lines. Max chose the rebuild.

## 2. Decisions

- **D1. Three functions only.** The gateway (a) scans seller files where they sit and sends ai.market metadata, plus a public sample only when the seller explicitly selects one; (b) serves purchased files directly to the buyer; (c) reports each delivery to ai.market. Nothing else runs inside the customer's perimeter.
- **D2. The website is the only management surface.** Pairing a gateway, choosing what to list, allAI enrichment and review, pricing, licences, samples, earnings, requests and payouts all happen on ai.market, using the flows every seller already uses. The gateway has no management UI: no login, no admin account, no local database server.
- **D3. New codebase and repository.** A new repository, proposed as `aidotmarket/aim-data-gateway` and public under Apache 2.0 (`308570bd`), keeps the product name AIM Data. No code is copied from `aidotmarket/aim-data`. Protocol ideas may be reused only when rewritten against this spec. The old repository is frozen: security fixes only until the last install is migrated (§7), then archived.
- **D4. Delivery goes through one seller-controlled door** (`308570bd`). The gateway listens on one HTTP port. The seller's own IT exposes it to the internet through their reverse proxy or firewall, which also terminates TLS. The buyer downloads straight from that address. ai.market never carries, relays, caches or stores the bytes (`data-delivery-p2p.md`, CORE S1).
- **D5. Permissions are signed with a public key.** ai.market signs every download permission with an Ed25519 key. The gateway verifies it offline against an ai.market public key pinned at pairing, with rotation announced over the control channel. The current delivery JWT is HS-signed with the backend `SECRET_KEY` (`app/core/security.py:188` `create_delivery_token`), so a gateway could only verify it by holding that secret. That is not acceptable, and the new permissions use a separate asymmetric key. Gate 2 decides whether to reuse the platform Ed25519 key material (`app/core/config.py:641` `PLATFORM_ED25519_PUBLIC_KEY`, and the scan-spec key distributed under `build:bq-data-verification-platform-key-distribution-s1717`) or a dedicated delivery key. A dedicated key is the default.
- **D6. Only the customer's own credentials.** The gateway reads mounted folders read-only, and S3-compatible storage using credentials the customer supplies (an instance or workload role, or its own keys). ai.market is never a principal the customer's cloud trusts.
- **D7. Outbound to one host, plus the door.** The only outbound connection is HTTPS to `api.ai.market:443`, for the control channel. The only inbound connection is the door the seller chooses to expose. There are no other network paths, telemetry, auto-updates or tunnels.
- **D8. Hardened sandbox by default.** The image runs as a fixed non-root UID with a read-only root filesystem, `cap_drop: [ALL]`, `no-new-privileges`, no Docker socket and no host networking. Writable state lives on one named volume. Every dependency is pinned by version and hash. Images are signed (Sigstore cosign) and ship with an SBOM (SPDX) and build provenance. Updates happen only when the customer changes the image tag. ai.market can refuse permissions for a version below a minimum it announces, but it can never change code on the customer's host.
- **D9. Metadata is structure, never values.** For each file the gateway sends its relative path, size, modification time, SHA-256 and media type. For tabular formats (CSV/TSV, JSON Lines, Parquet in v1) it adds column names, inferred types, row count, and per-column null and distinct-count estimates. It sends no cell values, minimums, maximums, top values or free text. A public sample is sent only after an explicit seller action on the website. It is exactly the bytes the seller chose, capped in size, and it is the CORE v9.19 exception. The gateway writes every outbound message body to a local append-only audit log, so the customer can see everything that left. allAI classifies and enriches this metadata on ai.market, which also feeds the corpus capture (`build:bq-structure-metadata-corpus-capture-s1396`).
- **D10. Simple pairing.** The seller clicks "Add a gateway" on the website and gets a one-time pairing code that expires in 15 minutes. The customer's IT runs the container with that code. The gateway generates its Ed25519 identity key locally, registers the public half, and receives the ai.market public key(s) and its gateway id. The private key never leaves the volume. Unpairing on the website revokes the gateway, and ai.market stops issuing permissions for it. This replaces the serial, the bootstrap token, the keystore passphrase, the admin account, OAuth loopback and the Postgres password.
- **D11. Small enough to review.** Target: under 5,000 lines of non-test code and no more than 12 direct runtime dependencies. Anything a later change adds beyond this must be justified at its gate. Implementation language is a Gate 2 decision. Go is proposed (one static binary on a distroless base, a small dependency tree, reproducible builds). Python is the alternative (matches the rest of the estate, and Parquet reading is mature). Reviewers are asked to weigh in (Q5).

## 3. How it works

```
 Seller's network                                  │ Internet
 ┌───────────────────────────────┐                 │
 │ folders / S3 (customer creds) │                 │
 │        │ read-only            │                 │
 │  ┌─────▼──────────────┐  outbound HTTPS only    │   ┌──────────────┐
 │  │  AIM Data gateway   │────────────────────────┼──▶│ api.ai.market │ control plane:
 │  │  (non-root sandbox) │  metadata, receipts     │   └──────▲───────┘ pairing, metadata,
 │  └─────▲──────────────┘                         │          │         permissions, receipts
 │        │ plain HTTP, internal                   │          │ signed permission
 │  ┌─────┴──────────────┐   TLS, the one door      │   ┌──────┴───────┐
 │  │ seller's reverse   │◀────────────────────────┼───│    buyer      │
 │  │ proxy / firewall   │   file bytes to buyer    │   └──────────────┘
 │  └────────────────────┘                         │
```

1. **Pair** (D10). The gateway opens its control channel: an authenticated outbound HTTPS long-poll or WebSocket where every request is signed with the gateway key. Gate 2 chooses between the two and checks whether the existing trust-channel endpoint can serve without the legacy fulfilment handlers.
2. **Scan.** The seller names sources in the gateway's config file (paths and S3 prefixes; the customer's IT owns this file). The gateway indexes them and sends metadata (D9). On the website the seller sees the gateway's files next to their cloud connections and builds listings with the normal flow: allAI enrichment, review, licence, price, optional public sample. A listing version pins each file's SHA-256, using the existing manifest contract kept by `P2P-STORAGE-DELETION-S1737.md` §Keep.
3. **Door check.** The seller enters the public door URL on the website. ai.market calls `GET <door>/.well-known/aim-gateway` and expects a statement signed by the gateway key, naming its gateway id and a fresh nonce. That proves the URL reaches this gateway. A listing backed by a gateway cannot be published until the check passes, and the check re-runs before each permission is issued (cached for at most 5 minutes).
4. **Buy.** After payment the buyer's order page (or the agent API) receives the door URL and one signed permission per file. Each permission carries the gateway id, order id, listing version id, file SHA-256, a single-use `jti`, and an expiry of no more than 15 minutes. It carries no buyer identity (the S1740 anonymity rule). Downloads go straight to the door.
5. **Serve.** The gateway checks the signature against the pinned key, the audience (its own id), the expiry, whether the `jti` is unused (a local ledger on the volume), and whether the SHA-256 matches a file it indexed. It re-hashes the file while streaming. On a mismatch it aborts, and the buyer's client verifies the manifest hash too. HTTP Range resume is allowed within one permission's life.
6. **Receipt.** The gateway sends a signed receipt (`jti`, bytes sent, SHA-256, start and end times, outcome) over the control channel. ai.market marks the file delivered when the receipt matches the permission, and the order when every file is delivered. Settlement, the 48-hour hold and disputes then work as today. A permission that expires unused can be re-issued from the order page, subject to the tier's download limits.

## 4. What changes on ai.market

- **Backend:** a gateway registry (id, public key, status, version, last seen, door URL, door-check result); pairing codes; the control channel; metadata intake into the existing listing and corpus models; the asymmetric permission signer and a public key endpoint; receipt intake connected to order delivery and settlement; a minimum-version policy. Everything ships dark behind one flag until chunk E passes.
- **Frontend:** a Gateways page (pair, status, door setup and check, unpair); gateway files offered as a listing source in the existing listing flow; a "What we receive" panel showing, for each file, exactly what the gateway sent; door URL and permissions on the buyer's order page.
- **Not changed:** Seller Workspace (cloud sellers), vectorAIz, the public sample store, licences, settlement.

## 5. Security and trust boundaries (for the customer's CISO and for this review)

- **Inside the perimeter:** only the gateway container. It has read-only access to what the customer mounts or grants, its own volume, one outbound host and one inbound port.
- **What ai.market can do to a gateway:** ask it for metadata, issue permissions for files the seller listed, announce key rotation and minimum versions, revoke it. It cannot run code, read arbitrary paths, pull files, or change configuration. The config file, the mounts and the door stay under customer control.
- **What a stolen permission gets:** one file of one order, within 15 minutes, once.
- **What a compromised ai.market signing key gets:** the ability to issue permissions for files the seller has already listed, which the attacker could then download from the door. It gives no access to anything unlisted. Mitigations are key rotation over the channel, a revocation list, and a customer option to require a second, gateway-side allowlist of listed files, which is the default. Reviewers are asked whether that is enough (Q2).
- **Anonymity (CORE P5):** the permission carries no buyer id. What remains:
  - The seller's door sees the buyer's network address, as any direct transfer does. The shipped Seller Workspace route has the same property, since the seller's bucket logs see the buyer.
  - The door hostname is revealed to the buyer after purchase and can identify the seller, for example `data.<company>.com`.
  
  Decided (Max, D-A in §11): the website shows the seller this before they enable a gateway listing and recommends a neutral hostname. An ai.market-provided neutral name is out of scope for v1.

## 6. Supply chain and release

The new repository is public from its first commit under Apache 2.0, and it includes:

- `SECURITY.md`
- a threat model
- a data-flow and egress statement matching §3 and §5
- the list of outbound message types with an example of each

CI does the following:

- builds reproducibly and checks that two builds give identical image digests
- produces the SBOM and provenance
- signs with cosign keyless (GitHub OIDC)
- runs dependency and image scanning
- fails if the compose file or image drops any hardening from D8

Releases are semantic versions. Compose pins the image by digest.

## 7. Legacy

- **`aidotmarket/aim-data`:** frozen at `4f4cc983` for features. Security fixes only.
- **Existing installs:** each is migrated by pairing a gateway, re-pointing its listings to the gateway's files (same SHA-256s, so listing versions carry over), then uninstalling. Gate 2 counts the installs from production (`aim_nodes` and activated serials) and names each one.
- **Backend paths removed after the last migration**, in a separate deletion spec using the S1737 pattern: legacy trust-channel fulfilment, `_queue_delivery_request`, serial activation and metering, and the AIM Data-only publish routes. vectorAIz's routes stay.
- **`aidotmarket/aim-node`:** already parked (S833). Archived with the old repository.

## 8. Chunks (all built by MP)

| Chunk | Contents | Depends on |
| --- | --- | --- |
| A | Backend control plane: registry, pairing, channel, metadata intake, permission signer and key endpoint, receipts, flag | Gate 2 |
| B | Gateway: pairing, config, scan and profile (D9), audit log, channel client, door, `jti` ledger, receipts, hardening | Gate 2 (can run in parallel with A against the frozen wire contract) |
| C | Frontend: Gateways page, listing source, "What we receive", buyer order page | A |
| D | Repository, CI, signing, SBOM, provenance, security documents, install guide | B |
| E | Money-path proof in the S1656 test environment: pair, list, buy, download through a real reverse proxy, receipt, settlement. Then production canary with one real seller. | A, B, C, D |
| F | Legacy removal (separate spec) | E plus all installs migrated |

## 9. Acceptance (Gate 1 level; Gate 2 turns each into tests)

1. A clean host installs with one compose file and one pairing code, and needs nothing else from ai.market.
2. A container scan shows: non-root, read-only rootfs, zero capabilities, no socket, and exactly one outbound hostname observed in a 24-hour soak.
3. No cell values leave: a fixture with planted marker strings in every column shows zero markers in the captured outbound traffic or the audit log.
4. A buyer downloads a file through a real TLS reverse proxy. ai.market's logs and storage contain zero bytes of it, checked with the `data-delivery-p2p.md` procedure. The buyer's hash matches.
5. Replay, expired, wrong-audience, tampered-signature and unlisted-file permissions are all refused with no bytes sent.
6. Receipt leads to order delivered, then settlement, in the test environment. A missing or mismatched receipt leaves the order undelivered.
7. Unpairing refuses the next permission within one control-channel round trip.
8. Non-test code stays under 5,000 lines with no more than 12 direct dependencies, or the excess is justified at Gate 3.
9. The image is signed, the SBOM and provenance verify, and two independent builds give the same digest.

## 10. Out of scope

- An ai.market-provided hostname or relay for the door.
- Push-to-seller-cloud delivery (Max rejected it for v1).
- Buyer-side software.
- Federated learning.
- Any local UI beyond a localhost health endpoint.
- Changes to vectorAIz or Seller Workspace.

## 11. Decided by Max

- **D-A: identity exposure through the door. Accepted for v1** (Max S1741, "I agree with your recommendations", recorded in the Event Ledger under dedupe key `s1741-aim-data-gateway-d-a`). After purchase the buyer learns the door hostname and the seller's door sees the buyer's network address. Before a gateway listing is enabled, the website warns the seller and recommends a neutral hostname. An ai.market-issued neutral hostname stays out of scope for v1 (§10).

## 12. Review questions

1. Does anything in §3 or §4 let seller bytes touch ai.market, or let ai.market reach into the customer's systems beyond §5? Automatic REJECT under `data-delivery-p2p.md` if so.
2. Is the key-compromise blast radius in §5 acceptable with the default gateway-side allowlist? What else should be required at Gate 2?
3. Is the metadata boundary in D9 tight enough to keep value leakage out (for example distinct-count estimates on low-cardinality columns, or paths that embed identifiers), and still rich enough for allAI to classify and match datasets for the moat?
4. Max has accepted D-A for v1. Does it conflict with CORE P5 as practised (the Seller Workspace precedent) in a way that must be raised with him again? Is the seller warning enough, or should Gate 2 add anything that costs little?
5. Go or Python for D11, given CISO reviewability, the Parquet and S3 libraries, and our builder and reviewer strengths?
6. SIMPLER / BETTER: is there a smaller design that meets Max's two requirements? In particular, should v1 drop S3 and support mounted folders only, leaving S3 to be mounted by the customer?

Voters return APPROVE, APPROVE_WITH_NITS, REQUEST_CHANGES or REJECT with SHA-bound findings. MP's response is advisory and is not counted.
