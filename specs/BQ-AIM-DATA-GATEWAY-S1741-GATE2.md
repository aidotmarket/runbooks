# BQ-AIM-DATA-GATEWAY-S1741: Gate 2, implementation specification (approved)

**Build Queue entity:** `build:bq-aim-data-gateway-rebuild-s1741`.
**Design authority:** Gate 1 [BQ-AIM-DATA-GATEWAY-S1741-GATE1.md](BQ-AIM-DATA-GATEWAY-S1741-GATE1.md), approved 3/3 at runbooks `8078d1e40f05734b734299cc0d17b547cd2aff2d` (Event Ledger `fb0d7272`) and merged at `ac8e8ed`. CORE v9.21 (Event Ledger `4349f80f`, `5d1edea7`).
**Reviewers:** GLM, DeepSeek and Gemini vote, and the vote must be unanimous. MP gives an advisory review and does not vote (Max S1741; route live at koskadeux-mcp `e670d015`).
**Status:** R7. The R6 confirmation round (at `f696c2be`) returned GLM APPROVE and DeepSeek APPROVE_WITH_NITS (2 NIT); MP (advisory) raised two edge cases in the refund binding. R7 folds them; §20 maps them. The R5 confirmation round (at `ee0e0d94`) returned GLM REQUEST_CHANGES (2 MEDIUM on the new refund handoff), DeepSeek APPROVE_WITH_NITS, Gemini APPROVE and MP REQUEST_CHANGES (2, advisory, the same two points); §19 maps them. R4 (at `2fda795a`) passed 3/3: GLM APPROVE_WITH_NITS (1 LOW, 1 NIT), DeepSeek APPROVE_WITH_NITS (1 LOW, 3 NIT), Gemini APPROVE; MP REQUEST_CHANGES (4, advisory). R5 folds those nits and MP's four points; §18 maps them. R3 (at `b4dcde8a`) returned GLM APPROVE_WITH_NITS (2), DeepSeek REQUEST_CHANGES (1 MEDIUM, 3 minor), Gemini APPROVE_WITH_NITS (1) and MP REQUEST_CHANGES (4, advisory); §17 maps each R3 finding. R2 (at `6a1cba99`) returned GLM REQUEST_CHANGES (5), DeepSeek APPROVE_WITH_NITS (4), Gemini APPROVE and MP REQUEST_CHANGES (4, advisory); §16 maps each R2 finding. R1 (at `588fba11`) returned GLM REQUEST_CHANGES (12 findings), DeepSeek REQUEST_CHANGES (6), Gemini APPROVE_WITH_NITS (3) and MP REQUEST_CHANGES (5, advisory), plus Mars's peer read of §0–§5. Every finding is folded; §15 maps each one to where it landed. §0–§5 freeze the website ↔ backend contract that chunk C (Mars) builds against.

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
- **Auth parity (Mars 8):** buyer routes in §2 accept the same buyer principals as the existing buyer delivery routes (a session or a buyer API key), so an agent can buy and fetch a gateway listing exactly as a person can.
- **Polling (Mars 7):** every `202` and every in-progress state carries `Retry-After` (seconds). Chunk C honours it and otherwise uses: door check 2 s for up to 30 s; describe 10 s; delivery view 5 s while any file is `in_progress`, 60 s otherwise.
- **Byte intervals (GLM 12):** every interval is `[start, end]`, inclusive at both ends, as in HTTP `Range`. The length of `[a, b]` is `b − a + 1`.

## 1. Seller surface (seller session auth; the seller owns the gateway)

### 1.1 Pairing and gateway list

| Method and path | Request | Success | Errors |
| --- | --- | --- | --- |
| `POST /gateways/pairing-codes` | `{}` | `201 PairingCode` | `429 pairing_rate_limited` (at most 5 per seller per hour) |
| `GET /gateways` | none | `200 {"gateways": [Gateway]}` | none |
| `GET /gateways/{gateway_id}` | none | `200 Gateway` | `404 gateway_not_found` |
| `PATCH /gateways/{gateway_id}` | `{"name"?: string ≤ 80, "door_url"?: string \| null}` | `200 Gateway` | `422 door_url_not_https`, `422 door_url_invalid`, `404 gateway_not_found` |
| `DELETE /gateways/{gateway_id}` | `{"confirm_open_orders"?: true}` | `204` (revoked; see below) | `409 gateway_has_open_orders` (`details.open_order_count`) unless confirmed, `404 gateway_not_found` |
| `POST /gateways/{gateway_id}/door-check` | `{}` | `202 {"door_check": DoorCheck}` (state `pending`) | `429 door_check_rate_limited` (at most 1 per minute), `409 door_url_missing` |
| `POST /gateways/{gateway_id}/identity-acknowledgement` | `{"acknowledged": true}` | `200 Gateway` (sets `identity_ack_at`) | `422 acknowledgement_required` |

`PairingCode` (Mars 3, GLM 10):

```json
{"code": "XXXX-XXXX-XXXX", "expires_at": "time",
 "image": "ghcr.io/aidotmarket/aim-gateway@sha256:<digest>", "version": "semver",
 "minimum_version": "semver", "install_guide_url": "https://…", "compose_snippet": "string"}
```

- **Code.** 12 characters of Crockford base32 from the operating system's cryptographic random source (60 bits), shown in three groups. It is valid for 15 minutes and used once.
- **Storage.** Only `HMAC-SHA256(pairing_pepper, code)` is stored; the pepper is held in Infisical.
- **Guessing.** The unauthenticated pair call (§7.2) allows 10 failed attempts per source address per hour and 1,000 failed attempts per hour in total. Beyond either, it answers `429` and alerts. A code is marked used in the same transaction that registers the gateway.

**Revoking a gateway (Mars 2).** Revoking stops new permissions and offers at once and unlists the listings the gateway backs. Every paid order on that gateway whose files are not all delivered gets `blocked_code = gateway_revoked`, and the system opens a delivery problem for it (§2.3, `opened_by = system`, `missing_data`), which freezes the payout until support refunds or resolves it. Permissions already bound may finish until their transfer deadline.

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
  "listing_count": 0,
  "open_order_count": 0,
  "can_publish": true,
  "blockers": [Blocker]
}
```

`Blocker` (Mars 4) = `{"code": "…", "file_id"?: "hex", "since"?: "time"}`. Codes:

| Code | Meaning |
| --- | --- |
| `gateway_offline` | no control-channel connection |
| `gateway_revoked` | the seller revoked it |
| `version_below_minimum` | the gateway must be updated |
| `egress_open` | the last canary result was `open` or `unknown` (§6.7) |
| `door_url_missing` | no door URL set |
| `door_check_not_passed` | the last door check failed or never ran |
| `door_check_stale` | the last pass is more than 10 minutes old |
| `identity_ack_missing` | the D-A acknowledgement has not been given |
| `file_not_described` | (with `file_id`) the file has no current description |
| `file_stale` | (with `file_id`) the file changed after it was described |
| `file_missing` | (with `file_id`) the file is absent from the latest inventory |

`DoorCheck`:

```json
{
  "state": "never | pending | passed | failed",
  "checked_at": "time | null",
  "failure_code": "null | dns_failed | address_not_public | tls_failed | redirect_refused | timeout | bad_signature | gateway_mismatch | response_too_large",
  "certificate_flags": ["organization_in_subject", "extra_subject_alt_names"]
}
```

`status` is `unsupported` whenever the last egress canary result is `open` or `unknown` (Gate 1 D7, §6.7) or the version is below `minimum_version`. `can_publish` is true only when `blockers` has no gateway-level code. `certificate_flags` are warnings only and never block publishing (Max D-A). Chunk C shows them next to the D-A notice.

**Gateway usable (GLM 5).** One predicate is used for publishing, for the first permission and for every re-issue: `status = online`, egress `closed`, not revoked, a door check `passed` for the **current** `door_url` no more than 10 minutes ago (Gate 1 §3 step 3), and `identity_ack_at` set.

**Door URL changes (GLM R2 4).** Every door check records the normalized URL it checked. Any change to `door_url` resets `door_check` to `never` at once, so the gateway is not usable until the new URL passes.

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
  "present": true,
  "description": {
    "state": "not_requested | requested | described | failed | stale",
    "requested_at": "time | null",
    "described_at": "time | null",
    "sha256": "hex | null",
    "row_count": 0,
    "columns": [
      {"name": "string", "type": "string | integer | float | boolean | date | timestamp | other",
       "null_rate_pct": "0 | 5 | 10 | … | 100 | null", "distinct_bucket": "1 | 2-10 | 11-100 | 101-1000 | >1000"}
    ],
    "failure_code": "null | unsupported_format | read_error | gateway_timeout"
  },
  "offerable": false,
  "listing_version_ids": ["uuid"]
}
```

