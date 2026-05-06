# auth-signup-flow — Sign-up & Login Path Reference

## What it is

Reference for the customer authentication paths in `ai-market-backend`: Google OAuth, GitHub OAuth, magic-link, and password registration. Documents the architectural principle that protects sign-up, the known issues affecting it, and the diagnostic + recovery procedures.

**Owning service:** `ai-market-backend` (see `ai-market-backend.md` for the broader service runbook)
**Live:** `api.ai.market`
**Customer-facing surface:** `ai.market/login` (frontend) → `/api/v1/auth/oauth/{provider}/callback` (backend)

## Architectural principle — non-negotiable

**Sign-up is sacred. No non-essential side effect (CRM provisioning, analytics, welcome email, audit log enrichment, party-role binding) may block account creation.**

The auth flow must commit the user FIRST. Side effects run in isolated transactions or as deferred tasks. Side-effect failures must be logged, monitored, and recoverable — but never customer-facing.

**Why this matters:** every blocked sign-up is a permanently lost prospect. The customer sees a generic OAuth error, has no way to recover, and never tries again. The architecture must guarantee that sign-up always succeeds when the credentials are valid, regardless of any other system state.

## Path map

| Path | Endpoint file | Notes |
|------|---------------|-------|
| Google OAuth callback | `app/api/v1/endpoints/auth.py:710` (`POST /auth/oauth/google/callback`) | Customer login flow. Calls `OAuthService.authenticate_callback("google", ...)` then `_build_auth_success_response`. |
| GitHub OAuth callback | `app/api/v1/endpoints/auth.py:737` (`POST /auth/oauth/github/callback`) | Same pattern as Google. |
| Magic-link redeem | `app/api/v1/endpoints/auth.py` (around line 670) | Email magic-link flow. |
| Password registration | `app/api/v1/endpoints/auth.py` register endpoint | Email + password + verification. |
| OAuth identity creation | `app/auth/oauth.py:377` (`OAuthService._link_or_create_user`) | The user-or-link decision logic. **Currently calls `ensure_user_crm_identity` inline — see Known Issues.** |
| CRM provisioning helper | `app/domains/crm/core/sync_helpers.py:18` (`ensure_user_crm_identity`) | Creates `Party`, `PartyIdentity`, optional `PartyRoleBinding`. Documented as safe to call repeatedly. |

**Note on the two oauth files:** `app/api/v1/endpoints/auth.py` and `app/api/v1/endpoints/oauth.py` are NOT in conflict. They serve different purposes:
- `auth.py` — customer login flow (Sign in with Google / GitHub)
- `oauth.py` — ai.market acting as an OAuth 2.0 provider for third-party clients (e.g., GPT Actions consuming our API)

The `auth.router` mounts at prefix `/auth` (line 133 of `router.py`); the `oauth.router` self-prefixes with `/oauth` and mounts without an additional prefix (line 234). No route collision. Do not confuse the two when investigating sign-up issues.

## Known issues

### Active: CRM provisioning blocking sign-up (P0, customer-blocking)

**Tracked under:** `BQ-AUTH-OAUTH-CRM-PROVISIONING-BLOCKS-SIGNUP-S574`
**Introduced by:** commit `5e47527` ("feat: auto-create CRM person + party + role bindings on user registration")

**Symptom:** Customer attempts Google or GitHub sign-up, completes the consent on the provider side, lands on `ai.market/login?error=oauth_failed`. Multiple retries produce the same outcome. No persisted user record (every attempt rolls back).

**Root cause:** `OAuthService._link_or_create_user` (at `app/auth/oauth.py:408`) calls `ensure_user_crm_identity` inline inside the FastAPI request transaction. When CRM provisioning raises any exception (FK violation, unique constraint, schema drift on `Party` / `PartyIdentity` / `PartyRoleBinding`), the exception bubbles up and FastAPI rolls back the entire transaction. The user row is never persisted; the frontend sees the generic error.

**How to recognize in logs:**
```sh
railway logs --service ai-market-backend 2>&1 | grep -iE "ensure_user_crm|PartyIdentity|PartyRoleBinding|integrityerror" | tail -30
```
Look for stack traces showing `_link_or_create_user` → `ensure_user_crm_identity` → SQLAlchemy `IntegrityError` or `OperationalError`. The frontend redirect to `/login?error=oauth_failed` happens when the POST to `/api/v1/auth/oauth/{provider}/callback` returns 5xx.

**Diagnosing affected users:**
```sql
-- Find users created without CRM identity (after fix, this query identifies backfill candidates)
SELECT u.id, u.email, u.created_at
FROM users u
LEFT JOIN party_identities pi
  ON pi.provider = 'auth_user' AND pi.external_id = u.id::text
WHERE pi.id IS NULL;
```

Pre-fix: this query returns nothing because affected users never get persisted (rollback). The customer simply can't sign up. There are no orphaned records to clean.

