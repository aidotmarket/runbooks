#!/usr/bin/env python3
"""Export Cloudflare DNS, settings and KV within the existing DR boundary."""
import datetime
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

CF = "https://api.cloudflare.com/client/v4"
BUCKET = "aimarket-backups-prod"
REGION = "eu-north-1"
TOK = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
ACCT = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "d5346d3e0f8f344c5f4915aaca689adf").strip()


def fail(stage):
    raise RuntimeError("Cloudflare export incomplete: " + stage)


def cf(path, params=""):
    url = f"{CF}{path}" + ("?" + params if params else "")
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOK})
            with urllib.request.urlopen(request, timeout=40) as response:
                return json.load(response)
        except urllib.error.HTTPError:
            fail("API HTTP error")
        except Exception:
            if attempt == 3:
                fail("API unavailable or malformed")
            time.sleep(3 * (attempt + 1))


def listing(response, stage, page=None, limit=None):
    if not isinstance(response, dict) or response.get("success") is not True or not isinstance(response.get("result"), list):
        fail(stage)
    result = response["result"]
    info = response.get("result_info")
    if limit is not None and info is None:
        fail(stage + " pagination unverified")
    if info is not None:
        if not isinstance(info, dict):
            fail(stage + " pagination malformed")
        pages = info.get("total_pages")
        current = info.get("page")
        if (pages is not None and (type(pages) is not int or pages < 0)) or (current is not None and (type(current) is not int or current < 1)):
            fail(stage + " pagination malformed")
        if pages == 0 and result:
            fail(stage + " pagination malformed")
        if page is None:
            if pages is not None and pages not in (0, 1):
                fail(stage + " pagination incomplete")
            if current is not None and current != 1:
                fail(stage + " pagination incomplete")
        elif current is not None and current != page:
            fail(stage + " pagination malformed")
        total = info.get("total_count")
        if total is not None and (type(total) is not int or total < 0 or (page is None and total != len(result))):
            fail(stage + " pagination incomplete")
        count = info.get("count")
        if count is not None and (type(count) is not int or count != len(result)):
            fail(stage + " pagination malformed")
    elif limit is not None and len(result) >= limit:
        fail(stage + " pagination unverified")
    cursor = response.get("cursor")
    cursors = info.get("cursors") if isinstance(info, dict) else None
    if cursor or (isinstance(info, dict) and (info.get("cursor") or (isinstance(cursors, dict) and cursors.get("after")))):
        fail(stage + " cursor pagination unsupported")
    return result, info or {}


def record(value, stage, key):
    if not isinstance(value, dict) or not isinstance(value.get(key), str) or not value[key]:
        fail(stage)
    return value[key]


def upload(out, now):
    payload = json.dumps(out, indent=2).encode()
    key = f"cloudflare/{now:%Y%m%d}/cloudflare-{now:%Y%m%dT%H%M%SZ}.json"
    env = dict(os.environ, AWS_ACCESS_KEY_ID=os.environ["AWS_BACKUP_WRITER_ACCESS_KEY_ID"].strip(),
               AWS_SECRET_ACCESS_KEY=os.environ["AWS_BACKUP_WRITER_SECRET"].strip(), AWS_DEFAULT_REGION=REGION)
    name = None
    try:
        with tempfile.NamedTemporaryFile("wb", suffix=".json", delete=False) as tmp:
            name = tmp.name
            tmp.write(payload)
        result = subprocess.run(["aws", "s3", "cp", name, f"s3://{BUCKET}/{key}",
                                 "--content-type", "application/json"], env=env,
                                capture_output=True, text=True)
        if result.returncode:
            fail("upload failed")
    finally:
        if name is not None:
            os.unlink(name)
    print(f"uploaded s3://{BUCKET}/{key} ({len(payload)} bytes)")
    print(f"  zones={len(out['zones'])}; KV namespaces={len(out['kv']['namespaces'])}")


def main():
    if not TOK:
        fail("missing CLOUDFLARE_API_TOKEN")
    now = datetime.datetime.now(datetime.timezone.utc)
    out = {"exported_at": now.isoformat(), "account_id": ACCT,
           "note": "Cloudflare DR export: DNS records + zone settings + KV. Worker scripts NOT here (GitHub).",
           "zones": []}
    zones, _ = listing(cf("/zones", "per_page=50"), "zones", limit=50)
    for item in zones:
        zid = record(item, "zone", "id")
        zone = {"id": zid, "name": record(item, "zone", "name"), "status": item.get("status")}
        records = []
        page = 1
        while True:
            batch, info = listing(cf(f"/zones/{zid}/dns_records", f"per_page=100&page={page}"), "DNS records", page, 100)
            for entry in batch:
                record(entry, "DNS record", "id")
            records.extend(batch)
            pages = info.get("total_pages")
            if pages is None:
                if len(batch) == 100:
                    fail("DNS pagination unverified")
                break
            if page >= pages:
                if info.get("total_count") is not None and info["total_count"] != len(records):
                    fail("DNS pagination incomplete")
                break
            if not batch:
                fail("DNS pagination incomplete")
            page += 1
        zone["dns_records"], zone["dns_record_count"] = records, len(records)
        settings, _ = listing(cf(f"/zones/{zid}/settings"), "settings")
        if any(not isinstance(setting, dict) or "value" not in setting for setting in settings):
            fail("settings")
        zone["settings"] = {record(setting, "setting", "id"): setting["value"] for setting in settings}
        out["zones"].append(zone)
    namespaces, _ = listing(cf(f"/accounts/{ACCT}/storage/kv/namespaces", "per_page=100"), "KV namespaces", limit=100)
    kv = {"namespaces": []}
    for namespace in namespaces:
        nid = record(namespace, "KV namespace", "id")
        entry = {"id": nid, "title": namespace.get("title"), "keys": {}}
        keys, _ = listing(cf(f"/accounts/{ACCT}/storage/kv/namespaces/{nid}/keys", "limit=1000"), "KV keys", limit=1000)
        for key in keys:
            name = record(key, "KV key", "name")
            url = f"{CF}/accounts/{ACCT}/storage/kv/namespaces/{nid}/values/{urllib.parse.quote(name, safe='')}"
            try:
                request = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOK})
                with urllib.request.urlopen(request, timeout=20) as response:
                    entry["keys"][name] = response.read().decode("utf-8", "replace")
            except Exception:
                fail("KV value read failed")
        kv["namespaces"].append(entry)
    out["kv"] = kv
    upload(out, now)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        sys.exit(str(exc))
    except (KeyError, TypeError, ValueError, OSError):
        sys.exit("Cloudflare export incomplete: local export failure")
