# bq-connector-oauth: MCP authorization server for connect.ai.market

Status: GATE 1 DRAFT v1 (2026-09-23). Not a build authorisation until Gate 1 passes.
Tier: **CORE S3 Tier 3** (auth + customer data + new external egress for CIMD fetches). Unanimous GLM + DeepSeek + Gemini; MP builds; Tier 3 cap 3 rounds (`runbooks/council-gate-process.md`, "Rational-use tiering").
Parent design (authority): `specs/BQ-CUSTOMER-MCP-CONNECTOR-DESIGN.md` v3 §3 "Authorization server" and "Org binding", §8 row P0 `bq-connector-oauth`. Max decisions D1–D9 there are binding here.
Precedent in-repo: `specs/BQ-AIM-DATA-SIGN-IN-WITH-AI-MARKET-S1659-GATE1.md` (first-party PKCE + frontend consent + binding cookie), runbook `aim-data-sign-in-with-ai-market.md`.

Source identity read for this brief (read-only, nothing fetched or modified):
- backend `ai-market-backend` main checkout `203bcf567` (same SHA the design cites);
- frontend `ai-market-frontend` `origin/main` `bae9399` (local checkout is on a build branch; all frontend citations are `origin/main`);
- deleted CRM MCP OAuth: backend `git show d2ff9c8b2^:app/mcp/oauth.py` (added `7bece0ec7` S146, removed `d2ff9c8b2` 2026-07-02);
- internal gateway `koskadeux-mcp` `3715b33957` (`gateway_server.py`, `simple_oauth.py`).
UNVERIFIED marks every claim not proven from those trees (notably anything about production rows).

## 0. Business summary (plain English)

People will connect Claude, ChatGPT, Cursor and similar apps to their ai.market account by pasting one address, `https://connect.ai.market/mcp`. The app sends them to ai.market to sign in (or sign up), shows them exactly which app is asking, what it may do and for which organisation, and asks them to approve. The app then gets a key that only works on the connector, lasts one hour and is renewed quietly; the person can see and cut off every connected app from Settings, and changing their password or two-factor setting cuts them all off automatically. Nothing about how AIM Data signs in today changes.

## 1. Problem

The directory listings (design §7) require standards-compliant OAuth 2.1 for remote MCP servers: RFC 9728 discovery from a 401, RFC 8414 metadata, PKCE S256, client registration by CIMD or DCR, audience-bound tokens. ai.market has no such issuer. The existing "OAuth 2.0 provider" cannot be extended into one:

1. **It cannot issue a user token to any third-party client today.** `POST /api/v1/oauth/token` hands every non-AIM-Data request to the client-credentials handler (`app/api/v1/endpoints/oauth.py:393-399` → `app/api/v1/endpoints/oauth_clients.py:159-163`, which rejects any `grant_type` other than `client_credentials`). `OAuthService.exchange_code_for_tokens`, `refresh_tokens` and `revoke_token` (`app/services/oauth_service.py:187`, `:272`, `:323`) have **no callers** (grep of `app/`). `POST /oauth/revoke` is documented (`oauth.py:13`) but not routed.
2. **No browser login.** `/authorize` reads the user only from an `Authorization: Bearer` header (`oauth.py:61-78`, "For MVP ... pass their Bearer token in a header"); a browser never sends one, so an unauthenticated user gets a static 401 page (`oauth.py:181-210`). The consent `<form>` POST (`oauth.py:257-270`) also cannot carry the header, so consent can never complete from a browser (`oauth.py:310-315`).
3. **No PKCE, no metadata, no registration, no resource binding.** Authorization codes carry no challenge (`oauth_service.py:163-172`); tokens carry `sub/client_id/scope/aud="oauth_agent"` only (`oauth_service.py:365-377`); refresh returns the same refresh token with no rotation (`oauth_service.py:315-321`).
4. **The client table is locked to two trust shapes.** Migration `s1659_aim_data_oauth` adds CHECK `aim_data_client_trust` (`alembic/versions/20260907_001_aim_data_oauth.py:52-60`, applied at `:176`): a row is either a confidential `client_secret_post` non-first-party client with a secret, or exactly `aim_data_desktop_v1`. A public DCR/CIMD client (`token_endpoint_auth_method=none`) cannot be inserted into `oauth_clients` without weakening that constraint.
5. **No persisted grant, no org binding, no user-facing revocation.** `get_user_grants`/`revoke_user_grant` (`oauth_service.py:385-416`) have no route and no UI; the settings page has Profile and Security sections only (frontend `app/dashboard/settings/page.tsx:276`, `:356`).

## 2. Scope

In scope (this BQ):
- A new authorization server (AS) whose issuer is `https://connect.ai.market`, beside, and sharing no tables or code paths with, the legacy `/api/v1/oauth/*` provider.
- RFC 8414 AS metadata. RFC 9728 protected-resource metadata (PRM) and the 401 `WWW-Authenticate: Bearer resource_metadata=...` are served by `bq-connector-core` (its §5.3); this BQ supplies the issuer, `scopes_supported` and the token verifier they point at (§5.6).
- Authorization-code grant only, PKCE S256 mandatory for every client; RFC 9207 `iss` on every authorization response; RFC 8707 `resource` required and bound into the token `aud`.
- Client registration: CIMD (Client ID Metadata Document) preferred; RFC 7591 DCR fallback carrying `application_type`; verified status and client profile assigned at grant creation from core's reviewed allowlist `app/mcp/connector/profiles.yaml` (core §5.4).
- Access tokens 1 h; opaque refresh tokens rotated on every use with reuse detection → `invalid_grant` + family revocation; RFC 7009 revocation endpoint.
- Real login redirect and sign-up inside `/authorize`, via the ai.market web app, including password, magic-link, Google, GitHub, SSO-enforced orgs and 2FA.
- Consent page showing client identity (name, host, verified/unverified), scopes, and organisation; persisted grant `(user, client, org, scopes, profile, resource)` referenced by every token; live grant/user/membership check on every connector call.
- Revocation of all connector grants on password reset, 2FA enable/disable, account deactivation, membership change.
- Frontend: `/oauth/connect` consent page, login/register continuation, **Connected apps** section in `/dashboard/settings`.
- Redirect-URI policy per design §3.
- Legacy OAuth client inventory (§4) and a migration runbook (new page `runbooks/connector-oauth.md`, written in the build PR) so every existing client keeps working.

## 3. Non-goals

