---
title: Customer MCP connector — build and operations
owner: unassigned
last_verified: '2026-09-26'
aliases: [customer MCP connector, ai-market-connector, ai-market-connector-auth, connect.ai.market, auth.ai.market]
error_signatures: [Config as Code is deprecated]
---

# Customer MCP connector — build and operations

This page records the verified Chunk 2 infrastructure state for `specs/BQ-CONNECTOR-CORE-GATE2.md` §2 row 2. Mars verified it in S1753 on 2026-09-26. Both public services currently run a health-only auth stub with connector flags off; this is not a working customer MCP or OAuth release.

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

The intended settings are described by backend files `railway.connector.json` and `railway.connector-auth.json`. They were applied to both services through Railway GraphQL `serviceInstanceUpdate`:

| Setting | Value on both services |
| --- | --- |
| `startCommand` | `uvicorn app.mcp.connector_auth.asgi:app --host 0.0.0.0 --port 8080 --workers 2 --limit-concurrency 50` |
| `healthcheckPath` | `/readyz` |
| `numReplicas` | `2` |
| `restartPolicyType` | `ON_FAILURE` |

The resource service runs the auth health stub until Chunk 3. Chunk 3 must switch its entrypoint to `app.mcp.connector.asgi:app`; `tests/connector/test_key_isolation.py::test_resource_service_switches_entrypoint_when_asgi_exists` enforces that switch. The start command overrides the backend Dockerfile command, so these services do not run migrations at startup.

Variables set through `variableCollectionUpsert` with `skipDeploys: true` were `PORT=8080` and `CONNECTOR_ENABLED`, `CONNECTOR_OAUTH_ENABLED`, `CONNECTOR_CIMD_ENABLED`, `CONNECTOR_DCR_ENABLED` all `false`. The stub reads none of the future secrets or datastore references; none is present yet. Before OAuth stage / Chunk 3, provision and verify these sources separately:

| Owner | Future variables | Required scope and verification |
| --- | --- | --- |
| Infisical | Distinct `SECRET_KEY` for each service; `CONNECTOR_OAUTH_SIGNING_KEYS` for auth only; resource audit HMAC key | Set up a separate correctly scoped secret path and native sync for each service. The existing `railway-backend-prod` sync targets only `ai-market-backend`. Exact new paths, syncs, values, and audit HMAC variable name are **UNVERIFIED**. |
| Railway | `DATABASE_URL` as a restricted connector runtime DSN; `REDIS_URL` | Create these as Railway variables/service references for the intended service. Never store them in Infisical, per `infisical-secrets.md`. The restricted role and references are not yet provisioned or verified. |

Before enable, verify that each connector Infisical path contains no `DATABASE_URL` or `REDIS_URL`, and use Railway GraphQL readback to confirm the intended service references and only the intended secret names. Suppress values in evidence.

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

Backend main `2df3e416cf421141311ca915a781487d24214953` was uploaded at about 19:05–19:07 CEST on 2026-09-26. The initial connector deployment `dbea8e89-50d1-4093-8351-90f86b5402a2` and auth deployment `5f73a187-ce60-4721-865d-8fce1324a6de` both reached `SUCCESS`. On both `https://connect.ai.market` and `https://auth.ai.market`, `/healthz` returned HTTP 200 with `{"status":"ok"}`, `/readyz` returned HTTP 200, and `/mcp` returned HTTP 404. These checks establish the health stub only.

Backend migration `s_connector_foundation_001` has been live since 2026-09-26 18:38 CEST through backend `2df3e416cf421141311ca915a781487d24214953` (PR #488). While `CONNECTOR_RUNTIME_DB_ROLE` is unset, that migration skips grants; it refuses owner, migrator, or superuser-reachable roles.

GLM's read-only production DB readback on 2026-09-26 found that `ai_market_app` has `DELETE`, `INSERT`, `REFERENCES`, `SELECT`, `TRIGGER`, `TRUNCATE`, and `UPDATE` on `connector_audit_events` (`relacl`: `ai_market_app=arwdDxtm/postgres`; row-level security off). `has_table_privilege` returned true for `UPDATE` and `DELETE`. Append-only behavior today rests on the table triggers only; the current ACL does **not** satisfy the connector runtime privilege gate.

**Mandatory before Gate 4 and before any connector service receives a database DSN:** create a separate connector runtime role with effective `INSERT` and `SELECT` only on `connector_audit_events`. Verify with `has_table_privilege` that `UPDATE`, `DELETE`, and `TRUNCATE` are all false for every role permitted as a connector runtime/application role. Also prove and record that `ai_market_app` is unreachable from connector services, or revoke its `UPDATE`, `DELETE`, and `TRUNCATE` grants on this table through a reviewed migration and verify the effective privileges again. Record the role, reachability/grant decision, and verification results on this page before issuing a DSN. This future verification is **PENDING**; the observed production ACL above is the current result.

## Capacity sample

The Chunk 2 point-in-time sample was taken on a Saturday evening. PostgreSQL `max_connections` was 500, reserved connections 3, and the peak `pg_stat_activity` count was 21 across six samples, leaving 476 connections of headroom. Redis `maxclients` was 10,000 and `connected_clients` was 58, leaving 9,942. The new maximum demand is 60 PostgreSQL and 60 Redis connections; with 25% margin, the budget is 75 each. Both fit within the sampled headroom. Re-sample before enable and before any replica increase; this sample does not establish future peak capacity.

## Rollback

Before the 2026-09-26 drill, Railway deployment history contained exactly one deployment per service: connector `dbea8e89-50d1-4093-8351-90f86b5402a2` and auth `5f73a187-ce60-4721-865d-8fce1324a6de`. There was no earlier deployment to restore. All four connector flags were off.

At 19:54 CEST, Mars tested Railway GraphQL `mutation { deploymentRemove(id:"<deployment id>") }` against connector deployment `dbea8e89-50d1-4093-8351-90f86b5402a2`. Its status became `REMOVED`; `https://connect.ai.market/healthz` returned HTTP 404 within 10 seconds while `https://auth.ai.market/healthz` still returned HTTP 200. Mars then used the archive deployment procedure above to restore the connector as deployment `3abe2c20-6321-4481-960c-ffd7f7c0b24d`.

Current rollback is `deploymentRemove` on the affected bad deployment. Once an earlier named deployment exists, redeploy that known deployment using the archive procedure and record its ID. Check the affected service health and leave the other service untouched.

## When it breaks

- `Config as Code is deprecated`: Railway refused a per-service config file. Keep the service source unattached and apply the settings above through `serviceInstanceUpdate`; deploy the backend archive with `railway up`.
- A service starts the backend app or runs Alembic: check whether repository source or the root Dockerfile command replaced the service start command. Restore the recorded `startCommand` and use the archive upload procedure.
- `/healthz` or `/readyz` stops returning HTTP 200: inspect the Railway deployment and its applied start command, health check path, and variables. A successful stub check is not proof of connector readiness.
- `/mcp` returns HTTP 404 at this Chunk 2 state: that is the recorded stub behavior. The resource ASGI entrypoint and protocol checks belong to Chunk 3.
