# Customer MCP connector core: one server at connect.ai.market, profiles, limits, audit, kill switches

Status: GATE 1 DRAFT, round 1 Council findings folded (GLM, DeepSeek and Gemini reviews of 2026-09-23; controller rulings cited inline as R1–R8); awaiting round 2. Build Queue entity `build:bq-connector-core` (P0). Tier: CORE S3 **Tier 3** (auth, customer data, rate caps, new external surface): GLM, DeepSeek and Gemini unanimous, MP builds (`runbooks/council-gate-process.md`, "Rational-use tiering"). Not a build authorisation until Gate 1 passes.

Design authority: `specs/BQ-CUSTOMER-MCP-CONNECTOR-DESIGN.md` v3 (approved by Max for build 2026-09-23), in particular D2, D9, §3 (architecture, client profiles), §4 (tool rules), §6 (audit, limits, kill switches) and §8 (the P0 row for this BQ). Where this spec and the design disagree, the design wins and this spec is wrong.

Source identity read for this brief: backend `aidotmarket/ai-market-backend` `origin/main` **`75c8be503`** (read via `git show origin/main:<path>`; the local Titan-1 checkout is detached at an older commit and was not modified). Every `file:line` below is at `75c8be503` unless stated. MCP SDK facts come from wheels downloaded to `/tmp/mcpsdk` on Titan-1 (not installed anywhere) and from PyPI JSON on 2026-09-23. Runbooks base `fc792e5`. Claims not proven by a read are marked **UNVERIFIED**.

