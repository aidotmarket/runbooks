"""Insert synthetic S1786 fixtures into a LOCAL migrated DB as migration owner."""
import argparse
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import asyncpg

async def seed(output):
    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
    from urllib.parse import urlsplit
    if urlsplit(url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Fixtures require an explicit loopback DATABASE_URL")
    c = await asyncpg.connect(url)
    ids = {k: str(uuid4()) for k in ("user_id", "organization_id", "membership_id", "session_id", "grant_id", "acceptance_id", "L1", "L2", "L3", "L4")}
    ids["client_id"] = "s1786-step5-test-" + uuid4().hex
    ids["literal_token"] = "s1786literal" + uuid4().hex
    now = datetime.now(timezone.utc)
    async def insert(table, values):
        # Only fixed internal table/column names are interpolated; values are bound.
        cols = list(values)
        await c.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('$'+str(i+1) for i in range(len(cols)))})", *values.values())
    try:
        async with c.transaction():
            await insert("users", dict(id=ids["user_id"], email=f"s1786-{uuid4().hex}@example.invalid", display_name="S1786 SYNTHETIC TEST user", is_test=True, role="buyer"))
            await insert("organizations", dict(id=ids["organization_id"], name="S1786 SYNTHETIC TEST organization", slug="s1786-test-"+uuid4().hex))
            await insert("organization_memberships", dict(id=ids["membership_id"], organization_id=ids["organization_id"], user_id=ids["user_id"], status="active", role="owner"))
            await insert("auth_sessions", dict(id=str(uuid4()), user_id=ids["user_id"], organization_id=ids["organization_id"], session_id=ids["session_id"], refresh_family=str(uuid4()), absolute_expires_at=now+timedelta(hours=1)))
            await insert("connector_oauth_clients", dict(client_id=ids["client_id"], registration_type="dcr", application_type="native", client_name="S1786 SYNTHETIC TEST public client", redirect_uris=json.dumps(["http://127.0.0.1/callback"]), token_endpoint_auth_method="none", grant_types=json.dumps(["authorization_code", "refresh_token"])))
            await insert("connector_oauth_grants", dict(id=ids["grant_id"], user_id=ids["user_id"], organization_id=ids["organization_id"], client_id=ids["client_id"], scopes=["market.read", "account.read"], profile="claude", resource="https://connect.ai.market/mcp", client_verified=True, consent_session_id=ids["session_id"]))
            for scope, key in [("global", "global")]+[("tool", t) for t in ("search_listings", "get_listing", "get_activity", "list_data_requests")]:
                await c.execute("INSERT INTO connector_switches(scope,key,disabled) VALUES($1,$2,false) ON CONFLICT(scope,key) DO UPDATE SET disabled=false", scope, key)
            await insert("seller_license_acceptances", dict(id=ids["acceptance_id"], seller_user_id=ids["user_id"], seller_org_id=ids["organization_id"], party_type="organization", seller_legal_name="S1786 SYNTHETIC TEST", seller_jurisdiction="US", signer_name="S1786 TEST signer", signer_title="TEST owner", authority_confirmed=True, license_code="standard", license_version="1.0", license_params=json.dumps({"ai_training":False}), license_sha256="a"*64, covenant_code="standard", covenant_version="1.0", covenant_sha256="b"*64, source="submission"))
            for label in ("L1", "L2", "L3", "L4"):
                v=dict(id=ids[label], seller_id=ids["user_id"], slug="s1786-test-"+ids[label], title=f"S1786 SYNTHETIC TEST {label} US grocery checkout transactions", description="SYNTHETIC TEST DATA: fictional US grocery checkout transactions.", short_description="SYNTHETIC grocery checkout transaction statistics", price=25, category="Retail", schema_info=json.dumps({"columns":[{"name":"product_category","type":"text"},{"name":"basket_total","type":"numeric"}]}), source_row_count=10, update_cadence_days=7, status="draft" if label=="L3" else "published", is_listed=True, published_at=now if label!="L3" else None, synthetic_queries=json.dumps([]), source_language="en")
                if label != "L2":
                    v.update(license_code="standard", license_version="1.0", license_params=json.dumps({"ai_training":False}), license_sha256="a"*64, covenant_sha256="b"*64, seller_acceptance_id=ids["acceptance_id"], seller_acceptance_source="submission")
                if label == "L4":
                    v["title"] += " " + ids["literal_token"]
                await insert("listings", v)
        Path(output).write_text(json.dumps(ids, indent=2)+"\n")
        print(json.dumps(ids, indent=2))
    finally:
        await c.close()

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    asyncio.run(seed(parser.parse_args().output))
