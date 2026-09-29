# BQ-CONNECTOR-CORE Gate 4 — provisioning and early-access enable plan (S1764)

Status: **plan only; no production enable authority or completion claim.** Review merge base: runbooks main `ee59009524013caa16d2b82d9a7c26d24e574bf6`; historical design base: runbooks main `d2cc51293ac127c94be1e73650e57a298818d150`; backend main `66109cdc681066bf05e99d3a43de368daa2d4c26` (2026-09-29). Authority: `customer-mcp-connector.md` (especially Mandatory for resource Gate 4, switch administration, keyset, consent and directory sections), core Gate 1/2, buyer discovery Gate 2, OAuth Gate 2, `infisical-secrets.md`, `local-secops.md`, `schema-migration.md`, `auth-signup-flow.md`, Railway runbooks. The operator records exact SHAs/deployments again at execution; a later backend main requires a fresh code/table-access diff. Target: `https://connect.ai.market/mcp` works with OAuth for Max, an approved synthetic reviewer, and existing test accounts, then Max may submit it from the ai.market Claude organization. Keep the allowlist until the P1 release decision.

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
WATCH='d48dd44c-4541-4387-89da-50b2b1d0c8fe'
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
    rows=json.loads(p.stdout)  # value-bearing; never print
    if not isinstance(rows,dict) or not all(isinstance(k,str) and isinstance(v,str)
                                              for k,v in rows.items()):
        raise RuntimeError('Railway variables --json shape changed; output suppressed')
    return rows

# Before executing the next block, bind deployment_ids() to the reviewed Railway
# GraphQL/UI readback of the latest deployment ID for EACH of BACK, AUTH, RES and WATCH,
# and global_kill_disabled() to the credentialed owner-session exact-row query:
# SELECT disabled FROM connector_switches WHERE scope='global' AND key='global';
# Both helpers must fail closed on missing/duplicate rows, unknown schema or IDs.
# Never print their raw responses. Pin the GraphQL field/input shapes by live
# introspection and record only field names/types in the ticket.
FLAGS=('CONNECTOR_ENABLED','CONNECTOR_OAUTH_ENABLED',
       'CONNECTOR_CIMD_ENABLED','CONNECTOR_DCR_ENABLED')
def closed_stage(label):
    for service in (BACK,AUTH,RES):
        values=rv(service)
        for name in FLAGS:
            # Backend main 673bba93 app/core/config.py:70-73 defaults unset to False.
            is_closed=(name not in values or values[name]=='false') if service==BACK else values.get(name)=='false'
            assert is_closed, (service,name,'must be closed')
            print(label,service,name,'unset/default false' if service==BACK and name not in values else 'false')
    assert global_kill_disabled() is True
    print(label,'global connector switch','disabled')

def deployment_snapshot():
    ids=deployment_ids()
    assert isinstance(ids,dict) and set(ids)=={BACK,AUTH,RES,WATCH}
    assert all(isinstance(v,str) and v for v in ids.values())
    return ids

def verify_upsert_shape():
    q='query { __type(name:"VariableCollectionUpsertInput") { inputFields { name type { kind name ofType { kind name } } } } __schema { mutationType { fields { name args { name type { kind name ofType { kind name } } } } } } }'
    data=gql(q,{})
    fields={f['name'] for f in data['__type']['inputFields']}
    mutations={f['name']:f for f in data['__schema']['mutationType']['fields']}
    assert fields=={'projectId','environmentId','serviceId','replace','skipDeploys','variables'}
    assert len(mutations['variableCollectionUpsert']['args'])==1
    assert mutations['variableCollectionUpsert']['args'][0]['name']=='input'
    assert mutations['variableCollectionUpsert']['args'][0]['type']['name']=='VariableCollectionUpsertInput' or mutations['variableCollectionUpsert']['args'][0]['type']['ofType']['name']=='VariableCollectionUpsertInput'
    return True

def put(service,items):
    assert service in (BACK,RES,AUTH)
    assert verify_upsert_shape()
    closed_stage('before-upsert')
    assert deployment_snapshot()==BASE_DEPLOYMENTS
    q='mutation($input:VariableCollectionUpsertInput!){variableCollectionUpsert(input:$input)}'
    result=gql(q,{'input':{'projectId':RP,'environmentId':RE,'serviceId':service,
                            'variables':items,'skipDeploys':True}})
    after=rv(service)
    for name,value in items.items():
        if name=='REDIS_URL' and value.startswith('${{'):
            assert isinstance(after.get(name),str) and after[name]
            # Also compare the raw reference with `value` via the separately
            # introspected GraphQL variable metadata/UI readback before receipt.
            assert raw_reference(service,name)==value
        else:
            assert after.get(name)==value
        print(service,name,'MATCH')
    assert deployment_snapshot()==BASE_DEPLOYMENTS
    closed_stage('after-upsert')
    return result
