# BQ-CONNECTOR-CORE Gate 4 — provisioning and early-access enable plan (S1764)

Status: **plan only; no production enable authority or completion claim.** Base: runbooks main `d2cc51293ac127c94be1e73650e57a298818d150`; backend main `66109cdc681066bf05e99d3a43de368daa2d4c26` (2026-09-29). Authority: `customer-mcp-connector.md` (especially Mandatory for resource Gate 4, switch administration, keyset, consent and directory sections), core Gate 1/2, buyer discovery Gate 2, OAuth Gate 2, `infisical-secrets.md`, `local-secops.md`, `schema-migration.md`, `auth-signup-flow.md`, Railway runbooks. The operator records exact SHAs/deployments again at execution; a later backend main requires a fresh code/table-access diff. Target: `https://connect.ai.market/mcp` works with OAuth for Max, an approved synthetic reviewer, and existing test accounts, then Max may submit it from the ai.market Claude organization. Keep the allowlist until the P1 release decision.

## Stop gates before a production change

Open one S1764 change ticket with owner, window, exact backend/frontend/runbooks SHAs, Railway deployment IDs, migration head, backup/recovery reference, rollback operator, and acceptance checklist. Confirm core Chunks 4/5 and discovery D1–D3 are merged, reviewed and deployed with flags/tools off; verify `s_connector_foundation_001` and `s_connector_audit_app_revoke_001` *artifacts*, not only `alembic_version`; confirm OAuth keyset JWKS thumbprints against the runbook and a reviewed keyset recovery/rotation route. Capture Postgres/Redis connection headroom from core Gate 2 §4. T-2026-000879 is a hard stop until the SSO+2FA consent policy is resolved and tested, or an explicit narrow early-access decision records why only password-login accounts are eligible. Max must approve privacy wording, the reviewer account identity/personal data, the full directory presentation pack, and submission. No production customer data is copied into the synthetic account.

**Current code gap:** backend main has no `CONNECTOR_EARLY_ACCESS_USER_IDS` read or enforcement in `app/`; `app/mcp/connector_shared/profiles.yaml` has empty Claude/OpenAI CIMD entries. A Railway variable alone cannot restrict access or yield a verified Claude profile. Before step 7, a separately reviewed/deployed backend change must enforce the nonempty UUID allowlist at OAuth consent, authorization-code **token exchange and refresh**, and resource request/grant use (including preexisting grants); fail closed on missing/malformed/empty configuration while early access is active; pin Claude's validated CIMD client document and exact redirect. The enforcement build covers the token endpoint: excluded accounts must receive no new or refreshed token, even after an earlier consent. Record deployed SHA and negative live proofs at consent, token, refresh and resource. Do not infer an allowlist from a switch, profile or DCR registration. This plan does not implement that code.

## Ordered operator procedure

Every mutation below gets its own timestamped ticket receipt: before/after **names or IDs only**, exact verification, actor, and immediate rollback. Disable shell tracing (`set +x`); load the migration-owner `AUTHOR_DISPATCH_DATABASE_URL` using `schema-migration.md` §S.7a and the credentialed production DB procedure in `auth-signup-flow.md`; do not echo a DSN, password, token, or secret. Verify `current_database()`, `current_user`, `inet_server_addr()`, and the Railway production project/environment before SQL. The resource never gets this owner DSN.

