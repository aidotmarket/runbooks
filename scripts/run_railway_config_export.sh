#!/usr/bin/env bash
# Daily Railway topology export -> WORM S3 (aimarket-backups-prod/railway-config/).
# Machine-identity (Universal Auth) login; secrets via `infisical run`. Mirrors run_qdrant_backup.sh.
# Exports services/source/branch/config/cron/domains + variable NAMES (NO secret values).
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
"$INF" run --token "$TOKEN" --projectId "$PROJECT" --env prod --path / --domain "$INF_DOMAIN" -- \
  "$PYBIN" "$SCRIPT_DIR/railway_config_export.py" >> "$LOG" 2>&1
rc=$?
unset TOKEN
if [ "$rc" -eq 0 ]; then touch "$LOCK"; echo "[$(ts)] railway-config export OK (lock set)" >> "$LOG"; else echo "[$(ts)] railway-config export FAILED rc=$rc" >> "$LOG"; fi
exit $rc