```

**Railway schema:** Mars's read-only production introspection at 2026-09-29T23:45Z found `VariableCollectionUpsertInput` fields `environmentId`, `projectId`, `replace`, `serviceId`, `skipDeploys`, `variables`; `VariableDeleteInput` has only `environmentId`, `name`, `projectId`, `serviceId`, with no `skipDeploys`. Re-introspect at execution and abort on drift. `customer-mcp-connector.md:46` records `variableCollectionUpsert(skipDeploys:true)`. Backend `app/agents/sysadmin/skills/railway_ops.py` instead demonstrates a deploy-triggering single `variableUpsert` followed by `serviceInstanceDeploy`; neither that nor `variableDelete` is the Step 2 removal path. The `deployment_ids()` and `global_kill_disabled()` bindings are mandatory, reviewed preconditions. Bind them in the same protected interpreter before running `closed_stage('preflight'); BASE_DEPLOYMENTS=deployment_snapshot(); assert verify_upsert_shape()`; do not begin §2.1 until these pass. For the Redis reference and §2.4 replacement, bind `raw_reference(service,name)` to live-introspected GraphQL raw variable metadata; refuse an unknown shape or unreadable raw value. Compare deployment IDs after every mutation, including sync operations. A value-bearing readback is never written to disk.

**No-deploy stop gate, forward and rollback.** `infisical-secrets.md` records that a `prod` secret write re-pushes syncs and redeploys the backend; S1753 records auth redeploys from sync creation and the signing-key write. Railway has only `production` in the `ai-market` project, so use a separate Railway project for the proof. Before the first dependent production mutation, prove each Infisical operation class below against the same self-hosted Infisical instance, native Railway connection type and current API versions. A passing class has an unchanged destination deployment ID after its sync job settles. A class that restarts, lacks a verified operation shape or lacks a receipt moves **with its forward and rollback actions** to Step 5's restart window by reviewed amendment; stop before its first Step 2 production dependency. A post-write production ID check cannot replace this preflight or undo a restart. The Railway `replace:true, skipDeploys:true` removal in §2.4 is a separate proof on the disposable service and then a guarded production operation. No `variableDelete` is permitted in Step 2.

Create a throwaway Railway project named `s1764-nodeploy-proof` with one trivial service from a pinned static image (for example `nginx:alpine` pinned by digest). Give it no database, Redis, shared network, production variable, domain or production resource reference. Record its project/environment/service IDs and image digest. In Infisical project `ai-market-backend` `bd272d48-c5a1-4b52-9d24-12066ae4403c`, use **staging** and create only `/s1764-proof`; never use root or `prod`. Create one native Railway sync from that exact folder to the disposable service, using the existing Railway connection type, `includeAllSubFolders:false`, `disableSecretDeletion:true`, and the same initial behavior/auto-sync settings planned for the resource sync. Capture the deployment ID immediately before the sync-create POST and after its first job settles; this is the `sync-create` proof row. Confirm the source path, environment, destination project/environment/service IDs and connection ID on readback. The existing production syncs must be unchanged. This setup touches no production resources; cost is only the short-lived throwaway Railway service and its sync jobs.

Run the following sequence from the protected Python interpreter used above, with `P` unchanged and a separate staging API wrapper (`PE='staging'`, `PROOF_PATH='/s1764-proof'`) and disposable Railway IDs. Tokens are loaded from `~/.config/infisical/sysadmin-token` and ambient `RAILWAY_API_TOKEN` as above; refresh through `infisical-secrets.md`/`local-secops.md`. No token or secret value goes to argv, disk, output or a receipt. `proof_deployment_id()` is bound to the same reviewed Railway deployment-ID reader as `deployment_ids()` but scoped to the disposable service. `proof_sync(sync_id)` filters `GET /api/v1/secret-syncs?projectId=P` by the exact ID and asserts its staging source and disposable destination before each operation. `wait_job(sync_id,old_job)` polls until a new `lastSyncJobId` has `syncStatus` `success`/`succeeded`, or fails on error/timeout. `wait_proof_quiet(sync_id)` polls the inventory and deployment ID until no job is pending and both remain stable through the operator's bounded observation interval; it fails on an unknown status or timeout. `proof_variables_raw()` uses the live-introspected raw-reference readback described in §2.4; it refuses unresolved values. The Infisical UI may supply `disable_proof_sync()` only after the operator verifies its exact sync ID and reads back `isAutoSyncEnabled=false`; an unverified pause API shape is a refusal, not a pass.

```python
PE='staging'; PROOF_PATH='/s1764-proof'
PROOF_NAME='s1764-nodeploy-proof'
# Bind these IDs and four guarded readers to the throwaway resources, never RP/RE/RES.
assert PROOF_PROJECT_ID!=RP and PROOF_ENV_ID!=RE
assert PROOF_SERVICE_ID not in (BACK,RES,AUTH,WATCH)
proof_api=api
receipt=[]
root=next(s for s in syncs() if s['name']=='railway-backend-prod')
assert root['projectId']==P and root['connection']['app']=='railway'
assert not any(s['name']==PROOF_NAME for s in syncs())
before=proof_deployment_id()
proof_api('POST','/api/v1/secret-syncs/railway',body={
    'name':PROOF_NAME,'projectId':P,'connectionId':root['connectionId'],
    'environment':PE,'secretPath':PROOF_PATH,'isAutoSyncEnabled':True,
    'syncOptions':{'initialSyncBehavior':'overwrite-destination',
                   'includeAllSubFolders':False,'disableSecretDeletion':True},
    'destinationConfig':{'projectId':PROOF_PROJECT_ID,
      'projectName':PROOF_PROJECT_NAME,'environmentId':PROOF_ENV_ID,
      'environmentName':PROOF_ENV_NAME,'serviceId':PROOF_SERVICE_ID,
      'serviceName':PROOF_SERVICE_NAME}})