1. **Create restricted role and grant only code-used columns.** Use one reviewed owner-session SQL change, **not migration replay**: `s_connector_foundation_001.upgrade()` creates tables before `_grant_audit_privileges()` and is already applied; rerunning it attempts table creation. A future additive grant-only migration may normalize the ACL. Run the step-1 SQL with a **psql 15 or later client** (`\getenv` requirement); the Titan-1 Homebrew client is 14.20, and the local `postgres:17` image satisfies this requirement. Record that local image's digest in the change ticket, verify `psql --version`, and run with `--pull=never` so the image does not change during execution. In a protected process, derive `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` and `PGSSLMODE` from the owner DSN without printing it; with those variables and `CONNECTOR_RUNTIME_SCRAM_VERIFIER` exported, feed the reviewed SQL on stdin using `docker run --rm --pull=never -i -e PGHOST -e PGPORT -e PGUSER -e PGPASSWORD -e PGDATABASE -e PGSSLMODE -e CONNECTOR_RUNTIME_SCRAM_VERIFIER postgres:17 psql -v ON_ERROR_STOP=1`. Pass values by environment-variable name only, with no DSN in any argv. The short-lived container has no persistent history; its `Env` remains locally inspectable during execution, an accepted short-lived risk. First check the role does not already exist, and its owner/migrator/superuser/`ai_market_app` membership paths are absent. In this step-1 session before the grant, capture current database, schema, table, sequence, routine and default ACLs, including any `PUBLIC EXECUTE`/`USAGE`, inheritance and effects on other services; stop for review if the explicit `PUBLIC` revokes below would remove another service's needed access. Any PUBLIC-granted sequence or routine right reaching `connector_runtime` must be accepted in writing or revoked by a separately reviewed change. Read `log_statement`, `log_min_duration_statement` and parameter/error logging controls. Generate an independent password and **client-side SCRAM-SHA-256 verifier** in a protected process; send only the verifier via protected environment/stdin, never plaintext in SQL, argv, history, logs or this spec. Confirm the server logs contain no credential material. Create `connector_runtime` as `LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS`. Substitute the verified database name for `railway` in the reviewed SQL.

   **Preflight result 2026-09-29:** `connector_runtime` is absent; `password_encryption=scram-sha-256`; `log_statement=none`; the 12 tables have no `PUBLIC` grants; existing default ACLs do not reach `connector_runtime`. The [read-only production preflight](/Users/max/koskadeux-state/connector-gate4-s1764/PREFLIGHT-STEP1-2026-09-29T1920Z.md) found that live login roles `issue_channel_queue_api` and `issue_channel_watcher` have no explicit `CONNECT` and rely on `PUBLIC CONNECT`. Revoking database access from `PUBLIC` would take those services offline, so the SQL below retains `PUBLIC CONNECT`; that grant gives no table access, while `connector_runtime` still receives explicit `CONNECT`. The database ACL also grants `TEMP` through `PUBLIC =Tc`; `connector_runtime` inherits it as an accepted residual, and TEMP grants no access to existing data. GLM's alternative of revoking `TEMP` now was considered and deferred because this preflight did not prove which live roles use TEMP. The same future PUBLIC-tightening change must first grant explicit `CONNECT` and, where proven needed, `TEMP` to every live login role before revoking either privilege from `PUBLIC`. The preflight did not capture sequence or routine ACLs; the step-1 session must capture them before the grant as required above.

   | Table | Exact runtime columns and verb | Read/write site on backend main |
   | --- | --- | --- |
   | `connector_audit_events` | `INSERT (id, occurred_at, event_type, outcome, event_count, request_id, trace_id, user_id, org_id, client_id, grant_id, profile, tool, scopes_used, error_code, policy_decision, pending_action_id, latency_ms, args_hmac, result_hmac, ip, user_agent_hmac, binding_terms)` | `connector_shared/audit.py` inserts only; operator readback uses owner role |
   | `connector_switches` | `SELECT (scope, key, disabled)` | `connector/switches.py` |
   | `connector_review_queue` | `INSERT (id, user_id, org_id, client_id, first_burst_at, last_burst_at, burst_count, throttle_until)`; `UPDATE (last_burst_at, burst_count, throttle_until)`; `SELECT (burst_count, reviewed_at)` | `connector/ratelimit.py` upsert reads existing `burst_count`; partial conflict predicate checks `reviewed_at` |
   | `connector_oauth_grants` | `SELECT (id, user_id, organization_id, client_id, scopes, profile, revoked_at, created_at)` | `connector_shared/oauth_store.py` active grant; `tools/account.py` grant display/join |
   | `connector_oauth_clients` | `SELECT (client_id, client_name)` | `tools/account.py` join/display; no secret or registration-IP hash |
   | `organization_memberships` | `SELECT (organization_id, user_id, status, role)` | `connector/auth.py`, `tools/account.py` |
   | `organizations` | `SELECT (id, name)` | `tools/account.py` |
   | `users` | `SELECT (id, display_name, email)` | `tools/account.py`; no credential/2FA columns |
   | `seller_profiles` | `SELECT (user_id)` | `tools/account.py` existence predicate |
   | `listings` | `SELECT (id, title, slug, description, short_description, category, price, privacy_score, compliance_status, data_format, source_row_count, tags, published_at, synthetic_queries, status, is_listed, license_code, license_version, license_params, license_sha256, covenant_sha256, seller_acceptance_id, seller_acceptance_source, license, schema_info, update_cadence_days)` | `listing_search_service.py` lexical/semantic/SQL fallback, licence attachment; `discovery/{visibility,projection}.py` detail. Keep `synthetic_queries`: the pinned backend baseline `66109cdc` connector `search_listings` calls `ListingSearchService`, which reads this column. |
   | `notifications` | `SELECT (id, type, created_at, read_at, user_id, archived_at)` | `discovery/activity.py` owner filter/order; no title/body/payload |
   | `data_requests` | `SELECT (id, title, description, categories, urgency, status, published_at, buyer_id, created_at)` | `discovery/requests.py` owner filter/order |

   SQL inside the owner `psql` session above, after the protected process has injected only `CONNECTOR_RUNTIME_SCRAM_VERIFIER` (never plaintext), is:

   ```sql
   \getenv scram_verifier CONNECTOR_RUNTIME_SCRAM_VERIFIER
   BEGIN;
   CREATE ROLE connector_runtime LOGIN NOINHERIT NOSUPERUSER NOCREATEDB
     NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'scram_verifier';
   REVOKE CREATE ON SCHEMA public FROM PUBLIC;
   REVOKE ALL ON connector_audit_events, connector_switches, connector_review_queue,
     connector_oauth_grants, connector_oauth_clients, organization_memberships,
     organizations, users, seller_profiles, listings, notifications, data_requests FROM PUBLIC;
   REVOKE ALL ON ALL TABLES IN SCHEMA public FROM connector_runtime;
   GRANT CONNECT ON DATABASE railway TO connector_runtime;
   GRANT USAGE ON SCHEMA public TO connector_runtime;
   GRANT INSERT (id, occurred_at, event_type, outcome, event_count, request_id,
     trace_id, user_id, org_id, client_id, grant_id, profile, tool, scopes_used,
     error_code, policy_decision, pending_action_id, latency_ms, args_hmac,
     result_hmac, ip, user_agent_hmac, binding_terms)
     ON connector_audit_events TO connector_runtime;
   GRANT SELECT (scope, key, disabled) ON connector_switches TO connector_runtime;
   GRANT INSERT (id, user_id, org_id, client_id, first_burst_at, last_burst_at,
     burst_count, throttle_until) ON connector_review_queue TO connector_runtime;
   GRANT UPDATE (last_burst_at, burst_count, throttle_until)
     ON connector_review_queue TO connector_runtime;
   GRANT SELECT (burst_count, reviewed_at) ON connector_review_queue TO connector_runtime;
   GRANT SELECT (id, user_id, organization_id, client_id, scopes, profile,
     revoked_at, created_at) ON connector_oauth_grants TO connector_runtime;
   GRANT SELECT (client_id, client_name) ON connector_oauth_clients TO connector_runtime;
   GRANT SELECT (organization_id, user_id, status, role)
     ON organization_memberships TO connector_runtime;
   GRANT SELECT (id, name) ON organizations TO connector_runtime;
   GRANT SELECT (id, display_name, email) ON users TO connector_runtime;
   GRANT SELECT (user_id) ON seller_profiles TO connector_runtime;
   GRANT SELECT (id, title, slug, description, short_description, category, price,
     privacy_score, compliance_status, data_format, source_row_count, tags,
     published_at, synthetic_queries, status, is_listed, license_code,
     license_version, license_params, license_sha256, covenant_sha256,
     seller_acceptance_id, seller_acceptance_source, license, schema_info,
     update_cadence_days) ON listings TO connector_runtime;
   GRANT SELECT (id, type, created_at, read_at, user_id, archived_at)
     ON notifications TO connector_runtime;
   GRANT SELECT (id, title, description, categories, urgency, status,
     published_at, buyer_id, created_at) ON data_requests TO connector_runtime;
   COMMIT;
   ```

   If the role exists, stop rather than replace it. Do not give ownership, blanket/default grants, `SET ROLE`, or schema creation. Keep the **84-boolean** `has_table_privilege` probe over these 12 tables × `SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER`; with column grants all 84 **table-level** results must be false:

   ```sql
   SELECT t.name, p.verb,
          has_table_privilege('connector_runtime', ('public.' || t.name)::regclass, p.verb)
   FROM (VALUES ('connector_audit_events'),('connector_switches'),('connector_review_queue'),
     ('connector_oauth_grants'),('connector_oauth_clients'),('organization_memberships'),
     ('organizations'),('users'),('seller_profiles'),('listings'),('notifications'),
     ('data_requests')) AS t(name)
   CROSS JOIN (VALUES ('SELECT'),('INSERT'),('UPDATE'),('DELETE'),('TRUNCATE'),
     ('REFERENCES'),('TRIGGER')) AS p(verb) ORDER BY 1,2;
   SELECT c.table_name, c.column_name, p.verb,
          has_column_privilege('connector_runtime',
            ('public.' || c.table_name)::regclass, c.column_name, p.verb)
   FROM information_schema.columns c
   JOIN (VALUES ('connector_audit_events'),('connector_switches'),('connector_review_queue'),
     ('connector_oauth_grants'),('connector_oauth_clients'),('organization_memberships'),
     ('organizations'),('users'),('seller_profiles'),('listings'),('notifications'),
     ('data_requests')) AS t(name) ON t.name = c.table_name
   CROSS JOIN (VALUES ('SELECT'),('INSERT'),('UPDATE')) AS p(verb)
   WHERE c.table_schema='public' ORDER BY 1,2,3;
   ```

   Compare every column/verb to the matrix, requiring every omitted grant false. In particular `users.password_hash`, `users.totp_secret_enc`, `users.backup_codes_hash`, `connector_oauth_clients.client_secret_hash`, `connector_oauth_clients.registration_ip_hash`, notifications `title/body/metadata` and OAuth token columns must return false (use `pg_attribute` to distinguish a missing column from an ACL pass). Prove audit `INSERT=true` through `has_column_privilege` for all inserted columns, audit `SELECT=false`, and `UPDATE/DELETE/TRUNCATE=false` for runtime, `ai_market_app` and `PUBLIC`. Also record `has_database_privilege` (`CONNECT=true`, `CREATE=false`, `TEMP=true` inherited from `PUBLIC =Tc` as the accepted residual), `has_schema_privilege` (`USAGE=true`, `CREATE=false`), default ACLs, and effective sequence/routine access, including PUBLIC-granted rights; any unintended inherited right stops. Connect as runtime and test each positive query and an audit insert inside a rollback-only transaction; negative sensitive-column and mutation queries must report permission denied. Recheck after every migration.

   **Row boundary:** column grants do not stop this credential from querying another user's permitted `email`, notification/request rows, or unpublished listing columns. The current SQL applies principal/visibility predicates in the handlers, with no connector RLS. Before production enable, require a reviewed database-enforced principal/public-visibility boundary with real-Postgres negative probes for another user's account/feed/request and an unpublished or unlicensed listing, **or** explicit owner acceptance in the change ticket of this remaining row-wide read risk after a red-team review. If accepted, record that direct runtime SQL can read those rows; only handler-level cross-user/visibility negatives are claimed. No grant widening to solve a query failure. Rollback: global switch disabled, remove resource `DATABASE_URL`, revoke this role's column grants and `CONNECT`, then `ALTER ROLE connector_runtime NOLOGIN`; keep audit rows.

