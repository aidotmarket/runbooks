# BQ-AGENT-API-OAUTH-ACCESS-S1738 — Gate 1 design

**Status:** Proposed Gate 1 design; no Council approval, implementation, merge, or deployment is asserted.

**Plain-English summary for Max:** The Agent API currently asks callers for an agent key that
customers cannot create, and its own OAuth quick start produces a token the purchase handlers will
not accept. Open catalogue discovery to visitors, let signed-in agents use one OAuth bearer
credential, and move the existing spending and audit controls onto the OAuth client. Keep
purchases closed until those controls and the test-environment money path pass.

**Authority:** Max's 2026-09-25 decision, Event Ledger 75245973, option A: open the Agent API with
the standard OAuth sign-in described in its documentation. This authoring request permits a Gate 1
proposal in runbooks, not backend work or public enablement.

**Source identity:** `aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658`
(fetched `origin/main` on 2026-09-25). All `repo@sha:path:line` citations below use this
immutable tree; source identity does not prove the deployed SHA. Runbooks base:
`aidotmarket/runbooks@b7009e89575ec0cef6b0c5e9c1a19b28848ee43a`.

## 1. Problem and evidence

1. The application installs `AgentAuthMiddleware` over the entire `/api/v1/agent` prefix. Its
   public-prefix list does not include Agent API routes, so every such path first needs
   `X-API-Key`; absent headers receive 401 `x-api-key header is required`.
   [aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/main.py:795-806;
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
credential identity through every route and service. Anonymous catalogue routes admit no actor and
cannot buy, inspect a wallet, see private data or receive delivery credentials.

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

Legacy `agent_api_keys` remain valid under the old path during migration. Existing key-plus-OAuth
callers continue to work only when the two credentials resolve to the same user/organization;
mismatched dual credentials fail closed. After the flag is enabled, a valid OAuth bearer is
sufficient for Agent API routes, and a valid legacy key can accompany it without changing its
effective identity or raising its limits. Never select whichever of two conflicting credentials
grants more authority.

### 2.1 Route classification

| Exact route and method | Flag-on admission | Constraint |
| --- | --- | --- |
| `GET /api/v1/agent/openapi.json`, `GET /api/v1/agent/llms.txt` | Anonymous | Public metadata only; no secrets or private schemas. |
| `GET /api/v1/agent/search`, `GET /api/v1/agent/datasets/{id}`, `GET /api/v1/agent/datasets/{id}/eval` | Anonymous or OAuth | Published, public listing metadata only; fixed field allowlist and anonymous budgets. |
| `GET /api/v1/agent/datasets/{id}/preview` | OAuth, `market.read` | Real sample rows require a separate privacy check and seller preview eligibility. |
| `GET /api/v1/agent/listings/{id}/synthetic_preview` | OAuth, `market.read` | Generation is costly and must not become an anonymous work queue; preserve synthetic labelling. |
| `GET /api/v1/agent/wallet/balance`, `POST /api/v1/agent/wallet/deposit` | OAuth, wallet scope | No anonymous zero-balance response; deposit still requires user authority and Stripe controls. |
| `POST /api/v1/agent/purchase`, `POST /api/v1/agent/orders/instant` | OAuth, `market.purchase`, paid policy | Same spend reservation, licence, seller, funds and synthetic guards. |
| `GET /api/v1/agent/orders`, `GET /api/v1/agent/orders/{id}/data`, `POST /api/v1/agent/orders/{id}/request_access`, `GET /api/v1/agent/orders/{id}/artifact` | OAuth, owner and scope | No order enumeration or access by another user/client/organization; licence gate before issuance. |
| Other routes mounted at `/api/v1/agent/*`, including tool and SSE routers | Current authorization until inventoried | No wildcard public exemption; explicit route-table review and separate approval. |

The three anonymous catalogue routes serve the P3 discoverability goal without allowing sample
bytes or economic actions. They may require a public projection rather than exposing current
service output directly. Existing public root discovery paths retain their own policy. Exact
method and routed ASGI path determine admission; a matching text prefix cannot open a sibling
route.

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
6. A request with both bearer and key must validate both. Require their user and organization
   binding to agree and use the more restrictive applicable scope and cap, reserving against both ledgers atomically if both
   are presented for a paid action. Reject a revoked or
   suspended presented key rather than ignoring it. No fallback from a bad bearer to a valid key,
   or from a bad key to a valid bearer.

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

### 2.4 Anonymous discovery and abuse controls

1. Public search/details/eval return only published listing projections that are already approved
   for public disclosure. Evaluate each response field, including schema, statistics, compliance
   claims, seller fields and price, against P3 public-discovery rules. Never surface owner notes,
   credentials, private URLs, raw data or unapproved scan results.
2. Apply a shared, bounded edge or Redis-backed limit by trusted resolved client IP, route and
   abuse signal; local process memory alone does not coordinate replicas. Set explicit burst and
   minute ceilings in Gate 2, with `Retry-After`, metrics and a quick disable switch. Use the
   backend's canonical trusted-IP resolver.
3. Bound query length, `limit`, result work, evaluation cost and pagination. Avoid unbounded
   fan-out and cache stampedes. Anonymous responses may be cached briefly only when the projection
   is public and seller changes invalidate or expire safely; private bearer responses are
   `no-store`.
4. The `X-Sandbox-Mode` header cannot authorize a public synthetic actor or bypass a money guard.
   Do not expose mock or test-only listings through anonymous discovery in production. Existing
   synthetic-pair purchase controls must be exercised with flag on and off.

## 3. Alternatives rejected

| Alternative | Reason rejected for this gate |
| --- | --- |
| Keep agent key plus OAuth bearer on all routes | Customers cannot obtain the first credential through a product flow; the documented token still has the wrong type/audience. |
| Automatically issue an agent key for each OAuth client | Creates a second long-lived secret and ambiguous revocation, spend and audit identities; hides the missing policy model. |
| Accept either a key or any bearer without actor reconciliation | Key-only cannot supply the current buyer principal; generic user JWTs or mixed credentials could become a confused-deputy path. |
| Make all `/agent/*` routes public | Exposes wallet, purchase, samples, order history and delivery; P3 only needs bounded catalogue discovery. |
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
5. **Public discovery leaks and cost:** field-level allowlists, rate limits and load tests are
   release blockers. Synthetic preview and real sample rows remain private at this gate.
6. **CSRF:** bearer tokens in an `Authorization` header are not ambient browser credentials, so
   CSRF is not the Agent API admission control. Authorization-code consent pages, if implemented,
   still need state/redirect/PKCE and ordinary browser-session CSRF review.
7. **Schema transition:** new nullable OAuth references must not rewrite historical key-linked
   transactions or audit rows. Migration and rollback must preserve both identities and all legal
   acceptance records.
8. **Compatibility:** any existing key use must keep working under the flag only with matching
   OAuth principal; report observed key users via privacy-safe counts before enforcing a
   retirement schedule. No key revocation is authorized by this spec.

## 5. Acceptance criteria

- **AC1 — route policy:** a generated FastAPI route inventory lists every method under
  `/api/v1/agent`, including mounted tool/SSE routes, with exact anonymous/protected treatment.
  Flag off reproduces current 401 for unauthenticated search; flag on returns 200 for a valid
  anonymous `q=test` search and public OpenAPI/eval, without exposing private fields.
- **AC2 — one credential:** an eligible self-service OAuth client can obtain the documented agent
  bearer and call protected routes without `X-API-Key`. The response, decoded claims and handler
  agree on type, audience, subject, client and scopes. A client-credentials request does not
  silently grant authorization-code delegation.
- **AC3 — negative auth:** absent/invalid/expired/wrong-audience/user/AIM Data/refresh bearer,
  inactive owner, revoked client, suspended policy, removed organization membership and mismatched
  dual credentials cannot access protected data or purchase. Revocation is effective for an
  existing token within the stated SLA.
- **AC4 — scopes:** `market.read`, wallet and `market.purchase` are separately enforced; read-only
  clients cannot deposit, buy or issue delivery. No default `read write` string implies
  `market.purchase`.
- **AC5 — money guard:** both `/purchase` and `/orders/instant`, plus canonical agent checkout,
  deny above-cap attempts before debit/Stripe side effect. Parallel requests cannot exceed cap;
  retries do not double reserve; failed/cancelled/refunded attempts release exactly once. Wallet
  and organization ceilings still apply.
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
- **AC9 — discovery safety:** anonymous limits apply across replicas; abusive queries get 429;
  only public published metadata is returned; preview, wallet, orders and delivery remain
  inaccessible without the correct actor.
- **AC10 — compatibility and operations:** legacy key-plus-matching-OAuth requests retain their
  prior permitted behavior, and an operator can disable the flag to restore the current closed
  state without losing accepted orders, reservations or audit evidence.

## 6. Test plan and evidence gates

1. **Gate 2 static contract:** freeze the generated route table, actor schema, OAuth token claims,
   client-policy schema, migration, cap state machine and exact flag precedence. Map each paid
   path to the shared guard and each delivery path to its owner and active-licence check. Include
   an explicit decision on authorization-code/refresh support.
2. **Auth integration:** construct real signed tokens for each type/audience/grant, exercise the
   actual middleware and route dependency together, create/revoke/rotate a client, change
   owner/organization authority during token lifetime, and test mixed key/bearer requests. Mocking
   `verify_access_token` alone is insufficient.
3. **Money integration:** use PostgreSQL row locks and concurrent tasks to test cap boundaries,
   idempotent retries, wallet debit failure, Stripe session failure, webhook replay, refund and
   reconciliation. Assert persisted totals and no orphan order, transaction, acceptance or audit
   entry after failure.
4. **Legal and synthetic integration:** exercise both Agent API purchase routes and the canonical
   checkout with S1735 on, a published listing, exact acceptance hashes and guarded synthetic
   pairs. Inspect records and every access door after licence termination.
5. **Public surface/load:** test anonymous search/details/eval projections, query bounds, cache
   changes after listing withdrawal, replicas sharing the limiter, and 429 retry behavior. Compare
   a snapshot of published response fields with the P3 disclosure allowlist.
6. **S1656 test environment:** obtain an ordinary self-service test client and token through
   product routes; perform an OAuth-only purchase and delivery flow through the canonical test
   money path with the environment's armed synthetic guard. Prove cap denial and revoked-client
   denial without manual `agent_api_keys` insertion. Capture request IDs, backend/deployment SHA,
   order/transaction/acceptance IDs and scrubbed audit evidence.
7. **After authorized deploy:** independently record deployed SHA and flag state. With flag on,
   live unauthenticated `GET /api/v1/agent/search?q=test` must return 200; public OpenAPI and eval
   must work. In S1656, repeat OAuth-authenticated purchase, spend-cap enforcement and
   revoked-client refusal. Probe protected wallet/order/preview as anonymous and a wrong-audience
   token; require denial. A healthy deploy alone does not satisfy these checks.
8. **Release review:** Council reviews the exact Gate 1 SHA before implementation authority. Later
   implementation, security review, migration proof, S1656 flow, deploy and live checks are
   separate gates; report each with exact candidate and deployment identity.

## 7. Rollout and rollback

1. Add an `AGENT_API_OAUTH_ACCESS_ENABLED` flag defaulting **false** in every environment. With
   false, the current middleware key gate and route behavior remain the operational fallback.
   Schema may land while disabled; no client receives new authority from the migration alone.
2. Deploy schema and read compatibility first; verify old key-linked records. Then deploy actor
   resolution and shared paid guard behind the flag. Observe denial, cap, audit and latency
   metrics in S1656 before any production enablement.
3. Enable in S1656 for the full proof, then a bounded production cohort of explicitly eligible
   OAuth clients. Open the exact anonymous discovery routes only after their projection and
   distributed limiter pass. Record who flipped the flag, timestamp, deployed SHA, client cohort,
   rate/cap settings and dashboards.
4. Monitor 401/403/429 by route and actor kind, token validation errors, client revocation age,
   cap reservations/releases, duplicate payments, licence denials, anonymous query cost,
   audit-write failures and payment reconciliation. Alert on missing actor or unbounded spend;
   fail paid paths closed if policy or audit persistence is unavailable.
5. Roll back by switching the flag off, restoring key-gated admission and closing anonymous Agent
   API discovery. Stop new OAuth-only paid admissions; complete or reconcile already-created
   payment/order states using their stored OAuth identity. Do not erase policy, transaction, audit
   or licence records. If a code rollback precedes schema rollback, preserve additive columns
   until all OAuth-origin obligations and access rights are safely handled.
6. Any wider public route, new grant, relaxed cap, or change to licence/synthetic safeguards
   returns to Council as a scope change.

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
4. Should `/datasets/{id}/eval` expose its complete current field set anonymously, or a reduced
   projection? The proposal requires the reduced public projection until P3 review approves each
   field.
5. What revocation SLA and token-epoch behavior are acceptable for regenerated client secrets? The
   proposal requires immediate database denial on paid calls.
6. Must legacy key-plus-OAuth callers continue beyond the initial rollout, and what observed usage
   justifies a retirement date? No retirement is proposed now.
7. Should `/wallet/deposit` remain in the Agent API, or redirect the human owner to the existing
   wallet UI? Either option must retain wallet scope, consent and payment controls.

## 9. Scope and handoff

This Gate 1 artifact defines an access and money-control contract. It does not create credentials,
change backend code, mutate production data, approve a Council verdict, merge or deploy. Gate 2
must supply the concrete migration and route-by-route implementation plan against a freshly pinned
backend SHA, with any changed assumptions called out. The runbook index and checker are authoring
checks only.
