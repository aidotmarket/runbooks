#!/bin/bash
# s3_backup_watchdog.sh — Telegram alert if the ai.market S3 backup is missing or stale (>26h).
# Autonomous: local `aimarket` AWS profile + Telegram creds from koskadeux-mcp/.env. No Infisical dependency.
# Scheduled by launchd com.aimarket.s3-backup-watchdog (every 6h + RunAtLoad). See backup-and-recovery.md §F.
set -uo pipefail
ENVF=/Users/max/koskadeux-mcp/.env
BUCKET="s3://aimarket-backups-prod/postgres/ai-market/"
MAX_AGE_H=26
PROFILE=aimarket
LOG=/Users/max/Library/Logs/aimarket_s3_backup_watchdog.log

tg() {
  local tok cid
  tok=$(grep -E '^TELEGRAM_BOT_TOKEN=' "$ENVF" | head -1 | cut -d= -f2- | tr -d "\"' ")
  cid=$(grep -E '^TELEGRAM_CHAT_ID='   "$ENVF" | head -1 | cut -d= -f2- | tr -d "\"' ")
  if [ -n "$tok" ] && [ -n "$cid" ]; then
    curl -s "https://api.telegram.org/bot$tok/sendMessage" \
      --data-urlencode "chat_id=$cid" --data-urlencode "text=$1" >/dev/null
  fi
}

ts=$(date -u +%FT%TZ)
newest=$(aws s3 ls "$BUCKET" --recursive --profile "$PROFILE" 2>/dev/null | sort | tail -1)
if [ -z "$newest" ]; then
  echo "[$ts] ALERT: no S3 backups found" >> "$LOG"
  tg "ALERT: ai.market has NO backup objects in S3 (aimarket-backups-prod). Backups are not running."
  exit 0
fi
bdate=$(echo "$newest" | awk '{print $1" "$2}')
bepoch=$(date -j -f "%Y-%m-%d %H:%M:%S" "$bdate" +%s 2>/dev/null || echo 0)
now=$(date +%s)
age_h=$(( (now - bepoch) / 3600 ))
if [ "$bepoch" -eq 0 ] || [ "$age_h" -ge "$MAX_AGE_H" ]; then
  echo "[$ts] ALERT: newest S3 backup ${age_h}h old ($bdate)" >> "$LOG"
  tg "ALERT: ai.market newest S3 backup is ${age_h}h old (latest $bdate). A nightly backup has NOT run. Bucket aimarket-backups-prod."
else
  echo "[$ts] OK: newest S3 backup ${age_h}h old ($bdate)" >> "$LOG"
fi
