# BQ-AGENT-API-OAUTH-ACCESS-S1738 — Gate 1 design

**Status:** Proposed Gate 1 design; no Council approval, implementation, merge, or deployment is asserted.

**Plain-English summary for Max:** The Agent API currently asks callers for an agent key that
customers cannot create, and its own OAuth quick start produces a token the purchase handlers will
not accept. Let credentialed agents use one OAuth bearer or an existing agent key, and move the
existing spending and audit controls onto the OAuth client. Keep
purchases closed until those controls and the test-environment money path pass.

**Authority:** Max's 2026-09-25 decision, Event Ledger 75245973 item 1A, authorizes admission
with the documented OAuth `client_credentials` bearer alongside the existing agent key. It does
not authorize anonymous (no-credential) catalogue access. This authoring request permits a Gate 1
proposal in runbooks, not backend work or public enablement.

**Source identity:** `aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658`
(pinned source tree for this review). All `repo@sha:path:line` citations below use this
immutable tree; its historical `origin/main` position and deployed SHA are not independently
verified here. Runbooks base:
`aidotmarket/runbooks@b7009e89575ec0cef6b0c5e9c1a19b28848ee43a`.

## 1. Problem and evidence

1. The application installs `AgentAuthMiddleware` over `/api/v1/agent`. Its existing public
   exceptions are `/api/v1/agent/openapi.json`, `/api/v1/agent/llms.txt`,
   `/api/v1/agent/sse` and `/api/v1/agent/tools/call`; the latter two are existing public MCP
   transport/tool routes with their own controls. Protected search, details, eval, wallet,
   purchase, order and delivery paths first need `X-API-Key`; absent headers receive 401
   `x-api-key header is required`.
   [aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/main.py:795-814;
   aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/middleware/agent_auth.py:21-30,80-108]
2. The key service looks up an eight-character prefix and SHA-256 key hash in `agent_api_keys`,
   checks active/revoked/suspended status, and returns scopes, spend cap/used and requests per
   minute. Its spend check locks the key row.
   [aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/services/agent_auth_service.py:18-42,60-105,112-155]
3. The table was introduced in agent-beta M2, commit `c523416432a5b00630a287b04f205bd099a1bf12` on
   2026-03-23. The current tree's `app/` and `scripts/` contain no `INSERT INTO agent_api_keys` or
   `AgentApiKey(` creator; test fixtures insert rows. This is a source search, not a claim about
   production row count.
   [aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:alembic/versions/20260323_004_agent_api_keys.py:17-36;
   aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:tests/test_canonical_checkout_synthetic_s1734.py:1026,1080]
4. The Agent API describes `POST /api/v1/oauth/token` with `client_credentials`, then Bearer.
   Self-service `POST /oauth/clients` creates user-owned clients. The token endpoint delegates
   non-AIM requests to the confidential client-credentials handler, which only supports that
   grant. Its returned JWT has `type=agent` and `aud=agent`.
   [aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/api/v1/agent/router.py:296-312;
   aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/api/v1/endpoints/oauth_clients.py:189-212,130-182;
   aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/api/v1/endpoints/oauth.py:381-399;
   aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/services/oauth_client_service.py:162-181]
5. Paid Agent API handlers independently resolve a user from an OAuth bearer by calling
   `OAuthService.verify_access_token`, which accepts `type=oauth_access` and `aud=oauth_agent`.
   Therefore the documented client-credentials token fails at this second door even if an agent
   key exists. The separate `OAuthService` can mint the accepted token after authorization-code
   exchange, but the mounted non-AIM token endpoint does not route authorization-code or
   refresh-token requests to that service; its description advertises both grants.
   [aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/api/v1/agent/router.py:548-579,717-739;
   aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/services/oauth_service.py:187-269,340-379;
   aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/api/v1/endpoints/oauth.py:356-399]
6. A live unauthenticated `GET https://api.ai.market/api/v1/agent/search?q=test` returned HTTP 401
   and `{"detail":"x-api-key header is required"}` on 2026-09-25. This confirms the
   customer-facing symptom, not the deployment SHA or any authenticated flow.
7. Existing `transactions.api_key_id` is a nullable FK to `agent_api_keys`. Agent checkout,
   idempotency, reconciliation, spend rollback and licence acceptance currently rely on that key
   identity. The Agent API's wallet purchase paths instead call `AgentService.execute_purchase`
   with a user ID and OAuth-derived licence credential; they do not pass the key into that
   service. Opening admission without a shared paid-path check would create a spending-control
   gap. [aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/models/transaction.py:139-163;
   aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/services/transaction_service.py:330-429,918-975;
   aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/api/v1/agent/router.py:582-604,703-739,795-860]
