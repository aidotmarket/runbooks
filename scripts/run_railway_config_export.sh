#!/usr/bin/env bash
# Daily Railway topology export -> WORM S3 (aimarket-backups-prod/railway-config/).
# Machine-identity (Universal Auth) login; secrets via `infisical run`. Mirrors run_qdrant_backup.sh.
# Exports services/source/branch/config/cron/domains + variable NAMES (NO secret values).
# S1002: dedicated bd272d48 RAILWAY_API_TOKEN was revoked (Not Authorized). Railway token now sourced
#        from the canonical Titan-1 path (railway-env.sh -> koskadeux-mcp project). AWS writer creds
#        still injected from bd272d48 via `infisical run`. Enumeration query fixed in the .py.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG=/Users/max/Library/Logs/aimarket_railway_config_export.log
LOCK="/tmp/aimarket_railway_config_export_$(date -u +%Y%m%d).lock"
INF=/opt/homebrew/bin/infisical
INF_DOMAIN=https://secrets.ai.market
PROJECT=bd272d48-c5a1-4b52-9d24-12066ae4403c
ID_DIR="$HOME/.config/infisical"
ts(){ date -u +%FT%TZ; }
if [ -f "$LOCK" ]; then echo "[$(ts)] already succeeded this UTC day; skipping" >> "$LOG"; exit 0; fi
echo "[$(ts)] === starting railway-config export ===" >> "$LOG"
PYBIN=""
for c in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  [ -x "$c" ] && PYBIN="$c" && break
done
[ -z "$PYBIN" ] && { echo "[$(ts)] FATAL no python3" >> "$LOG"; exit 8; }
# Canonical Railway account token (account-scoped, non-expiring; see infra:railway machine_identity)
source /Users/max/bin/railway-env.sh >/dev/null 2>&1 || true
GOOD_RT="${RAILWAY_API_TOKEN:-}"
[ -z "$GOOD_RT" ] && { echo "[$(ts)] FATAL canonical RAILWAY_API_TOKEN unavailable from railway-env.sh" >> "$LOG"; exit 10; }
CID="$(cat "$ID_DIR/backup-machine-identity.client-id" 2>/dev/null)"
CS="$(cat "$ID_DIR/backup-machine-identity.client-secret" 2>/dev/null)"
[ -z "$CID" ] || [ -z "$CS" ] && { echo "[$(ts)] FATAL machine-identity creds missing" >> "$LOG"; exit 9; }
TOKEN=""
for attempt in 1 2 3 4 5 6; do
  TOKEN="$("$INF" login --method=universal-auth --client-id="$CID" --client-secret="$CS" --domain="$INF_DOMAIN" --silent --plain 2>>"$LOG")"
  [ -n "$TOKEN" ] && break
  echo "[$(ts)] login attempt $attempt failed; retrying" >> "$LOG"; sleep 4
done
unset CID CS
[ -z "$TOKEN" ] && { echo "[$(ts)] FATAL login failed after retries" >> "$LOG"; exit 9; }
echo "[$(ts)] machine-identity auth OK" >> "$LOG"
# AWS writer creds from bd272d48; RAILWAY_API_TOKEN overridden with the canonical account token.
"$INF" run --token "$TOKEN" --projectId "$PROJECT" --env prod --path / --domain "$INF_DOMAIN" -- \
  env RAILWAY_API_TOKEN="$GOOD_RT" "$PYBIN" "$SCRIPT_DIR/railway_config_export.py" >> "$LOG" 2>&1
rc=$?
unset TOKEN GOOD_RT RAILWAY_API_TOKEN
if [ "$rc" -eq 0 ]; then touch "$LOCK"; echo "[$(ts)] railway-config export OK (lock set)" >> "$LOG"; else echo "[$(ts)] railway-config export FAILED rc=$rc" >> "$LOG"; fi
exit $rc
