# BQ-AIM-DATA-GATEWAY-S1741: Gate 2, implementation specification (DRAFT, part 1: wire contract)

**Build Queue entity:** `build:bq-aim-data-gateway-rebuild-s1741`.
**Design authority:** Gate 1 [BQ-AIM-DATA-GATEWAY-S1741-GATE1.md](BQ-AIM-DATA-GATEWAY-S1741-GATE1.md), approved 3/3 at runbooks `8078d1e40f05734b734299cc0d17b547cd2aff2d` (Event Ledger `fb0d7272`) and merged at `ac8e8ed`. CORE v9.21 (Event Ledger `4349f80f`, `5d1edea7`).
**Reviewers:** GLM, DeepSeek and Gemini vote, and the vote must be unanimous. MP gives an advisory review and does not vote (Max S1741; route live at koskadeux-mcp `e670d015`).
**Status:** part 1 of 2. This part freezes the website ↔ backend contract that chunk C (Mars) builds against, and folds every Gate 1 mandate. Part 2 adds the gateway internals, the control channel, keys and KMS, backend tables and migrations, the chunk test plans and the language decision. Voting happens on the whole document; part 1 goes to Mars first for a peer read.

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
