"""Run read-only Git operations without ambient process authority.

The runbook corpus is authority-bearing input.  Runtime callers therefore use
an exact executable and a deliberately small environment instead of inheriting
Git, SSH, dynamic-loader, hook, or object-store controls from their parent.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Any

GIT_EXECUTABLE = "/usr/bin/git"
GIT_TIMEOUT_SECONDS = 30
_GIT_ENV = MappingProxyType(
    {
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
)
_FIXED_ARGUMENTS = (
    "--no-replace-objects",
    "-c",
    "core.hooksPath=/dev/null",
    "-c",
    "protocol.allow=never",
    "-c",
    "protocol.file.allow=never",
)
_READ_ONLY_SUBCOMMANDS = frozenset(
    {"cat-file", "ls-tree", "merge-base", "rev-parse", "show"}
)


def _subcommand(arguments: Sequence[str]) -> str:
    cursor = 0
    while cursor < len(arguments) and arguments[cursor] == "-C":
        if cursor + 1 >= len(arguments):
            raise ValueError("Git -C requires a directory")
        cursor += 2
    if cursor >= len(arguments):
        raise ValueError("Git subcommand is required")
    return arguments[cursor]


def run_git(
    arguments: Sequence[str],
    *,
    cwd: Path | str | None = None,
    check: bool = False,
    capture_output: bool = True,
    text: bool = False,
    input: bytes | str | None = None,
) -> subprocess.CompletedProcess[Any]:
    """Run one Git command through the fixed, non-interactive read boundary."""

    if any(type(argument) is not str for argument in arguments):
        raise TypeError("Git arguments must be strings")
    subcommand = _subcommand(arguments)
    if subcommand not in _READ_ONLY_SUBCOMMANDS:
        raise ValueError(f"Git subcommand {subcommand!r} is outside the read boundary")
    return subprocess.run(
        [GIT_EXECUTABLE, *_FIXED_ARGUMENTS, *arguments],
        cwd=cwd,
        env=_GIT_ENV,
        check=check,
        capture_output=capture_output,
        text=text,
        input=input,
        timeout=GIT_TIMEOUT_SECONDS,
    )