8. The current wallet path enforces a synthetic buyer/seller pair guard before charging. That
   guard and the S1735 licence constructor/issuance checks are part of the money boundary.
   [aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/services/agent_service.py:482-515,581-604;
   aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/api/v1/agent/router.py:932-964,1080-1100,1143-1163]

## 2. Binding decision

**Admit an OAuth bearer alone for protected Agent API routes once the flag is enabled.** Do not
issue an invisible agent key for each OAuth client, and do not require two independent secrets. A
single server-resolved `AgentActor` carries user, client, organization, scopes, policy and
credential identity through every protected route and service. Search, details and eval require
this actor; no-credential requests to them are denied under either flag state.

The standard self-service flow is: the account owner creates an OAuth client, requests an
agent-scoped `client_credentials` token from `/api/v1/oauth/token`, and sends `Authorization:
Bearer <token>`. Under this flag, only an explicitly agent-enabled client can receive a token with
the canonical Agent API type `oauth_access` and audience `oauth_agent`; this token remains bound
to its owner and client. Existing `type=agent/aud=agent` tokens remain outside the Agent API and
are not silently broadened. The endpoint documentation, examples, token response and handler must
describe the same grant and token contract.

The authorization-code and refresh descriptions are currently ahead of the mounted implementation.
Gate 2 must reconcile them: either implement and test those grants for approved delegated clients
with consent and identical actor controls, or remove their claims from the Agent API documentation
and mark delegation unavailable in this release. They must not be treated as a working fallback
for this launch.

**One client, one bounded money policy.** Add a persistent, server-owned
`agent_oauth_client_policy` keyed by the OAuth client ID (or a reviewed equivalent relation), with
owner user, bound organization, approved scopes, spend cap and used cents, requests-per-minute
limit, suspension/revocation state and timestamps. Creation defaults to zero spend and no paid
scope. A documented authenticated control path must let an authorized owner configure or request a
bounded spend cap before purchase; administrative ceilings and authorization are server-enforced.
The policy is not synthesized from the JWT. The client, user, organization and policy are re-read
for paid operations, so revocation and budget changes take effect during token lifetime.

Legacy `agent_api_keys` remain valid under the old path during migration. Source search implies
production rows are expected to be zero: M2 deliberately key-gated the Agent Beta, provides no
issuance path, and only tests insert keys. This is a hypothesis, not a production count. Gate 2
must read the production row count without exposing keys or owner data before rollout. If nonzero,
pause enablement, measure active use through privacy-safe counts and route traces, preserve the
legacy path, and return a concrete caller migration/compatibility plan for review before enabling
the flag. No automatic key retirement or backfill is assumed.

**Exactly one credential is selected per request.** With the flag on, a syntactically valid OAuth
bearer selects the OAuth actor; `X-API-Key`, if also sent, is ignored entirely for authorization,
charging and records. A malformed/invalid bearer never falls back to a key. Without a bearer, a
key-only request takes the unchanged legacy path. With the flag off, the current key middleware
and route dependencies remain authoritative, including any route's existing independent OAuth
check. Ignoring an extra key under flag on lets a caller remove a stale header without changing
OAuth authority; selecting only the bearer prevents the extra credential from increasing scope,
RPM or spend cap. The selected policy alone owns reservation and release.

### 2.1 Route classification

| Exact route and method | Flag-on admission | Constraint |
| --- | --- | --- |
| `GET /api/v1/agent/openapi.json`, `GET /api/v1/agent/llms.txt` | Anonymous | Public metadata only; no secrets or private schemas. |
| `GET /api/v1/agent/search`, `GET /api/v1/agent/datasets/{id}`, `GET /api/v1/agent/datasets/{id}/eval` | OAuth bearer or existing agent key | Protected catalogue routes; deny requests without either credential. Preserve route-specific scope and disclosure checks. |
| `GET /api/v1/agent/datasets/{id}/preview` | OAuth `market.read` or existing agent key | Real sample rows require a separate privacy check and seller preview eligibility. |
| `GET /api/v1/agent/listings/{id}/synthetic_preview` | OAuth `market.read` or existing agent key | Generation is costly; preserve synthetic labelling. |
| `GET /api/v1/agent/wallet/balance`, `POST /api/v1/agent/wallet/deposit` | OAuth wallet scope or existing agent key | No balance response without a credential; deposit still requires user authority and Stripe controls. |
| `POST /api/v1/agent/purchase`, `POST /api/v1/agent/orders/instant` | OAuth `market.purchase` and paid policy, or existing agent key | Same spend reservation, licence, seller, funds and synthetic guards. |
| `GET /api/v1/agent/orders`, `GET /api/v1/agent/orders/{id}/data`, `POST /api/v1/agent/orders/{id}/request_access`, `GET /api/v1/agent/orders/{id}/artifact` | OAuth owner and scope, or existing agent key | No order enumeration or access by another user/client/organization; licence gate before issuance. |
| `GET /api/v1/agent/sse`, `POST /api/v1/agent/tools/call` | Existing public MCP admission | Retain existing transport/tool policy and rate controls; this flag does not extend their authority. |
| Other routes mounted at `/api/v1/agent/*` | Current authorization until inventoried | No wildcard public exemption; explicit route-table review and separate approval. |

