#!/bin/bash
# S3 backup freshness watchdog. Force UTC: AWS CLI renders listing times in local TZ.
set -uo pipefail
ENVF=${WATCHDOG_ENVF:-/Users/max/koskadeux-mcp/.env}
MAX_AGE_H=26
PROFILE=aimarket
LOG=${WATCHDOG_LOG:-/Users/max/Library/Logs/aimarket_s3_backup_watchdog.log}
ROOT=s3://aimarket-backups-prod
TARGETS=(
  "postgres|$ROOT/postgres/ai-market/"
  "infisical-secrets|$ROOT/postgres/infisical/"
  "qdrant|$ROOT/qdrant/"
  "railway-config|$ROOT/railway-config/"
  "cloudflare|$ROOT/cloudflare/"
)
ts=$(date -u +%FT%TZ) || exit 1
now=$(date -u +%s) || exit 1
tmp=$(mktemp -d) || exit 1
trap 'rm -rf "$tmp"' EXIT
failed=0
record() {
  if ! printf '%s\n' "$1" >> "$LOG"; then
    failed=1
  fi
}

telegram() {
  local tok cid http result
  if [ ! -r "$ENVF" ]; then return 1; fi
  tok=$(sed -n 's/^TELEGRAM_BOT_TOKEN=//p' "$ENVF" | head -1 | tr -d "\"' ")
  cid=$(sed -n 's/^TELEGRAM_CHAT_ID=//p' "$ENVF" | head -1 | tr -d "\"' ")
  if [ -z "$tok" ] || [ -z "$cid" ]; then return 1; fi
  http=$(curl -sS --max-time 20 --output "$tmp/telegram.json" --write-out '%{http_code}' \
    "https://api.telegram.org/bot$tok/sendMessage" \
    --data-urlencode "chat_id=$cid" --data-urlencode "text=$1" 2>/dev/null) || return 1
  if [ "$http" != 200 ]; then return 1; fi
  result=$(python3 - "$tmp/telegram.json" <<'PY'
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    message_id = data["result"]["message_id"]
    if data.get("ok") is not True or type(message_id) is not int or message_id <= 0:
        raise ValueError("unconfirmed response")
    print(message_id)
except (OSError, ValueError, KeyError, TypeError):
    sys.exit(1)
PY
  ) || return 1
  printf '%s' "$result"
}

alert() {
  local name=$1 reason=$2 message_id
  record "[$ts] ALERT($name): $reason"
  failed=1
  if message_id=$(telegram "ALERT: ai.market $name S3 backup check failed: $reason. Bucket aimarket-backups-prod."); then
    record "[$ts] Telegram confirmed($name): message_id=$message_id"
  else
    record "[$ts] Telegram delivery failed($name)"
    failed=1
  fi
}

for entry in "${TARGETS[@]}"; do
  name=${entry%%|*}; bucket=${entry#*|}
  if ! TZ=UTC aws s3 ls "$bucket" --recursive --profile "$PROFILE" > "$tmp/list" 2>/dev/null; then
    alert "$name" 'S3 listing failed'
    continue
  fi
  if [ "$name" = qdrant ]; then
    if ! aws s3 cp "$ROOT/backup-health/qdrant/last-run.json" "$tmp/manifest" --profile "$PROFILE" >/dev/null 2>&1; then
      alert "$name" 'health manifest unreadable'
      continue
    fi
  fi
  verdict=$(python3 - "$name" "$now" "$MAX_AGE_H" "$tmp/list" "$tmp/manifest" <<'PY'
import datetime as dt
import json
import re
import sys

name, now_text, threshold_text, listing_path, manifest_path = sys.argv[1:]
now = int(now_text)
threshold = int(threshold_text) * 3600
expected = {"action_logs", "aim_tools", "data_requests", "knowledge_base",
            "knowledge_base_v2", "listings"}

def fail(reason):
    print("ALERT|" + reason)
    sys.exit(0)

objects = {}
try:
    with open(listing_path, encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        match = re.fullmatch(r"(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d)\s+(\d+)\s+([^\s]+)\s*", line)
        if not match:
            fail("malformed S3 listing")
        day, clock, size, key = match.groups()
        stamp = int(dt.datetime.strptime(day + " " + clock, "%Y-%m-%d %H:%M:%S")
                    .replace(tzinfo=dt.timezone.utc).timestamp())
        if stamp > now + 300 or key in objects:
            fail("invalid S3 listing")
        objects[key] = (stamp, int(size))
except (OSError, UnicodeError, ValueError, OverflowError):
    fail("malformed S3 listing")

if not objects:
    fail("no S3 backup objects")

def fresh(key):
    stamp, size = objects[key]
    return size > 0 and 0 <= now - stamp < threshold

if name != "qdrant":
    newest = max(objects, key=lambda key: objects[key][0])
    if not fresh(newest):
        fail("newest backup missing, empty, or at least 26h old")
    print("OK|fresh S3 object")
    sys.exit(0)

try:
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    rows = manifest["collections"]
    if (manifest.get("target") != "qdrant" or manifest.get("status") != "ok"
            or type(rows) is not list or type(manifest.get("count")) is not int
            or manifest["count"] != len(rows)):
        fail("failed or incomplete health manifest")
    manifest_ts = dt.datetime.fromisoformat(manifest["ts"])
    if manifest_ts.tzinfo is None:
        fail("health manifest timestamp has no timezone")
    run_day = manifest_ts.astimezone(dt.timezone.utc).strftime("%Y%m%d")
    manifest_age = now - int(manifest_ts.timestamp())
    if manifest_age < 0 or manifest_age >= threshold:
        fail("stale health manifest")
    reported = {}
    for row in rows:
        collection = row["collection"]
        key = row["key"]
        if (not isinstance(collection, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", collection)
                or collection in reported or row.get("status") != "ok"
                or not isinstance(key, str)
                or not re.fullmatch(rf"qdrant/{collection}/[0-9]{{8}}/[^/\s]+", key)
                or type(row.get("bytes")) is not int or row["bytes"] <= 0):
            fail("failed or incomplete health manifest")
        key_day = key.split("/")[2]
        try:
            dt.datetime.strptime(key_day, "%Y%m%d")
        except ValueError:
            fail("invalid collection snapshot date")
        if key_day != run_day:
            fail("collection snapshot date differs from health manifest")
        reported[collection] = (key, row["bytes"])
    discovered = set()
    for key in objects:
        parts = key.split("/")
        if len(parts) < 4 or parts[0] != "qdrant" or not re.fullmatch(r"[A-Za-z0-9_-]+", parts[1]):
            fail("invalid Qdrant snapshot path")
        if parts[2] == run_day:
            discovered.add(parts[1])
    if not (expected | discovered) <= reported.keys():
        fail("missing collection in health manifest")
    for key, size in reported.values():
        if key not in objects:
            fail("missing collection snapshot")
        if objects[key][1] != size:
            fail("collection snapshot size mismatch")
        if not fresh(key):
            fail("stale or empty collection snapshot")
except (OSError, UnicodeError, ValueError, KeyError, TypeError, OverflowError, AttributeError):
    fail("malformed health manifest")
print("OK|fresh snapshots for %d collections" % len(reported))
PY
  ) || verdict='ALERT|backup evaluation failed'
  case "$verdict" in
    OK\|*) record "[$ts] OK($name): ${verdict#OK|}" ;;
    ALERT\|*) alert "$name" "${verdict#ALERT|}" ;;
    *) alert "$name" 'backup evaluation failed' ;;
  esac
done
exit "$failed"
