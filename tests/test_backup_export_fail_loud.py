"""Offline contract tests for the two backup exporters."""
import importlib.util
import io
import json
import runpy
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


ROOT = Path(__file__).resolve().parents[1] / "scripts"
SENTINEL = "SECRET_VALUE_DO_NOT_LOG"


def load(name, monkeypatch):
    monkeypatch.setenv("RAILWAY_API_TOKEN", "token")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token")
    monkeypatch.setenv("AWS_BACKUP_WRITER_ACCESS_KEY_ID", "writer")
    monkeypatch.setenv("AWS_BACKUP_WRITER_SECRET", "writer-secret")
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    return module


def upload_spy(module, monkeypatch, returncode=0):
    payloads = []

    def run(argv, **kwargs):
        assert argv[:3] == ["rtk", "proxy", "aws"]
        payloads.append(json.loads(Path(argv[5]).read_text()))
        return SimpleNamespace(returncode=returncode, stderr=SENTINEL)

    monkeypatch.setattr(module.subprocess, "run", run)
    return payloads


def railway_responses(deployments=None):
    return [
        {"data": {"workspaceType": {"fields": [{"name": "projects", "args": []}]},
                  "projectType": {"fields": [{"name": "environments", "args": []}, {"name": "services", "args": []}]}}},
        {"data": {"me": {"workspaces": [{"id": "w"}]}}},
        {"data": {"workspace": {"projects": {"edges": [{"node": {"id": "p", "name": "project"}}],
                                                    "pageInfo": {"hasNextPage": False}}}}},
        {"data": {"project": {"environments": {"edges": [{"node": {"id": "e", "name": "production"}}],
                                                 "pageInfo": {"hasNextPage": False}}}}},
        {"data": {"project": {"services": {"edges": [{"node": {"id": "s", "name": "service"}}],
                                              "pageInfo": {"hasNextPage": False}}}}},
        {"data": {"deployments": {"edges": [] if deployments is None else deployments}}},
        {"data": {"variables": {"SECRET_NAME": SENTINEL}}},
    ]


def test_railway_success_database_plugin_and_names_only(monkeypatch, capsys):
    module = load("railway_config_export", monkeypatch)
    responses = iter(railway_responses())
    monkeypatch.setattr(module, "gql", lambda *args, **kwargs: next(responses))
    uploads = upload_spy(module, monkeypatch)
    module.main()
    assert len(uploads) == 1
    assert uploads[0]["projects"][0]["services"][0]["variable_names"] == ["SECRET_NAME"]
    assert "meta_note" in uploads[0]["projects"][0]["services"][0]
    assert SENTINEL not in json.dumps(uploads[0]) + capsys.readouterr().out


@pytest.mark.parametrize("index,replacement", [
    (0, {"errors": [{"message": SENTINEL}], "data": {}}),
    (1, {"data": {"me": {"workspaces": [None]}}}),
    (2, {"data": {"workspace": {"projects": {"edges": []}}}}),
    (2, {"data": {"workspace": {"projects": {"edges": [], "pageInfo": {"hasNextPage": True}}}}}),
    (3, {"errors": [{"message": SENTINEL}], "data": {"project": None}}),
    (3, {"data": {"project": {"environments": {"edges": []}}}}),
    (4, {"data": {"project": {"services": None}}}),
    (5, {"errors": [{"message": SENTINEL}], "data": {"deployments": {"edges": []}}}),
    (5, {"data": {"deployments": {"edges": [{"node": {}}, {"node": {}}]}}}),
    (6, {"data": {"variables": None}}),
])
def test_railway_incomplete_never_uploads(monkeypatch, capsys, index, replacement):
    module = load("railway_config_export", monkeypatch)
    responses = railway_responses()
    responses[index] = replacement
    iterator = iter(responses)
    monkeypatch.setattr(module, "gql", lambda *args, **kwargs: next(iterator))
    uploads = upload_spy(module, monkeypatch)
    with pytest.raises((RuntimeError, TypeError, KeyError)):
        module.main()
    assert uploads == []
    captured = capsys.readouterr()
    assert SENTINEL not in captured.out + captured.err