Anonymous catalogue discovery is deferred to separate scope (§10). Existing public root discovery
paths retain their own policy. Exact
method and routed ASGI path determine admission; a matching text prefix cannot open a sibling
route. Gate 2 must test each route and method, including the four exceptions above, under flag
off, flag on and rollback. Today's middleware uses public *prefixes*; implementation must replace
that ambiguity with exact routed-path classification while preserving each exception's policy.

### 2.2 Principal and credential binding

1. Verify JWT signature, configured algorithm, expiry, `aud=oauth_agent`, `type=oauth_access`,
   issuer if present, and UUID subject. Require a nonempty `client_id` and only grants explicitly
   allowed for that client. Reject ordinary user `type=access`, AIM Data session tokens, legacy
   `type=agent/aud=agent`, refresh tokens, wrong-audience tokens and malformed bearer syntax.
2. Re-read the client and policy. Require active client, active owner, matching owner/subject,
   approved grant, bound organization and non-suspended policy. Check organization
   membership/authority on every paid action, not only at client creation. A removed member,
   deactivated client, regenerated secret or revoked grant cannot keep buying with a
   still-unexpired JWT.
   Client registration, revocation and secret rotation must require a verified interactive user
   token of the right type and audience. The current management dependency checks a decoded
   token's subject without checking its type, so an agent bearer must not become a client-management
   credential. [aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/api/v1/endpoints/oauth_clients.py:94-123]
3. The actor exposes `auth_kind=oauth_client`, stable client ID, user ID, organization ID,
   effective scopes and policy ID. Legacy actors expose `auth_kind=agent_key`, key ID and the same
   principal fields. No untrusted request field may set actor identity, cap or organization.
4. Effective permissions are the intersection of token scopes, current client grants, policy
   scopes and route scope. The self-service `read write` default is not interpreted as
   `market.purchase`; no wildcard scope is granted by client creation. Wallet and purchase
   handlers must enforce scopes themselves, not rely on their OpenAPI prose.
5. Existing licence acceptance `principal_ref` remains the authenticated buyer user or legal
   organization. `credential_id` is a namespaced, stable `oauth_client:<id>` or `agent_key:<id>`,
   not a bearer token, JWT `jti`, secret or caller-supplied ID. The order, acceptance, transaction
   and audit row agree on principal and credential. S1735's immutable document hash, signer
   authority, active acceptance and issuance gates remain in force.
6. Request actor resolution follows the single-credential matrix below. An ignored header cannot
   supply a principal, scope, rate budget, cap, transaction link or audit identity. Any downstream
   dependency still reading both credentials must be migrated to the selected actor before
   flag-on admission; otherwise the route stays closed.

| Flag | Headers on a protected request | Admission and principal | Scope and RPM | Reservation, transaction linkage, audit, idempotency and release |
| --- | --- | --- | --- | --- |
| Off | OAuth only | 401 at key gate; no actor. | None. | None. |
| Off | Key only | Valid key enters today's route; existing downstream bearer requirements still apply. Key principal. | Existing key scope and in-process key RPM. | Existing key spend behavior, `api_key_id`, key audit/idempotency/release; no OAuth charge or new linkage. |
| Off | Both | Today's key gate and route dependencies apply; no new OAuth admission. Key is the middleware actor. | Existing key scope and in-process key RPM; any route's existing bearer check remains. | Existing key spend behavior/linkage and route behavior; no new OAuth policy reservation. |
| Off | Neither | 401 at key gate; no actor. | None. | None. |
| On | OAuth only | Valid agent bearer admits. OAuth client, owner and bound organization are the actor. | Intersection of token/client/policy/route scopes; shared client RPM. | One OAuth policy reservation when paid; `oauth_client_id` only; OAuth audit, namespaced idempotency and one release. |
| On | Key only | Today's valid-key path and downstream requirements. Key principal. | Existing key scope and in-process key RPM. | Existing key spend behavior, `api_key_id`, key audit/idempotency/release; no OAuth charge. |
| On | Both | Valid agent bearer admits; key ignored even if invalid or mismatched. Invalid bearer denies without fallback. OAuth principal only. | OAuth intersection and shared client RPM only. | One OAuth policy reservation when paid; `oauth_client_id` only; OAuth audit, namespaced idempotency and one release; no key charge/link. |
| On | Neither | Denied; no actor. | None. | None. |

