---
title: Delivery ACK-timeout monitor (trust-channel fulfilment, stalled transfers)
owner: vulcan
last_verified: '2026-09-21'
aliases: [ACK monitor, ack timeout, cancel_ack_monitor, schedule_ack_monitor, stalled delivery, transfer stuck receiving, T-2026-000779]
error_signatures: ["NameError: name 'uuid' is not defined", "AUTHORIZATION_MISMATCH", "MANIFEST_DELIVERY_REQUIRED"]
---

# Delivery ACK-timeout monitor (trust-channel fulfilment, stalled transfers)

## What it does

When a seller's AIM Data install streams a purchased dataset to ai.market over the trust channel, accepted chunks are acknowledged in windows (every 4th chunk and the final chunk, `ACK_WINDOW = 4`, on both the legacy and manifest routes). After each ACK the backend (`app/api/v1/endpoints/trust_websocket.py`, `_handle_fulfillment_action`) schedules a per-transfer monitor (`schedule_ack_monitor` in `app/services/fulfillment_listener_service.py`): if no further chunk arrives within 30 s it re-sends the ACK once, and after another 30 s it aborts the transfer (`FulfillmentListenerService.abort_transfer`, legacy or manifest route). The monitor is keyed by the canonical transfer UUID string; a non-UUID transfer id is never scheduled.

> The transfer this monitor watches streams the buyer's file through ai.market, which breaks the peer-to-peer delivery rule (`runbooks/data-delivery-p2p.md`). It is the live path until T-2026-000839 replaces it; keep it working, do not extend it.

A monitor stops only when the proven owner of that exact transfer ends it:

- a chunk, complete or error frame, after the `(transfer_id, order_id, seller_id)` session is confirmed (`_legacy_handle_chunk`, `_legacy_handle_complete`, `_legacy_handle_error`, `ManifestFulfillment.dispatch`);
- with `MULTI_FILE_DATASETS_ENABLED` off, an owner complete/error for an existing manifest transfer stops its own monitor before the frame is refused with `MANIFEST_DELIVERY_REQUIRED`;
- manifest metadata replacing an older receiving session stops that session's monitor only when it belongs to the same seller.

On metadata, complete and error frames, malformed transfer, order or listing ids are refused with `AUTHORIZATION_MISMATCH` before any database read, with a rollback, and cancel nothing. A chunk frame with a malformed `transfer_id` fails earlier, in `validate_authorization_tuple`, and comes back as the raw UUID parse error string (no database read, nothing cancelled).

## History

- Until 2026-09-21 any authenticated device could stop another seller's monitor by quoting its transfer id in a complete/error frame: the cancel ran before authorization. Council caught it on 2026-09-08 (T-2026-000779), but that fold never merged (PR #350 merged without it). Fixed by ai-market-backend PR #439 (merge `c5b10b48`, S1734), Council Gate 3 unanimous (GLM, DeepSeek, Gemini, two rounds).
- Also until `c5b10b48`: the abort callback referenced `uuid` without importing it, so a monitor that reached its abort stage raised `NameError: name 'uuid' is not defined` and the stalled transfer was never aborted. Transfers stuck in `receiving` from before that deploy were not cleaned up by the monitor.

## When it breaks

| Symptom | Likely cause | Check |
| --- | --- | --- |
| Transfer stays `receiving` long after the seller stopped sending | Monitor never scheduled (no ACK sent, or non-UUID id), or the backend restarted: monitors live in process memory and do not survive a deploy | `SELECT transfer_id, status, updated_at FROM transfer_sessions WHERE status='receiving' ORDER BY updated_at` read-only; compare with the last deploy time |
| Log shows `NameError: name 'uuid' is not defined` in `_abort_transfer` | Backend older than `c5b10b48` | Confirm the deployed commit (`railway status --json`, see `sysadmin.md`) |
| Seller's frames refused with `AUTHORIZATION_MISMATCH` | Frame names a transfer/order/listing the device's seller does not own, or an id is not a UUID (chunk frames return the raw UUID parse error instead) | Compare the frame ids with `transfer_sessions`/`orders` rows for that seller |
| Owner's complete refused with `MANIFEST_DELIVERY_REQUIRED` | Multi-file delivery switched off while a manifest order is mid-delivery; the owner's monitor is still stopped | Expected; re-enable `MULTI_FILE_DATASETS_ENABLED` or let the order finish on the manifest route |

Tests that pin this behaviour: `tests/test_ack_monitor_authorization_s1734.py` (25 tests). `tests/test_fulfillment_listener.py` (8 failures) and `tests/test_s1681_s3_delivery.py` (83 failures) fail locally on Titan-1 identically on base `d4582fe9` and on the fix (both re-run by Vulcan S1734); CI Gold Path is the gate.

## Related

- `trust-channel.md` (control plane; fulfilment logic is out of its scope)
- `council-gate-process.md` (Tier 3 gate used for this fix)
