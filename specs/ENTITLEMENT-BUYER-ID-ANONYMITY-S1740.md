# Download tokens that reach the seller must not carry the buyer's user id (S1740)

**BQ:** `build:bq-entitlement-buyer-id-anonymity-s1740` (P1). **Rule:** CORE P5/S1 and Max's anonymity decision c3af20e0: a seller never learns the buyer's identity. The anonymity release is live at backend `d78f2d08`, and `runbooks/counterparty-anonymity.md` in ai-market-backend lists its surfaces. **Origin:** combined Gate 3 R3, question 6 (Gemini 021744): this is a counterparty leak, but not a blocker for that merge; it is a cross-repo follow-up. **Risk class:** customer data, so the design and the build each need a unanimous Council (GLM, DeepSeek, Gemini).

## Ground truth (read S1740, ai-market-backend `57e2d293`, aim-data `6529e1ed`)

- The backend issues the token. `POST /api/v1/orders/{order_id}/download-token` (`orders.py:364`) and the single-file download route (`orders.py:431`, calling `generate_download_token` at `:499`) call `RawDownloadService.generate_download_token` (`raw_download_service.py:46`).
  - The payload is `order_id, listing_id, buyer_id, file_path, file_hash, nonce, issued_at, expires_at`. `buyer_id` is `str(user_id)` (`:142`).
  - The payload is signed as hex HMAC-SHA256 over the sorted JSON and returned to the buyer as a JSON string (`:139-178`).
  - The docstring says the buyer presents it "to the seller's VZ for the actual file download". The response carries `redirect_url: None` and the note "VZ redirect URL available after M3 integration" (`orders.py` ~515).
- The backend validates the token in `validate_download_token` (`raw_download_service.py:182-232`). It checks the signature, expiry, licence acceptance and nonce, and never reads `buyer_id`. Nothing in `app` calls it today.
- The seller's AIM Data validates it at `GET /download/{file_id}` (`app/routers/raw_listings.py:421-458`) via `EntitlementService.validate_entitlement` (`entitlement_service.py:~80-150`).
  - It expects a different wire format: `Bearer base64(json).base64(sig)` with a derived shared secret.
  - It requires `buyer_id` among its fields (`:128`) and writes it to the seller's log: "Serving raw file %s to buyer %s" (`raw_listings.py:451`).
- A second, live token in the same family: the delivery JWT from `create_delivery_token` (`app/core/security.py:188-267`).
  - Its payload carries `"sub": buyer_id` (`:240`).
  - When the order's `delivery_config.gatekeeper_url` is set, the token is appended as a query parameter to the seller-controlled URL `{gatekeeper_url}/download?token=...` (`:265`). The docstring says it "is then presented to the seller's Gatekeeper Worker" (`:205-206`).
  - It is issued by `OrderService.issue_download_token` (`order_service.py:1579`, `buyer_id=str(buyer_id)`) and a second call at `:1669`, and it is returned by `POST /api/v1/orders/{order_id}/download` (`orders.py:260-306`).
  - It is redeemed back on ai.market by `redeem_download_token` (`order_service.py:~1702-1712`), which checks `claims["sub"] == str(buyer_id)`.
  - Production (S1740, read-only, 2026-09-23 06:04:40 UTC: `select count(*) filter (where delivery_config ? 'gatekeeper_url'), count(*) from orders` → `0 | 5`): no order carries a `gatekeeper_url`, so no seller has received one yet. The code path is live and covered by tests (`test_s1681_s3_delivery.py`, `test_delivery_r1_fold.py`).
- So the two entitlement formats do not interoperate today. This buyer→seller-node path is not live end to end, and the leak is latent. Once someone finishes "M3" integration it becomes real, and the shared field list is where it would leak.

## Change