2. **Railway and Infisical variables.** Build the restricted DSN using the role credential without displaying it, and set `DATABASE_URL` on **`ai-market-connector` only** via Railway service variable; do not use the owner/app DSN. Set `REDIS_URL` as a Railway reference to the existing production Redis service, also resource only. Confirm reference target and effective reachability with names-only Railway GraphQL readback and `/readyz` dependency checks; do not store either URL in Infisical. Create distinct `SECRET_KEY` values for auth and resource and `CONNECTOR_AUDIT_HMAC_KEY` for resource in `ai-market-backend`/`prod` under `/connector-auth` and a new `/connector-resource` folder respectively, through a reviewed scoped secret procedure (the generic local-secops executor does not manage `/connector-auth`). Keep the existing auth signing keyset and sync unchanged. Prove the new resource folder cannot recurse into `railway-backend-prod` or `railway-connector-auth-prod` with a disposable canary before creating `railway-connector-resource-prod`, targeted only at `ai-market-connector`, auto-sync on, overwrite destination, deletion disabled; then remove the canary by reviewed procedure. Names-only readback must show auth has its own `SECRET_KEY` and `CONNECTOR_OAUTH_SIGNING_KEYS`, resource has its different `SECRET_KEY` and audit HMAC key, and resource lacks signing keys; compare secret fingerprints in a protected process without outputting values. Export each connector folder's **key names** and assert neither contains `DATABASE_URL` or `REDIS_URL`; read back Railway key names and references. Verify canonical issuer/audience/JWKS URLs, `CONNECTOR_EXPECTED_PROCESSES=4` for 2 replicas × 2 workers, `CONNECTOR_AUTH_FAILURE_MAX_IPS>=1`, and `OTEL_SERVICE_NAME=ai-market-connector`. Rollback: turn flags off, remove resource Railway DSN/Redis references, disable only the new scoped resource sync and revoke resource secrets through its reviewed procedure; do not delete the signing keyset.

3. **Trusted edge peer.** With flags off, instrument a temporary *redacted* request-ID diagnostic at the resource edge (or use a reviewed existing equivalent) to record socket peer, full XFF hop count, and selected limiter IP for controlled requests; never log customer headers/IPs generally. Sample multiple real Railway edge requests from two controlled external source IPs and both replicas. Compare socket peers and Railway edge documentation/support evidence; choose the narrow actual peer CIDR(s), not all RFC1918 or Cloudflare ranges, then set `CONNECTOR_TRUSTED_PROXY_CIDRS` on the resource. Backend main `asgi.py::_edge_status` walks XFF **right to left** and selects the first untrusted hop; that selected `state.client_ip` feeds the pre-auth `ip` limiter and auth-failure audit. Probe ordinary traffic and forged `X-Forwarded-For: 1.2.3.4` from each source. **Only pass** if the measured Railway edge appends the true external caller to the right and the selected limiter bucket stays that caller, not `1.2.3.4`; do not assume edge header behavior. Also probe an untrusted direct peer and invalid XFF, which must use socket peer; record an all-trusted-hop case if observed. Record actual hop, peer ranges, request IDs and limiter bucket evidence with IPs redacted. Rollback: clear the CIDR variable and turn the global switch off until rate-limit attribution is repaired.

