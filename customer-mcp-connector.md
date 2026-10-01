---
title: Customer MCP connector — build and operations
owner: unassigned
last_verified: '2026-09-30'
aliases: [customer MCP connector, ai-market-connector, ai-market-connector-auth, connect.ai.market, auth.ai.market]
error_signatures: ["You are being ratelimited. Please try again later", insufficient_assurance, Config as Code is deprecated, Infisical sync recursion setting unknown or enabled, "module 'secrets' has no attribute 'token_bytes'", connector_audit_write_failed, SECRET_KEY must be set, DOWNLOAD_TOKEN_SECRET_KEY must be changed from the default in production, EARLY_ACCESS_ONLY, CONNECTOR_DISABLED]
---

# Customer MCP connector — build and operations

This page records the verified connector deployment state. Mars verified the Chunk 2 infrastructure in S1753 on 2026-09-26. The auth service runs the OAuth authorization server with all four connector flags off: JWKS is published, while OAuth metadata and endpoints are closed. Since S1757 the backend consent API and the website consent and Connected apps pages are deployed, also with flags off. The Chunk 3 resource request edge was deployed in S1762 on 2026-09-28, with flags off and datastore readiness pending. Neither service is a working customer release.

## Railway services and DNS

Railway project `ai-market` is `e81dd66f-808c-412e-b32c-f6d910f0ac5d`; the production environment is `23e322c3-b195-45d8-9151-c4c27a998c33`.

| Service | Service ID | Host | Custom domain ID | Port |
| --- | --- | --- | --- | --- |
| `ai-market-connector` | `a08ef347-d2d1-4fcb-ba50-9299a9484fd5` | `connect.ai.market` | `519d4d32-649c-4adc-afe1-b9dca9100168` | 8080 |
| `ai-market-connector-auth` | `5ee110fc-df73-4107-b8fd-469099cb64d2` | `auth.ai.market` | `8b41594b-2ef9-4b43-9689-5df8f9b47892` | 8080 |

DNS setup and verification are in `cloudflare-and-dns.md` under “Adding a Railway-hosted subdomain.” Mars read back both Railway custom domains through GraphQL on 2026-09-26 at 19:53 CEST with this query shape (substitute each custom domain ID from the table):

```graphql
{ customDomain(id:"<id>", projectId:"e81dd66f-808c-412e-b32c-f6d910f0ac5d") { domain syncStatus status { verified certificateStatus } } }
```

| Domain | `verified` | `certificateStatus` | `syncStatus` | `dig` CNAME target |
| --- | --- | --- | --- | --- |
| `connect.ai.market` | `true` | `CERTIFICATE_STATUS_TYPE_VALID` | `ACTIVE` | `04tecdf8.up.railway.app.` |
| `auth.ai.market` | `true` | `CERTIFICATE_STATUS_TYPE_VALID` | `ACTIVE` | `r4sae793.up.railway.app.` |

## Configuration and deployment

Neither service has repository source attached. Railway refused a per-service config file on new services with `Config as Code is deprecated`. Connecting the backend repository instead builds its root `railway.json` and Dockerfile command, which starts Alembic and the backend app. The related failure mode is documented in `aim-data-gateway.md` under the `gateway-signer` notes.

The settings are described by backend files `railway.connector.json` and `railway.connector-auth.json`. They were applied to the respective services through Railway GraphQL `serviceInstanceUpdate`:

| Service | `startCommand` | `healthcheckPath` | `numReplicas` | `restartPolicyType` |
| --- | --- | --- | --- | --- |
| `ai-market-connector` | `sh -c 'exec uvicorn app.mcp.connector.asgi:app --host 0.0.0.0 --port ${PORT:-8080} --workers ${CONNECTOR_WORKERS:-2} --log-level ${LOG_LEVEL:-info} --timeout-graceful-shutdown 20 --limit-concurrency ${CONNECTOR_MAX_CONCURRENCY:-50}'` | `/healthz` until Gate 4 | `2` | `ON_FAILURE` |
| `ai-market-connector-auth` | `uvicorn app.mcp.connector_auth.asgi:app --host 0.0.0.0 --port 8080 --workers 2 --limit-concurrency 50` | `/readyz` | `2` | `ON_FAILURE` |

The resource start command was changed from the auth health stub to the exact `railway.connector.json` value on 2026-09-28. `tests/connector/test_key_isolation.py::test_resource_service_switches_entrypoint_when_asgi_exists` enforces the entrypoint switch. The service start commands override the backend Dockerfile command, so these services do not run migrations at startup. The resource's `/readyz` returns HTTP 503 until `DATABASE_URL` and `REDIS_URL` exist and the connector tables are reachable, by design in the deployed Chunk 3 `app/mcp/connector/health.py`; the proposed Chunk 5 also requires a configured audit sink. Its first Chunk 3 deployment, `c0b22302-8df4-42b5-ad0b-9b0eb5ab940f`, failed the Railway `/readyz` health check, leaving the previous stub serving. The resource `healthcheckPath` was then changed to `/healthz`. Restore `/readyz` in the same Gate 4 change that provisions the restricted DSN, Redis reference, and audit HMAC key, and require HTTP 200 from `/readyz` before enable. The auth service keeps `/readyz`.

Variables set through `variableCollectionUpsert` with `skipDeploys: true` were `PORT=8080` and `CONNECTOR_ENABLED`, `CONNECTOR_OAUTH_ENABLED`, `CONNECTOR_CIMD_ENABLED`, `CONNECTOR_DCR_ENABLED` all `false`. On 2026-09-28, Mars set the resource boot prerequisites with `railway variables --skip-deploys`: `CONNECTOR_AUTH_ISSUER=https://auth.ai.market`, `CONNECTOR_AUDIENCE=https://connect.ai.market/mcp`, and `CONNECTOR_JWKS_URL=https://auth.ai.market/.well-known/jwks.json`. The resource process refuses to start without them. `CONNECTOR_ALLOWED_HOSTS` defaults to `connect.ai.market`. Backend PR #526 adds `CONNECTOR_EXPECTED_PROCESSES` as the rate-limit fallback divisor; it must equal resource replicas × `CONNECTOR_WORKERS` (default `2 × 2 = 4`). `CONNECTOR_OAUTH_SIGNING_KEYS` must never be present on the resource: startup refuses it. That keyset is provisioned on `ai-market-connector-auth` only (see "Signing keyset: DONE" below). Distinct `SECRET_KEY` values, the resource audit HMAC key, and the Railway DSN and Redis references remain pending. Before Gate 4, provision and verify the remaining sources separately:

