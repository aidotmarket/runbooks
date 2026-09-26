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

DNS setup and verification are in `cloudflare-and-dns.md` under “Adding a Railway-hosted subdomain.” Current Railway certificate status as a separate provider check is **UNVERIFIED** in this record; the HTTPS health checks below succeeded.

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

Variables set through `variableCollectionUpsert` with `skipDeploys: true` were `PORT=8080` and `CONNECTOR_ENABLED`, `CONNECTOR_OAUTH_ENABLED`, `CONNECTOR_CIMD_ENABLED`, `CONNECTOR_DCR_ENABLED` all `false`. The stub reads none of `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, a signing key, or an audit HMAC key; none is present yet. Add the needed values during OAuth stage / Chunk 3 through Infisical, the single secret store. The existing native sync `railway-backend-prod` targets only `ai-market-backend`; a sync or secret path for each new service is still to be set up. Exact future secret paths and values are **UNVERIFIED**.

The deployment procedure used a clean archive of backend main rather than a repository attachment:

```bash
git archive <backend main sha> | tar -x -C <dir>
cd <dir>
railway up --service <svc> --environment production --project e81dd66f-808c-412e-b32c-f6d910f0ac5d --detach -m '<msg>'
```

Use the account token from `~/bin/railway-env.sh` with `RAILWAY_TOKEN` unset. Railway GraphQL requests need a browser User-Agent. Do not print token values.

Backend main `2df3e416c` was uploaded at about 19:05–19:07 CEST on 2026-09-26. The connector deployment `dbea8e89-50d1-4093-8351-90f86b5402a2` and auth deployment `5f73a187-ce60-4721-865d-8fce1324a6de` both reached `SUCCESS`. On both `https://connect.ai.market` and `https://auth.ai.market`, `/healthz` returned HTTP 200 with `{"status":"ok"}`, `/readyz` returned HTTP 200, and `/mcp` returned HTTP 404. These checks establish the health stub only.

Backend migration `s_connector_foundation_001` has been live since 2026-09-26 18:38 CEST through backend `2df3e416c` (PR #488). The restricted runtime DB role and its audit-table INSERT/SELECT grant remain an operator step before Gate 4. While `CONNECTOR_RUNTIME_DB_ROLE` is unset, that migration skips grants; it refuses owner, migrator, or superuser-reachable roles. The future role identity and grant verification are **UNVERIFIED**.

## Capacity sample

The Chunk 2 point-in-time sample was taken on a Saturday evening. PostgreSQL `max_connections` was 500, reserved connections 3, and the peak `pg_stat_activity` count was 21 across six samples, leaving 476 connections of headroom. Redis `maxclients` was 10,000 and `connected_clients` was 58, leaving 9,942. The new maximum demand is 60 PostgreSQL and 60 Redis connections; with 25% margin, the budget is 75 each. Both fit within the sampled headroom. Re-sample before enable and before any replica increase; this sample does not establish future peak capacity.

## Rollback

Redeploy the previous deployment or scale the affected service to zero. All four connector flags are already off. The prior deployment IDs and any scale-to-zero execution are **UNVERIFIED** in this record.

## When it breaks

- `Config as Code is deprecated`: Railway refused a per-service config file. Keep the service source unattached and apply the settings above through `serviceInstanceUpdate`; deploy the backend archive with `railway up`.
- A service starts the backend app or runs Alembic: check whether repository source or the root Dockerfile command replaced the service start command. Restore the recorded `startCommand` and use the archive upload procedure.
- `/healthz` or `/readyz` stops returning HTTP 200: inspect the Railway deployment and its applied start command, health check path, and variables. A successful stub check is not proof of connector readiness.
- `/mcp` returns HTTP 404 at this Chunk 2 state: that is the recorded stub behavior. The resource ASGI entrypoint and protocol checks belong to Chunk 3.