def cf_responses():
    return [
        {"success": True, "result": [{"id": "z", "name": "zone"}], "result_info": {"page": 1, "count": 1, "total_pages": 1, "total_count": 1}},
        {"success": True, "result": [{"id": "r", "content": SENTINEL}], "result_info": {"page": 1, "count": 1, "total_pages": 1, "total_count": 1}},
        {"success": True, "result": [{"id": "setting", "value": SENTINEL}]},
        {"success": True, "result": [{"id": "n", "title": "namespace"}], "result_info": {"page": 1, "count": 1, "total_count": 1}},
        {"success": True, "result": [{"name": "key"}], "result_info": {"count": 1}},
    ]


def cloudflare_setup(monkeypatch, responses, value_error=False, upload_code=0):
    module = load("cloudflare_export", monkeypatch)
    iterator = iter(responses)
    monkeypatch.setattr(module, "cf", lambda *args: next(iterator))
    def urlopen(*args, **kwargs):
        if value_error:
            raise OSError(SENTINEL)
        return Mock(__enter__=lambda self: self, __exit__=lambda *args: None,
                    read=lambda: SENTINEL.encode())
    monkeypatch.setattr(module.urllib.request, "urlopen", urlopen)
    return module, upload_spy(module, monkeypatch, upload_code)


def test_cloudflare_success_upload_once(monkeypatch, capsys):
    module, uploads = cloudflare_setup(monkeypatch, cf_responses())
    module.main()
    assert len(uploads) == 1
    assert uploads[0]["kv"]["namespaces"][0]["keys"]["key"] == SENTINEL
    assert SENTINEL not in capsys.readouterr().out


def test_cloudflare_single_kv_page_empty_cursor_uploads_once(monkeypatch):
    responses = cf_responses()
    responses[4]["result_info"]["cursor"] = ""
    module, uploads = cloudflare_setup(monkeypatch, responses)
    module.main()
    assert len(uploads) == 1
    assert uploads[0]["kv"]["namespaces"][0]["keys"] == {"key": SENTINEL}


@pytest.mark.parametrize("index,replacement", [
    (0, {"success": False, "errors": [SENTINEL]}),
    (0, {"success": True, "result": []}),
    (0, {"success": True, "result": [], "result_info": {"total_pages": 2}}),
    (1, {"success": False, "errors": [SENTINEL]}),
    (1, {"success": True, "result": [], "result_info": {"page": 1, "total_pages": 2}}),
    (2, {"success": True, "result": None}),
    (2, {"success": True, "result": [{"id": "setting"}]}),
    (3, {"success": False, "errors": [SENTINEL]}),
    (3, {"success": True, "result": [], "result_info": {"cursor": "next"}}),
    (4, {"success": False, "errors": [SENTINEL]}),
    (4, {"success": True, "result": [], "result_info": {"cursors": {"after": "next"}}}),
    (4, {"success": True, "result": [{"name": "key"}], "result_info": {"count": 1, "cursor": 0}}),
    (4, {"success": True, "result": [{"name": "key"}], "result_info": {"count": 1, "cursor": False}}),
    (4, {"success": True, "result": [{"name": "key"}], "result_info": {"count": 1, "cursor": []}}),
])
def test_cloudflare_incomplete_never_uploads(monkeypatch, capsys, index, replacement):
    responses = cf_responses()
    responses[index] = replacement
    module, uploads = cloudflare_setup(monkeypatch, responses)
    with pytest.raises(RuntimeError):
        module.main()
    assert uploads == []
    captured = capsys.readouterr()
    assert SENTINEL not in captured.out + captured.err


def test_kv_value_failure_never_uploads(monkeypatch, capsys):
    module, uploads = cloudflare_setup(monkeypatch, cf_responses(), value_error=True)
    with pytest.raises(RuntimeError):
        module.main()
    assert uploads == []
    assert SENTINEL not in capsys.readouterr().err


