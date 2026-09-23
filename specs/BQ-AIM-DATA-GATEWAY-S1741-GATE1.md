# BQ-AIM-DATA-GATEWAY-S1741: Gate 1, rebuild AIM Data as a minimal self-hosted gateway (R3)

**Build Queue entity:** `build:bq-aim-data-gateway-rebuild-s1741` (P0, owner Vulcan).
**Authority:** Max, S1741, 2026-09-23.
- Event Ledger `904bacc0`: AIM Data is narrowed to a gateway plus a Docker sandbox and rebuilt from scratch. MP reviews without a vote.
- Event Ledger `308570bd`: delivery goes through one seller-controlled inbound door, and the public release is licensed Apache 2.0.
- Event Ledger `408f01ae`: D-A accepted for v1 (§11); MP's non-voting review goes through a tooling route, not a CORE change.

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

- **D1. Three functions only.** The gateway does three things and nothing else runs inside the customer's perimeter:
  - (a) it describes seller files to ai.market under the D9 boundary;
  - (b) it serves purchased files directly to the buyer;
  - (c) it reports each delivery to ai.market.
- **D2. The website is the only management surface.** Pairing a gateway, choosing what to list, allAI enrichment and review, pricing, licences, samples, earnings, requests and payouts all happen on ai.market, in the flows every seller already uses. The gateway has no management UI, no login, no admin account and no local database server. Its only local interface is a read-only command-line `preview` (D9) that lets the customer's IT see exactly what would be sent.
- **D3. New codebase and repository.** The repository is `aidotmarket/aim-data-gateway`, public from its first commit under Apache 2.0 (`308570bd`); the product name stays AIM Data. No code is copied from `aidotmarket/aim-data`, though protocol ideas may be reused when rewritten against this spec. The old repository is frozen: security fixes only until retirement (§7), then archived.
- **D4. Delivery goes through one seller-controlled door** (`308570bd`). The gateway listens on one HTTP port. The seller's own IT exposes it to the internet over HTTPS through their reverse proxy or firewall, which terminates TLS. The buyer downloads straight from that address. ai.market never carries, relays, caches or stores the bytes (`data-delivery-p2p.md`, CORE S1). ai.market rejects a door URL that is not `https://`; only the synthetic test harness can bypass this, through an explicit test flag.
- **D5. Two dedicated asymmetric keys.** ai.market signs with two Ed25519 keys:
  - the **permission key**, which signs download permissions;
  - the **listing key**, which signs the instruction that makes a file offerable (D12).

  Both keys are new and dedicated, not the platform key (`app/core/config.py:641`) or the scan-spec key. They are held in KMS or HSM, used only by a signing service outside the web API process, and used by different code paths. The gateway pins both public keys at pairing; rotation and revocation are announced over the control channel, signed by the outgoing key. The current delivery JWT is HS256-signed with the backend `SECRET_KEY` (`app/core/security.py:188`, `:253`; `config.py:115` `SECRET_KEY`, `:119` `ALGORITHM`), and verifying it would require the gateway to hold that secret. That is not acceptable, so the gateway does not use it.
