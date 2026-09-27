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
MAX_PAGES = 1000
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


def listing(response, stage):
    if not isinstance(response, dict) or response.get("success") is not True or not isinstance(response.get("result"), list):
        fail(stage)
    return response["result"], response.get("result_info")


def pages(path, stage, limit, key):
    result, seen, total = [], set(), None
    for page in range(1, MAX_PAGES + 1):
        batch, info = listing(cf(path, f"per_page={limit}&page={page}"), stage)
        if not isinstance(info, dict) or type(info.get("page")) is not int or info["page"] != page:
            fail(stage + " page malformed")
        if "cursor" in info or "cursors" in info:
            fail(stage + " pagination malformed")
        count = info.get("count")
        if count is not None and (type(count) is not int or count != len(batch)):
            fail(stage + " count malformed")
        reported = info.get("total_count")
        if type(reported) is not int or reported < 0 or (total is not None and reported != total):
            fail(stage + " total count malformed")
        total = reported
        if len(batch) > limit or len(result) + len(batch) > total:
            fail(stage + " count inconsistent")
        total_pages = info.get("total_pages")
        expected_pages = max(1, (total + limit - 1) // limit)
        if total_pages is not None and (type(total_pages) is not int or total_pages not in ({0, 1} if total == 0 else {expected_pages})):
            fail(stage + " page count inconsistent")
        for item in batch:
            identifier = record(item, stage, key)
            if identifier in seen:
                fail(stage + " duplicate resource")
            seen.add(identifier)
        result.extend(batch)
        if len(result) == total:
            return result
        if not batch:
            fail(stage + " page stalled")
    fail(stage + " page bound exceeded")


def kv_keys(path):
    result, seen_names, seen_cursors = [], set(), set()
    cursor = None
    for _ in range(MAX_PAGES):
        params = "limit=1000" + ("&cursor=" + urllib.parse.quote(cursor, safe="") if cursor else "")
        batch, info = listing(cf(path, params), "KV keys")
        if not isinstance(info, dict):
            fail("KV keys pagination unverified")
        if "cursors" in info:
            fail("KV keys pagination malformed")
        count = info.get("count")
        if count is not None and (type(count) is not int or count != len(batch)):
            fail("KV keys count malformed")
        if len(batch) > 1000:
            fail("KV keys page oversized")
        for item in batch:
            name = record(item, "KV key", "name")
            if name in seen_names:
                fail("KV key duplicate")
            seen_names.add(name)
        result.extend(batch)
        next_cursor = info.get("cursor")
        if next_cursor is None:
            return result
        if not isinstance(next_cursor, str) or not next_cursor or next_cursor == cursor or next_cursor in seen_cursors:
            fail("KV keys cursor stalled or malformed")
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    fail("KV keys page bound exceeded")


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
        result = subprocess.run(["rtk", "proxy", "aws", "s3", "cp", name, f"s3://{BUCKET}/{key}",
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
    zones = pages("/zones", "zones", 50, "id")
    for item in zones:
        zid = record(item, "zone", "id")
        zone = {"id": zid, "name": record(item, "zone", "name"), "status": item.get("status")}
        records = pages(f"/zones/{zid}/dns_records", "DNS records", 100, "id")
        zone["dns_records"], zone["dns_record_count"] = records, len(records)
        settings, info = listing(cf(f"/zones/{zid}/settings"), "settings")
        if any(not isinstance(setting, dict) or "value" not in setting for setting in settings):
            fail("settings")
        if isinstance(info, dict) and ((info.get("total_count") is not None and info["total_count"] != len(settings)) or
                                       (info.get("total_pages") not in (None, 0, 1))):
            fail("settings pagination incomplete")
        if len({record(setting, "setting", "id") for setting in settings}) != len(settings):
            fail("duplicate setting")
        zone["settings"] = {record(setting, "setting", "id"): setting["value"] for setting in settings}
        out["zones"].append(zone)
    namespaces = pages(f"/accounts/{ACCT}/storage/kv/namespaces", "KV namespaces", 100, "id")
    kv = {"namespaces": []}
    for namespace in namespaces:
        nid = record(namespace, "KV namespace", "id")
        entry = {"id": nid, "title": namespace.get("title"), "keys": {}}
        keys = kv_keys(f"/accounts/{ACCT}/storage/kv/namespaces/{nid}/keys")
        for key in keys:
            name = record(key, "KV key", "name")
            url = f"{CF}/accounts/{ACCT}/storage/kv/namespaces/{nid}/values/{urllib.parse.quote(name, safe='')}"
            try:
                request = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOK})
                with urllib.request.urlopen(request, timeout=20) as response:
                    entry["keys"][name] = response.read().decode("utf-8")
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
