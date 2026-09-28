---
title: Customer MCP connector — build and operations
owner: unassigned
last_verified: '2026-09-27'
aliases: [customer MCP connector, ai-market-connector, ai-market-connector-auth, connect.ai.market, auth.ai.market]
error_signatures: [insufficient_assurance, Config as Code is deprecated, Infisical sync recursion setting unknown or enabled, "module 'secrets' has no attribute 'token_bytes'"]
---

# Customer MCP connector — build and operations

This page records the verified Chunk 2 infrastructure state for `specs/BQ-CONNECTOR-CORE-GATE2.md` §2 row 2. Mars verified it in S1753 on 2026-09-26. The auth service now runs the OAuth authorization server with all four connector flags off: JWKS is published, while OAuth metadata and endpoints are closed. Since S1757 the backend consent API and the website consent and Connected apps pages are deployed, also with flags off. The resource service still runs the health stub until Chunk 3. Neither service is a working customer release.

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

Variables set through `variableCollectionUpsert` with `skipDeploys: true` were `PORT=8080` and `CONNECTOR_ENABLED`, `CONNECTOR_OAUTH_ENABLED`, `CONNECTOR_CIMD_ENABLED`, `CONNECTOR_DCR_ENABLED` all `false`. The resource health stub reads none of these secrets or datastore references. `CONNECTOR_OAUTH_SIGNING_KEYS` is now provisioned on `ai-market-connector-auth` (see "Signing keyset: DONE" below). Distinct `SECRET_KEY` values, the resource audit HMAC key, and the Railway DSN and Redis references remain pending. Before OAuth stage / Chunk 3, provision and verify the remaining sources separately:

| Owner | Future variables | Required scope and verification |
| --- | --- | --- |
| Infisical | Distinct `SECRET_KEY` for each service; `CONNECTOR_OAUTH_SIGNING_KEYS` for auth only; resource audit HMAC key | Signing keyset: **DONE** in `ai-market-backend`/`prod` at `/connector-auth`, synced only to `ai-market-connector-auth` by `railway-connector-auth-prod` (details below). Distinct `SECRET_KEY` paths and syncs, the resource audit HMAC key name, and their verification remain **PENDING**. The root `railway-backend-prod` sync targets only `ai-market-backend`. |
| Railway | `DATABASE_URL` as a restricted connector runtime DSN; `REDIS_URL` | Create these as Railway variables/service references for the intended service. Never store them in Infisical, per `infisical-secrets.md`. The restricted role and references are not yet provisioned or verified. |

Before enable, verify that each connector Infisical path contains no `DATABASE_URL` or `REDIS_URL`, and use Railway GraphQL readback to confirm the intended service references and only the intended secret names. Suppress values in evidence.

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

Backend main `2df3e416cf421141311ca915a781487d24214953` was uploaded at about 19:05–19:07 CEST on 2026-09-26. The initial connector deployment `dbea8e89-50d1-4093-8351-90f86b5402a2` and auth deployment `5f73a187-ce60-4721-865d-8fce1324a6de` both reached `SUCCESS`. On both `https://connect.ai.market` and `https://auth.ai.market`, `/healthz` returned HTTP 200 with `{"status":"ok"}`, `/readyz` returned HTTP 200, and `/mcp` returned HTTP 404. These checks establish the health stub only.

### Authorization server deployed, flags off (S1753, 2026-09-27)

Event `d8c9189f`: backend PR #505, the connector authorization server access-log redaction fix, merged as `c0695626b31188bdd30360f7a5bd918d7423daf9`. A git archive of that backend main was deployed to `ai-market-connector-auth` using the recorded procedure above. Railway deployment `ad0b07ee-521c-4542-a4ad-7afb0f4b929e` reached `SUCCESS` at about 13:03 CEST. All four connector flags remain `false`. The resource service `ai-market-connector` at `connect.ai.market` still runs the health stub until Chunk 3.