- Changing, migrating or deleting any legacy provider route, table row or token type (`/api/v1/oauth/*`, `oauth_clients`, `oauth_tokens`, `oauth_authorization_codes`, `aim_data_*`). The legacy open-redirect finding (§4.3) is filed as a separate ticket, not fixed here.
- Tools, `tools/list` filtering, profile→tool mapping, rate limiting, audit table, kill switches, the `/mcp` transport, SDK upgrade, PRM and the resource-side 401/403 headers: all `bq-connector-core`. This BQ supplies the verifier and grant store they consume (§5.6).
- Multi-org users (design §9; `organization_memberships.user_id` is UNIQUE, `app/models/organization.py:55`). Client-credentials, device-code, implicit, password or token-exchange grants. OpenID Connect ID tokens / `userinfo` for connector clients. `aim_` API keys on the connector (G3).
- Retiring MCPB/PyPI/FastMCP/SSE (`bq-mcp-surface-retirement`).
- Fixing `reset_password` not revoking website sessions (§4.4) beyond the connector grants; filed separately.

## 4. Current state (verified)

### 4.1 Web session model (what `/authorize` must reuse)
- Website login mints an HS256 access/refresh pair bound to an `auth_sessions` row (`app/core/security.py:29-109`; `app/services/sso.py:84-150`). Refresh rotation with family replay detection already exists (`sso.py:179-215`, `refresh_replay_detected`).
- The refresh cookie is `refresh_token`, path `/api/v1/auth`, SameSite Lax, on the API host (`app/core/auth_cookies.py:16-38`); the SPA holds the access token in memory. Therefore **no host other than the API can see the web session**; `connect.ai.market` cannot read it and must hand the browser to the web app.
- `decode_token` validates with `SECRET_KEY` and no audience (`security.py:174-181`). Verified on the pinned `python-jose==3.3.0` (`requirements.txt:19`): a token carrying any `aud` is rejected (`JWTClaimsError Invalid audience`). So aud-bearing tokens are already inert on every `get_current_user` path (`app/api/deps.py:86-94`).
- Email verification blocks password login for accounts created after 2026-07-07 (`app/api/v1/endpoints/auth.py:1221-1240`; `config.py:393-394`); OAuth and magic-link accounts count as verified.
- SSO-enforced orgs reject non-SSO sessions (`sso.py:218-251`). 2FA state is `users.totp_enabled` (`app/services/totp_service.py:99`, `:199`).

### 4.2 The working reference inside the repo: AIM Data sign-in (S1659)
`app/services/aim_data_oauth_service.py` is a correct, reviewed public-client flow and is the pattern this BQ generalises: server-side authorization transaction with hashed request id and a browser binding cookie (`:211-255`), redirect to the frontend `/oauth/authorize?request=` page, CSRF nonce issued by a metadata call (`:272-279`), consent as JSON with Origin check + Bearer web token + nonce (`:318-349`), 2FA assurance and SSO policy enforced (`:282-298`), PKCE S256 constant-time check and single-use code (`:358-383`), refresh via grant-owned family with reuse → revoke (`:392-419`). The frontend page is hard-wired to AIM Data (`app/oauth/authorize/page.tsx:7-34`, continuation regex `lib/redirect.ts:1`).

### 4.3 Legacy provider defects (reference only; not changed here)
- Open redirect: an unknown `client_id` or bad `response_type` redirects to the caller-supplied, unvalidated `redirect_uri` (`oauth.py:131-143` via `_oauth_error_redirect`, `:473-486`). File as ticket; this BQ never reuses `_oauth_error_redirect`.
- Refresh tokens stored with SHA-256 but not rotated (`oauth_service.py:315-321`); client secrets hashed with unsalted SHA-256 (`oauth_client_service.py:54-61`).

### 4.4 Credential-change hooks that exist today
- `POST /auth/reset-password` sets `password_hash` and commits; revokes nothing (`auth.py:740-777`, set at `:770`).
- `disable_2fa` bumps `users.last_login_at` as a "refresh floor" (`totp_service.py:199-204`); `verify_setup` (enable) does not (`:95-100`). AIM Data refresh honours that floor (`aim_data_oauth_service.py:407-410`).
- No authenticated change-password endpoint exists (grep: the only `password_hash =` writes are `auth.py:770` and `app/e2e/synthetic_accounts.py:88,104`).

### 4.5 Reference implementations outside the product path
- Deleted CRM MCP OAuth (`d2ff9c8b2^:app/mcp/oauth.py`): good shapes for RFC 9728/8414 documents (`:55-93`) and a Claude callback constant (`:44-45`, including the `claude.com` alternate). Defects not to copy: PKCE optional (`:283-293`), `sub` fixed to `"mcp_crm"` (no user, `:381-394`), refresh not rotated (`:341-378`), DCR accepts any redirect URIs (`:96-143`), authorize gated by an internal API key (`864c773af`). Its tables `mcp_auth_codes`, `mcp_refresh_tokens` (`alembic/versions/s146_mcp_oauth_tables.py`) remain in the schema, unused.
- Internal gateway `mcp.ai.market`: MCP Python SDK built-in AS (`gateway_server.py:624-650`, `AuthSettings` + `ClientRegistrationOptions`) over `simple_oauth.SimpleOAuthProvider` (JSON-file store, 1 h opaque access, 30-day refresh deleted on use without reuse detection, `simple_oauth.py:112-190`), consent by a single admin password (`gateway_server.py:726-770`). Proves Claude's connector completes SDK-shaped DCR + PKCE against us; it is not multi-user.
- Backend pins `mcp>=1.8.0,<1.9` (`requirements.txt:111`); the gateway runs `mcp>=1.28.1,<2`. The SDK upgrade is `bq-connector-core`'s.

### 4.6 Legacy OAuth client inventory (from code, migrations and seeds; production rows UNVERIFIED)

