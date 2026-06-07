#!/usr/bin/env python3
"""ai.market Qdrant 'knowledge_base' snapshot -> WORM S3 (aimarket-backups-prod/qdrant/).
Creds injected by `infisical run`: QDRANT_HOST, QDRANT_API_KEY (optional),
AWS_BACKUP_WRITER_ACCESS_KEY_ID, AWS_BACKUP_WRITER_SECRET. Secrets read from env only.
Writer key is PutObject+ListBucket only (no Get/Delete on S3)."""
import os, sys, json, datetime, tempfile, hashlib
BUCKET="aimarket-backups-prod"; REGION="eu-north-1"
COLLECTION=os.environ.get("QDRANT_COLLECTION","knowledge_base")
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
try:
    log(f"creating snapshot of '{COLLECTION}' on {host} ...")
    with httpx.Client(timeout=180.0) as c:
        r=c.post(f"{base}/collections/{COLLECTION}/snapshots",headers=headers); r.raise_for_status()
        name=r.json()["result"]["name"]
    log(f"snapshot created: {name}")
    with tempfile.TemporaryDirectory() as td:
        lp=os.path.join(td,name); h=hashlib.sha256(); n=0
        with httpx.Client(timeout=900.0) as c:
            with c.stream("GET",f"{base}/collections/{COLLECTION}/snapshots/{name}",headers=headers) as resp:
                resp.raise_for_status()
                with open(lp,"wb") as f:
                    for chunk in resp.iter_bytes(): f.write(chunk); h.update(chunk); n+=len(chunk)
        log(f"downloaded {name} ({n} bytes)")
        key=f"qdrant/{COLLECTION}/{day}/{name}"
        s3.upload_file(lp,BUCKET,key,ExtraArgs={"ContentType":"application/octet-stream"})
        items=s3.list_objects_v2(Bucket=BUCKET,Prefix=key).get("Contents",[])
        s3size=items[0]["Size"] if items else -1
        if s3size!=n: write_health("failed",stage="s3_verify",local=n,s3=s3size); log(f"FATAL size mismatch local={n} s3={s3size}"); sys.exit(4)
        log(f"upload OK -> s3://{BUCKET}/{key} ({n} bytes, sha256={h.hexdigest()[:16]})")
    try:
        with httpx.Client(timeout=60.0) as c:
            d=c.delete(f"{base}/collections/{COLLECTION}/snapshots/{name}",headers=headers)
        log(f"server snapshot cleanup: HTTP {d.status_code}")
    except Exception as e: log(f"WARN server snapshot delete failed (non-fatal): {e}")
    write_health("ok",key=key,bytes=n,sha256=h.hexdigest())
    log("SUCCESS qdrant backup")
except Exception as e:
    write_health("failed",error=str(e)[-400:]); log(f"FATAL {e}"); sys.exit(1)