| Owner | Future variables | Required scope and verification |
| --- | --- | --- |
| Infisical | Distinct `SECRET_KEY` for each service; `CONNECTOR_OAUTH_SIGNING_KEYS` for auth only; resource `CONNECTOR_AUDIT_HMAC_KEY` | Signing keyset: **DONE** in `ai-market-backend`/`prod` at `/connector-auth`, synced only to `ai-market-connector-auth` by `railway-connector-auth-prod` (details below). Distinct `SECRET_KEY` paths and syncs, the resource audit HMAC key name, and their verification remain **PENDING**. The root `railway-backend-prod` sync targets only `ai-market-backend`. |
| Railway | Resource `CONNECTOR_AUTH_ISSUER`, `CONNECTOR_AUDIENCE`, `CONNECTOR_JWKS_URL`, restricted `DATABASE_URL`, `REDIS_URL`, `CONNECTOR_EXPECTED_PROCESSES`, `CONNECTOR_AUTH_FAILURE_MAX_IPS`, `OTEL_SERVICE_NAME=ai-market-connector`, and optional `OTEL_EXPORTER_OTLP_ENDPOINT` | Keep the three canonical auth URLs recorded above. Create the restricted connector runtime DSN and Redis as Railway variables/service references for the resource only; never store them in Infisical, per `infisical-secrets.md`. The restricted role and references are not yet provisioned or verified. Set `CONNECTOR_EXPECTED_PROCESSES` to resource replicas × `CONNECTOR_WORKERS` (currently `2 × 2 = 4`) and verify it after any scale change. `CONNECTOR_AUTH_FAILURE_MAX_IPS` defaults to 10000 and must be an integer >= 1. Chunk 5 forces the OTel service identity to `ai-market-connector` at startup; the OTLP endpoint enables export when configured. |

Before enable, verify that each connector Infisical path contains no `DATABASE_URL` or `REDIS_URL`, and use Railway GraphQL readback to confirm the intended service references and only the intended secret names. Suppress values in evidence.

