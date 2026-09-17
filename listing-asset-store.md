---
title: ai.market Listing-Asset Object Store (Cloudflare R2)
owner: mars
last_verified: '2026-09-17'
aliases:
  - listing asset store
  - aimarket-listing-assets
  - sample file store
  - LISTING_ASSET_BUCKET
error_signatures:
  - sample_store_unavailable
  - listing_asset_access_denied
---

# ai.market Listing-Asset Object Store (Cloudflare R2)

**Purpose:** the one object store ai.market owns. It holds seller-chosen free-sample files (multi-file datasets, both routes) and — after the chunk D amendment of `specs/BQ-MULTI-FILE-DATASETS-S1717-GATE2.md` — delivery staging for AIM Data-route directory orders. Before it existed the backend had no store of its own: the rows sample lived in Postgres and fulfillment staging was `/tmp/fulfillment` on a Railway container with no volume (Gate 2 §2, §4.4). Decision D-G2-1: Max, 2026-09-16 ("Lets do the cloudflare bucket"), Event Ledger `cc3a2b7e`.

## Facts

| Item | Value |
| --- | --- |
| Cloudflare account | `d5346d3e0f8f344c5f4915aaca689adf` (the ai.market account; see `cloudflare-and-dns.md`) |
| Bucket | `aimarket-listing-assets` (created by Max in the dashboard, 2026-09-16; location hint EU) |
| S3 endpoint | `https://d5346d3e0f8f344c5f4915aaca689adf.r2.cloudflarestorage.com` (region `auto`) |
| Token | Account API token `aimarket-listing-assets-backend`, **Object Read & Write, scoped to this bucket only**, TTL forever (created by Max, 2026-09-16) |
| Secrets | Infisical project `ai-market-backend` (`bd272d48-…`), env `prod`, path `/`: `LISTING_ASSET_R2_ACCESS_KEY_ID`, `LISTING_ASSET_R2_SECRET_ACCESS_KEY` (entered by Max); `LISTING_ASSET_BUCKET`, `LISTING_ASSET_ENDPOINT` (set by Mars via CLI). The Infisical→Railway sync mirrors all four to the `ai-market-backend` service automatically (`infisical-secrets.md`). |
| Code consumer | none yet — chunk C0 of the S1717 Gate 2 adds `app/services/listing_asset_store.py` and the config fields; until then the variables are inert. |
| Key layout (Gate 2 §3; chunk D amendment §2) | `samples/local/<listing_version_id>/<index>/<sha256>`, `samples/workspace/<row_id>/<reservation_id>/<sha256>`, staging under `samples-staging/…`; delivery staging `orders/<order_id>/<generation>/<member_index>/<sha256>` (`specs/BQ-MULTI-FILE-DATASETS-S1717-CHUNK-D-STORE-AMENDMENT.md`, APPROVED 3/3 on `70d0f360`). |
| Object lifecycle rules (dashboard, set 2026-09-17 S1718 per D-A2, Event Ledger `a3a64f39`) | `Default Multipart Abort Rule` — bucket-wide, abort incomplete multipart uploads after **8 days** (Cloudflare's default rule, raised from 7 to 8 so it sits strictly above `ABANDONED_ORDER_TTL_S` = 7 days); `orders-abort-incomplete-multipart-8d` — prefix `orders/`, abort incomplete multipart uploads after **8 days**. Both are backstops only: the listener's own 3-day upload lease (`TRANSFER_UPLOAD_MAX_AGE_S`) and its `NoSuchUpload` → member-reset rule make correctness independent of them (amendment §3.4/§3.7). No delete-objects or storage-class rule exists; never add one on `orders/` or `samples*/` — the backend's sweeps own object deletion. |

## Verified 2026-09-16 (S1717)

From Titan-1 with the Railway-mirrored credentials (values never printed): `ListObjectsV2` on the bucket → 0 objects; `PutObject` → `GetObject` → `DeleteObject` of `_healthcheck/s1717.txt` all succeeded; `ListObjectsV2` on `ai-market-e2e-r2-test` with the same token → `AccessDenied` (token is bucket-scoped as intended).

## Procedures

**Re-verify access (read-only unless you write the health-check key):**

```bash
cd /Users/max/Projects/ai-market/ai-market-backend && unset RAILWAY_TOKEN
railway variables -e production -s ai-market-backend --json > /tmp/rv.json   # never cat this file
.venv/bin/python - <<'EOF'
import json,boto3,socket,urllib3.util.connection as uc
uc.allowed_gai_family=lambda: socket.AF_INET          # Titan-1: IPv6 to *.r2.cloudflarestorage.com times out
from botocore.config import Config
d=json.load(open('/tmp/rv.json'))
s3=boto3.client('s3',endpoint_url=d['LISTING_ASSET_ENDPOINT'],aws_access_key_id=d['LISTING_ASSET_R2_ACCESS_KEY_ID'],
  aws_secret_access_key=d['LISTING_ASSET_R2_SECRET_ACCESS_KEY'],region_name='auto',config=Config(connect_timeout=10,read_timeout=20,retries={'max_attempts':1}))
print(s3.list_objects_v2(Bucket=d['LISTING_ASSET_BUCKET'],MaxKeys=1).get('KeyCount'))
EOF
rm -f /tmp/rv.json
```

**Check or change the lifecycle rules:** Cloudflare dashboard → R2 → `aimarket-listing-assets` → Settings → Object Lifecycle Rules (`https://dash.cloudflare.com/d5346d3e0f8f344c5f4915aaca689adf/r2/default/buckets/aimarket-listing-assets/settings`). The bucket-scoped backend token is Object Read & Write only and cannot read or write lifecycle configuration through the S3 API, so the dashboard is the record; re-read it after any change and update the table above in the same session.

**Rotate the token:** Cloudflare dashboard → R2 → Manage R2 API Tokens → create a new bucket-scoped Object Read & Write token → put both values in Infisical (same names) → confirm the Railway mirror (`railway variables … --json`, lengths 32/64) → re-verify as above → delete the old token in the dashboard. Rotation triggers a backend redeploy through the sync.

**Never:** store these keys in the repo, a Railway literal, or a chat message; grant the token to more than this bucket; use the `E2E_R2_*` or `aimarket-e2e-harness` credentials for production listing assets.

## When it breaks

| Signature | Meaning | Fix |
| --- | --- | --- |
| `sample_store_unavailable` (publish/upload refused) | backend cannot reach the bucket or the credentials are missing/rotated | re-verify as above; check Infisical → Railway sync; rotate if `AccessDenied` on the own bucket |
| `listing_asset_access_denied` | token no longer scoped to the bucket, or bucket renamed | dashboard token scope; `LISTING_ASSET_BUCKET` value |
| `ConnectTimeoutError` from Titan-1 only | IPv6 path to the R2 endpoint | force IPv4 (see script); production (Railway) is unaffected |