| # | Client class | How created | Tokens it gets today | Live consumer | Disposition |
|---|---|---|---|---|---|
| L1 | `aim_data_desktop_v1` (public, PKCE, loopback, first-party) | seed `aim_data_oauth_provision.py:11-45` via migration `s1659_aim_data_oauth` | web session pair via `aim.token` (`oauth.py:393-394`) | `aim-data` repo `app/services/aim_market_oauth.py:13,80` (AIM Data frozen, S1741) | Untouched. Regression test proves unchanged. |
| L2 | User-created `aim_<...>` confidential clients | `POST /api/v1/oauth/clients` (`oauth_clients.py:189-213`) | client-credentials JWT `aud="agent"` (`oauth_client_service.py:147-182`) | none found: no verifier passes `audience="agent"` and `decode_token` rejects aud tokens (§4.1). UNVERIFIED whether any external caller relies on it | Untouched. Inventory query in runbook. |
| L3 | Authorization-code clients (`redirect_uris`, `allowed_scopes`, GPT-Actions era, Phase 4.1.1) | no route: `create_client` in `oauth.py:454-466` is undecorated; `OAuthService.create_client` refuses `user_id=None` (`oauth_service.py:65-66`). Only manual SQL could create one | **none** — code exchange unreachable (§1.1); `oauth_agent` tokens accepted by `wallet.py:64` and `agent/router.py:553,584` cannot be minted | none possible | Untouched; runbook lists any rows and states they are already non-functional. |
| L4 | `mcp_<hex>` DCR clients from the deleted CRM MCP (Feb–Jul 2026) | deleted `app/mcp/oauth.py:96-143` | none (routes removed) | none | Untouched; runbook lists rows (count UNVERIFIED). |
| L5 | MCP API keys `aim_*` (`mcp_api_keys`) | not OAuth | HMAC keys for the flagged FastMCP (`app/mcp/marketplace_auth.py:77-105`) | MCPB/PyPI | Out of scope; retired by `bq-mcp-surface-retirement`. |

Consequence: "every existing OAuth client keeps working" reduces to L1 (functional) and L2 (token minting, no known consumer). The new AS touches neither table nor route, so both are preserved by construction and by the regression tests in §9.

## 5. Design

### 5.1 Hosts, issuer, resource

- Issuer `https://connect.ai.market` (no path) = core's `CONNECTOR_AUTH_ISSUER`. AS endpoints served by the `ai-market-connector` Railway service (same image, design §3) under `/oauth/*`. The canonical resource (RFC 8707, and what MCP clients send as `resource`) is `https://connect.ai.market/mcp`; `https://connect.ai.market/mcp/openai` is accepted as a `resource` value and normalised to the same audience, because core applies profile ceilings by route (core §5.4.2), not by audience. The token `aud` is `https://connect.ai.market/mcp` (`CONNECTOR_AUDIENCE`) for every route, including tokens requested with `resource=https://connect.ai.market/mcp/openai`; core §5.3 checks the same value (adopted Q4a).
- Web steps (login, sign-up, consent) run on `https://ai.market`; their JSON APIs on `https://api.ai.market/api/v1/connector-oauth/*` with website auth.
- Package: `app/mcp/connector/auth/` (`metadata.py`, `authorize.py`, `token.py`, `registration.py`, `cimd.py`, `verifier.py`, `grants.py`, `models.py`) plus `app/api/v1/endpoints/connector_oauth.py` (web-facing API). Nothing imports `app/services/oauth_service.py` or `oauth_client_service.py`.

### 5.2 Endpoints

| Host | Method + path | Purpose |
|---|---|---|
| connect | `GET /.well-known/oauth-authorization-server` | RFC 8414: `issuer`, `authorization_endpoint`, `token_endpoint`, `registration_endpoint`, `revocation_endpoint`, `jwks_uri` (`https://connect.ai.market/oauth/jwks`), `scopes_supported`, `response_types_supported=["code"]`, `grant_types_supported=["authorization_code","refresh_token"]`, `code_challenge_methods_supported=["S256"]`, `token_endpoint_auth_methods_supported=["none","client_secret_basic","client_secret_post"]`, `authorization_response_iss_parameter_supported=true`, `client_id_metadata_document_supported=true`, `service_documentation`. Not served at `/.well-known/openid-configuration` (OIDC is a non-goal). |
| connect | `GET /.well-known/oauth-protected-resource[/mcp[/openai]]` | Served by **core** (core §5.3); listed here because its `authorization_servers` must equal this issuer and its `scopes_supported` must equal §5.4's scope set (A2 is a joint test). |
| connect | `GET /oauth/authorize` | Validate request, create transaction, set binding cookie, 303 to `https://ai.market/oauth/connect?request=<id>`. |
| connect | `GET /oauth/authorize/complete?request=&ticket=` | Browser returns here after consent; binding cookie + single-use ticket checked; code minted; 302 to client `redirect_uri` with `code`, `state`, `iss`. |
| connect | `POST /oauth/token` | `authorization_code` (PKCE, `resource`) and `refresh_token` (rotation, reuse detection). |
| connect | `POST /oauth/register` | RFC 7591 DCR (flag `CONNECTOR_DCR_ENABLED`). |
| connect | `POST /oauth/revoke` | RFC 7009; revokes the refresh family (and so the grant) for a refresh token, or the grant for an access token. Always 200. |
| connect | `GET /oauth/jwks` | RFC 7517 JWKS with the public ES256 keys (current and next `kid`); the only key material the resource side loads. `Cache-Control: max-age=300`. |
| api | `GET /api/v1/connector-oauth/requests/{request}` | Website-authenticated; Origin must equal `FRONTEND_URL`; returns client display block, scopes with plain-English text, org (name or "Personal account"), expiry, CSRF nonce. |
| api | `POST /api/v1/connector-oauth/requests/{request}/decision` | `{csrf_nonce, decision: approve|deny}`; returns `{continue_url}` = `https://connect.ai.market/oauth/authorize/complete?request=…&ticket=…`. |
| api | `GET /api/v1/connector/grants`, `DELETE /api/v1/connector/grants/{id}` | Connected apps list and revoke (website auth, owner only). |

### 5.3 Client registration and trust

**CIMD (preferred).** If `client_id` is an `https://` URL, the AS fetches it (on `/authorize` and on `/token` if the cached copy is stale): HTTPS only, port 443, no userinfo/fragment, hostname resolves only to public addresses (SSRF guard re-checked after connect), no redirects, 5 s timeout, 5 KB cap, `application/json`, document `client_id` must equal the URL byte-for-byte, cache per `Cache-Control` bounded to [5 min, 24 h], last-good copy kept on fetch failure for at most 24 h. The document's `redirect_uris` must each satisfy the redirect policy below; `token_endpoint_auth_method` must be `none` (CIMD clients are public in v1; `private_key_jwt` is Q6).

**DCR (fallback).** `POST /oauth/register` accepts `client_name`, `redirect_uris`, `application_type` (`web` default, or `native`), `token_endpoint_auth_method` (`none`, `client_secret_basic`, `client_secret_post`), `grant_types` ⊆ {`authorization_code`,`refresh_token`}, `response_types=["code"]`, `logo_uri`/`client_uri` (stored, not rendered in v1), `software_id`/`software_version`. Issues `client_id = "dcr_" + 32 random bytes b64url`; a secret (argon2id-hashed, not SHA-256) only for confidential methods. Registration is rate-limited per IP (Q7), `client_name` is stripped to printable text ≤ 80 chars, and registrations with no grant after 30 days are disabled by the cleanup job. PKCE is mandatory even for confidential clients.