For every selected OAuth request, the OAuth client's current owner/organization and policy own
scope, shared RPM counter, spend reservation, `transactions.oauth_client_id` (and no
`api_key_id`), namespaced licence credential, audit identity, idempotency namespace and exactly
one release. For every selected key request, the existing key principal/scope, in-process key RPM,
key spend behavior, `transactions.api_key_id` (and no `oauth_client_id`), audit identity,
idempotency and release remain exactly as today. A denied request creates no reservation or
transaction. The four existing public exceptions use their route-specific policy, not this
protected-credential matrix. Search, details and eval follow the matrix and deny neither-header
requests.

### 2.3 Spend, checkout and records

1. Introduce one paid-operation guard called from both wallet purchase routes and canonical
   `TransactionService` agent checkout. It validates the actor, route scope, organization, seller
   state, S1735 acceptance intent, synthetic-pair guard and policy cap before any wallet debit,
   Stripe session, order, transaction or access grant.
2. Reserve the maximum priced cents under a row lock on the policy with the idempotency key and
   actor credential. A retry for the same actor and request returns the existing result without a
   second reservation; another actor cannot reuse that key. Charge, reserve, order, acceptance and
   transaction must commit or compensate together according to the approved payment state machine.
   Refund/cancel/reconcile releases only the reserved amount once, with an audit event.
   Concurrency tests must prove no cap overshoot.
3. The cap is a client limit, in addition to wallet balance, user daily/monthly limits and any
   organization ceiling. No missing/zero policy is treated as unlimited; zero cap denies paid
   actions. Configure integer cents, nonnegative bounds and a deliberate owner/admin update rule.
   Rate limit and spend cap failures are distinct 429/403 outcomes.
   Every OAuth-admitted protected request, including reads and rejected paid attempts after
   admission, must consume the selected client's `rate_limit_rpm` budget before route work. Use a
   shared Redis sliding-window counter keyed by OAuth client ID, building on
   `app.core.redis_cache.redis_rate_limit_check_strict`. Its pipeline uses
   `transaction=True` (Redis MULTI/EXEC) for the count and increment
   [aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/core/redis_cache.py:319-327].
   Gate 2 validates cross-replica client keying and fail-closed behavior; no atomicity rewrite is
   presumed. A missing/nonpositive RPM policy denies protected OAuth admission. An unavailable
   shared limiter returns 503 before route work, because an outage is not a client quota violation;
   over-limit returns 429 with positive `Retry-After`. Scope denial and spend-cap denial retain
   separate reasons/statuses. Legacy key RPM keeps today's in-process policy.
   Client/policy suspension and revocation must deny protected OAuth requests within 5 seconds
   across replicas, including already-issued tokens; paid operations re-read authoritative state
   immediately before reservation/charge.
4. Extend transactions with nullable `oauth_client_id` referencing the OAuth client, while
   retaining `api_key_id` for historical and legacy transactions. New agent transactions require
   exactly one credential FK, with a validated ownership snapshot. Do not create a dummy
   `agent_api_keys` row to satisfy the FK. Adjust idempotency, reconciliation, refund and download
   ownership checks to use the tagged credential and original principal.
5. Extend `agent_audit_log` with the OAuth client reference and actor kind, retaining historical
   key references. Write acceptance, cap denial, reservation, purchase result, reconciliation and
   issuance events with correlation ID, user, organization, client or key,
   transaction/order/listing IDs and decision. Avoid raw tokens, secrets, licence text and private
   sample contents in logs.
6. Treat existing `agent_api_keys` spend and revocation behavior as the compatibility baseline,
   not proof that Agent API wallet purchases currently enforce it. Gate 2 must show call-path
   evidence for both purchase endpoints and the canonical transaction path, including failure
   before payment side effects.

### 2.4 Existing public exceptions and abuse controls

The only no-credential routes in this Agent API scope are the four existing exceptions in §2.1.
The inherited limiter currently **fails open** when Redis has no client or raises an error
[aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/middleware/rate_limiter.py:90-99,163-169].
The existing SSE and tool-call handlers use that limiter
[aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/routers/mcp_sse.py:375-425].
Gate 2 must resolve this outage behavior before the production cohort:

