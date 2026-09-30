# BQ-CONNECTOR-CORE Gate 4 — provisioning and early-access enable plan (S1764)

Status: **plan only; no production enable authority or completion claim.** Review merge base: runbooks main `4dbb9b99f0c895776d2cb46bf008eebf09795f90`; historical design base: runbooks main `d2cc51293ac127c94be1e73650e57a298818d150`; backend main `673bba93`. Authority: `customer-mcp-connector.md` (especially Mandatory for resource Gate 4, switch administration, keyset, consent and directory sections), core Gate 1/2, buyer discovery Gate 2, OAuth Gate 2, `infisical-secrets.md`, `local-secops.md`, `schema-migration.md`, `auth-signup-flow.md`, Railway runbooks. The operator records exact SHAs/deployments again at execution; a later backend main requires a fresh code/table-access diff. Target: `https://connect.ai.market/mcp` works with OAuth for Max, an approved synthetic reviewer, and existing test accounts, then Max may submit it from the ai.market Claude organization. Keep the allowlist until the P1 release decision.

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

3. **Trusted edge peer.** With flags off, instrument a temporary *redacted* request-ID diagnostic at the resource edge (or use a reviewed existing equivalent) to record socket peer, full XFF hop count, and selected limiter IP for controlled requests; never log customer headers/IPs generally. Sample multiple real Railway edge requests from two controlled external source IPs and both replicas. Compare socket peers and Railway edge documentation/support evidence; choose the narrow actual peer CIDR(s), not all RFC1918 or Cloudflare ranges, then set `CONNECTOR_TRUSTED_PROXY_CIDRS` on the resource. Backend main `asgi.py::_edge_status` walks XFF **right to left** and selects the first untrusted hop; that selected `state.client_ip` feeds the pre-auth `ip` limiter and auth-failure audit. Probe ordinary traffic and forged `X-Forwarded-For: 1.2.3.4` from each source. **Only pass** if the measured Railway edge appends the true external caller to the right and the selected limiter bucket stays that caller, not `1.2.3.4`; do not assume edge header behavior. Also probe an untrusted direct peer and invalid XFF, which must use socket peer; record an all-trusted-hop case if observed. Record actual hop, peer ranges, request IDs and limiter bucket evidence with IPs redacted. Rollback: clear the CIDR variable and turn the global switch off until rate-limit attribution is repaired. **S1786 supersession:** Step 3 is executed by "Gate 4 STEP 3 operator procedure" below. That procedure replaces this paragraph's temporary diagnostic, its both-replica and hop-count evidence, and its requirement to measure that the edge appends the caller; those items are recorded as not measured, and Step 3 completion is governed solely by §3.4 there.

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
    fields={f['name']:f for f in data['__type']['inputFields']}
    mutations={f['name']:f for f in data['__schema']['mutationType']['fields']}
    assert set(fields)=={'projectId','environmentId','serviceId','replace','skipDeploys','variables'}
    assert fields['replace']['type']['kind']=='SCALAR' and fields['replace']['type']['name']=='Boolean'
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
                            'variables':items,'replace':False,'skipDeploys':True}})
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

Run the following sequence from the protected Python interpreter used above, with `P` unchanged and a separate staging API wrapper (`PE='staging'`, `PROOF_PATH='/s1764-proof'`) and disposable Railway IDs. Tokens are loaded from `~/.config/infisical/sysadmin-token` and ambient `RAILWAY_API_TOKEN` as above; refresh through `infisical-secrets.md`/`local-secops.md`. No token or secret value goes to argv, disk, output or a receipt. `proof_deployment_id()` is bound to the same reviewed Railway deployment-ID reader as `deployment_ids()` but scoped to the disposable service. `proof_sync(sync_id)` filters `GET /api/v1/secret-syncs?projectId=P` by the exact ID and asserts its staging source and disposable destination before each operation. `wait_job(sync_id,old_job)` polls until a new `lastSyncJobId` has `syncStatus` `success`/`succeeded`, or fails on error/timeout. `wait_proof_quiet(sync_id)` polls the inventory and deployment ID until no job is pending and both remain stable through the operator's bounded observation interval; it fails on an unknown status or timeout. `proof_variables_raw()` and `proof_variables_effective()` use live-introspected raw and rendered readbacks described in §2.4; they refuse unknown shapes and unresolved references. The Infisical UI may supply `disable_proof_sync()` only after the operator verifies its exact sync ID and reads back `isAutoSyncEnabled=false`; an unverified pause API shape is a refusal, not a pass.

```python
# Definitions only; §2.0.1 invokes the sequence inside its guarded lifecycle.
def proof_api(method,path,query=None,body=None):
    operations={
        ('POST','/api/v1/secret-syncs/railway'):'sync-create',
        ('POST','/api/v1/secret-syncs/railway/'+globals().get('PROOF_SYNC_ID','')+'/sync-secrets'):'forced-sync',
        ('POST','/api/v4/secrets/S1764_PROOF'):'secret-write',
        ('DELETE','/api/v4/secrets/S1764_PROOF'):'secret-delete',
    }
    operation=operations.get((method,path))
    require(operation is not None, 'Unmapped proof mutation')
    return http_mutation(operation,method,path,body=body,query=query)
def production_sync_snapshot():
    return {s['id']:(s['syncOptions'],s['destinationConfig']) for s in syncs()
            if (s.get('environment') or {}).get('slug')==E}
def proof_source_users():
    users=[]
    for s in syncs():
        env=(s.get('environment') or {}).get('slug')
        # Unknown environment is tolerated only for the proof's own recorded sync; otherwise isolation is unproved.
        if env is None: require(s.get('id')==globals().get('created',{}).get('sync'), 'Sync environment unknown; isolation unproved')
        elif env!=PE: continue
        path=(s.get('folder') or {}).get('path')
        require(isinstance(path,str) and path.startswith('/'), 'Staging sync source unknown; isolation unproved')
        if path==PROOF_PATH:
            users.append(s['id'])
        elif PROOF_PATH.startswith(path.rstrip('/')+'/'):
            assert s['syncOptions'].get('includeAllSubFolders') is False
    return users

def run_disposable_proof():
    global PROOF_SYNC_ID, proof_class
    proof_class='sync-create'
    assert PROOF_PROJECT_ID!=RP and PROOF_ENV_ID!=RE
    assert PROOF_SERVICE_ID not in (BACK,RES,AUTH,WATCH)
    # infisical-sync is a Railway project token for RP only (S1771 run 1); use the disposable project's own connection.
    conn=proof_connection()
    assert not any(s['name']==PROOF_NAME for s in syncs())
    assert not proof_source_users()  # no existing staging sync can source the proof path
    before=proof_deployment_id()
    created['sync_attempted']=True
    result=proof_api('POST','/api/v1/secret-syncs/railway',body={
        'name':PROOF_NAME,'projectId':P,'connectionId':conn['id'],
        'environment':PE,'secretPath':PROOF_PATH,'isAutoSyncEnabled':True,
        'syncOptions':{'initialSyncBehavior':'overwrite-destination',
                       'includeAllSubFolders':False,'disableSecretDeletion':True},
        'destinationConfig':{'projectId':PROOF_PROJECT_ID,
          'projectName':PROOF_PROJECT_NAME,'environmentId':PROOF_ENV_ID,
          'environmentName':PROOF_ENV_NAME,'serviceId':PROOF_SERVICE_ID,
          'serviceName':PROOF_SERVICE_NAME}})
    PROOF_SYNC_ID=text_id(result['secretSync']['id']); created['sync']=PROOF_SYNC_ID
    matches=[s for s in syncs() if s['name']==PROOF_NAME]
    assert len(matches)==1 and matches[0]['id']==PROOF_SYNC_ID
    assert proof_source_users()==[PROOF_SYNC_ID]
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
        global proof_class
        proof_class=label
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

    # Sync creation is measured from before its POST, including the initial job.
    checked('folder-write',create_proof_child_folder,expect_job=False)
    checked('folder-delete',delete_proof_child_folder,expect_job=False)
    checked('secret-write',create_proof_secret)
    checked('forced-sync',lambda: proof_api('POST',
        '/api/v1/secret-syncs/railway/'+PROOF_SYNC_ID+'/sync-secrets'))
    checked('secret-delete',lambda: proof_api('DELETE','/api/v4/secrets/S1764_PROOF',
        body={'projectId':P,'environment':PE,'secretPath':PROOF_PATH,'type':'shared'}),expect_job=False)
    # The initial sync-create row was captured at setup, before this block.
    checked('sync-disable',disable_proof_sync,PROOF_SYNC_ID,False)
    proof_class='sync-delete'
    before=proof_deployment_id()
    delete_proof_sync()  # exact PROOF_SYNC_ID; assert absent in sync inventory
    wait_proof_service_quiet()  # no sync remains; watch the deployment ID
    after=proof_deployment_id()
    receipt.append({'operation':'sync-delete','before_deployment_id':before,
                    'after_deployment_id':after,'sync_id':PROOF_SYNC_ID,
                    'sync_job_id':None,'result':'PASS' if before==after else 'RESTART'})
    assert before==after, 'sync-delete must move to Step 5'
    assert not proof_source_users()
    assert production_sync_snapshot()==production_sync_before

    # Rehearse removal while preserving every other raw variable and reference.
    proof_class='railway-collection-remove'
    before=proof_deployment_id()
    raw=proof_variables_raw(PROOF_SERVICE_ID)
    assert 'S1764_PROOF_REMOVE' in raw
    reference_names={k for k,v in raw.items() if v.startswith('${{')}
    effective_before=proof_variables_effective(PROOF_SERVICE_ID)
    assert all(effective_before[k]!=raw[k] for k in reference_names)
    expected={k:v for k,v in raw.items() if k!='S1764_PROOF_REMOVE'}
    gql('mutation($input:VariableCollectionUpsertInput!){variableCollectionUpsert(input:$input)}',
        {'input':{'projectId':PROOF_PROJECT_ID,'environmentId':PROOF_ENV_ID,
                  'serviceId':PROOF_SERVICE_ID,'variables':expected,
                  'replace':True,'skipDeploys':True}})
    assert proof_variables_raw(PROOF_SERVICE_ID)==expected
    effective_after=proof_variables_effective(PROOF_SERVICE_ID)
    assert all(effective_after[k]==effective_before[k] and effective_after[k]!=raw[k]
               for k in reference_names)
    after=proof_deployment_id()
    receipt.append({'operation':'railway-collection-remove','before_deployment_id':before,
                    'after_deployment_id':after,'sync_id':None,'sync_job_id':None,
                    'result':'PASS' if before==after else 'RESTART'})
    assert before==after, 'Railway removal must move to Step 5'
    proof_class='reference-preservation'
    receipt.append({'operation':'reference-preservation','names':sorted(reference_names),
                    'result':'PASS' if reference_names else 'UNPROVED'})

```

Before executing the block, bind and review `delete_proof_child_folder()`, `disable_proof_sync()` and `delete_proof_sync()` to the current Infisical API or verified UI actions. Define the concrete bindings in §2.0.1 before preflight, then run its guarded lifecycle for setup, proof and teardown on both pass and failure. The folder deletion and sync pause shapes are not established by this runbook; refuse them until their endpoint/field shape or UI readback is recorded. Create `S1764_PROOF_REMOVE` on the disposable service with `skipDeploys:true` before the Railway removal rehearsal and capture that setup mutation's deployment IDs too. For each sync mutation, inspect the sync inventory and any new job until settled even where `expect_job=False`; record a new job ID if one appeared. The `sync-create` before ID must be captured **before** the setup POST; missing that boundary is a failed proof. Assert the source folder is still isolated and `production_sync_snapshot()==production_sync_before` again after final teardown; record the production-sync invariant comparison without exposing values. Also rehearse §2.4 with a raw `${{...}}` reference to a disposable service variable; assert its raw string and rendered value before and after replacement are unchanged, and record a names/IDs-only pass. If the reference cannot resolve without adding another service, mark reference preservation unproved and block any production removal that would retain a reference. **Proof connection (S1771):** the production Infisical Railway connection `infisical-sync` uses method `project-token`, which Railway scopes to the ai-market project only, so it cannot write to a throwaway project (run 1 failed with `Failed to sync secrets to Railway`). The proof therefore creates a Railway project token for the disposable project and a temporary Infisical Railway connection `s1764-proof-railway` (method `project-token`, Infisical project `P`), uses it for the proof sync only, and deletes it after the proof sync. The token exists only in memory and dies with the disposable project; the production connection and syncs are never changed. The §2.0.1 finally block tears down in reverse order on pass and failure, including partial setup: disable/delete the proof sync, delete the proof connection, delete proof secrets and folder, then delete the throwaway Railway project; verify absence in both systems before re-raising any original failure. Teardown may restart only the disposable service. Save a restricted, names/IDs-only `s1764-nodeploy-proof.json` receipt outside Git with `actor`, UTC time, Infisical host/project/environment/path, Railway project/environment/service/image IDs, API/schema versions, `operations` (the `receipt` rows above, including reference preservation and setup `sync-create`), teardown IDs/absence and the Step 2 or Step 5 disposition for each class. Never save raw API responses.