def test_invalid_utf8_kv_value_never_uploads(monkeypatch):
    module, uploads = cloudflare_setup(monkeypatch, cf_responses())
    monkeypatch.setattr(module.urllib.request, "urlopen",
                        lambda *args, **kwargs: Mock(__enter__=lambda self: self,
                                                     __exit__=lambda *args: None,
                                                     read=lambda: b"\xff"))
    with pytest.raises(RuntimeError, match="KV value read failed"):
        module.main()
    assert uploads == []


@pytest.mark.parametrize("name", ["railway_config_export", "cloudflare_export"])
def test_upload_failure_removes_temp_without_logging_stderr(monkeypatch, capsys, name):
    module = load(name, monkeypatch)
    created = []
    original = module.tempfile.NamedTemporaryFile
    def temporary(*args, **kwargs):
        tmp = original(*args, **kwargs)
        created.append(Path(tmp.name))
        return tmp
    monkeypatch.setattr(module.tempfile, "NamedTemporaryFile", temporary)
    if name == "railway_config_export":
        iterator = iter(railway_responses())
        monkeypatch.setattr(module, "gql", lambda *args, **kwargs: next(iterator))
    else:
        iterator = iter(cf_responses())
        monkeypatch.setattr(module, "cf", lambda *args: next(iterator))
        monkeypatch.setattr(module.urllib.request, "urlopen",
                            lambda *args, **kwargs: Mock(__enter__=lambda self: self,
                                                         __exit__=lambda *args: None,
                                                         read=lambda: SENTINEL.encode()))
    uploads = upload_spy(module, monkeypatch, 1)
    with pytest.raises(RuntimeError):
        module.main()
    assert len(uploads) == 1
    assert created and not created[0].exists()
    assert SENTINEL not in capsys.readouterr().out


@pytest.mark.parametrize("name", ["railway_config_export", "cloudflare_export"])
def test_http_denial_cli_exits_nonzero_without_upload_or_body(monkeypatch, capsys, name):
    monkeypatch.setenv("RAILWAY_API_TOKEN", "token")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token")
    monkeypatch.setattr(urllib.request, "urlopen", Mock(side_effect=urllib.error.HTTPError(
        "https://example.invalid", 403, "denied", {}, io.BytesIO(SENTINEL.encode()))))
    upload = Mock(side_effect=AssertionError("upload must not run"))
    monkeypatch.setattr(subprocess, "run", upload)
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(ROOT / (name + ".py")), run_name="__main__")
    assert exit_info.value.code != 0
    upload.assert_not_called()
    captured = capsys.readouterr()
    assert SENTINEL not in captured.out + captured.err + str(exit_info.value)


def test_railway_multi_page_export_once(monkeypatch, capsys):
    module = load("railway_config_export", monkeypatch)
    args = [{"name": "first", "type": {"name": "Int"}}, {"name": "after", "type": {"name": "String"}}]
    calls = []
    def connection(nodes, more=False, cursor=None, count=2):
        return {"edges": [{"node": node} for node in nodes],
                "pageInfo": {"hasNextPage": more, "endCursor": cursor}, "totalCount": count}
    def gql(query, variables=None):
        variables = variables or {}
        calls.append((query, variables))
        if "__type" in query:
            return {"data": {"workspaceType": {"fields": [{"name": "projects", "args": args}]},
                             "projectType": {"fields": [{"name": key, "args": args} for key in ("environments", "services")]}}}
        if "workspaces" in query:
            return {"data": {"me": {"workspaces": [{"id": "w"}]}}}
        if "workspace(" in query:
            second = variables["after"] is not None
            return {"data": {"workspace": {"projects": connection([{"id": "p2", "name": "two"}] if second else
                                                                  [{"id": "p1", "name": "one"}], not second, "p1" if not second else "p2")}}}
        if "project(" in query:
            field = "environments" if "environments" in query else "services"
            second = variables["after"] is not None
            node = ({"id": "e2", "name": "staging"} if second else {"id": "e1", "name": "production"}) if field == "environments" else ({"id": "s2", "name": "db"} if second else {"id": "s1", "name": "api"})
            return {"data": {"project": {field: connection([node], not second, field + "1" if not second else field + "2")}}}
        if "deployments(" in query:
            return {"data": {"deployments": {"edges": []}}}
        if "variables(" in query:
            return {"data": {"variables": {"SECRET_NAME": SENTINEL}}}
        raise AssertionError(query)
    monkeypatch.setattr(module, "gql", gql)
    uploads = upload_spy(module, monkeypatch)
    module.main()
    assert len(uploads) == 1
    assert [project["id"] for project in uploads[0]["projects"]] == ["p1", "p2"]
    assert all([service["id"] for service in project["services"]] == ["s1", "s2"] for project in uploads[0]["projects"])
    assert all("first:50,after:$after" in query for query, variables in calls if variables.get("after"))
    assert SENTINEL not in json.dumps(uploads) + capsys.readouterr().out


