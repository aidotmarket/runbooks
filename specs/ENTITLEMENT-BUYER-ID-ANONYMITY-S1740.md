# Download entitlement token must not carry the buyer's user id (S1740)

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
- So the two formats do not interoperate today. This buyer→seller-node path is not live end to end, and the leak is latent. Once someone finishes "M3" integration it becomes real, and the shared field list is where it would leak.

## Change

1. **Backend (ai-market-backend):** remove `buyer_id` from the entitlement payload in `generate_download_token`. Ownership is already enforced before signing (`:76`, `row["buyer_id"] != user_id` → "Not your order"), and the order id identifies the purchase. Keep the audit `actor_id=user_id` (server-side only). Add a test: the token contains no `buyer_id` and no user-identifying value, and `validate_download_token` still accepts it.
2. **AIM Data (aim-data):** remove `buyer_id` from the `required` tuple and from the docstring in `entitlement_service.py`. Change the log line in `raw_listings.py:451` to `file_id` and `order_id` only. Add a test: a token without `buyer_id` validates, and the log never contains a buyer identifier.
3. **Runbook:** add the entitlement token to the surfaces listed in `runbooks/counterparty-anonymity.md`.

## Ordering and compatibility

The two formats don't interoperate today, so no live download can break and the two repos can ship independently. For the day M3 integration lands: the AIM Data change makes the node tolerant (no `buyer_id` needed), and any old node that still requires `buyer_id` would reject a new token, which fails closed. To keep old nodes working, M3 would ship after this AIM Data release reaches the fleet. Record that constraint in the aim-data release notes. Nothing else changes: no schema, no migration, no flag.

## Out of scope

- Finishing M3, the buyer→seller-node redirect.
- The `delivery_service` JWT (`delivery_service.py:~250`). It carries `buyer_id`, but it travels only between the buyer and ai.market's trust-channel proxy and never reaches the seller device. The seller-facing trust frames had `buyer_id` removed in d78f2d08.

## Acceptance

- `git grep -n buyer_id` in the token builder and in AIM Data's entitlement and raw-listings files finds no remaining payload or log use.
- Focused tests pass in both repos, with no new failures versus main.
- Gate 3 unanimous on each repo's diff.