1. **Backend, delivery JWT (ai-market-backend `app/core/security.py`, `app/services/order_service.py`):**
   - New delivery JWTs carry no `sub` at all, and no buyer-derived value: no hash and no pseudonym. That follows `runbooks/counterparty-anonymity.md`: counterparty-visible surfaces use order and listing references only.
   - `redeem_download_token` drops its `claims["sub"] == str(buyer_id)` comparison. Ownership is already enforced by `_authorize_download_access(order_id, buyer_id, ...)` (`order_service.py:~1713`) against the authenticated buyer. The signed `order_id` claim must still equal the path order, and the `jti` reservation check stays.
   - Tokens issued before the release still carry `sub = buyer UUID`. They stay valid for their existing TTL, because redeem simply ignores `sub`. No buyer loses access, and no key-coupling question arises.
   - Tests: a new token's decoded payload contains neither the buyer UUID nor any `sub`; redeem by another authenticated user is refused (403); a pre-change token with a UUID `sub` still redeems within its TTL.
2. **Backend, entitlement token (ai-market-backend):** remove `buyer_id` from the entitlement payload in `generate_download_token`. Ownership is already enforced before signing (`:76`, `row["buyer_id"] != user_id` → "Not your order"), and the order id identifies the purchase. Keep the audit `actor_id=user_id` (server-side only). Add a test: the token contains no `buyer_id` and no user-identifying value, and `validate_download_token` still accepts it.
3. **AIM Data (aim-data):** remove `buyer_id` from the `required` tuple and from the docstring in `entitlement_service.py`. Change the log line in `raw_listings.py:451` to `file_id` and `order_id` only. Add a test: a token without `buyer_id` validates, and the log never contains a buyer identifier.
4. **Governing specs:** add a supersession note at the top of `ai-market-backend/specs/BQ-VZ-RAW-DELIVERY.md` and `aim-data/specs/BQ-AIM-RAW-LISTINGS.md`. The note names this spec as the controlling anonymity amendment, and strikes or marks every clause that puts `buyer_id` into a seller-visible payload, required claim, query parameter, Trust request or log (backend spec ~`:31-53`, `:214-223`, `:245-250`, `:315-322`, `:349-362`; AIM Data spec ~`:142-160`). Server-side audit `actor_id` stays.
5. **Runbook:** add both tokens to the surfaces listed in `runbooks/counterparty-anonymity.md`.

## Ordering and compatibility

The two formats don't interoperate today, so no live download can break and the two repos can ship independently. For the day M3 integration lands: the AIM Data change makes the node tolerant (no `buyer_id` needed), and any old node that still requires `buyer_id` would reject a new token, which fails closed. To keep old nodes working, M3 would ship after this AIM Data release reaches the fleet. The aim-data build adds this constraint to `CHANGELOG.md` under the next release, and the M3 readiness check (whenever M3 is specced) must confirm the fleet's reported AIM Data version is at least that release. Nothing else changes: no schema, no migration, no flag.

## Out of scope

- Finishing M3, the buyer→seller-node redirect.
- The legacy `JWTService.create_download_token` (`app/services/jwt_service.py:11-35`, schema `app/schemas/jwt_schema.py:19-26`) signs a plaintext `user_id`. S1740 found no call site in `app`. The backend build deletes the unused producer and its schema field if it confirms there are still no callers. If a caller exists, it removes `user_id` from the payload instead, and the build report names the caller.
- The `delivery_service` JWT (`delivery_service.py:~250`). It carries `buyer_id`, but it travels only between the buyer and ai.market's trust-channel proxy and never reaches the seller device. The seller-facing trust frames had `buyer_id` removed in d78f2d08.

## Acceptance

- Neither token's signed payload, nor the returned token or URL, nor the node's log, contains `buyer_id` or the buyer UUID. The ownership check and the SQL select of `buyer_id` inside `raw_download_service.py` stay, because they are server-side authorization.
- Focused tests pass in both repos, with no new failures versus main.
- Gate 3 unanimous on each repo's diff.