On `https://auth.ai.market`, `/healthz` and `/readyz` returned HTTP 200. `/.well-known/jwks.json` returned HTTP 200 with the two ES256 public keys `cs-20260927-251e63b07eed486c` and `cs-20260927-f99004199d45d762`; their RFC 7638 thumbprints matched the recorded values above, and the response contained no private key members. JWKS is served regardless of connector flags. `/.well-known/oauth-authorization-server` returned HTTP 404 because `CONNECTOR_OAUTH_ENABLED` is `false`. `/oauth/authorize`, POST `/oauth/token`, `/oauth/register`, and `/oauth/revoke` also returned HTTP 404 because OAuth endpoints are gated by that flag. Railway logs showed no logging errors, and access lines contained no client address or query.

Backend migration `s_connector_foundation_001` has been live since 2026-09-26 18:38 CEST through backend `2df3e416cf421141311ca915a781487d24214953` (PR #488). While `CONNECTOR_RUNTIME_DB_ROLE` is unset, that migration skips grants; it refuses owner, migrator, or superuser-reachable roles.

GLM's read-only production DB readback on 2026-09-26 found that `ai_market_app` has `DELETE`, `INSERT`, `REFERENCES`, `SELECT`, `TRIGGER`, `TRUNCATE`, and `UPDATE` on `connector_audit_events` (`relacl`: `ai_market_app=arwdDxtm/postgres`; row-level security off). `has_table_privilege` returned true for `UPDATE` and `DELETE`. At that time append-only behavior rested on the table triggers only and the ACL did not satisfy the connector runtime privilege gate (superseded for `ai_market_app` on 2026-09-27, below).

**Mandatory before Gate 4 and before any connector service receives a database DSN:** create a separate connector runtime role with effective `INSERT` and `SELECT` only on `connector_audit_events`. Verify with `has_table_privilege` that `UPDATE`, `DELETE`, and `TRUNCATE` are all false for every role permitted as a connector runtime/application role. Also prove and record that `ai_market_app` is unreachable from connector services, or revoke its `UPDATE`, `DELETE`, and `TRUNCATE` grants on this table through a reviewed migration and verify the effective privileges again. Record the role, reachability/grant decision, and verification results on this page before issuing a DSN.

**`ai_market_app` half: DONE (2026-09-27).** Max chose the revoke (Event Ledger `3d152156`). Backend PR #500, merged as `c231035f312d961dd3091a71ceae227105b3761b` after a unanimous Gate 3 (GLM, DeepSeek, CC in the Gemini seat per `d50cbd80`), adds revision `s_connector_audit_app_revoke_001`. It revokes `UPDATE`, `DELETE` and `TRUNCATE` on `connector_audit_events` from the role named in `ISSUE_CHANNEL_APPLICATION_DB_ROLE` and from `PUBLIC`. It refuses when that role is unset and the backend's seller-production predicate (`app/core/seller_production.py`) is true, or when the role is the owner, the migrating user, a superuser, or can reach one of them. Pre-merge read-only check: owner and migrator `postgres`; `ai_market_app` is not a superuser and cannot reach the owner, the migrator or any superuser. Railway deployment `fab83b3c-32ed-451c-b031-fe16c46a5c09` SUCCESS; `/health` healthy with Alembic current and head `s_connector_audit_app_revoke_001`. Read-only production readback on 2026-09-27 (owner DSN, `default_transaction_read_only=on`): `has_table_privilege('ai_market_app', 'connector_audit_events', ...)` is false for `UPDATE`, `DELETE` and `TRUNCATE`, and true for `INSERT` and `SELECT`. `PUBLIC` has no mutation privilege. `relacl` = `{postgres=arwdDxtm/postgres,ai_market_app=arxtm/postgres}`. `REFERENCES`, `TRIGGER` and `MAINTAIN` stay, as they are outside Max's decision.

**Connector runtime role half: PENDING.** No separate connector runtime role exists yet. Create it, verify it the same way, and record it here before any connector service receives a database DSN.

### Website/API consent stage released, flags off (S1757, 2026-09-27)

Gate 3 was unanimous (GLM, DeepSeek, CC in the Gemini seat per `d50cbd80`). Backend PR #510 merged as `0e95c72607aecd65bb56b3fd65a117a25984f976` and Railway deployment `b89c5911` of `ai-market-backend` reached `SUCCESS`. Frontend PR #94 merged as `559da55f072ec1368a0abde7c6019be89cd918f7` and Railway deployment `50746c2d` of `ai-market-frontend` reached `SUCCESS`. All connector flags stay `false`.

What shipped: backend `GET /api/v1/connector-oauth/status`, `GET /api/v1/connector-oauth/requests/{request}`, `POST /api/v1/connector-oauth/requests/{request}/decision`, `GET /api/v1/connector/grants` and `DELETE /api/v1/connector/grants/{id}`; a key-free sync-Session bridge in `app/mcp/connector_shared/`; and same-transaction grant revocation on password reset, 2FA enable and disable, organization membership create, invite and removal, and SSO membership creation (the user row is locked first). Frontend: `/oauth/connect` consent page, Connected apps in settings, and login, register, verify-email and callback resume through a 30-minute continuation.

Verify after any backend deploy while flags are off: `/health` returns HTTP 200; `GET https://api.ai.market/api/v1/connector-oauth/status` returns `{"enabled":false}`; `GET /api/v1/connector-oauth/requests/<43 chars>` and `GET /api/v1/connector/grants` return HTTP 404; `POST /api/v1/auth/reset-password` with body `{"token":"bogus-token-xyz","new_password":"Str0ng!Password123"}` and `Content-Type: application/json` returns HTTP 400 `{"detail":"Invalid or expired reset token"}` (a malformed body returns 422 instead, which is not a regression signal). All five held on 2026-09-27 at about 18:42 CEST.

Known gap: a user who signed in through SSO and has 2FA enabled cannot pass the consent assurance check (`insufficient_assurance`), because SSO sessions do not carry `auth_method == "2fa"`. The same applies to AIM Data OAuth. It is tracked as ticket T-2026-000879, to be settled before enable.

### Signing keyset recovery: NO SUPPORTED PATH TODAY (S1757, 2026-09-27)

The only copy of `CONNECTOR_OAUTH_SIGNING_KEYS` is Infisical `ai-market-backend`/`prod` `/connector-auth` and its synced Railway variable on `ai-market-connector-auth`. The 2026-09-27 03:04Z Infisical backup does not contain it (checked S1757). If both are lost, the keys cannot be restored, and there is no reviewed procedure to regenerate them. The provisioning tool's `generate` needs a canary proof that matches the live root sync (`connector_signing_keyset.py` `valid_canary_proof`), and `canary` refuses to mint a new one once the `railway-connector-auth-prod` sync exists (`require_syncs`). The S1753 proof saved as a local scratch receipt (`/Users/max/koskadeux-state/secrets/s1753/canary-proof.json`) still validated against the live root sync on 2026-09-27 at about 19:30 CEST (GLM read-only check), but it becomes invalid on any root-sync change and is not a reviewed or durable recovery route. Do not delete or recreate syncs, hand-write a proof, or create the secret by any other route. A lost keyset therefore means the authorization server stays down until a separately reviewed recovery or rotation procedure exists. Building that procedure is a pre-enable requirement of BQ-CONNECTOR-OAUTH. When it exists, record it here, including how to compare RFC 7638 thumbprints computed from the JWKS `kty`, `crv`, `x` and `y` members (JWKS itself publishes only `kid` and the public members). Any regenerated keyset invalidates every token signed with the old keys, so every connected client must reconnect.

## Anthropic directory listing (planned)

Max's directive (S1758, 2026-09-28): getting the connector into the Claude Connectors Directory is part of this build. Status: **not submitted**. The milestone and its checklist live on `build:bq-connector-core` under `directory_listing`.

- **Priority window.** Anthropic's email of 2026-07-06 ("Your MCP directory submission - action needed", to max@ai.market) asks older applicants to re-apply in the self-serve portal and then reply to that same email with the new submission link. Those re-applications go to the front of the review queue. The email gives no deadline.
- **Portal.** The email links `https://claude.ai/admin-settings/directory/submissions`; the current docs (`https://claude.com/docs/connectors/building/submission`) use `https://claude.ai/directory/manage`, choose **MCP connector**. Max submits from his own workspace.
- **Prerequisite.** The portal connects to the live `https://` server and syncs its tools. It cannot be done while `connect.ai.market/mcp` returns 404, so the first submission follows Chunk 3 with OAuth on for the early-access allowlist.
- **Needed at submission.** Every tool has a `title` and `readOnlyHint` or `destructiveHint`; the connector tested as a custom connector in Claude; OAuth working for Claude's client; documentation URL, privacy policy URL, support contact, icon, listing text, categories and a permanent slug; allowed link URIs `https://ai.market` and `https://auth.ai.market`; a fully populated synthetic reviewer account on the allowlist.
- **Financial transactions.** The portal's compliance step includes a financial-transactions acknowledgment. Max asked Anthropic about link-out checkout and negotiated quotes on 2026-09-23 (`mcp-review@anthropic.com`, ticket #135998017). Have that answer before submitting.
- **After submitting.** Max replies on the 2026-07-06 email with the submission link, BCC `drop@ai.market`. Record the submission link, listing URL and status here and on the build entity.

## Capacity sample

The Chunk 2 point-in-time sample was taken on a Saturday evening. PostgreSQL `max_connections` was 500, reserved connections 3, and the peak `pg_stat_activity` count was 21 across six samples, leaving 476 connections of headroom. Redis `maxclients` was 10,000 and `connected_clients` was 58, leaving 9,942. The new maximum demand is 60 PostgreSQL and 60 Redis connections; with 25% margin, the budget is 75 each. Both fit within the sampled headroom. Re-sample before enable and before any replica increase; this sample does not establish future peak capacity.

## Rollback

Before the 2026-09-26 drill, Railway deployment history contained exactly one deployment per service: connector `dbea8e89-50d1-4093-8351-90f86b5402a2` and auth `5f73a187-ce60-4721-865d-8fce1324a6de`. There was no earlier deployment to restore. All four connector flags were off.

At 19:54 CEST, Mars tested Railway GraphQL `mutation { deploymentRemove(id:"<deployment id>") }` against connector deployment `dbea8e89-50d1-4093-8351-90f86b5402a2`. Its status became `REMOVED`; `https://connect.ai.market/healthz` returned HTTP 404 within 10 seconds while `https://auth.ai.market/healthz` still returned HTTP 200. Mars then used the archive deployment procedure above to restore the connector as deployment `3abe2c20-6321-4481-960c-ffd7f7c0b24d`.

Current rollback is `deploymentRemove` on the affected bad deployment. Once an earlier named deployment exists, redeploy that known deployment using the archive procedure and record its ID. Check the affected service health and leave the other service untouched.

## When it breaks

- `Config as Code is deprecated`: Railway refused a per-service config file. Keep the service source unattached and apply the settings above through `serviceInstanceUpdate`; deploy the backend archive with `railway up`.
- A service starts the backend app or runs Alembic: check whether repository source or the root Dockerfile command replaced the service start command. Restore the recorded `startCommand` and use the archive upload procedure.
- `/healthz` or `/readyz` stops returning HTTP 200: inspect the Railway deployment and its applied start command, health check path, and variables. Successful health checks are not proof of a working customer release.
- `/mcp` returns HTTP 404 on the resource service at this Chunk 2 state: that is the recorded stub behavior. The resource ASGI entrypoint and protocol checks belong to Chunk 3.