4. **Audit alert.** The backend OTel code exports only when `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS` are configured; `connector/telemetry.py` defines counters but no rule. Verify live Grafana Cloud ingestion for resource service `ai-market-connector` and both counters. Scope both queries to the verified service label, then install `sum(increase(connector_audit_write_failures_total[5m])) / clamp_min(sum(increase(connector_requests_total{method="tools/call"}[5m])), 1) > 0.001` across all replicas/workers, plus `sum(increase(connector_audit_write_failures_total[5m])) > 0` for low-volume failures. Add a no-data/stale-ingestion alert. Route to the existing issue channel with service, window, counts and dashboard link, no payload. Inject a controlled failure on a noncustomer test host; prove one ticket, a zero-volume/no-data ticket and recovery. If Grafana ingestion/routing is unavailable, **stop enable** until a reviewed fallback exists: add a redacted structured audit-write outcome log at the same `record_read`/`record_auth_failure`/required-write failure sites and a redacted `tools/call` count log; ship both to a verified central log store. A dedicated authenticated scheduled job (record its service identity and least-privilege log-read/issue-write credentials) queries five-minute `audit_failure` and `tools_call` counts there each minute, applies the same aggregate ratio and nonzero-failure rule, and opens/deduplicates the same issue-channel ticket. Alert on missing log ingestion for two collection periods or job/query/delivery failure through an independent job-health route; test those paths and recovery before enable. There is no resource `/metrics` endpoint, so a collector cannot scrape these counters as-is. A draft rule or local log line fails the gate. Rollback: global off, disable alert route only after calls stop; preserve tickets.

5. **D2 runtime and test-host proof, then readiness.** Before production D2 switches, provision connector-scoped `LISTING_LICENSES_ENABLED` matching the backend's effective value and, when true, `TERMS_1_1_EFFECTIVE_AT` (also verify `X402_ENABLED=false`); `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_API_KEY`, `SEARCH_SCORE_THRESHOLD`; `VERTEX_GEMINI_KEY`, `VERTEX_EMBEDDING_LOCATION`, `LLM_EMBEDDING_MODEL`, `LLM_EMBEDDING_DIMENSIONS` matching the indexed collection. Read back names, nonsecret values and secret fingerprints only. Backend main's lazy D2 import still loads `app.core.config`, whose Railway validation also demands nondefault `DOWNLOAD_TOKEN_SECRET_KEY` and `INTERNAL_API_KEY`. Do **not** copy those unrelated backend credentials: a separately reviewed/deployed connector-minimal settings/import change must remove that dependency, or D2 remains disabled. On a noncustomer test host with representative licensed/incomplete fixtures, a controlled grant and D2 switches enabled **there only**, prove semantic and degraded `search_listings` (`hybrid`/`lexical` and `sql_fallback` as applicable), `get_listing`, and indistinguishable `NOT_FOUND` for published-but-ineligible and unpublished listings; compare production visibility policy and ensure no valid call returns `TEMPORARILY_UNAVAILABLE`. Record exact image/config identity and query/fixture IDs before any production D2 switch. Then set Railway resource `healthcheckPath=/readyz` (auth stays `/readyz`) in the same provisioning window, redeploy the pinned image with all four flags false, and require both replicas healthy, `/healthz` 200, `/readyz` **200** (DB, four tables, Redis, audit sink), protected metadata 200 and `/mcp` 503 `CONNECTOR_DISABLED`. Confirm connection headroom. Rollback: keep flags false, remove failing reference or revert resource image **and its prior healthcheckPath**; `/healthz` is temporary repair status, never enable evidence.

