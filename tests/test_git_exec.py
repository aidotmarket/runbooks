from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from runbook_tools import git_exec
from runbook_tools.catalog.validator import _git_show
from runbook_tools.cli import _git_head


def _setup_git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    env = {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(root),
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
    }
    return subprocess.run(
        [git_exec.GIT_EXECUTABLE, "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def _repository(root: Path) -> str:
    root.mkdir()
    _setup_git(root, "init", "-q")
    (root / "payload.txt").write_text("authoritative bytes\n")
    _setup_git(root, "add", "payload.txt")
    _setup_git(
        root,
        "-c",
        "user.name=Runbook Test",
        "-c",
        "user.email=runbook@example.invalid",
        "commit",
        "-q",
        "-m",
        "fixture",
    )
    return _setup_git(root, "rev-parse", "HEAD").stdout.strip()


def test_run_git_passes_only_the_fixed_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, Any] = {}

    def capture(arguments: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        observed["arguments"] = arguments
        observed["kwargs"] = kwargs
        return subprocess.CompletedProcess(arguments, 0, stdout="ok\n", stderr="")

    monkeypatch.setenv("GIT_DIR", "/attacker/git-dir")
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", "/attacker/objects")
    monkeypatch.setenv("DYLD_INSERT_LIBRARIES", "/attacker/library")
    monkeypatch.setattr(git_exec.subprocess, "run", capture)

    result = git_exec.run_git(
        ["-C", "/trusted/repository", "rev-parse", "HEAD"],
        check=True,
        text=True,
    )

    assert result.stdout == "ok\n"
    assert observed["arguments"] == [
        "/usr/bin/git",
        "--no-replace-objects",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "protocol.allow=never",
        "-c",
        "protocol.file.allow=never",
        "-C",
        "/trusted/repository",
        "rev-parse",
        "HEAD",
    ]
    assert dict(observed["kwargs"]["env"]) == {
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_LITERAL_PATHSPECS": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PROTOCOL_FROM_USER": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "HOME": "/",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
    }
    assert "GIT_DIR" not in observed["kwargs"]["env"]
    assert "GIT_OBJECT_DIRECTORY" not in observed["kwargs"]["env"]
    assert "DYLD_INSERT_LIBRARIES" not in observed["kwargs"]["env"]
    assert observed["kwargs"]["timeout"] == 30


@pytest.mark.parametrize(
    "arguments",
    [[], ["-C"], ["status"], ["config", "user.name"]],
)
def test_run_git_rejects_commands_outside_its_read_boundary(
    arguments: list[str],
) -> None:
    with pytest.raises(ValueError):
        git_exec.run_git(arguments)


def test_authoritative_reads_ignore_ambient_git_and_loader_poison(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "trusted"
    sha = _repository(repo)
    marker = tmp_path / "ambient-git-executed"
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    fake_git.write_text(f"#!/bin/sh\ntouch {marker}\nexit 77\n")
    fake_git.chmod(0o755)
    fake_home = tmp_path / "fake-home"
    fake_home.mkdir()
    malicious_config = fake_home / "gitconfig"
    malicious_config.write_text("[core]\n\trepositoryFormatVersion = 999\n")

    poison = {
        "DYLD_INSERT_LIBRARIES": str(tmp_path / "inject.dylib"),
        "DYLD_LIBRARY_PATH": str(tmp_path),
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(tmp_path / "alternate-objects"),
        "GIT_ASKPASS": str(fake_git),
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
        "GIT_COMMON_DIR": str(tmp_path / "common-dir"),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_GLOBAL": str(malicious_config),
        "GIT_CONFIG_KEY_0": "core.repositoryFormatVersion",
        "GIT_CONFIG_NOSYSTEM": "0",
        "GIT_CONFIG_SYSTEM": str(malicious_config),
        "GIT_CONFIG_VALUE_0": "999",
        "GIT_DIR": str(tmp_path / "wrong-git-dir"),
        "GIT_EXEC_PATH": str(fake_bin),
        "GIT_GRAFT_FILE": str(tmp_path / "grafts"),
        "GIT_INDEX_FILE": str(tmp_path / "index"),
        "GIT_NAMESPACE": "attacker",
        "GIT_OBJECT_DIRECTORY": str(tmp_path / "wrong-objects"),
        "GIT_OPTIONAL_LOCKS": "1",
        "GIT_QUARANTINE_PATH": str(tmp_path / "quarantine"),
        "GIT_REPLACE_REF_BASE": "refs/attacker/replace/",
        "GIT_SHALLOW_FILE": str(tmp_path / "shallow"),
        "GIT_SSH": str(fake_git),
        "GIT_SSH_COMMAND": str(fake_git),
        "GIT_TERMINAL_PROMPT": "1",
        "GIT_WORK_TREE": str(tmp_path / "wrong-worktree"),
        "HOME": str(fake_home),
        "LD_LIBRARY_PATH": str(tmp_path),
        "LD_PRELOAD": str(tmp_path / "inject.so"),
        "PATH": str(fake_bin),
        "SSH_ASKPASS": str(fake_git),
        "SSH_AUTH_SOCK": str(tmp_path / "agent.sock"),
        "XDG_CONFIG_HOME": str(fake_home),
    }
    for name, value in poison.items():
        monkeypatch.setenv(name, value)

    assert _git_head(repo) == sha
    assert _git_show(repo, sha, "payload.txt") == b"authoritative bytes\n"
    assert not marker.exists()
    assert os.environ["PATH"] == str(fake_bin)