- **Phase 1 fields.** `file_id`, `display_name`, `size_bytes`, `media_type`, `content_commitment`, `present` and the two times are phase 1. The website never sees a path.
- **Default display name (GLM 6).** Without a customer alias, `display_name` is `file-<first 8 hex of file_id>.<ext>`, where `ext` comes from the media type (`csv`, `tsv`, `jsonl`, `parquet`, otherwise `bin`). The source file name is never used.
- **Phase 2 fields.** `description.*` is phase 2. It is present only after `describe`.
- **Null rate (GLM 6, DeepSeek 3, MP 5).** `null_rate_pct = 5 × floor((40 × nulls + rows) / (2 × rows))`, computed in integers: the rate rounded to the nearest 5%, halves rounding up. It is `null` when `rows = 0`. For example, 249 nulls in 10,000 rows gives 0, and 250 gives 5.
- **`offerable` (Mars 5)** is true when `present` is true and `description.state = described`. Publishing additionally needs a usable gateway (§1.1).
- **Staleness.** `stale` means the gateway reported a new `content_commitment` after the file was described. The description must be requested again before the file can back a new listing version. Listing versions already published stay bound to their SHA-256 (§2.4).
- **Before confirming.** The confirmation page in chunk C shows this fixed text: "ai.market will receive this file's column names (after your gateway's rename and drop settings), their types, the row count, null rates rounded to 5%, bucketed distinct counts, and the file's SHA-256. It will not receive any values." It also links the customer's IT to `aim-gateway preview <file-id>`, which prints the exact payload locally.
- **Confirmation binding (MP Q3, Gemini BETTER, GLM Q3).** A confirmed `describe` creates a confirmation id, and the backend sends the gateway a `describe` instruction signed with the listing key that carries it (§3.2). The gateway runs a description only for a valid, unexpired, unseen instruction.

### 1.3 "What we receive" (Gate 1 §4)

| Method and path | Request | Success |
| --- | --- | --- |
| `GET /gateways/{gateway_id}/received?cursor=&limit≤200&message_type=` | none | `200 {"messages": [ReceivedMessage], "next_cursor"}` |