| Existing public route | Redis unavailable decision |
| --- | --- |
| `GET /api/v1/agent/openapi.json` | Accepted fail-open exception: static, cacheable metadata with no DB or model work. Preserve cacheability and verify no dynamic work is introduced. |
| `GET /api/v1/agent/llms.txt` | Accepted fail-open exception: static, cacheable metadata with no DB or model work. Preserve cacheability and verify no dynamic work is introduced. |
| `GET /api/v1/agent/sse` | Must not become unbounded: return 503 while the limiter is unavailable, or use a demonstrated bounded per-replica fallback with connection/concurrency ceilings. |
| `POST /api/v1/agent/tools/call` | Must not become unbounded: return 503 before tool work, or use a demonstrated bounded per-replica fallback with request/work ceilings. |

The two metadata exceptions are accepted only while their static, cacheable, no-DB/no-model
properties hold. Gate 2 must record the outcome of each route with Redis unavailable across at
least two replicas and reject an unbounded SSE or tool-call result. This flag grants those routes
no new authority. `X-Sandbox-Mode` cannot authorize a synthetic actor or bypass a money guard;
existing synthetic-pair purchase controls must be exercised with the flag on and off.

## 3. Alternatives rejected

| Alternative | Reason rejected for this gate |
| --- | --- |
| Keep agent key plus OAuth bearer on all routes | Customers cannot obtain the first credential through a product flow; the documented token still has the wrong type/audience. |
| Automatically issue an agent key for each OAuth client | Creates a second long-lived secret and ambiguous revocation, spend and audit identities; hides the missing policy model. |
| Accept either a key or any bearer without actor reconciliation | Key-only cannot supply the current buyer principal; generic user JWTs or mixed credentials could become a confused-deputy path. |
| Make all `/agent/*` routes public | Exposes wallet, purchase, samples, order history and delivery; no anonymous expansion is authorized in this gate. |
| Put a fixed cap in a self-contained JWT | A revoked client or lowered cap would remain spendable until expiry; concurrent purchases can exceed an unsigned balance. |
| Remove caps until after launch | Opens a real money path while removing its key-based safeguard and audit identity. |

## 4. Risks and required security review

1. **Token confusion:** reviewers must trace every JWT issuer and verifier that can reach
   `/agent/*`; audience and type checks are both mandatory. Preserve separate AIM Data and
   ordinary user-token audiences. Include negative tests for cross-service tokens and algorithm
   confusion.
2. **Owner/organization confusion:** client credentials act for the owner only under a documented,
   revocable delegation; a client ID cannot impersonate another user or organization. If
   organization authority cannot be verified reliably, paid OAuth access stays closed.
3. **Revocation lag:** a valid signature alone is insufficient. Client, grant and policy status
   must be checked on every protected call or through a proven invalidation cache with a bounded
   revocation SLA. Secret rotation must invalidate outstanding agent access or use an explicit
   token epoch.
4. **Payment races:** simultaneous wallet/Stripe attempts, retries, webhooks, refunds and cap
   updates must not double reserve or double release. Preserve canonical checkout and
   transaction-state idempotency; do not add a parallel charge constructor.
5. **Public exception cost:** Redis outage behavior for SSE and tool calls, route bounds and load
   tests are release blockers. Search, details, eval, synthetic preview and real sample rows
   remain credential-protected at this gate.
6. **CSRF:** bearer tokens in an `Authorization` header are not ambient browser credentials, so
   CSRF is not the Agent API admission control. Authorization-code consent pages, if implemented,
   still need state/redirect/PKCE and ordinary browser-session CSRF review.
7. **Schema transition:** new nullable OAuth references must not rewrite historical key-linked
   transactions or audit rows. Migration and rollback must preserve both identities and all legal
   acceptance records.
8. **Compatibility:** key-only use keeps today's behavior under either flag setting. When both
   headers are present under flag on, only OAuth has authority; the extra key never widens it.
   Verify the production key-row count read-only and resolve any nonzero active use before
   enablement. No key revocation is authorized by this spec.

## 5. Acceptance criteria

- **AC1 — route policy:** a generated FastAPI route inventory lists every method under
  `/api/v1/agent`, including mounted tool/SSE routes, with exact anonymous/protected treatment.
  Flag off and on both deny no-credential search, details and eval; flag on admits an eligible
  OAuth bearer or existing agent key to those protected routes, subject to route policy. Exact-path
  classification tests cover search, details, eval, OpenAPI, llms.txt, SSE and tools/call with
  flag off, on and rolled back, preserving the four existing exceptions' separate policies.
- **AC2 — one credential:** an eligible self-service OAuth client can obtain the documented agent
  bearer and call protected routes without `X-API-Key`. The response, decoded claims and handler
  agree on type, audience, subject, client and scopes. A client-credentials request does not
  silently grant authorization-code delegation.