**Redirect policy (design §3).** A redirect URI is accepted only if it is in the static allowlist or is loopback:
- `https://claude.ai/api/mcp/auth_callback` (and `https://claude.com/api/mcp/auth_callback`, used by the CRM reference `d2ff9c8b2^:app/mcp/oauth.py:44-45`; Q3);
- `https://chatgpt.com/connector_platform_oauth_redirect`;
- `https://vertexaisearch.cloud.google.com/oauth-redirect`;
- Cursor and Copilot Studio: exact callback URIs UNVERIFIED; the build adds them from each vendor's published docs with a doc citation in the allowlist file, or leaves them out;
- loopback `http://localhost:<port>/<path>` and `http://127.0.0.1:<port>/<path>` (any port, RFC 8252 §7.3), only for `application_type=native` DCR clients or CIMD documents; `[::1]` accepted as loopback.
Matching is exact string match on the registered URI except the loopback port. No wildcard, no custom schemes other than an allowlisted Cursor scheme if verified. The allowlist is code (`app/mcp/connector/auth/redirect_allowlist.py`), changed only by reviewed PR.

**Verified clients and profiles.** Adopts core §5.4.1 exactly: an entry in `app/mcp/connector/profiles.yaml` (reviewed code, not DB) matches only a **verified** identity — a CIMD `client_id` URL on an allowlisted host whose fetched document validated, or a pre-registered `client_id` — **and** the redirect URI used for this grant being one of the entry's URIs. The AS evaluates this at consent and stores `profile` and `client_verified` on the grant. Every DCR client, loopback redirect and unknown CIMD host gets `default` and shows as Unverified, even if its redirect is a vendor callback. `client_name` is never an input to trust or profile. The profile is also carried in the token (`prf` claim) for audit; core reads it from the grant.

### 5.4 Authorization flow

`GET /oauth/authorize` validates, in this order, and **never redirects before client and redirect URI are validated** (unlike `oauth.py:131-143`): `client_id` known or CIMD-resolvable; `redirect_uri` registered and passes policy (else a static 400 page); `response_type=code`; `code_challenge` 43–128 chars and `code_challenge_method=S256` (missing or `plain` → `invalid_request` redirect); `resource` present and one of the canonical resources (else `invalid_target`); `scope` ⊆ `scopes_supported` and ⊆ client's allowed scopes (absent → default `account.read market.read`, Q5); `state` ≤ 512 chars. It then writes a `connector_oauth_transactions` row (hashed request id, hashed binding cookie, all parameters, TTL 30 min — longer than AIM Data's 10 because sign-up with email verification must fit; Q2), sets `connector_oauth_tx` (HttpOnly, Secure, SameSite=Lax, host-only on `connect.ai.market`, path `/oauth`, max-age = TTL) and 303s to `https://ai.market/oauth/connect?request=<id>`.

The frontend page (new; generalises `app/oauth/authorize/page.tsx`) follows the AIM Data continuation discipline: if not signed in it saves the continuation and routes to `/login?redirect=/oauth/connect?request=<id>`; `lib/redirect.ts` gains `CONNECTOR_CONTINUATION = /^\/oauth\/connect\?request=([A-Za-z0-9_-]{43})(?![\s\S])/`; `/register` carries the same `redirect` through verification (the verify-email link and magic-link verify must resume it — §8 "the hard part"); Google/GitHub/SSO callbacks already resume `redirect` for existing flows (UNVERIFIED for SSO; the build adds a test). Once signed in it calls the metadata API, renders consent, and on Approve/Deny posts the decision; the API checks Origin, the website access token and its `auth_sessions` row (`validate_auth_session`), SSO policy with `auth_method="refresh"` on that session, 2FA assurance (`session.auth_method == "2fa"` when `totp_enabled`), email verification, `users.status=active`, and the nonce. On approve it creates or replaces the grant (§5.5), stores a hashed single-use `ticket` (60 s) on the transaction and returns `continue_url`. The browser navigates top-level to `/oauth/authorize/complete`, which requires the binding cookie to match (so the browser that started the flow is the one that finishes it), consumes the ticket, deletes the transaction, mints a 60 s single-use code bound to `(grant_id, client_id, redirect_uri, code_challenge, resource)` and redirects with `code`, `state`, `iss=https://connect.ai.market`. Deny and every post-validation error redirect with `error`, `state`, `iss`.

```mermaid
sequenceDiagram
  autonumber
  participant C as MCP client (Claude)
  participant R as connect.ai.market /mcp
  participant AS as connect.ai.market /oauth
  participant W as ai.market (web app)
  participant API as api.ai.market
  C->>R: POST /mcp (no token)
  R-->>C: 401 WWW-Authenticate: Bearer resource_metadata=".../.well-known/oauth-protected-resource/mcp"
  C->>AS: GET PRM, then GET /.well-known/oauth-authorization-server
  C->>AS: (CIMD) client_id=https URL, or POST /oauth/register (DCR)
  C->>AS: GET /oauth/authorize?client_id&redirect_uri&code_challenge(S256)&resource&scope&state
  AS->>AS: validate client + redirect first, store transaction
  AS-->>W: 303 /oauth/connect?request=R + Set-Cookie connector_oauth_tx (connect host)
  W->>W: not signed in: /login or /register?redirect=/oauth/connect?request=R
  W->>API: GET /connector-oauth/requests/R (Bearer web token, Origin)
  API-->>W: client, verified, scopes, org, csrf_nonce
  W->>API: POST .../R/decision {approve, nonce}
  API->>API: session, SSO, 2FA, status checks; upsert grant; ticket T
  API-->>W: continue_url
  W->>AS: GET /oauth/authorize/complete?request=R&ticket=T (cookie)
  AS-->>C: 302 redirect_uri?code&state&iss
  C->>AS: POST /oauth/token code + code_verifier + resource (+ client auth)
  AS-->>C: access_token (ES256 JWT, 1 h, aud=https://connect.ai.market/mcp) + refresh_token
  C->>R: POST /mcp Authorization: Bearer
  R->>R: verify ES256 sig (JWKS)/iss/aud/exp, live grant + user + org-binding check
```

### 5.5 Grant, token format and refresh

