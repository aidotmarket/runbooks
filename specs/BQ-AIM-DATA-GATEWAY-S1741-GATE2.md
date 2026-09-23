# BQ-AIM-DATA-GATEWAY-S1741: Gate 2, implementation specification (complete draft for R1)

**Build Queue entity:** `build:bq-aim-data-gateway-rebuild-s1741`.
**Design authority:** Gate 1 [BQ-AIM-DATA-GATEWAY-S1741-GATE1.md](BQ-AIM-DATA-GATEWAY-S1741-GATE1.md), approved 3/3 at runbooks `8078d1e40f05734b734299cc0d17b547cd2aff2d` (Event Ledger `fb0d7272`) and merged at `ac8e8ed`. CORE v9.21 (Event Ledger `4349f80f`, `5d1edea7`).
**Reviewers:** GLM, DeepSeek and Gemini vote, and the vote must be unanimous. MP gives an advisory review and does not vote (Max S1741; route live at koskadeux-mcp `e670d015`).
**Status:** complete draft for Council R1. §0–§5 freeze the website ↔ backend contract that chunk C (Mars) builds against, and fold every Gate 1 mandate. §6–§14 cover the gateway internals, the control channel, the keys and signing service, backend data and workers, test plans, the language and dependency budget, legacy installs, chunk order and the review questions. §5 questions are for Mars's peer read.

**Pins:**
- ai-market-backend `53ae0916` (main after licence D)
- ai-market-frontend `6b6862cf`
- runbooks `ac8e8ed`

## 0. Conventions

- **Paths and schemas:** every path is under `/api/v1`. JSON field names are `snake_case`. Times are RFC 3339 UTC.
- **Money:** unchanged; nothing here touches pricing.
- **Errors:** every error is `{"error": {"code": "<stable_code>", "message": "<human text>", "details": {...}}}` with the HTTP status given. Chunk C keys its behaviour on `code`, never on `message`.
- **Flag:** everything is behind `AIM_GATEWAY_ENABLED` (backend setting, default off). When off, every route below answers `404 {"error":{"code":"gateway_disabled"}}`. Chunk C hides the Gateways entry when `GET /gateways` returns that code.
- **Anonymity (S1740, CORE §2):** no response to a buyer names or identifies the seller beyond what the door URL itself reveals (Gate 1 D-A). No response to a seller carries any buyer identifier. Order ids are the only join key, as today.

## 1. Seller surface (seller session auth; the seller owns the gateway)

### 1.1 Pairing and gateway list

| Method and path | Request | Success | Errors |
| --- | --- | --- | --- |
| `POST /gateways/pairing-codes` | `{}` | `201 {"code": "XXXX-XXXX-XXXX", "expires_at": "…"}` (15-minute validity, single use) | `429 pairing_rate_limited` (at most 5 per seller per hour) |
| `GET /gateways` | none | `200 {"gateways": [Gateway]}` | none |
| `GET /gateways/{gateway_id}` | none | `200 Gateway` | `404 gateway_not_found` |
| `PATCH /gateways/{gateway_id}` | `{"name"?: string ≤ 80, "door_url"?: string \| null}` | `200 Gateway` | `422 door_url_not_https`, `422 door_url_invalid`, `404 gateway_not_found` |
| `DELETE /gateways/{gateway_id}` | none | `204` (revoked: no new permissions or offers; the listings it backs are unlisted) | `404 gateway_not_found` |
| `POST /gateways/{gateway_id}/door-check` | `{}` | `202 {"door_check": DoorCheck}` (state `pending`) | `429 door_check_rate_limited` (at most 1 per minute), `409 door_url_missing` |
| `POST /gateways/{gateway_id}/identity-acknowledgement` | `{"acknowledged": true}` | `200 Gateway` (sets `identity_ack_at`) | `422 acknowledgement_required` |

`Gateway`:

```json
{
  "gateway_id": "uuid",
  "name": "string",
  "status": "online | offline | revoked | unsupported",
  "status_reason": "null | egress_open | version_below_minimum | never_connected",
  "version": "semver | null",
  "minimum_version": "semver",
  "last_seen_at": "time | null",
  "egress_check": {"state": "closed | open | unknown", "checked_at": "time | null"},
  "door_url": "https://… | null",
  "door_check": "DoorCheck",
  "identity_ack_at": "time | null",
  "can_publish": true,
  "can_publish_blockers": ["door_check_not_passed", "identity_ack_missing", "status_not_online"]
}
```