@pytest.mark.parametrize("second", [
    {"edges": [{"node": {"id": "a"}}], "pageInfo": {"hasNextPage": True, "endCursor": "one"}},
    {"edges": [{"node": {"id": "a"}}], "pageInfo": {"hasNextPage": False}},
    {"edges": [{"node": {"id": "b"}}], "pageInfo": {"hasNextPage": True, "endCursor": None}},
    {"edges": [{"node": {"id": "b"}}], "pageInfo": {"hasNextPage": False}, "totalCount": 3},
])
def test_railway_later_page_stall_duplicate_or_count_fails(second, monkeypatch):
    module = load("railway_config_export", monkeypatch)
    first = {"edges": [{"node": {"id": "a"}}], "pageInfo": {"hasNextPage": True, "endCursor": "one"}, "totalCount": 2}
    responses = iter([first, second])
    with pytest.raises(RuntimeError):
        module.collect(lambda _: next(responses), "projects", True)


@pytest.mark.parametrize("terminal_cursor", [None, ""])
def test_cloudflare_multi_page_zones_namespaces_and_kv(monkeypatch, terminal_cursor):
    module = load("cloudflare_export", monkeypatch)
    calls = []
    def page(items, number, total):
        return {"success": True, "result": items, "result_info": {"page": number, "count": len(items), "total_count": total}}
    def cf(path, params=""):
        calls.append((path, params))
        if path == "/zones":
            number = 2 if "page=2" in params else 1
            return page([{"id": "z" + str(number), "name": "zone"}], number, 2)
        if path.endswith("/dns_records"):
            return page([{"id": "r"}], 1, 1)
        if path.endswith("/settings"):
            return {"success": True, "result": [{"id": "ssl", "value": "full"}]}
        if path.endswith("/namespaces"):
            number = 2 if "page=2" in params else 1
            return page([{"id": "n" + str(number), "title": "namespace"}], number, 2)
        if path.endswith("/keys"):
            second = "cursor=" in params
            info = {"count": 1}
            if not second:
                info["cursor"] = "next"
            elif terminal_cursor is not None:
                info["cursor"] = terminal_cursor
            return {"success": True, "result": [{"name": "k2" if second else "k1"}],
                    "result_info": info}
        raise AssertionError(path)
    monkeypatch.setattr(module, "cf", cf)
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *args, **kwargs:
                        Mock(__enter__=lambda self: self, __exit__=lambda *args: None, read=lambda: SENTINEL.encode()))
    uploads = upload_spy(module, monkeypatch)
    module.main()
    assert len(uploads) == 1
    assert [z["id"] for z in uploads[0]["zones"]] == ["z1", "z2"]
    assert [n["id"] for n in uploads[0]["kv"]["namespaces"]] == ["n1", "n2"]
    assert all(list(n["keys"]) == ["k1", "k2"] for n in uploads[0]["kv"]["namespaces"])
    assert any("cursor=next" in params for _, params in calls)


@pytest.mark.parametrize("second", [
    {"success": False, "errors": [SENTINEL]},
    {"success": True, "result": [{"id": "a"}], "result_info": {"page": 2, "count": 1, "total_count": 2}},
    {"success": True, "result": [], "result_info": {"page": 2, "count": 0, "total_count": 2}},
    {"success": True, "result": [{"id": "b"}], "result_info": {"page": 2, "count": 1, "total_count": 3}},
])
def test_cloudflare_later_page_failure_duplicate_stall_count(second, monkeypatch):
    module = load("cloudflare_export", monkeypatch)
    first = {"success": True, "result": [{"id": "a"}], "result_info": {"page": 1, "count": 1, "total_count": 2}}
    responses = iter([first, second])
    monkeypatch.setattr(module, "cf", lambda *args: next(responses))
    with pytest.raises(RuntimeError):
        module.pages("/zones", "zones", 50, "id")


