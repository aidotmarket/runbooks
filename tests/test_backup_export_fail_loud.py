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
        payloads.append(json.loads(Path(argv[3]).read_text()))
        return SimpleNamespace(returncode=returncode, stderr=SENTINEL)

    monkeypatch.setattr(module.subprocess, "run", run)
    return payloads


def railway_responses(deployments=None):
    return [
        {"data": {"me": {"workspaces": [{"projects": {"edges": [{"node": {"id": "p", "name": "project"}}],
                                                   "pageInfo": {"hasNextPage": False}}}]}}},
        {"data": {"project": {"name": "project", "environments": {"edges": [{"node": {"id": "e", "name": "production"}}],
                                                                  "pageInfo": {"hasNextPage": False}},
                              "services": {"edges": [{"node": {"id": "s", "name": "service"}}],
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
    (0, {"errors": [{"message": SENTINEL}], "data": {"me": None}}),
    (0, {"data": {"me": {"workspaces": [None]}}}),
    (0, {"data": {"me": {"workspaces": [{"projects": {"edges": []}}]}}}),
    (0, {"data": {"me": {"workspaces": [{"projects": {"edges": [], "pageInfo": {"hasNextPage": True}}}]}}}),
    (1, {"errors": [{"message": SENTINEL}], "data": {"project": None}}),
    (1, {"data": {"project": {"environments": {"edges": []}, "services": None}}}),
    (2, {"errors": [{"message": SENTINEL}], "data": {"deployments": {"edges": []}}}),
    (2, {"data": {"deployments": {"edges": [{"node": {}}], "pageInfo": {"hasNextPage": True}}}}),
    (3, {"data": {"variables": None}}),
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
        {"success": True, "result": [{"id": "z", "name": "zone"}], "result_info": {"total_pages": 1, "total_count": 1}},
        {"success": True, "result": [{"id": "r", "content": SENTINEL}], "result_info": {"page": 1, "total_pages": 1, "total_count": 1}},
        {"success": True, "result": [{"id": "setting", "value": SENTINEL}]},
        {"success": True, "result": [{"id": "n", "title": "namespace"}], "result_info": {"total_pages": 1, "total_count": 1}},
        {"success": True, "result": [{"name": "key"}], "result_info": {"total_pages": 1, "total_count": 1}},
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
