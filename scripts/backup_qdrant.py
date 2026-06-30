#!/usr/bin/env python3
"""ai.market Qdrant snapshots -> WORM S3 (aimarket-backups-prod/qdrant/).

Backs up EVERY live Qdrant collection (S1081: was knowledge_base-only).
Creds injected by `infisical run`: QDRANT_HOST, QDRANT_API_KEY (required since the
S1081 lockdown), AWS_BACKUP_WRITER_ACCESS_KEY_ID, AWS_BACKUP_WRITER_SECRET.
Optional QDRANT_COLLECTIONS (comma-separated) pins an explicit subset; default = all live.
Writer key is PutObject+ListBucket only (no Get/Delete on S3)."""
import os, sys, json, datetime, tempfile, hashlib
BUCKET="aimarket-backups-prod"; REGION="eu-north-1"
HEALTH_KEY="backup-health/qdrant/last-run.json"
now=datetime.datetime.now(datetime.timezone.utc)
day=now.strftime("%Y%m%d")
def log(m): print(f"[{datetime.datetime.now(datetime.timezone.utc).isoformat()}] {m}", flush=True)
host=os.environ.get("QDRANT_HOST"); api=os.environ.get("QDRANT_API_KEY")
ak=os.environ.get("AWS_BACKUP_WRITER_ACCESS_KEY_ID"); sk=os.environ.get("AWS_BACKUP_WRITER_SECRET")
missing=[n for n,v in [("QDRANT_HOST",host),("AWS_BACKUP_WRITER_ACCESS_KEY_ID",ak),("AWS_BACKUP_WRITER_SECRET",sk)] if not v]
if missing: log(f"FATAL missing env (values not printed): {missing}"); sys.exit(2)
import boto3, httpx
s3=boto3.client("s3",region_name=REGION,aws_access_key_id=ak,aws_secret_access_key=sk)
base=(host if host.startswith("http") else f"https://{host}").rstrip("/"); headers={}
if api: headers["api-key"]=api

def write_health(status,**extra):
    rec={"target":"qdrant","status":status,"ts":now.isoformat(),**extra}
    try:
        s3.put_object(Bucket=BUCKET,Key=HEALTH_KEY,Body=json.dumps(rec).encode(),ContentType="application/json")
        log(f"health record written: status={status}")
    except Exception as e: log(f"WARN health write failed: {e}")

def list_collections():
    override=os.environ.get("QDRANT_COLLECTIONS","").strip()
    if override:
        names=[c.strip() for c in override.split(",") if c.strip()]
        log(f"collections (QDRANT_COLLECTIONS override): {names}")
        return names
    with httpx.Client(timeout=60.0) as c:
        r=c.get(f"{base}/collections",headers=headers); r.raise_for_status()
        names=sorted({i["name"] for i in r.json().get("result",{}).get("collections",[]) if i.get("name")})
    if not names: raise RuntimeError("Qdrant returned no collections")
    log(f"collections discovered: {names}")
    return names

def backup_one(collection):
    log(f"creating snapshot of '{collection}' on {host} ...")
    with httpx.Client(timeout=180.0) as c:
        r=c.post(f"{base}/collections/{collection}/snapshots",headers=headers); r.raise_for_status()
        name=r.json()["result"]["name"]
    log(f"snapshot created: {name}")
    with tempfile.TemporaryDirectory() as td:
        lp=os.path.join(td,name); h=hashlib.sha256(); n=0
        with httpx.Client(timeout=900.0) as c:
            with c.stream("GET",f"{base}/collections/{collection}/snapshots/{name}",headers=headers) as resp:
                resp.raise_for_status()
                with open(lp,"wb") as f:
                    for chunk in resp.iter_bytes(): f.write(chunk); h.update(chunk); n+=len(chunk)
        log(f"downloaded {name} ({n} bytes)")
        key=f"qdrant/{collection}/{day}/{name}"
        s3.upload_file(lp,BUCKET,key,ExtraArgs={"ContentType":"application/octet-stream"})
        items=s3.list_objects_v2(Bucket=BUCKET,Prefix=key).get("Contents",[])
        s3size=items[0]["Size"] if items else -1
        if s3size!=n: raise RuntimeError(f"s3 size mismatch local={n} s3={s3size} key={key}")
        log(f"upload OK -> s3://{BUCKET}/{key} ({n} bytes, sha256={h.hexdigest()[:16]})")
    try:
        with httpx.Client(timeout=60.0) as c:
            d=c.delete(f"{base}/collections/{collection}/snapshots/{name}",headers=headers)
        log(f"server snapshot cleanup: HTTP {d.status_code}")
    except Exception as e: log(f"WARN server snapshot delete failed (non-fatal): {e}")
    return {"collection":collection,"status":"ok","key":key,"bytes":n,"sha256":h.hexdigest()}

results=[]
try:
    names=list_collections()
    for collection in names:
        try:
            results.append(backup_one(collection))
        except Exception as e:
            log(f"FATAL collection backup failed: collection={collection} error={str(e)[-300:]}")
            results.append({"collection":collection,"status":"failed","error":str(e)[-300:]})
except Exception as e:
    write_health("failed",stage="startup",error=str(e)[-400:],collections=results)
    log(f"FATAL {e}"); sys.exit(1)

ok = bool(results) and all(r.get("status")=="ok" for r in results)
write_health("ok" if ok else "failed", collections=results, count=len(results))
if ok:
    log(f"SUCCESS qdrant backup ({len(results)} collections)"); sys.exit(0)
log(f"FAILED qdrant backup (some collections failed): {[r['collection'] for r in results if r.get('status')!='ok']}")
sys.exit(1)