- **D6. Only the customer's own storage, mounted by the customer.** In v1 the gateway reads only folders the customer mounts read-only into the container. It includes no cloud SDK. A customer whose data is in S3 or similar mounts it with their own tool (for example `mountpoint-s3`, `rclone` or `s3fs`) and their own credentials. The install guide documents this. ai.market is never a principal the customer's cloud trusts. (DeepSeek R1 SIMPLER, adopted: this is simpler for Max's "as simple as possible", removes a dependency, and removes a class of credential configuration.)
- **D7. Outbound to one host, inbound on one door.** The only outbound connection is HTTPS to `api.ai.market:443` for the control channel. Inbound, only two things ever arrive at the door: buyer downloads and ai.market's periodic door probe (§3 step 3). There is no other network path, no telemetry, no auto-update and no tunnel. **Enforcement, not just behaviour:** the reference compose file puts the gateway on an internal Docker network whose only route out is a pinned, allowlisting forward proxy sidecar that permits `api.ai.market:443` alone and resolves DNS itself (the gateway has no direct DNS or internet route). The install guide also gives the equivalent host-firewall rule for customers who run the gateway without the sidecar. A compromised gateway process therefore cannot reach a second host. The sidecar is one small pinned image, counted in D11's review budget.
- **D8. Hardened sandbox by default.**
  - The image runs as a fixed non-root UID with a read-only root filesystem, `cap_drop: [ALL]` and `no-new-privileges`. It has no Docker socket and no host networking.
  - Writable state lives on one named volume.
  - Every dependency is pinned by version and hash.
  - Images are signed (Sigstore cosign) with an SBOM (SPDX) and build provenance.
  - Updates happen only when the customer changes the image tag. ai.market can refuse permissions below a minimum version it announces, but it can never change code on the customer's host.
- **D9. Two-phase metadata; structure, never values, and nothing identifying without the seller.**
  - **Phase 1 is automatic, for every file under the configured sources.** For each file the gateway sends:
    - an opaque file id: an HMAC, keyed by a secret generated on the gateway's volume, over the source's configured name and the file's path relative to that source (domain-separated, so identical relative paths in two sources get different ids). Every phase-2 request, offer instruction, permission and serve looks a file up by the tuple (gateway id, file id, SHA-256), never by file id alone;
    - a display name: the alias from the customer's config, or else the neutral default `file-<first 8 of id>.<ext>`, where `<ext>` comes from the detected media type's standard extension (for example `.csv`, `.parquet`), never from the file's own name;
    - size, media type and SHA-256.

    No path, directory name, file name or column name leaves in phase 1.
  - **Phase 2 is one file at a time, only after an explicit seller action.** On the website the seller chooses "describe this file". That page states what will be sent and asks for confirmation. Only then does the gateway send, for that file alone:
    - column names, after the customer's config rename and drop map;
    - inferred types and row count;
    - null rate, to the nearest 5%;
    - distinct count as a bucket (1, 2–10, 11–100, 101–1,000, more than 1,000).

    It never sends cell values, minimums, maximums, top values or free text. Tabular formats in v1 are CSV/TSV, JSON Lines and Parquet. Other media types get phase 1 only.
  - **Public sample.** A public sample is sent only after a separate explicit seller action. It is exactly the bytes the seller chose, a portion of their own data (the CORE v9.19 exception), within the platform's existing sample limits (`SAMPLE_MAX_FILE_BYTES` 64 MiB, `SAMPLE_MAX_TOTAL_BYTES` 256 MiB, `SAMPLE_MAX_FILES` 10 at `app/core/config.py:71-73`).
  - **Preview and audit.** `aim-gateway preview <file>` prints, without sending anything, the exact phase-1 and phase-2 payloads. Every outbound message body is appended to a local audit log.
  - **What allAI works from.** allAI classifies and enriches phase-2 metadata on ai.market, which also feeds corpus capture (`build:bq-structure-metadata-corpus-capture-s1396`). Column names, types, counts and bucketed statistics are enough for classification and dataset matching; values are not needed.
- **D10. Simple pairing.**
  - The seller clicks "Add a gateway" on the website and gets a one-time pairing code valid for 15 minutes. The customer's IT runs the container with that code.
  - The gateway generates its Ed25519 identity key locally, registers the public half, and receives the two ai.market public keys and its gateway id. The private key never leaves the volume.
  - Unpairing revokes the gateway.
  - This replaces the serial, the bootstrap token, the keystore passphrase, the admin account, the OAuth loopback and the Postgres password.
- **D11. Small enough to review.**
  - Target: under 5,000 lines of non-test code and no more than 12 direct runtime dependencies. Anything beyond that is justified at its gate.
  - Proposed language: Go (GLM, Mars and DeepSeek lean the same way): one static binary on a distroless base, a small dependency tree, reproducible builds.
  - Gate 2 confirms Go against evidence: Apache Arrow Go reads the Parquet fixture set correctly. If it does not, Gate 2 switches to Python.
  - The wire contract is language-neutral, with golden byte vectors shared by the Python backend and the gateway (the S1732 preview-contract corpus pattern). This keeps the two sides from drifting.
- **D12. Nothing unlisted can be served, even with the permission key stolen.** The gateway serves a file only if all three hold:
  - (i) it is inside the customer's local offer ceiling, a config glob list that defaults to every configured source and is never set remotely;
  - (ii) it is in the gateway's offerable set. A file enters that set only through an instruction signed by the **listing key** and naming the file id and SHA-256. ai.market sends that instruction when the seller publishes a listing version, and removes it on unlist;
  - (iii) a valid permission signed by the **permission key** names it.

  The gateway checks the permission signature first, then the offerable set, then the ceiling. The permission key cannot add a file to the offerable set, and neither key can change the ceiling. Optional stricter mode: `offer_requires_local_approval: true` makes each file also need `aim-gateway approve <file-id>` run locally.

## 3. How it works

```
 Seller's network                                  │ Internet
 ┌───────────────────────────────┐                 │
 │ folders mounted read-only     │                 │
 │ (local, NFS, or S3 mounted    │                 │
 │  by the customer)             │                 │
 │        │ read-only            │                 │
 │  ┌─────▼──────────────┐  outbound HTTPS only    │   ┌──────────────┐
 │  │  AIM Data gateway   │────────────────────────┼──▶│ api.ai.market │ control plane:
 │  │  (non-root sandbox) │  metadata, receipts     │   └──────▲───────┘ pairing, metadata,
 │  └─────▲──────────────┘                         │          │         permissions, receipts
 │        │ plain HTTP, internal                   │          │ signed permission
 │  ┌─────┴──────────────┐   HTTPS, the one door    │   ┌──────┴───────┐
 │  │ seller's reverse   │◀────────────────────────┼───│    buyer      │
 │  │ proxy / firewall   │   file bytes to buyer    │   └──────────────┘
 │  └────────────────────┘                         │
```

1. **Pair** (D10). The gateway opens its control channel: an authenticated outbound HTTPS long-poll or WebSocket, with every message signed by the gateway key. Gate 2 chooses the transport and decides whether it reuses any existing trust-channel endpoint without the legacy fulfilment handlers.
2. **Describe and list** (D9). The seller sees the gateway's files, under display names, next to their cloud connections on the website. They run phase 2 on the files they want to list, then build listings with the normal flow: allAI enrichment and review, licence, price, optional public sample. A listing version pins each file's id and SHA-256, using the manifest contract kept by `P2P-STORAGE-DELETION-S1737.md` §Keep. Publishing sends the listing-key instruction that makes those files offerable (D12).
3. **Door check.** The seller enters the door URL on the website; it must be `https://` (D4). ai.market fetches `GET <door>/.well-known/aim-gateway` and expects a statement signed by the gateway key that names the gateway id and a fresh nonce. The check runs when the URL is entered, then every 5 minutes, never tied to an order, so the door cannot learn when a buyer is about to arrive. A listing backed by a gateway can be published, and permissions can be issued, only while the latest check is no more than 10 minutes old and passed. The fetch runs from an egress-restricted worker, not the API process. It:
   - resolves the host once and rejects private, loopback, link-local and cloud-metadata ranges;
   - pins the resolved IP for the request;
   - follows no redirects;
   - caps the response at 4 KiB, with a 5-second timeout.

   The check also reads the door's TLS certificate and flags (D-A, §11) an organisation name in the subject, or subject alternative names beyond the door host.
4. **Buy.** After payment the buyer's order page (or the agent API) gets the door URL and one permission per file. Each permission carries the gateway id, order id, listing version id, file id, SHA-256, a `jti`, a start deadline no more than 15 minutes out, and a transfer deadline of the start deadline plus the file size at 1 MB/s, capped at 24 hours. It carries no buyer identity (S1740). **Re-issue:** the buyer can get a fresh permission from the order page for any file whose previous permission expired or closed **without a complete matching receipt** (unused, interrupted, retries exhausted, or past the transfer deadline). The new permission has a new `jti` and the old one stays refused. Partial attempts do not count against the tier's download limit; only a completed download does. A re-issued permission may resume from the byte offset the gateway recorded for that order and file, so a very large file on a slow link completes across several permissions instead of being stranded by the 24-hour cap. Delivery and settlement still wait for one complete matching receipt.
5. **Serve.** The gateway checks D12 in order, and also the audience (its own id) and the deadlines. `jti` rules:
   - The first request that starts serving bytes before the start deadline **binds** the `jti` to that file.
   - Later HTTP Range requests with the same permission are allowed until the transfer deadline, but each byte range is served at most twice. This allows retries and blocks repeated full reads.
   - The `jti` **closes** when every byte has been served at least once, or at the transfer deadline. Closing takes precedence: after close, even a range served only once is refused.
   - **Unlist during a transfer:** a file removed from the offerable set refuses new binds at once. A `jti` that was already bound may finish until its transfer deadline, so a buyer who has paid is not cut off mid-download.
   - The ledger is SQLite on the volume, with a synchronous commit before the first byte of each response, so a restart never un-binds or reopens a `jti`.

   The gateway re-hashes the file while serving the first complete pass. On a mismatch it stops and reports.
6. **Receipt.** The gateway sends a signed receipt (`jti`, bytes served, ranges, SHA-256, times, outcome). A receipt is the seller's evidence, not proof. The file counts as delivered when:
   - a matching receipt has arrived, **and**
   - the buyer has raised no problem during the 48-hour payout hold.

   The order page has a one-click "didn't arrive / file doesn't match", which opens a dispute and freezes settlement (the dispute-hold rule, `build:bq-dispute-hold-gate-s1711`). The order page also offers "Verify file": the buyer picks the downloaded file, it is hashed in the browser, and the result is compared with the listing's SHA-256. The agent API returns the SHA-256 for the agent to check. Neither is required, and neither sends the file anywhere.

## 4. What changes on ai.market

- **Backend (chunk A):**
  - a gateway registry: id, public key, status, version, last seen, door URL, door-check result;
  - pairing codes and the control channel;
  - phase-1 and phase-2 metadata intake into the existing listing and corpus models;
  - the permission and listing signing service with its two keys, and a public key endpoint;
  - listing-key offer and unoffer instructions on publish and unlist;
  - receipt intake connected to delivery, the dispute hold and settlement;
  - the door-check worker;
  - a minimum-version policy.

  Everything is dark behind one flag until chunk E passes.
- **Frontend (chunk C, Mars):**
  - a Gateways page: pair, status, door setup and check with its warnings, unpair;
  - gateway files as a listing source, including the phase-2 "describe this file" confirmation;
  - a "What we receive" panel rendered from the gateway's own audit-log entries relayed over the channel, so the seller sees byte for byte what left;
  - door URL, permissions, "Verify file" and "didn't arrive / doesn't match" on the buyer's order page;
  - the D-A seller acknowledgement.
- **Wire contract frozen at Gate 2 for chunk C:** gateway list and status shape; phase-1 and phase-2 metadata exactly as sent; door-check result and failure reasons; the permission issue and re-issue endpoint with per-file deadlines; the dispute/mismatch hook; the per-seller D-A acknowledgement.
- **Not changed:** Seller Workspace (cloud sellers), vectorAIz, the public sample store, licences, settlement rules.

## 5. Security and trust boundaries (for the customer's CISO and for this review)

- **Inside the perimeter:** only the gateway container. It has read-only access to what the customer mounts, its own volume, one outbound host and one inbound port.
- **What ai.market can do to a gateway:**
  - request phase-2 metadata for a file, only after the seller's explicit action;
  - send listing-key offer and unoffer instructions, within the customer's local ceiling;
  - issue permissions for offerable files;
  - probe the door's `/.well-known/aim-gateway` signed statement;
  - announce key rotation and minimum versions;
  - revoke the gateway.

  It cannot run code, read files outside the configured sources, pull files, change the ceiling or change configuration. The config file, the mounts and the door stay under customer control.
- **What a stolen permission gets:** at most one file of one order, before its deadlines, with each byte range served at most twice.
- **What a stolen permission key gets:** the ability to issue permissions for files already on a gateway's offerable set, which then download from the door. It gives no access to anything not offerable (D12), and it cannot make a file offerable.
- **What stolen permission and listing keys together get:** any file inside the customer's local ceiling. That is why the ceiling is local, and why the optional local-approval mode exists for customers who want no remote path at all.
- **Mitigations:** both keys in KMS or HSM behind a separate signing service; rotation and a revocation list over the channel; the receipt audit trail.
- **Anonymity (CORE P5; Max D-A, §11):** permissions carry no buyer id. What remains:
  - The seller's door sees the buyer's network address, as any direct transfer does. The shipped Seller Workspace route has the same property.
  - The door hostname, and its TLS certificate, are revealed to the buyer after purchase and can identify the seller.

  The website warns the seller before a gateway listing goes live. It asks for a neutral hostname and a domain-validated certificate naming nothing else, and the door check flags certificates that identify an organisation.

## 6. Supply chain and release

The repository is public from its first commit under Apache 2.0. It includes:

- `SECURITY.md`
- a threat model
- a data-flow and egress statement matching §3 and §5
- the list of outbound message types with an example of each, generated from the golden vectors

CI does the following:

- builds reproducibly and checks that two builds give identical image digests
- produces the SBOM and provenance
- signs with cosign keyless (GitHub OIDC)
- runs dependency and image scanning
- runs the golden-vector contract tests against the backend's copy
- fails if the compose file or image drops any hardening from D8

Releases are semantic versions. Compose pins the image by digest.

## 7. Legacy

- **`aidotmarket/aim-data`:** frozen for features at `4f4cc983` (Max, relayed by Mars S1738: "Stop AIM-DATA work. No one is using it."). Security fixes only.
- **Existing installs:** Gate 2 confirms from a production read (activated serials and `aim_nodes`, which had 2 rows at S1737) that no install serves a live listing. Any that does is named and migrated: pair a gateway, re-point the listing to the same SHA-256s, uninstall. If there are none, chunk F follows chunk E with no migration wait.
- **Backend paths removed in chunk F**, under its own deletion spec using the S1737 pattern: legacy trust-channel fulfilment, `_queue_delivery_request`, serial activation and metering, and the AIM Data-only publish routes. vectorAIz's routes stay.
- **`aidotmarket/aim-node`:** already parked (S833). Archived with the old repository.

## 8. Chunks (all built by MP; each gate reviewed by GLM, DeepSeek and Gemini, with MP non-voting where it did not build)

| Chunk | Contents | Owner | Depends on |
| --- | --- | --- | --- |
| A | Backend control plane (§4) | Vulcan | Gate 2 |
| B | Gateway: pairing, config, phase-1/phase-2 description, preview, audit log, channel client, D12 checks, door, `jti` ledger, receipts, hardening | Vulcan | Gate 2 (can run in parallel with A against the frozen wire contract and golden vectors) |
| C | Frontend (§4) | Mars | A |
| D | Repository, CI, signing, SBOM, provenance, security documents, install guide | Vulcan and Mars | B |
| E | Money-path proof in the S1656 test environment: pair, describe, list, buy, download through a real TLS reverse proxy, receipt, hold, settlement, dispute path. Then a production canary with one real seller. | Vulcan and Mars | A, B, C, D |
| F | Legacy removal (separate spec) | either | E |

## 9. Acceptance (Gate 1 level; Gate 2 turns each into tests)

1. A clean host installs with one compose file and one pairing code, and needs nothing else from ai.market.
2. A container scan shows: non-root, read-only rootfs, zero capabilities, no socket, and exactly one outbound hostname observed in a 24-hour soak.
3. **No values or identifiers leave without the seller.** Marker strings are planted in cell values, directory names, file names and column names. Captured outbound traffic and the audit log show zero cell markers ever, and zero path or file-name markers ever. Column-name markers appear only after the phase-2 confirmation for that file, and never when the config drop or rename map covers them. Distinct counts appear only as buckets.
4. A buyer downloads a file through a real TLS reverse proxy. ai.market's logs and storage contain zero bytes of it (the `data-delivery-p2p.md` procedure), and "Verify file" matches.
5. Refused with no bytes sent:
   - replay after close
   - past the start deadline
   - wrong audience
   - tampered signature
   - a file not offerable
   - a file outside the ceiling
   - an offer instruction signed with the permission key
   - an `http://` door URL at registration (422)
6. An interrupted large download resumes with Range and completes. A third serve of the same range is refused. After a container restart, the `jti` is still bound or closed. Two interrupted attempts, and separately an expiry before full coverage, are each followed by a successful authenticated re-issue that resumes and completes, while the old `jti` stays refused. Two sources with the same relative path list as two files and serve only the hash-bound one. Under the reference compose profile, an attempt to reach a second host or an outside DNS server fails while the control channel keeps working.
7. Receipt and 48-hour hold with no dispute lead to delivered, then settlement, in the test environment. "Didn't arrive" freezes settlement. A missing or mismatched receipt leaves the order undelivered.
8. Door check: private, loopback and metadata addresses, redirects and oversized responses are all refused. An OV certificate or extra SANs raise the D-A flag.
9. Unpairing refuses the next permission within one control-channel round trip.
10. Non-test code stays under 5,000 lines with no more than 12 direct dependencies, or the excess is justified at Gate 3. The image is signed, the SBOM and provenance verify, and two independent builds give the same digest.

## 10. Out of scope

- An ai.market-provided hostname or relay for the door.
- Push-to-seller-cloud delivery (Max rejected it for v1).
- Built-in cloud SDKs (D6).
- Buyer-side software beyond the in-browser "Verify file".
- Federated learning.
- Any local UI beyond `preview`, `approve` and a localhost health endpoint.
- Changes to vectorAIz or Seller Workspace.

## 11. Decided by Max

- **D-A: identity exposure through the door. Accepted for v1.** Max S1741: "I agree with your recommendations". The decision is in the Event Ledger as `408f01ae`, under dedupe key `s1741-aim-data-gateway-d-a`.
  - After purchase the buyer learns the door hostname, and the seller's door sees the buyer's network address.
  - Before a gateway listing goes live, the website warns the seller and recommends a neutral hostname.
  - R2 adds, per Mars's peer review: the door's TLS certificate can identify the seller too, so the warning also asks for a domain-validated certificate naming nothing else, and the door check flags one that identifies an organisation (§3 step 3). This makes Max's accepted position actionable without changing it.
  - An ai.market-issued neutral hostname stays out of scope for v1 (§10).

## 12. Round 3 fold log and review questions

**R2 inputs** (all on `833c2dba`):
- GLM `122652`: REQUEST_CHANGES. One MEDIUM (incomplete permissions could not be re-issued), two LOW (file-id uniqueness across sources, egress enforcement) and two NITs (a leftover "AIM Data conduit" phrase in CORE, trailing whitespace).
- DeepSeek `122655`: APPROVE_WITH_NITS. F1 the large-file cap, F2 the sample cap, F3 a line cite, F4 close precedence, F5 "single-use" wording in the amendment.
- Gemini `122657`: APPROVE_WITH_NITS. Re-issue of incomplete transfers, display-name extension, unlist during a transfer.

**Adopted:**
- GLM 1, DeepSeek F1 and Gemini 1: re-issue for any permission that ended without a complete matching receipt, resume from the recorded offset, and partial attempts free (§3 step 4; acceptance 6).
- GLM 2: domain-separated file id and tuple lookup (D9).
- GLM 3: egress enforced by an internal network plus an allowlisting proxy sidecar, with a host-firewall alternative (D7; acceptance 6).
- GLM 4: the amendment also replaces CORE v9.20 lines 64–65 (vectorAIz "the same way AIM Data does" and "the AIM Data conduit").
- GLM 5: whitespace stripped.
- DeepSeek F2: the sample follows the existing platform limits, and the CORE citation is corrected (D9).
- DeepSeek F3: the line cite is fixed (D5).
- DeepSeek F4: close takes precedence (§3 step 5).
- DeepSeek F5: the amendment now says "download permissions signed by ai.market, each for one file of one order".
- Gemini 2: the extension comes from the media type (D9).
- Gemini 3: unlist refuses new binds, and bound transfers may finish (§3 step 5).

**Not adopted:** none.

**Risk questions:** the six questions from R2 stand; please re-answer them only where R3 changes your answer. GLM: confirm your MEDIUM finding is closed. All voters: check the new egress sidecar (D7) against D11 and the "as simple as possible" requirement.

Voters return APPROVE, APPROVE_WITH_NITS, REQUEST_CHANGES or REJECT with SHA-bound findings. MP's response is advisory and not counted.
