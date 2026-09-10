# BQ-BUYER-DOWNLOAD-UNIFICATION-S1711 — Gate 1 draft (joint: mars + vulcan)

Status: DRAFT, not dispatched. Authority: Max decision 2026-09-10 (Event Ledger `8510ec8c-191f-4e4c-9dfb-bf294eb7624b`): agents (API-key buyers) must be able to buy and download Seller Workspace listings; unify buyer download where it makes sense; Mars and Vulcan must agree the design. Gated after BQ-MONEY-PATH-DELIVERY-LEG-S1681's first exit-2 run and Seller Workspace W5. Money path + customer data: unanimous CC/GLM/DeepSeek at Gate 1; builder MP.

Source identities for every `file:line` below: backend `31f09b5666314aa375d41d269be52552d518ba94`, frontend `943429b586fa4acd55f81f23ded5005cbcf841e1` unless stated. Re-verify with `git show` before dispatch.

## 1. What exists today (both instances to confirm or correct)

| Buyer intent | Device-delivered / legacy (mars) | Seller Workspace (vulcan) |
| --- | --- | --- |
| Start a download | `POST /orders/{id}/download` (`orders.py:260–311`) returns one of three shapes: gatekeeper token, `S3DownloadTokenResponse`, `s3_scoped_credential` dict | `POST /seller-workspace/orders/{id}/prepare` then `POST /seller-workspace/orders/{id}/download` (`seller_workspace_delivery.py:35–61`) returns `WorkspaceDownloadResponse` (session + `files[]`) |
| Fetch bytes | `POST /orders/{id}/download/redeem` → 303 to the device presign (`:313–323`, S1681 G3) | `POST /seller-workspace/orders/{id}/download/{session}/files/{index}` → `DirectDownloadFile` grant (`:64+`) |
| Refresh | `/download/refresh` (`:325–335`), `/delivery/refresh` (`:337–355`), `/refresh` (`:809+`) | new session |
| Other | `POST /download-token` (`:357+`), `GET /download` (`:419+`), `GET /access` (`:508+`) | — |
| Auth | `get_current_user_flexible` (session or API key) | `require_buyer_session` → JWT only (`:20–23`) |
| Limits | `RateLimiter(cost=10)` on `/refresh` only | discovery limiter (user + IP + global) on prepare/download; file-delivery limiter on grants |
| Frontend | `api/orders.ts` (download, refresh, delivery/refresh); order page branches on `order.workspace_delivery` (`app/dashboard/orders/[id]/page.tsx:122–147`); S1681 redeem is NOT wired | `api/sellerWorkspaceDownload.ts` (prepare, download, file) |
| Agent API | `agent/router.py:880–905` builds a legacy gatekeeper URL from `issue_download_token` | not reachable |

## 2. Target (proposal; vulcan to amend)

- One entry: `POST /orders/{id}/download` for every listing. `OrderService` dispatches on the order's source (the same predicate `FulfillmentService` uses at `fulfillment_service.py:177–178`, `is_workspace_source(order.source_delivery)`).
- One envelope: `{delivery_kind, files: [{index, filename, size_bytes, url | grant_path, expires_at}], downloads_remaining, expires_at, refresh_allowed}`; device deliveries have one file whose `url` is produced by today's redeem logic; Workspace responses carry `grant_path` per file exactly as today's session/grant model, so no Workspace delivery mechanics change.
- One auth dependency: `get_current_user_flexible` on every buyer download route. Workspace per-file grants, the discovery and file-delivery limiters (keyed user + IP), and any browser step-up remain inside `SellerWorkspaceDeliveryService` as policy. If W1's session-only rule protected something specific (vulcan: name it), that protection moves into the service, not the route.
- One refresh: `POST /orders/{id}/download/refresh`; `/delivery/refresh` and `/refresh` become aliases for one release, then removed. `/download-token` and `GET /download` (gatekeeper) removed after confirming no production caller (search: frontend, agent router, MCP tools, AIM Data, docs).
- Aliases: `/seller-workspace/orders/*` kept for one release for the current web app, then removed.
- Frontend: one download component driven by the envelope; removes the `workspace_delivery` branch; wires the device redeem flow (gap today).
- Agent API: `DataDelivery` built from the envelope (fixes `agent/router.py:899`).

## 3. Open points for vulcan

1. Anything in W5 (AWS publication/delivery) that assumes `require_buyer_session` or the `/seller-workspace/orders/*` path shape.
2. Grant semantics that must survive verbatim (session lifetime, per-file expiry, index bounds `MAX_SELECTION_FILES`, limiter keys).
3. Whether a browser step-up is required for multi-file grants and where it should live.
4. Whether `prepare` (source materialisation) should be implicit inside the unified `download` or stay a separate call.

## 4. Non-goals

Delivery mechanics (Trust Channel, Workspace grants, presign policies), seller-side routes, entitlement/refund rules.

## 5. Tests (minimum)

Every source kind × auth kind (session, API key, none); entitlement, refund, revocation and expiry negatives on the unified route; limiter behaviour preserved for Workspace; alias parity for one release; frontend order page renders both kinds from the envelope; agent `DataDelivery` for both kinds.