6. **Reviewer data and allowlist.** Max approves the synthetic email/display name, data provenance and who holds its password. Register a fresh **password-login** account through normal verified-email/onboarding flow, enable 2FA if required, and test consent assurance; do not use SSO until T-2026-000879 closes. Use synthetic, labeled production-safe fixtures through normal product flows: two published visible listings, one own published request, a safe notification, and a legitimately owned completed order; record IDs and ownership, not personal data. Identify Max and existing test accounts by verified `users.id` UUIDs. Set `CONNECTOR_EARLY_ACCESS_USER_IDS` on **every consent, token/refresh and resource enforcement service**, verify hash/count readback, then prove an excluded existing user cannot consent, exchange a previously issued code, refresh an existing token or call with a preexisting grant; included accounts pass. **No enable if the code gap remains.** Rollback: global off, remove reviewer UUID on every enforcing service, restart/redeploy as needed and revoke grants; verify all four negative paths. Retain fixtures under the approved retention procedure.
   Set `CONNECTOR_EARLY_ACCESS_USER_IDS` and `CONNECTOR_EARLY_ACCESS_ENFORCED` identically as process environment values on `ai-market-backend` (website consent API), `ai-market-connector-auth` and `ai-market-connector`, and restart all three after changing either value before treating the change as effective (backend PR #540 early-access erratum; GLM LOW 2). Public opening later follows core Gate 1 §9 step 5 by explicitly setting `CONNECTOR_EARLY_ACCESS_ENFORCED=false` on all three services and restarting them; an empty list while enforcement is true denies everyone.

7. **Enable one gate at a time.** Use owner-session SQL from `customer-mcp-connector.md` switch administration; keep exact `(scope,key)` rows, actor, reason, affected-row count `1`, and five-second cache/ten-second observed deadline. Prestage `('global','global')`, `('profile','default')`, `('profile','claude')`, `('profile','openai')` and each registered discovery tool as `disabled=true`; never rely on absent rows. `get_my_account` has no explicit-switch requirement, so create and control its tool row too. D2/D3 four reads (`search_listings`, `get_listing`, `get_activity`, `list_data_requests`) require explicit enabled rows. Keep `ask_allai` absent/disabled. Verify resource and auth flags false before each step.

   1. Enable `CONNECTOR_OAUTH_ENABLED=true` on auth/backend/website consent owners, leaving resource global off; enable `CONNECTOR_CIMD_ENABLED=true` only after reviewed Claude CIMD URL, live document, SHA-256 pin and redirect match; enable `CONNECTOR_DCR_ENABLED=true` for the default-profile test path. Confirm AS metadata 200 (`client_id_metadata_document_supported`, PKCE, revocation), public-only JWKS 200, DCR rejects disallowed redirect and rate-limit excess, and Claude CIMD resolves to a **verified `claude`** grant while DCR stays `default`. Roll back each flag to false if its probe fails.
   2. With global DB row still disabled, set `CONNECTOR_ENABLED=true` on resource; require `/readyz` 200 and `/mcp` `CONNECTOR_DISABLED`. Use the real Claude client for consent and token exchange: browser shows client name/host, scopes and Personal account; approve yields single-use code, token has correct issuer/audience/scopes; deny/replay/expired code fail. Prove T-879 policy plus excluded-user refusal at consent, code exchange, refresh and resource. Rollback: `CONNECTOR_ENABLED=false` and restart resource.
   3. Enable only `('profile','default')` and `('profile','claude')`, then set `('global','global')` `disabled=false` while **all tool rows remain disabled**; confirm empty `tools/list`. Enable `('tool','get_my_account')`, then the four discovery tool rows **one at a time**; `search_listings`/`get_listing` stay disabled until step 5's exact test-host D2 receipt passes. Keep `openai` profile disabled unless its separate client proof is requested. For each change, read exact row and `tools/list` from a new Claude/default grant; verify profile-specific schema and exact names. For every listed tool, run valid input returning real reviewer data and invalid input returning a specific `INVALID_ARGUMENT` pointer; check `NOT_FOUND` for unknown listing, `TOOL_DISABLED`/`TOOL_NOT_AVAILABLE` for killed/unknown tool, `INSUFFICIENT_SCOPE` for under-scoped grant, 401 `AUTH_REQUIRED`, and 429 `RATE_LIMITED` with retry seconds. Verify one `tool.call` row for each call with request/trace/grant/tool/outcome and HMAC only, no raw args/results. Probe pre-auth 60/min/IP, read 120/min/user and search 600/hour/client-user on a controlled test account without exhausting customer buckets. A failed smoke disables the just-enabled row, then global if behavior persists.
   4. Drill the global kill by `UPDATE connector_switches SET disabled=true, reason=..., actor=..., updated_at=now() WHERE scope='global' AND key='global'` in the credentialed owner session. Require `CONNECTOR_DISABLED` on all replicas within **10 seconds** (five-second snapshot plus propagation), including a previously valid token; restore only after ticket review. Revoke the reviewer grant through Connected apps/dashboard, verify next call 401 and refresh refusal, then re-consent if needed. Exercise resource env-floor kill `CONNECTOR_ENABLED=false` and restore only after all checks. Keep AS JWKS reachable during a resource kill.

8. **Directory handoff.** First submission contains `get_my_account` and D1–D3's four read-only discovery tools, with real valid/invalid reviewer results. Add `ask_allai` only if D4 has merged, its budget migration and model usage/neutrality/concurrency gates have passed, `CONNECTOR_ALLAI_MODEL=gpt-5.6-luna` per Max Event `c3dd857b`, exact current **OpenAI list prices** and provider-enforced input/output/thinking/cache/retry bounds are recorded, and its own disabled switch is enabled after a live priced call. Default caps remain 20 calls/user-client UTC day and USD 5/day, fallback models empty; otherwise it is absent from `tools/list`. Max approves professional listing copy, public Claude use docs, connector privacy wording, support contact, icon, categories, permanent slug and allowed link URIs, then submits through the ai.market Claude organization. The portal must connect to the live server and sync precisely the approved tool list. Record portal submission ID/status; do not claim Anthropic Verified until Anthropic grants it.

## Rollback command map and records

| Layer | First rollback action | Verification |
| --- | --- | --- |
| Global DB kill | Owner `psql` exact-row `UPDATE connector_switches SET disabled=true, reason='S1764 rollback', actor=:'actor', updated_at=now() WHERE scope='global' AND key='global';` | one row; all replicas return `CONNECTOR_DISABLED` within 10 s |
| Profile/tool | Same exact-row `UPDATE` with `scope='profile'/'tool'` and approved key | `tools/list` and call removed within 10 s |
| Resource env | Railway resource `CONNECTOR_ENABLED=false`, redeploy/restart | `/mcp` disabled; `/readyz` remains 200 if dependencies healthy |
| Auth env | Railway auth/backend `CONNECTOR_OAUTH_ENABLED=false`, `CONNECTOR_CIMD_ENABLED=false`, `CONNECTOR_DCR_ENABLED=false` | metadata/endpoints gated, JWKS still public; existing resource tokens need global kill too |
| Early-access allowlist | Global kill first; remove reviewer UUID from `CONNECTOR_EARLY_ACCESS_USER_IDS` on every consent, token/refresh and resource enforcer, redeploy/restart, revoke its grants | hash/count readback; excluded account refused at consent, token, refresh and resource, including old grant |
| Credential/data | Remove resource Railway DSN/reference, `ALTER ROLE connector_runtime NOLOGIN` after global kill; revoke grant via Connected apps | no new DB session/grant; preserve audit and migration tables |
| Image/config | Redeploy prior exact resource/auth SHA and restore prior Railway config and `healthcheckPath` only after flags/global off | health, key-name isolation and disabled response |

Update `customer-mcp-connector.md` and `infisical-secrets.md` after actual execution with role/ACL proof, edge CIDR and hop, sync IDs, alert rule and issue-channel test, readiness, allowlist enforcement SHA, switch/flag order, reviewer fixture IDs (private receipt), kill/revoke timing and current directory status. Log Event Ledger entries for preflight decision, each provisioning stage, failed/retried step, enable, rollback drill, Max approvals and submission; link them and the change ticket in the runbook. A draft PR for this **plan** is not an enable receipt.

## Gate 4 STEP 2 operator procedure — secrets and variables (S1764)

**Procedure only, not an execution receipt.** Step 1 completed 2026-09-29 (Event `2c4998ed`): `connector_runtime` exists; its password lives only in the Titan-1 macOS keychain (`keyring`, service `ai-market-connector-runtime-db`, account `connector_runtime`). Recheck Step 1's privilege evidence before provisioning. Keep the global connector switch and all four connector flags off. Use the S1764 ticket and the rollback map above. Record actor, timestamp, before/after *names or IDs only*, sync job IDs, deployment IDs and an immediate rollback for each mutation. Disable tracing (`set +x`), set `umask 077`, and suppress HTTP error bodies and debug logging. Never put a DSN, token, key or password in argv, a shell trace, a log, Git, or a receipt.

### 2.0 Preflight and API session

Re-read `customer-mcp-connector.md` (environment table, Signing keyset DONE, and `railway-connector-auth-prod`) and `infisical-secrets.md`. Verify live Railway project `ai-market` `e81dd66f-808c-412e-b32c-f6d910f0ac5d`, production environment `23e322c3-b195-45d8-9151-c4c27a998c33`, and services: backend `4a68ea36-41de-4300-9bab-48e506b0dba6`, resource `a08ef347-d2d1-4fcb-ba50-9299a9484fd5`, auth `5ee110fc-df73-4107-b8fd-469099cb64d2`. Infisical project is `ai-market-backend` `bd272d48-c5a1-4b52-9d24-12066ae4403c`, env `prod`, API `https://secrets.ai.market`. Refuse a mismatch or `/Users/max/local-secops/HALT`. From the linked Railway operator directory, `rtk railway status --json` must show those IDs; Railway CLI 4.30.3 has no project selector for `status`. `rtk railway variables --service <service-id> --environment <environment-id> --json` is a read only, value-bearing command: capture and parse its stdout inside the protected Python process, never print it.

Refresh Infisical's short-lived Universal Auth JWT using `rtk proxy ~/bin/infisical_auth_refresh.sh >/dev/null 2>&1`; source `~/bin/railway-env.sh` with output suppressed, then `unset RAILWAY_TOKEN`. Load `~/.config/infisical/sysadmin-token` and ambient `RAILWAY_API_TOKEN` in the protected Python process, not on a command line. The following snippets use one protected interpreter session; no helper file is installed. They reuse `koskadeux-mcp/scripts/connector_keyset/connector_signing_keyset.py`'s `Client.request`, secret list, sync inventory and payload shapes. Turn off urllib/requests debugging, catch failures without printing response bodies, and never print `values()`, `rv()`, `gql()` or their raw results.

```python
import hashlib, json, os, secrets, subprocess, urllib.parse, urllib.request
from pathlib import Path
P='bd272d48-c5a1-4b52-9d24-12066ae4403c'; E='prod'
RP='e81dd66f-808c-412e-b32c-f6d910f0ac5d'
RE='23e322c3-b195-45d8-9151-c4c27a998c33'
BACK='4a68ea36-41de-4300-9bab-48e506b0dba6'
RES='a08ef347-d2d1-4fcb-ba50-9299a9484fd5'
AUTH='5ee110fc-df73-4107-b8fd-469099cb64d2'
assert not Path('/Users/max/local-secops/HALT').exists()
IT=Path.home().joinpath('.config/infisical/sysadmin-token').read_text().strip()
RT=os.environ['RAILWAY_API_TOKEN']; assert IT and RT

def api(method,path,query=None,body=None):
    url='https://secrets.ai.market'+path
    if query: url+='?'+urllib.parse.urlencode(query)
    req=urllib.request.Request(url,method=method,
      data=None if body is None else json.dumps(body,separators=(',',':')).encode(),
      headers={'Authorization':'Bearer '+IT,'User-Agent':'connector-step2/1.0',
               **({'Content-Type':'application/json'} if body is not None else {})})
    with urllib.request.urlopen(req,timeout=30) as response: return json.load(response)

def gql(query,variables):
    req=urllib.request.Request('https://backboard.railway.app/graphql/v2',
      data=json.dumps({'query':query,'variables':variables},separators=(',',':')).encode(),
      headers={'Authorization':'Bearer '+RT,'Content-Type':'application/json',
               'User-Agent':'Mozilla/5.0 (S1764 operator)'})
    with urllib.request.urlopen(req,timeout=30) as response: result=json.load(response)
    if result.get('errors'): raise RuntimeError('Railway GraphQL error; body suppressed')
    return result['data']

def folder(path,show_values=False):
    rows=api('GET','/api/v4/secrets',{'projectId':P,'environment':E,
      'secretPath':path,'viewSecretValue':str(show_values).lower(),
      'recursive':'false','includeImports':'false',
      'expandSecretReferences':'false'})['secrets']
    assert all(r.get('type')=='shared' for r in rows)
    out={r['secretKey']:(r['secretValue'] if show_values else None) for r in rows}
    assert len(out)==len(rows)
    return out

def syncs(): return api('GET','/api/v1/secret-syncs',{'projectId':P})['secretSyncs']

def rv(service):
    assert service in (BACK,RES,AUTH)
    p=subprocess.run(['/opt/homebrew/bin/railway','variables','--service',service,
      '--environment',RE,'--json'],capture_output=True,text=True,check=True,
      cwd='/Users/max/Projects/ai-market/ai-market-backend')
    return json.loads(p.stdout)  # value-bearing; never print

def put(service,items):
    assert service in (BACK,RES,AUTH)
    q='mutation($input:VariableCollectionUpsertInput!){variableCollectionUpsert(input:$input)}'
    return gql(q,{'input':{'projectId':RP,'environmentId':RE,'serviceId':service,
                           'variables':items,'skipDeploys':True}})
```

**UNVERIFIED Railway schema:** The runbooks confirm `variableCollectionUpsert(skipDeploys:true)` but do not preserve the full current `VariableCollectionUpsertInput` signature. Before the first write, introspect `__type(name:"VariableCollectionUpsertInput")` and the mutation arguments (names/types only); compare them with `put()` and adjust only the input envelope if necessary. The existing backend `app/agents/sysadmin/skills/railway_ops.py` is a second local example. Abort on an unknown shape. After every `put()`, assert the target value equals `rv(service)[name]` *in process*, print only `service-id name MATCH`, and verify deployment IDs did not change. A value-bearing readback is never written to disk. For raw service-reference metadata and `variableDelete`, introspect their current Railway GraphQL shapes before use; their exact schema is **UNVERIFIED** by the supplied runbooks.

**Native sync restart stop gate.** Railway `skipDeploys:true` applies to GraphQL variable mutations. `infisical-secrets.md` records that a `prod` secret write re-pushes syncs and redeploys the backend; S1753 records auth redeploys from sync creation and the signing-key write. No source proves native sync can stage changes without restarting. Before any Infisical write or forced sync, prove in a disposable nonproduction setup of the same native-sync version that these operations preserve destination deployment IDs, or obtain a reviewed amendment that moves those writes to Step 5. If neither is available, **stop Step 2 here**. Do not label a sync-driven restart as `skipDeploys` compliant. The canary forced sync can itself restart backend/auth.

### 2.1 Restricted resource DSN and Redis

Read the owner `AUTHOR_DISPATCH_DATABASE_URL` from Infisical root in the *same protected process* using `folder('/',True)` (the `schema-migration.md` §S.7a credential source). Parse only its host, port, database path and TLS query; get the Step 1 password through Python `keyring`. Refuse missing password, malformed URI, an unverified database/host, or a URL that does not decode to user `connector_runtime`. Never use the owner username/password in the result. The owner DSN, derived DSN and Railway request exist only in memory; no shell substitution, SQL literal, CLI `--set` or secret in argv.

```python
import keyring
from urllib.parse import urlsplit,urlunsplit,quote
owner=folder('/',True)['AUTHOR_DISPATCH_DATABASE_URL']
u=urlsplit(owner); pw=keyring.get_password('ai-market-connector-runtime-db','connector_runtime')
assert u.scheme in ('postgres','postgresql') and u.hostname and u.path not in ('','/') and pw
host=u.hostname if ':' not in u.hostname else '['+u.hostname+']'
netloc='connector_runtime:'+quote(pw,safe='')+'@'+host
if u.port: netloc+=':'+str(u.port)
dsn=urlunsplit((u.scheme,netloc,u.path,u.query,''))
assert urlsplit(dsn).username=='connector_runtime'
del owner,pw
assert 'DATABASE_URL' not in rv(RES)  # if present, investigate; do not overwrite
put(RES,{'DATABASE_URL':dsn})
assert rv(RES).get('DATABASE_URL')==dsn
print(RES,'DATABASE_URL MATCH')
del dsn,u,netloc
```

Inspect the live production Redis service name, ID and `REDIS_URL` in Railway before setting the reference. **UNVERIFIED:** these runbooks do not prove that the service is literally `Redis`, or that another service currently uses `${{Redis.REDIS_URL}}`. If the live service name and reference form match, call `put(RES,{'REDIS_URL':'${{Redis.REDIS_URL}}'})`; otherwise substitute the verified service name in Railway's reference syntax. Read back the raw reference through Railway GraphQL variable metadata or UI, check the effective `REDIS_URL` is present in `rv(RES)` without printing it, and confirm this action did not add the name to auth/backend. `/readyz` reachability is proved after the Step 5 restart, not by this readback. Neither URL belongs in Infisical.

### 2.2 Canary, distinct secrets and resource sync

Capture names from `folder('/')`, `folder('/connector-auth')`, `folder('/connector-resource')` if present, `rv()` for all three services, and `syncs()`. Require the auth folder already contains `CONNECTOR_OAUTH_SIGNING_KEYS`, no new `SECRET_KEY`, and the resource folder is absent or empty; investigate any drift before writing. Require neither connector folder has `DATABASE_URL` or `REDIS_URL`. Verify root `railway-backend-prod` and `railway-connector-auth-prod` paths, connection ID, auto-sync, `disableSecretDeletion`, destination IDs and non-recursion against `connector_signing_keyset.py` `require_syncs()`; do not call its `generate` or `create-sync` because the signing keyset and auth sync already exist.

Use `POST /api/v2/folders` body `{'projectId':P,'environment':E,'name':'connector-resource','path':'/'}` only if absent. Write a disposable random value via `POST /api/v4/secrets/CONNECTOR_RESOURCE_CANARY_S1764`, body `{'projectId':P,'environment':E,'secretPath':'/connector-resource','secretValue':secrets.token_urlsafe(32),'skipMultilineEncoding':True,'type':'shared'}`. Do not print the value. Force **each** existing sync, one at a time, with bodiless `POST /api/v1/secret-syncs/railway/<sync-id>/sync-secrets` (no `Content-Type`); poll `syncs()` until a new `lastSyncJobId` has `syncStatus` `success` or `succeeded`. Require the canary name absent from `rv(BACK)`, `rv(AUTH)` and `rv(RES)`. A leaked name stops the procedure and triggers the canary rollback. Save the root/auth sync job IDs, versions and service deployment IDs in the ticket. This is the disposable non-recursion proof for the *current* shapes, not a permanent assertion about future sync versions.

Then create the resource native sync using the exact `connector_signing_keyset.py` payload pattern and the verified root `connectionId`:

```python
root=next(r for r in syncs() if r['name']=='railway-backend-prod')
payload={'name':'railway-connector-resource-prod','projectId':P,
 'connectionId':root['connectionId'],'environment':E,'secretPath':'/connector-resource',
 'isAutoSyncEnabled':True,
 'syncOptions':{'initialSyncBehavior':'overwrite-destination',
                'includeAllSubFolders':False,'disableSecretDeletion':True},
 'destinationConfig':{'projectId':RP,'projectName':'ai-market',
   'environmentId':RE,'environmentName':'production',
   'serviceId':RES,'serviceName':'ai-market-connector'}}
api('POST','/api/v1/secret-syncs/railway',body=payload)
```

Read back sync ID, source path/env, connection, target ID, auto-sync and options. If readback omits `includeAllSubFolders`, accept only this exact pinned shape plus the just-completed canary proof; unknown/enabled recursion stops. Wait for the new sync job and require the canary on resource **only**. Generate three independent `secrets.token_urlsafe(48)` values in process; write `SECRET_KEY` to `/connector-auth`, a different `SECRET_KEY` and `CONNECTOR_AUDIT_HMAC_KEY` to `/connector-resource`, each by `POST /api/v4/secrets/<name>` with `projectId`, `environment`, exact `secretPath`, `secretValue`, `skipMultilineEncoding=True`, `type='shared'`. Write one at a time, wait for the corresponding sync job to succeed, check names/fingerprints, and receipt each separately. Never change `CONNECTOR_OAUTH_SIGNING_KEYS` or its auth sync. Do not create a root sync or use local-secops' generic executor for `/connector-auth`.

Remove the canary with `DELETE /api/v4/secrets/CONNECTOR_RESOURCE_CANARY_S1764`, body `{'projectId':P,'environment':E,'secretPath':'/connector-resource','type':'shared'}`. Since deletion is disabled for the sync, also delete the resource Railway canary variable by `variableDelete(input:$input)` with its introspected input shape, or `rtk railway variable delete CONNECTOR_RESOURCE_CANARY_S1764 --service <resource-id> --environment <environment-id> --json` (argv contains only the disposable name). Require source and all three Railway services to lack the name. Do not leave the canary as a permanent variable.

### 2.3 Remaining variables and readback

With `put()` and `skipDeploys:true`, set resource `CONNECTOR_EXPECTED_PROCESSES=4` after verifying 2 replicas × `CONNECTOR_WORKERS=2`; set `CONNECTOR_AUTH_FAILURE_MAX_IPS=10000` (documented default, integer >=1), and `OTEL_SERVICE_NAME=ai-market-connector`. Read back existing resource `CONNECTOR_AUTH_ISSUER=https://auth.ai.market`, `CONNECTOR_AUDIENCE=https://connect.ai.market/mcp`, `CONNECTOR_JWKS_URL=https://auth.ai.market/.well-known/jwks.json`; repair any drift via `put()` and record it. On **each** of backend, auth and resource, set `CONNECTOR_EARLY_ACCESS_ENFORCED=true` and `CONNECTOR_EARLY_ACCESS_USER_IDS=''` with `put()`. Verify exact values on all three and record only the count `0` and a protected in-process comparison to the SHA-256 of the empty string. Empty plus enforcement true admits nobody. Step 6 supplies UUIDs identically to all three, restarts them and proves the negative paths. Recalculate expected processes after any resource scale change.

Final names-only proof: `/connector-auth` has `SECRET_KEY` and `CONNECTOR_OAUTH_SIGNING_KEYS`, but no audit key or URLs; `/connector-resource` has `SECRET_KEY` and `CONNECTOR_AUDIT_HMAC_KEY`, but no signing key or URLs. Check backend has no new connector key names, auth lacks the resource audit key, and resource lacks signing keys. In protected memory compare `hashlib.sha256(source.encode()).digest()` with each destination secret, and prove the two `SECRET_KEY` digests differ; output only `MATCH`/`DIFFERENT`, no values or hashes. Check the existing public JWKS thumbprints against `customer-mcp-connector.md`. Compare source/root names and all deployment IDs with baseline. Any unexpected name, sync scope, value mismatch or restart fails Step 2. Runtime `/readyz` and dependency reachability are Step 5 proofs.

Independently export **key names only** from each connector path, following `infisical-secrets.md`'s JSON-array rule. Run the Infisical CLI as a Python subprocess with `INFISICAL_TOKEN` in its environment (never `--token`), `--domain=https://secrets.ai.market`, `--projectId=P`, `--env=prod`, `--path=/connector-auth` or `/connector-resource`, `--format=json`, `--silent`; capture stdout in memory and emit only `sorted(r['key'] for r in json.loads(stdout))`. Assert neither set contains `DATABASE_URL` or `REDIS_URL`. Do not redirect raw JSON to a file or paste it into a ticket. Compare those names with the API names and destination names. In that same protected process, apply the following exact checks without printing values:

```python
def exported_names(path):
    env={**os.environ,'INFISICAL_TOKEN':IT,'INFISICAL_API_URL':'https://secrets.ai.market'}
    p=subprocess.run(['/opt/homebrew/bin/infisical','export','--domain=https://secrets.ai.market',
      '--projectId='+P,'--env=prod','--path='+path,'--format=json','--silent'],
      env=env,capture_output=True,text=True,check=True)
    rows=json.loads(p.stdout)
    assert isinstance(rows,list)
    return {r['key'] for r in rows}
for path in ('/connector-auth','/connector-resource'):
    keys=exported_names(path)
    assert keys==set(folder(path)) and not keys.intersection({'DATABASE_URL','REDIS_URL'})
    print(path,sorted(keys))
srca=folder('/connector-auth',True); srcr=folder('/connector-resource',True)
dst_a=rv(AUTH); dst_r=rv(RES)
for k in ('SECRET_KEY','CONNECTOR_OAUTH_SIGNING_KEYS'):
    assert hashlib.sha256(srca[k].encode()).digest()==hashlib.sha256(dst_a[k].encode()).digest()
    print(AUTH,k,'MATCH')
for k in ('SECRET_KEY','CONNECTOR_AUDIT_HMAC_KEY'):
    assert hashlib.sha256(srcr[k].encode()).digest()==hashlib.sha256(dst_r[k].encode()).digest()
    print(RES,k,'MATCH')
assert hashlib.sha256(srca['SECRET_KEY'].encode()).digest()!=hashlib.sha256(srcr['SECRET_KEY'].encode()).digest()
print('SECRET_KEY','DIFFERENT')
assert 'CONNECTOR_OAUTH_SIGNING_KEYS' not in dst_r
assert 'CONNECTOR_AUDIT_HMAC_KEY' not in dst_a
del srca,srcr,dst_a,dst_r
```

### 2.4 Per-action rollback

Before deletion, introspect the Railway `VariableDeleteInput` shape; if it lacks `skipDeploys`, the no-restart property of deletion is **UNVERIFIED** and requires a reviewed timing decision. With `disableSecretDeletion=true`, deleting an Infisical secret or sync does not delete its Railway copy: explicitly revoke both sides. Keep global switch/flags off throughout. If flags were later enabled, use the rollback map's global kill first.

The existing `scripts/railway_watcher_credential/railway_watcher_credential.py` uses `gql('mutation($input:VariableDeleteInput!){variableDelete(input:$input)}', {'input':{'projectId':RP,'environmentId':RE,'serviceId':RES,'name':'CONNECTOR_RESOURCE_CANARY_S1764'}})` for a single name. Use the same call for the table's target service/name after introspection; it does **not** show `skipDeploys`, so treat a deletion-triggered deployment as possible. Infisical secret deletion is `api('DELETE','/api/v4/secrets/'+name,body={'projectId':P,'environment':E,'secretPath':path,'type':'shared'})`. Sync deletion is `api('DELETE','/api/v1/secret-syncs/railway/'+resource_sync_id)` only after proving the ID belongs to `railway-connector-resource-prod`. **UNVERIFIED disable endpoint:** the source scripts show sync create/delete but no reviewed pause mutation; use the Infisical UI to switch off auto-sync and read it back before deletion, or stop for a reviewed API shape. These calls remove only the named resource objects; never target the root or auth sync.

| Action | Immediate rollback and proof |
| --- | --- |
| Restricted DSN | Delete resource `DATABASE_URL` only; names-only absence and unchanged deployment ID. Step 1 role `NOLOGIN` and grant revocation are a separate, global-kill-first rollback. |
| Redis reference | Delete resource `REDIS_URL` only; names-only absence, backend/auth unchanged. |
| Folder/canary | Delete source canary and any leaked Railway canary explicitly; prove name absent everywhere. Leave an empty folder if deleting it would alter sync scope. |
| New resource sync | Disable only `railway-connector-resource-prod`, then delete its ID if the reviewed API permits; prove root/auth sync IDs, options and destinations unchanged. Separately delete already-synced resource variables. |
| New auth `SECRET_KEY` | Delete/revoke that new source name and explicitly delete its auth Railway variable; prove signing keyset fingerprint and auth sync unchanged. If already consumed, coordinate safe replacement/redeploy with flags off. |
| Resource `SECRET_KEY` or audit HMAC | Revoke the affected source name and explicitly delete its resource Railway variable; prove absence everywhere else. Preserve audit rows. |
| Nonsecret settings and early-access env | Restore the exact prior value on the same service with `skipDeploys:true`, or delete a new name with verified input. Keep enforcement true with empty list on all three until Step 6; global kill first if rollback could weaken admission. |

After rollback repeat names-only inventories, retained-secret in-process comparisons, sync-scope checks and deployment-ID comparison. An incomplete cleanup is an open blocker, not a Step 2 receipt. Never delete the existing signing keyset.