@pytest.mark.parametrize("second", [
    {"success": False, "errors": [SENTINEL]},
    {"success": True, "result": [{"name": "a"}], "result_info": {"count": 1}},
    {"success": True, "result": [], "result_info": {"count": 0, "cursor": "one"}},
    {"success": True, "result": [], "result_info": {"count": 0, "cursor": []}},
    {"success": True, "result": [], "result_info": {"count": 0, "cursor": False}},
    {"success": True, "result": [], "result_info": {"count": 0, "cursor": 0}},
    {"success": True, "result": [], "result_info": {"count": 0, "cursor": {}}},
])
def test_kv_later_page_failure_duplicate_stall_or_malformed_cursor(second, monkeypatch):
    module = load("cloudflare_export", monkeypatch)
    first = {"success": True, "result": [{"name": "a"}], "result_info": {"count": 1, "cursor": "one"}}
    responses = iter([first, second])
    monkeypatch.setattr(module, "cf", lambda *args: next(responses))
    with pytest.raises(RuntimeError):
        module.kv_keys("/keys")


def test_later_railway_page_error_never_uploads(monkeypatch, capsys):
    module = load("railway_config_export", monkeypatch)
    args = [{"name": "first", "type": {"name": "Int"}}, {"name": "after", "type": {"name": "String"}}]
    responses = iter([
        {"data": {"workspaceType": {"fields": [{"name": "projects", "args": args}]},
                  "projectType": {"fields": [{"name": "environments", "args": args}, {"name": "services", "args": args}]}}},
        {"data": {"me": {"workspaces": [{"id": "w"}]}}},
        {"data": {"workspace": {"projects": {"edges": [{"node": {"id": "p", "name": "project"}}],
                                               "pageInfo": {"hasNextPage": True, "endCursor": "next"}}}}},
        {"errors": [{"message": SENTINEL}], "data": {"workspace": None}},
    ])
    monkeypatch.setattr(module, "gql", lambda *args, **kwargs: next(responses))
    uploads = upload_spy(module, monkeypatch)
    with pytest.raises(RuntimeError):
        module.main()
    assert uploads == []
    assert SENTINEL not in capsys.readouterr().out


def test_later_cloudflare_page_error_never_uploads(monkeypatch, capsys):
    module = load("cloudflare_export", monkeypatch)
    responses = iter([
        {"success": True, "result": [{"id": "z", "name": "zone"}],
         "result_info": {"page": 1, "count": 1, "total_count": 2}},
        {"success": False, "errors": [SENTINEL]},
    ])
    monkeypatch.setattr(module, "cf", lambda *args: next(responses))
    uploads = upload_spy(module, monkeypatch)
    with pytest.raises(RuntimeError):
        module.main()
    assert uploads == []
    assert SENTINEL not in capsys.readouterr().out


@pytest.mark.parametrize("name", ["railway_config_export", "cloudflare_export"])
def test_page_bound_fails(name, monkeypatch):
    module = load(name, monkeypatch)
    monkeypatch.setattr(module, "MAX_PAGES", 2)
    if name.startswith("railway"):
        number = 0
        def fetch(_):
            nonlocal number
            number += 1
            return {"edges": [{"node": {"id": str(number)}}],
                    "pageInfo": {"hasNextPage": True, "endCursor": str(number)}}
        with pytest.raises(RuntimeError, match="page bound"):
            module.collect(fetch, "projects", True)
    else:
        number = 0
        def cf(*_):
            nonlocal number
            number += 1
            return {"success": True, "result": [{"name": str(number)}],
                    "result_info": {"count": 1, "cursor": str(number)}}
        monkeypatch.setattr(module, "cf", cf)
        with pytest.raises(RuntimeError, match="page bound"):
            module.kv_keys("/keys")
