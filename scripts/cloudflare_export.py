#!/usr/bin/env python3
"""Export Cloudflare DR data to S3: DNS records + zone settings (+ best-effort KV state).
Worker SCRIPTS are NOT exported here (their source lives in GitHub). DNS/settings are not secret.
Env (inject via `infisical run`): CLOUDFLARE_API_TOKEN, AWS_BACKUP_WRITER_ACCESS_KEY_ID, AWS_BACKUP_WRITER_SECRET.
Uploads to s3://aimarket-backups-prod/cloudflare/<YYYYMMDD>/cloudflare-<ts>.json
"""
import os, json, sys, time, datetime, tempfile, subprocess, urllib.request, urllib.error, urllib.parse
CF="https://api.cloudflare.com/client/v4"; BUCKET="aimarket-backups-prod"; REGION="eu-north-1"
TOK=os.environ.get("CLOUDFLARE_API_TOKEN","").strip()
ACCT=os.environ.get("CLOUDFLARE_ACCOUNT_ID","d5346d3e0f8f344c5f4915aaca689adf").strip()
def cf(path, params=""):
    url=f"{CF}{path}"+("?"+params if params else ""); last=None
    for t in range(4):
        try:
            req=urllib.request.Request(url, headers={"Authorization":"Bearer "+TOK})
            with urllib.request.urlopen(req, timeout=40) as r: return json.load(r)
        except urllib.error.HTTPError as ex: return {"success":False,"http":ex.code,"body":ex.read().decode()[:200]}
        except Exception as e: last=e; time.sleep(3*(t+1))
    return {"success":False,"error":str(last)}
def main():
    if not TOK: sys.exit("missing CLOUDFLARE_API_TOKEN")
    now=datetime.datetime.now(datetime.timezone.utc)
    out={"exported_at":now.isoformat(),"account_id":ACCT,
         "note":"Cloudflare DR export: DNS records + zone settings (+best-effort KV). Worker scripts NOT here (GitHub).","zones":[]}
    for z in cf("/zones","per_page=50").get("result",[]):
        zid=z["id"]; zone={"id":zid,"name":z["name"],"status":z.get("status")}
        recs=[]; page=1
        while True:
            r=cf(f"/zones/{zid}/dns_records",f"per_page=100&page={page}")
            res=r.get("result",[]) or []; recs.extend(res)
            ti=(r.get("result_info") or {})
            if not res or page>=ti.get("total_pages",1): break
            page+=1
        zone["dns_records"]=recs; zone["dns_record_count"]=len(recs)
        st=cf(f"/zones/{zid}/settings")
        zone["settings"]={s["id"]:s.get("value") for s in st.get("result",[])} if st.get("success") else {"error":st}
        out["zones"].append(zone)
    nl=cf(f"/accounts/{ACCT}/storage/kv/namespaces","per_page=100")
    if nl.get("success"):
        kv={"namespaces":[]}
        for ns in nl.get("result",[]):
            nid=ns["id"]; entry={"id":nid,"title":ns.get("title"),"keys":{}}
            for k in (cf(f"/accounts/{ACCT}/storage/kv/namespaces/{nid}/keys","limit=1000").get("result",[]) or []):
                vurl=f"{CF}/accounts/{ACCT}/storage/kv/namespaces/{nid}/values/{urllib.parse.quote(k['name'],safe='')}"
                try:
                    with urllib.request.urlopen(urllib.request.Request(vurl,headers={"Authorization":"Bearer "+TOK}),timeout=20) as r:
                        entry["keys"][k["name"]]=r.read().decode("utf-8","replace")
                except Exception as e: entry["keys"][k["name"]]={"error":str(e)[:80]}
            kv["namespaces"].append(entry)
    else:
        kv={"note":"KV not exported (token scope or none)","detail":nl}
    out["kv"]=kv
    payload=json.dumps(out,indent=2).encode()
    key=f"cloudflare/{now:%Y%m%d}/cloudflare-{now:%Y%m%dT%H%M%SZ}.json"
    tmp=tempfile.NamedTemporaryFile("wb",suffix=".json",delete=False); tmp.write(payload); tmp.close()
    env=dict(os.environ, AWS_ACCESS_KEY_ID=os.environ["AWS_BACKUP_WRITER_ACCESS_KEY_ID"].strip(),
             AWS_SECRET_ACCESS_KEY=os.environ["AWS_BACKUP_WRITER_SECRET"].strip(), AWS_DEFAULT_REGION=REGION)
    r=subprocess.run(["aws","s3","cp",tmp.name,f"s3://{BUCKET}/{key}","--content-type","application/json"],env=env,capture_output=True,text=True)
    os.unlink(tmp.name)
    if r.returncode!=0: sys.exit("UPLOAD FAILED: "+r.stderr[-300:])
    print(f"uploaded s3://{BUCKET}/{key} ({len(payload)} bytes)")
    for z in out["zones"]: print(f"  zone {z['name']}: {z.get('dns_record_count')} DNS records")
    print("  KV:", ("namespaces="+str(len(out['kv']['namespaces']))) if 'namespaces' in out['kv'] else out['kv'].get('note'))
if __name__=="__main__": main()