#### 2.0.1 Reviewed helper bindings (S1771)

Run order: §2.0 definitions → §2.0.1 definitions → §2.0.1 setup → §2.0 proof block (guarded lifecycle).

Run these definitions after §2.0's import/definition blocks and before its preflight calls, then run the guarded lifecycle once in the **same protected interpreter** (`set +x`, `umask 077`; no helper file, raw output, debug logging or credential-bearing traceback). No live API verification is claimed here. **UNVERIFIED — operator must pin by live read-only call or UI readback before use; refuse on mismatch** applies to every `REVIEWED_*` entry: populate it in memory after independent review, never by automatically copying the current response. Pins contain schema names/types, exact request key/type shapes, and sets of required mutation-response key paths from the table below; record those and their source in the ticket. Extra response keys and nullable optional values are allowed; consumed IDs must be non-empty strings. Keep the `/api/status` key/type shape pin unchanged. The operator-entered Infisical version (for example `infisical/infisical:v0.161.11` from the Railway dashboard) is informational receipt metadata only, never a mutation precondition.

Sources: [owner query and DSN](../customer-mcp-connector.md#connector-switch-administration-p0-runbook-sql) (lines 155–157), [owner retrieval](../schema-migration.md#s7a-s1163-schema-classification-tooling-operator-reference), [Infisical credentials/target](../infisical-secrets.md#safe-cli-verification), and `koskadeux-mcp/scripts/connector_keyset/connector_signing_keyset.py` (`Client.secrets`, `Client.syncs`, `require_no_connector_subfolders`, `run`: secret/folder GET, folder POST). Upstream [folder DELETE](https://infisical.com/docs/api-reference/endpoints/folders/delete), [Railway sync PATCH](https://infisical.com/docs/api-reference/endpoints/secret-syncs/railway/update) and [sync DELETE/removeSecrets](https://infisical.com/docs/api-reference/endpoints/secret-syncs/railway/delete) describe the proposed shapes, **not** this self-hosted version; pin the status shape at `https://secrets.ai.market/api/status` as a reachability/identity check of the self-hosted instance. The upstream Infisical API docs are the reference for reviewing the HTTP shapes. Railway [GraphQL connections](https://docs.railway.com/integrations/api/graphql-overview) and [project/service creation](https://docs.railway.com/integrations/api/api-cookbook) establish examples; the exact endpoint/schema, `projectDelete` and raw `variables(unrendered)` remain **UNVERIFIED** until live introspection. `variableCollectionUpsert` is sourced by §2.0's schema receipt and `customer-mcp-connector.md:46`, rechecked below.

The instance runs `infisical/infisical:v0.161.11`; upstream API references below are informational, not live instance verification. Required paths cover only mutation-response fields the proof consumes; source/destination and job checks use separate inventory readbacks. An empty set means no response fields are consumed (a dict is still required).

| Operation | Method | Endpoint template | Required response key paths | API reference |
|---|---|---|---|---|
| sync-create | POST | `/api/v1/secret-syncs/railway` | `{('secretSync', 'id')}` | [Create](https://infisical.com/docs/api-reference/endpoints/secret-syncs/railway/create) |
| forced-sync | POST | `/api/v1/secret-syncs/railway/{syncId}/sync-secrets` | `set()` | [Sync secrets](https://infisical.com/docs/api-reference/endpoints/secret-syncs/railway/sync-secrets) |
| sync-pause | PATCH | `/api/v1/secret-syncs/railway/{syncId}` | `{('secretSync', 'id')}` | [Update](https://infisical.com/docs/api-reference/endpoints/secret-syncs/railway/update) |
| sync-delete | DELETE | `/api/v1/secret-syncs/railway/{syncId}` | `{('secretSync', 'id')}` | [Delete](https://infisical.com/docs/api-reference/endpoints/secret-syncs/railway/delete) |
| secret-write | POST | `/api/v4/secrets/S1764_PROOF` (`{secretName}` in API reference) | `{('secret', 'id')}` | [Create](https://infisical.com/docs/api-reference/endpoints/secrets/create) |
| secret-delete | DELETE | `/api/v4/secrets/S1764_PROOF` (`{secretName}` in API reference) | `set()` | [Delete](https://infisical.com/docs/api-reference/endpoints/secrets/delete) |
| folder-create | POST | `/api/v2/folders` | `{('folder', 'id'), ('folder', 'name')}` | [Create](https://infisical.com/docs/api-reference/endpoints/folders/create) |
| folder-delete | DELETE | `/api/v2/folders/{folderIdOrName}` | `{('folder', 'id'), ('folder', 'name')}` | [Delete](https://infisical.com/docs/api-reference/endpoints/folders/delete) |
| connection-create | POST | `/api/v1/app-connections/railway` | `{('appConnection', 'id')}` | [Create](https://infisical.com/docs/api-reference/endpoints/app-connections/railway/create) |
| connection-delete | DELETE | `/api/v1/app-connections/railway/{connectionId}` | `{('appConnection', 'id')}` | [Delete](https://infisical.com/docs/api-reference/endpoints/app-connections/railway/delete) |

```python
import os, re, time, urllib.parse
assert __debug__, 'Do not run this session with Python -O'
os.umask(0o077)
REVIEWED_GQL={}  # (type_name, field_name): exact schema_field() tuple; names/types only
REVIEWED_HTTP={} # operation: ((method, endpoint_template, shape(body), shape(query)), required_response_paths_set)
REVIEWED_STATUS=None  # shape(api GET /api/status); reachability/identity only
INFISICAL_VERSION=None  # operator-entered informational string; never a precondition
REVIEWED_DB_IDENTITY=None  # (database, owner_role, server_address), pinned by the credentialed owner session

def require(ok, reason):
    if not ok: raise RuntimeError(reason)

def safe(call, *args, **kwargs):
    try: return call(*args, **kwargs)
    except Exception: raise RuntimeError('Protected call failed; details suppressed') from None

def text_id(value):
    require(isinstance(value,str) and bool(value.strip()), 'Missing/empty ID')
    return value

def shape(value):
    if isinstance(value,dict): return tuple(sorted((k,shape(v)) for k,v in value.items()))
    if isinstance(value,list): return ('list',tuple(sorted(set(shape(v) for v in value),key=repr)))
    return type(value).__name__  # no values, including secret values

def type_text(t):
    if t['kind'] in ('NON_NULL','LIST'):
        require(t.get('ofType') is not None, 'Introspection too shallow: deepen ofType')
    if t['kind']=='NON_NULL': return type_text(t['ofType'])+'!'
    if t['kind']=='LIST': return '['+type_text(t['ofType'])+']'
    return text_id(t['name'])

def schema_field(type_name, name):
    # Read-only at backboard.railway.app/graphql/v2 through the existing gql().
    q='query($n:String!){__type(name:$n){fields{name args{name type{kind name ofType{kind name ofType{kind name ofType{kind name ofType{kind name ofType{kind name}}}}}}} type{kind name ofType{kind name ofType{kind name ofType{kind name ofType{kind name ofType{kind name}}}}}}} inputFields{name type{kind name ofType{kind name ofType{kind name ofType{kind name ofType{kind name ofType{kind name}}}}}}}}}'
    row=safe(gql,q,{'n':type_name})['__type']
    require(isinstance(row,dict), 'Unknown GraphQL type')
    fields=row.get('fields') if row.get('fields') is not None else row.get('inputFields')
    matches=[f for f in fields if f['name']==name]
    require(len(matches)==1, 'GraphQL field missing/duplicate: '+type_name+'.'+name)
    f=matches[0]
    return (name,type_text(f['type']),tuple(sorted((a['name'],type_text(a['type'])) for a in f.get('args',[]))))

def pin_field(type_name,name):
    require((type_name,name) in REVIEWED_GQL, 'UNVERIFIED field: pin required')
    actual=schema_field(type_name,name)
    require(REVIEWED_GQL[(type_name,name)]==actual, 'schema drift: pinned shape mismatch')
    return actual

def base_type(signature): return signature[1].replace('!','').strip('[]')

def verify_deployment_shape():
    f=pin_field('Query','deployments'); args=dict(f[2])
    require(args.get('input')=='DeploymentListInput!' and args.get('first')=='Int', 'Deployment query drift')
    for name in ('projectId','environmentId','serviceId'):
        require(base_type(pin_field('DeploymentListInput',name))=='String', 'Deployment input drift')
    edge=base_type(pin_field(base_type(f),'edges'))
    node=base_type(pin_field(edge,'node'))
    require(node=='Deployment', 'Deployment node drift')
    for name in ('id','status','createdAt'): pin_field(node,name)

def latest_deployment(project,environment,service):
    verify_deployment_shape()
    q='query($i:DeploymentListInput!){deployments(first:1,input:$i){edges{node{id status createdAt}}}}'
    data=safe(gql,q,{'i':{'projectId':text_id(project),'environmentId':text_id(environment),'serviceId':text_id(service)}})
    rows=data['deployments']['edges']
    require(isinstance(rows,list) and len(rows)==1, 'Latest deployment missing/duplicate')
    node=rows[0]['node']
    require(set(node)=={'id','status','createdAt'} and all(isinstance(v,str) and v for v in node.values()), 'Deployment response drift')
    text_id(node['id'])
    return node

def deployment_ids() -> dict[str,str]:
    services=(BACK,AUTH,RES,WATCH)
    require(len(set(services))==4, 'Duplicate production service IDs')
    out={s:latest_deployment(RP,RE,s)['id'] for s in services}
    require(len(set(out.values()))==4, 'Duplicate deployment IDs')
    return out

def global_kill_disabled() -> bool:
    # Documented non-interactive owner path: customer-mcp-connector.md:157; schema-migration.md §S.7a.
    # Reconfirm owner DB/host/environment by the credentialed owner-session procedure before this call.
    require(E=='prod' and P=='bd272d48-c5a1-4b52-9d24-12066ae4403c', 'Owner source mismatch')
    require(isinstance(REVIEWED_DB_IDENTITY,tuple) and len(REVIEWED_DB_IDENTITY)==3
        and all(isinstance(v,str) and v for v in REVIEWED_DB_IDENTITY), 'Owner DB identity unreviewed')
    single=safe(api,'GET','/api/v4/secrets/AUTHOR_DISPATCH_DATABASE_URL',
        {'projectId':P,'environment':E,'secretPath':'/','viewSecretValue':'true','expandSecretReferences':'false'})
    assert set(single)=={'secret'}
    assert single['secret']['secretKey']=='AUTHOR_DISPATCH_DATABASE_URL' and single['secret']['type']=='shared'
    dsn=single['secret'].get('secretValue')
    del single
    require(isinstance(dsn,str) and bool(dsn), 'Owner DSN absent')
    conn=None
    try:
        import psycopg2  # schema-migration.md §S.7a read-only owner path
        conn=psycopg2.connect(dsn,connect_timeout=5)
        conn.set_session(readonly=True)
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '5s'")
            cur.execute('SELECT current_database(), current_user, inet_server_addr()::text')
            require(cur.fetchall()==[REVIEWED_DB_IDENTITY], 'Owner DB identity mismatch')
            cur.execute("SELECT disabled FROM connector_switches WHERE scope='global' AND key='global'")
            result=cur.fetchall()
        require(len(result)==1 and len(result[0])==1 and type(result[0][0]) is bool, 'Global switch row/type mismatch')
        return result[0][0]
    except Exception: raise RuntimeError('Owner read refused; details suppressed') from None
    finally:
        del dsn
        if conn is not None: safe(conn.close)

def proof_scope():
    require(PE=='staging' and PROOF_PATH=='/s1764-proof' and PROOF_NAME=='s1764-nodeploy-proof', 'Proof source mismatch')
    require(text_id(PROOF_PROJECT_ID)!=RP and text_id(PROOF_ENV_ID)!=RE, 'Production destination refused')
    require(text_id(PROOF_SERVICE_ID) not in (BACK,AUTH,RES,WATCH), 'Production service refused')

def variables_read(project,environment,service,raw):
    f=pin_field('Query','variables'); args=dict(f[2])
    require(set(args)=={'projectId','environmentId','serviceId','unrendered'}, 'Variables argument drift')
    require(args['unrendered'] in ('Boolean','Boolean!'), 'Raw variables unsupported')
    require(all(args[k] in ('String','String!') for k in ('projectId','environmentId','serviceId')), 'Variables ID type drift')
    q='query($p:String!,$e:String!,$s:String!,$u:Boolean!){variables(projectId:$p,environmentId:$e,serviceId:$s,unrendered:$u)}'
    out=safe(gql,q,{'p':project,'e':environment,'s':service,'u':raw})['variables']
    require(isinstance(out,dict) and all(isinstance(k,str) and isinstance(v,str) for k,v in out.items()), 'Variables response drift')
    return out

def raw_reference(service,name) -> str:
    require(service in (BACK,AUTH,RES) and isinstance(name,str), 'Raw reference scope mismatch')
    out=variables_read(RP,RE,service,True)
    require(name in out, 'Raw variable missing')
    return out[name]

def proof_variables_raw(service_id) -> dict[str,str]:
    proof_scope(); require(service_id==PROOF_SERVICE_ID, 'Proof service mismatch')
    return variables_read(PROOF_PROJECT_ID,PROOF_ENV_ID,service_id,True)

def proof_variables_effective(service_id) -> dict[str,str]:
    proof_scope(); require(service_id==PROOF_SERVICE_ID, 'Proof service mismatch')
    out=variables_read(PROOF_PROJECT_ID,PROOF_ENV_ID,service_id,False)
    require(not any('${{' in v for v in out.values()), 'Unresolved proof reference')
    return out

def proof_deployment_id():
    proof_scope()
    return latest_deployment(PROOF_PROJECT_ID,PROOF_ENV_ID,PROOF_SERVICE_ID)['id']

def proof_sync(sync_id):
    proof_scope(); text_id(sync_id)
    rows=safe(syncs)
    require(isinstance(rows,list) and all(isinstance(r,dict) for r in rows), 'Sync inventory drift')
    ids=[text_id(r.get('id')) for r in rows]
    require(len(ids)==len(set(ids)), 'Duplicate sync IDs')
    matches=[r for r in rows if r['id']==sync_id]
    require(len(matches)==1, 'Proof sync missing/duplicate')
    r=matches[0]; dest=r.get('destinationConfig') or {}
    require(r.get('projectId')==P and (r.get('environment') or {}).get('slug')==PE
        and (r.get('folder') or {}).get('path')==PROOF_PATH
        and dest.get('projectId')==PROOF_PROJECT_ID and dest.get('environmentId')==PROOF_ENV_ID
        and dest.get('serviceId')==PROOF_SERVICE_ID and r.get('destination')=='railway', 'Proof sync scope mismatch')
    require(type(r.get('isAutoSyncEnabled')) is bool, 'Sync pause field drift')
    return r

SUCCESS={'success','succeeded'}; BUSY={'pending','running'}
def job_state(row):
    status=row.get('syncStatus')
    require(status in SUCCESS|BUSY, 'Failed/error/unknown sync status')
    job=row.get('lastSyncJobId')
    require(job is None or isinstance(job,str) and bool(job), 'Job ID drift')
    require(status not in SUCCESS or bool(job), 'Successful sync has no job ID')
    return job,status

def wait_job(sync_id,old_job,timeout=300):
    require(0<timeout<=300, 'Invalid job timeout')
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        job,status=job_state(proof_sync(sync_id))
        if job!=old_job and status in SUCCESS: return job
        time.sleep(5)
    raise RuntimeError('Proof sync job timeout')

def quiet(sync_id,observe):
    proof_scope(); require(0<observe<600, 'Invalid observation interval')
    deadline=time.monotonic()+600; unchanged=None; previous=None
    while time.monotonic()<deadline:
        rows=safe(syncs)
        require(isinstance(rows,list) and all(isinstance(r,dict) for r in rows), 'Sync inventory drift')
        # None selects service-quiet, used only after the proof sync is deleted.
        target=PROOF_SYNC_ID if sync_id is None else sync_id
        matches=[r for r in rows if r.get('id')==target]
        require(len(matches)<=1, 'Duplicate proof sync')
        state=job_state(proof_sync(target)) if matches else (None,None)
        busy=state[1] in BUSY
        current=(state,proof_deployment_id()); now=time.monotonic()
        if busy or current!=previous: unchanged=None
        if not busy and unchanged is None: unchanged=now
        if unchanged is not None and now-unchanged>=observe: return
        previous=current; time.sleep(5)
    raise RuntimeError('Proof quiet timeout')

def wait_proof_quiet(sync_id,observe=90): return quiet(sync_id,observe)
def wait_proof_service_quiet(observe=90): return quiet(None,observe)

def check_instance_status():
    require(REVIEWED_STATUS is not None, 'UNVERIFIED /api/status')
    data=safe(api,'GET','/api/status')  # api() targets https://secrets.ai.market
    require(isinstance(data,dict) and shape(data)==REVIEWED_STATUS, 'Infisical status shape drift')

def http_mutation(operation,method,path,body=None,query=None,created_key=None):
    # UNVERIFIED self-hosted mutation: exact request shape and required response paths reviewed BEFORE use.
    pin=REVIEWED_HTTP.get(operation)
    require(isinstance(pin,tuple) and len(pin)==2, 'UNVERIFIED Infisical mutation')
    require(isinstance(pin[1],set) and all(isinstance(p,tuple) and p
        and all(isinstance(k,str) and k for k in p) for p in pin[1]), 'UNVERIFIED response key paths')
    endpoint=re.sub(r'(?<=/folders/)[^/]+$', '{folderIdOrName}',path)
    endpoint=re.sub(r'(?<=/secret-syncs/railway/)[^/]+(?=/sync-secrets$|$)', '{syncId}',endpoint)
    endpoint=re.sub(r'(?<=/app-connections/railway/)[^/]+$', '{connectionId}',endpoint)
    require(pin[0]==(method,endpoint,shape(body),shape(query)), 'Infisical request shape drift')
    check_instance_status()
    result=safe(api,method,path,query=query,body=body)
    require(isinstance(result,dict), 'Infisical mutation response is not a dict')
    for key_path in pin[1]:
        value=result
        for key in key_path:
            require(isinstance(value,dict) and key in value, 'Missing required response key path')
            value=value[key]
        if key_path[-1]=='id': text_id(value)
    if created_key is not None: created[created_key]=text_id(result['folder']['id'])
    return result

def proof_folders(parent):
    # connector_signing_keyset.py:414–420, 436–440 establishes folders list at the requested parent.
    require(PE=='staging' and parent in ('/',PROOF_PATH,PROOF_PATH+'/child'), 'Folder scope mismatch')
    data=safe(api,'GET','/api/v2/folders',{'projectId':P,'environment':PE,'path':parent})
    rows=data.get('folders') if isinstance(data,dict) else None
    require(isinstance(rows,list) and all(isinstance(r,dict) and isinstance(r.get('name'),str) for r in rows), 'Folder list drift')
    ids=[text_id(r.get('id')) for r in rows]
    require(len(ids)==len(set(ids)) and len(rows)==len({r['name'] for r in rows}), 'Duplicate folders')
    return rows

def proof_secrets_empty(path):
    # Client.secrets establishes this exact list shape; values are never requested.
    require(PE=='staging' and path in (PROOF_PATH,PROOF_PATH+'/child'), 'Secret path mismatch')
    data=safe(api,'GET','/api/v4/secrets',{'projectId':P,'environment':PE,'secretPath':path,
        'viewSecretValue':'false','recursive':'false','includeImports':'false','expandSecretReferences':'false'})
    require(isinstance(data,dict) and isinstance(data.get('secrets'),list) and not data['secrets'], 'Proof folder is not empty')
    require(not proof_folders(path), 'Proof folder has children')

def remove_folder(parent,name):
    require(PE=='staging' and PROOF_PATH=='/s1764-proof', 'Proof source mismatch')
    rows=[r for r in proof_folders(parent) if r['name']==name]
    require(len(rows)==1, 'Proof folder missing/duplicate')
    folder_id=rows[0]['id']; path=parent.rstrip('/')+'/'+name
    proof_secrets_empty(path)
    # Upstream folders/delete; UNVERIFIED for this instance until request/response shapes are reviewed.
    result=http_mutation('folder-delete','DELETE','/api/v2/folders/'+urllib.parse.quote(folder_id,safe=''),
        body={'projectId':P,'environment':PE,'path':parent})
    require(isinstance(result,dict) and isinstance(result.get('folder'),dict)
        and result['folder'].get('id')==folder_id and result['folder'].get('name')==name, 'Deleted folder response mismatch')
    require(not any(r['name']==name or r['id']==folder_id for r in proof_folders(parent)), 'Folder still present')

def delete_proof_child_folder(): return remove_folder(PROOF_PATH,'child')

def disable_proof_sync():
    row=proof_sync(PROOF_SYNC_ID)
    # Upstream railway/update; UNVERIFIED self-hosted PATCH response until pin.
    result=http_mutation('sync-pause','PATCH','/api/v1/secret-syncs/railway/'+urllib.parse.quote(PROOF_SYNC_ID,safe=''),
        body={'isAutoSyncEnabled':False})
    require(isinstance(result,dict) and isinstance(result.get('secretSync'),dict)
        and result['secretSync'].get('id')==row['id'], 'Sync pause response mismatch')
    require(proof_sync(PROOF_SYNC_ID)['isAutoSyncEnabled'] is False, 'Sync still enabled')

def delete_proof_sync():
    require(proof_sync(PROOF_SYNC_ID)['isAutoSyncEnabled'] is False, 'Pause sync before deletion')
    wait_proof_quiet(PROOF_SYNC_ID)
    # Upstream railway/delete documents removeSecrets; refuse if current instance cannot pin false.
    result=http_mutation('sync-delete','DELETE','/api/v1/secret-syncs/railway/'+urllib.parse.quote(PROOF_SYNC_ID,safe=''),
        query={'removeSecrets':'false'})
    require(isinstance(result,dict) and isinstance(result.get('secretSync'),dict)
        and result['secretSync'].get('id')==PROOF_SYNC_ID, 'Deleted sync response mismatch')
    require(not any(r.get('id')==PROOF_SYNC_ID for r in safe(syncs)), 'Sync still present')

def delete_proof_folder():
    require(PE=='staging' and PROOF_PATH=='/s1764-proof', 'Proof source mismatch')
    require(not any((r.get('environment') or {}).get('slug')==PE
        and (r.get('folder') or {}).get('path')==PROOF_PATH for r in safe(syncs)), 'Proof folder still has a sync')
    return remove_folder('/','s1764-proof')

def proof_project():
    pin_field('Query','project')
    for name in ('id','name','workspaceId','environments','services'): pin_field('Project',name)
    for field in ('environments','services'):
        connection=base_type(pin_field('Project',field))
        edge=base_type(pin_field(connection,'edges')); node=base_type(pin_field(edge,'node'))
        for name in ('id','name'): pin_field(node,name)
    return safe(gql,'query($id:String!){project(id:$id){id name workspaceId environments{edges{node{id name}}} services{edges{node{id name}}}}}',
        {'id':text_id(PROOF_PROJECT_ID)})['project']

def delete_proof_project():
    require(text_id(PROOF_PROJECT_ID)!=RP, 'Production project refused')
    row=proof_project()
    require(isinstance(row,dict) and row['id']==PROOF_PROJECT_ID and row['name']=='s1764-nodeploy-proof'
        and row.get('workspaceId')==W, 'Project deletion scope mismatch')
    f=pin_field('Mutation','projectDelete')
    require(dict(f[2])=={'id':'String!'} and base_type(f)=='Boolean', 'UNVERIFIED projectDelete shape')
    result=safe(gql,'mutation($id:String!){projectDelete(id:$id)}',{'id':PROOF_PROJECT_ID})
    require(result.get('projectDelete') is True, 'Project deletion unconfirmed')
    require(proof_project_absent(), 'Project absence unproved')

def proof_project_absent():
    # Null project, or only the exact 'Project not found' error; any other error or transport failure is not absence evidence.
    req=urllib.request.Request('https://backboard.railway.app/graphql/v2',
      data=json.dumps({'query':'query($id:String!){project(id:$id){id}}','variables':{'id':text_id(PROOF_PROJECT_ID)}},separators=(',',':')).encode(),
      headers={'Authorization':'Bearer '+RT,'Content-Type':'application/json','User-Agent':'Mozilla/5.0 (S1764 operator)'})
    result=safe(lambda: json.load(urllib.request.urlopen(req,timeout=30)))
    require(isinstance(result,dict) and ('data' in result or 'errors' in result), 'Non-GraphQL response; absence unproved')
    if 'errors' in result:
        errors=result['errors']
        require(isinstance(errors,list) and errors and all(isinstance(e,dict)
            and e.get('message')=='Project not found' for e in errors), 'Project absence unproved')
        require(result.get('data') is None or (isinstance(result['data'],dict) and result['data'].get('project') is None), 'Project absence unproved')
    else:
        require(isinstance(result['data'],dict) and 'project' in result['data'] and result['data']['project'] is None, 'Project still present')
    # Authoritative workspace inventory must lack both the recorded ID and the proof name.
    require(not any(r['id']==PROOF_PROJECT_ID for r in workspace_projects()), 'Project ID still listed')
    return proof_project_by_name() is None

def proof_connections():
    data=safe(api,'GET','/api/v1/app-connections/railway')
    rows=data.get('appConnections') if isinstance(data,dict) else None
    require(isinstance(rows,list) and all(isinstance(r,dict) for r in rows), 'Connection inventory drift')
    # Keep names/IDs only; credentials fields are never retained.
    return [{k:r.get(k) for k in ('id','name','method','projectId','app')} for r in rows]

def proof_connection():
    rows=[r for r in proof_connections() if r['id']==created.get('connection')]
    require(len(rows)==1, 'Proof connection missing/duplicate')
    r=rows[0]
    require(r['name']==PROOF_CONN_NAME and r['method']=='project-token' and r['projectId']==P
        and r['app']=='railway', 'Proof connection scope mismatch')
    return r

def create_proof_connection():
    # Railway project token for the disposable project only; it dies with projectDelete. Memory only.
    proof_scope()
    require(not any(r['name']==PROOF_CONN_NAME for r in proof_connections()), 'Proof connection already exists')
    f=pin_field('Mutation','projectTokenCreate')
    require(dict(f[2])=={'input':'ProjectTokenCreateInput!'} and base_type(f)=='String', 'Project token schema drift')
    for name in ('projectId','environmentId','name'): pin_field('ProjectTokenCreateInput',name)
    token=safe(gql,'mutation($i:ProjectTokenCreateInput!){projectTokenCreate(input:$i)}',
        {'i':{'projectId':PROOF_PROJECT_ID,'environmentId':PROOF_ENV_ID,'name':PROOF_CONN_NAME}})['projectTokenCreate']
    try:
        require(isinstance(token,str) and bool(token), 'Project token missing')
        created['connection_attempted']=True
        result=http_mutation('connection-create','POST','/api/v1/app-connections/railway',
            body={'name':PROOF_CONN_NAME,'method':'project-token','projectId':P,'credentials':{'apiToken':token}})
        created['connection']=text_id(result['appConnection']['id'])
        del result
    finally:
        del token
    return proof_connection()

def delete_proof_connection():
    proof_connection()
    require(not any(r.get('connectionId')==created['connection'] for r in safe(syncs)), 'Proof connection still used by a sync')
    result=http_mutation('connection-delete','DELETE','/api/v1/app-connections/railway/'+urllib.parse.quote(created['connection'],safe=''))
    require(result['appConnection']['id']==created['connection'], 'Deleted connection response mismatch')
    require(not any(r['id']==created['connection'] for r in proof_connections()), 'Proof connection still present')
```

```python
# Run once after reviewed pins and §2.0 preflight; no production mutations.
PE='staging'; PROOF_PATH='/s1764-proof'; PROOF_NAME='s1764-nodeploy-proof'; PROOF_CONN_NAME='s1764-proof-railway'
created={}; receipt=[]; failure=None; teardown_failed=False; receipt_write_failed=False; proof_class='setup'
production_sync_before=None; IMAGE_DIGEST=None

def create_proof_secret():
    created['secret_attempted']=True
    result=proof_api('POST','/api/v4/secrets/S1764_PROOF',body={'projectId':P,'environment':PE,
        'secretPath':PROOF_PATH,'secretValue':secrets.token_urlsafe(32),'type':'shared','skipMultilineEncoding':True})
    created.setdefault('secrets',{})['S1764_PROOF']=text_id(result['secret']['id'])

def create_proof_child_folder():
    created['child_attempted']=True
    return http_mutation('folder-create','POST','/api/v2/folders',
        body={'projectId':P,'environment':PE,'name':'child','path':PROOF_PATH},created_key='child')

def recover_infisical_creates():
    global PROOF_SYNC_ID
    if created.get('sync_attempted') and 'sync' not in created:
        rows=[r for r in safe(syncs) if r.get('name')==PROOF_NAME
            and (r.get('environment') or {}).get('slug')==PE
            and (r.get('folder') or {}).get('path')==PROOF_PATH]
        require(len(rows)<=1, 'Ambiguous proof sync; cleanup refused')
        if rows:
            PROOF_SYNC_ID=text_id(rows[0]['id']); created['sync']=PROOF_SYNC_ID
            proof_sync(PROOF_SYNC_ID)  # normal destination/source checks before cleanup
    for key,parent,name in (('folder','/','s1764-proof'),('child',PROOF_PATH,'child')):
        if created.get(key+'_attempted') and key not in created:
            rows=[r for r in proof_folders(parent) if r['name']==name]
            require(len(rows)<=1, 'Ambiguous proof folder; cleanup refused')
            if rows: created[key]=text_id(rows[0]['id'])
    if created.get('connection_attempted') and 'connection' not in created:
        rows=[r for r in proof_connections() if r['name']==PROOF_CONN_NAME]
        require(len(rows)<=1, 'Ambiguous proof connection; cleanup refused')
        if rows: created['connection']=text_id(rows[0]['id'])
    if created.get('secret_attempted') and not created.get('secrets'):
        rows=proof_secret_rows()
        require(len(rows)<=1, 'Ambiguous proof secret; cleanup refused')
        if rows: created['secrets']={'S1764_PROOF':text_id(rows[0]['id'])}

def proof_secret_rows():
    rows=safe(api,'GET','/api/v4/secrets',{'projectId':P,'environment':PE,'secretPath':PROOF_PATH,
        'viewSecretValue':'false','recursive':'false','includeImports':'false','expandSecretReferences':'false'})['secrets']
    require(isinstance(rows,list) and all(isinstance(r,dict) for r in rows), 'Secret inventory drift')
    return [r for r in rows if r.get('secretKey')=='S1764_PROOF' and r.get('type')=='shared']

def teardown(label,ids,action):
    global teardown_failed
    try:
        action()
        receipt.append({'operation':label,'ids':ids,'result':'PASS'})
    except Exception:
        teardown_failed=True
        receipt.append({'operation':label,'ids':ids,'result':'FAIL'})

def cleanup_sync(disable):
    if any(r.get('id')==created['sync'] for r in safe(syncs)):
        if disable: disable_proof_sync()
        else: delete_proof_sync()

def cleanup_connection():
    if any(r['id']==created['connection'] for r in proof_connections()):
        delete_proof_connection()

def cleanup_secret(name,secret_id):
    rows=safe(api,'GET','/api/v4/secrets',{'projectId':P,'environment':PE,'secretPath':PROOF_PATH,
        'viewSecretValue':'false','recursive':'false','includeImports':'false','expandSecretReferences':'false'})['secrets']
    if any(r.get('id')==secret_id and r.get('secretKey')==name for r in rows):
        proof_api('DELETE','/api/v4/secrets/'+urllib.parse.quote(name,safe=''),
            body={'projectId':P,'environment':PE,'secretPath':PROOF_PATH,'type':'shared'})

def cleanup_folder(key,parent,name):
    if any(r['id']==created[key] and r['name']==name for r in proof_folders(parent)):
        remove_folder(parent,name)

def verify_infisical_absence():
    require(not any(r.get('id')==created.get('sync') for r in safe(syncs)), 'Proof sync remains')
    require(not proof_source_users(), 'Proof source still used')
    folders=proof_folders('/')
    if created.get('secret_attempted') and any(r['name']=='s1764-proof' for r in folders):
        require(not proof_secret_rows(), 'Proof secret remains')
    require(not any(r['id']==created.get('folder') or r['name']=='s1764-proof' for r in folders), 'Proof folder remains')
    require(not any(r['id']==created.get('connection') or r['name']==PROOF_CONN_NAME for r in proof_connections()), 'Proof connection remains')

def production_workspace():
    f=pin_field('Query','project')
    require(dict(f[2]).get('id')=='String!', 'Project query drift')
    pin_field(base_type(f),'workspaceId')
    project=safe(gql,'query($id:String!){project(id:$id){workspaceId}}',{'id':RP})['project']
    require(isinstance(project,dict), 'Production project missing; workspace unavailable')
    return text_id(project.get('workspaceId'))


def workspace_projects():
    # Workspace-scoped, complete inventory; RP is the positive visibility control.
    f=pin_field('Query','projects'); args=dict(f[2])
    require(args.get('workspaceId') in ('String','String!') and args.get('first')=='Int', 'Projects query drift')
    connection=base_type(f)
    edge=base_type(pin_field(connection,'edges')); node=base_type(pin_field(edge,'node'))
    for name in ('id','name'): pin_field(node,name)
    page=base_type(pin_field(connection,'pageInfo')); pin_field(page,'hasNextPage')
    inventory=safe(gql,'query($w:String!){projects(workspaceId:$w,first:100){edges{node{id name}} pageInfo{hasNextPage}}}',
        {'w':W})['projects']
    rows=inventory['edges']
    require(isinstance(rows,list) and all(isinstance(r,dict) and isinstance(r.get('node'),dict)
        and set(r['node'])=={'id','name'} for r in rows), 'Project inventory drift')
    require(inventory['pageInfo']['hasNextPage'] is False and any(r['node']['id']==RP for r in rows),
        'Project listing not authoritative')
    return [r['node'] for r in rows]

def proof_project_by_name():
    matches=[r for r in workspace_projects() if r['name']==PROOF_NAME]
    require(len(matches)<=1, 'Duplicate proof project name; deletion refused')
    if matches: require(text_id(matches[0]['id'])!=RP, 'Production project refused')
    return matches[0] if matches else None

def cleanup_railway_project(ids):
    global PROOF_PROJECT_ID
    if 'project' not in created:
        require(created.get('name_absent_before_create') is True, 'Project name pre-check missing; deletion refused')
        row=proof_project_by_name()
        if row is None: return
        PROOF_PROJECT_ID=text_id(row['id']); created['project']=PROOF_PROJECT_ID
        ids.append(PROOF_PROJECT_ID)
    row=proof_project()
    if isinstance(row,dict) and row.get('workspaceId')!=W:
        receipt.append({'operation':'teardown-project-manual-cleanup','ids':[PROOF_PROJECT_ID],
            'result':'FAIL','note':'Manual cleanup required: disposable project is in the wrong workspace; deletion refused'})
    delete_proof_project()

def verify_railway_absence():
    if created.get('railway_project_attempted'):
        if 'project' in created:
            require(proof_project_absent(), 'Railway project ID absence unproved')
        require(proof_project_by_name() is None, 'Railway project absence unproved')

try:
    W=production_workspace()  # bind once for creation, listing, recovery and absence
    production_sync_before=production_sync_snapshot()
    require(bool(production_sync_before), 'Production sync snapshot empty')
    IMAGE_DIGEST='<operator: rtk docker buildx imagetools inspect nginx:alpine>'
    require(re.fullmatch(r'sha256:[0-9a-f]{64}',IMAGE_DIGEST) is not None, 'Fill the inspected image digest')
    IMAGE='nginx:alpine@'+IMAGE_DIGEST
    f=pin_field('Mutation','projectCreate')
    require(dict(f[2])=={'input':'ProjectCreateInput!'} and base_type(f)=='Project', 'Project creation schema drift')
    pin_field('ProjectCreateInput','name')
    require(base_type(pin_field('ProjectCreateInput','workspaceId'))=='String',
        'Project creation refused: workspaceId unsupported in pinned schema')
    for name in ('id','name'): pin_field('Project',name)
    require(proof_project_by_name() is None, 'Proof project name already exists; creation refused')
    created['name_absent_before_create']=True
    created['railway_project_attempted']=True
    resource=safe(gql,'mutation($i:ProjectCreateInput!){projectCreate(input:$i){id name}}',{'i':{'name':PROOF_NAME,'workspaceId':W}})['projectCreate']
    PROOF_PROJECT_ID=text_id(resource['id']); created['project']=PROOF_PROJECT_ID
    require(isinstance(resource,dict) and set(resource)=={'id','name'} and resource['name']==PROOF_NAME, 'Project create response drift')
    require(PROOF_PROJECT_ID!=RP, 'Production project refused')
    project=proof_project()
    require(isinstance(project,dict) and project.get('workspaceId')==W, 'Created project workspace mismatch; creation refused')
    require(project['id']==PROOF_PROJECT_ID and project['name']==PROOF_NAME and not project['services']['edges'], 'New project readback mismatch')
    envs=project['environments']['edges']; require(isinstance(envs,list) and len(envs)==1, 'Proof must have one environment')
    PROOF_ENV_ID=text_id(envs[0]['node']['id']); PROOF_ENV_NAME=text_id(envs[0]['node']['name'])
    PROOF_PROJECT_NAME=project['name']; require(PROOF_ENV_ID!=RE, 'Production environment refused')
    f=pin_field('Mutation','serviceCreate')
    require(dict(f[2])=={'input':'ServiceCreateInput!'} and base_type(f)=='Service', 'Service creation schema drift')
    for name in ('projectId','name','source'): pin_field('ServiceCreateInput',name)
    source=base_type(pin_field('ServiceCreateInput','source')); pin_field(source,'image')
    for name in ('id','name'): pin_field('Service',name)
    # Project-level lookup/deletion also covers serviceCreate with an unusable response.
    resource=safe(gql,'mutation($i:ServiceCreateInput!){serviceCreate(input:$i){id name}}',
        {'i':{'projectId':PROOF_PROJECT_ID,'name':'proof','source':{'image':IMAGE}}})['serviceCreate']
    PROOF_SERVICE_ID=text_id(resource['id']); created['service']=PROOF_SERVICE_ID
    require(isinstance(resource,dict) and set(resource)=={'id','name'} and resource['name']=='proof', 'Service create response drift')
    PROOF_SERVICE_NAME=resource['name']; proof_scope()
    project=proof_project(); services=project['services']['edges']
    require(len(services)==1 and services[0]['node']==resource and project['environments']['edges']==envs, 'Disposable IDs/names readback mismatch')
    # Wait for initial image deployment to finish; missing IDs/status drift still refuse.
    deadline=time.monotonic()+600
    while time.monotonic()<deadline:
        node=latest_deployment(PROOF_PROJECT_ID,PROOF_ENV_ID,PROOF_SERVICE_ID)
        if node['status']=='SUCCESS': break
        require(node['status'] in {'INITIALIZING','QUEUED','BUILDING','DEPLOYING'}, 'Initial deployment failed/unknown status')
        time.sleep(5)
    else: raise RuntimeError('Initial deployment timeout')
    require(verify_upsert_shape(), 'Collection upsert schema drift')
    require(base_type(pin_field('Mutation','variableCollectionUpsert'))=='Boolean', 'Upsert result type drift')
    for name in ('projectId','environmentId','serviceId','variables','replace','skipDeploys'):
        pin_field('VariableCollectionUpsertInput',name)
    proof_class='setup-variables'
    before=proof_deployment_id()
    items={'S1764_PROOF_REMOVE':'disposable','S1764_PROOF_TARGET':'reference-target',
           'S1764_PROOF_REFERENCE':'${{proof.S1764_PROOF_TARGET}}'}
    result=safe(gql,'mutation($i:VariableCollectionUpsertInput!){variableCollectionUpsert(input:$i)}',
        {'i':{'projectId':PROOF_PROJECT_ID,'environmentId':PROOF_ENV_ID,'serviceId':PROOF_SERVICE_ID,
              'variables':items,'replace':False,'skipDeploys':True}})
    if result.get('variableCollectionUpsert') is True:
        created['variables']={name:PROOF_SERVICE_ID for name in items}
    require(result.get('variableCollectionUpsert') is True, 'Setup variable mutation unconfirmed')
    raw=proof_variables_raw(PROOF_SERVICE_ID); effective=proof_variables_effective(PROOF_SERVICE_ID)
    require(all(raw.get(k)==v for k,v in items.items()) and effective.get('S1764_PROOF_REFERENCE')==items['S1764_PROOF_TARGET'], 'Same-service reference setup failed')
    after=proof_deployment_id()
    receipt.append({'operation':'setup-variables','before_deployment_id':before,'after_deployment_id':after,
        'project_id':PROOF_PROJECT_ID,'environment_id':PROOF_ENV_ID,'service_id':PROOF_SERVICE_ID,'image_digest':IMAGE_DIGEST,
        'result':'PASS' if before==after else 'RESTART'})
    require(before==after, 'Setup variables must move to Step 5')
    require(not any(r['name']=='s1764-proof' for r in proof_folders('/')), 'Proof folder already exists')
    # Folder POST: connector_signing_keyset.py run(); self-hosted request/response shapes still require review.
    proof_class='proof-folder-create'
    created['folder_attempted']=True
    result=http_mutation('folder-create','POST','/api/v2/folders',body={'projectId':P,'environment':PE,'name':'s1764-proof','path':'/'},created_key='folder')
    require(isinstance(result,dict) and isinstance(result.get('folder'),dict) and result['folder'].get('name')=='s1764-proof', 'Folder create response drift')
    require(len([r for r in proof_folders('/') if r['name']=='s1764-proof' and r['id']==result['folder'].get('id')])==1, 'Folder create readback mismatch')
    proof_class='proof-connection-create'
    create_proof_connection()
    run_disposable_proof()
except Exception as exc:
    failure=exc
    receipt.append({'operation':proof_class,'result':'RESTART','disposition':'Step 5'})
finally:
    if any(created.get(k+'_attempted') for k in ('sync','folder','child','secret','connection')):
        teardown('teardown-infisical-recovery',[],recover_infisical_creates)
    if 'sync' in created:
        teardown('teardown-sync-disable',[created['sync']],lambda: cleanup_sync(True))
        teardown('teardown-sync-delete',[created['sync']],lambda: cleanup_sync(False))
    if 'connection' in created:
        teardown('teardown-connection-delete',[created['connection']],cleanup_connection)
    for name,secret_id in reversed(list(created.get('secrets',{}).items())):
        teardown('teardown-secret-delete',[secret_id],lambda n=name,i=secret_id: cleanup_secret(n,i))
    if 'child' in created:
        teardown('teardown-child-delete',[created['child']],lambda: cleanup_folder('child',PROOF_PATH,'child'))
    if 'folder' in created:
        teardown('teardown-folder-delete',[created['folder']],lambda: cleanup_folder('folder','/','s1764-proof'))
    if created.get('railway_project_attempted'):
        ids=[created['project']] if 'project' in created else []
        teardown('teardown-project-delete',ids,lambda: cleanup_railway_project(ids))
    teardown('teardown-infisical-absence',[],verify_infisical_absence)
    teardown('teardown-railway-absence',[created['project']] if 'project' in created else [],verify_railway_absence)
    if production_sync_before is not None:
        teardown('teardown-production-sync-invariant',[],
            lambda: require(production_sync_snapshot()==production_sync_before, 'Production sync invariant failed'))
    try:
        # Persist names/IDs/status only, including failures; never serialize exceptions or values.
        import datetime, getpass
        operations=[{**r,'disposition':'Step 2' if r['result']=='PASS' else 'Step 5'}
            for r in receipt if not r['operation'].startswith('teardown-')]
        dispositions={r['operation']:('Step 5' if any(x['disposition']=='Step 5'
            for x in operations if x['operation']==r['operation']) else 'Step 2') for r in operations}
        restricted={'actor':getpass.getuser(),'utc_time':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'infisical':{'host':'secrets.ai.market','project_id':P,'environment':PE,'path':PROOF_PATH},
            'railway':{'project_name':PROOF_NAME,'project_id':created.get('project'),
                'environment_id':globals().get('PROOF_ENV_ID'),'environment_name':globals().get('PROOF_ENV_NAME'),
                'service_name':'proof','service_id':created.get('service'),
                'proof_connection_name':PROOF_CONN_NAME,'proof_connection_id':created.get('connection'),
                'image_digest':IMAGE_DIGEST if isinstance(IMAGE_DIGEST,str) and re.fullmatch(r'sha256:[0-9a-f]{64}',IMAGE_DIGEST) else None},
            'infisical_version_informational':INFISICAL_VERSION if isinstance(INFISICAL_VERSION,str) else None,
            'schema_api_pins':{
                'railway_gql_fields':[{'type_name':t,'field_name':n} for t,n in sorted(REVIEWED_GQL)]},
            'operations':operations,'teardown':[r for r in receipt if r['operation'].startswith('teardown-')],
            'dispositions':dispositions,'teardown_failed':teardown_failed}
        os.umask(0o077)
        receipt_path=Path('/Users/max/koskadeux-state/s1771/s1764-nodeploy-proof.json')
        receipt_path.parent.mkdir(parents=True,exist_ok=True)
        with receipt_path.open('w') as out:
            os.fchmod(out.fileno(),0o600)
            json.dump(restricted,out,indent=2); out.write('\n')
    except Exception:
        receipt_write_failed=True
    if failure is not None and teardown_failed:
        raise RuntimeError('proof failed and teardown failed; see receipt') from failure
    elif failure is not None: raise failure from None
    elif teardown_failed: raise RuntimeError('Teardown or absence verification failed; see receipt')
    elif receipt_write_failed: raise RuntimeError('receipt write failed')

```

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

**Superseded for execution by §2.5 (S1771):** the folder, canary, forced-sync, resource-sync and secret-write mutations below run only through §2.5b in a restart window. From this section, run only the definitions block and its pre-write reconcile.

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
        # S1771: self-hosted Infisical v0.161.11 does not return includeAllSubFolders for Railway syncs, even when
        # created with False. For the resource sync, omission is accepted only with a flat source (no child folders);
        # root non-recursion into /connector-resource is proven by the §2.5b canary forced-sync.
        if include=='omitted' and name=='railway-connector-resource-prod':
            children=api('GET','/api/v2/folders',{'projectId':P,'environment':E,'path':'/connector-resource'})['folders']
            assert after and isinstance(children,list) and not children
        else:
            assert include is False or include=='omitted'
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

Read back sync ID, source path/env, connection, target ID, auto-sync and options. Create the new sync with explicit `includeAllSubFolders:false`. Enabled recursion stops. Infisical v0.161.11 omits this field on readback for every Railway sync (S1771), so omission is accepted only while `/connector-resource` has no child folders; the §2.5b canary proves the root sync does not reach this folder. Wait for its first successful job; then assert `DATABASE_URL` and `REDIS_URL` remain present on `rv(RES)` (names only) and canary absent everywhere. Generate three independent `secrets.token_urlsafe(48)` values in process; write `SECRET_KEY` to `/connector-auth`, a different `SECRET_KEY` and `CONNECTOR_AUDIT_HMAC_KEY` to `/connector-resource`, each by `POST /api/v4/secrets/<name>` with `projectId`, `environment`, exact `secretPath`, `secretValue`, `skipMultilineEncoding=True`, `type='shared'`. Run `reconcile_active_sync_values(after=True)` before each write. Write one at a time, wait for the corresponding sync job to succeed, check names/fingerprints, run `closed_stage()` and compare deployment IDs, and receipt each separately. Never change `CONNECTOR_OAUTH_SIGNING_KEYS` or its auth sync. Do not create a root sync or use local-secops' generic executor for `/connector-auth`.

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

For a removal, fetch the **entire current service variable name set** through `rv(service)` in the protected interpreter. Fetch each name's raw value through the live-introspected Railway metadata readback `raw_reference(service,name)`; this must return the literal value or the unchanged raw `${{...}}` reference, never a resolved reference value. Assert the raw metadata names equal `rv(service).keys()`, and refuse if any raw value is missing, unreadable or of unknown shape. Re-read immediately before mutation; refuse concurrent name/value drift. Form `variables` as exactly that protected-memory mapping minus the named removals (or with exact prior values restored for a mixed rollback). Apply one `variableCollectionUpsert` with `replace:true, skipDeploys:true`, then assert readback names equal the expected set, retained raw references and their rendered values equal their originals, retained literal values match in protected memory, and **all four** production deployment IDs equal the baseline. Do not log values. This operation is permitted only for `ai-market-connector` (`RES`) and `ai-market-connector-auth` (`AUTH`), never `ai-market-backend` (`BACK`) or `issue-channel-watcher` (`WATCH`). A backend-only new variable requiring deletion moves with its dependent forward action to Step 5's restart window; do not extend this helper's allow-list.

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
    assert rv(service)==effective
    assert {k:raw_reference(service,k) for k in names}==raw
    references={k for k in expected if k in raw and raw[k].startswith('${{')}
    assert all(effective[k]!=raw[k] for k in references)  # resolved before mutation
    gql('mutation($input:VariableCollectionUpsertInput!){variableCollectionUpsert(input:$input)}',
        {'input':{'projectId':RP,'environmentId':RE,'serviceId':service,
                  'variables':expected,'replace':True,'skipDeploys':True}})
    assert set(rv(service))==set(expected)
    assert {k:raw_reference(service,k) for k in expected}==expected
    after=rv(service)
    assert all(after[k]==effective[k] and after[k]!=raw[k] for k in references)
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

### 2.5 Restart-window execution (S1771)

**Why:** the §2.0 proof (S1771 run 2, Event `e4a8b7f1`, receipt `s1764-nodeploy-proof.json`) showed `variableCollectionUpsert(skipDeploys:true)` leaves the deployment unchanged (**Step 2**), but an Infisical native Railway `sync-create` redeployed its destination (**Step 5**). Every §2.2 action that runs or can trigger a sync job (folder create, canary write/delete, forced syncs, resource sync create, the three secret writes) therefore moves, with its rollback, to a Max-approved restart window, as §2.0 requires. **§2.2's inline mutation steps and its resource-sync code block are superseded by this section**; keep only §2.2's definitions and pre-write reconcile. §2.1's DSN and all §2.3 variable upserts stay Step 2 and run first with unchanged-deployment checks; they take effect at the target's next redeploy in the window. Flags and the global switch stay off throughout. Targets may redeploy during the window (the forced root sync can redeploy the backend for about a minute); a target that Railway leaves unchanged is also accepted.

**One execution sequence** in one protected interpreter: §2.0 definitions and preflight → §2.0.1 definitions with the reviewed pins (add `Query.serviceInstance` and `ServiceInstance.numReplicas`) → §2.1 DSN block → §2.5a → §2.2 definitions and pre-write reconcile → §2.5b (window) → §2.3 final readback block → §2.5c. Nothing is complete until §2.5c passes.

**Journal and failure handling.** `window_action` journals each action as `attempted` before its mutation and `completed` after its sync job, deployments and health pass. On any failure after dispatch it records `failed`, waits up to ten minutes for deployments to settle, re-baselines `BASE_DEPLOYMENTS` to the observed IDs (so §2.4's guards compare against reality) and stops with no further forward writes. Roll back the **failed** action first, then earlier actions in reverse, per §2.4. In the window, wrap each rollback that can run a sync job in `window_action` with the same target. A Railway name removal uses §2.4's guarded replacement; because its disposable rehearsal did not run (the proof stopped at `sync-create`), inside the window `variableDelete` of the exact named resource/auth variable is permitted instead, wrapped in `window_action` with that service as target. The watcher has no public HTTP endpoint: its check is deployment `SUCCESS` plus its existing issue-channel health monitoring, which the operator confirms after the window.

```python
# §2.5a — Step 2 upserts (no redeploy), after §2.1's DSN block.
assert 'REDIS_URL' not in rv(RES) and 'REDIS_URL' not in rv(AUTH)
put(RES,{'REDIS_URL':'${{Redis.REDIS_URL}}'})  # live service is literally `Redis` and exposes REDIS_URL (S1771)
print(RES,'REDIS_URL vs backend REDIS_URL','MATCH' if rv(RES)['REDIS_URL']==rv(BACK)['REDIS_URL'] else 'DIFFERENT')
assert 'REDIS_URL' not in rv(AUTH)
backend=rv(BACK)
assert backend.get('LISTING_LICENSES_ENABLED')=='true' and backend.get('X402_ENABLED')=='false' and backend.get('TERMS_1_1_EFFECTIVE_AT')
backend_terms=backend['TERMS_1_1_EFFECTIVE_AT']; del backend
f=pin_field('Query','serviceInstance'); pin_field('ServiceInstance','numReplicas')
replicas=safe(gql,'query($e:String!,$s:String!){serviceInstance(environmentId:$e,serviceId:$s){numReplicas}}',{'e':RE,'s':RES})['serviceInstance']['numReplicas']
assert replicas==2 and rv(RES).get('CONNECTOR_WORKERS','2')=='2', 'Resource process topology drift'
PRIOR_NAMES={s:sorted(k for k in rv(s) if k in {'LISTING_LICENSES_ENABLED','TERMS_1_1_EFFECTIVE_AT','X402_ENABLED',
    'CONNECTOR_EXPECTED_PROCESSES','CONNECTOR_AUTH_FAILURE_MAX_IPS','OTEL_SERVICE_NAME',
    'CONNECTOR_EARLY_ACCESS_ENFORCED','CONNECTOR_EARLY_ACCESS_USER_IDS'}) for s in (RES,AUTH,BACK)}
# Protected-memory raw prior values for §2.4 exact restore (absent names = remove on rollback). Never printed or saved.
PRIOR_VALUES={s:{k:raw_reference(s,k) for k in names} for s,names in PRIOR_NAMES.items()}
put(RES,{'LISTING_LICENSES_ENABLED':'true','TERMS_1_1_EFFECTIVE_AT':backend_terms,'X402_ENABLED':'false'})
del backend_terms
put(RES,{'CONNECTOR_EXPECTED_PROCESSES':'4','CONNECTOR_AUTH_FAILURE_MAX_IPS':'10000','OTEL_SERVICE_NAME':'ai-market-connector'})
for s in (RES,AUTH,BACK):  # backend puts are skipDeploys; they apply at the backend redeploy in the window
    put(s,{'CONNECTOR_EARLY_ACCESS_ENFORCED':'true','CONNECTOR_EARLY_ACCESS_USER_IDS':''})

def require_step2_settings():
    res=rv(RES); back=rv(BACK)
    for k in ('LISTING_LICENSES_ENABLED','TERMS_1_1_EFFECTIVE_AT','X402_ENABLED'):
        require(res.get(k)==back.get(k), 'Licensing trio differs from backend: '+k)
    require(res.get('LISTING_LICENSES_ENABLED')=='true' and res.get('X402_ENABLED')=='false', 'Licensing trio drift')
    require(res.get('CONNECTOR_EXPECTED_PROCESSES')=='4' and res.get('CONNECTOR_AUTH_FAILURE_MAX_IPS')=='10000'
        and res.get('OTEL_SERVICE_NAME')=='ai-market-connector', 'Resource settings drift')
    require(res.get('CONNECTOR_AUTH_ISSUER')=='https://auth.ai.market' and res.get('CONNECTOR_AUDIENCE')=='https://connect.ai.market/mcp'
        and res.get('CONNECTOR_JWKS_URL')=='https://auth.ai.market/.well-known/jwks.json', 'Issuer/audience/JWKS drift')
    require(isinstance(res.get('DATABASE_URL'),str) and res['DATABASE_URL'] and raw_reference(RES,'REDIS_URL')=='${{Redis.REDIS_URL}}', 'Resource DSN/Redis missing')
    for s,vals in ((RES,res),(AUTH,rv(AUTH)),(BACK,back)):
        require(vals.get('CONNECTOR_EARLY_ACCESS_ENFORCED')=='true', 'Early access not enforced')
        ids=vals.get('CONNECTOR_EARLY_ACCESS_USER_IDS')
        require(ids is not None and hashlib.sha256(ids.encode()).digest()==hashlib.sha256(b'').digest(), 'Allowlist not empty')
    print('step2 settings exact; allowlist count 0 on backend/auth/resource')
require_step2_settings()
```

```python
# §2.5b — run only inside the Max-approved restart window, after §2.2's definitions and pre-write reconcile.
import time
window=[]
HEALTH={BACK:[('https://api.ai.market/health',200)],
        AUTH:[('https://auth.ai.market/readyz',200)],
        RES:[('https://connect.ai.market/healthz',200),('https://connect.ai.market/mcp',503)],
        WATCH:[]}  # no public endpoint; deployment SUCCESS + existing issue-channel monitoring
def http_status(url):
    req=urllib.request.Request(url,headers={'User-Agent':'connector-step2/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=15) as r: return r.status
    except urllib.error.HTTPError as e: return e.code
    except Exception: return None
def health(service,timeout=300):
    deadline=time.monotonic()+timeout
    for url,code in HEALTH[service]:
        while http_status(url)!=code:
            require(time.monotonic()<deadline, 'Health check failed: '+url)
            time.sleep(10)
def sync_row(name):
    rows=[r for r in syncs() if r.get('name')==name]
    require(len(rows)==1, 'Sync missing/duplicate: '+name)
    return rows[0]
def wait_sync(name,old_job,timeout=600):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        r=sync_row(name); status=r.get('syncStatus'); job=r.get('lastSyncJobId')
        require(status in {'success','succeeded','pending','running'}, 'Sync failed: '+name)
        if job and job!=old_job and status in {'success','succeeded'}: return job
        time.sleep(5)
    raise RuntimeError('Sync job timeout: '+name)
def wait_deploys(before,targets,quiet=None,timeout=900):
    # Targets may redeploy or stay put; non-targets must not change. Empty target sets use a shorter quiet period.
    quiet=(120 if targets else 60) if quiet is None else quiet
    deadline=time.monotonic()+timeout; stable_since=time.monotonic(); last=None
    while True:
        require(time.monotonic()<deadline, 'Deployment wait timeout')
        nodes={s:latest_deployment(RP,RE,s) for s in before}
        for s,n in nodes.items():
            if s not in targets: require(n['id']==before[s], 'Unexpected redeploy of non-target service')
            require(n['status'] not in {'FAILED','CRASHED','REMOVED'}, 'Deployment failed')
        state={s:(n['id'],n['status']) for s,n in nodes.items()}
        if state!=last: stable_since=time.monotonic(); last=state
        settled=all(n['status']=='SUCCESS' for s,n in nodes.items() if s in targets)
        if settled and time.monotonic()-stable_since>=quiet: break
        time.sleep(10)
    for s in targets: health(s)
    return {s:n['id'] for s,n in nodes.items()}
def settle_after_failure(timeout=600):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        nodes={s:latest_deployment(RP,RE,s) for s in (BACK,AUTH,RES,WATCH)}
        if all(n['status'] in {'SUCCESS','FAILED','CRASHED','REMOVED'} for n in nodes.values()):
            return {s:n['id'] for s,n in nodes.items()}
        time.sleep(10)
    return deployment_snapshot()
def window_action(label,targets,fn,sync_name=None):
    global BASE_DEPLOYMENTS
    closed_stage('before-'+label)
    before=deployment_snapshot(); require(before==BASE_DEPLOYMENTS, 'Baseline drift before '+label)
    old_job=sync_row(sync_name).get('lastSyncJobId') if sync_name and any(r.get('name')==sync_name for r in syncs()) else None
    entry={'operation':label,'targets':sorted(targets),'sync':sync_name,'state':'attempted','before':before}
    window.append(entry)
    try:
        fn()
        entry['sync_job_id']=wait_sync(sync_name,old_job) if sync_name else None
        after=wait_deploys(before,set(targets))
        closed_stage('after-'+label)
    except BaseException:
        entry['state']='failed'
        BASE_DEPLOYMENTS=entry['after']=settle_after_failure()
        entry['restarted']=sorted(s for s in before if entry['after'][s]!=before[s])
        raise
    entry.update(state='completed',after=after,restarted=sorted(s for s in before if after[s]!=before[s]))
    BASE_DEPLOYMENTS=after
def destination_names(service):
    return set(rv(service)) if service in (BACK,AUTH,RES) else set(watcher_railway_variables())
CANARY='CONNECTOR_RESOURCE_CANARY_S1764'
def canary_absent_everywhere():
    for s in (BACK,AUTH,RES,WATCH):
        require(CANARY not in destination_names(s), 'Canary leaked to a destination')

reconcile_active_sync_values()
if not any(r['name']=='connector-resource' for r in api('GET','/api/v2/folders',{'projectId':P,'environment':E,'path':'/'})['folders']):
    window_action('resource-folder-create',set(),lambda: api('POST','/api/v2/folders',
        body={'projectId':P,'environment':E,'name':'connector-resource','path':'/'}))
require(not folder('/connector-resource'), 'Resource folder not empty')
reconcile_active_sync_values()
window_action('canary-write',set(),lambda: api('POST','/api/v4/secrets/'+CANARY,body={'projectId':P,
    'environment':E,'secretPath':'/connector-resource','secretValue':secrets.token_urlsafe(32),
    'skipMultilineEncoding':True,'type':'shared'}))
canary_absent_everywhere()
for name,target in (('railway-backend-prod',BACK),('railway-connector-auth-prod',AUTH),
                    ('railway-issue-channel-watcher-events-prod',WATCH)):
    reconcile_active_sync_values()
    sid=sync_row(name)['id']
    window_action('forced-sync-'+name,{target},lambda sid=sid: api('POST',
        '/api/v1/secret-syncs/railway/'+urllib.parse.quote(sid,safe='')+'/sync-secrets'),sync_name=name)
    canary_absent_everywhere()
window_action('canary-delete',set(),lambda: api('DELETE','/api/v4/secrets/'+CANARY,body={'projectId':P,
    'environment':E,'secretPath':'/connector-resource','type':'shared'}))
require(CANARY not in folder('/connector-resource'), 'Canary still in source'); canary_absent_everywhere()

root=require_current_syncs()['railway-backend-prod']
reconcile_active_sync_values()
payload={'name':'railway-connector-resource-prod','projectId':P,
 'connectionId':root['connectionId'],'environment':E,'secretPath':'/connector-resource',
 'isAutoSyncEnabled':True,
 'syncOptions':{'initialSyncBehavior':'overwrite-destination',
                'includeAllSubFolders':False,'disableSecretDeletion':True},
 'destinationConfig':{'projectId':RP,'projectName':'ai-market',
   'environmentId':RE,'environmentName':'production',
   'serviceId':RES,'serviceName':'ai-market-connector'}}
window_action('resource-sync-create',{RES},lambda: api('POST','/api/v1/secret-syncs/railway',body=payload),
    sync_name='railway-connector-resource-prod')
require_current_syncs(after=True)
require({'DATABASE_URL','REDIS_URL'}<=set(rv(RES)), 'Resource URL names missing after sync')
canary_absent_everywhere()

for path,name,target,sync_name in (('/connector-auth','SECRET_KEY',AUTH,'railway-connector-auth-prod'),
                                   ('/connector-resource','SECRET_KEY',RES,'railway-connector-resource-prod'),
                                   ('/connector-resource','CONNECTOR_AUDIT_HMAC_KEY',RES,'railway-connector-resource-prod')):
    reconcile_active_sync_values(after=True)
    require(name not in folder(path), 'Secret already present: '+path+' '+name)
    window_action('secret-write-'+path.strip('/')+'-'+name,{target},lambda path=path,name=name: api('POST',
        '/api/v4/secrets/'+name,body={'projectId':P,'environment':E,'secretPath':path,
        'secretValue':secrets.token_urlsafe(48),'skipMultilineEncoding':True,'type':'shared'}),sync_name=sync_name)
reconcile_active_sync_values(after=True)
print('2.5b window complete:',[(w['operation'],w['state'],w.get('restarted')) for w in window])
```

```python
# §2.5c — completion, after §2.3's final readback block. Step 2 is complete only if this passes.
require_step2_settings()
closed_stage('final')
require_current_syncs(after=True)
require(deployment_snapshot()==BASE_DEPLOYMENTS, 'Deployment drift after window')
require(all(w['state']=='completed' for w in window), 'Window journal incomplete')
print('Step 2 complete; connect /readyz:',http_status('https://connect.ai.market/readyz'))
```

Save `window` and `PRIOR_NAMES` (names/IDs only) with the Step 2 receipt. `PRIOR_VALUES` stays in the protected interpreter for §2.4 restoration (names in `PRIOR_NAMES` restore their exact raw prior value; other §2.5a names are removed) until Step 2 is complete or rolled back; keep admission closed during any restore.

## Gate 4 STEP 3 operator procedure — trusted edge peer (S1786)

This section makes Step 3 executable. It replaces Step 3's "temporary redacted request-ID diagnostic" with an existing equivalent that needs no code change and logs no customer header or IP. Flags and the global switch stay off throughout. It does **not** claim per-replica attribution, the XFF hop count, or whether the edge strips or appends client XFF; §3.4 says what it does prove.

### 3.0 Method: read the limiter bucket itself

For every well-formed `/mcp` GET or POST that passes `_edge_status`, `RequestEdge` (backend main `83e9b8f9`, `app/mcp/connector/asgi.py`) calls `limiter.check("ip", limit_key("ip", ip=state.client_ip))` **before** the switch check. Requests rejected earlier (413, 403, 421) never reach the limiter. `limit_key` returns the IP unchanged and `ratelimit.py` writes the Redis sorted set `conn:rl:v1:ip:<client_ip>` with a 60-second expiry. If Redis is unavailable the limiter uses an in-process fallback and writes no key, so a window only counts when `/readyz` is 200 (Redis healthy) immediately before it. With those conditions, the key is exactly the selected limiter bucket that the pre-auth limiter and auth-failure audit use.

Receipt `koskadeux-state/s1786/receipts/railway-readback-pre.json` (SHA-256 `cd19e1f4c770e17c5e34bba8f61b75f94b7f925d2baf080cf2aa230f92dbbf79`, `ts` 2026-09-30T22:24:40Z, deployment `e0a3e2d0-14cc-4409-a35e-c49b32a82cd2` `SUCCESS`, 2 replicas) records the effective configuration: the start command below, `CONNECTOR_TRUSTED_PROXY_CIDRS`, `FORWARDED_ALLOW_IPS`, `UVICORN_PROXY_HEADERS` and `UVICORN_FORWARDED_ALLOW_IPS` absent, no TCP proxy, and one custom domain. The image (`Dockerfile` runtime stage) sets no forwarded-header environment. The resource start command (`railway.connector.json`) is `uvicorn app.mcp.connector.asgi:app ...` without `--proxy-headers`/`--forwarded-allow-ips`, and `FORWARDED_ALLOW_IPS` is not set; uvicorn trusts forwarded headers only from `127.0.0.1` by default, and the observed peers are not loopback, so `request.client.host` is the real socket peer.

Tools (not runbook tooling; session scripts under `koskadeux-state/s1786/`, pinned by SHA-256):

| File | SHA-256 | Role |
| --- | --- | --- |
| `edge_probe.py` (v2) | `5f6eb2a6f1102fa348246993afaf8730a5d06807fa3a66f68df00c8bbd041acb` | Stdlib probe sender, run from each source. `--label CLOUD\|MAC --window P1..P4`; records `start_epoch`/`end_epoch`; sends 12 `POST /mcp` with body `{"jsonrpc":"2.0","id":1,"method":"ping"}` and the window's `X-Forwarded-For`; records status, JSON-RPC `error.data.error.code`, and `x-request-id` per response. Never prints the source IP. |
| `edge_readback.py` (v4) | `7fd2c999d05d16519cc1962fbd3f92eeba06d49771eb5d67ad90dc300801079b` | Read-only Redis readback, **Koskadeux host only**, `--source CLOUD\|MAC\|NONE --window Pn --phase pre\|post`. Loads `REDIS_PUBLIC_URL` of the `Redis` service through the Railway API (never printed); collects every `conn:rl:v1:ip:*` key with `SCAN` (deduplicated: SCAN may return a key twice), then `ZCARD`, `PTTL`, then classifies; no other network call. `--probe-start EPOCH` adds `probe_start_to_collection_end_seconds`. Reports `public_sum`, `infra_sum`, sentinels, class counts and `scan_seconds`. |
| `run_window.sh` (v4) | `98be7a2cdeebb7d21d291c64ce33ba50e685495ddf9642111320bf11c0dd2769` | Koskadeux wrapper `run_window.sh SOURCE Pn pre\|post [PROBE_START_EPOCH]` (for `MAC` the start is read from its own probe file). `pre`: `/readyz` and a fresh preflight readback. `post`: for `MAC`, `/readyz`, the 12 probes, `/readyz`, readback; for `CLOUD` (probe already sent from the cloud workspace), `/readyz` then readback. Receipts `Pn-SOURCE-{pre,probe,post}.json` and `Pn-SOURCE-readyz.txt`. |
| `apply_step3.py` (v2) | `7108e00d48af57ce1e0360be49b369ba57697277edd958c5a19f9c0de15f59a3` | §3.3 apply and §3.5 rollback (`apply\|rollback\|status`, dry run without `--execute`): one variable change, waits for the replacement deployment, requires `SUCCESS`, 2 replicas and the prior deployment `REMOVED`, then health, and asserts the effective variable (`100.64.0.0/24` after apply, absent after rollback) and `CONNECTOR_ENABLED=false`. |

Readback output rules (v3). Only addresses in the **verified infrastructure set** `100.64.0.0/24` print in full. That is safe because before the CIDR is set every key is a socket peer, and after it is set `_edge_status` skips trusted hops when walking XFF, so a `100.64.0.0/24` value can only be selected as the socket peer itself (an all-trusted chain keeps the peer). The sentinels print as `FORGED_A` (`1.2.3.4`) and `FORGED_B` (`5.6.7.8`). Every public address prints only as `<SOURCE>_PUBLIC` with its count, never the address, and no address is sent to any other service. Other CGNAT, private and non-IP values are only counted by class (`other_cgnat_outside_infra`, `other_private`, `non_ip`).

**Why the method changed after execution 1 (S1786, 2026-10-01 00:43–00:51 CEST).** v1 labelled sources by the address `api.ipify.org` reported. After apply (deployment `a4067faf-7ee6-4bd8-9c62-89c64ead70e2`), window P1 produced **no** `100.64.x` bucket and five public buckets, none equal to either ipify address: the Railway edge supplied real public caller addresses and the right-to-left walk selected them, but the Koskadeux host reaches Railway through a different egress network (RDAP `CDN77-PAR`, rotating across at least two addresses) and the cloud workspace also egresses to Railway from addresses outside the ipify-reported `/24`. (The source networks were identified with ad-hoc read-only scripts `diag_classify.py` and `diag_rdap.py`, which printed classes and RDAP organisation names only; their console output was not kept as a receipt. They sent the probe addresses to `rdap.org`; the pinned tools no longer do.) The v1 exact-count criterion therefore failed, and §3.5 rollback ran (deployment `6404b1b3-4ed1-4577-b34a-44ec02063685` `SUCCESS` with 2 replicas, variable absent, health green, a single-source MAC P1 check with zero public buckets and probes back in `100.64.x` buckets). Prior deployments `a4067faf` and `e0a3e2d0` read `REMOVED` at 22:58Z (`receipts/deployments-after-rollback.json`); the rollback helper did not check that itself in execution 1, and `apply_step3.py` now does. The RB-P1 readback held 17 entries for 12 MAC probes because keys from the P1 window and the diagnostics were still alive, so exclusive accounting of that check is not claimed; it shows only that no probe was bucketed on a public address. Receipts: `koskadeux-state/s1786/receipts/{apply.log,P1-*,rollback.log,RB-P1-*}`. The revised method stops guessing source addresses and uses one source per window, with a fresh preflight read before it; §3.4 states what that does and does not prove.

Sources: `CLOUD` reaches Railway edge `iad1`; `MAC` is the Koskadeux host in Madrid. `connect.ai.market` is served directly by Railway (`server: railway-hikari`, `x-railway-edge`); Cloudflare is not in front.

### 3.1 Baseline measured (S1786, no CIDR set)

Receipts `koskadeux-state/s1786/receipts/BASE-*.json` (2026-09-30T22:20Z): 12 POSTs per source, all 503 `CONNECTOR_DISABLED`. The readback shows 14 buckets, all in `100.64.0.2`–`100.64.0.23`, no `CLOUD` or `MAC` bucket, and zero redacted values. The 27 bucket entries exceed the 24 recorded probes because the operator sent three ad-hoc POSTs (tool test and response-shape check) inside the same 60-second window, so exclusive attribution for that baseline is not claimed; it only shows that no bucket was a source address. An earlier unrecorded read the same night (48 GETs, 21 peers `100.64.0.2`–`.22`) agreed. Consequence today: every caller is bucketed by whichever Railway edge proxy carried it, so about 20 shared buckets serve the whole internet and a few busy clients could rate-limit everyone. Step 3 is required before enable.

Railway's own statements conflict (community thread "Edge Proxy X-Forwarded-For and X-Real-Ip can't be trusted": the rightmost XFF value is the real client; thread "Security-Critical Questions on Edge Proxy Header Handling": the edge strips client XFF and "the first value is the real connecting IP"). The probe decides; neither statement is assumed.

### 3.2 CIDR choice

Set `CONNECTOR_TRUSTED_PROXY_CIDRS=100.64.0.0/24` on `ai-market-connector` only. It covers every observed peer with headroom and is far narrower than `100.64.0.0/10`, RFC 1918, or Cloudflare ranges. Public ingress is Railway's HTTP edge only: the pre-apply receipt shows no TCP proxy (`tcpProxies: []`), no Railway service domain, and one custom domain (`connect.ai.market`). The claim is limited to that: public callers reach the container only through the Railway edge, whose socket peers were observed in `100.64.0.2`–`.23`. Other services in our own Railway project can reach the container over private networking; they are our own services, not untrusted callers. A caller able to originate traffic from inside Railway's infrastructure is outside this threat model, and such a caller could already bypass the pre-auth limiter by rotating edges. Within that boundary, an untrusted public caller cannot present a `100.64.0.0/24` socket peer. The failure modes are asymmetric: a future edge peer outside the /24 is untrusted, so its callers fall back to that peer's shared bucket (today's behaviour: over-limiting, never a bypass). Step 7 smoke re-runs the readback; a nonzero `other_cgnat_outside_infra` count with all traffic accounted for is the signal to widen by a reviewed change.

### 3.3 Apply

First satisfy the §3.4a region prerequisite. Before: record the resource's current deployment ID, `CONNECTOR_TRUSTED_PROXY_CIDRS` absent, `CONNECTOR_ENABLED=false`, and the global row disabled (owner-session read per switch administration). Then, with `apply_step3.py apply --execute` (run `apply_step3.py apply` first as a dry run), one Railway `variableCollectionUpsert` on the resource (`a08ef347-d2d1-4fcb-ba50-9299a9484fd5`, environment `23e322c3-b195-45d8-9151-c4c27a998c33`) with `skipDeploys:false`. That redeploys **only** `ai-market-connector`. It has no Infisical write, so no sync job runs and no other service restarts; the resource is dark. Wait for the new deployment `SUCCESS` with `numReplicas` 2, read back the effective (rendered) variable, then run the "Verify after a resource deploy" checks in `customer-mcp-connector.md` with `/readyz` 200. No Max restart window is needed because no customer-serving service restarts.

### 3.4 Probe and pass criteria

Run eight single-source windows in order: P1–P4 from `CLOUD`, then P1–P4 from `MAC`. For every window:

1. **Preflight.** Wait at least 65 seconds after the previous window's last request, then run `run_window.sh SOURCE Pn pre`. It must show `/readyz` 200, `public_sum` 0, no sentinel and `non_ip` 0; otherwise wait 65 seconds and repeat the preflight (this also applies before the first window).
2. **Probe.** `CLOUD`: in the cloud workspace run `mkdir -p receipts && edge_probe.py --label CLOUD --window Pn > receipts/Pn-CLOUD-probe.json`, then immediately `run_window.sh CLOUD Pn post <start_epoch from that probe file>` on Koskadeux (host clocks are NTP-synchronised; skew measured under 1 s); copy the probe file into `koskadeux-state/s1786/receipts/` before §3.6. `MAC`: `run_window.sh MAC Pn post` (probes and reads back in one step).
3. **Decide** with the table below, first matching row wins.

| # | Condition | Outcome |
| --- | --- | --- |
| 1 | Any probe response not 503 `CONNECTOR_DISABLED`; `/readyz` not 200 before or after; or `probe_start_to_collection_end_seconds` missing or over 45 (the limiter keys live 60 s, so a longer window could lose early probes) | **Void**: rerun the window |
| 2 | Any `FORGED_A`, `FORGED_B` or `non_ip` bucket | **Fail**: §3.5 at once |
| 3 | `public_sum` above 12 (or, in P3, `public_sum` + `infra_sum` above 12) | **Void** (unrelated caller): rerun |
| 4 | P1, P2 or P4 with `infra_sum`, `other_cgnat_outside_infra` or `other_private` above 0 | **Fail**: §3.5 at once (a probe was bucketed on an edge or internal peer, including one outside the trusted /24; widen only by a reviewed change) |
| 5 | `public_sum` + `infra_sum` below 10 (fewer than 10 of 12 probes reached Redis; the rest took the limiter's local fallback) | **Void**: rerun |
| 6 | P1, P2, P4: `public_sum` 10–12 and `infra_sum` 0. P3: `public_sum` + `infra_sum` 10–12 (record the split) | **Pass** |

In P3, nonzero `other_private` or `other_cgnat_outside_infra` counts are recorded and investigated before the window can pass. A nonzero `other_cgnat_outside_infra` count is also the §3.2 widen signal. A window voided three times in a row stops execution (no rollback needed) for investigation.

What a pass proves, and what it does not. With the CIDR set, a probe whose client-supplied `X-Forwarded-For` the edge passed through unchanged would have the forged value selected (right-to-left walk, forged value rightmost and untrusted) and would appear as `FORGED_A`/`FORGED_B`. A P1, P2 or P4 pass (every recorded probe public, rows 4 and 6) therefore shows that, for the Redis-recorded probes from two egress networks, the selected bucket was a public address that was not the forged value and not the edge peer. A P3 pass shows only that unparseable client XFF never became a bucket name: its probes land either on a public address or, by design (`asgi.py` `ValueError` fallback), on the edge peer, and the split is recorded. This does not depend on knowing the source's address. It does **not** identify which public address belongs to the source, because egress to Railway differs from what IP echo services report. It assumes no unrelated caller and no limiter fallback during the window: the preflight, the `/readyz` checks and the exact counts make that unlikely on the dark endpoint but cannot exclude a coincidence such as one probe falling back while an unrelated caller writes one key. That coincidence cannot hide a sentinel from the other Redis-recorded probes of the same window. A probe whose limiter check takes the local fallback (any exception, including the 100 ms `asyncio.wait_for` budget in `ratelimit.py` `check`) makes no further Redis write, although a timed-out `EVAL` may already have written its key; rows 5 and 6 therefore require at least 10 of the 12 probes to be recorded, and every recorded probe is checked. If the edge passed client XFF through, every recorded P2/P4 probe would select the forged value, so any recorded probe exposes it; unrelated traffic cannot mask a sentinel either. It also does not distinguish stripping from appending, measure the hop count, or prove which replica served each request; those stay recorded as not measured. Both replicas run the same image and variables, and per-replica attribution would need a code change. Not reachable, recorded as such: an untrusted direct socket peer (no TCP proxy; `_peer_trusted` false path covered by backend unit tests) and a client-originated all-trusted-hop chain.

### 3.4a Region prerequisite (execution 2 finding, S1786)

Execution 2 (2026-10-01 01:24–01:30 CEST, receipts `koskadeux-state/s1786/receipts/{apply-exec2.log,exec2/,rollback-exec2.log,rbcheck/}`) applied the CIDR (deployment `4c33080b-522f-4fa1-b83c-cf7fd163d6b2`). CLOUD P1 then recorded only 3 of 12 probes, all in public buckets and none on the edge peer. The previous row 4 made that a fail, so §3.5 rolled back (deployment `5b7960e0-7f0d-496c-88a3-a81a1b50b92a`, variable absent, prior deployment `REMOVED`). Two MAC P1 checks after rollback recorded 6 and 8 of 12 probes in peer buckets; the preflight before the first of them already held one peer entry, so exclusive attribution of that check is not claimed. Recording loses probes with or without the CIDR.

Placement is the leading hypothesis, not a measured cause. Receipt `placement-pre.json` (23:38Z) shows `ai-market-connector` and `ai-market-connector-auth` in `us-east4-eqdc4a`, while `Redis`, `Postgres` and `ai-market-backend` are in `us-west2`. Each connector service is also running **one** instance, although its `numReplicas` setting is 2 and `CONNECTOR_EXPECTED_PROCESSES=4` assumes two. Neither connector service has a volume. A cross-continent round trip would push many limiter `EVAL`s past the 100 ms budget. The test of the hypothesis is the before/after recording rate below.

**Move (tool `region_move.py`, SHA-256 `301674202fb3e2903c3ca270298ea98858d54bd763d6a77c5dc82da92c9cc3cd`, journal `receipts/region-journal.jsonl`).** Run `region_move.py move-west` first as a dry run. The dry run reports the dark and auth precheck and the captured prior configuration. Then run `region_move.py move-west --execute`. For each service in turn (resource, then auth), the tool:

1. journals the step, then runs `serviceInstanceUpdate multiRegionConfig {"us-west2": {"numReplicas": 2}}`;
2. triggers `serviceInstanceRedeploy` if no new deployment appears within 45 seconds;
3. accepts the move only when the live deployment is `SUCCESS`, its manifest lists exactly `us-west2`, exactly two instances are `RUNNING` (bounded at 15 minutes), and any replaced deployment reads `REMOVED`.

After both services are accepted, the dark and auth checks must pass again:

- resource `/healthz`, `/readyz` and protected-resource metadata return 200, and `/mcp` returns 503 `CONNECTOR_DISABLED`;
- resource `CONNECTOR_ENABLED=false`;
- auth `/readyz` and JWKS return 200, and the JWKS `kid` and RFC 7638 thumbprints equal `auth-baseline-pre.json`;
- auth OAuth metadata, `/register` and `/authorize` return 404;
- auth `CONNECTOR_OAUTH_ENABLED`, `CONNECTOR_CIMD_ENABLED` and `CONNECTOR_DCR_ENABLED` are all `false`;
- `api.ai.market/health` returns 200 and the connector-oauth status returns `enabled:false` (the backend does not move; this confirms the website consent owner stays dark).

On any failure, the tool restores every service it already changed to its captured prior configuration, using the same acceptance rule, reruns the checks and stops. `region_move.py restore --execute` restores both services by hand. Custom domains and DNS are unchanged. Signing keys and Infisical syncs are not touched.

**Prerequisite pass.** Run two single-source MAC P1 checks without the CIDR, each with a fresh preflight. The prerequisite passes only if both show `public_sum` 0, `other_private` and `other_cgnat_outside_infra` 0, and at least 11 of 12 probes recorded in `100.64.x` peer buckets (`infra_sum` 11–12), compared with 6 and 8 before the move. The bar is one probe stricter than the windows' 10 because it tests the cause itself: after colocation, fallback should be rare. If the checks fail, run `restore --execute` and stop Step 3 for a reviewed limiter-timeout change. With two instances running, `CONNECTOR_EXPECTED_PROCESSES=4` matches reality again. Record regions, instance counts, deployment IDs and check results in the Step 3 receipt.

### 3.5 Rollback

1. Confirm the global row is still disabled and `CONNECTOR_ENABLED=false` (admission closed).
2. `variableDelete` of `CONNECTOR_TRUSTED_PROXY_CIDRS` on the resource, which triggers a resource-only redeploy (if Railway reports no new deployment, trigger `serviceInstanceRedeploy` for the resource).
3. Wait for the replacement deployment `SUCCESS` with both replicas and the prior deployment removed; read back that the effective variable is absent.
4. Rerun the resource verify checks (`/healthz` 200, `/readyz` 200, `/mcp` 503 `CONNECTOR_DISABLED`) and one single-source P1 window with a fresh preflight: pass means `public_sum` 0, `other_private` and `other_cgnat_outside_infra` 0, and at least 10 of the 12 probes recorded in `100.64.x` peer buckets (`infra_sum` 10–12, the §3.1 state). `apply_step3.py rollback --execute` performs steps 2–3 and asserts the prior deployment is `REMOVED`.
5. If the replacement fails or a trusted-CIDR process is still serving, keep admission closed, redeploy the resource's recorded prior deployment, and repeat step 4. Rollback is recorded complete only after step 4 passes. Enable stays blocked until rate-limit attribution is repaired by a reviewed change.

### 3.6 Record

Receipt `koskadeux-state/s1786/step3-receipt.json`: before/after deployment IDs, effective variable readback, and per window the probe JSON (labels, statuses, codes, request IDs) and readback JSON, with timestamps. Also an Event Ledger entry and a `customer-mcp-connector.md` "Gate 4 Step 3 done" section with the CIDR, what was and was not measured, and the receipt path.