- **AC3 — negative auth:** absent/invalid/expired/wrong-audience/user/AIM Data/refresh bearer,
  inactive owner, revoked client, suspended policy and removed organization membership cannot
  access protected data or purchase. A bad bearer with a valid key cannot fall back. Under flag
  on an extra mismatched or invalid key is ignored; the bearer receives only its own policy.
  Suspension/revocation is effective for existing tokens across replicas within 5 seconds and
  is re-read immediately before charge.
- **AC4 — scopes:** `market.read`, wallet and `market.purchase` are separately enforced; read-only
  clients cannot deposit, buy or issue delivery. No default `read write` string implies
  `market.purchase`.
- **AC5 — money guard:** both `/purchase` and `/orders/instant`, plus canonical agent checkout,
  deny above-cap attempts before debit/Stripe side effect. Parallel requests cannot exceed cap;
  retries do not double reserve; failed/cancelled/refunded attempts release exactly once. Wallet
  and organization ceilings still apply. PostgreSQL integration proves one selected credential
  and one reservation/linkage for OAuth-only, key-only and both-header calls, concurrent purchases,
  retry/idempotency, revocation between reservation and charge, process failure and refund; each
  reservation releases exactly once and transaction/order/acceptance/audit identities agree.
  Under flag on, a valid key alongside a valid OAuth bearer with zero paid cap cannot subsidize
  the OAuth actor: deny with a clear OAuth policy/cap error code and no key reservation.
- **AC6 — legal binding:** S1735 acceptance records the exact licence hash, buyer legal principal,
  authority and namespaced OAuth client or legacy key ID in the same order/transaction path.
  Missing or stale acceptance creates no charge or credential. Every download, request-access and
  artifact door refuses absent or terminated acceptance.
- **AC7 — synthetic isolation:** an unarmed synthetic buyer/seller pair cannot purchase under
  either flag setting; a permitted S1656 test run uses its explicit E2E guard and cannot cross
  into real funds or real customer identities.
- **AC8 — records:** OAuth transactions carry `oauth_client_id` and no fake key ID; legacy rows
  retain `api_key_id`. Audit and reconciliation can trace either to the same principal and
  idempotency key, with no credential secret logged.
- **AC9 — public exception outage:** with Redis unavailable across at least two replicas,
  record each of the four inherited public routes' outcomes. OpenAPI and llms.txt may remain
  available under the accepted static/cacheable/no-DB/no-model exception. SSE and tools/call
  return 503 or stay within a measured per-replica fallback bound; neither is unbounded.
- **AC10 — compatibility and operations:** key-only requests retain today's full behavior with
  flag off, on and rolled back. The both-header matrix is tested for valid, invalid and
  mismatched credentials with zero/nonzero OAuth policies. The read-only production key-row count
  and any required migration plan are recorded before rollout. An operator can disable the flag
  without losing accepted orders, reservations or audit evidence.
- **AC11 — protected OAuth RPM:** every protected OAuth request uses the client's positive RPM
  policy and an atomic shared Redis counter. After RPM valid calls in one minute, request RPM+1
  returns 429 with positive `Retry-After`; a second replica sees the same counter. Counter outage
  returns 503 before route work on both replicas, distinct from quota, scope and cap denials.
  Suspension/revocation denies on both replicas within 5 seconds.

## 6. Test plan and evidence gates

1. **Gate 2 static contract:** freeze the generated route table, actor schema, OAuth token claims,
   client-policy schema, migration, cap state machine and exact flag precedence. Map each paid
   path to the shared guard and each delivery path to its owner and active-licence check. Include
   an explicit decision on authorization-code/refresh support.
2. **Auth integration:** construct real signed tokens for each type/audience/grant, exercise the
   actual middleware and route dependency together, create/revoke/rotate a client, change
   owner/organization authority during token lifetime, and test all eight flag/header matrix
   cases including both-header mismatch and invalid/zero policies. Assert that a valid key does
   not fund an OAuth bearer with zero paid cap and that the denial identifies the OAuth policy.
   Test RPM+1, cross-replica keying, `Retry-After`, 503 limiter outage and the 5-second
   revocation SLA. Mocking `verify_access_token` alone is insufficient.
3. **Money integration:** use PostgreSQL row locks and concurrent tasks to test cap boundaries,
   idempotent retries, wallet debit failure, Stripe session failure, webhook replay, refund and
   reconciliation. Include revocation between reservation and charge, process failure and both
   headers under flag off/on; verify only the selected credential's ledger changes and every
   release happens exactly once. Assert persisted totals and no orphan order, transaction,
   acceptance or audit entry after failure.
4. **Legal and synthetic integration:** exercise both Agent API purchase routes and the canonical
   checkout with S1735 on, a published listing, exact acceptance hashes and guarded synthetic
   pairs. Inspect records and every access door after licence termination.
