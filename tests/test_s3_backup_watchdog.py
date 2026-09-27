"""Isolated watchdog regressions: fake AWS, date and Telegram commands."""
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/s3_backup_watchdog.sh"
NOW = dt.datetime(2026, 9, 27, 12, tzinfo=dt.timezone.utc)
NAMES = ("action_logs", "aim_tools", "data_requests", "knowledge_base",
         "knowledge_base_v2", "listings")


def stamp(hours_ago=1, seconds_ago=0):
    return (NOW - dt.timedelta(hours=hours_ago, seconds=seconds_ago)).strftime("%Y-%m-%d %H:%M:%S")


def listing(key, hours_ago=1, size=20, seconds_ago=0):
    return f"{stamp(hours_ago, seconds_ago)} {size} {key}\n"


def fixture():
    keys = {name: f"qdrant/{name}/20260927/snapshot" for name in NAMES}
    data = {
        "postgres/ai-market/": listing("postgres/ai-market/dump"),
        "postgres/infisical/": listing("postgres/infisical/dump"),
        "qdrant/": "".join(listing(key) for key in keys.values()),
        "railway-config/": listing("railway-config/export"),
        "cloudflare/": listing("cloudflare/export"),
    }
    manifest = {"target": "qdrant", "status": "ok", "count": len(keys),
                "ts": NOW.isoformat(),
                "collections": [
                    {"collection": name, "status": "ok", "key": key, "bytes": 20}
                    for name, key in keys.items()
                ]}
    return data, manifest


def run_case(tmp_path, data=None, manifest=None, *, envfile=True,
             telegram_http="200", telegram_body=None, tz="Europe/Madrid"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    if data is None or manifest is None:
        data, manifest = fixture()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (tmp_path / "data.json").write_text(json.dumps(data))
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (bin_dir / "aws").write_text("""#!/usr/bin/env python3
import datetime as dt, json, os, pathlib, sys
from zoneinfo import ZoneInfo
data = json.loads(pathlib.Path(os.environ["MOCK_DATA"]).read_text())
if sys.argv[1:3] == ["s3", "ls"]:
    prefix = sys.argv[3].split("aimarket-backups-prod/", 1)[1]
    value = data.get(prefix)
    if value is None:
        sys.exit(3)
    for line in value.splitlines(keepends=True):
        try:
            utc = dt.datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc)
        except ValueError:
            sys.stdout.write(line)
        else:
            local = utc.astimezone(ZoneInfo(os.environ["TZ"]))
            sys.stdout.write(local.strftime("%Y-%m-%d %H:%M:%S") + line[19:])
elif sys.argv[1:3] == ["s3", "cp"]:
    pathlib.Path(sys.argv[4]).write_bytes(pathlib.Path(os.environ["MOCK_MANIFEST"]).read_bytes())
else:
    sys.exit(4)
""")
    (bin_dir / "date").write_text(f"""#!/bin/sh
case "$2" in
  +%s) echo {int(NOW.timestamp())} ;;
  +%FT%TZ) echo 2026-09-27T12:00:00Z ;;
  *) exit 3 ;;
esac
""")
    (bin_dir / "curl").write_text("""#!/usr/bin/env python3
import os, pathlib, sys
args = sys.argv[1:]
pathlib.Path(os.environ["MOCK_CALLS"]).open("a").write("call\\n")
pathlib.Path(args[args.index("--output") + 1]).write_text(os.environ["MOCK_TG_BODY"])
print(os.environ["MOCK_TG_HTTP"], end="")
""")
    for path in bin_dir.iterdir():
        path.chmod(0o755)
    credential_file = tmp_path / "env"
    if envfile:
        credential_file.write_text("TELEGRAM_BOT_TOKEN=secret-token\nTELEGRAM_CHAT_ID=secret-chat\n")
    log = tmp_path / "watchdog.log"
    calls = tmp_path / "calls"
    environment = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
                       TZ=tz, WATCHDOG_ENVF=str(credential_file), WATCHDOG_LOG=str(log),
                       MOCK_DATA=str(tmp_path / "data.json"),
                       MOCK_MANIFEST=str(tmp_path / "manifest.json"),
                       MOCK_CALLS=str(calls), MOCK_TG_HTTP=telegram_http,
                       MOCK_TG_BODY=telegram_body or '{"ok":true,"result":{"message_id":42}}')
    result = subprocess.run(["bash", str(SCRIPT)], env=environment, text=True,
                            capture_output=True, timeout=20)
    output = log.read_text() if log.exists() else ""
    assert "secret-token" not in output + result.stdout + result.stderr
    assert "secret-chat" not in output + result.stdout + result.stderr
    return result.returncode, output, calls.read_text().count("call") if calls.exists() else 0