**Early-access env erratum (backend PR #540, DeepSeek Gate 3 Finding 1; Max's Q8 decision: early access is a user allowlist).** Set `CONNECTOR_EARLY_ACCESS_USER_IDS` and `CONNECTOR_EARLY_ACCESS_ENFORCED` as process environment values, identically on `ai-market-backend` (website consent API), `ai-market-connector-auth` and `ai-market-connector`. `CONNECTOR_EARLY_ACCESS_ENFORCED` defaults to `true` and accepts `true`/`1`/`yes` or `false`/`0`/`no`. While enforced, only listed user UUIDs may consent, obtain or refresh tokens, or call the resource. A missing or empty list denies everyone; any malformed entry denies everyone and emits a critical log. To admit everyone, explicitly set `CONNECTOR_EARLY_ACCESS_ENFORCED=false` on all three services; an empty list alone never opens access. Restart all three after changing either value before treating the change as effective.

### Signing keyset: DONE (S1753, 2026-09-27)

Max's decision is Event Ledger `3d152156`; provisioning and verification are recorded in Events `53a51344`, `c8d012e4`, and `fa836fd2`. `CONNECTOR_OAUTH_SIGNING_KEYS` lives in Infisical project `ai-market-backend` (`bd272d48-c5a1-4b52-9d24-12066ae4403c`), environment `prod`, folder `/connector-auth`. The second native sync, `railway-connector-auth-prod`, sends that folder only to Railway `ai-market-connector-auth` (`5ee110fc-df73-4107-b8fd-469099cb64d2`), with auto-sync on, initial behavior `overwrite-destination`, and `disableSecretDeletion` true. A canary in `/connector-auth` did not appear in `ai-market-backend` or `ai-market-connector` after a forced `railway-backend-prod` root sync pass. That proves the root sync is non-recursive for this recorded setup.

The keyset has two P-256/ES256 public keys. `cs-20260927-251e63b07eed486c` signs; both it and `cs-20260927-f99004199d45d762` are published in JWKS. Their RFC 7638 thumbprints, in that order, are `_E2lVi8hJvz9E__tQjYH6TK0wPpDFhwWHCN4XcS0muU` and `hq0qWxa0BdJNJ2EfNNf78K8nVj0JVn1j9GoSd-lIjM0`. The canonical JWKS SHA-256 is `75d3999ee3bc147a30fb444207dbcd58330266945b97ab14f545489495d2cc19`. These are public identifiers and metadata, not signing material.

### How to operate: connector signing keyset tool

For the one-time provisioning sequence, use koskadeux-mcp main 0d7c6c25 or a reviewed successor in a clean detached checkout. The tool is `scripts/connector_keyset/connector_signing_keyset.py` (PR #253). Run it with `/Users/max/koskadeux-mcp/venv/bin/python`. Save its JSON receipts in a private scratch directory; they contain names and public metadata only. The sequence is:

```bash
PY=/Users/max/koskadeux-mcp/venv/bin/python
TOOL=scripts/connector_keyset/connector_signing_keyset.py
$PY "$TOOL" --selftest
$PY "$TOOL" inventory > baseline.json
$PY "$TOOL" drift-check
$PY "$TOOL" canary
$PY "$TOOL" canary --execute > canary-proof.json
$PY "$TOOL" create-sync --canary-proof canary-proof.json
$PY "$TOOL" create-sync --execute --canary-proof canary-proof.json
$PY "$TOOL" generate --canary-proof canary-proof.json
$PY "$TOOL" generate --execute --canary-proof canary-proof.json
$PY "$TOOL" verify --baseline baseline.json
```

Review each dry run before its `--execute` step. The tool refuses when `/Users/max/local-secops/HALT` exists, if the signing secret already exists, or on drift. `--selftest` makes no network calls. Its audit JSONL is `~/koskadeux-state/secrets/connector_signing_keyset.audit.jsonl`. This sequence records how provisioning was done; the live secret now exists, so `generate` will refuse. **Rotation is not supported by this tool.** Rotation needs a separate reviewed procedure.

The canary forces one `railway-backend-prod` sync pass, which redeployed `ai-market-backend` (`e5ab7c66`, healthy, values identical). Creating the connector sync and writing the key each redeployed `ai-market-connector-auth` (`a414391a` and `02354162`, both `SUCCESS`). The generate write did not redeploy the backend. Any Infisical `prod` write can trigger both syncs, so do not write to `/connector-auth` except through this tool for initial provisioning or a reviewed procedure.

### S1753 incident: Python standard-library shadowing (2026-09-27)

Events `12389ec2` and `5bb4880c`: koskadeux-mcp PR #249 added a `secrets/` package directly under `scripts/`, which shadowed Python's standard-library `secrets` module for any program started as `python scripts/X.py`. Railway issue-channel-watcher crashed from about 08:46Z to 09:40Z UTC with asyncpg `module 'secrets' has no attribute 'token_bytes'`. PR #253 fixed this by renaming the package to `scripts/connector_keyset/` and adding `tests/test_scripts_no_stdlib_shadow.py`. Never name a file or directory directly under koskadeux-mcp `scripts/` after a Python standard-library module.

### Deployment procedure

The deployment procedure used a clean archive of backend main rather than a repository attachment:

```bash
SHA=2df3e416cf421141311ca915a781487d24214953 # Replace with the full 40-character backend main SHA for a later deployment.
D=/Users/max/worktrees/connector-deploy-$SHA
mkdir -p "$D"
git -C /Users/max/Projects/ai-market/ai-market-backend fetch -q origin
git -C /Users/max/Projects/ai-market/ai-market-backend archive "$SHA" | tar -x -C "$D"
cd "$D"
unset RAILWAY_TOKEN
railway up --service ai-market-connector-auth --environment production --project e81dd66f-808c-412e-b32c-f6d910f0ac5d --detach -m "connector from ai-market-backend@$SHA"
railway up --service ai-market-connector --environment production --project e81dd66f-808c-412e-b32c-f6d910f0ac5d --detach -m "connector from ai-market-backend@$SHA"
```

Use the account token from `~/bin/railway-env.sh` with `RAILWAY_TOKEN` unset. Railway GraphQL requests need a browser User-Agent. Do not print token values.

Backend main `2df3e416cf421141311ca915a781487d24214953` was uploaded at about 19:05–19:07 CEST on 2026-09-26. The initial connector deployment `dbea8e89-50d1-4093-8351-90f86b5402a2` and auth deployment `5f73a187-ce60-4721-865d-8fce1324a6de` both reached `SUCCESS`. On both `https://connect.ai.market` and `https://auth.ai.market`, `/healthz` returned HTTP 200 with `{"status":"ok"}`, `/readyz` returned HTTP 200, and `/mcp` returned HTTP 404. These checks establish the health stub only; see the S1762 resource deployment below for the current resource behavior.

### Authorization server deployed, flags off (S1753, 2026-09-27)

Event `d8c9189f`: backend PR #505, the connector authorization server access-log redaction fix, merged as `c0695626b31188bdd30360f7a5bd918d7423daf9`. A git archive of that backend main was deployed to `ai-market-connector-auth` using the recorded procedure above. Railway deployment `ad0b07ee-521c-4542-a4ad-7afb0f4b929e` reached `SUCCESS` at about 13:03 CEST. All four connector flags remain `false`. The resource service `ai-market-connector` at `connect.ai.market` still runs the health stub until Chunk 3; see the S1762 resource deployment below for its later state.

On `https://auth.ai.market`, `/healthz` and `/readyz` returned HTTP 200. `/.well-known/jwks.json` returned HTTP 200 with the two ES256 public keys `cs-20260927-251e63b07eed486c` and `cs-20260927-f99004199d45d762`; their RFC 7638 thumbprints matched the recorded values above, and the response contained no private key members. JWKS is served regardless of connector flags. `/.well-known/oauth-authorization-server` returned HTTP 404 because `CONNECTOR_OAUTH_ENABLED` is `false`. `/oauth/authorize`, POST `/oauth/token`, `/oauth/register`, and `/oauth/revoke` also returned HTTP 404 because OAuth endpoints are gated by that flag. Railway logs showed no logging errors, and access lines contained no client address or query.

Backend migration `s_connector_foundation_001` has been live since 2026-09-26 18:38 CEST through backend `2df3e416cf421141311ca915a781487d24214953` (PR #488). While `CONNECTOR_RUNTIME_DB_ROLE` is unset, that migration skips grants; it refuses owner, migrator, or superuser-reachable roles.

GLM's read-only production DB readback on 2026-09-26 found that `ai_market_app` has `DELETE`, `INSERT`, `REFERENCES`, `SELECT`, `TRIGGER`, `TRUNCATE`, and `UPDATE` on `connector_audit_events` (`relacl`: `ai_market_app=arwdDxtm/postgres`; row-level security off). `has_table_privilege` returned true for `UPDATE` and `DELETE`. At that time append-only behavior rested on the table triggers only and the ACL did not satisfy the connector runtime privilege gate (superseded for `ai_market_app` on 2026-09-27, below).

**Mandatory for resource Gate 4, before enable:**

- Create a separate connector runtime DB role with effective `INSERT` and `SELECT` only on `connector_audit_events`. Before issuing its restricted `DATABASE_URL`, verify with `has_table_privilege` that `UPDATE`, `DELETE`, and `TRUNCATE` are false for every role permitted as a connector runtime/application role. Prove and record that `ai_market_app` is unreachable from connector services, or revoke its `UPDATE`, `DELETE`, and `TRUNCATE` grants through a reviewed migration and verify the effective privileges again. Record the role, reachability/grant decision, and results here.
- Provision that restricted `DATABASE_URL` and a Railway `REDIS_URL` reference on the resource service.
- Provision distinct `SECRET_KEY` values for resource and auth, and resource `CONNECTOR_AUDIT_HMAC_KEY` through the scoped Infisical paths and syncs above; keep signing keys off the resource. Verify the canonical resource `CONNECTOR_AUTH_ISSUER`, `CONNECTOR_AUDIENCE`, and `CONNECTOR_JWKS_URL`, set `CONNECTOR_EXPECTED_PROCESSES` to replicas × workers, and use `OTEL_SERVICE_NAME=ai-market-connector` (with `OTEL_EXPORTER_OTLP_ENDPOINT` if exporting telemetry).
- Configure the connector audit-write-failure alert in the telemetry alerting system before enable: `connector_audit_write_failures_total` above 0.1% of tool calls over five minutes. Backend Chunk 5 emits the metric but does not install an alert rule; this remains a Gate 4 prerequisite.
- Set `CONNECTOR_TRUSTED_PROXY_CIDRS` to Railway's actual edge peer range. Prove the setting with a forged `X-Forwarded-For` probe in both directions: real edge traffic is admitted, and a client-forged header does not change the resolved caller. Record which forwarded hop the Chunk 4 rate limiter must use; the edge currently takes the leftmost hop from a trusted peer.
- In the same change as the restricted DSN and Redis reference, set the resource Railway `healthcheckPath` back to `/readyz`. Confirm that `/readyz` returns HTTP 200 before enable.

**`ai_market_app` half: DONE (2026-09-27).** Max chose the revoke (Event Ledger `3d152156`). Backend PR #500, merged as `c231035f312d961dd3091a71ceae227105b3761b` after a unanimous Gate 3 (GLM, DeepSeek, CC in the Gemini seat per `d50cbd80`), adds revision `s_connector_audit_app_revoke_001`. It revokes `UPDATE`, `DELETE` and `TRUNCATE` on `connector_audit_events` from the role named in `ISSUE_CHANNEL_APPLICATION_DB_ROLE` and from `PUBLIC`. It refuses when that role is unset and the backend's seller-production predicate (`app/core/seller_production.py`) is true, or when the role is the owner, the migrating user, a superuser, or can reach one of them. Pre-merge read-only check: owner and migrator `postgres`; `ai_market_app` is not a superuser and cannot reach the owner, the migrator or any superuser. Railway deployment `fab83b3c-32ed-451c-b031-fe16c46a5c09` SUCCESS; `/health` healthy with Alembic current and head `s_connector_audit_app_revoke_001`. Read-only production readback on 2026-09-27 (owner DSN, `default_transaction_read_only=on`): `has_table_privilege('ai_market_app', 'connector_audit_events', ...)` is false for `UPDATE`, `DELETE` and `TRUNCATE`, and true for `INSERT` and `SELECT`. `PUBLIC` has no mutation privilege. `relacl` = `{postgres=arwdDxtm/postgres,ai_market_app=arxtm/postgres}`. `REFERENCES`, `TRIGGER` and `MAINTAIN` stay, as they are outside Max's decision.

**Connector runtime role half: PENDING.** No separate connector runtime role exists yet. Create it, verify it the same way, and record it here before any connector service receives a database DSN.

### Website/API consent stage released, flags off (S1757, 2026-09-27)

Gate 3 was unanimous (GLM, DeepSeek, CC in the Gemini seat per `d50cbd80`). Backend PR #510 merged as `0e95c72607aecd65bb56b3fd65a117a25984f976` and Railway deployment `b89c5911` of `ai-market-backend` reached `SUCCESS`. Frontend PR #94 merged as `559da55f072ec1368a0abde7c6019be89cd918f7` and Railway deployment `50746c2d` of `ai-market-frontend` reached `SUCCESS`. All connector flags stay `false`.

What shipped: backend `GET /api/v1/connector-oauth/status`, `GET /api/v1/connector-oauth/requests/{request}`, `POST /api/v1/connector-oauth/requests/{request}/decision`, `GET /api/v1/connector/grants` and `DELETE /api/v1/connector/grants/{id}`; a key-free sync-Session bridge in `app/mcp/connector_shared/`; and same-transaction grant revocation on password reset, 2FA enable and disable, organization membership create, invite and removal, and SSO membership creation (the user row is locked first). Frontend: `/oauth/connect` consent page, Connected apps in settings, and login, register, verify-email and callback resume through a 30-minute continuation.

Verify after any backend deploy while flags are off: `/health` returns HTTP 200; `GET https://api.ai.market/api/v1/connector-oauth/status` returns `{"enabled":false}`; `GET /api/v1/connector-oauth/requests/<43 chars>` and `GET /api/v1/connector/grants` return HTTP 404; `POST /api/v1/auth/reset-password` with body `{"token":"bogus-token-xyz","new_password":"Str0ng!Password123"}` and `Content-Type: application/json` returns HTTP 400 `{"detail":"Invalid or expired reset token"}` (a malformed body returns 422 instead, which is not a regression signal). All five held on 2026-09-27 at about 18:42 CEST.

Known gap: a user who signed in through SSO and has 2FA enabled cannot pass the consent assurance check (`insufficient_assurance`), because SSO sessions do not carry `auth_method == "2fa"`. The same applies to AIM Data OAuth. It is tracked as ticket T-2026-000879, to be settled before enable.

### Resource request edge deployed, flags off (S1762, 2026-09-28)

Backend PR #523 delivered core Chunk 3: the resource request edge, stateless MCP protocol, protected resource metadata (PRM), and error contract. It passed a unanimous Gate 3 with GLM, DeepSeek, and CC in the Gemini seat per `d50cbd80`, then merged as `0014396fc14f3ccccdea32d6e766cb6a24e69170`. Mars deployed a git archive of that SHA with `railway up` to `ai-market-connector` only. Deployment `f5a6f071-33b7-4ae1-80eb-7bd03a83820a` reached `SUCCESS` at about 22:34 CEST.

Mars verified at about 22:36 CEST: `https://connect.ai.market/healthz` returned HTTP 200 `{"status":"ok"}`; `/readyz` returned HTTP 503 `{"status":"unavailable"}`, expected until the restricted DSN, Redis reference, and connector tables are ready. Both `GET /.well-known/oauth-protected-resource` and `GET /.well-known/oauth-protected-resource/mcp` returned HTTP 200 with resource `https://connect.ai.market/mcp`, `authorization_servers` [`https://auth.ai.market`], nine sorted scopes, and `bearer_methods_supported` [`header`]. `POST /mcp` returned HTTP 503 with a JSON-RPC `CONNECTOR_DISABLED` error and action `wait`. `https://api.ai.market/health` returned HTTP 200, and `GET https://api.ai.market/api/v1/connector-oauth/status` returned `{"enabled":false}`. All four connector flags remain `false`.

Verify after a resource deploy while flags are off: require HTTP 200 `{"status":"ok"}` from `/healthz`; until Gate 4, expect HTTP 503 `{"status":"unavailable"}` from `/readyz`. Check both protected resource metadata URLs for HTTP 200 and the resource, authorization server, nine sorted scopes, and header bearer method above. Check `POST /mcp` for HTTP 503 JSON-RPC `CONNECTOR_DISABLED` with action `wait`. Check backend `/health` for HTTP 200 and `/api/v1/connector-oauth/status` for `{"enabled":false}`. Before enable, complete the Gate 4 prerequisites above and require `/readyz` to return HTTP 200.

### Connector switch administration (P0, runbook SQL)

This procedure applies once backend PR #526 is merged and deployed. The resource service reads `connector_switches` from Postgres at most every five seconds. `CONNECTOR_ENABLED=false` always keeps `/mcp` off, regardless of these rows. A cold process that cannot read the table stays disabled. P0 has no switch HTTP endpoint.

Migration `s_connector_foundation_001` creates `connector_switches` with `PRIMARY KEY (scope, key)`. Scope is one of `global`, `profile`, or `tool`; the global row is `('global', 'global')`. Until the connector runtime DB role exists (Gate 4), use the migration owner for writes through the documented credentialed production database access procedure in [`auth-signup-flow.md`](auth-signup-flow.md#production-database-query-when-needed); see also [`schema-migration.md`](schema-migration.md#s5-production-deploy-alignment) for the schema-owner connection boundary. Verify the database and environment before any statement. Never print credentials. Record the actor and reason in the change ticket.

Run only the single action needed. Follow the credentialed production database procedure above and the `AUTHOR_DISPATCH_DATABASE_URL` retrieval in [`schema-migration.md`](schema-migration.md#s7a-s1163-schema-classification-tooling-operator-reference). In the operator shell, disable tracing with `set +x`, load the documented Infisical API URL and token, then assign `DB_URL="$(infisical secrets get AUTHOR_DISPATCH_DATABASE_URL --projectId bd272d48-c5a1-4b52-9d24-12066ae4403c --env prod --plain | grep '^postgres' | tail -1)"` and `export DB_URL` after confirming it is nonempty. This obtains the migration-owner DSN from `ai-market-backend`/`prod` without printing it. Do not echo the DSN or paste its literal value into command history. This `DB_URL` is the temporary operator connection; the resource `DATABASE_URL` is the restricted runtime DSN. Verify the database and environment, then replace the example `reason` and `actor` with the ticket reason and operator identity. The `:'name'` form quotes each psql variable as a SQL literal. Each write block must change exactly one row; confirm `INSERT 0 1` or `UPDATE 1`, then confirm the exact-row readback and verify `/mcp` behavior within ten seconds of the write. Stop and investigate if the write count or readback differs. Keep the row for operator history.

Pause the entire connector (global row):

```bash
psql "$DB_URL" -v ON_ERROR_STOP=1 -v scope=global -v key=global -v reason='ticket reason' -v actor='operator identity' <<'SQL'
INSERT INTO connector_switches(scope, key, disabled, reason, actor, updated_at)
VALUES (:'scope', :'key', true, :'reason', :'actor', now())
ON CONFLICT (scope, key) DO UPDATE SET disabled = true,
  reason = EXCLUDED.reason, actor = EXCLUDED.actor, updated_at = now();
SELECT scope, key, disabled, reason, actor, updated_at
FROM connector_switches WHERE scope=:'scope' AND key=:'key';
SQL
```

Pause one verified grant profile (`default`, `claude`, or `openai`; example `openai`):

```bash
psql "$DB_URL" -v ON_ERROR_STOP=1 -v scope=profile -v key=openai -v reason='ticket reason' -v actor='operator identity' <<'SQL'
INSERT INTO connector_switches(scope, key, disabled, reason, actor, updated_at)
VALUES (:'scope', :'key', true, :'reason', :'actor', now())
ON CONFLICT (scope, key) DO UPDATE SET disabled = true,
  reason = EXCLUDED.reason, actor = EXCLUDED.actor, updated_at = now();
SELECT scope, key, disabled, reason, actor, updated_at
FROM connector_switches WHERE scope=:'scope' AND key=:'key';
SQL
```

Pause one registered tool (example `get_my_account`):

```bash
psql "$DB_URL" -v ON_ERROR_STOP=1 -v scope=tool -v key=get_my_account -v reason='ticket reason' -v actor='operator identity' <<'SQL'
INSERT INTO connector_switches(scope, key, disabled, reason, actor, updated_at)
VALUES (:'scope', :'key', true, :'reason', :'actor', now())
ON CONFLICT (scope, key) DO UPDATE SET disabled = true,
  reason = EXCLUDED.reason, actor = EXCLUDED.actor, updated_at = now();
SELECT scope, key, disabled, reason, actor, updated_at
FROM connector_switches WHERE scope=:'scope' AND key=:'key';
SQL
```

Enable one existing exact `(scope, key)` after approval (example `tool`, `get_my_account`):

```bash
psql "$DB_URL" -v ON_ERROR_STOP=1 -v scope=tool -v key=get_my_account -v reason='ticket reason for enable' -v actor='operator identity' <<'SQL'
UPDATE connector_switches SET disabled=false, reason=:'reason', actor=:'actor', updated_at=now() WHERE scope=:'scope' AND key=:'key';
SELECT scope, key, disabled, reason, actor, updated_at
FROM connector_switches WHERE scope=:'scope' AND key=:'key';
SQL
```

Read back one exact row without changing it (example `tool`, `get_my_account`):

```bash
psql "$DB_URL" -v ON_ERROR_STOP=1 -v scope=tool -v key=get_my_account <<'SQL'
SELECT scope, key, disabled, reason, actor, updated_at
FROM connector_switches WHERE scope=:'scope' AND key=:'key';
SQL
```

Do not set `CONNECTOR_ENABLED=true` as part of a DB switch change; that environment flag is a separate launch gate and requires a service restart.

### Audit and telemetry (Chunk 5)

Backend draft PR #528 at `b1358ba43fc660a400ccf6efb7a3269f65061816` adds this resource behavior; it has not been recorded here as deployed. Before enable, the resource needs canonical `CONNECTOR_AUTH_ISSUER=https://auth.ai.market`, `CONNECTOR_AUDIENCE=https://connect.ai.market/mcp`, and `CONNECTOR_JWKS_URL=https://auth.ai.market/.well-known/jwks.json`; a restricted connector runtime `DATABASE_URL`; `REDIS_URL`; resource `CONNECTOR_AUDIT_HMAC_KEY` from a scoped Infisical resource path and sync only; a `SECRET_KEY` distinct from auth; and `CONNECTOR_EXPECTED_PROCESSES` equal to resource replicas × `CONNECTOR_WORKERS` (currently `2 × 2 = 4`, default 4). `CONNECTOR_AUTH_FAILURE_MAX_IPS` defaults to 10000 and must be an integer >= 1. Set `OTEL_SERVICE_NAME=ai-market-connector`; `OTEL_EXPORTER_OTLP_ENDPOINT` is optional and enables OTLP export when present. Never put `CONNECTOR_OAUTH_SIGNING_KEYS` on the resource or use the backend root Infisical sync for its audit key. Resource startup rejects signing keys and noncanonical auth URLs. With `CONNECTOR_ENABLED=true`, missing `DATABASE_URL` or `CONNECTOR_AUDIT_HMAC_KEY` raises a settings error and refuses startup. With the flag off, missing either leaves the audit sink unconfigured and `/readyz` returns HTTP 503; readiness also requires database, connector tables, and Redis.

For authenticated `tools/call` requests that reach the tool handler, the code attempts one `tool.call` audit row per call, including tool, scope, validation, rate-limit, and handler denials. The request edge also records an insufficient-scope denial before dispatch. The row carries request and trace IDs, principal/grant/profile/tool metadata, scopes used, error code, and latency; arguments, result, and user agent are stored only as HMAC digests. `tools/list` is not audited. HTTP 401/403 responses on `/mcp` increment an in-memory `http.auth_failure` count by client IP and minute, per process. The writer flushes completed minutes to one row per IP/minute/process, with `event_count`; this is bounded write amplification under controller ruling S1762, not database-enforced uniqueness. After `CONNECTOR_AUTH_FAILURE_MAX_IPS` distinct IPs in a minute, further new IPs are counted in one overflow `http.auth_failure` row per minute per process with `ip = NULL`; already-counted IPs keep their own counts. For analysis, `SUM(event_count)` across per-process rows for an `(ip, minute)` (CC advisory). A crash can lose or duplicate one partial window. A flush-time database failure drops that window and increments `connector_audit_write_failures_total`. A read-audit insert failure still returns the tool response, increments the same metric, and logs `connector_audit_write_failed` with request ID and event type. An auth-dependency exception logs `connector_auth_dependency_unavailable` with request ID and exception class.

The code defines `connector_requests_total`, `connector_tool_latency_ms`, `connector_limiter_rejections_total`, `connector_fallback_activations_total`, `connector_switch_state`, and `connector_audit_write_failures_total`. The request metric's method labels are exactly `initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`, and `unknown`; outcome labels are exactly `ok`, `error`, `rate_limited`, and `denied`. Configure the audit-write-failure alert in the telemetry alerting system at more than 0.1% of tool calls over five minutes before Gate 4 enable; the draft code defines metrics but no alert rule. Custom connector trace attributes are limited to `mcp.method.name`, `mcp.tool.name`, `mcp.protocol.version`, `connector.profile`, `connector.client_id`, `connector.outcome`, `connector.error_code`, and `enduser.id_hash`. For traced POST `/mcp` requests, the request ID is the 32-character trace ID used in the response header, request log, and audit row, including when OTLP export is off.

### Discovery D2 deployed, tools disabled (S1762, 2026-09-29)

Backend PR #536 added `search_listings` and `get_listing`. Gate 3 R2 was a unanimous APPROVE from GLM, DeepSeek, and CC in the Gemini seat per `d50cbd80`. The PR merged as `6622153298f062b614b195f27d1e1a284484040d`. Both tools are registered for the `default`, `claude`, and `openai` profiles, require `market.read`, and have `explicit_switch_required`. A tool with this flag is hidden and uncallable unless its `connector_switches` tool row exists with `disabled=false`. A missing row, `disabled=true`, a cold process, or a failed switch read keeps it off. `get_my_account` retains the older rule: an absent row means enabled. The `openai` profile's output schemas have no price or purchase fields.

Before the merge, Mars inserted `('tool', 'search_listings')` and `('tool', 'get_listing')` rows with `disabled=true` at 08:41Z through the switch administration procedure above (ticket T-2026-000895, actor `mars-s1762`). After the Gate 4 prerequisites on this page pass, use the **Enable one existing exact `(scope, key)`** block above for each tool separately, with `scope=tool` and the exact tool key. Do not enable either tool before those prerequisites pass.

The first resource deployment of `66221532`, `757a160c-e73f-4d15-a7c1-486a1a959c20`, failed at startup. Its D2 import chain (`contact_scrubber` → `MediationService` → `app.core.config`) loaded backend Settings, which refuses startup without `SECRET_KEY`, `DOWNLOAD_TOKEN_SECRET_KEY`, and `INTERNAL_API_KEY`. The resource service deliberately has none of these backend secrets. Railway kept the previous deployment serving; there was no service impact. The issue channel recorded the failure about one minute after Railway's email (ticket T-2026-000896).

Backend PR #537, merged as `bb5ad62ad46419793962fee58f9daf33e24dc909`, moved those imports to call time. A settings failure during a call returns `TEMPORARILY_UNAVAILABLE`. `tests/connector/test_import_isolation.py` checks that a clean-environment import does not load `app.core.config`, `mediation_service`, `listing_search_service`, `qdrant_client`, or `embedding_service`. The Dockerfile connector smoke runs under `env -i` without `SECRET_KEY`, so this startup regression fails the build. Resource deployment `c8ec9984-d0a7-43f9-82c2-6e9eb64d064c` from `bb5ad62a` reached `SUCCESS` at about 11:58 CEST. Verification returned HTTP 200 from `/healthz`, HTTP 503 from `/readyz` as expected, HTTP 200 from protected resource metadata (PRM), and HTTP 503 `CONNECTOR_DISABLED` from POST `/mcp`.

**Gate 4 prerequisite for D2:** These tools need backend settings for the listing licence flag, Qdrant, and embedding at call time. Provision a connector-scoped minimal configuration without the backend's unrelated secrets, then prove both a search call and a detail call on the test host before enabling either tool.

**RULE:** Never add a module-level import of `app.core.config` (or anything that imports it) to the connector resource import path; keep it at call time.

### Discovery D3 and D4 deployed (S1762/S1764, 2026-09-29)

D3 backend PR #538 merged as `66109cdc` and deployed as `a4bd992b`. Disabled `('tool', 'get_activity')` and `('tool', 'list_data_requests')` switch rows were inserted under T-2026-000897.

D4 `ask_allai` backend PR #539 passed unanimous Gate 3 at R3 (GLM, DeepSeek, CC in the Gemini seat per `d50cbd80`) and merged as `08000393ece9eee2ef404eefff16cf26d253b51a`. Railway `ai-market-backend` deployment `cbbcd198-fc8d-4e6d-b5d3-38a5f9dabc6e` reached `SUCCESS`. Migration `20260929_002_connector_allai_budget` (revision `s1762_connector_allai_budget`, parent `s1761_t891_payout_path`) creates `connector_allai_daily_budget`, `connector_allai_daily_calls`, and `connector_allai_reservations`; its downgrade refuses while ledger evidence exists. Under change ticket `T-2026-000899`, Mars inserted `('tool', 'ask_allai')` with `disabled=true`; Event Ledger receipt `0775c46e-3901-48b1-b20a-e6a39c3286aa` records the D4 deploy and switch row, `INSERT 0 1`, at `2026-09-29 18:42:55.67751Z` (actor `mars-s1764`). Backend `/health` reported Alembic current=head=`s1762_connector_allai_budget`; connector-oauth status returned `enabled:false`; POST `https://connect.ai.market/mcp` returned HTTP 503 `CONNECTOR_DISABLED`. The resource service `ai-market-connector` still runs pre-D4 code until its Gate 4 redeploy.

### ask_allai enable configuration (for Gate 4)

Max chose `gpt-5.6-luna` in Event `c3dd857b`. Use these exact process environment values for Gate 4; the JSON is one complete value for `CONNECTOR_ALLAI_MODEL_PRICES_JSON`:

```text
CONNECTOR_ALLAI_MODEL=gpt-5.6-luna
CONNECTOR_ALLAI_FALLBACK_MODELS=
CONNECTOR_ALLAI_MAX_INPUT_TOKENS=16000
CONNECTOR_ALLAI_MAX_OUTPUT_TOKENS=512
CONNECTOR_ALLAI_CALLS_PER_USER_CLIENT_UTC_DAY=20
CONNECTOR_ALLAI_USD_PER_UTC_DAY=5.00
CONNECTOR_ALLAI_MODEL_PRICES_JSON={"gpt-5.6-luna":{"provider":"openai","prices":{"CONNECTOR_ALLAI_MODEL_INPUT_USD_PER_TOKEN":"0.0000002","CONNECTOR_ALLAI_MODEL_OUTPUT_USD_PER_TOKEN":"0.0000012","CONNECTOR_ALLAI_MODEL_THINKING_USD_PER_TOKEN":"0.0000012","CONNECTOR_ALLAI_MODEL_CACHE_USD_PER_TOKEN":"0.00000002"},"bounds":{"input":16000,"output":512,"thinking":0,"cache":16000},"attempts":1}}
```

The four prices are USD/token; cache `0.00000002` matches backend main `app/allai/cost_control.py` Luna cached input `0.02` USD per million tokens. At backend main `35af29cb`, `policy_from_settings()` accepts this configuration and calculates a maximum of **4,135 micro-USD (USD 0.004135) per call**, far below the **USD 5.00 connector-wide per UTC day** cap. The separate limit is **20 accepted calls per user-client per UTC day**. `CONNECTOR_ALLAI_MAX_INPUT_TOKENS` preflight compares UTF-8 bytes, a conservative upper bound on tokens. Reasoning models are refused without a mapped entry. Connector calls use the Responses API with reasoning effort `none`, `max_retries=0`, and no implicit fallback or temperature retry. Timeout defaults to 10 seconds and concurrency to 2 (maximum 64). Enable `ask_allai` only after Gate 4 and a live priced call proof.

### Early-access enforcement merged (S1764)

Backend PR #540 merged as `35af29cbd36f8a8ac05776d6bc17846f62c02920` on 2026-09-29. Railway `ai-market-backend` deployment `8a31909a-5b40-40f2-96f9-d62ef6671220` reached `SUCCESS` on main `35af29cb`; Event Ledger receipt `c2479a93-9fd0-48f1-974f-749e8c12ae0a` records the #540 deploy. `CONNECTOR_EARLY_ACCESS_ENFORCED` (default `true`) and `CONNECTOR_EARLY_ACCESS_USER_IDS` enforce the user allowlist at website consent, authorization-server authorize, token code exchange and refresh, and resource admission. Set both environment values identically on `ai-market-backend`, `ai-market-connector-auth`, and `ai-market-connector`; see specs erratum `b886ba76`. Enforcement becomes live on auth and resource only at their Gate 4 redeploy.

### Gate 4 Step 2 done: connector variables and secrets (S1771, 2026-09-30)

Mars ran Step 2 on production in a restart window Max approved, following `specs/BQ-CONNECTOR-GATE4-PROVISIONING-S1764.md` §2.1, §2.5 and the §2.3 final readback (Event `7340d351`; restricted receipt `koskadeux-state/s1771/step2-receipt.json`). Flags and the global switch stayed off throughout.

- **Resource Railway variables** (`skipDeploys`): restricted `DATABASE_URL` for `connector_runtime`; `REDIS_URL=${{Redis.REDIS_URL}}` (same Redis as the backend); the licensing trio equal to the backend; `CONNECTOR_EXPECTED_PROCESSES=4`, `CONNECTOR_AUTH_FAILURE_MAX_IPS=10000`, `OTEL_SERVICE_NAME=ai-market-connector`.
- **Early access:** `CONNECTOR_EARLY_ACCESS_ENFORCED=true` and an empty `CONNECTOR_EARLY_ACCESS_USER_IDS` on backend, auth and resource. Nobody is admitted until Step 6 adds UUIDs.
- **Infisical:** a new `/connector-resource` folder and native sync `railway-connector-resource-prod` (`29c333cf-82e8-4237-82a9-bb9066bbb225`) to `ai-market-connector` only. `/connector-auth` holds `CONNECTOR_OAUTH_SIGNING_KEYS` and its own `SECRET_KEY`. `/connector-resource` holds a different `SECRET_KEY` and `CONNECTOR_AUDIT_HMAC_KEY`. Destination fingerprints match their sources.
- **Non-recursion:** a canary in `/connector-resource` did not reach backend, auth, resource or watcher after forced runs of all three existing syncs. The canary was then deleted.
- **Health after the window:** `api.ai.market/health` 200, `auth.ai.market/readyz` 200, `connect.ai.market/healthz` 200, `/readyz` 200, `/mcp` 503 `CONNECTOR_DISABLED`.

What the no-deploy proof showed (S1771): a Railway `variableCollectionUpsert` with `skipDeploys:true` does not redeploy, but every Infisical native Railway sync job (create, forced run, or a secret write in a synced folder) redeploys its destination service. Plan any Infisical write to a synced folder as a restart of that service. Self-hosted Infisical v0.161.11 does not return `includeAllSubFolders` on Railway sync readback.

### Gate 4 Step 3 done: trusted edge peer and region (S1786, 2026-10-01)

Mars ran Step 3 per `specs/BQ-CONNECTOR-GATE4-PROVISIONING-S1764.md` §3 (runbooks #378, #380 and #383; each carries its full-panel gate record as a PR comment). The final receipt is `koskadeux-state/s1786/step3-receipt.json` (SHA-256 `4255d5329bd5f8195ef62146c07da19a2d74ef67b0f5981688886a6a153d4f51`). Flags and the global switch stayed off throughout.

- **Setting:** `CONNECTOR_TRUSTED_PROXY_CIDRS=100.64.0.0/24` on `ai-market-connector` only, live in deployment `90eda905-421c-4e58-ab19-416c1f154755`. Railway's edge reaches the container from socket peers in `100.64.0.2`–`.23`. Before the setting, every caller shared about 20 edge-peer rate-limit buckets.
- **Proof:** eight single-source windows, P1–P4 from the cloud workspace and from the Koskadeux host. All passed with 12 of 12 probes recorded in public caller buckets, none on an edge peer, and no `1.2.3.4`/`5.6.7.8` bucket. A client-supplied `X-Forwarded-For`, forged, invalid or prepended, never chose the bucket. Not measured: per-replica attribution, hop count, and whether the edge strips or appends.
- **Region:** both connector services ran in `us-east4-eqdc4a` with one instance each, while Redis, Postgres and the backend run in `us-west2`. In that placement only 6 and 8 of 12 probes reached Redis. The likely cause, confirmed by the 12 of 12 result after the move, is the pre-auth limiter's 100 ms Redis budget expiring across the continent; those requests fell back to per-process limits. Both services now run in `us-west2` with two instances each:
  - resource deployment `45bcc9b6-cb6f-4878-8439-4e318aca6016` for the move, superseded by `90eda905` when the CIDR was applied;
  - auth deployment `dfe2e9f7-f371-4353-a620-b162a90dd362`;
  - tool `koskadeux-state/s1786/region_move.d87911e9423d.py`, journal `receipts/region-journal.jsonl`.

  After the move, two checks recorded 12 of 12 probes. `CONNECTOR_EXPECTED_PROCESSES=4` (2 replicas × 2 workers) is now true. The JWKS kids and thumbprints are unchanged, OAuth routes return 404, and the auth flags are false.
- **Two rollbacks on the way, both clean:**
  - Execution 1 labelled sources by ipify addresses, but egress to Railway differs from what ipify reports.
  - Execution 2 lost probes to the limiter fallback, which led to the region finding.

  Receipts: `koskadeux-state/s1786/receipts/{exec1,exec2,rbcheck}/`.
- **Recorded, not changed:** these services also run in `us-east4` while their data stores are in `us-west2`: `ai-market-celery-worker`, `ai-market-celery-beat`, `ai-market-seller-profile-worker`, `gateway-signer`, `ai-market-gateway-door-worker` and `issue-channel-watcher`. `ai-market-backup` is also configured there but had no running instance at the time. Each database or Redis call they make crosses the continent. Moving them is a separate decision.

Rollback for Step 3: `koskadeux-state/s1786/apply_step3.py rollback --execute` (spec §3.5). Region rollback: `region_move.d87911e9423d.py restore --execute` restores the captured prior placement.

### Signing keyset recovery: NO SUPPORTED PATH TODAY (S1757, 2026-09-27)

The only copy of `CONNECTOR_OAUTH_SIGNING_KEYS` is Infisical `ai-market-backend`/`prod` `/connector-auth` and its synced Railway variable on `ai-market-connector-auth`. The 2026-09-27 03:04Z Infisical backup does not contain it (checked S1757). If both are lost, the keys cannot be restored, and there is no reviewed procedure to regenerate them. The provisioning tool's `generate` needs a canary proof that matches the live root sync (`connector_signing_keyset.py` `valid_canary_proof`), and `canary` refuses to mint a new one once the `railway-connector-auth-prod` sync exists (`require_syncs`). The S1753 proof saved as a local scratch receipt (`/Users/max/koskadeux-state/secrets/s1753/canary-proof.json`) still validated against the live root sync on 2026-09-27 at about 19:30 CEST (GLM read-only check), but it becomes invalid on any root-sync change and is not a reviewed or durable recovery route. Do not delete or recreate syncs, hand-write a proof, or create the secret by any other route. A lost keyset therefore means the authorization server stays down until a separately reviewed recovery or rotation procedure exists. Building that procedure is a pre-enable requirement of BQ-CONNECTOR-OAUTH. When it exists, record it here, including how to compare RFC 7638 thumbprints computed from the JWKS `kty`, `crv`, `x` and `y` members (JWKS itself publishes only `kid` and the public members). Any regenerated keyset invalidates every token signed with the old keys, so every connected client must reconnect.

## Anthropic directory listing (planned)

Max's directive (S1758, 2026-09-28): getting the connector into the Claude Connectors Directory is part of this build. Status: **not submitted**. The milestone and its checklist live on `build:bq-connector-core` under `directory_listing`.

- **Priority window.** Anthropic's email of 2026-07-06 ("Your MCP directory submission - action needed", to max@ai.market) asks older applicants to re-apply in the self-serve portal and then reply to that same email with the new submission link. Those re-applications go to the front of the review queue. The email gives no deadline.
- **Portal.** The email links `https://claude.ai/admin-settings/directory/submissions`; the current docs (`https://claude.com/docs/connectors/building/submission`) use `https://claude.ai/directory/manage`, choose **MCP connector**. Max submits from the ai.market Claude Team/Enterprise organization where he is Owner, so the listing belongs to ai.market rather than a personal account.
- **Prerequisite.** The portal connects to the live `https://` server and syncs its tools. The resource now returns `CONNECTOR_DISABLED` while flags are off, so the first submission follows Gate 4 with OAuth on for the early-access allowlist.
- **Needed at submission.** Every tool has a `title` and `readOnlyHint` or `destructiveHint`; the connector tested as a custom connector in Claude; OAuth working for Claude's client; documentation URL, privacy policy URL, support contact, icon, listing text, categories and a permanent slug; allowed link URIs `https://ai.market` and `https://auth.ai.market`; a fully populated synthetic reviewer account on the allowlist.
- **Presentation standard.** Max (S1758): the directory presentation must be very professional. Aim for the Verified label, where Anthropic reviewers test every tool: each tool succeeds with valid input and returns specific, actionable errors. Listing text in Max's voice; a public "Use ai.market in Claude" documentation page; a connector section in the privacy notice at `https://ai.market/legal/privacy` (on 2026-09-28 it did not mention assistants or connectors); a square icon legible on light and dark; a reviewer account populated with listings, conversations and a completed order. Max approves the whole pack before submission.
- **Financial transactions.** The portal's compliance step includes a financial-transactions acknowledgment. Max asked Anthropic about link-out checkout and negotiated quotes on 2026-09-23 (`mcp-review@anthropic.com`, ticket #135998017). Have that answer before submitting.
- **After submitting.** Max replies on the 2026-07-06 email with the submission link, BCC `drop@ai.market`. Record the submission link, listing URL and status here and on the build entity.

## Capacity sample

The Chunk 2 point-in-time sample was taken on a Saturday evening. PostgreSQL `max_connections` was 500, reserved connections 3, and the peak `pg_stat_activity` count was 21 across six samples, leaving 476 connections of headroom. Redis `maxclients` was 10,000 and `connected_clients` was 58, leaving 9,942. The new maximum demand is 60 PostgreSQL and 60 Redis connections; with 25% margin, the budget is 75 each. Both fit within the sampled headroom. Re-sample before enable and before any replica increase; this sample does not establish future peak capacity.

## Rollback

Before the 2026-09-26 drill, Railway deployment history contained exactly one deployment per service: connector `dbea8e89-50d1-4093-8351-90f86b5402a2` and auth `5f73a187-ce60-4721-865d-8fce1324a6de`. There was no earlier deployment to restore. All four connector flags were off.

At 19:54 CEST, Mars tested Railway GraphQL `mutation { deploymentRemove(id:"<deployment id>") }` against connector deployment `dbea8e89-50d1-4093-8351-90f86b5402a2`. Its status became `REMOVED`; `https://connect.ai.market/healthz` returned HTTP 404 within 10 seconds while `https://auth.ai.market/healthz` still returned HTTP 200. Mars then used the archive deployment procedure above to restore the connector as deployment `3abe2c20-6321-4481-960c-ffd7f7c0b24d`.

Current rollback is `deploymentRemove` on the affected bad deployment. Once an earlier named deployment exists, redeploy that known deployment using the archive procedure and record its ID. Check the affected service health and leave the other service untouched.

## When it breaks

- `You are being ratelimited. Please try again later` (Railway CLI) or HTTP 429 from `backboard.railway.app`: the account API token allows 1,000 requests per hour (`x-ratelimit-reset` gives the reset time). Guarded provisioning scripts spend it fast: each `railway variables` call and each deployment poll counts. Stop at a safe point, wait for the reset, poll every 30 s, and read variables through one GraphQL `variables` query rather than the CLI.
- `Config as Code is deprecated`: Railway refused a per-service config file. Keep the service source unattached and apply the settings above through `serviceInstanceUpdate`; deploy the backend archive with `railway up`.
- A service starts the backend app or runs Alembic: check whether repository source or the root Dockerfile command replaced the service start command. Restore the recorded `startCommand` and use the archive upload procedure.
- `/healthz` stops returning HTTP 200, or `/readyz` remains HTTP 503 after Gate 4: inspect the Railway deployment and its applied start command, health check path, variables, and connector table reachability. Successful health checks are not proof of a working customer release.
- `POST /mcp` on the resource returns HTTP 503 `CONNECTOR_DISABLED` while flags are off: that is the recorded Chunk 3 behavior. HTTP 404 was the earlier Chunk 2 stub behavior.