`ReceivedMessage` = `{"seq": 0, "received_at": "time", "message_type": "hello | inventory | description | receipt | canary_result | revocation_ack | offer_ack | prepare_ack | error", "body": {…}}`. `body` is the message exactly as the gateway sent it (the gateway's own signed audit-log entry, relayed over the channel), rendered verbatim. It never includes the signature bytes. `seq` is the gateway's audit-log sequence, so a gap is visible. The optional `message_type` filter takes one type (Mars 9). Messages are kept for the life of the gateway record, including `hello`.

### 1.4 Listing with a gateway source

The existing listing flow gains one source type. Chunk C does not create a separate listing wizard.

```json
"source": {"type": "gateway", "gateway_id": "uuid", "file_ids": ["hex"]}
```

- **Draft rules.** A draft may reference any file. Publishing requires every file to be `offerable` and the gateway to be usable (§1.1). Otherwise the call fails with `409 gateway_not_publishable` and `details.blockers` (a list of `Blocker`).
- **Publish.** Publishing records each file's `sha256` on the listing version (the existing manifest contract) and sends the listing-key offer instruction (Gate 1 D12).
- **Unlist.** Unlisting sends the unoffer instruction.
- **Samples and licences.** The public sample and the licence choice use the existing listing surfaces unchanged.

## 2. Buyer surface (the buyer owns the order)

### 2.1 Delivery view

`GET /orders/{order_id}/gateway-delivery` → `200 GatewayDelivery`. It returns `404 not_a_gateway_order` for an order whose listing version has no gateway source. Chunk C renders it as a section of the existing order page (`app/dashboard/orders/[id]/page.tsx`), shown only for gateway orders (Mars Q2).

```json
{
  "door_url": "https://…",
  "hold": {"state": "pending_confirmation | held_until | no_hold", "until": "time | null", "disputable": true},
  "problem": "Problem | null",
  "files": [
    {
      "file_id": "hex",
      "display_name": "string",
      "size_bytes": 0,
      "sha256": "hex",
      "state": "not_started | in_progress | delivered",
      "transmitted_bytes": 0,
      "permission": "Permission | null",
      "reissue": {"allowed": true, "remaining_24h": 5,
                  "blocked_code": "null | complete | rate_limited | gateway_unavailable | gateway_revoked | coverage_exhausted | order_not_deliverable"}
    }
  ]
}
```

`Permission` = `{"token": "compact JWS", "jti": "uuid", "start_deadline": "time", "transfer_deadline": "time", "download_url": "https://<door>/v1/files/<file_id>", "browser_url": "https://<door>/v1/files/<file_id>?t=<token>", "resume_offset": 0}`.

- **Permission lifetime.** A permission is issued lazily, on the first `GET` after the order is deliverable, and only when the gateway is usable (§1.1) and answers the prepare exchange (§7.2). It is returned again on later `GET`s until it expires or closes. If the gateway is not usable, `permission` is `null` and `blocked_code` says why.
- **Browser download (GLM 1, Mars 1).** The browser downloads by top-level navigation to `browser_url`, so the browser's own download manager saves and resumes it. There is no cross-origin `fetch` and the door serves no CORS headers.
- **Agent download.** An agent sends `Authorization: Bearer <token>` to `download_url`. `Range` is supported on both.
- **Token in a URL.** The token is bound to one order, one file and one gateway, expires at its transfer deadline, and cannot move more than two serves of any byte. The door answers with `Referrer-Policy: no-referrer`, `Cache-Control: no-store` and `Content-Disposition: attachment`. The seller's door logs are the seller's own.
- **Hold (GLM R2 2, MP R2 3, DeepSeek R2 4).** `hold.until` is `payout_hold_until`, one helper shared by this view, the problem route and `order_payout_eligibility`, computed exactly as payout computes it today (`order_money_service.py:884-893`): for an order with a transaction, the latest `confirmed` transaction event plus 48 hours; otherwise `escrow_hold_until`. The helper returns one of three states (GLM R3 1, MP R3 3): `pending_confirmation` (a transaction with no `confirmed` event yet; `until` is `null`), `held_until` (with a timestamp in `until`), or `no_hold` (no transaction and `escrow_hold_until` is `null`). `hold` in the view is `{"state", "until", "disputable"}`, and `disputable` follows the problem window in §2.3 exactly.
- **Browser resume across a re-issue (MP R2 2).** Within one permission, the browser's download manager resumes the same `browser_url`. A new permission is a new URL, so the browser cannot append to the earlier partial file. For a browser, re-issue therefore restarts the file from byte 0 (`mode = restart`, §2.2), which is the retry the second serve exists for. The view also shows a copyable command for the header path (`download_url` never changes, only the token), for example `curl -C - -H "Authorization: Bearer <token>" -o <display_name> <download_url>`, which resumes across permissions without restarting. `-C -` resumes from what the buyer's own file holds, which is the right point for the buyer; it can differ from `resume_offset`, which counts only bytes the door wrote (DeepSeek R3 3).
- **After two serves (MP R3 1).** If a browser download is interrupted again after a restart, `restart` is refused because some bytes have been served twice. Gate 1 §3 step 4 settles this case: bytes already served twice go to the problem path, not to another serve. The view then offers "Report a problem" and the header command. The command helps only when the buyer's saved file ends at a byte with fewer than two serves; if it asks for bytes already served twice, the door refuses them and the problem path is the answer (GLM R4 1). Reaching it takes two interrupted transfers, each running past its transfer deadline.
- **`coverage_exhausted` (GLM 11).** Some bytes not yet transmitted can no longer be served (§6.5). The view offers "Report a problem" and no re-issue.

### 2.2 Re-issue

`POST /orders/{order_id}/gateway-delivery/files/{file_id}/permissions` with `{"mode"?: "restart | resume"}` → `201 Permission`. `mode` is optional and defaults to `resume`; chunk C sends `restart` explicitly (Gemini R3 1). `restart` issues `ro = 0` and needs every byte of the file to have been written at most once so far; otherwise it answers `409 restart_unavailable` and the view offers `resume`. `resume` issues `ro = resume_offset`.

Errors:
- `409 delivery_complete`
- `429 reissue_rate_limited` (5 per file per order per 24 hours; `details.retry_after`)
- `409 gateway_unavailable` (not usable, §1.1; `details.blockers`)
- `409 gateway_revoked`
- `409 coverage_exhausted`
- `409 restart_unavailable`
- `409 order_not_deliverable` (refunded or cancelled)

Order of operations (Gate 1 §3 step 4): send the signed revocation of the old `jti` over the channel and wait for the gateway's idempotent confirmation; send the signed `prepare` and wait for `prepare_ack` (each at most 10 seconds; otherwise `409 gateway_unavailable`); then issue the new permission with `ro` set by `mode`. An open delivery problem does not block re-issue, so the file can still arrive while support looks at it.

### 2.3 Problems (GLM 2, DeepSeek 2, MP 3, Gemini 1–2, Mars 6)

The deprecated `POST /orders/{order_id}/dispute` is **not** used. Gateway orders have their own route:

`POST /orders/{order_id}/gateway-delivery/problems` with `{"category": "missing_data | corrupted", "file_ids": ["hex"], "note"?: "string ≤ 2000"}` → `201 Problem`.

`Problem` = `{"problem_id": "uuid", "category": "…", "file_ids": ["hex"], "opened_at": "time", "opened_by": "customer | system", "state": "open | refund_pending | resolved", "resolution": "null | released | refunded | partially_refunded", "support_case_id": "uuid"}`.

- **When (DeepSeek R3 1, MP R3 3, GLM R3 1).** One rule, used by the route and by `hold.disputable`:
  - while any file of the order is not `delivered` (order status `paid`, `in_escrow`, `pending_delivery` or `delivery_failed`): always allowed, whatever the hold says. Payout cannot happen in these states, because `gateway_delivery_incomplete` refuses it;
  - once every file is delivered (status `delivered` or `completed`): allowed while the hold is `pending_confirmation`, or `held_until` a time still in the future. Closed when that time has passed, and closed at once for `no_hold`;

  Otherwise `409 problem_window_closed`. (Opening a problem after payout ownership was taken does not widen this window; it only marks the payout `reconciliation_required`, as described below. DeepSeek R4 2.) A file id not in the order is `422 file_not_in_order`. At most one problem per order is unresolved (`open` or `refund_pending`) at a time: a second call while one is unresolved adds its `file_ids` to it and returns `200`; if that problem is `refund_pending`, the new files are held in its `pending_file_ids` and raise a support task on its case; they are not covered by the refund already decided (MP R6 2).
- **What it does, in one transaction under the order money lock** (the same lock the legacy dispute takes, `order_service.py:1967`):
  - writes a `gateway_delivery_problems` row with the file ids and `state = open`; this row is the authoritative hold, read by the new payout reason `gateway_problem_open`, which applies while any problem on the order is not `resolved`, that is `open` or `refund_pending` (GLM R2 BETTER, DeepSeek R4 1);
  - sets `orders.disputed_at` to now and `dispute_category`, and **clears** `dispute_resolved_at` (GLM R2 3), so the existing `disputed` reason (`order_money_service.py:846-847`) also refuses payout, and the order shows as disputed on existing surfaces;
  - cancels a reserved payout, or marks it `reconciliation_required` when payout ownership has already been taken, exactly as `order_service.py:1981-1986` does;
  - opens a support case through the CRM support workflow (`crm_support_service.open_dispute`, a `DisputeCase` with `transaction_id`), so it appears where support already works disputes.
- **What it does not do.** It does not set `revoked`, and it does not change the order status. Delivery continues.
- **`note`.** Optional. The support case's `opened_reason` is built from the category and the files' display names, plus the note when given.
- **Resolution (MP R2 1, MP R3 4, GLM R3 2).** The legacy resolve path refuses orders whose status is not `disputed` (`order_service.py:2049-2052`), so it is not used. A gateway problem is resolved only through `resolve_gateway_problem(problem_id, outcome, resolved_by)`, reached from one admin route, `POST /admin/gateway-problems/{problem_id}/resolve` with `{"outcome": "released | refunded | partially_refunded | reopen", "refund_cents"?, "note"?}` (`refund_cents` is required for `partially_refunded`, and absent for `refunded`, `released` and `reopen`; GLM R5 3, DeepSeek R6 2). The route requires the existing admin role check (as `disputes.py:327-350` does) and records `resolved_by`. In one database transaction under the order money lock it:
  - on `released`: sets the problem `resolved`, sets `dispute_resolved_at`, and moves the linked `DisputeCase` to `resolved` with the outcome in its audit record, through a variant of the CRM transition that does not commit on its own. The variant includes the nested task completion (`crm_service.py:2803-2826`, which commits today), so the problem, the case, the task and the audit rows commit or roll back together (MP R4 4);
  - on `refunded` or `partially_refunded` (MP R4 1): records on the problem the decision, the amount still to be refunded under this decision (`refund_cents`: for `partially_refunded` the amount given; for `refunded` the order total minus `refund_applied_cents` at that moment, so a full refund after earlier partial refunds is reachable; MP R6 1, DeepSeek R6 1), `refund_pending_at` = now, and `refund_baseline_cents` = the order's `order_money_state.refund_applied_cents` at that moment, and sets it `refund_pending`. The backend has no refund-creation path today: refunds are issued in Stripe and come back as `charge.refunded` events, which `refund_processing_service.admit_order_refund` admits and `apply_order_refund_effects` applies under the order money lock. Support therefore issues the refund in Stripe as it does now (optionally tagging it `gateway_problem_id` for its own reference; the backend does not rely on the tag).
  - **Binding a refund to the problem (GLM R5 1, MP R5 1, DeepSeek R5 2).** In the same transaction in which `apply_order_refund_effects` applies a refund's effects to an order, it looks up that order's single unresolved problem. If it is `refund_pending` and `refund_applied_cents − refund_baseline_cents ≥ refund_cents`, it sets exactly that problem (by id) `resolved`, with `resolution` from the recorded decision and the applied amount, and resolves its `DisputeCase` through the non-committing variant. If the problem holds `pending_file_ids`, the same transaction opens a new `open` problem for those files with the same effects as the problem route (its own support case, `disputed_at` set and `dispute_resolved_at` cleared; DeepSeek R7 1), so a complaint made while the refund was pending keeps the payout frozen until support decides it (MP R6 2). A refund applied while the problem is `open`, or one that leaves the total short of `refund_cents`, changes nothing on the problem and raises a support task on its case. Because the check reads applied totals under the lock, a replayed event that applies nothing new changes nothing.
  - **Refund watch (GLM R5 2, MP R5 2).** A Celery beat task, `gateway_refund_watch`, runs every 15 minutes on the backend's ordinary worker. For each `refund_pending` problem with `refund_pending_at` more than 72 hours ago and `refund_alerted_at` empty, it raises one support task on the linked case and sets `refund_alerted_at`, so it alerts exactly once. `{"outcome": "reopen"}` is accepted only on a `refund_pending` problem: it returns it to `open`, merges its `pending_file_ids` into `file_ids` and clears them, and clears `refund_cents`, `refund_pending_at`, `refund_baseline_cents` and `refund_alerted_at`, so a later refund decision starts a fresh watch and covers every reported file (GLM R7 1, MP R7 1). Any other resolve call on a `refund_pending` problem is refused with `409 refund_pending`, and `reopen` on any other state with `409 not_refund_pending`.

  Creating provider refunds from the backend is out of scope here.

  It never changes the delivery status. The generic CRM transition to `resolved` is refused for a case linked to a gateway problem that is `open` or `refund_pending` (`409 gateway_problem_requires_outcome`; GLM R4 2, DeepSeek R4 1, MP R4 2), so a case cannot close while its hold stays open, and money cannot move without a recorded outcome. Payout becomes eligible again only when every problem is `resolved` and every other reason has cleared.
- **Repeated problems.** A new problem after a resolved one opens a fresh row, sets `disputed_at` again and clears `dispute_resolved_at`, all under the same lock. History stays in `gateway_delivery_problems` and the CRM.
- **Alignment with `build:bq-dispute-hold-gate-s1711`.** That item makes an open dispute freeze settlement for every order. This route freezes gateway orders through `gateway_problem_open` and the existing `disputed` reason, and chunk E adds a further guard, `gateway_delivery_incomplete`, which refuses payout for a gateway order until every file has a complete matching receipt. When S1711 lands, its predicate covers these orders too, and nothing here conflicts with it.

**Verify file.** This runs entirely in the browser, and nothing is uploaded. The buyer picks the downloaded file, and chunk C hashes it with `@noble/hashes` SHA-256 (already in the lockfile through `@noble/curves`; chunk C makes it a direct dependency) in 8 MiB chunks inside a Web Worker, and compares the result with `files[].sha256` (Mars Q4).

### 2.4 Delivered state

- **In the view.** A file is `delivered` when the backend holds the complete matching receipt (§3.4). The order is delivered when every file is.
- **Settlement.** Settlement waits for the 48-hour hold with no open problem, and the payout check additionally refuses a gateway order without complete matching receipts for every file (§2.3).

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

### 3.2 Signed instructions from ai.market

Every server → gateway message is a compact JWS. The gateway rejects an `iid` it has already seen, an instruction whose `aud` is not its own id (GLM R5 Q2 mandate), and one signed with the wrong key.

| `op` | Key | `typ` | Claims besides `op`, `aud`, `iid`, `iat` |
| --- | --- | --- | --- |
| `offer`, `unoffer` | listing | `aim-offer+jwt` | `fid`, `sha256`, `lvid` |
| `describe` | listing | `aim-describe+jwt` | `fid`, `cid` (the seller's confirmation id), `exp` (`iat` + 15 minutes) |
| `revoke` | permission | `aim-revoke+jwt` | `jti` |
| `prepare` | permission | `aim-prepare+jwt` | `oid`, `fid`, `sha256` |
| `key_rotation` | outgoing key of the same kind | `aim-keys+jwt` | `keys` |
| `minimum_version` | listing | `aim-minver+jwt` | `version` |

### 3.3 Gateway answers

The gateway signs each with its gateway key:

- **Revocation confirmation:** `{"op": "revoke_ack", "jti", "state_before": "active | expired | closed | unknown"}`. It always succeeds (Gemini R4).
- **Prepare answer:** `{"op": "prepare_ack", "iid", "oid", "fid", "ready": true, "refusal": "null | not_offered | outside_ceiling | awaiting_local_approval | file_changed | file_missing | coverage_exhausted | complete", "resume_offset": 0, "transmitted_bytes": 0, "interval_count": 0, "max_serve_count": 0}`. `resume_offset` is the first byte not yet transmitted; `max_serve_count` is the highest serve count of any byte, which decides `restart_unavailable`. The full intervals travel only in receipts (MP R2 SIMPLER).

### 3.4 Receipt (GLM R5 2.5; R1: MP 1–2, GLM 3, DeepSeek 1)

The gateway signs this with its gateway key, one receipt per (order, file) state change, and the receipts are cumulative:

```json
{"op": "receipt", "oid": "uuid", "fid": "hex", "sha256": "hex", "size_bytes": 0,
 "jtis": ["uuid"], "transmitted": [[0, 1048575]], "transmitted_bytes": 0,
 "max_serves_reached_bytes": 0, "outcome": "in_progress | complete | aborted_block_mismatch | aborted_deadline",
 "blocks_verified": true, "first_byte_at": "time", "last_byte_at": "time", "seq": 0}
```

- **`transmitted`** is the normalized, merged set of byte intervals the door actually wrote to a buyer connection, across every listed `jti`. Bytes reserved for a request but not written are never in it (§6.5). It holds at most 1,025 intervals (§6.5), and `max_serves_reached_bytes` is a count, not a list (DeepSeek R3 2), so a receipt stays well under the 1 MiB message limit (MP R2 4).
- **`blocks_verified`** is true when every transmitted byte came from a block whose hash matched the block list bound to `sha256` at the moment it was read (§6.6).
- **Complete matching receipt.** `outcome = complete`, `transmitted_bytes = size_bytes`, `sha256` equals the listing version's value, `blocks_verified = true`, and every `jti` was issued for that (order, file).
- **Acknowledged bytes.** A door cannot observe what the buyer's disk kept. "Transmitted" is the strongest fact the gateway can sign, and the buyer's check is "Verify file" plus a problem during the hold.

### 3.5 Keys for the file id and content commitment (GLM R5 2.4, DeepSeek R5 F5)

- **Derivation.** The gateway volume secret `S` (32 random bytes) is never used directly. Two keys are derived with HKDF-SHA256:
  - `K_id = HKDF(S, info="aim-gateway/file-id/v1")`
  - `K_cc = HKDF(S, info="aim-gateway/content-commitment/v1")`
- **Values.**
  - `file_id = hex(HMAC-SHA256(K_id, source_name || 0x00 || relative_path))[:32]`. The id is truncated to 128 bits: it only has to be unique within one gateway (at most 100,000 files), and a short id keeps URLs readable (DeepSeek 6).
  - `content_commitment = hex(HMAC-SHA256(K_cc, raw_sha256_bytes))`

## 4. Gate 1 mandates folded here

| Mandate | Where |
| --- | --- |
| Canary state machine (GLM 2.1, DeepSeek F2) | §6.7. One table, used everywhere: any DNS answer, an established TCP connection, a completed TLS handshake or a `2xx` to a proxy `CONNECT` means `open`. A failed DNS lookup means closed only when ai.market's authoritative DNS saw no query for that label. The canary dial uses its own client, never the pinned `api.ai.market` client. |
| The canary exception in D7 and acceptance 2 (DeepSeek F1) | Acceptance 2 reads "exactly one *successful* outbound hostname"; the canary dials are expected to fail and are listed. |
| Canary latency (DeepSeek F3) | Cadence tightened to hourly and at every control-channel reconnect. Latency is stated as at most 1 hour. `open` or `unknown` stops new permissions at once. |
| Purpose-specific keys (GLM 2.4, DeepSeek F5) | §3.5 |
| Customer display alias (GLM 2.2) | An alias in the customer's config is the customer's own disclosure choice. The install guide says so, and `preview` shows it. The default stays neutral (§1.2). |
| Door-check addresses (GLM 2.3) | The door check connects only to public global unicast addresses (IPv4 and IPv6, per the IANA special-purpose registries). Everything else is `address_not_public`. |
| Cumulative receipt shape (GLM 2.5) | §3.4 |
| Typo at Gate 1 §3 step 4 (DeepSeek R5 F4) | Corrected in the Gate 1 text in the same PR. |

## 5. Mars's peer read

Mars read §0–§5 (peer #6003) and his answers are folded: download by navigation (§2.1), revoking with open orders (§1.1), the pairing response (§1.1), structured blockers (§1.1), `offerable` (§1.2), problems across several files (§2.3), polling (§0), agent parity (§0), the `received` filter and retention (§1.3), the order-page section (§2.1) and `@noble/hashes` (§2.3). Part 1 is frozen for chunk C once R2 passes.

## 6. The gateway (chunk B)

### 6.1 Shape

- **Binary and image.** One static binary, `aim-gateway` (`CGO_ENABLED=0`), in a distroless image.
- **Runtime constraints (Gate 1 D8; GLM 8).** The shipped compose file and the install guide require: UID 65532, a read-only root filesystem, `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`, no Docker socket or other host socket mounted, no `network_mode: host`, no `privileged`, no `pid: host` or `ipc: host`, and only the mounts below. The gateway checks what it can see at start (UID, writable root, capabilities, a mounted Docker socket) and refuses to run if any is wrong.
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
  - `door.listen = ":8080"`: plain HTTP inside the container network. TLS is terminated by the seller's reverse proxy, as Gate 1 D4 settled; the gateway holds no TLS key (GLM R2 5)
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
- **What is recorded.** For each file: size, modification time, media type (from magic bytes, using a small built-in table; `application/octet-stream` otherwise), a streamed SHA-256 and, in the same read, a **block list**: the SHA-256 of each 8 MiB block (the last one may be shorter). The block list stays in `gateway.db` and is never sent. For inventory only, a file is re-hashed when its size or mtime changes; serving never relies on size or mtime (§6.6).
- **Rescan.** Every 15 minutes, and immediately after reconnecting. There is no remote rescan request (GLM SIMPLER).
- **What is sent.** Phase-1 records (§3.5 ids and commitments, plus display names) go in `inventory` messages of up to 1,000 records each, as a full snapshot with a generation number, so deletions are visible.
- **Deletions (Amendment B, S1750).** Because a generation may span several messages, the server never infers a deletion from absence. A file that was in the gateway's previous inventory and is no longer found is sent in the next generation with `present: false`. The resume rule in §7.2 guarantees that entry arrives, so it is sent once.

### 6.3 Description (phase 2)

A description runs only for a signed `describe` instruction (§3.2) that is unexpired and unseen. It covers exactly one file.

- **CSV/TSV.** The header row gives the columns. The whole file is streamed. Types are inferred from the first 10,000 non-null values per column, with a fallback to `string`.
- **JSON Lines.** Columns are the union of top-level keys, capped at 1,000. Values are streamed.
- **Parquet.** Schema and row count come from the footer. Null counts come from column statistics where every row group has them; otherwise the file is scanned.
- **Null rate.** Rounded to the nearest 5% by the integer rule in §1.2, in the gateway, before the payload is built.
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
  - `files(fid, source, relative_path, size, mtime, sha256, block_size, block_hashes)`
  - `permissions(jti, oid, fid, sha256, sd, td, ro, state[issued|bound|closed|revoked], bound_at, closed_at)`
  - `serves(oid, fid, start, end, count)`: how many times each byte has been reserved for serving, intervals normalized so they never overlap
  - `transmitted(oid, fid, start, end)`: bytes actually written to a buyer connection, normalized
  - `requests(id, jti, start, end, written_through, open)`: one row per in-flight response
  - `revocations(jti, received_at)`
  - `receipts_outbox(seq, body, sent_at)`
- **Reserve, then write, then settle (MP 1).** For each request, in one transaction: clip the range against `serves` at `count = 2`, add one to `count` for the clipped range, and insert the `requests` row. Only then is the first byte written. While writing, the door records `written_through` and adds the written bytes to `transmitted` at least every 8 MiB and at the end. When the response ends for any reason, one transaction gives back the reservation for bytes that were reserved but never written (subtracting one from `count`) and closes the request.
- **After a crash.** On start, every still-open request keeps its reservation up to `written_through` plus one 8 MiB window, and gives back the rest. So a crash can cost at most one window of one serve, never a replay.
- **Two serves per byte (Gate 1 §3 step 5).** A byte can be written at most twice across all permissions of an order. Disconnecting before the first byte, or partway through, uses up nothing that was not written.
- **Closing a `jti` (Gate 1 §3 step 5; GLM R2 1, DeepSeek R2 1).** In the same transaction that settles a request, if `transmitted` for the (order, file) now covers every byte, every `issued` or `bound` `jti` for that (order, file) is set `closed`. A `jti` is also closed at its `td`. Closing is durable before the complete receipt is queued, and it takes precedence: after close, even a range served only once is refused. So one permission never gives two full reads.
- **Fragmentation (MP R2 4, MP R3 2, DeepSeek R3 4, MP R4 3).** A response writes a contiguous run of bytes from its start, so, however early it stops, it adds at most one new `transmitted` interval, and none when its first byte extends an existing interval. A request is *extending* when it starts at byte 0 or the byte before its start is already transmitted; otherwise it is *isolated*. Extending requests are never refused for fragmentation, so filling a gap, a `resume` from `resume_offset` and a browser `restart` from 0 cannot hit this limit; they remain subject to every other check, including permission validity, the two-serve rule, `restart_unavailable` and `coverage_exhausted` (GLM R5 4). An isolated request is admitted only when the current interval count, plus the number of other open isolated requests for that (order, file), plus one, is at most 1,024; otherwise the door answers `409` with code `coverage_fragmented` before anything is reserved. The only extending request that can add an interval is one starting at an untransmitted byte 0, so the list never exceeds 1,025 intervals. A buyer never needs an isolated request to finish a file.
- **Coverage exhausted.** When a byte that has not been transmitted has `count = 2` (possible only after crashes), the gateway counts it in `max_serves_reached_bytes` and `prepare_ack` refuses with `coverage_exhausted`; the buyer is sent to a problem report (§2.3).
- **Ranges.** Only a single range per request is supported. A multi-range request is answered `416`.

### 6.6 Door server

- **Routes:**
  - `GET /v1/files/{fid}` with `Authorization: Bearer <permission>` or `?t=<permission>` (the browser path, §2.1). If both are present they must be equal.
  - `GET /.well-known/aim-gateway?nonce=<32 hex>`, which returns a JWS signed by the gateway key: `{gid, nonce, iat}`
- **Nothing else.** There is no directory listing and no other route, and no CORS: `OPTIONS` and any other method get `405` with no `Access-Control-*` headers. `/healthz` is on a separate listener bound to `127.0.0.1:8081` for the container healthcheck only.
- **Response headers.** `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, `Content-Disposition: attachment; filename="<display_name>"`, `Accept-Ranges: bytes`.
- **Limits.** Header timeout 10 s; idle timeout 60 s; at most 8 concurrent downloads (configurable).
- **Serve order (GLM 4, DeepSeek 4; Gate 1 D12).** Each step must pass before the next:
  1. Verify the permission's signature against a pinned permission key.
  2. `aud` is this gateway.
  3. Look up the offer for (`fid`, `sha256`). It must be `offered` and must have been signed with the **listing** key. An offer withdrawn after this `jti` was bound still lets that `jti` finish until `td`; it allows no new bind.
  4. The file's path is inside `offer_ceiling`, evaluated now.
  5. When `offer_requires_local_approval` is on, the offer has `approved_locally_at`.
  6. Deadlines: `sd` for a bind, `td` for every request.
  7. The `jti` is `issued` (bind it) or `bound` to this (`oid`, `fid`), and not revoked or closed.
  8. Reserve (§6.5).
  9. Serve with block verification.
- **Block verification (MP 2, GLM 3, DeepSeek 1).** The door reads the file in whole 8 MiB blocks, hashes each block and compares it with the block list stored for this `sha256` before writing any of that block's bytes, including when the request starts or ends inside a block. A mismatch stops the response before the bad bytes are written, marks the file changed, and reports `aborted_block_mismatch`. This works the same for every `Range`, every resume and every re-issue, and it catches a change that keeps the size and mtime. An offer for a `sha256` whose block list the gateway does not hold is refused in `offer_ack` with `file_changed`.
- **Memory.** One 8 MiB buffer per download; 64 MiB at the default limit of 8.

### 6.7 Egress canary (Gate 1 mandate, GLM R5 2.1; R1: GLM 7, MP 4)

- **When.** Hourly, and on every channel reconnect.
- **DNS probe.** Resolve `<random 16 hex>.<canary_zone>` with the system resolver. The zone answers every label with an A and an AAAA record.
- **TCP probe.** Using its own plain `net.Dialer`, never the pinned channel client, connect to `canary_host:443` with a 5-second timeout.
- **Proxy probe.** When `egress.connect_proxy` is set, send `CONNECT canary_host:443` through it with a 5-second timeout.
- **Classification (one table, also used in §4):**

  | Observation | Result |
  | --- | --- |
  | Any A/AAAA answer | `open` |
  | Established TCP connection, whatever happens next | `open` |
  | Proxy `CONNECT` answered `2xx` | `open` |
  | Authoritative DNS or the canary host logged this label or this gateway within 5 minutes | `open`, whatever the gateway reported |
  | NXDOMAIN, NODATA, SERVFAIL, REFUSED or timeout, with no server-side hit | closed for DNS |
  | Refused, unreachable or timed-out connect | closed for TCP |
  | Proxy refused, `403`, `407` or other non-`2xx` | closed for the proxy |
  | No `canary_result` within 2 hours | `unknown` |

- **Result.** `closed` only if every probe is closed and there is no server-side hit. `open` and `unknown` make the gateway `unsupported`: no new permissions and no publishing. Detection latency is at most 1 hour.
- **Reporting.** A `canary_result` message reports `{state, dns, tcp, proxy, label, at}`.

## 7. Control channel

### 7.1 Transport

- **Endpoint.** A new WebSocket endpoint at `wss://api.ai.market/api/v1/gateway-channel`, opened by the gateway. It goes through the customer's CONNECT proxy when one is configured.
- **Legacy channel.** The legacy trust-channel endpoint (`trust_websocket.py`) is not reused. Its handlers are the legacy fulfilment path that chunk F deletes, and a separate endpoint keeps that deletion clean.
- **Keep-alive.** A heartbeat every 30 seconds. Reconnect with exponential backoff from 1 to 60 seconds, with jitter.
- **Size.** At most 1 MiB per message.

### 7.2 Pairing and authentication

- **Pairing.** `POST /api/v1/gateway-channel/pair {code, gateway_public_key, version}` returns `{gateway_id, permission_keys: [{kid, alg, key}], listing_keys: [...], minimum_version, canary_host, canary_zone}`. This is the only unauthenticated call; the single-use code authorises it, under the limits in §1.1.
- **Connection.** On each connection the server sends a 32-byte nonce. The gateway answers with a signed `hello {gid, nonce, version, ts}`, and the server verifies it against the registered public key.
- **Gateway → server messages.** Every one is signed by the gateway key, with a monotonic `seq`. These are the audit-log entries.
- **Resume and acknowledgement (Amendment B, S1750).** The server accepts audit entries strictly in order (`seq` = last stored + 1, `prev_hash` = last stored entry hash) and refuses a repeated `seq`, so the gateway must know where the server stopped:
  - After it verifies `hello`, the server sends `{"resume": {"seq": <last stored seq, 0 if none>, "entry_hash": "<its entry hash, empty if none>"}}` before anything else. The gateway resends its local audit entries from `seq + 1` in order. If the server's `seq` is ahead of the gateway's log, or the hash does not match the gateway's own entry at that `seq`, the gateway stops sending, logs `audit_divergence` locally and retries on the next connection; it never rewrites or skips local entries.
  - After storing each entry, the server sends `{"ack": <seq>}`. The gateway treats an entry (for example a queued receipt) as delivered only once its `seq` is acknowledged, either by `ack` or by a later `resume`.
  - Neither message is signed: both only report what the server stored, the gateway's entries stay self-authenticating through the hash chain, and a false value can only make the gateway resend (refused as out of order) or wait, never lose or forge an entry.
- **Server → gateway messages.** Every one is a signed instruction (§3.2). There are no unsigned requests.
- **Prepare (GLM BETTER, GLM 5).** Before any permission is returned, first issue or re-issue, the backend sends `prepare` and waits up to 10 seconds for `prepare_ack`. The gateway runs serve-order steps 3–5 (§6.6), checks that it holds the block list for `sha256`, and returns its resume point and coverage summary. The backend issues the permission only when `ready` is true, with `ro` set by the re-issue `mode` (§2.2).

### 7.3 Message types

- **Gateway → server:** `hello`, `inventory`, `description`, `receipt`, `canary_result`, `revocation_ack`, `offer_ack`, `prepare_ack`, `error`.
- **Server → gateway:** `offer`, `unoffer`, `describe`, `revoke`, `prepare`, `key_rotation`, `minimum_version`.

The golden vectors (§10) define every body.

## 8. Keys and the signing service (chunk A)

### 8.1 Keys

- **Where the keys live.** Two asymmetric signing keys, `gateway-permission` and `gateway-listing`, in Google Cloud KMS at the SOFTWARE protection level. Cloud KMS offers `EC_SIGN_ED25519` only at that level; it is not available in Cloud HSM (Google's published algorithm table, read during build step A0 on 2026-09-23; this is a documentation finding, not yet a live A0 result). Gate 1 D5 requires the keys to be held "in KMS or HSM", so this meets it: the private keys are generated in and never leave Cloud KMS, they are not exportable, every signature request is written to the `gateway-signer` log (§8.2), chunk A turns on Cloud Audit Logs data-access logging for KMS in the key's project and its acceptance checks that a test signature appears there, and only the `gateway-signer` service's credential can use them (§8.2). The backend already uses Cloud KMS (`app/services/kms_service.py`).
- **Algorithm.** `EC_SIGN_ED25519` (EdDSA), as Gate 1 D5 settled. Build step A0 verifies that this algorithm is available in the project's KMS location, and that KMS signatures verify with Go's `crypto/ed25519` and with the Python used by the tests.
- **If A0 fails (GLM 9).** The build stops and the algorithm comes back to Council. There is no automatic fallback and only one token format.
- **Amendment A (A0, S1741).** The original text asked for the HSM protection level, which Cloud KMS does not offer for Ed25519. Rather than change the Gate 1 algorithm to one Cloud HSM supports (ES256 was the practical candidate), the keys use the SOFTWARE level. Council approved this 3/3 (GLM and DeepSeek APPROVE_WITH_NITS, Gemini APPROVE). Chunk A does not start until a live A0 record shows a SOFTWARE-level Ed25519 key version, a KMS signature, and successful Go and Python verification.

### 8.2 Signing service

- **Deployment.** A new Railway service, `gateway-signer`, with no public ingress. It is reachable only on the private network from `ai-market-backend`, which authenticates with a dedicated Infisical-held token.
- **Credentials.** It alone holds the KMS service-account credential. The API process never does.
- **Interface.** Two operations: `sign_permission_key(claims)` (permissions, revocations, prepares) and `sign_listing_key(claims)` (offers, unoffers, describes, minimum version). Each validates the claim schema for its `typ`, refuses a `td` more than 25 hours out, rate-limits per gateway, and appends every signature request (claims only) to its own log.
- **Availability.** If the signer is down, permissions and offers fail closed with `503 signer_unavailable`; nothing is issued unsigned.
- **Rotation.** New key versions are announced with `key_rotation` messages signed by the outgoing version. Gateways accept both versions for 7 days.

## 9. Backend (chunk A) data and workers

- **One migration, additive only.** New tables:
  - `gateways(id, seller_user_id, party_id, name, public_key, status, status_reason, version, last_seen_at, door_url, identity_ack_at, egress_state, egress_checked_at, created_at, revoked_at)`
  - `gateway_pairing_codes(code_hmac, seller_user_id, expires_at, used_at)`
  - `gateway_pair_attempts(source_address, attempted_at, ok)`
  - `gateway_files(gateway_id, file_id, display_name, size_bytes, media_type, content_commitment, generation, first_seen_at, changed_at, deleted_at)`
  - `gateway_file_descriptions(gateway_id, file_id, state, confirmation_id, requested_at, described_at, sha256, row_count, columns jsonb, failure_code)`
  - `gateway_messages(gateway_id, seq, received_at, message_type, body jsonb, prev_hash, signature)`, append-only; receipts live here and nowhere else (DeepSeek SIMPLER)
  - `gateway_door_checks(gateway_id, door_url, checked_at, state, failure_code, certificate_flags)`
  - `gateway_offers(gateway_id, file_id, sha256, listing_version_id, instruction_id, op, sent_at, acked_at, ack_refusal)`
  - `gateway_permissions(jti, order_id, gateway_id, file_id, sha256, sd, td, ro, issued_at, revoked_at)`
  - `gateway_order_files(order_id, file_id, state, transmitted_bytes, last_receipt_seq, complete_receipt_seq)`
  - `gateway_delivery_problems(id, order_id, category, file_ids jsonb, note, opened_by, opened_at, dispute_case_id, state[open|refund_pending|resolved], resolution, refund_cents, refund_baseline_cents, refund_pending_at, refund_alerted_at, pending_file_ids jsonb, resolved_by, resolved_at)`, with at most one unresolved row per order (a partial unique index on `order_id` where `state <> 'resolved'`)
- **Where the file SHA-256 is recorded.** Listing versions record each gateway file's `sha256` in the existing `listing_version_members` manifest contract (kept by the S1737 deletion spec), with `source = {"type": "gateway", "gateway_id", "file_id"}`.
- **Door-check worker.** A Celery beat task every 5 minutes on a dedicated worker service whose egress is restricted to public addresses. It implements Gate 1 §3 step 3 and the public-global-unicast rule (§4).
- **Refund watch.** `gateway_refund_watch` (§2.3) runs every 15 minutes on the backend's ordinary Celery worker, not on the door-check worker.
- **Canary correlation.** The same worker reads the canary DNS and host logs every 5 minutes and marks a gateway `open` on any hit for its labels (§6.7).
- **Channel handler.** Runs in the API process (WebSocket). It writes messages to `gateway_messages`, updates the tables above, and never logs or stores anything that phase 1 does not carry.
- **Settlement.** A complete matching receipt sets the file's delivery state. When every file is delivered, the order becomes `delivered` and the existing hold and settlement proceed. `delivery_method = direct` is reused. `order_payout_eligibility` gains the reasons `gateway_problem_open` and `gateway_delivery_incomplete` (§2.3), and uses the shared `payout_hold_until` helper (§2.1).
- **Flag.** `AIM_GATEWAY_ENABLED` (off) gates every route, the worker and the channel.

## 10. Test plans and golden vectors

- **Golden vectors.** `aim-data-gateway/contract/vectors/*.json`, one file per message type and token. Each holds a test-only key pair, the input, the exact bytes and the expected verdict. The backend holds a byte-identical copy under `tests/contract/gateway/`, and a required CI check in each repository compares the copy's SHA-256 with the other side's pinned value (the S1732 preview-contract pattern). Vectors include the null-rate boundaries (249 and 250 nulls in 10,000 rows; 9,749 and 9,750; zero rows), the default display name, and interval lengths at byte 0, byte 1, the last byte, suffix and open-ended ranges.
- **Chunk A (backend):**
  - every route in §1 and §2, success and error codes;
  - pairing: single use, the attempt limits, the stored value is an HMAC;
  - door check against public, private, loopback, metadata and redirect cases, plus the certificate flags;
  - the usable-gateway predicate refuses the first permission and a re-issue when the gateway is offline, revoked, unsupported, or its door check is failed, stale or for a previous `door_url`; a fresh pass for the current URL succeeds;
  - re-issue `restart` refused with `restart_unavailable` once any byte has two serves, and `resume` still allowed;
  - permission issue and re-issue with revocation, prepare, and the confirmation timeout;
  - receipt aggregation into a complete matching receipt; `blocks_verified = false` or a short `transmitted` never completes;
  - problems: a `missing_data` problem on a `pending_delivery` order freezes payout (reasons `gateway_problem_open` and `disputed`) and opens a `DisputeCase`; open, release and reopen on one order freezes payout again; release works on a `pending_delivery` order through `resolve_gateway_problem` and payout then becomes eligible; on a transaction order with `escrow_hold_until = null`, a problem after a complete receipt but before confirmation plus 48 hours succeeds, and after it returns `problem_window_closed`; a problem on a `pending_delivery` order after the hold has passed succeeds; a `no_hold` legacy order that is `completed` returns `problem_window_closed`; a transaction order before its confirmation event succeeds; the resolve route returns `403` for a non-admin and records `resolved_by`; release, full refund, partial refund and an invalid outcome leave the problem, the `DisputeCase` and the money state consistent, including a refund whose effects arrive later; the generic CRM resolve of a linked case is refused while the problem is `open` and while it is `refund_pending`; a refund whose effects are applied resolves the problem and the case together; `gateway_refund_watch` raises no alert before 72 hours from `refund_pending_at`, exactly one at or after it, and none once the refund has applied; `reopen` returns the problem to `open` and resets the watch; `reopen` on a non-`refund_pending` problem and `released` with `refund_cents` are refused; a refund of the requested amount resolves exactly that problem and its case; a full refund decided after an earlier partial refund resolves once the remaining balance applies; a file reported while a partial refund is pending is carried into a new `open` problem when that refund resolves, and payout stays frozen; the same file, with the refund instead reopened and then released, stays in the reopened problem and payout stays frozen until that problem is decided; a full refund after an earlier partial refund with a file reported meanwhile resolves the first problem and opens one for the file; while a short refund, a refund while the problem is `open`, and a replayed refund event leave it unchanged and raise a support task; a forced failure after the task update rolls back the problem, case, task and audit rows together; `corrupted` stores the validated file ids; an unknown file id is refused; a second problem adds to the open one; after the hold the window is closed; release and refund both clear it; payout refuses a gateway order without complete receipts (`gateway_delivery_incomplete`);
  - revoking a gateway with open orders needs confirmation and opens system problems;
  - the flag-off 404s;
  - the migration upgrade and downgrade on a disposable database;
  - no buyer identifier in any seller-visible payload (golden check).
- **Chunk B (gateway):**
  - every acceptance item in Gate 1 §9 that the gateway owns;
  - the planted-marker fixture (Gate 1 acceptance 3), and no file name or path in any phase-1 payload without an alias;
  - symlink escape, special files and the 100k cap;
  - CSV, JSON Lines and Parquet profiles, including the Parquet fixtures from Event `s1741-gateway-go-parquet-evidence`;
  - the Range state machine: overlap, suffix, open-ended, multi-range 416, the third serve refused, restart persistence, re-issue resume;
  - reservations: a disconnect before the first byte and a disconnect halfway each leave the unwritten bytes servable and produce no complete receipt; a crash keeps at most one 8 MiB window reserved;
  - an interrupted download that resumes at a nonzero offset, across a re-issue, produces a complete matching receipt;
  - after one complete download and a restart, every further request under that `jti` is refused, including a range served only once, and exactly one complete receipt is sent;
  - at 1,024 intervals, with and without other open isolated requests, a new isolated request is refused with `coverage_fragmented`; a gap-filling request, a `resume` from `resume_offset` and a `restart` from 0 are admitted; short writes and concurrent requests at the boundary never leave more than 1,025 intervals;
  - a same-size, same-mtime change is caught at the first block served, including under fragmented Range requests from nonzero offsets;
  - D12: a valid permission for an unoffered file, an offer signed with the permission key, a file outside the ceiling, a file id collision across sources, and an unoffer after bind (the bound `jti` finishes; no new bind);
  - unsigned, replayed, expired or wrong-key `describe` is refused;
  - the door answers `OPTIONS` with `405` and no CORS headers, and accepts the query token and the header token;
  - the canary, every row of the §6.7 table, including SERVFAIL, a server-side hit, an allowlisting proxy (closed) and an open proxy (open);
  - a static scan listing every network dial site (one channel client plus the canary);
  - two reproducible builds with an identical digest;
  - the start-up self-check refuses a writable root, a non-dropped capability, UID 0 and a mounted Docker socket.
- **Chunk C (website):**
  - every screen against the §1 and §2 shapes, using mocked responses built from the golden vectors;
  - every blocker message;
  - a browser download by navigation, interrupted and resumed, from a test door; and a browser re-issue that restarts from byte 0 and completes;
  - "Verify file" on a 2 GiB file in a headless browser;
  - a `coverage_exhausted` file shows "Report a problem" and no re-issue;
  - no buyer identifier rendered on seller pages, and no path rendered anywhere.
- **Chunk D (repository and release; GLM 8):** CI fails when the compose file loses any §6.1 runtime constraint or gains a socket, host network or privileged setting; when `go.sum` verification fails or a dependency is not pinned (`-mod=readonly`, `GOFLAGS=-mod=readonly`, `GONOSUMDB` empty); when `LICENSE` is not Apache 2.0; or when the repository is not public. The SBOM and provenance verify, and cosign signature verification passes. The security documents are present.
- **Chunk E (money path):** as Gate 1 §8, plus the problem freeze and `gateway_delivery_incomplete` in the money-path environment: open a problem during delivery, prove the payout is refused, resolve it, prove the payout then proceeds.

## 11. Language and dependency budget (Gate 1 D11)

- **Language.** **Go.** Arrow Go v18.8.0 read all five Parquet fixtures correctly (Event `s1741-gateway-go-parquet-evidence`). Its `pqarrow` build, though, is 41 MB and compiles 19 third-party modules, including grpc and protobuf.
- **Budget (DeepSeek 5, Gemini 3).** Gate 1 D11 stands unchanged: at most 12 direct runtime dependencies and under 5,000 lines of non-test code, measured by CI. Gate 2 adds two limits on the whole binary: **at most 25 compiled third-party modules** (`go list -deps`, `golang.org/x/*` included), and **no grpc, no protobuf and no cgo**.
- **Build step B0.** Build a skeleton that links every library the gateway will ship (Parquet, SQLite, WebSocket, TOML), with the Parquet profile tried both as `github.com/parquet-go/parquet-go` and as arrow-go's `parquet/file` package (without `pqarrow`). Keep the combination that passes the fixtures inside every limit. If none fits, B0 stops and the choice comes back to review. It is not waived silently. Gemini's measurement (arrow-go `parquet/file` alone: 14 modules, no grpc or protobuf) is the starting point.

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

A0 (KMS algorithm check) → A, and in parallel B0 (library budget) → B, both against the frozen §3 vectors → C (after A's routes exist behind the flag) → D → E → F (separate spec).

**Owners:** Vulcan owns every chunk, A to F (Max, S1749, Event Ledger 78fff844). Mars gives brief help on request only. The original split (Vulcan A, B and D; Mars C; both E) is superseded.

## 14. Review questions (Gate 2 R4, carried into R5)

1. §2.3: is the problem window now one unambiguous rule: always open before full delivery, and tied to the three hold states after it?
2. §2.3: does the single admin resolve path, with `refund_pending` and the refused generic CRM resolve, keep the problem, the support case and the money consistent?
3. §6.5: does admission counting open requests bound the interval list under short writes and concurrency?
4. §2.1: is sending the twice-served browser case to the problem path, as Gate 1 §3 step 4 says, acceptable?
5. Is anything in R4 a drift from a Gate 1 decision?
6. SIMPLER / BETTER: what here could be removed without breaking a Gate 1 decision?
7. R7: with §20 (remaining-balance target, files reported during `refund_pending`), do the refund binding (by applied totals under the order money lock), the refund watch and the `reopen` rules in §2.3 close GLM R5 1–3 and MP R5 1–2, and are they accurate to the pinned backend?

## 15. R1 fold log

| Finding | Where it landed |
| --- | --- |
| GLM 1 (HIGH, CORS), Mars 1 | §2.1 browser URL; §6.6 no CORS, `405` for `OPTIONS`, headers |
| GLM 2 (HIGH, dispute), DeepSeek 2, MP 3, Gemini 1–2, Mars 6 | §2.3 problem route; §9 table; §10 tests |
| GLM 3 (HIGH, bind hash), DeepSeek 1, MP 2 | §6.2 block list; §6.6 block verification; §3.4 `blocks_verified` |
| MP 1 (HIGH, reserved vs transmitted) | §6.5 reserve-write-settle; §3.4 `transmitted` |
| GLM 4, DeepSeek 4 (D12 in serve order) | §6.6 serve order |
| GLM 5 (initial issuance gate) | §1.1 usable predicate; §2.1; §7.2 prepare |
| GLM 6, DeepSeek 3, MP 5 (D9) | §1.2 default name and null-rate rule; §6.3; §10 vectors |
| GLM 7 (SERVFAIL), MP 4 (CONNECT) | §6.7 table and proxy probe; §4 |
| GLM 8 (hardening, release) | §6.1 runtime constraints and self-check; §10 chunk D |
| GLM 9 (ES256 fallback) | §8.1: A0 failure stops the build |
| GLM 10 (pairing code) | §1.1 code, storage, attempt limits; §9 |
| GLM 11 (coverage exhausted) | §2.1, §2.2, §6.5 |
| GLM 12 (intervals) | §0 |
| DeepSeek 5, Gemini 3 (budget) | §11 |
| DeepSeek 6 (id truncation) | §3.5 |
| MP Q3, Gemini BETTER, GLM Q3 (describe binding) | §1.2, §3.2 signed `describe` with confirmation id |
| GLM SIMPLER (drop `rescan`) | §6.2, §7.3 |
| GLM BETTER (prepare before issue) | §3.3, §7.2 |
| DeepSeek SIMPLER (receipts in `gateway_messages`) | §9 |
| Mars 2–5, 7–9 | §1.1, §1.2, §1.3, §0 |

## 16. R2 fold log

| Finding | Where it landed |
| --- | --- |
| GLM R2 1 (HIGH), DeepSeek R2 1 (`jti` closing) | §6.5 closing rule; §10 chunk B test |
| GLM R2 2 (HIGH), MP R2 3, DeepSeek R2 4 (hold clock) | §2.1 `payout_hold_until`; §2.3 window; §10 chunk A test |
| GLM R2 3 (HIGH, repeated problems) | §2.3 opening clears `dispute_resolved_at`; `gateway_problem_open` payout reason; §10 |
| MP R2 1 (HIGH, release path) | §2.3 `resolve_gateway_problem` and admin route; §10 |
| GLM R2 4 (door URL change) | §1.1 door check bound to the current URL; §9; §10 |
| GLM R2 5 (gateway TLS), GLM R2 SIMPLER | §6.1 TLS config removed |
| MP R2 2 (browser resume across re-issue) | §2.1, §2.2 `restart` and `resume` modes, and the header command |
| MP R2 4 (fragmentation), MP R2 SIMPLER | §6.5 1,024-interval limit (bound restated as 1,025 at R5); §3.3 summary-only `prepare_ack`; §3.4 |
| GLM R2 BETTER (explicit hold reason) | §2.3 `gateway_problem_open`, read from the problems table |
| DeepSeek R2 2 (fold-log attribution) | §4 |
| DeepSeek R2 3 (line number) | §2.3 |
| MP R2 BETTER (in-browser assembly across permissions) | Not adopted: it needs cross-origin fetch and CORS on the door, which R2 removed (GLM R1 1). The header command covers resume across permissions, and `restart` covers the browser. |

## 17. R3 fold log

| Finding | Where it landed |
| --- | --- |
| DeepSeek R3 1 (MEDIUM, window before delivery), MP R3 3, GLM R3 1 | §2.3 one window rule; §2.1 three hold states; §10 chunk A tests |
| MP R3 4 (CRM resolution), GLM R3 2 (admin principal) | §2.3 single admin resolve path, `refund_pending`, generic CRM resolve refused; §9; §10 |
| MP R3 2 (partial writes), DeepSeek R3 4 (`416`) | §6.5 admission counts open requests; `409 coverage_fragmented`; §10 chunk B |
| DeepSeek R3 2 (`max_serves_reached` size) | §3.4 count instead of list |
| DeepSeek R3 3 (curl offset) | §2.1 note on `-C -` |
| Gemini R3 1 (`mode` default) | §2.2 optional, defaults to `resume` |
| MP R3 1 (browser after two serves) | §2.1: Gate 1 §3 step 4 sends twice-served bytes to the problem path; the header command still fetches the missing bytes. Not changed further, as another serve would breach a settled decision. |

## 18. R4 fold log (confirmation round R5)

| Finding | Where it landed |
| --- | --- |
| GLM R4 1 (header command after a short write) | §2.1: the command is best-effort; twice-served bytes go to the problem path |
| GLM R4 2, DeepSeek R4 1, MP R4 2 (`refund_pending` guard) | §2.3: `gateway_problem_open` and the CRM guard cover `open` and `refund_pending`; §10 |
| DeepSeek R4 2 (consequence listed as a window condition) | §2.3: moved out of the window list |
| DeepSeek R4 3 (`until` state name) | §2.1: state renamed `held_until` |
| DeepSeek R4 4 (severity labels) | Recorded as reported by each round; no change |
| MP R4 1 (refund initiation) | §2.3: refunds are issued in Stripe as today and resolve the problem through the existing `charge.refunded` handler; 72-hour alert and `reopen`; §10 |
| MP R4 3 (admission could refuse a gap fill) | §6.5: extending requests always admitted; 1,025 bound; §3.4; §10 |
| MP R4 4 (nested commit in task completion) | §2.3: the non-committing variant covers the task update; §10 rollback test |

## 19. R5 fold log (R6)

| Finding | Where it landed |
| --- | --- |
| GLM R5 1, MP R5 1, DeepSeek R5 2 (refund binding and amount) | §2.3: bound by applied totals against a baseline under the order money lock; one unresolved problem per order (partial unique index, §9); metadata not relied on; §10 negative tests |
| GLM R5 2, MP R5 2 (72-hour clock and scanner) | §2.3 `refund_pending_at`, `refund_alerted_at`, `gateway_refund_watch`; §9; §10 |
| GLM R5 3 (`reopen` in the schema) | §2.3 request enum and field rules |
| GLM R5 4 ("always admitted") | §6.5: never refused for fragmentation, other checks still apply |
| DeepSeek R5 1 (historical 1,024) | §15 annotated |

## 20. R6 fold log (R7)

| Finding | Where it landed |
| --- | --- |
| MP R6 1, DeepSeek R6 1 (full refund after an earlier partial refund) | §2.3: `refund_cents` for `refunded` is the remaining balance at decision time |
| DeepSeek R6 2 (`refund_cents` rule for `refunded`) | §2.3 request field rules |
| MP R6 2 (complaint added during `refund_pending`) | §2.3 `pending_file_ids`, carried into a new `open` problem on resolution; §9; §10 |

**Final nit fold after R7** (R7: GLM APPROVE_WITH_NITS, DeepSeek APPROVE_WITH_NITS, Gemini APPROVE; MP advisory): `reopen` merges `pending_file_ids` into the problem (GLM R7 1, MP R7 1); a carried problem has the full open-path effects (DeepSeek R7 1); column types (DeepSeek R7 2); combined tests in §10.