Runbooks followed: `runbooks/council-gate-process.md` (gate shape, tiering), `aimarket-mcp-server.md` (PyPI surface), `cloudflare-and-dns.md` plus the unmerged branch `origin/docs/connect-ai-market-dns` commit `e8c982d` (PR #266, the `connect.ai.market` record and Railway subdomain procedure), `celery-infrastructure-deployment.md` (same-image, per-service `startCommand` topology, project and environment ids).

## 0. Problem

ai.market has six partial MCP surfaces, three auth schemes and none a directory can list (design §2). Max decided (D2, D9) there will be one remote server at `https://connect.ai.market/mcp`, OAuth 2.1 only, on its own Railway service. Nothing of that server exists: the Railway service `ai-market-connector` is empty, the backend pins an MCP SDK that speaks at most protocol `2024-11-05`, rate limiting is split between an in-memory per-process limiter and Redis limiters that fail open, there is no per-client capability control, no connector audit record, no kill switch.

This BQ builds the chassis every connector tool will run on: the server process, the transport, token checking against the new issuer (interface only), the client profiles, scope-filtered tool discovery, the tool lint, the error contract, Redis limits, the audit hook, tracing, kill switches, health, Railway config, and one tool (`get_my_account`) that proves the chain end to end. Buyer and seller tools, the OAuth issuer and the action path are other BQs.

## 1. Plain-English summary for the business

We are building the socket that Claude, ChatGPT, Cursor and the like will plug into. After this BQ a customer can add `connect.ai.market` to Claude, sign in, and ask "what is my ai.market account?" and get a correct answer; nothing else yet. What matters to the business is what this socket refuses to do: it never shows one company's data to another, it gives an unknown app the smallest possible toolset, it gives ChatGPT only what OpenAI will approve, it slows down abusive callers without locking out paying customers, it records who did what, and any tool, any client type, or the whole connector can be switched off in seconds without a deploy. It runs as its own service, so a connector problem cannot take down the website or the API; the sign-in service that issues the keys runs as a separate service again, so a break-in at the socket cannot mint keys.

## 2. Scope

1. Packages `app/mcp/connector/` (the MCP resource server, own ASGI entrypoint, not `app.main`) and `app/mcp/connector_shared/` (key-free code both services need) in ai-market-backend, with the CI-enforced import rules of §5.1 and the Cross-spec contract.
2. Railway service `ai-market-connector` (`a08ef347-d2d1-4fcb-ba50-9299a9484fd5`), same Dockerfile image, own `railway.connector.json` start command, port 8080, custom domain `connect.ai.market` (already attached, `519d4d32-649c-4adc-afe1-b9dca9100168`). Plus the Railway configuration (not the code) of the separate authorization-server service `ai-market-connector-auth`: same image, `railway.connector-auth.json` (entrypoint `app.mcp.connector_auth.asgi:app`), custom domain `auth.ai.market`, flags off (R1, R5; the AS code is bq-connector-oauth's).
3. Streamable HTTP only, stateless, JSON responses; protocol floor 2025-11-25.
4. MCP SDK upgrade from `mcp>=1.8.0,<1.9` with the blast-radius work it forces on the existing mounts.
5. Bearer validation against `bq-connector-oauth` tokens, as an interface plus a test double; RFC 9728 protected-resource metadata and 401/403 `WWW-Authenticate` on the resource side. The connector service holds only the AS's public keys; CI, startup and deploy checks keep the signing key and signing module out of it (R1).
6. Client capability profiles `claude`, `openai`, `default` bound to a server-side allowlist of verified client registrations; one MCP URL, the profile comes only from the verified grant (R2).
7. `tools/list` and `tools/call` filtered by profile, granted scopes (all of a tool's required scopes, R3) and kill switches.
8. A tool registry and a CI lint for names, titles, descriptions, annotations, schemas and per-profile counts.
9. The error contract.
10. Redis rate limits at the design §6 numbers, replacing the in-memory pattern for the connector.
11. Audit hook and the connector audit table, typed by `event_type` and shared with the AS and action-path (R4).
12. OpenTelemetry tracing.
13. Kill switches: global, per profile, per tool.
14. Tool `get_my_account`.
15. `/healthz`, `/readyz`.
16. The retirement plan for the other surfaces (§5.15); retirement itself is `bq-mcp-surface-retirement`.
17. The inert "connector foundation" stage that the AS, this server and action-path build on (§9 step 1, R5).

## 3. Non-goals

- The authorization server code (its Railway service configuration is in scope, item 2), consent, login, grants storage, Connected apps page, legacy client migration (`bq-connector-oauth`).
- Any write tool, ActionRegistry wiring, PolicyEngine decisions, `pending_action`, checkout refactor (`bq-connector-action-path`); this BQ only reserves the audit fields and error codes they fill.
- Buyer, seller, negotiation tools and MCP Apps UI (P1–P3 BQs).
- Retiring PyPI, MCPB, `marketplace_remote`, legacy SSE or WebMCP (`bq-mcp-surface-retirement`).
- Directory submissions, docs site, privacy policy.
- Migrating the backend's other limiters (`agent_auth.py`, `marketplace_auth.py`) to the new limiter. The new limiter is written so they can adopt it later.
- MCP SDK 2.x migration of `aim_discovery`, `marketplace_remote` and `aim_node` (see §5.14 and Q1).
- Multi-org users (design §9: after P2).

## 4. Current state (evidence)

### 4.1 Dependencies and SDK

| Fact | Evidence |
|---|---|
| MCP SDK pinned below 1.9 | `requirements.txt:110-111` `mcp>=1.8.0,<1.9` ("CRM MCP for Claude.ai connector", the CRM server deleted in S1098) |
| `fastmcp` declared, never imported | `requirements.txt:33` `fastmcp>=0.3`; `git grep -E "^(import fastmcp\|from fastmcp)"` returns nothing. It resolves to `fastmcp 1.0` in `.venv` (depends `mcp<2,>=1.0`) |
| Framework pins | `requirements.txt:2-3` `fastapi==0.110.1`, `uvicorn[standard]==0.27.0`; `redis==5.0.1` `:16`; OTel 1.39 / 0.60b1 `:131-137` |
| `aim-node` package declares `mcp>=1.0` with no upper bound | `pyproject.toml:15`; published by `.github/workflows/aim-node-publish.yml:42` (`hatch publish`). Its seller server imports `from mcp.server.fastmcp import FastMCP` (`aim_node/seller/server.py:18`) and `mcp.server.fastmcp.tools.Tool` (`aim_node/seller/tool_wrapper.py:13`) |
| Local envs disagree | `.venv` has `mcp 1.29.0, uvicorn 0.51.0`; `.venv-ci` has `mcp 1.8.1, uvicorn 0.27.0` (pip list, 2026-09-23) |
| Dependency drift gate | `.github/workflows/dependency-drift.yml` runs `scripts/check_dependency_drift.py`: every `pyproject` dependency must appear in `requirements.txt` |

SDK versions on PyPI (2026-09-23): latest `mcp 2.2.0`; latest 1.x `1.30.0` (uploaded 2026-09-07). From the wheels' `types.py` / `mcp_types/version.py`:

| mcp | `LATEST_PROTOCOL_VERSION` | uvicorn floor | Notes |
|---|---|---|---|
| 1.8.1 (current) | 2024-11-05 | >=0.23.1 | |
| 1.9.0 – 1.23.0 | 2025-03-26 → 2025-06-18 | 0.23.1, then >=0.31.1 from 1.14 at the latest | |
| **1.24.0** | **2025-11-25** (first) | >=0.31.1 | |
| 1.30.0 | 2025-11-25 | >=0.31.1 | FastMCP retained; `FastMCP.__init__` turns on DNS-rebinding protection allowing only `127.0.0.1/localhost/[::1]` when `host` is left at its default `127.0.0.1` and no `transport_security` is passed (`mcp/server/fastmcp/server.py:171,191-195`); failure is `421 Invalid Host header` (`mcp/server/transport_security.py`, `validate_request`) |
| 2.0.0 (2026-07-28) – 2.2.0 | handshake 2025-11-25 + modern 2026-07-28 | >=0.31.1 | `mcp.server.fastmcp` is a stub that raises `ModuleNotFoundError` ("FastMCP was renamed to MCPServer"); new deps `httpx2>=2.5.0`, `mcp-types`, `opentelemetry-api>=1.28` |

### 4.2 Existing MCP surfaces in the backend

- `app/mcp/aim_discovery.py:7,15-24` — FastMCP, `stateless_http=True`, default host. **Mounted unconditionally** at `/mcp/aim-discovery/` (`app/main.py:1013-1024`); mount errors are logged and swallowed (`:1021-1024`), and its session manager is started in the lifespan (`:618-629`). Unauthenticated.
- `app/mcp/marketplace_remote.py:28,34-45` — FastMCP, 7 tools, `aim_` API keys via `app/mcp/marketplace_auth.py`; mounted only when `MARKETPLACE_MCP_ENABLED` (`app/core/config.py:415-416`, default `False`; `app/main.py:996-1011`). Production value **UNVERIFIED** (design §2 calls it flagged off).
- Legacy SSE / JSON-RPC: `app/api/v1/endpoints/mcp_server.py:293` (`GET /api/v1/mcp/sse`), `app/api/v1/endpoints/mcp.py:151,382`, public `app/routers/mcp_sse.py:375,397` mounted under `/api/v1/agent` (`app/api/v1/router.py:260-262`); WebMCP manifest `app/main.py:899-904`; MCP API keys `app/api/v1/router.py:451-454`.
- `scripts/allai_bridge.py:48-50` (low-level stdio server) and `tests/test_aim_tool_wrapper.py:4` also import the SDK.
- `app/main.py` is not a safe entrypoint for a second service: its lifespan (`:335-`) starts APScheduler when `SCHEDULER_MODE=apscheduler` (`:111,500-513`), the sysadmin health scheduler (`:635`), the Qdrant sync worker (`:600`) and the MCP session managers. The Dockerfile `CMD` runs Alembic before uvicorn (`Dockerfile:103`).

### 4.3 Auth, identity, limits, audit, telemetry

- Legacy OAuth access tokens are HS256 JWTs signed with the shared `SECRET_KEY`, `aud="oauth_agent"`, claims `sub, client_id, scope, exp, iat, type` (`app/services/oauth_service.py:39,340-358,365-377`). No grant id, no org, no issuer.
- `Settings` refuses to load without a `SECRET_KEY` of ≥32 chars (`app/core/config.py:115,747-765`), so any process importing `app.core.config` must hold one.
- One organisation per user: `organization_memberships.user_id` is `unique=True` (`app/models/organization.py:50-56`).
- In-memory per-process limiter: `app/middleware/agent_auth.py:31-33,61-78` (`defaultdict(deque)` + `Lock`); invisible across replicas and workers.
- Redis limiters exist and **fail open**: `app/services/mcp_middleware_service.py:34-72` (`mcp_rl:<key_hash>`, "Fail open — don't block requests if Redis is down" `:71`); `app/middleware/rate_limiter.py:80-160` allows everything when there is no Redis client (`:92-98`) and **auto-suspends** for 900 s after 10 violations in 300 s (`:19-22`). The design (§6) forbids automatic suspension. Both add the request to the window before deciding, so rejected calls consume budget.
- Caller IP: `app/core/request_ip.py:16-24,138-165` trusts `X-Forwarded-For` only when the socket peer is an internal hop, takes the leftmost entry, never reads `X-Envoy-External-Address`; evidence recorded 2026-07-13 for the backend service. `marketplace_auth.py:61` uses it.
- Kill-switch precedent: `app/allai/evolution/kill_switches.py` (Redis keys, all switches read as off when Redis is absent).
- `agent_audit_log` model is keyed by `api_key_id` with `tool_name`, `client_ip`, request/response JSONB (`app/models/agent_audit_log.py:16-31`); it has no user, org or OAuth client column. The baseline DDL in `alembic/versions/000_initial.py:5617-5626` shows different column names (`action`, `ip`, `payload`); which one production has is **UNVERIFIED** and is not load-bearing here because §5.9 uses a new table.
- Telemetry: `app/core/observability.py:18-99` `init_telemetry(app, engine)`, no-op without `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME` defaults to `ai-market-backend`, instruments FastAPI, httpx, Redis, SQLAlchemy.
- DB pool is hard-coded `pool_size=20, max_overflow=10` per process (`app/core/database.py:37-50`).

### 4.4 Railway and DNS

- Same-image topology: services differ by `deploy.startCommand` in `railway.<role>.json` (`railway.worker.json`; `celery-infrastructure-deployment.md` §Runtime Topology). Project `e81dd66f-808c-412e-b32c-f6d910f0ac5d`, environment `production` `23e322c3-b195-45d8-9151-c4c27a998c33`.
- `connect.ai.market` → DNS-only CNAME `04tecdf8.up.railway.app` plus `_railway-verify` TXT, target port 8080, service empty (design D9; runbooks `e8c982d`, PR #266 **not yet merged** to runbooks `main`). DNS-only means Cloudflare is not in the path: `CF-Connecting-IP` is never trustworthy here.
- `auth.ai.market` (R1): no DNS record, custom domain or Railway service `ai-market-connector-auth` is known to exist (**UNVERIFIED**; not checked on 2026-09-23). The foundation stage (§9 step 1) creates them with the same DNS-only procedure as `connect.ai.market` (runbooks PR #266).

## 5. Design

### 5.1 Module layout

```
app/mcp/connector_shared/   # key-free; imported by connector, connector_auth and the main backend
  __init__.py
  tokens.py          # VerifiedToken, TokenVerifier protocol + ES256/JWKS implementation (bq-connector-oauth fills it)
  grants.py          # Grant, GrantStore / load_active_grant, revoke_grant, revoke_all_for_user (bq-connector-oauth fills them)
  profiles.py        # Profile enum, profiles.yaml loader
  profiles.yaml      # verified client registrations → profile (reviewed like code)
  scopes.py          # scope catalogue (names, descriptions), also read by the AS consent screen
  audit.py           # AuditSink protocol (record, record_required), DbAuditSink, redaction/hashing
app/mcp/connector/          # the MCP resource server (this BQ)
  __init__.py
  asgi.py            # Starlette app: routes, middleware order, lifespan (engine, Redis, OTel); no import of app.main
  settings.py        # ConnectorSettings (CONNECTOR_* env), read once at startup
  transport.py       # SDK low-level Server + StreamableHTTPSessionManager(stateless=True, json_response=True)
  auth.py            # BearerMiddleware, VerifiedPrincipal, PRM routes (uses connector_shared.tokens / grants)
  profile_resolution.py  # resolve_profile() (stored grant profile only, R2)
  registry.py        # ToolSpec, @connector_tool, visible_tools(principal): scopes_required ⊆ principal.scopes (R3)
  errors.py          # ConnectorError codes → JSON-RPC / tool-result / HTTP mapping
  ratelimit.py       # Redis sliding-window (Lua), key builders, local fallback
  switches.py        # kill switches (Postgres source, 5 s cache, env floor)
  telemetry.py       # span helpers, attribute allowlist
  health.py          # /healthz, /readyz
  tools/account.py   # get_my_account
railway.connector.json
railway.connector-auth.json   # AS service config (R1); the AS code under app/mcp/connector_auth/ is bq-connector-oauth's
alembic/versions/<date>_connector_foundation.py   # connector_switches, connector_audit_events (event_type), connector_review_queue; foundation stage (§9)
tests/connector/...  # see §8
```

The SDK's high-level FastMCP class is not used for the connector: its `list_tools` is global (`fastmcp/server.py:320,331`), while ours must depend on the caller. The low-level `Server` gives per-request `list_tools`/`call_tool` handlers, and keeping our auth, profile and error code outside SDK classes limits the next SDK major migration to `transport.py`.

Import boundary (R1; package ruling in the Cross-spec contract): three packages. `app.mcp.connector_shared` holds everything both services need and is key-free (`VerifiedToken`, `TokenVerifier`, `Grant`/`GrantStore`/`load_active_grant`, `revoke_grant`/`revoke_all_for_user`, the profiles loader and `profiles.yaml`, the scope catalogue, `AuditSink`). `app.mcp.connector_auth` is the AS and the only package that imports the signing module. `app.mcp.connector` (this server) and the main backend may import `app.mcp.connector_shared` but never `app.mcp.connector_auth`; `app.mcp.connector_auth` may import `app.mcp.connector_shared` and not `app.mcp.connector`. CI enforces all of this (§5.13, A23).

### 5.2 Request lifecycle

Middleware order, outermost first: body-size limit (256 KB) → Host/Origin check → request id + trace span → pre-auth IP limiter → global kill switch → bearer auth → profile resolution → MCP transport → per-method handler (scope filter, tool switch, rate limit, audit).

```mermaid
sequenceDiagram
    autonumber
    participant C as MCP client (Claude / ChatGPT / Cursor)
    participant E as Railway edge
    participant M as Connector ASGI middleware
    participant V as TokenVerifier + GrantStore (bq-connector-oauth interface)
    participant R as Redis
    participant S as Switches (Postgres, 5 s cache)
    participant H as Tool handler
    participant A as Audit sink (Postgres)
    C->>E: POST /mcp  Authorization: Bearer <t>  (JSON-RPC)
    E->>M: XFF = caller, Railway edge; peer = internal hop
    M->>M: size ≤ 256 KB, Host ∈ allowlist, Origin absent or allowed
    M->>R: pre-auth limiter conn:rl:v1:ip:<ip>
    M->>S: global switch / CONNECTOR_ENABLED
    alt no or invalid token
        M-->>C: 401 WWW-Authenticate: Bearer resource_metadata="https://connect.ai.market/.well-known/oauth-protected-resource/mcp"
    end
    M->>V: verify(t, resource) → sub, client_id, grant_id, jti, scopes
    V-->>M: VerifiedToken | None
    M->>V: load_active_grant(grant_id) + live org binding (membership in grant.org_id, or none if NULL)
    M->>M: profile = grant.profile (set by the AS from verified client identity)
    M->>S: profile switch
    M->>H: JSON-RPC via SDK stateless transport
    alt tools/list
        H->>S: tool switches
        H-->>C: profile tools with scopes_required ⊆ token scopes, not killed
    else tools/call name, args
        H->>H: visible? scope? schema-valid?
        H->>R: rate-limit keys for the tool's class
        H->>H: execute (DB session, org-filtered)
        H->>A: one tool.call audit row (hashed args/result, outcome)
        H-->>C: result or isError + structured error
    end
```

### 5.3 Authentication interface (defined here in `app.mcp.connector_shared`, implemented by bq-connector-oauth, consumed here)

```python
@dataclass(frozen=True)
class VerifiedToken:
    user_id: UUID; client_id: str; grant_id: UUID; token_jti: str  # JWT jti (R7)
    scopes: frozenset[str]; issuer: str; audience: str; expires_at: datetime

class TokenVerifier(Protocol):
    async def verify(self, token: str, *, resource: str) -> VerifiedToken | None: ...

@dataclass(frozen=True)
class Grant:
    grant_id: UUID; user_id: UUID; org_id: UUID | None; client_id: str  # None = personal grant
    scopes: frozenset[str]; profile: Profile; revoked_at: datetime | None

class GrantStore(Protocol):
    async def load_active_grant(self, grant_id: UUID) -> Grant | None: ...
```

Rules the connector enforces regardless of the implementation:
- Reject any token whose `iss` is not `CONNECTOR_AUTH_ISSUER` (`https://auth.ai.market`, R1) or whose `aud` is not `CONNECTOR_AUDIENCE` = `https://connect.ai.market/mcp`, the one canonical resource (R2: no second MCP URL, no audience normalisation). Only ES256 signatures from the AS's JWKS (`https://auth.ai.market/.well-known/jwks.json`) are accepted, so legacy `aud="oauth_agent"` tokens (`oauth_service.py:39`, HS256 under `SECRET_KEY`) and `mcp.ai.market` gateway tokens are rejected on algorithm, issuer and audience.
- `token.scopes ⊆ grant.scopes`, `token.user_id == grant.user_id`, `token.client_id == grant.client_id`, grant not revoked; else 401 `invalid_token`.
- Live org-binding check on every request: if `grant.org_id` is set, the user's `organization_memberships` row exists, is `active`, and its `organization_id == grant.org_id`; if `grant.org_id` is NULL (personal grant), the user must have no active membership. Otherwise 401 `invalid_token` with an error description telling the user to reconnect. No grant cache in v1 (one indexed read per request; measured at Gate 3; a ≤10 s cache is the fallback if p95 suffers).
- The connector service (`ai-market-connector`) never mints, refreshes or introspects tokens. It verifies ES256 JWTs locally against the AS's public JWKS (`CONNECTOR_JWKS_URL` = `https://auth.ai.market/.well-known/jwks.json`, cached ≤ 5 min, one refetch on an unknown `kid`). The private signing keys (`CONNECTOR_OAUTH_SIGNING_KEYS`) exist only in the separate `ai-market-connector-auth` service (R1, adopted Q3a): the connector service's environment never contains them and its entrypoint never imports the AS signing module (A23; `ConnectorSettings` refuses to start if `CONNECTOR_OAUTH_SIGNING_KEYS` is set).
- Until the oauth BQ lands, `tests/connector/fakes.py` provides `FakeTokenVerifier`/`FakeGrantStore`; production refuses to start if `CONNECTOR_AUTH_ISSUER` is unset (fail closed).

Resource-server metadata served here: `GET /.well-known/oauth-protected-resource` and `/.well-known/oauth-protected-resource/mcp`, both describing the single resource (RFC 9728: `resource: "https://connect.ai.market/mcp"`, `authorization_servers: ["https://auth.ai.market"]`, `scopes_supported`, `bearer_methods_supported: ["header"]`). AS metadata is served by the AS service, not here. 401 carries `WWW-Authenticate: Bearer resource_metadata="…"`; a known tool the profile allows but the token lacks scope for returns HTTP 403 `WWW-Authenticate: Bearer error="insufficient_scope", scope="<the tool's scopes_required, space-separated>"` (step-up, MCP 2025-11-25 authorization). Tokens in query strings are rejected.

### 5.4 Profile resolution

Profiles: `claude`, `openai`, `default`. They are separate tool sets, not a ranking; each principal has exactly one, taken from its grant.

1. `grant.profile` is decided by the oauth BQ at grant creation from the server-side allowlist `app/mcp/connector_shared/profiles.yaml`, never from anything the client says at request time. An entry matches on **verified** client identity only: a CIMD `client_id` URL on an allowlisted host whose fetched metadata was validated and matches the hash pinned in the entry, or a pre-registered `client_id`, **and** the redirect URI used in that grant being one of the entry's redirect URIs (e.g. `https://claude.ai/api/mcp/auth_callback` → `claude`; `https://chatgpt.com/connector_platform_oauth_redirect` → `openai`). Everything else — DCR clients, loopback redirects, Cursor, Copilot Studio, Vertex, unknown CIMD hosts — gets `default` until someone adds a reviewed allowlist entry.
2. Claude and ChatGPT reach their profiles through CIMD (R8). Claude uses CIMD when the AS metadata advertises `client_id_metadata_document_supported: true` and `none` in `token_endpoint_auth_methods_supported`, which the AS does (bq-connector-oauth). ChatGPT publishes a CIMD document whose current shape (plural `token_endpoint_auth_methods_supported: ["none", "private_key_jwt"]`, legacy singular `private_key_jwt`) the AS must accept; bq-connector-oauth owns that parser and its fixture. A client that falls back to DCR gets `default`, even with a vendor redirect URI: DCR is always `default`.
3. If the fetched CIMD document of an allowlisted client no longer matches its pinned hash, bq-connector-oauth downgrades every affected grant's profile to `default` (audit `oauth.grant_downgraded`) until the entry is re-reviewed; it owns when revalidation runs. The connector reads the stored `grant.profile` on every request (no grant cache, §5.3), so the next call after a downgrade sees only `default` tools.
4. There is one MCP URL, `https://connect.ai.market/mcp` (R2). Effective tool set = `tools(grant.profile)`. No path, header, query parameter or body field selects, widens or narrows a profile.
5. `clientInfo.name`, `User-Agent`, `Origin`, `Mcp-Session-Id` and custom headers are logged (hashed where identifying) but never read for authorisation.
6. Why redirect binding is sound: the authorisation code only ever reaches the registered redirect URI, and PKCE binds it to the party that started the flow, so a token issued for a grant whose redirect was `claude.ai` can only be held by Claude's backend or by someone who already controls Claude's callback.

Tool sets in this BQ: `get_my_account` is in all three profiles. The profile tables for P1/P2 tools are filled by those BQs; this BQ ships the mechanism, the `default` rule "read-only tools only (`readOnlyHint: true`, not open-world)", and the ≤ 20-tools-per-profile lint.

### 5.5 Scope filtering

`visible(principal) = { t ∈ registry | t.name ∈ profile_tools(grant.profile) ∧ t.scopes_required ⊆ principal.scopes ∧ ¬killed(t) }`.

Scope semantics are all-of (R3): a tool is listed and callable only if the principal holds every scope in its `scopes_required`. Any-of semantics exist only where a tool explicitly declares `scopes_any_of`; no P0 tool does, and the lint rejects the field in P0. `tools/list` and `tools/call` evaluate the same predicate (one function in `registry.py`).

- `tools/list` returns exactly `visible`, sorted by name, no pagination needed below 50.
- `tools/call` for a name not in `visible` because of profile or kill switch → tool result `isError` with `TOOL_NOT_AVAILABLE` / `TOOL_DISABLED`; indistinguishable from an unknown tool in timing and wording except the code. For a tool in the profile but missing one or more of its `scopes_required` → HTTP 403 `insufficient_scope` (5.3). The check happens again at call time; the list is not trusted.
- Arguments are validated against the tool's JSON Schema before the handler runs; unknown properties rejected (`additionalProperties: false`).

### 5.6 Tool registry and lint

`@connector_tool(name, title, description, scopes_required, effect ∈ {read, write_reversible, write_destructive, open_world}, rate_class, input_model, output_model, profiles)` builds a `ToolSpec` and derives annotations: `readOnlyHint = effect == read`; writes always set `destructiveHint` explicitly; `openWorldHint` always explicit; `idempotentHint` explicit on writes.

CI lint `tests/connector/test_tool_lint.py` (runs in the normal pytest job; fails the build):
- name matches `^[a-z][a-z0-9_]{2,62}$`, unique; title present and ≤ 60 chars; description 40–1024 chars and contains no URLs other than `https://ai.market/...`;
- every tool has input and output schema; every non-read tool has a required `idempotency_key` string;
- annotations consistent with `effect`; no tool named or described as a catch-all (`run`, `execute`, `query`, `call_api`, free `url`/`sql` parameters);
- tools whose input or output carries counterparty text declare those fields `x-untrusted: true` and their descriptions say counterparty content is data (design §4);
- every tool declares a non-empty `scopes_required` whose scopes all exist in the scope catalogue (`scopes.py`); `scopes_any_of` is rejected in P0 (R3);
- per profile ≤ 20 tools; `default` contains only `effect == read`; every tool in `profiles.yaml` sets exists in the registry;
- list/call parity: the generated `tools/list` for a principal with all scopes equals the registry for each profile.

### 5.7 Error contract

One module maps domain failures to the three MCP channels:

| Condition | Channel | Code | Retry? | Message tells the model to |
|---|---|---|---|---|
| no/invalid/expired token, revoked grant, membership changed | HTTP 401 + `WWW-Authenticate` | `AUTH_REQUIRED` | after re-auth | ask the user to reconnect ai.market |
| scope missing for an allowed tool | HTTP 403 `insufficient_scope` | `INSUFFICIENT_SCOPE` | after step-up | ask the user to grant `<scope>` |
| connector globally off | HTTP 503 + JSON-RPC error `-32000` | `CONNECTOR_DISABLED` | `Retry-After` | tell the user the service is paused; status page link |
| pre-auth IP limit | HTTP 429 + `Retry-After` | `RATE_LIMITED` | yes | wait |
| malformed JSON-RPC, batch, GET/SSE on `/mcp` | JSON-RPC `-32600/-32601`; `405` for GET | `INVALID_REQUEST` | no | — |
| tool hidden by profile / killed | tool result `isError` | `TOOL_NOT_AVAILABLE` / `TOOL_DISABLED` | no | not retry; use listed tools |
| schema violation | tool result `isError` | `INVALID_ARGUMENT` + JSON pointer | after fix | fix field X |
| per-user/org/client limit | tool result `isError` | `RATE_LIMITED` + `retry_after_s` | yes | wait N s |
| object not found **or other org's** | tool result `isError` | `NOT_FOUND` | no | — (never `FORBIDDEN`: existence is not disclosed) |
| REVIEW (action-path, reserved) | tool result `isError` | `NEEDS_HUMAN` + confirmation URL | no | give the user the link |
| DENY (action-path, reserved) | tool result `isError` | `POLICY_DENIED` + reason | no | explain reason |
| DB/Redis/upstream down | tool result `isError` | `TEMPORARILY_UNAVAILABLE` | yes, backoff | retry later |
| anything else | tool result `isError` | `INTERNAL` | no | report `request_id` |

Tool-level errors use `isError: true` with `structuredContent = {"error": {"code", "message", "action", "retry_after_s"?, "request_id", "docs_url"?}}` and the same text in `content[0]`. `request_id` equals the trace id. No stack traces, SQL, internal ids of other principals, or token contents ever appear. The legacy `MCPHTTPException` envelope (`app/main.py:836-838`) is not reused: it is HTTP-shaped and the connector's errors are mostly in-band.

### 5.8 Rate limits

Redis, one atomic Lua script per check (ZREMRANGEBYSCORE + conditional ZADD + ZCARD + PEXPIRE) so a rejected call does **not** consume budget, unlike `mcp_middleware_service.py:34-72` and `rate_limiter.py:80-160`. Values are settings, defaults from design §6.

| Class | Key | Limit | Applies to |
|---|---|---|---|
| pre-auth | `conn:rl:v1:ip:<ip>` | 60 / 60 s | every request before token check (incl. 401s) |
| read | `conn:rl:v1:read:u:<user_id>` | 120 / 60 s | `initialize`, `tools/list`, `ping`, read `tools/call` |
| write | `conn:rl:v1:write:u:<user_id>` | 20 / 60 s | non-read `tools/call` (none in this BQ; key live) |
| outreach | `conn:rl:v1:outreach:o:<org_id>` | 30 / 86 400 s | `ask_seller` + `post_data_request` (P1) |
| offers | `conn:rl:v1:offer:o:<org_id>` | 50 / 86 400 s | `make_offer` (P3) |
| search | `conn:rl:v1:search:c:<client_id>:u:<user_id>` | 600 / 3 600 s | `search_listings` (P1) |
| strikes | `conn:abuse:v1:strikes:u:<user_id>` | 3 bursts / 24 h | a burst = any 60 s window with ≥1 rejection |

Keys with `o:<org_id>` use `u:<user_id>` instead when the principal's `org_id` is NULL (personal grant), e.g. `conn:rl:v1:outreach:u:<user_id>`.

A tool may consume several classes (e.g. `search_listings` = read + search). On the third burst in 24 h the connector inserts one row in `connector_review_queue` (user, org, client, counts, first/last) and applies a throttle factor of 0.5 to that user's read/write limits for 24 h; no suspension, no revocation (design §6). Humans clear the row; the appeal route is support email.

Redis failure: reads fall back to a per-process token bucket at `limit / expected_processes` (logged and counted); writes and the outreach/offer classes **fail closed** with `TEMPORARILY_UNAVAILABLE`. This is deliberately stricter than the existing fail-open limiters; spend/rate caps are in the Tier-3 fail-closed envelope. Responses carry `RateLimit-Limit/Remaining/Reset` headers on HTTP-level 429 only.

Each worker uses one bounded Redis connection pool (`CONNECTOR_REDIS_MAX_CONNECTIONS`, default 10; R6). A check that waits more than 100 ms for a pooled connection is treated as a Redis failure, so pool exhaustion degrades like an outage (reads fall back, writes fail closed) instead of opening more connections to the shared Redis. Budgets are in §5.13.

### 5.9 Audit hook

`AuditSink.record(event)` writes exactly one `tool.call` row per `tools/call` (success, tool error, denial) and one `http.auth_failure` row per IP per minute for 401/403s, aggregated to avoid write amplification from floods (`event_count` holds the number). `tools/list` is not audited, only counted in metrics.

New append-only table `connector_audit_events` (R4): `id, occurred_at, event_type, event_count (default 1), request_id, trace_id, user_id, org_id (NULL for personal grants), client_id, grant_id, profile, tool, scopes_used, outcome (ok|error), error_code, policy_decision (null|APPROVE|DENY|REVIEW, filled by action-path), pending_action_id (null), latency_ms, args_hmac, result_hmac, ip, user_agent_hmac, binding_terms (jsonb, null here; action-path)`.

- `event_type` (NOT NULL, CHECK against the catalogue): `tool.call`, `http.auth_failure`, `oauth.grant_created`, `oauth.grant_superseded`, `oauth.grant_revoked`, `oauth.grant_downgraded`, `oauth.refresh_reuse_detected`, `oauth.registration_created`, `action.confirm`, `action.decline`. A new type is a migration plus a contract-test row, reviewed in the BQ that writes it.
- NOT NULL: `id, occurred_at, event_type, event_count, outcome`. Nullable: `tool, user_id, grant_id, args_hmac, result_hmac` (R4) and every other column, because AS and HTTP events have no tool and registration and auth-failure events have no user or grant. A CHECK requires `tool`, `user_id`, `grant_id`, `client_id` and `args_hmac` when `event_type = 'tool.call'`.
- One row per tool call: partial unique index on `request_id` where `event_type = 'tool.call'` (batches are rejected, so a request carries at most one call).
- Writers: core (`tool.call`, `http.auth_failure`); the AS service (`oauth.*`); action-path (`tool.call` for the calls it executes, via `record_required`, and `action.confirm` / `action.decline` from its web routes).

Reads store HMACs (keyed by `CONNECTOR_AUDIT_HMAC_KEY`) of canonical JSON args and results, never content (design §6 "reads hashed"). No free text, no secrets, no tokens. Access: the application role has INSERT and SELECT on its own rows only via the service; UPDATE/DELETE revoked (migration grants). Retention (adopted Q5a, same in all three connector specs): keep every row until legal sign-off, then apply the retention matrix; no purge path ships before sign-off. This is the single connector audit table: bq-connector-action-path writes its rows (with `policy_decision`, `pending_action_id`, `binding_terms` filled) through `AuditSink.record_required()` and does not extend `agent_audit_log`.

Failure mode: a read tool whose audit insert fails still returns its result, emits the event to structured logs and increments `connector_audit_write_failures_total`; an alert fires above 0.1 % over 5 min. Writes (action-path) must fail closed on audit failure; this BQ exposes `AuditSink.record_required(event, session)`, which inserts on the caller's DB session so the row commits or rolls back with the effect. For a `tools/call` executed through action-path's `execute_connector`, action-path writes the one row for that call and core's hook does not write a second; action-path's web confirm/decline routes write `action.confirm` / `action.decline` rows.

Joint contract test `tests/connector/test_audit_contract.py` (shared with bq-connector-oauth and bq-connector-action-path and run in each one's CI): each named `event_type` inserts exactly one valid row through the sink its writer uses; a `tool.call` routed through `execute_connector` yields exactly one row; a second `tool.call` insert for the same `request_id` is refused.

`agent_audit_log` is not reused: it is keyed by API key, lacks user/org/client, and its production shape is uncertain (§4.3).

### 5.10 Tracing and logs

`asgi.py` calls the existing `init_telemetry(app, engine)` with `OTEL_SERVICE_NAME=ai-market-connector`. Spans: `connector.http` (root), `mcp.<method>`, `mcp.tool.<name>`, plus existing SQLAlchemy/Redis auto-instrumentation. Attributes from an allowlist only: `mcp.method.name`, `mcp.tool.name`, `mcp.protocol.version`, `connector.profile`, `connector.client_id`, `connector.outcome`, `connector.error_code`, `enduser.id_hash`. Tool arguments, results, tokens, emails and IPs are never span attributes. JSON logs carry `request_id` = trace id. Metrics: requests by method/profile/outcome, tool latency histogram (p95 read < 2 s is a design success metric), limiter rejections, fallback activations, switch state.

### 5.11 Kill switches

Three levels, checked on every request:

1. **Env floor** `CONNECTOR_ENABLED` (default `false`). False → every `/mcp*` request gets 503 `CONNECTOR_DISABLED`; health and metadata still answer. Needs a restart to change; used for launch and for "Postgres is down, we still want it off".
2. **Global / per-profile / per-tool** rows in `connector_switches(scope ∈ {global, profile, tool}, key, disabled, reason, actor, updated_at)`, read through a 5 s in-process cache. A disabled profile makes the connector answer that profile's requests with 503 `CONNECTOR_DISABLED` (profile-level message); a disabled tool vanishes from `tools/list` and returns `TOOL_DISABLED`.
3. On switch-read failure the last loaded state is kept; a process that has never loaded state treats everything as disabled (fail closed).

Postgres, not Redis, is the source of truth because a kill switch must not be lost to Redis eviction or restart, unlike the allAI precedent (`kill_switches.py`) which reads as "off" without Redis. Toggling is by the runbook SQL or an internal-key endpoint on the main backend (`POST /api/v1/internal/connector/switches`, `X-Internal-API-Key`, audited); the new runbook page (§7) is part of this BQ's done. Target time from decision to effect: ≤ 10 s.

### 5.12 First tool: `get_my_account`

- Scope `account.read`; effect read; all profiles; rate class read.
- Output: `{user: {id, display_name, email}, organization: {id, name, role} | null, connection: {client_name, profile, scopes, granted_at}, seller: {has_seller_profile}, negotiation_limits: null}` (`negotiation_limits` is filled in P3; design §4 row; `organization` is `null` for a personal grant).
- Reads only rows owned by `principal.user_id` and, when set, `grant.org_id`; no argument accepts an id. Proves: token → grant → live org binding → profile → scope filter → limiter → audit → trace.

### 5.13 Deployment on Railway

Two services from the same image (R1), both in project `e81dd66f-808c-412e-b32c-f6d910f0ac5d`, environment `production`:

| Service | Entrypoint | Host | Key material |
|---|---|---|---|
| `ai-market-connector` (resource server; this BQ's code) | `app.mcp.connector.asgi:app` | `https://connect.ai.market/mcp` | public JWKS only, fetched from `CONNECTOR_JWKS_URL` |
| `ai-market-connector-auth` (authorization server; bq-connector-oauth's code, this BQ's service config) | `app.mcp.connector_auth.asgi:app` | `https://auth.ai.market` (issuer) | sole holder of `CONNECTOR_OAUTH_SIGNING_KEYS`; serves `https://auth.ai.market/.well-known/jwks.json` |

`railway.connector.json`:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": {
    "startCommand": "sh -c 'exec uvicorn app.mcp.connector.asgi:app --host 0.0.0.0 --port 8080 --workers ${CONNECTOR_WORKERS:-2} --log-level ${LOG_LEVEL:-info} --timeout-graceful-shutdown 20 --limit-concurrency ${CONNECTOR_MAX_CONCURRENCY:-50}'",
    "healthcheckPath": "/readyz",
    "numReplicas": 2,
    "restartPolicyType": "ON_FAILURE"
  }
}
```

`railway.connector-auth.json`:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": {
    "startCommand": "sh -c 'exec uvicorn app.mcp.connector_auth.asgi:app --host 0.0.0.0 --port 8080 --workers ${CONNECTOR_AUTH_WORKERS:-2} --log-level ${LOG_LEVEL:-info} --timeout-graceful-shutdown 20 --limit-concurrency ${CONNECTOR_AUTH_MAX_CONCURRENCY:-50}'",
    "healthcheckPath": "/readyz",
    "numReplicas": 2,
    "restartPolicyType": "ON_FAILURE"
  }
}
```

- The AS entrypoint must serve `/healthz` and `/readyz` (bq-connector-oauth). Until its code lands, the foundation stage ships a stub `app/mcp/connector_auth/asgi.py` that serves only those two and 404 elsewhere, so the service can be configured and health-checked with flags off.
- No Alembic at start on either service: the backend web service owns migrations (`Dockerfile:103`); the connector's migration ships through the backend deploy first and the connector tolerates missing connector tables by failing `/readyz`.
- Port 8080 is hard-coded because the custom domain's target port is 8080 (D9); `PORT` is ignored. The auth service also listens on 8080; `auth.ai.market`'s custom-domain target port is set to 8080 when it is created.
- Each service's config-file path is set to its `railway.connector*.json` the same way the worker uses `railway.worker.json` (mechanism **UNVERIFIED** for these services; follow `celery-infrastructure-deployment.md`). No `*.up.railway.app` service domain is generated; only `connect.ai.market` and `auth.ai.market`.
- Dockerfile smoke gains `python -c "import app.mcp.connector.asgi"` and a check that importing it imports neither `app.main` nor anything under `app.mcp.connector_auth` (A19, A23); importing `app.main` likewise loads nothing under `app.mcp.connector_auth`.
- Key isolation (R1), three layers: (1) static: `tests/connector/test_key_isolation.py` fails (AST scan) if any module under `app/mcp/connector/` or the main backend imports `app.mcp.connector_auth`, if any module under `app/mcp/connector_auth/` imports `app.mcp.connector`, or if `app/mcp/connector_shared/` imports either; and, in a subprocess, if `import app.mcp.connector.asgi` or `import app.main` leaves any `app.mcp.connector_auth*` module in `sys.modules`; (2) startup: `ConnectorSettings` refuses to start when `CONNECTOR_OAUTH_SIGNING_KEYS` is present; (3) deploy: the runbook's pre-enable check lists the `ai-market-connector` variables and fails if `CONNECTOR_OAUTH_SIGNING_KEYS` is among them. Infisical must deliver the key to the auth service only (path and scoping **UNVERIFIED**; bq-connector-oauth names them).

Connector service env vars (least secret; everything else deliberately absent — no `CONNECTOR_OAUTH_SIGNING_KEYS`, Stripe, Gmail, KMS, GCP, Telegram, author DSN, internal API key):

| Var | Value |
|---|---|
| `CONNECTOR_ENABLED` | `false` at first deploy |
| `CONNECTOR_PUBLIC_BASE_URL` | `https://connect.ai.market` |
| `CONNECTOR_AUTH_ISSUER` | `https://auth.ai.market` (R1) |
| `CONNECTOR_JWKS_URL` | `https://auth.ai.market/.well-known/jwks.json` (public ES256 keys only; R1, adopted Q3a) |
| `CONNECTOR_ALLOWED_HOSTS` | `connect.ai.market` |
| `CONNECTOR_EARLY_ACCESS_USER_IDS` | test and Max accounts during rollout (empty = everyone) |
| `CONNECTOR_AUDIT_HMAC_KEY` | new Infisical secret |
| `CONNECTOR_WORKERS`, `CONNECTOR_MAX_CONCURRENCY` | 2, 50 per worker (draft had 200; R6, see capacity) |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_STATEMENT_TIMEOUT_MS` | 5, 5, 5000 (requires parameterising `app/core/database.py:37-50`; backend defaults unchanged at 20/10) |
| `DATABASE_URL` | restricted application role (not the schema-owner DSN) |
| `REDIS_URL`, `CONNECTOR_REDIS_MAX_CONNECTIONS` | Redis service reference; 10 per worker (R6) |
| `SECRET_KEY` | required by `Settings` (`config.py:747-765`); a separate random value, not the backend's, used for no signing (adopted Q3a) |
| `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_SERVICE_NAME=ai-market-connector` | as backend |

Auth service env (this BQ creates the service; bq-connector-oauth owns the full list): `CONNECTOR_OAUTH_SIGNING_KEYS` (Infisical, this service only), `CONNECTOR_AUTH_ISSUER=https://auth.ai.market`, `CONNECTOR_OAUTH_ENABLED=false` and its sub-flags off at first deploy, `CONNECTOR_AUTH_WORKERS=2`, `CONNECTOR_AUTH_MAX_CONCURRENCY=50`, `DB_POOL_SIZE=3`, `DB_MAX_OVERFLOW=2`, `DB_STATEMENT_TIMEOUT_MS=5000`, `CONNECTOR_REDIS_MAX_CONNECTIONS=5`, `DATABASE_URL` (restricted role), `REDIS_URL`, its own random `SECRET_KEY`, OTel with `OTEL_SERVICE_NAME=ai-market-connector-auth`.

Capacity budget (R6; per-process pools are hard caps):

| Service | Processes (replicas × workers) | Postgres (pool + overflow) | Redis (pool) |
|---|---|---|---|
| `ai-market-connector` | 2 × 2 = 4 | 4 × (5 + 5) = 40 | 4 × 10 = 40 |
| `ai-market-connector-auth` | 2 × 2 = 4 | 4 × (3 + 2) = 20 | 4 × 5 = 20 |
| **New total** | 8 | **60** | **60** |

`CONNECTOR_MAX_CONCURRENCY` drops from the draft's 200 to 50 per worker: a request holds at most one DB and one Redis connection at a time, so 50 in flight over 10-connection pools bounds queueing to the pools' wait timeouts, and uvicorn answers 503 beyond that instead of piling load onto the shared Postgres and Redis. The value is re-tuned from the Gate 3 load test and is not raised without redoing this table.

Pre-deploy check (foundation stage, repeated before enabling and before adding a replica to either service): Postgres `SHOW max_connections` minus the peak `pg_stat_activity` count, and Redis `maxclients` (`CONFIG GET maxclients`, or Railway's configured limit if `CONFIG` is disabled) minus the peak `INFO clients` `connected_clients`, each measured across the backend, workers, Beat and every other consumer, must leave the new totals above plus 25 %. Live values are **UNVERIFIED**; they are measured and recorded in `customer-mcp-connector.md` before Gate 4.

### 5.14 SDK upgrade plan and blast radius

Recommendation: **`mcp>=1.30,<2`** in this BQ (Q1). It is the newest 1.x, speaks 2025-11-25 (the design floor), keeps the FastMCP API the two existing mounts and `aim_node` use, and needs no new HTTP client. mcp 2.x (2026-07-28 stateless envelope, `server/discover`) is a follow-up BQ once 2.x has settled: it renames FastMCP (import raises), adds `httpx2`, and would drag `aim_node`, `aim_discovery`, `marketplace_remote`, `scripts/allai_bridge.py` and tests into this Tier-3 change. The connector keeps SDK types inside `transport.py` so the move is local.

Chunk 0 (its own PR, lands and deploys before any connector code):
1. `requirements.txt`: `mcp>=1.30,<2`; `uvicorn[standard]>=0.31.1` (forced by mcp ≥1.14); remove unused `fastmcp>=0.3`. Coordinate with `BQ-STARLETTE-CVE-48710-FRAMEWORK-UPGRADE-S1658` (proposed Gate 1, not built), which resolves the same graph: whichever lands first sets the uvicorn/starlette pins, the other rebases. FastAPI 0.110.1 with Starlette ≥0.27 satisfies mcp 1.30 (`starlette>=0.27` for Python < 3.14).
2. `pyproject.toml:15` (`aim-node`): `mcp>=1.24,<2`. Today `mcp>=1.0` lets a fresh `aim-node` install resolve mcp 2.2.0, whose `mcp.server.fastmcp` import raises; whether published `aim-node` releases are already affected is **UNVERIFIED** (no `aim-node` project was found on public PyPI; the publish target of `hatch publish` was not traced).
3. `app/mcp/aim_discovery.py:15-24` and `app/mcp/marketplace_remote.py:34-45`: pass explicit `transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=["api.ai.market", <backend railway host>], allowed_origins=[…])` (or explicitly disabled with a comment). Without this, mcp 1.30's default turns on localhost-only Host checking and **every request to `https://api.ai.market/mcp/aim-discovery/mcp` returns 421** — silently, because the mount's failures are swallowed and the Dockerfile smoke only imports `app.main`.
4. Tests: an ASGI test that sends `initialize` then `tools/list` to `/mcp/aim-discovery/mcp` with `Host: api.ai.market` and expects 200 and the 5 tools; same for `/mcp/marketplace/mcp` with the flag on; `tests/test_aim_tool_wrapper.py` still passes (it uses `mcp.server.fastmcp.tools.Tool`, an internal class whose constructor may have changed — **UNVERIFIED** until run); `aim_node` seller server test suite; `scripts/allai_bridge.py` import check.
5. Rebuild `.venv-ci` so CI stops testing mcp 1.8.1.

Blast radius: backend web (two mounts, uvicorn), `aim-node` package consumers, CI. Workers and Beat do not run uvicorn or MCP. Rollback: revert the Chunk 0 commit; no data change.

### 5.15 Retirement path for the other surfaces (plan only)

| Surface | Evidence | Retirement (bq-mcp-surface-retirement, after P1) |
|---|---|---|
| PyPI/npm `aimarket-mcp` (`aim_` keys) | `aimarket-mcp-server.md` | final release that prints a deprecation notice pointing to `connect.ai.market`; yank after 60 days |
| MCPB bundle | design D2 | withdraw from directory; notice |
| `marketplace_remote` FastMCP | `app/main.py:996-1011`, flag default off | delete module, flag and `/health/mcp-marketplace` (`:1230-1242`) |
| Legacy SSE / JSON-RPC (`/api/v1/mcp/*`, `/api/v1/agent/sse`, `/tools/call`) | `mcp_server.py:293`, `mcp.py:151`, `mcp_sse.py:375,397` | 410 with a link, then delete; MCP API keys revoked after migration notice |
| Public WebMCP manifest | `app/main.py:899-904` | replace content with a pointer to the connector's server card / registry entry |
| AIM Discovery mount | `app/main.py:1013-1024` | stays until D6 (model/compute listings after P1) decides its home |

Precondition for each: usage in the last 30 days measured from logs; zero-usage surfaces go first. This BQ only records the plan and ensures nothing in the connector depends on these surfaces.

## 6. Invariants

- I1 No request reaches a tool handler without a verified token, an active grant and a live org binding (active membership in the grant's org, or no active membership for a personal grant with `org_id` NULL).
- I2 The effective profile is the stored `grant.profile` only; no path, request header or body field can select, widen or narrow it.
- I3 `tools/call` re-checks visibility; `tools/list` output is never trusted as authorisation. A tool is visible and callable only if all its `scopes_required` are granted (R3).
- I4 Every data read is filtered by `principal.user_id` and, when set, `grant.org_id`; cross-org objects are `NOT_FOUND`.
- I5 Tokens not issued by `CONNECTOR_AUTH_ISSUER` (`https://auth.ai.market`) for the connector audience `https://connect.ai.market/mcp` (ES256 only, keys from the AS JWKS) are rejected. The connector service never holds `CONNECTOR_OAUTH_SIGNING_KEYS` and never imports the AS signing module (R1).
- I6 Limits never fail open for write, outreach or offer classes; rejected calls do not consume budget; no automatic suspension.
- I7 Kill switches take effect within 10 s and fail closed on first load.
- I8 The connector process never runs Alembic, schedulers, Celery or `app.main`'s lifespan.
- I9 No tool arguments, results, tokens or emails in spans, metrics labels or audit rows (HMACs only).
- I10 Stateless: no server-side MCP session state; any replica can serve any request; `Mcp-Session-Id` is ignored.
- I11 Every tool passes the lint; each profile has ≤ 20 tools; `default` is read-only.
- I12 Exactly one `connector_audit_events` row per `tools/call`; every row carries an `event_type` from the catalogue (R4).

## 7. Security analysis

**Profile escalation.** Vectors: (a) spoofed `clientInfo`/User-Agent — ignored (I2); (b) DCR client registering Claude's redirect URI — gets `default` because DCR is not on the allowlist, and even if it were, codes go only to `claude.ai`; (c) choosing a different URL — there is only `https://connect.ai.market/mcp`, and the profile comes from the grant alone (R2); (d) token replay from another resource (legacy `oauth_agent`, `mcp.ai.market`) — audience/issuer check (I5); (e) grant for org A used after the user moved to org B — live membership check (I1); (f) a CIMD document changed after allowlisting — the oauth BQ pins the verified metadata hash and, on a mismatch, downgrades the affected grants' stored profile to `default` (`oauth.grant_downgraded`) until re-reviewed; the connector reads the stored profile on every request, so the next call sees `default` (R8; revalidation timing is bq-connector-oauth's, Q2); (g) a token holding only some of a tool's scopes — all-of semantics hide and refuse the tool (R3).

**Unauthenticated `tools/list` leakage.** Every `/mcp*` JSON-RPC method, including `initialize` and `tools/list`, requires a bearer token; unauthenticated callers get 401 with only the PRM pointer. PRM discloses the issuer and `scopes_supported`, nothing per-user. The public tool catalogue is documented on the docs page (P1), not served anonymously. If OpenAI review needs anonymous discovery, that is Q4, not a default.

**DoS.** Body cap 256 KB before parsing; JSON-RPC batches rejected; `GET /mcp` (SSE stream) 405 and `json_response=True`, so no long-lived connections; pre-auth IP limiter runs before signature verification and DB; signature check before any DB read; DB statement timeout 5 s; uvicorn `--limit-concurrency`; separate service and separate small DB pool so a connector flood cannot exhaust the backend's pool; audit of 401s aggregated. Residual: a distributed flood across many IPs is absorbed only by Railway; Cloudflare is not in the path (DNS-only) — Q6.

**Header spoofing behind Railway.** The connector uses `resolve_client_ip` (`request_ip.py:138-165`): trust XFF only from an internal-hop peer, leftmost entry, never `X-Envoy-External-Address`, never `CF-Connecting-IP` (DNS-only zone record). The 2026-07-13 evidence was gathered on the backend service; the same edge behaviour on the new service is **UNVERIFIED** and is a Gate 4 probe (send a forged `X-Forwarded-For: 1.2.3.4` and confirm the resolved IP is the real caller). Uvicorn's own proxy-header handling stays inert (default `forwarded_allow_ips=127.0.0.1`; Railway peers are not loopback), as on the backend. `Host` must be in `CONNECTOR_ALLOWED_HOSTS` (421 otherwise); `Origin`, when present, must be allowlisted (403), per the MCP transport's DNS-rebinding guidance. IP is only a limiter key and audit field, never an authorisation input, so a spoofing failure degrades rate limiting, not access.

**Secrets on the connector.** Holding the backend `SECRET_KEY` would let a connector compromise forge legacy tokens and anything else signed with it (`oauth_service.py:365-377` signs with it). Adopted Q3a removes that exposure: connector tokens are ES256 and each service's `SECRET_KEY` is its own unrelated random value. Holding the ES256 private key would be the same failure one step later: a remote-code-execution bug in the process that parses untrusted JSON-RPC and runs tool handlers would mint tokens for any user, org and scope. Module separation inside one process is not a boundary, so the AS runs as its own Railway service (`ai-market-connector-auth`, `https://auth.ai.market`) and is the sole holder of `CONNECTOR_OAUTH_SIGNING_KEYS`; the connector service holds only the public JWKS (R1). "Holds no signing key" is a claim about `ai-market-connector` only, enforced by the static import check, the startup refusal and the deploy-time variable check (§5.13, A23). Residual: both services share Postgres and Redis, so a connector compromise can still reach what its DB role allows; it cannot sign.

**Prompt injection.** Not exercised by `get_my_account` (no counterparty text). The registry's `x-untrusted` marking and lint exist now so P1 tools cannot ship without them.

## 8. Acceptance criteria → tests

| # | Criterion | Test |
|---|---|---|
| A1 | `get_my_account` succeeds from Claude (claude.ai custom connector) with the test account through the CIMD path: the AS advertises `client_id_metadata_document_supported: true` and `none`, Claude presents its allowlisted CIMD `client_id` (not a DCR id), and the grant profile is `claude` (R8) | Gate 4 manual E2E, screenshots + `oauth.grant_created` row showing the CIMD `client_id` + `tool.call` row + trace id (needs bq-connector-oauth) |
| A2 | Same from ChatGPT developer mode on `https://connect.ai.market/mcp` through ChatGPT's allowlisted CIMD `client_id` (current document shape, plural `token_endpoint_auth_methods_supported`); profile `openai` (R8) | Gate 4 manual E2E, CIMD path shown in the `oauth.grant_created` row; the CIMD parsing fixture is bq-connector-oauth's |
| A3 | Same from Cursor; profile `default` | Gate 4 manual E2E |
| A4 | MCP Inspector connects over streamable HTTP, protocol 2025-11-25 negotiated, `tools/list` = `[get_my_account]` | `tests/connector/test_transport_inspector.py` (SDK client) + Gate 4 Inspector run |
| A5 | Unknown/DCR/loopback client → `default`; DCR is always `default`, even with a vendor redirect URI; a grant downgraded after a pinned-hash mismatch gets `default` tools on the next call | `test_profiles.py::test_unknown_client_default` (parametrised: DCR id, DCR id with `https://claude.ai/api/mcp/auth_callback`, unknown CIMD host, loopback redirect, spoofed `clientInfo.name="claude-ai"`), `::test_downgraded_grant_next_call` |
| A6 | Profile comes only from the grant: one MCP URL, any other `/mcp/*` path → 404, no header, query or body field changes the tool set (R2) | `test_profiles.py::test_profile_from_grant_only` |
| A7 | `tools/list` = profile tools whose `scopes_required` ⊆ granted scopes, minus killed; `tools/call` evaluates the same predicate; a principal holding a proper subset of a multi-scope tool's `scopes_required` can neither list nor call it (R3) | `test_scope_filter.py` (property tests over scope subsets with a synthetic multi-scope tool) |
| A8 | Unauthenticated `initialize`/`tools/list`/`tools/call` → 401 + `resource_metadata`; no tool names in body | `test_auth.py::test_unauth_no_leak` |
| A9 | Legacy `oauth_agent` token, HS256-signed token, wrong issuer, wrong audience (incl. `https://connect.ai.market` without `/mcp`), expired, revoked grant, token in query, token with any issuer other than `https://auth.ai.market` (incl. the draft's `https://connect.ai.market`) → 401; a valid token's `VerifiedToken` carries `token_jti` (R7) | `test_auth.py` parametrised |
| A10 | Cross-org: user A never sees org B data; grant for org A after membership moved to B → 401; forged `sub` of another user with A's grant → 401; personal grant (`org_id` NULL) accepted while the user has no membership and 401 once they join an org | `test_cross_org.py` (two orgs, two users, real DB) |
| A11 | Missing scope for allowed tool → 403 `insufficient_scope` with `scope=` | `test_auth.py::test_step_up` |
| A12 | Rate limits at §5.8 values; rejected calls don't consume; Redis down → reads local fallback, writes fail closed; third burst → one review-queue row, no suspension | `test_ratelimit.py` (fakeredis + Lua, clock control) |
| A13 | Kill switches: global/profile/tool effective ≤ 10 s; cold start with DB down → disabled; env floor wins | `test_switches.py` |
| A14 | Error contract: each row of §5.7 produces the documented channel, code, and no internal detail | `test_errors.py` table-driven |
| A15 | Audit: exactly one `tool.call` row per `tools/call` with HMACs only (duplicate insert refused); 401 floods aggregated into `http.auth_failure` rows; audit failure does not fail a read; every named `event_type` inserts exactly one valid row (R4) | `test_audit.py`, joint `test_audit_contract.py` |
| A16 | Tracing: spans present with allowlisted attributes only | `test_telemetry.py` (in-memory exporter; asserts no arg values) |
| A17 | Tool lint enforced | `test_tool_lint.py`, plus a negative fixture registry that must fail |
| A18 | Header safety: forged XFF from external peer ignored; bad Host 421; bad Origin 403; body > 256 KB 413; GET `/mcp` 405; batch rejected | `test_transport_security.py`; Gate 4 forged-XFF probe on production |
| A19 | Import hygiene: `import app.mcp.connector.asgi` does not import `app.main`, starts no scheduler | `test_import_hygiene.py` (subprocess) + Dockerfile smoke |
| A20 | SDK Chunk 0: AIM Discovery and (flag-on) marketplace mounts answer `initialize` with `Host: api.ai.market`; aim_node and wrapper tests pass; `pyproject` bounded | `test_mcp_mounts_sdk_upgrade.py` + existing suites; production curl after deploy |
| A21 | `/healthz` 200 without deps; `/readyz` 503 when DB or Redis or connector tables missing | `test_health.py` |
| A22 | Stateless: two sequential calls routed to different app instances succeed without session id | `test_stateless.py` (two app instances, shared Redis/DB) |
| A23 | Key isolation (R1) and package rules: no module under `app/mcp/connector/` or the main backend imports `app.mcp.connector_auth`; `app/mcp/connector_auth/` imports only `app.mcp.connector_shared` among connector packages; `app/mcp/connector_shared/` imports neither; importing `app.mcp.connector.asgi` or `app.main` loads no `app.mcp.connector_auth*` module; the connector refuses to start with `CONNECTOR_OAUTH_SIGNING_KEYS` set; production `ai-market-connector` variables lack it; PRM `authorization_servers` = `["https://auth.ai.market"]` | `test_key_isolation.py`, `test_settings.py::test_refuses_signing_key`, `test_prm.py`; Gate 4 variable listing |
| A24 | Capacity (R6): Redis and Postgres pools bounded per worker; Redis pool exhaustion → reads fall back, writes `TEMPORARILY_UNAVAILABLE`; pre-deploy headroom check recorded | `test_ratelimit.py::test_pool_exhaustion`; Gate 3 load test at configured concurrency; Gate 4 recorded check |

## 9. Rollout, flags, rollback

This is the single merge/deploy order for the three P0 connector specs (R5); any text elsewhere implying a different order is superseded by this list.

1. **Connector foundation** (owned by this BQ; inert, nothing customer-reachable):
   - (a) SDK Chunk 0 merges and deploys on the backend; A20 verified in production (`/mcp/aim-discovery/mcp` initialize 200).
   - (b) Foundation PR: the `app/mcp/connector_shared/` package, the shared migration (`connector_switches`, `connector_audit_events` with `event_type`, `connector_review_queue`), `profiles.yaml` and the scope catalogue, the §5.3 interfaces (`VerifiedToken` incl. `token_jti`, `TokenVerifier`, `Grant`, `GrantStore`) with fakes, the verifier contract tests and the joint audit contract test, both `railway.connector*.json` files, the key-isolation check (A23), and the stub `app/mcp/connector_auth/asgi.py` (health routes only). The migration deploys via the backend service.
   - (c) Both Railway services configured: `ai-market-connector` (`connect.ai.market`) and the new `ai-market-connector-auth` (`auth.ai.market` DNS-only record and custom domain), env per §5.13 with `CONNECTOR_ENABLED=false` and `CONNECTOR_OAUTH_ENABLED=false`, signing keys on the auth service only; the Redis/Postgres capacity check (§5.13) run and recorded.
2. **OAUTH AS** (bq-connector-oauth) deploys on `ai-market-connector-auth` with its flags off.
3. **Connector server** (the rest of this BQ) deploys on `ai-market-connector` with `CONNECTOR_ENABLED=false`; verify `/healthz`, `/readyz`, PRM, 503 on `/mcp`, forged-XFF probe, Host check, A23 variable check.
4. **Enable together:** `CONNECTOR_OAUTH_ENABLED=true` (CIMD on) and `CONNECTOR_ENABLED=true` with `CONNECTOR_EARLY_ACCESS_USER_IDS` = test accounts + Max; A1–A3 E2E.
5. Early-access list emptied when P1 buyer tools ship (bq-connector-buyer decides).

bq-connector-action-path's migrations and flag-off code land after step 1 (they need the foundation's audit table); its flags turn on only after step 4, in the order its spec gives.

Rollback: DB global switch (≤ 10 s) → `CONNECTOR_ENABLED=false` (restart) → redeploy previous image. Either service rolls back alone and neither rollback touches the backend. Turning the AS off (`CONNECTOR_OAUTH_ENABLED=false`) stops new authorizations and refreshes only: access tokens already issued (≤ 1 h) keep verifying locally: the public JWKS route stays served when that flag is off (metadata does not), and the verifier keeps its last successfully fetched key set if a refresh fails (with an alert), failing closed only when it has never fetched one (e.g. first start while the auth service is down). Live access is cut by the connector kill switch (DB global / per-profile / per-tool switches, `CONNECTOR_ENABLED=false`) and by grant revocation, which is checked live on every call. Chunk 0 rolls back by reverting its commit. Migrations only add tables, so no down-migration is needed to roll back code; the foundation stays in place, inert.

## 10. Dependencies

- **bq-connector-oauth (hard, for A1–A3, A9 in production):** provides the AS code for `ai-market-connector-auth` (`app.mcp.connector_auth.asgi:app`; issuer `https://auth.ai.market`; JWKS `https://auth.ai.market/.well-known/jwks.json`; sole holder of `CONNECTOR_OAUTH_SIGNING_KEYS`), token format (ES256 JWT with `jti`), `TokenVerifier`/`GrantStore` implementations and the revocation hooks placed in the key-free `app.mcp.connector_shared` so the connector and the main backend can import them, grant rows with `org_id` (nullable: personal grant) and `profile`, CIMD verification (including ChatGPT's current document shape), metadata pinning and the downgrade on hash change, AS metadata advertising `client_id_metadata_document_supported` and `none`, the redirect allowlist, and the `oauth.*` audit rows. Everything else here builds and tests against fakes. Contract freeze: the §5.3 interfaces and the foundation stage (§9 step 1) are agreed at both Gate 2s.
- **bq-connector-action-path (soft):** fills `policy_decision`, `pending_action_id`, `binding_terms` in `connector_audit_events` (the single connector audit table; `agent_audit_log` is not extended) and uses `NEEDS_HUMAN`/`POLICY_DENIED` and `AuditSink.record_required()`; its web confirm/decline routes write `action.confirm` / `action.decline` rows. No write tool ships from this BQ; action-path lands after the foundation stage (§9).
- **BQ-STARLETTE-CVE-48710-FRAMEWORK-UPGRADE-S1658 (coordination):** same dependency graph (uvicorn/starlette/FastAPI).
- Runbooks PR #266 (connect.ai.market DNS) should merge before Gate 4, and the `auth.ai.market` record follows the same procedure; a new runbook page `customer-mcp-connector.md` (deploy, env, switches SQL, limits, alerts, rollback) is written in this BQ before it is reported done.

## Cross-spec contract

This section is identical in the three P0 connector specs (`BQ-CONNECTOR-CORE-GATE1.md`, `BQ-CONNECTOR-OAUTH-GATE1.md`, `BQ-CONNECTOR-ACTION-PATH-GATE1.md`). Changing anything here changes all three and needs all three Gate 2s to agree. It reflects the controller rulings of Council Gate 1 round 1 (2026-09-23) and the controller's package-layout and rollback rulings of the same day; where a spec body disagrees with this section, this section wins and the body is wrong.

- **Packages and import rules.** Three packages in ai-market-backend:
  - `app/mcp/connector_shared/`: everything both services need, key-free: `VerifiedToken`, `TokenVerifier` (ES256 verification against the JWKS), `Grant`, `GrantStore` / `load_active_grant`, the `revoke_grant` / `revoke_all_for_user` hooks, the `profiles.yaml` loader (and the file, `app/mcp/connector_shared/profiles.yaml`), the scope catalogue, `AuditSink` (incl. `record_required`), and the OAuth persistence both the AS and the main-backend consent / Connected-apps APIs use: the ORM models for `connector_oauth_clients`, `_transactions`, `_grants`, `_codes`, `_refresh_tokens` (`oauth_models.py`) and the key-free grant and consent-ticket functions (`oauth_store.py`: create/replace grant, write and redeem the single-use ticket; `revoke_grant` and `revoke_all_for_user` live only in `grants.py`).
  - `app/mcp/connector_auth/`: the authorization server (AS); the only package that imports the signing module. Entrypoint `app.mcp.connector_auth.asgi:app`, Railway service `ai-market-connector-auth`, host and issuer `https://auth.ai.market`.
  - `app/mcp/connector/`: the MCP resource server. Entrypoint `app.mcp.connector.asgi:app`, Railway service `ai-market-connector`, `https://connect.ai.market/mcp`.
  - Import rules, enforced by CI: `app.mcp.connector` and the main backend (`app.main`, `app.api`, `app.services`, `app.actions`) may import `app.mcp.connector_shared` but never `app.mcp.connector_auth`; `app.mcp.connector_auth` may import `app.mcp.connector_shared` (and not `app.mcp.connector`); `app.mcp.connector_shared` imports neither.
- **Issuer, keys, resource.** Issuer `CONNECTOR_AUTH_ISSUER = https://auth.ai.market`; JWKS `CONNECTOR_JWKS_URL = https://auth.ai.market/.well-known/jwks.json` (public keys only). The sole resource and token audience is `CONNECTOR_AUDIENCE = https://connect.ai.market/mcp`: no alias URL, no audience normalisation; the profile (including `openai`) comes only from the verified grant. Access tokens are ES256 JWTs; the private signing keys (`CONNECTOR_OAUTH_SIGNING_KEYS`) exist only in the `ai-market-connector-auth` environment; `ai-market-connector` and the main backend hold only public keys and refuse or fail checks if the key is present. The resource server's PRM lists `authorization_servers: ["https://auth.ai.market"]`.
- **Interfaces.** `VerifiedToken` carries `user_id, client_id, grant_id, token_jti, scopes, issuer, audience, expires_at` (`token_jti` = the JWT `jti`; core copies it into action-path's `ConnectorPrincipal.token_jti`, persisted in `connector_action_requests.token_jti`). `Grant.org_id` is `UUID | None` (None = personal grant). Live org-binding rule, checked on every call: if `grant.org_id` is set, the user must hold an active membership in that org; if it is NULL, the user must hold no active membership; otherwise 401 `invalid_token` (reconnect). Reads filter by `user_id` and, when set, `org_id`; org-keyed rate limits fall back to the user id when `org_id` is NULL.
- **Scopes.** All-of semantics everywhere: a tool is listed, callable and executable (`tools/list`, `tools/call`, `execute_connector`) only if `scopes_required ⊆ principal.scopes`; any-of only where a tool declares it (none in P0).
- **Profiles and client trust.** `app/mcp/connector_shared/profiles.yaml` is owned by core (its §5.4); the AS reads it at consent to set `grant.profile` and `client_verified`. Claude and ChatGPT match through allowlisted CIMD `client_id`s; DCR is always `default`. For each allowlisted CIMD client the AS pins the verified document hash in `connector_oauth_clients.pinned_metadata_sha256` (owned by oauth); on a mismatch it downgrades every active grant of that client to `default` and writes `oauth.grant_downgraded`; core reads the stored profile on every call.
- **Audit.** `connector_audit_events` is the single connector audit table, owned by core (its §5.9, created by the foundation migration); `agent_audit_log` is not extended. `event_type` catalogue: `tool.call`, `http.auth_failure`, `oauth.grant_created`, `oauth.grant_superseded`, `oauth.grant_revoked`, `oauth.grant_downgraded`, `oauth.refresh_reuse_detected`, `oauth.registration_created`, `action.confirm`, `action.decline`. Tool-call fields (`tool`, `user_id`, `grant_id`, `args_hmac`, `result_hmac`, `policy_decision`, `pending_action_id`, `binding_terms`) are nullable; exactly one `tool.call` row per tool call. Writers, all through `AuditSink`: core (`tool.call`, `http.auth_failure`), the AS (`oauth.*`), action-path (the `tool.call` row for calls it executes, via `record_required` in the effect's transaction, with `policy_decision`, `pending_action_id`, `binding_terms` filled; `action.confirm` / `action.decline` from its web routes). Joint contract test: every event type inserts exactly one valid row.
- **Action-path tables.** `pending_actions`, `connector_action_requests` and `checkout_handoffs` are owned by action-path (its §4.4); core's `get_activity` reads them owner-filtered.
- **Rollout order.** (0) Connector foundation, owned by core and inert: `connector_shared` package, shared migration, `profiles.yaml` and scope catalogue, interfaces and contract tests, SDK Chunk 0, capacity budget, both Railway services configured with flags off. (1) OAuth AS on `ai-market-connector-auth`, `CONNECTOR_OAUTH_ENABLED=false`. (2) Connector server on `ai-market-connector`, `CONNECTOR_ENABLED=false`. (3) Both enabled together. (4) Action-path writes enabled only after (3); its migration and flag-off code may land any time after (0). Core §9 is the authoritative step list.
- **Rollback.** Turning the AS off (`CONNECTOR_OAUTH_ENABLED=false`) stops new authorizations and refreshes only; access tokens already issued (≤ 1 h) keep verifying locally: the public JWKS route stays served when that flag is off (metadata does not), and the verifier keeps its last successfully fetched key set if a refresh fails (with an alert), failing closed only when it has never fetched one (e.g. first start while the auth service is down). Live access is cut by the connector kill switch (`CONNECTOR_ENABLED=false`, or the DB global / per-profile / per-tool switches) and by grant revocation, which core checks live on every call. Action-path rolls back by its flags with its tables retained. Tables are never dropped as part of rollback.

## Adopted defaults (controller, 2026-09-23; Max may override)

Q-numbers used in the body of this spec refer to the entries below (adopted) or to the open questions that follow.

- **Q1 SDK target** → (a) `mcp>=1.30,<2` now; 2.x in a later BQ.
- **Q2 Which clients get `claude`/`openai`** → (a) only CIMD or pre-registered clients whose grant redirect matches the allowlist; DCR always `default`. Claude and ChatGPT get their profiles through allowlisted CIMD `client_id`s (Claude uses CIMD because the AS advertises `client_id_metadata_document_supported` and `none`); a pinned-hash change downgrades the grant to `default` (R8).
- **Q3 Token verification key** → (a) the oauth BQ issues asymmetric **ES256** connector access tokens with a dedicated key pair held only by the separate AS service `ai-market-connector-auth` (R1; round 1: GLM and DeepSeek mandated the split, Gemini preferred co-location); the connector service holds only the public key (JWKS at `https://auth.ai.market/.well-known/jwks.json`); each service's `SECRET_KEY` is its own random value unused for signing. Refresh tokens are opaque, rotating, strict reuse → revoke grant.
- **Issuer (shared, R1)** → `https://auth.ai.market`, served by Railway service `ai-market-connector-auth`; `connect.ai.market` serves only the MCP resource and its PRM.
- **Audience (shared, R2)** → `aud = https://connect.ai.market/mcp`, the single canonical resource; no alias URL, no normalisation; the profile comes only from the grant (supersedes the draft's oauth Q4a).
- **Q4 Anonymous discovery** → (a) every MCP method requires auth.
- **Q5 Audit retention before legal sign-off** → (a) keep everything until sign-off, then apply the matrix (rule below).
- **Q6 Edge protection** → (a) stay DNS-only for P0; app limits and Railway.
- **Q7 Kill-switch control surface** → (a) runbook SQL + internal-key endpoint.
- **Audit table (shared)** → `connector_audit_events` is the single connector audit table, owned here; action-path fills `policy_decision`, `pending_action_id`, `binding_terms` instead of extending `agent_audit_log`. Rows are typed by `event_type` (R4, §5.9).
- **Scope semantics (shared, R3)** → all-of: `scopes_required ⊆ principal.scopes`; any-of only when a tool declares it (none in P0).
- **Deploy order (shared, R5)** → connector foundation → OAUTH AS (flags off) → connector server (flag off) → enable together (§9).
- **Users without an organisation (shared).** A personal grant with `org_id = NULL` is allowed. Live check: if `grant.org_id` is set, an active membership in that org is required; if NULL, the user must have no active membership (else 401, reconnect). Reads filter by `user_id` and, when set, `org_id`; org-keyed rate limits fall back to the user id when `org_id` is NULL.
- **Audit retention (shared by all three connector specs; core Q5a).** Keep every `connector_audit_events` row until legal sign-off, then apply the retention matrix; no purge path ships before sign-off.

## 11. Open questions for Max

None open. - **Q8 decided by Max (2026-09-23): (a).** Early access is a user allowlist (test accounts and Max) until the P1 buyer-tools BQ ships.

## 12. The hard part

Not the MCP plumbing — it is making "which toolset does this caller get" impossible to argue with. The profile must come from something the caller cannot choose (the verified registration and the redirect the code was delivered to), survive the messy reality of how each vendor registers (CIMD for some, DCR for others, loopback for desktop tools, vendors changing callbacks without notice), and still fail safe to the least-privileged set rather than to an error that blocks real customers. Get it too loose and ChatGPT sees purchase tools OpenAI forbids, which costs the listing; too tight and Claude users get the narrow set, which costs the product. The second hard thing is the SDK upgrade: it looks like a version bump, but mcp 1.30's default Host check would silently take the live AIM Discovery endpoint to 421 while every build and health check stays green, and `aim-node`'s unbounded pin means the 2.x rename can break customers' installs independently of anything we deploy.
