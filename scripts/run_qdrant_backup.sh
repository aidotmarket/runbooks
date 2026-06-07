#!/usr/bin/env bash
# Daily ai.market Qdrant 'knowledge_base' snapshot -> WORM S3 (aimarket-backups-prod/qdrant/).
# Machine-identity (Universal Auth) login; secrets via `infisical run`. Mirrors run_pg_backup.sh.
# Per-UTC-day lock so the DST-safe dual launchd fire runs at most once per UTC day.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG=/Users/max/Library/Logs/aimarket_qdrant_backup.log
LOCK="/tmp/aimarket_qdrant_backup_$(date -u +%Y%m%d).lock"
INF=/opt/homebrew/bin/infisical
INF_DOMAIN=https://secrets.ai.market
PROJECT=bd272d48-c5a1-4b52-9d24-12066ae4403c
ID_DIR="$HOME/.config/infisical"
ts(){ date -u +%FT%TZ; }
if [ -f "$LOCK" ]; then echo "[$(ts)] already succeeded this UTC day; skipping" >> "$LOG"; exit 0; fi
echo "[$(ts)] === starting qdrant backup ===" >> "$LOG"
PYBIN=""
for c in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  if [ -x "$c" ] && "$c" -c 'import boto3,httpx' 2>/dev/null; then PYBIN="$c"; break; fi
done
if [ -z "$PYBIN" ]; then echo "[$(ts)] FATAL no python3 with boto3+httpx" >> "$LOG"; exit 8; fi
CID="$(cat "$ID_DIR/backup-machine-identity.client-id" 2>/dev/null)"
CS="$(cat "$ID_DIR/backup-machine-identity.client-secret" 2>/dev/null)"
if [ -z "$CID" ] || [ -z "$CS" ]; then echo "[$(ts)] FATAL machine-identity creds missing" >> "$LOG"; exit 9; fi
TOKEN=""
for attempt in 1 2 3 4 5 6; do
  TOKEN="$("$INF" login --method=universal-auth --client-id="$CID" --client-secret="$CS" --domain="$INF_DOMAIN" --silent --plain 2>>"$LOG")"
  [ -n "$TOKEN" ] && break
  echo "[$(ts)] login attempt $attempt failed; retrying" >> "$LOG"; sleep 4
done
unset CID CS
if [ -z "$TOKEN" ]; then echo "[$(ts)] FATAL login failed after retries" >> "$LOG"; exit 9; fi
echo "[$(ts)] machine-identity auth OK" >> "$LOG"
"$INF" run --token "$TOKEN" --projectId "$PROJECT" --env prod --path / --domain "$INF_DOMAIN" -- \
  "$PYBIN" "$SCRIPT_DIR/backup_qdrant.py" >> "$LOG" 2>&1
rc=$?
unset TOKEN
if [ "$rc" -eq 0 ]; then touch "$LOCK"; echo "[$(ts)] qdrant backup OK (lock set for today)" >> "$LOG"; else echo "[$(ts)] qdrant backup FAILED rc=$rc" >> "$LOG"; fi
exit $rc