5. **Public surface/load:** with Redis unavailable across two replicas, test and record each of
   OpenAPI, llms.txt, SSE and tools/call against §2.4 and AC9. Prove static metadata exceptions
   remain cacheable with no DB/model work; prove SSE and tool calls return 503 or remain within
   measured per-replica limits. Test protected search/details/eval denial without credentials,
   their route bounds with a valid actor, and exact method/path matching.
6. **S1656 test environment:** obtain an ordinary self-service test client and token through
   product routes; perform an OAuth-only purchase and delivery flow through the canonical test
   money path with the environment's armed synthetic guard. Prove cap denial and revoked-client
   denial without manual `agent_api_keys` insertion. Capture request IDs, backend/deployment SHA,
   order/transaction/acceptance IDs and scrubbed audit evidence.
7. **After authorized deploy:** independently record deployed SHA and flag state for every serving
   replica. With flag on, no-credential search/details/eval must deny and an eligible OAuth bearer
   must reach them under route policy; existing public OpenAPI and llms.txt retain their policy.
   In S1656, repeat OAuth-authenticated purchase, spend-cap enforcement and revoked-client refusal.
   Probe protected wallet/order/preview without a credential and with a wrong-audience token;
   require denial. A healthy deploy alone does not satisfy these checks.
8. **Release review:** Council reviews the exact Gate 1 SHA before implementation authority. Later
   implementation, security review, migration proof, S1656 flow, deploy and live checks are
   separate gates; report each with exact candidate and deployment identity.

## 7. Rollout and rollback

1. Add an `AGENT_API_OAUTH_ACCESS_ENABLED` flag defaulting **false** in every environment. With
   false, the current middleware key gate and route behavior remain the operational fallback.
   Schema may land while disabled; no client receives new authority from the migration alone.
   The `oauth_access/oauth_agent` client-credentials token change is gated by this same flag;
   these new tokens must not be issued while it is off.
2. Deploy schema and read compatibility first; verify old key-linked records. Then deploy actor
   resolution and shared paid guard behind the flag. Observe denial, cap, audit and latency
   metrics in S1656 before any production enablement.
3. Enable in S1656 for the full proof, then a bounded production cohort of explicitly eligible
   OAuth clients. Before cohort traffic, record each serving replica's deployed SHA and effective
   flag value; require homogeneous state or keep the cohort closed. Search, details and eval stay
   credential-protected. Record who flipped the flag, timestamp, client cohort, rate/cap settings
   and dashboards.
4. Monitor 401/403/429/503 by route and actor kind, token validation errors, client revocation
   age, cap reservations/releases, duplicate payments, licence denials, public MCP route cost,
   audit-write failures and payment reconciliation. Alert on missing actor or unbounded spend;
   fail paid paths closed if policy or audit persistence is unavailable.
5. Roll back by switching the flag off, restoring key-gated admission. Stop new OAuth-only paid
   admissions; complete or reconcile already-created payment/order states using their stored OAuth
   identity. Do not erase policy, transaction, audit
   or licence records. If a code rollback precedes schema rollback, preserve additive columns
   until all OAuth-origin obligations and access rights are safely handled.
6. Any wider public route, new grant, relaxed cap, or change to licence/synthetic safeguards
   returns to Council as a scope change. Anonymous discovery specifically needs a separate Max
   decision and Council review (§10).

## 8. Open questions for Council

1. Is an owner-bound `client_credentials` grant sufficient for the first release, with delegated
   authorization-code/refresh held until its mounted endpoint and consent checks are repaired? The
   proposal says yes.
2. What maximum self-service cap, minimum limit, reset period and escalation authority apply to a
   new OAuth client? The security default proposed here is zero paid spend until an explicit
   owner-authorized cap is set under a platform ceiling.
3. Which organization membership source is authoritative at purchase time, and can a client be
   bound to more than one organization? The proposal requires one explicit organization per
   policy.
4. What route-specific disclosure limits should credentialed `datasets/{id}/eval` retain? Any
   no-credential projection is outside this gate (§10).
5. What token-epoch behavior should accompany regenerated client secrets? The proposal fixes a
   5-second revocation SLA across replicas and requires immediate database denial on paid calls.
6. Does the read-only production count reveal any real legacy key users who need an explicit
   migration plan? No retirement is proposed now.
7. Should `/wallet/deposit` remain in the Agent API, or redirect the human owner to the existing
   wallet UI? Either option must retain wallet scope, consent and payment controls.

## 9. Scope and handoff