created=[s for s in syncs() if s['name']==PROOF_NAME]
assert len(created)==1
PROOF_SYNC_ID=created[0]['id']
wait_job(PROOF_SYNC_ID,None)
after=proof_deployment_id()
receipt.append({'operation':'sync-create','before_deployment_id':before,
                'after_deployment_id':after,'sync_id':PROOF_SYNC_ID,
                'sync_job_id':proof_sync(PROOF_SYNC_ID).get('lastSyncJobId'),
                'result':'PASS' if before==after else 'RESTART'})
assert before==after, 'sync-create must move to Step 5'
assert proof_sync(PROOF_SYNC_ID)['id']==PROOF_SYNC_ID
assert proof_sync(PROOF_SYNC_ID)['folder']['path']==PROOF_PATH
assert proof_sync(PROOF_SYNC_ID)['environment']['slug']==PE
assert proof_sync(PROOF_SYNC_ID)['destinationConfig']['projectId']==PROOF_PROJECT_ID
assert proof_sync(PROOF_SYNC_ID)['destinationConfig']['serviceId']==PROOF_SERVICE_ID
def checked(label, operation, sync_id=PROOF_SYNC_ID, expect_job=True):
    before=proof_deployment_id()
    old_job=proof_sync(sync_id).get('lastSyncJobId')
    operation()
    if expect_job: wait_job(sync_id,old_job)
    else: wait_proof_quiet(sync_id)
    after=proof_deployment_id()
    receipt.append({'operation':label,'before_deployment_id':before,
                    'after_deployment_id':after,'sync_id':sync_id,
                    'sync_job_id':proof_sync(sync_id).get('lastSyncJobId'),
                    'result':'PASS' if before==after else 'RESTART'})
    assert before==after, label+' must move to Step 5'

# Baseline sync creation is measured against the service ID recorded just before
# POST /api/v1/secret-syncs/railway; use the §2.2 payload with PE/PROOF_PATH and
# disposable destination substituted. Do not count setup as proof of creation.
checked('folder-write',lambda: proof_api('POST','/api/v2/folders',
    body={'projectId':P,'environment':PE,'name':'child','path':PROOF_PATH}),expect_job=False)
checked('folder-delete',delete_proof_child_folder,expect_job=False)
checked('secret-write',lambda: proof_api('POST','/api/v4/secrets/S1764_PROOF',
    body={'projectId':P,'environment':PE,'secretPath':PROOF_PATH,
          'secretValue':secrets.token_urlsafe(32),'type':'shared',
          'skipMultilineEncoding':True}))
checked('forced-sync',lambda: proof_api('POST',
    '/api/v1/secret-syncs/railway/'+PROOF_SYNC_ID+'/sync-secrets'))
checked('secret-delete',lambda: proof_api('DELETE','/api/v4/secrets/S1764_PROOF',
    body={'projectId':P,'environment':PE,'secretPath':PROOF_PATH,'type':'shared'}))
# The initial sync-create row was captured at setup, before this block.
checked('sync-disable',disable_proof_sync,PROOF_SYNC_ID,False)
before=proof_deployment_id()
delete_proof_sync()  # exact PROOF_SYNC_ID; assert absent in sync inventory
wait_proof_service_quiet()  # no sync remains; watch the deployment ID
after=proof_deployment_id()
receipt.append({'operation':'sync-delete','before_deployment_id':before,
                'after_deployment_id':after,'sync_id':PROOF_SYNC_ID,
                'sync_job_id':None,'result':'PASS' if before==after else 'RESTART'})