**Fix path (in flight):** Decouple CRM provisioning from the auth transaction. Three candidate strategies under evaluation in the Gate 1 spec:
1. Lazy idempotent provisioning — call `ensure_user_crm_identity` on first authenticated request when the user lacks a `PartyIdentity`. Cleanest if a clear hook point exists.
2. Separate-transaction wrapper — keep the call site but wrap in `try/except` after the user is committed in its own transaction; on failure, log + emit event + return user normally.
3. Async background task — only if the codebase already has an async-task framework in use (Celery / RQ / FastAPI BackgroundTasks).

The chosen strategy will be documented here once the fix lands.

**Architectural fix requirements (any chosen strategy must satisfy):**
- User row committed before any CRM provisioning is attempted.
- CRM provisioning failures logged with structured context (`user_id`, `email`, exception type, traceback) and emitted as a metric/event for monitoring.
- Backfill mechanism for users with missing CRM identity so failed provisionings can be re-run without manual recovery.
- Regression test: OAuth callback returns 200 with valid token even when `ensure_user_crm_identity` raises a synthetic exception.
- Same protection applied to all sign-up paths (magic-link, password registration, both OAuth providers).

**Front-door observability gap:** This incident is the exact class of failure that `BQ-AUTH-FRONT-DOOR-OBSERVABILITY-S573` targets. Today we have no proactive alerting on sign-up failure rates; we only learn about these incidents when a customer surfaces them out of band. That BQ should be promoted alongside the fix landing.

### Resolved: OAuth consent screen `org_internal` block (S573)

**Symptom:** Google OAuth blocked customers with `org_internal` error before reaching the ai.market callback.
**Cause:** Google Cloud OAuth consent screen User Type was set to Internal.
**Fix:** Max flipped User Type to External in Google Cloud Console (S573); app published.
**Status:** Fixed; no code change required.

## Diagnostic procedures

### Live capture of a failing sign-up

When investigating an active customer report, capture the failure live rather than guessing from cold logs:

1. Confirm the customer is ready to retry.
2. Open a streaming log tail:
   ```sh
   cd /Users/max/Projects/ai-market/ai-market-backend
   railway logs --service ai-market-backend
   ```
3. Have the customer attempt sign-up. Record the timestamp.
4. Filter the captured stream for the relevant request:
   - Look for `POST /api/v1/auth/oauth/{provider}/callback`
   - If no POST appears: failure is frontend-side (sessionStorage, cookies, browser issue). Check `ai-market-frontend/app/auth/oauth/[provider]/callback/page.tsx` line 26 (missing code/state/nonce path) vs. line 35 (oauthLogin rejection path).
   - If POST appears with 5xx: failure is backend-side. Capture the full traceback.

### Production database query (when needed)

The Railway PostgreSQL hostname (`postgres.railway.internal`) only resolves inside Railway's network. To query from outside:

- **Option A (preferred):** `railway connect Postgres` — opens a proxied psql session.
- **Option B:** `railway run --service ai-market-backend -- python3 ...` runs locally with prod env vars but the internal hostname won't resolve from your laptop. Use only if your script doesn't actually open a DB connection.
- **Option C:** Run the query from inside the deployed service via a one-off admin endpoint (preferred for any ad-hoc admin work that should be auditable).

### Verifying a fix in production

After any change to the sign-up path:
1. Confirm Railway deploy succeeded: `railway deployment list --service ai-market-backend` (most recent SUCCESS).
2. Smoke-check health: `curl -s https://api.ai.market/health` (HTTP 200, `alembic_drift=false`).
3. Run a sign-up end-to-end with a fresh test email.
4. Confirm the user row + CRM identity are both created via the SQL query above.
5. Synthetic-failure test: with the regression test fixture in place, run the OAuth callback test that mocks `ensure_user_crm_identity` to raise — must return 200 + valid token.

## Recovery — backfilling affected users (post-fix)

Once the architectural fix lands, any customer who attempted sign-up during the broken window may have either no record (pre-fix rollback path) or a partial record (if the fix lands mid-flight). The post-fix backfill path:

```sql
SELECT u.id, u.email
FROM users u
LEFT JOIN party_identities pi
  ON pi.provider = 'auth_user' AND pi.external_id = u.id::text
WHERE pi.id IS NULL;
```

Re-provisioning is done by calling `ensure_user_crm_identity(db, user.id, email=user.email, ...)` per affected user, either via the admin endpoint exposed by the fix or via a one-off reconciliation script.

## Cross-references

- `ai-market-backend.md` — broader service runbook (deploy, alembic, troubleshooting).
- `crm-architecture.md` — CRM data model (`Party`, `PartyIdentity`, `PartyRoleBinding`, `CRMEntity`, `CRMPerson`).
- `crm-target-state.md` — CRM target architecture for design decisions.

---

*Created: S574 (2026-05-06) — captures architectural principle + active P0 incident `BQ-AUTH-OAUTH-CRM-PROVISIONING-BLOCKS-SIGNUP-S574`.*
*To be updated when the fix lands: chosen isolation strategy, commit/PR refs, regression test path, backfill verification.*