This Gate 1 artifact defines an access and money-control contract. It does not create credentials,
change backend code, mutate production data, approve a Council verdict, merge or deploy. Gate 2
must supply the concrete migration and route-by-route implementation plan against a freshly pinned
backend SHA, with any changed assumptions called out. The runbook index and checker are repository
hygiene checks only: they do not enumerate or validate `specs/` content. A read-only reviewer can
run `python3 scripts/check.py` alone; `scripts/index.py` writes generated index files.

## 10. Deferred, separate scope

No-credential search, `datasets/{id}` details and `datasets/{id}/eval` discovery are outside
`AGENT_API_OAUTH_ACCESS_ENABLED` and this Gate 1 contract. They need their own Max decision and
Council review before any anonymous admission is designed or enabled. That later scope must settle
field projections, query/evaluation cost, shared abuse limits, Redis-outage behavior and a
separate rollout/rollback switch. P3 discoverability alone is not authority to open these routes.

## 11. Round 2 disposition

| Finding | Severity | Raiser | Answering section |
| --- | --- | --- | --- |
| Anonymous discovery exceeds item 1A authority and is coupled to the OAuth flag | MEDIUM | DeepSeek | Authority; §§2.1, 5 AC1, 6, 7.3, 7.6, 10 |
| Limiter outage could unbound inherited public MCP routes | MEDIUM | GLM | §§2.3.3, 2.4, 5 AC9/AC11, 6.2/6.5 |
| Transactional Redis helper was incorrectly called non-atomic | LOW | DeepSeek | §2.3.3 |
| Underlying Event Ledger records remain externally UNVERIFIED | LOW | GLM | Appendix A; immutable export remains a Gate 2 requirement |
| Index/check excludes `specs/`; index writes in read-only worktrees | NIT | GLM; Gemini | §9; Appendix A verification note |
| Mixed replica flag/deploy state before cohort | NIT | GLM | §§6.7, 7.3 |
| Both headers with zero-cap OAuth policy need a clear denial | NIT | Gemini | §§5 AC5, 6.2 |
| Historical `origin/main` claim could not be independently confirmed | NIT | DeepSeek | Source identity |
| Review controller omitted requested repository/branch despite exact artifact identity | NIT | DeepSeek; GLM | Review dispatch metadata; no spec contract change |

## Appendix A. Authority and evidence records

The following is the verbatim **field content supplied for this review**, with full IDs and UTC
timestamps. The Event Ledger's storage path and full serialized records were not available in this
worktree or through the available search result, so fields beyond those shown are not claimed.
The underlying authority records remain externally **UNVERIFIED**. This makes the supplied fields
inspectable here without database access; Gate 2 must attach an immutable ledger export when
available and cannot claim external verification until the exact records are retrieved.

| Event ID | Time and actor | Verbatim supplied fields |
| --- | --- | --- |
| `75245973-7c4e-4425-8e07-5f1fc4139813` | `2026-09-25T07:44:44Z`; `max`; `trust_tier: human` | `title: "Max decisions (S1738, 2026-09-25): Agent API open via OAuth; ClamAV as a dedicated service; test refund via real-Stripe test pair; dispute refund bug fixed now"`<br>`payload.1_agent_api: "A: open /api/v1/agent/* to the standard OAuth client_credentials bearer its own OpenAPI documents (agent-key middleware no longer the only door) (Events 285e48c6, 9e322a2c)"`<br>`source_ref: Max chat 2026-09-25 "I agree with your recommendations"` |
| `285e48c6-7064-4e9c-891a-d84e5272c51e` | `2026-09-24T23:11:55Z`; `mars` | `finding that /api/v1/agent/* requires an agent_api_keys key no product route issues; live GET api.ai.market/api/v1/agent/search -> 401 x-api-key header is required.` |
| `9e322a2c-4423-4657-8a11-251c26729501` | `2026-09-24T23:23:55Z`; `mars` | `correction - the Agent API is the March 2026 Agent Beta (M2, commit c52341643), gated by agent keys by design; no issuance path exists; only tests insert keys.` |

**Review environment and checks.** This Round 2 disposition changes this spec only; it includes
no backend code, migration, deployment or production mutation. `python3 scripts/index.py &&
python3 scripts/check.py` passed here (`indexed 135 runbooks`; `checked 135 runbooks`, exit 0).
That is repository hygiene, not spec-content validation, because those scripts exclude `specs/`.
No backend tests or lint were run for this document change. The live symptom rests on one unauthenticated
GET returning HTTP 401 on 2026-09-25; there was no authenticated flow or deployment-SHA proof.
The minimal reproducible status-only probe is:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' 'https://api.ai.market/api/v1/agent/search?q=test'
```

The historical shell invocation was not retained, so this command reproduces the stated request
rather than claiming to be its original receipt. No second production request is implied.
