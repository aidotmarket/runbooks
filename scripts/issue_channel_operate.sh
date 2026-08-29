#!/usr/bin/env bash
# Issue-channel operator helpers (runbook issue-channel.md §E). Source this file: `source OPERATE.sh`.
# Never echo $W or $URL. The watcher role is read-only; never write with it.
export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH HOME=/Users/max

ic_url() {  # E-01: compose the watcher DB URL over the Postgres public TCP proxy into $URL
  "$HOME/bin/infisical_auth_refresh.sh" >/dev/null 2>&1 || true
  local TOKEN W PUB; TOKEN=$(cat "$HOME/.config/infisical/sysadmin-token")
  W=$(curl -sf "https://secrets.ai.market/api/v3/secrets/raw/ISSUE_CHANNEL_WATCHER_DATABASE_URL?workspaceId=bd272d48-c5a1-4b52-9d24-12066ae4403c&environment=prod&secretPath=/" -H "Authorization: Bearer $TOKEN" | /usr/bin/python3 -c 'import json,sys;print(json.load(sys.stdin)["secret"]["secretValue"])')
  PUB=$(cd /Users/max/ops/aimarket-backend-main && railway variables -s Postgres --json | python3 -c 'import json,sys;print(json.load(sys.stdin)["DATABASE_PUBLIC_URL"])')
  URL=$(W="$W" PUB="$PUB" python3 -c 'import os;from urllib.parse import urlsplit,urlunsplit;w=urlsplit(os.environ["W"]);p=urlsplit(os.environ["PUB"]);print(urlunsplit((w.scheme,f"{w.username}:{w.password}@{p.hostname}:{p.port}",w.path,w.query,w.fragment)))')
  export URL; [ -n "$URL" ] || { echo "ic_url: compose failed" >&2; return 1; }
}
ic_status() {  # E-01: canonical status counts + intents
  ic_url && psql "$URL" -At -F'|' -c "select current_user, now();" -c "select status, count(*) from issue_channel.canonical_issues group by 1 order by 1;" -c "select count(*) intents from issue_channel.dispatch_intents;"
}
ic_rows() {  # E-01: every canonical row with decision + resolution fields
  ic_url && psql "$URL" -At -F'|' -c "select provider, kind, subject, status, opened_at, resolved_at, episode_key, safe_metadata->'decision'->>'rule_id', safe_metadata->'decision'->>'would_action' from issue_channel.canonical_issues order by opened_at;"
}
ic_health() {  # E-02: deploy + mirror snapshot + board republish
  (cd /Users/max/koskadeux-mcp && railway deployment list -s issue-channel-watcher --json | python3 -c 'import json,sys;d=json.load(sys.stdin);[print(x.get("status"),x.get("createdAt"),(x.get("meta") or {}).get("commitHash","")[:10]) for x in d[:2]]')
  python3 -c "import json;s=json.load(open('/Users/max/koskadeux-state/issue-channel/snapshot.json'));print('generated',s['generated_at'],'open',s['snapshot']['open_count'],'expired',s['snapshot'].get('expired_count'),{k:v['observation_complete'] for k,v in s['snapshot']['sources'].items()})"
  (cd /Users/max/koskadeux-mcp && python3 scripts/ground_truth_open_items.py --publish | grep -i "published to Living")
}
ic_export() {  # E-03: export a fresh replay corpus and replay the shipped rules; $1 = review package dir
  local PKG=${1:?package dir}; local OUT="$PKG/corpus-$(date -u +%Y%m%dT%H%M%SZ)"
  ic_url && (cd /Users/max/koskadeux-mcp && ISSUE_CHANNEL_WATCHER_DATABASE_URL="$URL" venv/bin/python scripts/issue_channel.py --export-corpus "$OUT" && venv/bin/python scripts/issue_channel.py --replay --rules config/issue_channel/dispatch_rules.yaml --corpus "$OUT" > "$OUT.replay.json") && echo "corpus=$OUT report=$OUT.replay.json"
}
ic_package_for_kimi() {  # E-05: $1 base SHA, $2 head SHA, $3 package dir
  local BASE=${1:?} HEAD=${2:?} P=${3:?}; mkdir -p "$P"
  (cd /Users/max/koskadeux-mcp && git diff "$BASE..$HEAD" > "$P/diff-$BASE..$HEAD.patch" && git archive "$HEAD" koskadeux_mcp/issue_channel tests/issue_channel config/issue_channel | tar -x -C "$P")
  (cd "$P" && shasum -a 256 *.patch *.log *.md 2>/dev/null > SHA256SUMS); echo "packaged at $P"
}