assert before==after, 'sync-delete must move to Step 5'

# Rehearse the Railway removal with a disposable literal variable. The helper
# reads EVERY raw variable first and must preserve every name/value except one.
before=proof_deployment_id()
raw=proof_variables_raw(PROOF_SERVICE_ID)
assert 'S1764_PROOF_REMOVE' in raw
expected={k:v for k,v in raw.items() if k!='S1764_PROOF_REMOVE'}
gql('mutation($input:VariableCollectionUpsertInput!){variableCollectionUpsert(input:$input)}',
    {'input':{'projectId':PROOF_PROJECT_ID,'environmentId':PROOF_ENV_ID,
              'serviceId':PROOF_SERVICE_ID,'variables':expected,
              'replace':True,'skipDeploys':True}})
assert proof_variables_raw(PROOF_SERVICE_ID)==expected
after=proof_deployment_id()
receipt.append({'operation':'railway-collection-remove','before_deployment_id':before,
                'after_deployment_id':after,'sync_id':None,'sync_job_id':None,
                'result':'PASS' if before==after else 'RESTART'})
assert before==after, 'Railway removal must move to Step 5'
```

Before executing the block, bind and review `delete_proof_child_folder()`, `disable_proof_sync()` and `delete_proof_sync()` to the current Infisical API or verified UI actions. The folder deletion and sync pause shapes are not established by this runbook; refuse them until their endpoint/field shape or UI readback is recorded. Create `S1764_PROOF_REMOVE` on the disposable service with `skipDeploys:true` before the Railway removal rehearsal and capture that setup mutation's deployment IDs too. For each sync mutation, inspect the sync inventory and any new job until settled even where `expect_job=False`; record a new job ID if one appeared. The `sync-create` before ID must be captured **before** the setup POST; missing that boundary is a failed proof. Assert the source folder is still isolated and no production sync ID/options changed. Also rehearse §2.4 with a raw `${{...}}` reference to a disposable service variable; if the reference cannot resolve without adding another service, mark reference preservation unproved and block any production removal that would retain a reference. Teardown in reverse order: disable/delete the proof sync, delete proof secrets and folder, then delete the throwaway Railway project; verify absence in both systems. Teardown may restart only the disposable service. Save a restricted, names/IDs-only `s1764-nodeploy-proof.json` receipt outside Git with `actor`, UTC time, Infisical host/project/environment/path, Railway project/environment/service/image IDs, API/schema versions, `operations` (the `receipt` rows above plus setup `sync-create`), teardown IDs/absence and the Step 2 or Step 5 disposition for each class. Never save raw API responses.

### 2.1 Restricted resource DSN and Redis

Read only `AUTHOR_DISPATCH_DATABASE_URL` from Infisical root in the *same protected process* (the `schema-migration.md` §S.7a credential source), using a scoped single-secret GET with project, environment and `/` path verified against the live Infisical API response shape. Refuse an unknown shape; do not fetch the whole root folder for this DSN. Parse only its host, port, database path and TLS query; get the Step 1 password through Python `keyring`. Refuse missing password, malformed URI, an unverified database/host, or a URL that does not decode to user `connector_runtime`. Never use the owner username/password in the result. The owner DSN, derived DSN and Railway request exist only in memory; no shell substitution, SQL literal, CLI `--set` or secret in argv.

```python
import keyring
from urllib.parse import urlsplit,urlunsplit,quote
single=api('GET','/api/v4/secrets/AUTHOR_DISPATCH_DATABASE_URL',
           {'projectId':P,'environment':E,'secretPath':'/',
            'viewSecretValue':'true','expandSecretReferences':'false'})
assert set(single)=={'secret'} and single['secret']['secretKey']=='AUTHOR_DISPATCH_DATABASE_URL'
owner=single['secret']['secretValue']; assert isinstance(owner,str) and owner
del single
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

Inspect the live production Redis service name, ID and `REDIS_URL` in Railway before setting the reference. **UNVERIFIED:** these runbooks do not prove that the service is literally `Redis`, or that another service currently uses `${{Redis.REDIS_URL}}`. If the live service name and reference form match, call `put(RES,{'REDIS_URL':'${{Redis.REDIS_URL}}'})`; otherwise substitute the verified service name in Railway's reference syntax. Read back the raw reference through Railway GraphQL variable metadata or UI, check the effective `REDIS_URL` is present in `rv(RES)` without printing it, and confirm this action did not add the name to auth/backend. Run `closed_stage('after-DSN-and-Redis')` and assert `deployment_snapshot()==BASE_DEPLOYMENTS`. `/readyz` reachability is proved after the Step 5 restart, not by this readback. Neither URL belongs in Infisical.

### 2.2 Canary, distinct secrets and resource sync