@pytest.mark.parametrize("tz", ("UTC", "Europe/Madrid", "America/Los_Angeles"))
def test_utc_listing_under_inherited_timezone(tmp_path, tz):
    code, log, calls = run_case(tmp_path, tz=tz)
    assert code == 0 and log.count("OK(") == 5 and calls == 0


@pytest.mark.parametrize("tz", ("UTC", "Europe/Madrid", "America/Los_Angeles"))
def test_exact_threshold_and_malformed_or_missing_listing(tmp_path, tz):
    data, manifest = fixture()
    data["postgres/ai-market/"] = listing("postgres/ai-market/dump", 26)
    data["railway-config/"] = listing("railway-config/export", 26, seconds_ago=-1)
    data["postgres/infisical/"] = "bad listing\n"
    data["cloudflare/"] = None
    code, log, calls = run_case(tmp_path, data, manifest, tz=tz)
    assert code != 0 and calls == 3
    assert "ALERT(postgres)" in log
    assert "ALERT(infisical-secrets): malformed S3 listing" in log
    assert "ALERT(cloudflare): S3 listing failed" in log
    assert "OK(railway-config)" in log
    assert log.count("message_id=42") == 3


@pytest.mark.parametrize("tz", ("UTC", "Europe/Madrid", "America/Los_Angeles"))
def test_qdrant_collection_at_exact_threshold(tmp_path, tz):
    data, manifest = fixture()
    key = "qdrant/listings/20260927/snapshot"
    data["qdrant/"] = data["qdrant/"].replace(listing(key), listing(key, 26))
    code, log, calls = run_case(tmp_path, data, manifest, tz=tz)
    assert code != 0 and "ALERT(qdrant): stale or empty collection snapshot" in log
    assert calls == 1 and "Telegram confirmed(qdrant): message_id=42" in log


def test_qdrant_stale_and_missing_sibling(tmp_path):
    data, manifest = fixture()
    data["qdrant/"] = data["qdrant/"].replace(
        listing("qdrant/listings/20260927/snapshot"),
        listing("qdrant/listings/20260927/snapshot", 27))
    code, log, calls = run_case(tmp_path, data, manifest)
    assert code != 0 and "stale or empty collection snapshot" in log and calls == 1
    data["qdrant/"] = data["qdrant/"].replace(
        listing("qdrant/listings/20260927/snapshot", 27), "")
    code, log, calls = run_case(tmp_path / "missing", data, manifest)
    assert code != 0 and "missing collection snapshot" in log and calls == 1


def test_failed_incomplete_and_discovered_collection(tmp_path):
    data, manifest = fixture()
    manifest["status"] = "failed"
    code, log, _ = run_case(tmp_path, data, manifest)
    assert code != 0 and "failed or incomplete health manifest" in log
    data, manifest = fixture()
    manifest["collections"].pop()
    manifest["count"] -= 1
    code, log, _ = run_case(tmp_path / "incomplete", data, manifest)
    assert code != 0 and "missing collection in health manifest" in log
    data, manifest = fixture()
    data["qdrant/"] += listing("qdrant/new_collection/20260927/snapshot")
    code, log, _ = run_case(tmp_path / "discovered", data, manifest)
    assert code != 0 and "missing collection in health manifest" in log
    data, manifest = fixture()
    manifest["collections"][0]["status"] = "failed"
    code, log, _ = run_case(tmp_path / "failed_row", data, manifest)
    assert code != 0 and "failed or incomplete health manifest" in log
    data, manifest = fixture()
    manifest["ts"] = (NOW - dt.timedelta(hours=26)).isoformat()
    code, log, _ = run_case(tmp_path / "old_manifest", data, manifest)
    assert code != 0 and "stale health manifest" in log


def test_telegram_http_api_and_missing_credentials_fail_visible(tmp_path):
    data, manifest = fixture()
    data["postgres/ai-market/"] = ""
    for label, options in (
        ("http", {"telegram_http": "500"}),
        ("api", {"telegram_body": '{"ok":false,"description":"secret-token"}'}),
        ("credentials", {"envfile": False}),
    ):
        code, log, calls = run_case(tmp_path / label, data, manifest, **options)
        assert code != 0 and "Telegram delivery failed(postgres)" in log
        assert "message_id=" not in log
        assert calls == (0 if label == "credentials" else 1)
