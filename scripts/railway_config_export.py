#!/usr/bin/env python3
"""Export Railway topology (NO secret VALUES) to S3 for disaster recovery.

Captures every project -> service -> source repo/branch, config-as-code path,
Dockerfile, cron schedule, region, and the *names* of its variables (never values).
Secret VALUES are intentionally excluded -- they live in Infisical, which is itself
backed up to S3; this export is the rebuild MAP, not a secret store.

Env (inject via `infisical run` for scheduled use):
  RAILWAY_API_TOKEN, AWS_BACKUP_WRITER_ACCESS_KEY_ID, AWS_BACKUP_WRITER_SECRET
Uploads to s3://aimarket-backups-prod/railway-config/<YYYYMMDD>/railway-config-<ts>.json
"""
import os, json, sys, time, datetime, tempfile, subprocess, urllib.request, urllib.error

API="https://backboard.railway.app/graphql/v2"
BUCKET="aimarket-backups-prod"; REGION="eu-north-1"
TOK=os.environ.get("RAILWAY_API_TOKEN","").strip()
H={"Authorization":"Bearer "+TOK,"Content-Type":"application/json",
   "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36","Accept":"application/json"}

def gql(q,v=None,tries=4):
    body=json.dumps({"query":q,"variables":v or {}}).encode(); last=None
    for t in range(tries):
        try:
            req=urllib.request.Request(API,data=body,headers=H)
            return json.load(urllib.request.urlopen(req,timeout=45))
        except urllib.error.HTTPError as ex:
            return {"errors":[{"http":ex.code,"body":ex.read().decode()[:200]}]}
        except Exception as e:
            last=e; time.sleep(3*(t+1))
    return {"errors":[{"net":str(last)}]}

def main():
    if not TOK: sys.exit("missing RAILWAY_API_TOKEN")
    now=datetime.datetime.now(datetime.timezone.utc)
    out={"exported_at":now.isoformat(),
         "note":"Railway topology for DR rebuild. Secret VALUES excluded (live in Infisical, backed up separately). Variable NAMES only.",
         "projects":[]}
    pr=gql('{ projects { edges { node { id name } } } }')
    for pe in pr.get("data",{}).get("projects",{}).get("edges",[]):
        pid=pe["node"]["id"]; pname=pe["node"]["name"]
        pd=gql('query($id:String!){ project(id:$id){ name environments{edges{node{id name}}} services{edges{node{id name}}} } }',{"id":pid})
        proj=pd.get("data",{}).get("project")
        if not proj:
            out["projects"].append({"id":pid,"name":pname,"error":pd.get("errors")}); continue
        envs={e["node"]["name"]:e["node"]["id"] for e in proj["environments"]["edges"]}
        eid=envs.get("production") or (list(envs.values())[0] if envs else None)
        pj={"id":pid,"name":pname,"environments":list(envs.keys()),"prod_env_id":eid,"services":[]}
        for se in proj["services"]["edges"]:
            sid=se["node"]["id"]; sname=se["node"]["name"]; svc={"id":sid,"name":sname}
            dep=gql('query($e:String!,$s:String!){ deployments(first:1, input:{environmentId:$e, serviceId:$s}){ edges{ node{ status createdAt meta } } } }',{"e":eid,"s":sid})
            try:
                node=dep["data"]["deployments"]["edges"][0]["node"]; m=node.get("meta",{}) or {}; sm=m.get("serviceManifest",{}) or {}
                svc["source"]={"repo":m.get("repo"),"branch":m.get("branch")}
                svc["configFile"]=m.get("configFile")
                svc["build"]=sm.get("build"); svc["deploy"]=sm.get("deploy")
                svc["last_deploy"]={"status":node.get("status"),"at":node.get("createdAt")}
            except Exception as e:
                svc["meta_note"]="no deployment meta (e.g. database plugin) "+str(e)[:60]
            v=gql('query($p:String!,$e:String!,$s:String!){ variables(projectId:$p, environmentId:$e, serviceId:$s) }',{"p":pid,"e":eid,"s":sid})
            vd=v.get("data",{}).get("variables")
            svc["variable_names"]=sorted(vd.keys()) if isinstance(vd,dict) else {"error":v.get("errors")}
            pj["services"].append(svc)
        out["projects"].append(pj)
    payload=json.dumps(out,indent=2).encode()
    key=f"railway-config/{now:%Y%m%d}/railway-config-{now:%Y%m%dT%H%M%SZ}.json"
    tmp=tempfile.NamedTemporaryFile("wb",suffix=".json",delete=False); tmp.write(payload); tmp.close()
    env=dict(os.environ,
             AWS_ACCESS_KEY_ID=os.environ["AWS_BACKUP_WRITER_ACCESS_KEY_ID"].strip(),
             AWS_SECRET_ACCESS_KEY=os.environ["AWS_BACKUP_WRITER_SECRET"].strip(),
             AWS_DEFAULT_REGION=REGION)
    r=subprocess.run(["aws","s3","cp",tmp.name,f"s3://{BUCKET}/{key}","--content-type","application/json"],env=env,capture_output=True,text=True)
    os.unlink(tmp.name)
    if r.returncode!=0: sys.exit("UPLOAD FAILED: "+r.stderr[-300:])
    print(f"uploaded s3://{BUCKET}/{key} ({len(payload)} bytes; {len(out['projects'])} projects)")
    for p in out["projects"]:
        print("  -", p["name"], "->", [s["name"] for s in p.get("services",[])])

if __name__=="__main__":
    main()