Capture names from `folder('/')`, `folder('/connector-auth')`, `folder('/connector-resource')` if present, `rv()` for all three services, and `syncs()`. Require the auth folder already contains `CONNECTOR_OAUTH_SIGNING_KEYS`, no new `SECRET_KEY`, and the resource folder is absent or empty; investigate any drift before writing. Require neither connector folder has `DATABASE_URL` or `REDIS_URL`. Reuse `connector_signing_keyset.py` field/payload and `drift_check()` comparison logic, **not** its root/auth-only `require_syncs()` inventory predicate. The active native-sync universe is exactly root `railway-backend-prod`, `railway-connector-auth-prod`, and `railway-issue-channel-watcher-events-prod`, then those three plus `railway-connector-resource-prod`. Reject unknown or duplicate syncs, recursion, wrong source/destination/connection, auto-sync or option drift. The watcher source is `/issue-channel-watcher-railway`, destination `issue-channel-watcher` (`d48dd44c-4541-4387-89da-50b2b1d0c8fe`). Verify service IDs/names against live Railway. Do not call the helper's `generate` or `create-sync` because the signing keyset and auth sync already exist.

```python
def watcher_railway_variables():
    p=subprocess.run(['/opt/homebrew/bin/railway','variables','--service',WATCH,
      '--environment',RE,'--json'],capture_output=True,text=True,check=True,
      cwd='/Users/max/Projects/ai-market/ai-market-backend')
    rows=json.loads(p.stdout)  # value-bearing; never print
    if not isinstance(rows,dict) or not all(isinstance(k,str) and isinstance(v,str)
                                              for k,v in rows.items()):
        raise RuntimeError('Watcher Railway variables --json shape changed; output suppressed')
    return rows
SYNC_SCOPE={
 'railway-backend-prod':('/',BACK,'ai-market-backend','import-prioritize-source'),
 'railway-connector-auth-prod':('/connector-auth',AUTH,'ai-market-connector-auth','overwrite-destination'),
 'railway-issue-channel-watcher-events-prod':('/issue-channel-watcher-railway',WATCH,'issue-channel-watcher','overwrite-destination'),
 'railway-connector-resource-prod':('/connector-resource',RES,'ai-market-connector','overwrite-destination')}
def require_current_syncs(after=False):
    rows=syncs(); names=[r.get('name') for r in rows]
    expected=set(SYNC_SCOPE) if after else set(SYNC_SCOPE)-{'railway-connector-resource-prod'}
    assert len(names)==len(expected) and set(names)==expected
    by_name={r['name']:r for r in rows}
    connection=by_name['railway-backend-prod']['connectionId']
    for name in expected:
        row=by_name[name]; path,service_id,service_name,behavior=SYNC_SCOPE[name]
        opts=row.get('syncOptions') or {}; dest=row.get('destinationConfig') or {}
        assert row.get('destination')=='railway' and (row.get('connection') or {}).get('app')=='railway'
        assert row.get('projectId')==P and (row.get('environment') or {}).get('slug')==E
        assert (row.get('folder') or {}).get('path')==path and row.get('connectionId')==connection
        assert row.get('isAutoSyncEnabled') is True
        assert opts.get('initialSyncBehavior')==behavior and opts.get('disableSecretDeletion') is True
        assert dest.get('projectId')==RP and dest.get('environmentId')==RE
        assert dest.get('projectName')=='ai-market' and dest.get('environmentName')=='production'
        assert dest.get('serviceId')==service_id and dest.get('serviceName')==service_name
        include=opts.get('includeAllSubFolders','omitted')
        assert include is False or (include=='omitted' and name!='railway-connector-resource-prod')
    return by_name

def reconcile_active_sync_values(after=False):
    for name in require_current_syncs(after).keys():
        path,service_id,_,_=SYNC_SCOPE[name]
        source=folder(path,True)
        destination=rv(service_id) if service_id in (BACK,AUTH,RES) else watcher_railway_variables()
        for key in sorted(source.keys() & destination.keys()):
            status=('MATCH' if hashlib.sha256(source[key].encode()).digest()==
                    hashlib.sha256(destination[key].encode()).digest() else 'MISMATCH')
            print(name,key,status)
            assert status=='MATCH'
    backend=rv(BACK)
    assert backend.get('LISTING_LICENSES_ENABLED')=='true'
    assert backend.get('X402_ENABLED')=='false'
    assert backend.get('TERMS_1_1_EFFECTIVE_AT')
    # backend main 673bba93 app/core/config.py:990-994 enforces this trio.

closed_stage('before-sync-work')
assert deployment_snapshot()==BASE_DEPLOYMENTS
reconcile_active_sync_values()  # before the FIRST Infisical write or forced sync
```