`DoorCheck`:

```json
{
  "state": "never | pending | passed | failed",
  "checked_at": "time | null",
  "failure_code": "null | dns_failed | address_not_public | tls_failed | redirect_refused | timeout | bad_signature | gateway_mismatch | response_too_large",
  "certificate_flags": ["organization_in_subject", "extra_subject_alt_names"]
}
```

`status` is `unsupported` whenever the last egress canary result is `open` (Gate 1 D7) or the version is below `minimum_version`. `can_publish` is true only when `status` is `online`, the door check has `passed` within the last 10 minutes, and `identity_ack_at` is set. `certificate_flags` are warnings only and never block publishing (Max D-A). Chunk C shows them next to the D-A notice.

### 1.2 Files and two-phase description (Gate 1 D9)

| Method and path | Request | Success | Errors |
| --- | --- | --- | --- |
| `GET /gateways/{gateway_id}/files?cursor=&limit≤200` | none | `200 {"files": [GatewayFile], "next_cursor": string \| null}` | `404 gateway_not_found` |
| `GET /gateways/{gateway_id}/files/{file_id}` | none | `200 GatewayFile` | `404 file_not_found` |
| `POST /gateways/{gateway_id}/files/{file_id}/describe` | `{"confirm": true}` | `202 GatewayFile` (`description.state` = `requested`) | `422 confirmation_required`, `409 gateway_offline`, `409 already_described` |

`GatewayFile`:

```json
{
  "file_id": "hex",
  "display_name": "string",
  "size_bytes": 0,
  "media_type": "string",
  "content_commitment": "hex",
  "first_seen_at": "time",
  "changed_at": "time",
  "description": {
    "state": "not_requested | requested | described | failed | stale",
    "requested_at": "time | null",
    "described_at": "time | null",
    "sha256": "hex | null",
    "row_count": 0,
    "columns": [
      {"name": "string", "type": "string | integer | float | boolean | date | timestamp | other",
       "null_rate_pct": 0, "distinct_bucket": "1 | 2-10 | 11-100 | 101-1000 | >1000"}
    ],
    "failure_code": "null | unsupported_format | read_error | gateway_timeout"
  },
  "offerable": false,
  "listing_version_ids": ["uuid"]
}
```

- **Phase 1 fields.** `file_id`, `display_name`, `size_bytes`, `media_type`, `content_commitment` and the two times are phase 1. The website never sees a path.
- **Phase 2 fields.** `description.*` is phase 2. It is present only after `describe`.
- **Staleness.** `stale` means the gateway reported a new `content_commitment` after the file was described. The description must be requested again before the file can back a new listing version. Listing versions already published stay bound to their SHA-256 (§2.4).
- **Before confirming.** The confirmation page in chunk C shows this fixed text: "ai.market will receive this file's column names (after your gateway's rename and drop settings), their types, the row count, bucketed null and distinct counts, and the file's SHA-256. It will not receive any values." It also links the customer's IT to `aim-gateway preview <file-id>`, which prints the exact payload locally.

### 1.3 "What we receive" (Gate 1 §4)

| Method and path | Request | Success |
| --- | --- | --- |
| `GET /gateways/{gateway_id}/received?cursor=&limit≤200` | none | `200 {"messages": [ReceivedMessage], "next_cursor"}` |

