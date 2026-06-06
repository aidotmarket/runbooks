# Production Access from the Titan-1 Claude.ai Sandbox

Status: DRAFT (authored S784 during live work; full lint + gate at completion)
Owner: Vulcan/Mars instances · Surface: operational

## A. What this covers
How a Claude.ai instance (Vulcan/Mars), whose `shell_request` lands on Titan-1 (Mac Studio,
serial G6XQC2KL44), reaches production secrets, the production Postgres, and AWS — without any
interactive login. Resolves the recurring "Infisical not logged in on Titan-1" blocker: the
interactive `infisical login` session is NOT present, but a non-interactive service token is, and
that is the supported path.

## B. Identities & prerequisites
- Infisical: self-hosted at https://secrets.ai.market. Project `bd272d48-c5a1-4b52-9d24-12066ae4403c`, env `prod`.
  Service token lives in `~/.zshrc` as `INFISICAL_SERVICE_TOKEN` (a non-interactive shell does NOT
  auto-source `~/.zshrc`, so read it explicitly).
- Railway: account token in vault as `RAILWAY_API_TOKEN`; `railway` CLI present (4.30.x); the backend
  repo is linked to project `ai-market` / env `production`.
- AWS: platform STS identity `arn:aws:iam::948749907373:user/ai-market-backend-sts`, region `us-east-1`,
  creds in vault as `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION`.

## C. Secrets access (non-interactive)
    export INFISICAL_API_URL=https://secrets.ai.market
    PROJ=bd272d48-c5a1-4b52-9d24-12066ae4403c
    TOK=$(grep -E 'INFISICAL_SERVICE_TOKEN=' ~/.zshrc | head -1 \
          | sed -E "s/.*INFISICAL_SERVICE_TOKEN=//; s/^export //; s/^['\"]//; s/['\"]$//")
    infisical secrets get <KEY> --env prod --projectId "$PROJ" --plain --token "$TOK"
- List key NAMES only (never values): `infisical export --env prod --projectId "$PROJ" --token "$TOK" --format=dotenv | cut -d= -f1`
- The DB key in the vault is `DATABASE_URL` (internal host, see D). There is no `DATABASE_PUBLIC_URL` in the vault.

## D. Production Postgres
- `DATABASE_URL` from the vault points at `postgres.railway.internal:5432` — the Railway PRIVATE host,
  NOT reachable from Titan-1. Do not use it directly.
- Use the public proxy URL from Railway (same credentials, public host/port):
    export RAILWAY_API_TOKEN="$(infisical secrets get RAILWAY_API_TOKEN --env prod --projectId "$PROJ" --plain --token "$TOK")"
    cd /Users/max/Projects/ai-market/ai-market-backend
    DBPUB=$(railway variables --service Postgres --kv | grep '^DATABASE_PUBLIC_URL=' | cut -d= -f2-)
    psql "$DBPUB" -tAc 'select 1'
- Capture `$DBPUB` into a variable and never echo it; print only query results.

## E. AWS
    g(){ infisical secrets get "$1" --env prod --projectId "$PROJ" --plain --token "$TOK"; }
    export AWS_ACCESS_KEY_ID="$(g AWS_ACCESS_KEY_ID)" AWS_SECRET_ACCESS_KEY="$(g AWS_SECRET_ACCESS_KEY)"
    export AWS_REGION="$(g AWS_REGION)" AWS_DEFAULT_REGION="$AWS_REGION"
    aws sts get-caller-identity   # expect account 948749907373, user ai-market-backend-sts

## F. Verification quick reference
- Host is Titan-1: `ioreg -l | grep IOPlatformSerialNumber` -> `G6XQC2KL44`.
- Secrets reachable: `infisical export ... --format=dotenv | grep -c '='` (expect ~118 keys).
- DB reachable: `psql "$DBPUB" -tAc 'select 1'` -> `1`.
- AWS reachable: `aws sts get-caller-identity` returns the platform user.

## G. Gotchas (learned the hard way)
- `infisical export --format=dotenv` wraps values in SINGLE quotes. A masking `sed` that strips only
  double quotes will PRINT the raw value. Always strip single quotes too, and never echo a secret —
  print lengths/hostnames only. (A prod DB password was exposed once this way; see H.)
- A fresh `shell_request` is a new shell: re-export `INFISICAL_API_URL`/`PROJ`/`TOK` each call.
- Tool-call casing: use the exact `Koskadeux:*` / `koskadeux:*` form the last tool_search returned.

## H. Known issues / follow-ups
- ROTATE the production DB password — it was printed once in tool output during S784 setup. Internal-only
  host limits blast radius, but the public proxy shares the password.
- Canonical interactive `infisical login` is still not established on Titan-1; the service-token path
  above is the working substitute. Establish a login or wire the token into the agent env if desired.
- SysAdmin agent `exec_command` was reported broken (S783) — verify separately before delegating prod checks to it.

## I. History
- S784: authored after establishing this path live; superseded the S783 "Infisical not logged in" blocker.

## J. References
- `connectivity.md` (topology, remote access to Titan-1)
- `aws.md`, `gcp-auth.md` (provider-specific auth)
- Living State `config:resource-registry`, `infra:railway`, `infra:titan-1`.

## K. Discipline
Never echo secret values, tokens, or full connection URLs into tool output or logs. Capture into shell
variables; print only sanitized status (lengths, hostnames, exit codes, query results).