The watcher readback has the same protected, shape-checked Railway CLI behavior as `rv()`; never print its raw output. The digest comparison must cover **every shared name/value for every active sync**. Output only names and `MATCH`/`MISMATCH`; a mismatch stops before writing or forcing. Reconcile under that sync's reviewed procedure, then repeat preflight. The backend licence/X402/terms pre-check is mandatory because backend main `673bba93` `app/core/config.py:990-994` rejects their incompatible combination.

Use `POST /api/v2/folders` body `{'projectId':P,'environment':E,'name':'connector-resource','path':'/'}` only if absent. Reconcile values again, then write a disposable random value via `POST /api/v4/secrets/CONNECTOR_RESOURCE_CANARY_S1764`, body `{'projectId':P,'environment':E,'secretPath':'/connector-resource','secretValue':secrets.token_urlsafe(32),'skipMultilineEncoding':True,'type':'shared'}`. Do not print the value. After each mutation run `closed_stage()` and compare all four deployment IDs. Force **each** existing sync, one at a time, only after rerunning `reconcile_active_sync_values()`, with bodiless `POST /api/v1/secret-syncs/railway/<sync-id>/sync-secrets` (no `Content-Type`); poll `syncs()` until a new `lastSyncJobId` has `syncStatus` `success` or `succeeded`. Require the canary name absent from backend, auth, watcher and resource Railway variable names. After each force run `closed_stage()` and compare deployment IDs. A leaked name stops and triggers canary rollback. Save all three existing sync job IDs, versions and deployment IDs in the ticket. This proves non-recursion for the current shapes only.

**Remove the canary before creating the resource sync**, using `DELETE /api/v4/secrets/CONNECTOR_RESOURCE_CANARY_S1764` with body `{'projectId':P,'environment':E,'secretPath':'/connector-resource','type':'shared'}`. Require the name absent from source and every Railway destination, then repeat deployment, flag/global-switch and drift checks. No Railway canary deletion is needed. Then create the resource native sync using the exact `connector_signing_keyset.py` payload pattern and the verified root `connectionId`:

```python
root=require_current_syncs()['railway-backend-prod']
reconcile_active_sync_values()
closed_stage('before-resource-sync-create')
assert deployment_snapshot()==BASE_DEPLOYMENTS
payload={'name':'railway-connector-resource-prod','projectId':P,
 'connectionId':root['connectionId'],'environment':E,'secretPath':'/connector-resource',
 'isAutoSyncEnabled':True,
 'syncOptions':{'initialSyncBehavior':'overwrite-destination',
                'includeAllSubFolders':False,'disableSecretDeletion':True},
 'destinationConfig':{'projectId':RP,'projectName':'ai-market',
   'environmentId':RE,'environmentName':'production',
   'serviceId':RES,'serviceName':'ai-market-connector'}}
api('POST','/api/v1/secret-syncs/railway',body=payload)
require_current_syncs(after=True)
assert deployment_snapshot()==BASE_DEPLOYMENTS
closed_stage('after-resource-sync-create')
```

Read back sync ID, source path/env, connection, target ID, auto-sync and options. Require explicit `includeAllSubFolders:false` on the new sync; omission or enabled recursion stops. Wait for its first successful job; then assert `DATABASE_URL` and `REDIS_URL` remain present on `rv(RES)` (names only) and canary absent everywhere. Generate three independent `secrets.token_urlsafe(48)` values in process; write `SECRET_KEY` to `/connector-auth`, a different `SECRET_KEY` and `CONNECTOR_AUDIT_HMAC_KEY` to `/connector-resource`, each by `POST /api/v4/secrets/<name>` with `projectId`, `environment`, exact `secretPath`, `secretValue`, `skipMultilineEncoding=True`, `type='shared'`. Run `reconcile_active_sync_values(after=True)` before each write. Write one at a time, wait for the corresponding sync job to succeed, check names/fingerprints, run `closed_stage()` and compare deployment IDs, and receipt each separately. Never change `CONNECTOR_OAUTH_SIGNING_KEYS` or its auth sync. Do not create a root sync or use local-secops' generic executor for `/connector-auth`.

Require `require_current_syncs(after=True)`, all four flag values and the global switch still off, no canary on any destination, the two resource Railway URL names still present, and all four tracked deployment IDs unchanged. No canary may remain as a permanent variable.

### 2.3 Remaining variables and readback