**Grant.** One active grant per `(user_id, client_id, organization_id)`. Approving again revokes the previous grant (reason `superseded`) and its refresh family, then inserts a new one; the token response and audit use the new `grant_id`. `organization_id` is the user's single active membership org at consent, or NULL shown as "Personal account" (registration creates no org: `auth.py:423-530` has no membership insert). A personal grant (`organization_id` NULL) is valid only while the user has no active membership: core's live check (core §5.3) answers 401 reconnect once the user has joined an org, and the membership change also revokes the grant (revocation triggers below). Adopted Q13a.

**Access token.** JWT, `typ: at+jwt` (RFC 9068 profile), **ES256**, signed by the AS with a **dedicated** P-256 key pair (private keys `CONNECTOR_OAUTH_SIGNING_KEYS`, Infisical `ai-market-backend/prod`, loaded only by the AS token module `token.py`; `kid` header; two keys live during rotation; never `SECRET_KEY`). The public keys are published at `GET /oauth/jwks`; the resource side (core's bearer middleware and `verifier.py`) holds only these public keys. Lifetime 3600 s. Claims: `iss`, `aud` (= `https://connect.ai.market/mcp`, the normalised resource), `sub` (user id), `client_id`, `gid` (grant id), `org` (org id or null), `scope`, `prf` (profile), `jti`, `iat`, `nbf`, `exp`, `auth_time`. Adopted Q1: asymmetric ES256 JWT (controller decision; the draft had recommended HS256).

**Verifier and grant store** implement core's protocols (core §5.3): `ConnectorTokenVerifier.verify(token, *, resource) -> VerifiedToken | None` checks `kid` against the JWKS (cache ≤ 5 min, one refetch on an unknown `kid`), the ES256 signature (algorithm allowlist `["ES256"]`; `none` and `HS*` refused), `typ`, `iss`, `aud` against the normalised resource, `exp/nbf` with 60 s skew, and returns `VerifiedToken(user_id, client_id, grant_id, scopes, issuer, audience, expires_at)`; `ConnectorGrantStore.load_active_grant(grant_id) -> Grant | None` does one indexed read and returns `None` if the grant is revoked, its client disabled, or its user not `active`. Core then applies its own rules (scope subset, user/client match, live org binding: active membership in `grant.org_id` when set, no active membership when it is NULL) and emits 401 `invalid_token`. When core observes a membership mismatch it calls `revoke_grant(grant_id, 'membership_changed')` exported by this BQ. Role rules are core's.

**Refresh token.** 256-bit opaque, stored as SHA-256 in `connector_oauth_refresh_tokens(token_hash, grant_id, parent_hash, issued_at, expires_at, consumed_at)`. On use, under `SELECT … FOR UPDATE` on the grant: if the token is already consumed → **reuse**: revoke the grant and all its refresh tokens (`refresh_reuse_detected`), return `invalid_grant`. Otherwise mark consumed, insert the successor, issue a new access token. Client authentication and `client_id` must match; `resource` if sent must equal the grant's; `scope` may only narrow. Idle expiry 30 days, absolute grant lifetime none until revoked (Q8). Concurrent-refresh tolerance (clients that retry with the same token) is Q9; default is strict.

**Revocation triggers.** `connector_grant_service.revoke_all_for_user(user_id, reason)` is called in the same transaction as: `reset_password` (`auth.py:770`), 2FA enable (`totp_service.py:99`) and disable (`:199`), user status leaving `active`, account deletion/teardown, organization membership removal or change; and by the Connected apps revoke, `/oauth/revoke`, and the operator kill command. It sets `revoked_at` on grants; access tokens die on their next call through the live check (≤ 0 s), refresh tokens immediately.

### 5.6 Resource-server contract (with bq-connector-core)

Core owns PRM, the 401 `WWW-Authenticate: Bearer resource_metadata=...` and the 403 `insufficient_scope` step-up (core §5.3). This BQ exports exactly: `ConnectorTokenVerifier`, `ConnectorGrantStore`, `revoke_grant`, the scope catalogue (names + plain-English text, shared with consent and Connected apps), `CONNECTOR_AUTH_ISSUER`, `CONNECTOR_AUDIENCE` (`https://connect.ai.market/mcp`) and the JWKS endpoint. Core's `FakeTokenVerifier`/`FakeGrantStore` must be replaced by these with no change to core's call sites; a contract test runs core's auth suite against the real implementations.

### 5.7 Data model (one additive migration `s_connector_oauth_001`; downgrade retains tables, following `20260907_001_aim_data_oauth.py:188-190`)

- `connector_oauth_clients`: `client_id` text PK; `registration_type` (`cimd|dcr`); `application_type` (`web|native`); `client_name`; `redirect_uris` jsonb; `token_endpoint_auth_method`; `client_secret_hash` (argon2id, NULL for public); `grant_types` jsonb; `software_id`, `software_version`; `metadata_sha256`, `metadata_fetched_at`, `metadata_expires_at` (CIMD); `registration_ip_hash`; `created_at`, `last_used_at`, `disabled_at`, `disabled_reason`. CHECK: `client_secret_hash IS NULL` iff method = `none`.
- `connector_oauth_transactions`: `request_hash` PK, `binding_hash`, `client_id` FK, `redirect_uri`, `scope`, `state`, `code_challenge`, `resource`, `csrf_hash`, `ticket_hash`, `ticket_expires_at`, `approved_grant_id`, `created_at`, `expires_at`. Cleanup job deletes expired rows.
- `connector_oauth_grants`: `id` uuid PK; `user_id` FK; `client_id` FK; `organization_id` FK NULL; `scopes` text[]; `profile`; `resource`; `client_verified` bool (snapshot); `consent_session_id` FK `auth_sessions(session_id)`; `created_at`, `last_used_at`, `revoked_at`, `revoke_reason`. Partial unique index on `(user_id, client_id, coalesce(organization_id, '00000000-…'))` WHERE `revoked_at IS NULL`.
- `connector_oauth_codes`: `code_hash` PK, `grant_id` FK, `client_id`, `redirect_uri`, `code_challenge`, `resource`, `expires_at`, `used_at`.
- `connector_oauth_refresh_tokens`: as §5.5; index on `grant_id`.
No change to `oauth_clients`, its CHECK `aim_data_client_trust`, `oauth_tokens`, `oauth_authorization_codes`, `aim_data_*`, `mcp_auth_codes`, `mcp_refresh_tokens`, `auth_sessions`.

### 5.8 Frontend

- `app/oauth/connect/page.tsx`: consent card — app name and host (e.g. "Claude · claude.ai") with a Verified badge or an amber "Unverified app — only continue if you started this from <host>"; signed-in email; organisation line; scope list in plain English (text from one backend table, same strings on Connected apps); Approve / Deny; expiry handling as the AIM Data page (`page.tsx:105-114`).
- `lib/redirect.ts`: `CONNECTOR_CONTINUATION` accepted by `validateRedirect` beside `AIM_DATA_CONTINUATION` (`lib/redirect.ts:1`, `:19`); login (`app/login/LoginForm.tsx:51,93,118`) and register (`app/register/RegisterForm.tsx:17-27`) already route `redirect` through it.
- `/dashboard/settings#connected-apps`: table of active grants (app, verified, organisation, permissions, connected on, last used) with Revoke (confirm dialog) → `DELETE /api/v1/connector/grants/{id}`; empty state explains how to connect.

## 6. Invariants

- I1 No authorization code, token or redirect carrying `code` is ever issued to a redirect URI that was not registered for that client and does not pass the §5.3 policy; no redirect of any kind happens before the client and redirect URI are validated.
- I2 Every authorization code requires a matching S256 `code_verifier`; `plain` and absent challenges are refused.
- I3 An access token is accepted only by the resource named in its `aud`, only with this issuer and key set; website tokens are never accepted by the connector and connector tokens are never accepted by any `/api/v1` route.
- I4 Every accepted token maps to one non-revoked grant whose user is active and whose org binding still holds, checked on every call.
- I5 A refresh token is usable once; presenting a consumed one revokes the whole grant.
- I6 Password reset, 2FA change, deactivation and membership change revoke all of that user's connector grants in the same transaction as the change.
- I7 A client's profile and verified status come only from `profiles.yaml` matched on verified identity and redirect URI, never from client-supplied metadata.
- I8 The legacy provider's routes, tables, CHECK constraint and AIM Data flow are byte-for-byte unchanged in behaviour.
- I9 The user who approves consent is the user whose web session is validated server-side at decision time, and the browser that completes the flow holds the binding cookie set when the flow started.
- I10 Secrets at rest are hashed (codes, refresh tokens, request ids, tickets, binding cookies: SHA-256 of 256-bit randoms; client secrets: argon2id); none is logged (extend the AIM Data log filter pattern, `aim_data_oauth_service.py:493-503`, to `/oauth/*` on the connector).

## 7. Security analysis

| Threat | Vector | Control |
|---|---|---|
| Code interception | Malicious app on the same machine, leaked redirect, log capture | PKCE S256 mandatory (I2); 60 s single-use codes bound to client, redirect, challenge, resource; loopback only for native/CIMD clients; `iss` in response (mix-up, RFC 9207); no-store/no-referrer headers; path log filter. |
| Open redirect | Crafted `redirect_uri` with unknown client or bad params | Validate client+redirect before any redirect (I1); exact-match allowlist; static error page otherwise; frontend continuation regex accepts only `/oauth/connect?request=<43>`. |
| Token replay | Stolen access token used elsewhere; stolen refresh token | 1 h lifetime; `aud`-bound (I3); live grant check makes revocation immediate (I4); refresh rotation + reuse detection (I5); dedicated ES256 signing key pair, the resource side holds only the public JWKS. Sender-constraining (DPoP) not in v1 (Q10). |
| CSRF on consent / login CSRF | Attacker page auto-submits approve; attacker starts a flow and lures victim to finish it (session swapping) | Decision API needs Bearer web token (not a cookie) + Origin == FRONTEND_URL + per-transaction CSRF nonce; completion requires the binding cookie from the browser that started the flow (I9), so a victim cannot complete an attacker-started transaction and vice versa. |
| Org confusion | Token used against another org's data; user moved orgs | Grant stores org; token carries `org`; core rechecks the live org binding on every call — membership in the grant's org, or no membership for a personal grant (I4); membership change revokes (I6); core's cross-org contract tests. v1 one org per user (`organization.py:55`). |
| Client impersonation via CIMD | Attacker hosts a CIMD claiming "Claude" | Consent shows the client_id **host**, not only the name; "Unverified" unless on allowlist (I7); CIMD `client_id` must equal fetch URL; redirect URIs from the doc must pass policy. |
| Client impersonation via DCR | Registers "ChatGPT" with loopback or own redirect | Same unverified labelling; `client_name` never trusted; vendor callbacks deliver codes only to the vendor; registration rate limit; stale registrations disabled. |
| Profile escalation | Unknown client obtains `claude` profile or scopes beyond default | Profile from `profiles.yaml` only; DCR always `default` (I7); scopes ⊆ client allowed ⊆ profile ceiling (ceiling defined by core; AS rejects over-ceiling requests at authorize with `invalid_scope`). |
| SSRF via CIMD fetch | `client_id` pointing at internal metadata endpoints | HTTPS/443 only, public-IP resolution checked post-connect, no redirects, size/time caps, dedicated egress client; new external egress is why this BQ is Tier 3 even apart from auth. |
| Weak assurance | Password-only session approving for a 2FA or SSO-enforced account | Decision enforces 2FA assurance and SSO policy exactly as AIM Data does (`aim_data_oauth_service.py:282-298`). |
| Credential change not honoured | Password reset after compromise leaves agents connected | I6 hooks; test per trigger. |
| Registration flooding / DB growth | Scripted DCR | Per-IP rate limit, cleanup job, `client_name` length cap. |

## 8. The hard part

The hard part is not the token endpoint — the AIM Data code and the gateway already prove PKCE, rotation and SDK-shaped DCR. It is keeping **one authorization transaction alive and bound to one browser across three hosts** while the person may be signing up from nothing: `connect.ai.market` starts it and owns the binding cookie; `ai.market` must carry it through login, Google/GitHub/SSO round-trips, magic-link, password registration and the **email-verification link that may open in a different tab or on a different device**, and 2FA; `api.ai.market` decides consent with a web session that `connect` cannot see (`auth_cookies.py:16-17`). Any shortcut breaks a guarantee: sharing a parent-domain cookie weakens host isolation; dropping the binding re-opens session swapping; a short TTL makes sign-up fail; skipping email verification lets an unverified address authorise an agent. The design keeps the binding on `connect` (checked only at completion), carries only the opaque request id through the web app via an exact-match continuation regex, and accepts that a verification link opened on another device ends in a clear "return to the app and connect again" page rather than silently completing (Q2). The Gate 2 spec must enumerate every login/sign-up exit and prove each one resumes or fails closed.

## 9. Acceptance criteria → tests

All under `tests/connector_oauth/` (backend, pytest) and `tests/connector-oauth/` (frontend, vitest/playwright) unless noted.

| AC | Requirement | Test |
|---|---|---|
| A1 | AS metadata matches RFC 8414 and advertises S256 only, `iss` support, CIMD support | `test_metadata.py::test_as_metadata_shape` (JSON schema + exact values) |
| A2 | Core's PRM `authorization_servers` equals this issuer and `scopes_supported` equals the scope catalogue; core's auth suite passes against the real verifier/grant store | `test_contract_with_core.py` (joint) |
| A3 | Unknown client or unregistered/unapproved redirect → 400 page, never a redirect | `test_authorize.py::test_no_redirect_before_validation` (parameterised: unknown client, bad response_type first, off-list redirect, wildcard attempt) |
| A4 | Missing/`plain` PKCE refused; wrong verifier → `invalid_grant`; code single-use and 60 s | `test_token.py::test_pkce_*`, `::test_code_single_use`, `::test_code_expiry` |
| A5 | `resource` required and one of the accepted values, else `invalid_target`; `aud` = `https://connect.ai.market/mcp` for both accepted resources; token with any other `aud` (incl. `https://connect.ai.market`), `iss` or `kid`, or any `alg` other than ES256, rejected; `/oauth/jwks` serves public keys only | `test_verifier.py::test_audience_binding` |
| A6 | Web access tokens rejected by the verifier; connector tokens rejected by `get_current_user` and by legacy `verify_access_token` | `test_verifier.py::test_cross_token_isolation` |
| A7 | Refresh rotates; replay of consumed token → `invalid_grant` and grant + all tokens revoked | `test_token.py::test_refresh_rotation`, `::test_refresh_reuse_revokes_family`, concurrency test with two parallel refreshes |
| A8 | Password reset, 2FA enable, 2FA disable, deactivation, membership change each revoke grants; next `/mcp` call 401 | `test_revocation_triggers.py` (one case per trigger) |
| A9 | Consent CSRF: missing/wrong nonce, wrong Origin, no Bearer → 403; completion without binding cookie or with another browser's cookie → 403; ticket single-use | `test_consent.py::test_csrf_*`, `::test_binding_required`, `::test_ticket_single_use` |
| A10 | 2FA-enabled user with password-only session → `insufficient_assurance`; SSO-enforced org with non-SSO session → denied | `test_consent.py::test_assurance`, `::test_sso_enforced` |
| A11 | CIMD: fetch rules (https, size, timeout, no redirect, private IP refused, `client_id` mismatch refused), cache bounds | `test_cimd.py` with a local test server + resolver stub |
| A12 | DCR: `application_type` rules (loopback only for native), secret only for confidential methods, name sanitised, rate limit | `test_registration.py` |
| A13 | Profile/verified only from `profiles.yaml` (verified identity + redirect); DCR named "Claude", even with the claude.ai callback, gets `default`/unverified | `test_trust.py::test_profile_from_allowlist_only` |
| A14 | Grant persisted with user/client/org/scopes/profile/resource; re-consent supersedes; token `gid` refers to it | `test_grants.py` |
| A15 | Connected apps lists only own grants; revoke works and next call 401; other user's grant id → 404 | `test_grants_api.py`; frontend `connected-apps.test.tsx` |
| A16 | Login and sign-up resume consent: password, magic-link, Google, GitHub, SSO, 2FA, register→verify-email same tab; other-device verify ends in the restart page | playwright `connector-oauth-continuation.spec.ts` (test env, `FRONTEND_URL=http://localhost:13000`) |
| A17 | Legacy unchanged: AIM Data full flow, client-credentials token, `/oauth/authorize` legacy responses identical with the connector flag on and off | existing `tests/test_aim_data_oauth_routes.py`, `test_aim_data_oauth_flag_off_equivalence.py` + new `test_legacy_unchanged.py` (golden responses) |
| A18 | Migration additive; `aim_data_client_trust` CHECK and `oauth_*` schemas unchanged; downgrade retains | `test_connector_oauth_migration.py` (schema diff before/after) |
| A19 | Flag off → all connector AS routes 404 and metadata absent; web APIs 404 | `test_flag_off.py` |
| A20 | Secrets not logged; responses `Cache-Control: no-store` | `test_logging.py` (caplog over full flow) |
| A21 | E2E (joint with core): MCP Inspector completes auth; Claude custom connector and ChatGPT developer-mode connector connect and call `get_my_account` | Gate 4 evidence, recorded per `runbooks/connector-oauth.md` |

## 10. Rollout, feature flag, rollback

Flags (all default false; `app/core/config.py`): `CONNECTOR_OAUTH_ENABLED` (master), `CONNECTOR_DCR_ENABLED`, `CONNECTOR_CIMD_ENABLED`. Steps:
1. Merge with flags off; run migration (additive). Verify A18/A19 in production: metadata 404, legacy golden tests pass.
2. Test environment (`money-path-test-environment` pattern): flags on, run A1–A21 incl. Inspector + Claude + ChatGPT dev mode against the test host.
3. Production: master + CIMD on, DCR on; verify with Max's own account from Claude; then open to all.
4. Frontend Connected apps ships in the same release as step 3 (hidden while master flag off, driven by a `/api/v1/connector-oauth/status` call).
Rollback: set `CONNECTOR_OAUTH_ENABLED=false` (routes 404, verifier refuses everything → connector 401); optional `python -m app.mcp.connector.auth.ops revoke-all --reason rollback` (writes revoke on all grants, audit row per grant). Tables are retained (no destructive downgrade). Legacy provider and AIM Data are unaffected by any step because they share no table or route (I8). Key compromise: generate a new ES256 key pair, publish it in the JWKS and remove the old `kid` — every access token signed with the old key fails at once; refresh continues.

Runbook obligations (project instructions): the build PR adds `runbooks/connector-oauth.md` (operate: enable/disable, key rotation, revoke-all, allowlist change, inventory SQL for L1–L4 with the read-only query and how to classify rows; fail: `invalid_grant` on refresh reuse, CIMD fetch failure, `insufficient_assurance`) and `ERRORS.md` entries, then runs `python3 scripts/index.py && python3 scripts/check.py`.

## 11. Dependencies on bq-connector-core

- Core provides: the `ai-market-connector` service and routing for `connect.ai.market` (design D9), the MCP SDK upgrade, mounting of `/mcp*`, profile → tool ceilings and the scope ceiling per profile (this BQ reads it to reject over-ceiling scope requests), Redis rate limiter (used for DCR/authorize limits), audit table `connector_audit_events` (this BQ writes `grant_created/superseded/revoked`, `refresh_reuse_detected`, `registration_created` events through core's audit writer), kill switches.
- This BQ provides to core: implementations of core's `TokenVerifier` and `GrantStore` protocols, `revoke_grant`, the scope catalogue, `CONNECTOR_AUTH_ISSUER`, `CONNECTOR_AUDIENCE`, the JWKS endpoint. Core provides PRM and the 401/403 headers.
- **Org binding (adopted Q13a):** core's `Grant.org_id` is `UUID | None`. A grant with an org requires a live active membership in that org; a personal grant (`organization_id` NULL — most self-registered users, since `auth.py:423-530` creates no org) requires the user to have no active membership, else 401 reconnect (core §5.3).
- Ordering: the AS and verifier land first (standalone tests A1–A20 with a test-only protected echo route that exists only when `ENVIRONMENT=test`); A21 runs when core's `/mcp` is deployed.
- Also touches `auth.py` and `totp_service.py` (revocation hooks) — owned code, coordinate with any in-flight auth BQ.

## Cross-spec contract

The three P0 connector specs (`BQ-CONNECTOR-OAUTH-GATE1.md`, `BQ-CONNECTOR-CORE-GATE1.md`, `BQ-CONNECTOR-ACTION-PATH-GATE1.md`) share these interfaces; changing one changes all three and needs all three Gate 2s to agree.
- `TokenVerifier` / `GrantStore` (+ `revoke_grant`): protocols defined in core §5.3, implemented by bq-connector-oauth (its §5.5–5.6), consumed by core's bearer middleware. `Grant.org_id` is `UUID | None` (None = personal grant).
- Constants: issuer `CONNECTOR_AUTH_ISSUER = https://connect.ai.market`; audience `CONNECTOR_AUDIENCE = https://connect.ai.market/mcp` for every route (`/mcp/openai` is accepted as `resource` and normalised; the route alias is only a profile ceiling); access tokens are ES256 JWTs verified against the AS's public JWKS (`https://connect.ai.market/oauth/jwks`).
- `app/mcp/connector/profiles.yaml`: owned by core (its §5.4); the AS reads it at consent to set `grant.profile` and `client_verified`.
- `connector_audit_events`: owned by core (its §5.9, created by core's migration); action-path fills `policy_decision`, `pending_action_id`, `binding_terms` through `AuditSink.record_required`; the AS writes grant events through the same sink; `agent_audit_log` is not extended.
- `pending_actions` + `connector_action_requests`: owned by action-path (its §4.4); core's `get_activity` reads them, owner-filtered.

## Adopted defaults (controller, 2026-09-23; Max may override)

Q-numbers used in the body of this spec refer to the entries below (adopted) or to the open questions that follow.

- **Q1 Access-token format** → asymmetric JWT, **ES256**, signed by the AS with a dedicated key pair; public keys published as JWKS; the resource side holds only the public key; live grant check on every call retained. Refresh tokens stay opaque, rotating, strict reuse → revoke grant. (Controller decision; replaces the draft's HS256 recommendation; matches core Q3a.)
- **Q3 `claude.com` callback** → (a) allow both `claude.ai` and `claude.com` callbacks.
- **Q4 Audience value** → (a) `aud = https://connect.ai.market/mcp` for all routes; `/mcp/openai` accepted as `resource` and normalised; the route alias is a profile ceiling only. Core §5.3 uses the same value.
- **Q5 Default scopes** → (a) `account.read market.read` when a client requests none.
- **Q6 CIMD client authentication** → (a) public clients only in v1.
- **Q7 DCR rate limit** → (a) 10 registrations/IP/hour, 1000/day global.
- **Q8 Grant lifetime** → (a) no absolute expiry, 30-day idle refresh expiry.
- **Q9 Concurrent refresh** → (a) strict: any second use is reuse → revoke the grant.
- **Q10 DPoP** → (a) not in v1.
- **Q11 Consent scope editing** → (a) all-or-nothing approve in v1.
- **Q12 Legacy L2/L3/L4 rows** → (a) untouched, inventory only.
- **Q13 Users with no organisation** → (a) personal grant with `org_id = NULL` (rule below).
- **Users without an organisation (shared).** A personal grant with `org_id = NULL` is allowed. Live check: if `grant.org_id` is set, an active membership in that org is required; if NULL, the user must have no active membership (else 401, reconnect). Reads filter by `user_id` and, when set, `org_id`; org-keyed rate limits fall back to the user id when `org_id` is NULL.
- **Audit retention (shared by all three connector specs; core Q5a).** Keep every `connector_audit_events` row until legal sign-off, then apply the retention matrix; no purge path ships before sign-off.

## 11a. For the Council: where the authorization server runs

The controller's adopted default is that the connector's resource server holds only the ES256 public key. In this spec the authorization-server routes (`/authorize`, `/token`, `/register`, `/oauth/jwks`, metadata) are served from the same Railway service as the MCP endpoint (`ai-market-connector`, host `connect.ai.market`), so that service's environment necessarily holds the private signing key; separation is by module only (`token.py` signs, `verifier.py` verifies). Reviewers are asked to rule between (a) accept co-location with module separation and a key available only to the AS process role, or (b) run the AS as a second process/service (e.g. on api.ai.market or a separate Railway service behind a path route) so the MCP process never holds the private key. Related legacy defects found while writing this spec are filed as T-2026-000850 (open redirect in legacy /oauth/authorize) and T-2026-000851 (password reset does not revoke sessions).

## 12. Open questions for Max

- **Q2 Transaction lifetime / cross-device email verification.** (a) 30-minute transaction; an email verification opened on another device asks the user to go back to the app and reconnect **(recommended)**; (b) 60-minute transaction; (c) no email verification before connector consent.

## 13. Surprising findings (for the Council)

1. The legacy authorization-code provider is non-functional end to end: `/token` only does client-credentials for non-AIM-Data clients, the service's exchange/refresh/revoke methods are dead code, and consent needs a Bearer header a browser cannot send (§1). The `oauth_agent` token verifiers in `wallet.py:64` and `agent/router.py:553,584` accept tokens nothing can mint.
2. Legacy `/oauth/authorize` is an open redirect for unknown clients (`oauth.py:131-143`).
3. Client-credentials tokens (`aud="agent"`) appear to have no consumer (§4.6 L2) — UNVERIFIED beyond grep.
4. `reset_password` revokes no website sessions (`auth.py:740-777`); this BQ revokes connector grants there, and a separate ticket should cover web sessions.
5. The deleted CRM connector's tables `mcp_auth_codes`/`mcp_refresh_tokens` and possibly `mcp_*` client rows remain.
