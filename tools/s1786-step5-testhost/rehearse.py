"""Own a fresh LOCAL database, roles, Redis, host and keys; clean up in finally."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import secrets
import shlex
import socket
import sys
import subprocess
import tempfile
import time
import asyncpg

KIT=Path(__file__).resolve().parent
DB="s1786_step5"
CI="s1786_step5_app"
RUNTIME="s1786_step5_runtime"
REDIS="s1786-step5-testhost-redis"
REDIS_IMAGE="sha256:c6eabf748fc7a61dbb5a705c78bcf3d6377b1127a97d0ce965c11c44ba46896f"

def command(argv, *, env=None, cwd=None, check=True):
    argv=["rtk","proxy",*map(str,argv)]
    print("$ "+shlex.join(argv),flush=True)
    result=subprocess.run(argv,env=env,cwd=cwd)
    print("exit="+str(result.returncode),flush=True)
    if check and result.returncode:
        raise RuntimeError("Command failed (see sanitized output)")
    return result

async def main(a):
    backend=Path(a.backend).resolve()
    python=Path(a.python).absolute()
    port=a.port
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1",port))==0:
            raise ValueError(f"Port {port} occupied; choose --port; no existing service will be stopped")
    owner_url=os.environ["S1786_OWNER_DATABASE_URL"].replace("postgresql+asyncpg://","postgresql://",1)
    from urllib.parse import urlsplit, urlunsplit
    parsed=urlsplit(owner_url)
    if parsed.hostname not in {"127.0.0.1","localhost","::1"}:
        raise ValueError("Owner URL must use loopback")
    c=await asyncpg.connect(owner_url)
    created_db=created_ci=created_runtime=redis_created=False
    host=None
    # Start with a minimal environment: no ambient production credentials or .env.
    env={k:os.environ[k] for k in ("PATH","HOME","TMPDIR","LANG") if k in os.environ}
    env.update(ENVIRONMENT="test",SECRET_KEY=secrets.token_urlsafe(48),PYTHONPATH=str(backend))
    password=secrets.token_hex(32)
    local_owner=urlunsplit(parsed._replace(path="/"+DB))
    try:
        print("SQL (owner, loopback): SELECT current_user, version(); SHOW timezone",flush=True)
        print(dict(await c.fetchrow("SELECT current_user, version()")), await c.fetchval("SHOW timezone"),flush=True)
        for name in (CI,RUNTIME):
            print(f"SQL: CREATE ROLE {name} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS",flush=True)
            await c.execute(f"CREATE ROLE {name} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS")
            if name==CI: created_ci=True
            else: created_runtime=True
        # Parameter values are never logged or passed in argv.
        await c.execute("SELECT set_config('s1786.local_password', $1, false)",password)
        await c.execute("DO $$ BEGIN EXECUTE format('ALTER ROLE s1786_step5_runtime PASSWORD %L',current_setting('s1786.local_password')); END $$")
        print("SQL: runtime password generated locally and set via bound value (suppressed)",flush=True)
        print("SQL: CREATE DATABASE s1786_step5; ALTER DATABASE s1786_step5 SET timezone TO 'UTC'",flush=True)
        await c.execute(f"CREATE DATABASE {DB}")
        created_db=True
        await c.execute(f"ALTER DATABASE {DB} SET timezone TO 'UTC'")
        env.update(DATABASE_URL=local_owner,RUN_ONE_SHOT_S1163_P2="1",ISSUE_CHANNEL_APPLICATION_DB_ROLE=CI,CONNECTOR_RUNTIME_DB_ROLE=CI)
        command([python,"-m","alembic","upgrade","head"],env=env,cwd=backend)
        db=await asyncpg.connect(local_owner)
        try:
            print("SQL: SELECT version_num FROM alembic_version",flush=True)
            print(await db.fetchval("SELECT version_num FROM alembic_version"),flush=True)
            print("SQL: runtime_grants.sql (Step 1 column grants)",flush=True)
            await db.execute((KIT/"runtime_grants.sql").read_text())
        finally:
            await db.close()
        with tempfile.TemporaryDirectory(prefix="s1786-step5-") as tmp:
            fixtures=Path(tmp)/"fixtures.json"
            keys=Path(tmp)/"keys"
            command([python,KIT/"fixtures.py","--output",fixtures],env=env,cwd=backend)
            command([python,KIT/"mint_token.py","--fixtures",fixtures,"--key-dir",keys],env=env,cwd=backend)
            ids=json.loads(fixtures.read_text())
            # Cached image only; isolated instance; no existing Redis is touched.
            result=command(["docker","run","--pull=never","--detach","--name",REDIS,"-p","127.0.0.1:16386:6379",REDIS_IMAGE],check=False)
            redis_created=result.returncode==0
            if not redis_created:
                print("Redis unavailable; single-process connector local limiter fallback will be reported",flush=True)
            env.update(CONNECTOR_ENABLED="true",CONNECTOR_AUTH_ISSUER="https://auth.ai.market",CONNECTOR_AUDIENCE="https://connect.ai.market/mcp",CONNECTOR_JWKS_URL="https://auth.ai.market/.well-known/jwks.json",CONNECTOR_ALLOWED_HOSTS="connect.ai.market",CONNECTOR_EARLY_ACCESS_ENFORCED="true",CONNECTOR_EARLY_ACCESS_USER_IDS=ids["user_id"],DATABASE_URL=f"postgresql://{RUNTIME}:{password}@127.0.0.1:{parsed.port or 5432}/{DB}",REDIS_URL="redis://127.0.0.1:16386/0",CONNECTOR_EXPECTED_PROCESSES="1",CONNECTOR_AUDIT_HMAC_KEY=secrets.token_urlsafe(48),S1786_LOCAL_JWKS_FILE=str(keys/"jwks.json"),QDRANT_HOST="127.0.0.1",QDRANT_PORT="16387",QDRANT_API_KEY=secrets.token_urlsafe(32))
            with socket.socket() as s:
                if s.connect_ex(("127.0.0.1",16387))==0:
                    raise ValueError("No-Qdrant port 16387 unexpectedly reachable")
            print("Environment: canonical identity; runtime role; one process; generated local secrets suppressed; Qdrant 127.0.0.1:16387 unreachable; VERTEX_GEMINI_KEY unset; no signing keys or OTLP",flush=True)
            argv=["rtk","proxy",str(python),"-m","uvicorn","harness_app:app","--app-dir",str(KIT),"--host","127.0.0.1","--port",str(port),"--workers","1"]
            print("$ "+shlex.join(argv),flush=True)
            host=subprocess.Popen(argv,cwd=backend,env=env)
            import httpx
            for _ in range(60):
                if host.poll() is not None:
                    raise RuntimeError("Harness exited before health check")
                try:
                    r=httpx.get(f"http://127.0.0.1:{port}/healthz",trust_env=False,timeout=1)
                    if r.status_code==200:
                        print("GET /healthz: 200 "+r.text,flush=True)
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.5)
            else:
                raise RuntimeError("Harness startup timed out")
            command([python,KIT/"run_calls.py","--fixtures",fixtures,"--token-file",keys/"token.jwt","--url",f"http://127.0.0.1:{port}/mcp"],env=env,cwd=backend)
            db=await asyncpg.connect(local_owner)
            try:
                print("SQL: audit readback as owner (request IDs and HMAC presence only)",flush=True)
                rows=await db.fetch("SELECT request_id,tool,outcome,args_hmac IS NOT NULL AS args_hmac,result_hmac IS NOT NULL AS result_hmac,user_agent_hmac IS NOT NULL AS user_agent_hmac FROM connector_audit_events WHERE event_type='tool.call' ORDER BY occurred_at")
                print(json.dumps([dict(r) for r in rows],indent=2),flush=True)
                assert len(rows)==7 and all(r["args_hmac"] and r["result_hmac"] and r["user_agent_hmac"] for r in rows)
                print("SQL: production visibility predicate applied to fixture IDs",flush=True)
                sys.path.insert(0, str(backend))
                from app.mcp.connector.discovery.visibility import ConnectorListingVisibility
                visible=await db.fetch("SELECT l.id,l.title FROM listings l WHERE "+ConnectorListingVisibility.current().sql())
                print(json.dumps([dict(r)|{"id":str(r["id"])} for r in visible]),flush=True)
                assert {str(r["id"]) for r in visible}=={ids["L1"],ids["L4"]}
                print("PASS: seven audit rows with HMAC fields; PostgreSQL visibility excludes L2/L3",flush=True)
            finally:
                await db.close()
            # Stop while public JWKS still exists. Clean stop flushes audit buffers.
            if host:
                host.terminate()
                host.wait(timeout=15)
                host=None
        print("Deleted temporary local private key, JWT, JWKS and fixture manifest",flush=True)
    finally:
        if host:
            host.terminate()
            try: host.wait(timeout=15)
            except subprocess.TimeoutExpired:
                host.kill(); host.wait()
        if redis_created:
            command(["docker","rm","--force",REDIS],check=False)
        try:
            if created_db:
                print("SQL: DROP DATABASE s1786_step5 WITH (FORCE)",flush=True)
                await c.execute(f"DROP DATABASE {DB} WITH (FORCE)")
            for name,created in ((RUNTIME,created_runtime),(CI,created_ci)):
                if created:
                    print(f"SQL: DROP ROLE {name}",flush=True)
                    await c.execute(f"DROP ROLE {name}")
        finally:
            await c.close()
        print("Teardown finished",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--backend",default="/tmp/s1786-backend-5f3efc85")
    p.add_argument("--python",default="/Users/max/Projects/ai-market/ai-market-backend/.venv/bin/python")
    p.add_argument("--port",type=int,default=8080)
    asyncio.run(main(p.parse_args()))