Before the first §2.3 write, read backend `LISTING_LICENSES_ENABLED`, `TERMS_1_1_EFFECTIVE_AT`, and `X402_ENABLED` as nonsecret effective values. Require exactly `true`, a nonempty effective terms value, and exactly `false`, respectively; this is backend main `673bba93` `app/core/config.py:990-994`'s boot invariant. Record resource prior values for rollback. Set these three on **resource only, in one** `put(RES, {'LISTING_LICENSES_ENABLED':'true', 'TERMS_1_1_EFFECTIVE_AT':backend_terms, 'X402_ENABLED':'false'})` collection upsert with `skipDeploys:true`. `backend_terms=rv(BACK)['TERMS_1_1_EFFECTIVE_AT']` is read and held in the protected interpreter. Assert resource readback equals backend for all three nonsecret values, names absent from both connector Infisical folders, `closed_stage('after-licence-upsert')`, and unchanged deployment IDs. These three Step 2 settings satisfy Step 5's line-113 provisioning prerequisite; Step 5 still proves effective values after restart. Backend PR `build/connector-licence-fail-closed-s1764` makes connector listing visibility fail closed independently of this setting, subject to its own merge/deploy verification.

With `put()` and `skipDeploys:true`, set resource `CONNECTOR_EXPECTED_PROCESSES=4` after verifying 2 replicas × `CONNECTOR_WORKERS=2`; set `CONNECTOR_AUTH_FAILURE_MAX_IPS=10000` (documented default, integer >=1), and `OTEL_SERVICE_NAME=ai-market-connector`. Read back existing resource `CONNECTOR_AUTH_ISSUER=https://auth.ai.market`, `CONNECTOR_AUDIENCE=https://connect.ai.market/mcp`, `CONNECTOR_JWKS_URL=https://auth.ai.market/.well-known/jwks.json`; repair any drift via `put()` and record it. On **each** of backend, auth and resource, set `CONNECTOR_EARLY_ACCESS_ENFORCED=true` and `CONNECTOR_EARLY_ACCESS_USER_IDS=''` with `put()`, but first capture exact prior names/values. If either backend name is absent, move its forward addition and rollback to Step 5's restart window; §2.4 forbids backend variable removal. Verify exact values on all three after the applicable window and record only the count `0` and a protected in-process comparison to the SHA-256 of the empty string. Empty plus enforcement true admits nobody. Step 6 supplies UUIDs identically to all three, restarts them and proves the negative paths. Recalculate expected processes after any resource scale change.

Final names-only proof: `/connector-auth` has `SECRET_KEY` and `CONNECTOR_OAUTH_SIGNING_KEYS`, but no audit key or URLs; `/connector-resource` has `SECRET_KEY` and `CONNECTOR_AUDIT_HMAC_KEY`, but no signing key or URLs. Check backend has no new connector key names, auth lacks the resource audit key, and resource lacks signing keys. In protected memory compare `hashlib.sha256(source.encode()).digest()` with each destination secret, and prove the two `SECRET_KEY` digests differ; output only `MATCH`/`DIFFERENT`, no values or hashes. Check the existing public JWKS thumbprints against `customer-mcp-connector.md`. Run `closed_stage('final')`, compare the three licensing values with backend, check the global switch remains disabled, assert `require_current_syncs(after=True)`, and compare all deployment IDs with baseline. Any unexpected name, sync scope, value mismatch or restart fails Step 2. Runtime `/readyz` and dependency reachability are Step 5 proofs.

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

Before **any** Step 2 production mutation, complete §2.0's no-deploy proof for each dependent Infisical forward/rollback class and the Railway collection replacement. Mars's 2026-09-29T23:45Z read-only introspection proves `VariableDeleteInput` has no `skipDeploys`; `variableDelete` is prohibited for Step 2 even though `scripts/railway_watcher_credential/railway_watcher_credential.py` uses it elsewhere. With `disableSecretDeletion=true`, deleting an Infisical secret or sync leaves its Railway copy; remove those names explicitly only through the guarded collection replacement below. Keep global switch/flags off throughout; if flags were later enabled, use the rollback map's global kill first.

For a removal, fetch the **entire current service variable name set** through `rv(service)` in the protected interpreter. Fetch each name's raw value through the live-introspected Railway metadata readback `raw_reference(service,name)`; this must return the literal value or the unchanged raw `${{...}}` reference, never a resolved reference value. Assert the raw metadata names equal `rv(service).keys()`, and refuse if any raw value is missing, unreadable or of unknown shape. Re-read immediately before mutation; refuse concurrent name/value drift. Form `variables` as exactly that protected-memory mapping minus the named removals (or with exact prior values restored for a mixed rollback). Apply one `variableCollectionUpsert` with `replace:true, skipDeploys:true`, then assert readback names equal the expected set, retained raw references equal their originals, retained literal values match in protected memory, and **all four** production deployment IDs equal the baseline. Do not log values. This operation is permitted only for `ai-market-connector` (`RES`) and `ai-market-connector-auth` (`AUTH`), never `ai-market-backend` (`BACK`) or `issue-channel-watcher` (`WATCH`). A backend-only new variable requiring deletion moves with its dependent forward action to Step 5's restart window; do not extend this helper's allow-list.

