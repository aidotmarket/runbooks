# S1786 Gate 4 Step 5 local test-host kit

Recipe: `spec/s1786-gate4-step5-d2` at
`9c393949963c8afefb7645dbf95b157d8d512d24`,
`specs/BQ-CONNECTOR-GATE4-PROVISIONING-S1764.md` §5.2.
Backend: `5f3efc85a707e2f94a9b19f84efd53afdf0c7a53`.
The harness is exactly the §5.2 Python module, named `harness_app.py`.
It marks the resource process before settings imports and substitutes only the
canonical public JWKS response through MockTransport. Grants, memberships,
switches, handlers, limiter and audit use backend defaults.

This native-venv rehearsal proves the requested no-Qdrant path. It does not prove
an unchanged deployed image digest, semantic/hybrid search, stale-vector
hydration or the full Step 5 production procedure. No production access is needed.

## One-command rehearsal

Use the existing local PostgreSQL server, with an owner able to create a database
and roles. Do not initdb another cluster (host shared memory is exhausted).
The runner refuses an occupied application port and never replaces an existing
DB, role or container. It owns only `s1786_step5`, `s1786_step5_app`,
`s1786_step5_runtime` and its disposable Redis container. It tears these down,
stops its host and deletes local keys even after a failed assertion.

From this runbooks checkout:

```bash
rtk git -C /Users/max/Projects/ai-market/ai-market-backend worktree add --detach /tmp/s1786-backend-5f3efc85 5f3efc85a707e2f94a9b19f84efd53afdf0c7a53
export S1786_OWNER_DATABASE_URL=postgresql://max@127.0.0.1:5432/postgres
rtk proxy /Users/max/Projects/ai-market/ai-market-backend/.venv/bin/python tools/s1786-step5-testhost/rehearse.py
```

If 8080 is occupied, choose an unused local port explicitly with `--port 18080`.
Capture the full sanitized command/output transcript by redirecting the runner's
stdout and stderr to a file outside the repository. Never enable shell tracing.
The owner DSN is supplied by environment only. If credentials are required,
load the environment privately; do not put passwords in argv or this README.

The runner uses the documented backend CI migration settings:
`RUN_ONE_SHOT_S1163_P2=1`,
`ISSUE_CHANNEL_APPLICATION_DB_ROLE=s1786_step5_app`,
`CONNECTOR_RUNTIME_DB_ROLE=s1786_step5_app`, `ENVIRONMENT=test` and a generated
`SECRET_KEY`, then `rtk proxy <venv>/python -m alembic upgrade head` in the pinned
backend checkout. The migration owner is separate from the runtime login.
`runtime_grants.sql` copies the Step 1 column grant matrix, renamed for this
local DB and role. No blanket/default table grant is given to runtime.

Redis uses the cached `redis:7` image ID
`sha256:c6eabf748fc7a61dbb5a705c78bcf3d6377b1127a97d0ce965c11c44ba46896f`
with `--pull=never` and loopback port 16386. If absent, the runner reports Redis
unavailable and exercises the connector's single-process limiter fallback.
Existing Redis instances are untouched. Qdrant must be unreachable on 16387.
The connector itself runs natively, without Docker.

## Individual commands

After owner migrations and runtime column grants, from this checkout:

```bash
export DATABASE_URL=postgresql://max@127.0.0.1:5432/s1786_step5
rtk proxy /Users/max/Projects/ai-market/ai-market-backend/.venv/bin/python tools/s1786-step5-testhost/fixtures.py --output /tmp/s1786-fixtures.json
rtk proxy /Users/max/Projects/ai-market/ai-market-backend/.venv/bin/python tools/s1786-step5-testhost/mint_token.py --fixtures /tmp/s1786-fixtures.json --key-dir /tmp/s1786-keys
```

`fixtures.py` binds values and commits all rows in one transaction. All fixtures
share a fictional US grocery checkout subject and carry SYNTHETIC TEST labels.
It creates an active organization membership and sets the grant's real column
`organization_id` to that organization. The consent session is real synthetic
`auth_sessions.session_id`. It also creates a complete synthetic
`seller_license_acceptances` record required by the listing foreign key.
L2 lacks all licence snapshot fields; L3 has a complete snapshot but is draft.
L1 and L4 have complete snapshots, two schema columns, ten rows, seven-day
cadence and price 25. `synthetic_queries` is an empty JSON array on all four.
Generated IDs and the distinct L4 query token are printed, and saved in the
manifest. No customer data, login password or signing secret is inserted.

Set the following environment privately (the runner does this automatically):

