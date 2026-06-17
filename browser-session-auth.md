# browser-session-auth — Login Sessions That Survive Reload

## What it is
How a logged-in ai.market browser session stays alive across page reloads and new
tabs. The model is deliberate: the **access token lives only in memory** (never in
localStorage — XSS posture, see backend `lib/SECURITY.md`), and an **httpOnly refresh
cookie** silently re-mints the access token on page load. On a fresh load the app calls
`POST /api/v1/auth/refresh` with `withCredentials` and no body; the browser attaches the
refresh cookie; the backend returns a new access token and rotates the cookie.

Repos: backend `ai-market-backend` (`app/api/v1/endpoints/auth.py`, `app/core/auth_cookies.py`),
frontend `ai-market-frontend` (`api/client.ts`, `store/auth.ts`).

## Architectural principle — non-negotiable
**The frontend and the API it calls MUST be the same site (same registrable domain).**
The refresh cookie is `SameSite=Lax`. Browsers only attach a Lax cookie to a background
(fetch/XHR) request when the request target is the **same site** (same eTLD+1) as the
page. `ai.market` and `api.ai.market` share registrable domain `ai.market` → same-site →
the cookie flows. `ai.market` and `…up.railway.app` are **different sites** → the browser
silently withholds the cookie → every reload logs the user out.

Therefore the frontend MUST call `https://api.ai.market`, **never** the raw Railway
service host (`ai-market-backend-production.up.railway.app`). This is set by
`NEXT_PUBLIC_API_URL` (and `API_URL`) on the **Railway `ai-market-frontend` service
variables** (authoritative at build time — Next.js inlines `NEXT_PUBLIC_*` during build;
the committed `.env` is gitignored and does NOT drive the Railway build).

Do **not** "fix" a reload-logout by switching the cookie to `SameSite=None`. That re-opens
the cross-site/CSRF exposure the design avoids (Gate 1 decision: Lax is sufficient because
refresh is POST-only behind an Origin allowlist). Same-site hosting is the fix; `None` is not.

## Cookie contract (backend)
Set/cleared centrally in `app/core/auth_cookies.py`:
- name `refresh_token`; `HttpOnly`; `SameSite=Lax`; `Path=/api/v1/auth` (so it reaches both
  `/refresh` and `/logout`); `Secure` env-gated (true in prod via `ENVIRONMENT`/
  `RAILWAY_ENVIRONMENT`/`PRODUCTION`); `Max-Age = REFRESH_TOKEN_EXPIRE_DAYS * 86400`; no `Domain` (host-only).
- Set on every browser issuance path (login, oauth google/github, magic-link verify,
  2FA verify, OIDC SSO). `register` and `reauth` are intentionally excluded.
- Login/refresh JSON body returns `refresh_token = None` (the token never enters the browser as JSON).
- `/refresh` reads the cookie only when the request `Origin` is in `CORS_ORIGINS`
  (`_allowed_origin_refresh_cookie`); absent/foreign Origin → clean 401. Rotates the
  refresh family (jti + refresh_family) and re-sets the cookie.
- `/logout` clears the cookie (`Max-Age=0`) and best-effort revokes the session.

## Verifying a fix — the only valid check is a real browser
**An API curl is NOT a valid verification of session persistence.** `curl` does not enforce
the browser SameSite rule, and hitting `api.ai.market` directly bypasses the cross-site
path the browser actually takes. Two incidents (S927) were each falsely declared "passing"
on curl evidence before a real hard refresh failed.

Gate-4 / production check for "login survives reload":
1. In a browser on `https://ai.market`, log in **fresh** (a session created before the
   cookie code deployed has no refresh cookie — re-login first).
2. Hard refresh (Shift-Cmd-R / Ctrl-Shift-R). You must stay logged in.
3. Open DevTools → Application → Cookies for `api.ai.market`: confirm `refresh_token`
   present with `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/api/v1/auth`.
4. DevTools → Network on reload: `POST …/api/v1/auth/refresh` returns 200 and carries the
   `Cookie:` header (proves same-site flow). If it 401s, check the request host — if it's
   `…up.railway.app`, the same-site invariant is violated (see Architectural principle).
5. Log out → reload → you stay logged out.

Curl is fine for the backend contract only (does the endpoint behave with a cookie
present), never as the sign-off for the browser behavior.

## Known gotchas (both hit in S927)
1. **Cross-site API host (the big one).** Frontend pointed at the raw Railway host → Lax
   cookie withheld → logout on reload. Fix: `NEXT_PUBLIC_API_URL=https://api.ai.market` on
   the Railway `ai-market-frontend` service, then redeploy (rebuild re-inlines it).
2. **Whole-second `iat` vs microsecond `last_login_at`.** The `/refresh` "invalidate tokens
   issued before last login" check compared the JWT `iat` (whole-second Unix timestamp)
   against `user.last_login_at` (microsecond precision set at login). A freshly minted
   token looked sub-second too old and was rejected on the first refresh (401 "Refresh
   token invalidated"). Fix: compare at whole-second granularity
   (`last_login.replace(microsecond=0)`). Unit tests passed because test fixtures don't
   reproduce the sub-second skew against real Postgres `now()` — caught only in prod.

## Diagnostic quick map
- Reload logs out, login works → suspect the cross-site host first. Check the deployed
  bundle's API base: `curl -s https://ai.market/ | grep -oE '/_next/static/chunks/[^"]+\.js'`,
  fetch the auth chunk, grep for the API host; or check `railway variables | grep API_URL`
  on the `ai-market-frontend` service. Must be `https://api.ai.market`.
- First refresh 401 "Refresh token invalidated" with a same-site host → gotcha #2.
- 401 "Refresh token required" → no cookie sent: cross-site host, or Origin not in
  `CORS_ORIGINS`, or session predates the cookie deploy (re-login).

## Cross-references
- Sign-up / login path: [auth-signup-flow.md](auth-signup-flow.md)
- Web app & deploy: [ai-market-frontend.md](ai-market-frontend.md)
- Backend API / deploy: [ai-market-backend.md](ai-market-backend.md)
- 2FA: [two-factor-auth.md](two-factor-auth.md)