```python
def remove_or_restore_connector_vars(service,remove=(),restore=None):
    assert service in (RES,AUTH)  # never BACK or WATCH
    remove=set(remove); restore={} if restore is None else dict(restore)
    assert remove.isdisjoint(restore)
    assert verify_upsert_shape() and closed_stage('before-collection-replace') is None
    assert deployment_snapshot()==BASE_DEPLOYMENTS
    effective=rv(service)                 # values stay in protected memory
    names=set(effective)
    assert remove <= names
    raw={name:raw_reference(service,name) for name in names}
    assert set(raw)==names and all(isinstance(v,str) for v in raw.values())
    # The raw reader must distinguish a literal from a Railway reference.
    # In particular, never replace a ${{...}} value with rv()'s expansion.
    assert all(not v.startswith('${{') or v.endswith('}}') for v in raw.values())
    expected={k:v for k,v in raw.items() if k not in remove}
    expected.update(restore)
    assert set(rv(service))==names
    assert {k:raw_reference(service,k) for k in names}==raw
    gql('mutation($input:VariableCollectionUpsertInput!){variableCollectionUpsert(input:$input)}',
        {'input':{'projectId':RP,'environmentId':RE,'serviceId':service,
                  'variables':expected,'replace':True,'skipDeploys':True}})
    assert set(rv(service))==set(expected)
    assert {k:raw_reference(service,k) for k in expected}==expected
    assert deployment_snapshot()==BASE_DEPLOYMENTS
    closed_stage('after-collection-replace')
    print(service,sorted(remove),'removed; retained names verified; deployments unchanged')
```

The helper's live metadata binding and a disposable rehearsal are prerequisites. A Railway reference's raw syntax and target must be validated before the call; the `endswith` check alone is not sufficient. Infisical secret deletion is `api('DELETE','/api/v4/secrets/'+name,body={'projectId':P,'environment':E,'secretPath':path,'type':'shared'})`. Sync deletion is `api('DELETE','/api/v1/secret-syncs/railway/'+resource_sync_id)` only after proving the ID belongs to `railway-connector-resource-prod`. For sync disable, use only the reviewed API shape or Infisical UI to switch off auto-sync and read it back before deletion. These calls remove only the named resource objects; never target the root or auth sync. After each rollback action run `closed_stage()` and compare all deployment IDs. If any required operation class lacks a passing §2.0 receipt, move the whole dependent action and rollback to Step 5 before Step 2 mutates production.

| Action | Immediate rollback and proof |
| --- | --- |
| Restricted DSN | `remove_or_restore_connector_vars(RES,{'DATABASE_URL'})`; names-only absence and unchanged deployment IDs. Step 1 role `NOLOGIN` and grant revocation are a separate, global-kill-first rollback. |
| Redis reference | `remove_or_restore_connector_vars(RES,{'REDIS_URL'})`; names-only absence, backend/auth unchanged. |
| Folder/canary | Remove the source canary before resource-sync creation; prove name absent everywhere, with no Railway canary deletion. If it leaked into an existing destination, stop and use a separately reviewed no-deploy deletion route. Leave an empty folder if deleting it would alter sync scope. |
| New resource sync | Disable only `railway-connector-resource-prod`, then delete its ID if the reviewed API permits; prove root/auth sync IDs, options and destinations unchanged. Separately delete already-synced resource variables. |
| New auth `SECRET_KEY` | Delete/revoke that new source name, then `remove_or_restore_connector_vars(AUTH,{'SECRET_KEY'})`; prove signing keyset fingerprint and auth sync unchanged. If already consumed, coordinate safe replacement/redeploy with flags off. |
| Resource `SECRET_KEY` or audit HMAC | Revoke the affected source name, then use `remove_or_restore_connector_vars(RES,{name})`; prove absence everywhere else. Preserve audit rows. |
| Resource licensing trio | Restore the exact prior `LISTING_LICENSES_ENABLED`, `TERMS_1_1_EFFECTIVE_AT` and `X402_ENABLED` state together with one `remove_or_restore_connector_vars(RES, absent_names, prior_present_values)` call. Read back nonsecret values and exact names, check backend remains `true`/effective terms/`false`, flags and global switch off, and deployment IDs unchanged. Do not leave a partial incompatible trio. |
| Nonsecret settings and early-access env | On resource/auth, restore prior values or remove new names with the guarded collection replacement. Backend names must remain present and closed; any backend deletion is deferred with its dependent forward action to Step 5. Keep enforcement true with empty list on all three until Step 6; global kill first if rollback could weaken admission. |

After rollback repeat names-only inventories, retained-secret in-process comparisons, sync-scope checks and deployment-ID comparison. An incomplete cleanup is an open blocker, not a Step 2 receipt. Never delete the existing signing keyset.