```text
ENVIRONMENT=test
CONNECTOR_ENABLED=true
CONNECTOR_AUTH_ISSUER=https://auth.ai.market
CONNECTOR_AUDIENCE=https://connect.ai.market/mcp
CONNECTOR_JWKS_URL=https://auth.ai.market/.well-known/jwks.json
CONNECTOR_ALLOWED_HOSTS=connect.ai.market
CONNECTOR_EARLY_ACCESS_ENFORCED=true
CONNECTOR_EARLY_ACCESS_USER_IDS=<manifest user_id>
DATABASE_URL=<local s1786_step5_runtime DSN>
REDIS_URL=redis://127.0.0.1:16386/0
CONNECTOR_EXPECTED_PROCESSES=1
CONNECTOR_AUDIT_HMAC_KEY=<fresh local random value>
SECRET_KEY=<different fresh local random value>
S1786_LOCAL_JWKS_FILE=/tmp/s1786-keys/jwks.json
QDRANT_HOST=127.0.0.1
QDRANT_PORT=16387
QDRANT_API_KEY=<fresh local value>
```

Unset `VERTEX_GEMINI_KEY`, `CONNECTOR_OAUTH_SIGNING_KEYS`, all OTLP endpoints,
and the four Step 5 search/embedding overrides. Run with a minimal environment
and no backend `.env` file. The reusable runner already isolates its environment.

From the pinned backend checkout, with an absolute runbooks kit path:

```bash
rtk proxy /Users/max/Projects/ai-market/ai-market-backend/.venv/bin/python -m uvicorn harness_app:app --app-dir /absolute/runbooks/tools/s1786-step5-testhost --host 127.0.0.1 --port 8080 --workers 1
```

From this runbooks checkout in another terminal:

```bash
rtk proxy /Users/max/Projects/ai-market/ai-market-backend/.venv/bin/python tools/s1786-step5-testhost/run_calls.py --fixtures /tmp/s1786-fixtures.json --token-file /tmp/s1786-keys/token.jwt
```

`run_calls.py` sends Host `connect.ai.market`, bearer auth and MCP protocol
`2025-11-25`. It prints status, response and request ID, never request auth.
It asserts exactly five tools; three private reads; L1 ListingOutput; identical
wire L2/L3 envelopes after replacing only request IDs (both calls use
the same JSON-RPC correlation ID); and L4 present with `sql_fallback`.
The runner reads audit as owner, asserting seven tool.call rows with populated
argument, result and user-agent HMAC fields. No raw request text is selected.
Visibility authority: pinned backend
`app/mcp/connector/discovery/visibility.py:20-31`; detail uses the predicate in
`projection.py:98`; connector search SQL fallback uses the same predicate at
`app/services/listing_search_service.py:994`.

Tokens last ten minutes. Remint if needed. Only the public JWKS reaches the
harness. Private keys and token files are mode 0600 outside the repository.
For individual execution, stop uvicorn, delete `/tmp/s1786-keys` and the manifest,
remove only the owned Redis container, drop the owned database, then the two
roles. Prefer the runner so cleanup is automatic and recorded.

## Rehearsal recorded 2026-10-01

Native pinned backend venv, PostgreSQL 17.7 (Homebrew), UTC; migration head
`s1787_card_fee_gl`; disposable Redis at 16386. Port **18080** was used because
8080 belongs to the existing `aim-data-fresh-s1665-app-1` container, left running.
Qdrant was unreachable and Vertex credentials absent. No Docker connector or
production image-digest claim is made.

| Call | HTTP | Result | Request ID |
| --- | --- | --- | --- |
| initialize | 200 | MCP 2025-11-25 | 4deed0242ab539d711a5d3b213f29893 |
| tools/list | 200 | Exactly the five required tools | 4ec986577f02ed1d221906f28a48ed4f |
| get_my_account | 200 | Synthetic user and active organization | 826b77f18dd789f58f2a280df3af9787 |
| get_activity | 200 | Empty successful page | 49c9a1e6640595793fc13028b6dc34a4 |
| list_data_requests | 200 | Empty successful page | ea67b1f846c707e3cda0ff3e6502d88e |
| get_listing L1 | 200 | ListingOutput; two columns, ten rows, schema_stats | af8cbcb683da52dd6388488952164929 |
| get_listing L2 | 200 | NOT_FOUND | a62778859324a9c7fcf4445ae2a0d388 |
| get_listing L3 | 200 | Byte-identical envelope after request ID substitution | 7ce3efaeaec3aec07cdeb17514ce8c67 |
| search_listings L4 token | 200 | sql_fallback; only L4; no TEMPORARILY_UNAVAILABLE | ebbd56a6ac2116c4f146b5900c3cd3a1 |

L1 `489e713f-b9e7-4576-af67-792da110e0cc`;
L4 `258e9620-0ae4-4465-8757-825d374c4f2a`.
Seven tool.call audit rows have argument, result and user-agent HMAC fields.
The owner visibility readback returns exactly L1 and L4.
Full sanitized commands, migration output, fixture IDs, MCP response bodies,
request IDs, audit readback and teardown are in the delivered local transcript
`/tmp/s1786-step5-rehearsal-3.log` (not committed; scripts only).
Runner exit status 0. Database and both roles dropped, Redis container removed,
uvicorn stopped, temporary private key/token/JWKS/manifest deleted.

Two earlier runner attempts exposed kit bugs (venv symlink resolution and the
parent-process backend import path). Both cleaned up; both were fixed before
this successful run. The missing-Vertex embedding exception in the successful
transcript is expected and exercises SQL fallback.