`ReceivedMessage` = `{"seq": 0, "received_at": "time", "message_type": "hello | inventory | description | receipt | canary_result | revocation_ack", "body": {…}}`. `body` is the message exactly as the gateway sent it (the gateway's own signed audit-log entry, relayed over the channel), rendered verbatim. It never includes the signature bytes. `seq` is the gateway's audit-log sequence, so a gap is visible.

### 1.4 Listing with a gateway source

The existing listing flow gains one source type. Chunk C does not create a separate listing wizard.

```json
"source": {"type": "gateway", "gateway_id": "uuid", "file_ids": ["hex"]}
```

- **Draft rules.** A draft may reference any file. Publishing requires every file to have `description.state = described`, and the gateway to have `can_publish = true`. Otherwise the call fails with `409 gateway_not_publishable` and `details.blockers` (the same codes as `can_publish_blockers`, plus `file_not_described:<file_id>`).
- **Publish.** Publishing records each file's `sha256` on the listing version (the existing manifest contract) and sends the listing-key offer instruction (Gate 1 D12).
- **Unlist.** Unlisting sends the unoffer instruction.
- **Samples and licences.** The public sample and the licence choice use the existing listing surfaces unchanged.

## 2. Buyer surface (buyer session auth; the buyer owns the order)

### 2.1 Delivery view

`GET /orders/{order_id}/gateway-delivery` → `200 GatewayDelivery`. It returns `404 not_a_gateway_order` for an order whose listing version has no gateway source.

```json
{
  "door_url": "https://…",
  "hold": {"until": "time | null", "disputable": true},
  "files": [
    {
      "file_id": "hex",
      "display_name": "string",
      "size_bytes": 0,
      "sha256": "hex",
      "state": "not_started | in_progress | delivered | disputed",
      "coverage_bytes": 0,
      "permission": "Permission | null",
      "reissue": {"allowed": true, "remaining_24h": 5, "blocked_code": "null | complete | rate_limited | gateway_unavailable | order_not_deliverable"}
    }
  ]
}
```

`Permission` = `{"token": "compact JWS", "jti": "uuid", "start_deadline": "time", "transfer_deadline": "time", "download_url": "https://<door>/v1/files/<file_id>", "resume_offset": 0}`.

- **Permission lifetime.** A permission is issued lazily, on the first `GET` after the order is deliverable. It is returned again on later `GET`s until it expires or closes.
- **Download mechanics.** The buyer's browser downloads with `Authorization: Bearer <token>` against `download_url`. Chunk C uses a fetch with a streamed save, or an agent does the same. `Range` is supported.
- **Hold.** `hold.until` is the 48-hour payout hold (the existing `escrow_hold_until`).

### 2.2 Re-issue

`POST /orders/{order_id}/gateway-delivery/files/{file_id}/permissions` → `201 Permission`.

Errors:
- `409 delivery_complete`
- `429 reissue_rate_limited` (5 per file per order per 24 hours; `details.retry_after`)
- `409 gateway_unavailable` (the gateway is not `online`, or its door check is stale)
- `409 order_not_deliverable` (refunded, revoked or disputed)

Order of operations (Gate 1 §3 step 4): send the signed revocation of the old `jti` over the channel, wait for the gateway's idempotent confirmation (at most 10 seconds; otherwise `409 gateway_unavailable`), then issue the new permission with `resume_offset` taken from the gateway's coverage ledger.

### 2.3 Problems and verification

- **Problems.** "Didn't arrive" and "doesn't match" call the existing `POST /orders/{order_id}/dispute` (`orders.py:821`) with `category` `missing_data` or `corrupted` (the existing `DisputeCategory`) and a new optional `file_id`. This freezes settlement exactly as today. Chunk C adds the two buttons per file on the delivery view while `hold.disputable` is true.
- **Verify file.** This runs entirely in the browser, and nothing is uploaded. The buyer picks the downloaded file, chunk C hashes it with a streaming SHA-256 (a WebCrypto-compatible incremental library, in chunks, so large files work), and compares the result with `files[].sha256`.

### 2.4 Delivered state

- **In the view.** A file is `delivered` when the backend holds the complete matching receipt (§3.4). The order is delivered when every file is.
- **Settlement.** Settlement waits for the hold with no open dispute, as today (`escrow_hold_until`, `DisputeCase`).

## 3. Formats shared by backend and gateway (the golden vectors cover all of these)

### 3.1 Permission token

- **Encoding.** Compact JWS, `alg: EdDSA` (Ed25519), `typ: aim-permission+jwt`. `kid` is the permission key id.
- **Claims:**

  | Claim | Meaning |
  | --- | --- |
  | `aud` | gateway id |
  | `oid` | order id |
  | `lvid` | listing version id |
  | `fid` | file id |
  | `sha256` | the file's SHA-256 |
  | `jti` | permission id |
  | `iat` | issued at |
  | `sd` | start deadline (epoch seconds) |
  | `td` | transfer deadline (epoch seconds) |
  | `ro` | resume offset in bytes |

- **No buyer identity.** There is no `sub` and no buyer identifier.
- **Transfer deadline.** `td = sd + ceil(size_bytes / 1 MiB/s)`, capped at `sd + 24 h`.

### 3.2 Offer and unoffer instruction

- **Encoding.** Compact JWS, `alg: EdDSA`, signed with the **listing key**, `typ: aim-offer+jwt`.
- **Claims:** `aud`, `op` (`offer` or `unoffer`), `fid`, `sha256`, `lvid`, `iid` (instruction id, unique), `iat`.
- **Replay protection.** The gateway rejects an `iid` it has already seen, and an instruction whose `aud` is not its own id (GLM R5 Q2 mandate).

### 3.3 Revocation and confirmation

- **Revocation.** Signed with the permission key: `{"op": "revoke", "jti", "aud", "iat"}`.
- **Confirmation.** The gateway signs `{"op": "revoke_ack", "jti", "state_before": "active | expired | closed | unknown"}` with its gateway key. The confirmation always succeeds (Gemini R4).

### 3.4 Receipt (GLM R5 2.5)

The gateway signs this with its gateway key, one receipt per (order, file) state change, and the receipts are cumulative:

```json
{"op": "receipt", "oid": "uuid", "fid": "hex", "sha256": "hex", "size_bytes": 0,
 "jtis": ["uuid"], "coverage": [[0, 1048575]], "covered_bytes": 0,
 "max_serves_reached": [[start, end]], "outcome": "in_progress | complete | aborted_hash_mismatch | aborted_deadline",
 "hash_verified_at_bind": true, "first_byte_at": "time", "last_byte_at": "time", "seq": 0}
```

- **Coverage.** `coverage` is the normalized, merged set of byte intervals served at least once, across every listed `jti`.
- **Complete matching receipt.** A receipt is the complete matching receipt when `outcome = complete`, `covered_bytes = size_bytes`, `sha256` equals the listing version's value, `hash_verified_at_bind = true`, and every `jti` was issued for that (order, file).

### 3.5 Keys for the file id and content commitment (GLM R5 2.4, DeepSeek R5 F5)

- **Derivation.** The gateway volume secret `S` (32 random bytes) is never used directly. Two keys are derived with HKDF-SHA256:
  - `K_id = HKDF(S, info="aim-gateway/file-id/v1")`
  - `K_cc = HKDF(S, info="aim-gateway/content-commitment/v1")`
- **Values.**
  - `file_id = hex(HMAC-SHA256(K_id, source_name || 0x00 || relative_path))[:32]`
  - `content_commitment = hex(HMAC-SHA256(K_cc, raw_sha256_bytes))`

## 4. Gate 1 mandates folded here

| Mandate | Where |
| --- | --- |
| Canary state machine (GLM 2.1, DeepSeek F2) | Part 2 §gateway. Fixed now: a DNS answer, an established TCP connection or a completed TLS handshake to the canary each mean `open`. Only NXDOMAIN or no answer for DNS, and a refused, unreachable or timed-out connect, mean `closed`. The canary dial uses its own client, never the pinned `api.ai.market` client. Tests cover DNS resolves, TCP established with TLS failed, TCP refused, and timeout. |
| The canary exception in D7 and acceptance 2 (DeepSeek F1) | Acceptance 2 reads "exactly one *successful* outbound hostname"; the canary dials are expected to fail and are listed. |
| Canary latency (DeepSeek F3) | Cadence tightened to hourly and at every control-channel reconnect. Latency is stated as at most 1 hour. `status = unsupported` stops new permissions at once. |
| Purpose-specific keys (GLM 2.4, DeepSeek F5) | §3.5 |
| Customer display alias (GLM 2.2) | An alias in the customer's config is the customer's own disclosure choice. The install guide says so, and `preview` shows it. The default stays neutral. |
| Door-check addresses (GLM 2.3) | The door check connects only to public global unicast addresses (IPv4 and IPv6, per the IANA special-purpose registries). Everything else is `address_not_public`. |
| Cumulative receipt shape (GLM 2.5) | §3.4 |
| Typo at Gate 1 §3 step 4 (DeepSeek F4) | Corrected in the Gate 1 text in the same PR. |

## 5. Questions for Mars's peer read (before the Council round)

1. Is anything missing that chunk C needs to render the seller Gateways page, the listing source picker, "What we receive", or the buyer delivery view?
2. Should the delivery view live on the existing order page, as a section, or be its own route?
3. `can_publish_blockers`: are these codes enough for the UI to explain each blocker in plain words?
4. "Verify file": do you have an incremental SHA-256 library already in the frontend, or does this add one?

## 6. The gateway (chunk B)

### 6.1 Shape

- **Binary and image.** One static binary, `aim-gateway`, in a distroless image. It runs as UID 65532 with a read-only root filesystem and `cap_drop: [ALL]` (Gate 1 D8).
- **Subcommands:**
  - `run` (the default)
  - `preview <file-id>`: prints the exact phase-1 and phase-2 payloads and sends nothing
  - `approve <file-id>`: only used when `offer_requires_local_approval` is on
  - `version`
- **Mounts:**
  - `/config/gateway.toml`: read-only, owned by the customer
  - `/sources/<name>`: read-only, one mount per source
  - `/state`: the only writable volume
- **Config keys:**
  - `sources = [{name, path}]`
  - `offer_ceiling = [globs]` (default: everything under the sources)
  - `aliases = {relative_path: display_name}`
  - `columns = {relative_path: {rename = {…}, drop = [...]}}`
  - `door.listen = ":8080"`, plus optional `door.tls_cert` and `door.tls_key` files
  - `egress.connect_proxy = "host:port"` (optional; Gate 1 D7 profile a)
  - `offer_requires_local_approval = false`
- **State on `/state`:**
  - `identity.key` (Ed25519, mode 0600)
  - `secret.bin` (S, 32 bytes, 0600)
  - `pins.json`: pinned ai.market key sets, the canary host and zone, and the minimum version
  - `gateway.db` (SQLite)
  - `audit/` (§6.4)
- **Pairing.** The first `run` with `AIM_PAIRING_CODE` set generates the key and secret, pairs (§7.2) and writes `pins.json`. A second pairing attempt on an already-paired volume is refused.

### 6.2 Inventory (phase 1)

- **Walk.** Each source is walked. The gateway never follows a symlink that resolves outside its source root and skips anything that is not a regular file. There are at most 100,000 files per gateway in v1; beyond that the gateway refuses and reports `inventory_too_large`.
- **What is recorded.** For each file: size, modification time, media type (from magic bytes, using a small built-in table; `application/octet-stream` otherwise) and a streamed SHA-256. A file is re-hashed only when its size or mtime changes.
- **Rescan.** Every 15 minutes, and immediately after reconnecting.
- **What is sent.** Phase-1 records (§3.5 ids and commitments, plus display names) go in `inventory` messages of up to 1,000 records each, as a full snapshot with a generation number, so deletions are visible.

### 6.3 Description (phase 2)

A description runs only on a signed-in seller's request, relayed by the backend (§1.2). It covers exactly one file.

- **CSV/TSV.** The header row gives the columns. The whole file is streamed. Types are inferred from the first 10,000 non-null values per column, with a fallback to `string`.
- **JSON Lines.** Columns are the union of top-level keys, capped at 1,000. Values are streamed.
- **Parquet.** Schema and row count come from the footer. Null counts come from column statistics where every row group has them; otherwise the file is scanned.
- **Distinct counts.** An in-memory HyperLogLog (precision 14) per column. Only the bucket (§1.2) leaves the gateway.
- **Rename and drop.** The config map is applied before the payload is built. A dropped column does not appear at all.
- **Budget.** At most 30 minutes per description, otherwise `gateway_timeout`. One description runs at a time.

### 6.4 Audit log

- **Format.** Append-only JSON Lines under `/state/audit/`. Each entry is `{seq, time, message_type, body, prev_hash, sig}`, where `sig` is the gateway key's signature over the other fields.
- **Chaining.** The hash chain runs across file rotations (100 MB per file, all files kept), so a truncation or edit is detectable locally and by the backend. The backend stores every relayed entry (§1.3) and alerts on a `seq` gap or a `prev_hash` mismatch.
- **Scope.** Every gateway → ai.market message is written here before it is sent.

### 6.5 Ledger (SQLite, WAL, `synchronous=FULL`)

- **Tables:**
  - `offers(fid, sha256, lvid, iid, state, approved_locally_at)`
  - `seen_instructions(iid)`
  - `permissions(jti, oid, fid, sha256, sd, td, ro, state[issued|bound|closed|revoked], bound_at, closed_at)`
  - `coverage(oid, fid, start, end, serve_count)`, with intervals normalized so they never overlap
  - `revocations(jti, received_at)`
  - `receipts_outbox(seq, body, sent_at)`
- **Serve order.** For each request: verify the signature, audience and deadlines; bind or check the `jti`; clip the requested `Range` against the coverage rows at `serve_count = 2`; commit the new serve counts; only then write the first byte.
- **Ranges.** Only a single range per request is supported. A multi-range request is answered `416`.
- **Retries.** A byte whose count was committed but never delivered, because the connection died, is still counted. That is why the limit is two serves rather than one (Gate 1 §3 step 5).

### 6.6 Door server

- **Routes:**
  - `GET /v1/files/{fid}` with `Authorization: Bearer <permission>`
  - `GET /.well-known/aim-gateway?nonce=<32 hex>`, which returns a JWS signed by the gateway key: `{gid, nonce, iat}`
- **Nothing else.** There is no directory listing and no other route. `/healthz` is on a separate listener bound to `127.0.0.1:8081` for the container healthcheck only.
- **Limits.** Header timeout 10 s; idle timeout 60 s; at most 8 concurrent downloads (configurable).
- **Checks at bind.** The gateway confirms that the file's size and mtime still match its index. If either changed, it re-hashes the file, and if the result differs from the permission's `sha256` it refuses with `409 file_changed` and reports it.
- **Streaming hash.** While serving, the gateway hashes the bytes it streams whenever the pass starts at offset 0. It records `hash_verified_at_bind` in the receipt. A mismatch at the end of a full pass aborts the transfer with `aborted_hash_mismatch`.

### 6.7 Egress canary (Gate 1 mandate, GLM R5 2.1)

- **When.** Hourly, and on every channel reconnect.
- **DNS probe.** Resolve `<random 16 hex>.<canary_zone>` with the system resolver. Any A/AAAA answer means `open`. NXDOMAIN, SERVFAIL or a timeout means closed for DNS.
- **TCP probe.** Using its own plain `net.Dialer`, never the pinned channel client, connect to `canary_host:443` with a 5-second timeout. An established TCP connection means `open`, whatever happens next. Refused, unreachable or timed out means closed for TCP.
- **Result.** `closed` only if both probes are closed.
- **Reporting.** A `canary_result` message reports `{state, dns, tcp, at}`. ai.market's authoritative DNS and the canary host independently log hits under the gateway's random label, so an open result is visible server-side even if the gateway lies.
- **Failure mode.** Detection latency is at most 1 hour. `open` makes the gateway `unsupported`: no new permissions and no publishing.

## 7. Control channel

### 7.1 Transport

- **Endpoint.** A new WebSocket endpoint at `wss://api.ai.market/api/v1/gateway-channel`, opened by the gateway. It goes through the customer's CONNECT proxy when one is configured.
- **Legacy channel.** The legacy trust-channel endpoint (`trust_websocket.py`) is not reused. Its handlers are the legacy fulfilment path that chunk F deletes, and a separate endpoint keeps that deletion clean.
- **Keep-alive.** A heartbeat every 30 seconds. Reconnect with exponential backoff from 1 to 60 seconds, with jitter.
- **Size.** At most 1 MiB per message.

### 7.2 Pairing and authentication

- **Pairing.** `POST /api/v1/gateway-channel/pair {code, gateway_public_key, version}` returns `{gateway_id, permission_keys: [{kid, alg, key}], listing_keys: [...], minimum_version, canary_host, canary_zone}`. This is the only unauthenticated call, and the single-use code authorises it.
- **Connection.** On each connection the server sends a 32-byte nonce. The gateway answers with a signed `hello {gid, nonce, version, ts}`, and the server verifies it against the registered public key.
- **Gateway → server messages.** Every one is signed by the gateway key, with a monotonic `seq`. These are the audit-log entries.
- **Server → gateway messages that change what the gateway will do** are JWS signed by the matching ai.market key: offer and unoffer with the listing key; revoke with the permission key; key rotation (with the outgoing key of the same kind) and minimum version (with the listing key).
- **Server → gateway requests that only ask for data** (`describe`, `rescan`) are unsigned. Their results are data, and they cannot widen access.

### 7.3 Message types

- **Gateway → server:** `hello`, `inventory`, `description`, `receipt`, `canary_result`, `revocation_ack`, `offer_ack`, `error`.
- **Server → gateway:** `offer`, `unoffer`, `revoke`, `describe`, `rescan`, `key_rotation`, `minimum_version`.

The golden vectors (§9) define every body.

## 8. Keys and the signing service (chunk A)

### 8.1 Keys

- **Where the keys live.** Two asymmetric signing keys, `gateway-permission` and `gateway-listing`, in Google Cloud KMS, HSM protection level. The backend already uses Cloud KMS (`app/services/kms_service.py`).
- **Algorithm.** `EC_SIGN_ED25519` (EdDSA). Build step A0 verifies that this algorithm is available in the project's KMS location, and that KMS signatures verify with Go's `crypto/ed25519` and with the Python used by the tests.
- **Fallback.** If A0 fails, both keys use `EC_SIGN_P256_SHA256` (JWS `ES256`) and the golden vectors are regenerated. The tokens keep the same claims, and nothing else changes. Reviewers are asked below whether ES256 should simply be the default.

### 8.2 Signing service

- **Deployment.** A new Railway service, `gateway-signer`, with no public ingress. It is reachable only on the private network from `ai-market-backend`, which authenticates with a dedicated Infisical-held token.
- **Credentials.** It alone holds the KMS service-account credential. The API process never does.
- **Interface.** Two operations: `sign_permission(claims)` and `sign_listing_instruction(claims)`. Each validates the claim schema, refuses a `td` more than 25 hours out, rate-limits per gateway, and appends every signature request (claims only) to its own log.
- **Rotation.** New key versions are announced with `key_rotation` messages signed by the outgoing version. Gateways accept both versions for 7 days.

## 9. Backend (chunk A) data and workers

- **One migration, additive only.** New tables:
  - `gateways(id, seller_user_id, party_id, name, public_key, status, status_reason, version, last_seen_at, door_url, identity_ack_at, egress_state, egress_checked_at, created_at, revoked_at)`
  - `gateway_pairing_codes(code_hash, seller_user_id, expires_at, used_at)`
  - `gateway_files(gateway_id, file_id, display_name, size_bytes, media_type, content_commitment, generation, first_seen_at, changed_at, deleted_at)`
  - `gateway_file_descriptions(gateway_id, file_id, state, requested_at, described_at, sha256, row_count, columns jsonb, failure_code)`
  - `gateway_messages(gateway_id, seq, received_at, message_type, body jsonb, prev_hash, signature)`, append-only
  - `gateway_door_checks(gateway_id, checked_at, state, failure_code, certificate_flags)`
  - `gateway_offers(gateway_id, file_id, sha256, listing_version_id, instruction_id, op, sent_at, acked_at)`
  - `gateway_permissions(jti, order_id, gateway_id, file_id, sha256, sd, td, ro, issued_at, revoked_at)`
  - `gateway_receipts(gateway_id, order_id, file_id, seq, body jsonb, complete, received_at)`
- **Where the file SHA-256 is recorded.** Listing versions record each gateway file's `sha256` in the existing `listing_version_members` manifest contract (kept by the S1737 deletion spec), with `source = {"type": "gateway", "gateway_id", "file_id"}`.
- **Door-check worker.** A Celery beat task every 5 minutes on a dedicated worker service whose egress is restricted to public addresses. It implements Gate 1 §3 step 3 and the public-global-unicast rule (§4).
- **Channel handler.** Runs in the API process (WebSocket). It writes messages to `gateway_messages`, updates the tables above, and never logs or stores anything that phase 1 does not carry.
- **Settlement.** A complete matching receipt sets the file's delivery state. When every file is delivered, the order becomes `delivered` and the existing hold and settlement proceed. `delivery_method = direct` is reused.
- **Flag.** `AIM_GATEWAY_ENABLED` (off) gates every route, the worker and the channel.

## 10. Test plans and golden vectors

- **Golden vectors.** `aim-data-gateway/contract/vectors/*.json`, one file per message type and token. Each holds a test-only key pair, the input, the exact bytes and the expected verdict. The backend holds a byte-identical copy under `tests/contract/gateway/`, and a required CI check in each repository compares the copy's SHA-256 with the other side's pinned value (the S1732 preview-contract pattern).
- **Chunk A (backend):**
  - every route in §1 and §2, success and error codes;
  - pairing single use;
  - door check against public, private, loopback, metadata and redirect cases, plus the certificate flags;
  - permission issue, and re-issue with revocation and confirmation timeout;
  - receipt aggregation into a complete matching receipt;
  - dispute with `file_id`;
  - the flag-off 404s;
  - the migration upgrade and downgrade on a disposable database;
  - no buyer identifier in any seller-visible payload (golden check).
- **Chunk B (gateway):**
  - every acceptance item in Gate 1 §9 that the gateway owns;
  - the planted-marker fixture (Gate 1 acceptance 3);
  - symlink escape, special files and the 100k cap;
  - CSV, JSON Lines and Parquet profiles, including the Parquet fixtures from Event `s1741-gateway-go-parquet-evidence`;
  - the Range state machine: overlap, suffix, open-ended, multi-range 416, the third serve refused, restart persistence, re-issue resume;
  - the canary: DNS resolves, TCP established with TLS failed, refused, timeout;
  - a static scan listing every network dial site (one channel client plus the canary);
  - two reproducible builds with an identical digest;
  - the image runs with a read-only rootfs and no capabilities.
- **Chunk C (website):**
  - every screen against the §1 and §2 shapes, using mocked responses built from the golden vectors;
  - every blocker message;
  - "Verify file" on a 2 GiB file in a headless browser;
  - no buyer identifier rendered on seller pages, and no path rendered anywhere.
- **Chunk D (repository and release):** the SBOM and provenance verify, cosign signature verification, the hardening lint on the compose file, and the security documents present.
- **Chunk E (money path):** as Gate 1 §8, including the dispute path.

## 11. Language and dependency budget (Gate 1 D11)

- **Language.** **Go.** Arrow Go v18.8.0 read all five Parquet fixtures correctly (Event `s1741-gateway-go-parquet-evidence`). Its static build, though, is 41 MB and compiles 19 third-party modules, including grpc and protobuf.
- **Budget.** The budget is set on compiled third-party modules, not direct dependencies: **at most 15, and grpc and protobuf are not allowed.**
- **Build step B0.** Build the Parquet profile with `github.com/parquet-go/parquet-go` and with arrow-go's `parquet/file` package (without `pqarrow`), measure each with `go list -deps`, and keep the one inside budget that passes the fixtures. If neither fits, B0 stops and the choice comes back to review. It is not waived silently.
- **Line budget.** Still under 5,000 lines of non-test code, measured by CI.

## 12. Legacy installs (production read, 2026-09-23)

A read-only query of production shows:

| Measure | Count |
| --- | --- |
| Serials with status `activated` | 573 |
| Of those, metered in the last 30 days | 106 |
| Metered serials with no linked user (`auto_provision`), across 39 distinct hosts, most recent today 01:22Z | 101 |
| Metered serials linked to an `e2e-test.ai.market` user | 4 |
| Metered serials linked to an external user, last metered 2026-09-15 | 1 |
| Listed listings owned by any of those users | 0 |
| `aim_nodes` rows, both `suspended` | 2 |

- **What this does not show.** Serials are shared by AIM Data and vectorAIz, and nothing in the `serials` table says which product activated each one. So this read cannot confirm "no one is using it" for AIM Data specifically. The 101 unlinked, auto-provisioned installs are most likely vectorAIz downloads.
- **Rule for chunk F.** Serial activation and metering are **not** removed while any vectorAIz install uses them. Chunk F removes only AIM Data–specific routes. A migration is needed only for an install that backs a listed listing, and there are none today.
- **Before chunk F.** Its spec must attribute every active serial to a product first.

## 13. Chunk order

A0 (KMS algorithm check) → A, and in parallel B0 (Parquet budget) → B, both against the frozen §3 vectors → C (after A's routes exist behind the flag) → D → E → F (separate spec).

**Owners:** Vulcan owns A, B and D. Mars owns C. Both own E.

## 14. Review questions (Gate 2)

1. §2 and §3: does anything give ai.market seller bytes or buyer identity, or give the seller buyer identity? Automatic REJECT under `data-delivery-p2p.md` if it does.
2. §6.5: is the order commit-then-first-byte, with at most two serves per byte, free of replay and of stranding? Is refusing multi-range requests acceptable?
3. §7.2: is splitting unsigned data requests from signed authority messages sound? Can any unsigned request widen what the gateway serves or sends?
4. §8: should ES256 be the default instead of Ed25519, since it is supported everywhere? Is a signing service outside the API process with its own credential the right cut?
5. §11: is 15 compiled third-party modules, with no grpc or protobuf, the right budget for CISO reviewability?
6. §12: is the chunk F rule (keep serial activation and metering while vectorAIz uses them) right?
7. SIMPLER / BETTER: what here could be removed without breaking a Gate 1 decision?
