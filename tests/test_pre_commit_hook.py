from __future__ import annotations

import os
import shutil
import signal
import stat
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
HOOK = REPO_ROOT / "scripts" / "hooks" / "pre-commit"
WARNING = (
    "WARNING: catalog regeneration failed; commit continues with advisory "
    "generated-index drift."
)
GENERATED_OUTPUTS = {"CATALOG.json", "README.md", "TOPIC-ROUTER.md"}
SIGNAL_NAMES = [
    "HUP",
    "INT",
    "QUIT",
    "ILL",
    "TRAP",
    "ABRT",
    "EMT",
    "FPE",
    "BUS",
    "SEGV",
    "SYS",
    "PIPE",
    "ALRM",
    "TERM",
    "TSTP",
    "TTIN",
    "TTOU",
    "XCPU",
    "XFSZ",
    "VTALRM",
    "PROF",
    "USR1",
    "USR2",
]
DELIVERED_SIGNALS = [
    resolved_signal
    if (resolved_signal := getattr(signal, f"SIG{signal_name}", None)) is not None
    else pytest.param(
        None,
        marks=pytest.mark.skip(
            reason=f"SIG{signal_name} is not available on {sys.platform}"
        ),
    )
    for signal_name in SIGNAL_NAMES
]
MINIMAL_GENERATOR = textwrap.dedent(
    """\
    from __future__ import annotations

    import os
    import sys
    import time
    from pathlib import Path


    if sys.argv[1:] != ["generate"]:
        raise SystemExit(2)

    ready_path = os.environ.get("CATALOG_TEST_READY")
    if ready_path:
        Path(ready_path).write_text(f"{os.getppid()}\\n", encoding="utf-8")
        release_path = Path(os.environ["CATALOG_TEST_RELEASE"])
        deadline = time.monotonic() + 10
        while not release_path.exists() and time.monotonic() < deadline:
            time.sleep(0.01)

    excluded = {"README.md", "TOPIC-ROUTER.md"}
    sources = sorted(
        path for path in Path.cwd().rglob("*.md") if path.name not in excluded
    )
    token = os.environ.get("CATALOG_TEST_TOKEN", "missing-token")
    inventory = "\\n".join(
        f"{path.as_posix()}:{path.read_text(encoding='utf-8')}" for path in sources
    )
    content = f"{token}\\n{inventory}"
    for output in ("CATALOG.json", "TOPIC-ROUTER.md", "README.md"):
        Path(output).write_text(content, encoding="utf-8")
    """
)


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    source = root / "runbooks" / "member.md"
    source.parent.mkdir()
    source.write_text("# Member\n")
    module = root / "runbook_tools" / "catalog"
    module.mkdir(parents=True)
    (root / "runbook_tools" / "__init__.py").write_text("")
    (module / "__init__.py").write_text("")
    (module / "__main__.py").write_text(MINIMAL_GENERATOR)

    environment = os.environ.copy()
    environment["CATALOG_TEST_TOKEN"] = "baseline"
    subprocess.run(
        ["python3", "-m", "runbook_tools.catalog", "generate"],
        cwd=root,
        env=environment,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Catalog Hook Test",
            "-c",
            "user.email=catalog-hook@example.test",
            "commit",
            "-q",
            "--no-verify",
            "-m",
            "baseline",
        ],
        cwd=root,
        check=True,
    )


def _fake_python3(bin_dir: Path, body: str) -> None:
    executable = bin_dir / "python3"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n" + body)
    executable.chmod(0o755)


def _run_hook(
    root: Path,
    *,
    path_prefix: Path | None = None,
    token: str = "test-run",
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["CATALOG_TEST_TOKEN"] = token
    if path_prefix is not None:
        environment["PATH"] = f"{path_prefix}:{environment['PATH']}"
    return subprocess.run(
        [str(HOOK)],
        cwd=root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def _stage(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    subprocess.run(["git", "add", "--", relative_path], cwd=root, check=True)


def _staged_paths(root: Path) -> set[str]:
    return set(
        subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )


def test_hook_is_tracked_as_executable() -> None:
    assert HOOK.stat().st_mode & stat.S_IXUSR


def test_generation_failure_warns_once_and_never_blocks(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _stage(tmp_path, "runbooks/member.md", "# Changed member\n")
    bin_dir = tmp_path / "bin"
    _fake_python3(bin_dir, "exit 23\n")

    result = _run_hook(tmp_path, path_prefix=bin_dir)

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr.splitlines() == [WARNING]


def test_staged_runbook_edit_regenerates_and_stages_all_outputs(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    _stage(tmp_path, "runbooks/member.md", "# Changed member\n")

    result = _run_hook(tmp_path, token="runbook-edit")

    assert result.returncode == 0
    assert result.stderr == ""
    assert GENERATED_OUTPUTS < _staged_paths(tmp_path)
    for output in GENERATED_OUTPUTS:
        assert (tmp_path / output).read_text().startswith("runbook-edit\n")
        assert "runbooks/member.md:# Changed member" in (tmp_path / output).read_text()


def test_root_level_markdown_edit_regenerates_all_outputs(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _stage(tmp_path, "allai-agents.md", "# Root-level discovery source\n")

    result = _run_hook(tmp_path, token="root-markdown-edit")

    assert result.returncode == 0
    assert result.stderr == ""
    assert GENERATED_OUTPUTS < _staged_paths(tmp_path)
    for output in GENERATED_OUTPUTS:
        content = (tmp_path / output).read_text()
        assert content.startswith("root-markdown-edit\n")
        assert "allai-agents.md:# Root-level discovery source" in content


def test_unrelated_commit_still_regenerates_without_error(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _stage(tmp_path, "notes.txt", "unrelated\n")

    result = _run_hook(tmp_path, token="unrelated-commit")

    assert result.returncode == 0
    assert result.stderr == ""
    assert GENERATED_OUTPUTS < _staged_paths(tmp_path)
    for output in GENERATED_OUTPUTS:
        assert (tmp_path / output).read_text().startswith("unrelated-commit\n")


@pytest.mark.parametrize(
    "delivered_signal",
    DELIVERED_SIGNALS,
    ids=SIGNAL_NAMES,
)
def test_catchable_signal_warns_and_does_not_block_commit(
    tmp_path: Path, delivered_signal: signal.Signals
) -> None:
    _init_repo(tmp_path)
    _stage(tmp_path, "notes.txt", "signal test\n")
    installed_hook = tmp_path / ".git" / "hooks" / "pre-commit"
    shutil.copy2(HOOK, installed_hook)
    ready = tmp_path / "generator-ready"
    release = tmp_path / "generator-release"
    environment = os.environ.copy()
    environment["CATALOG_TEST_READY"] = str(ready)
    environment["CATALOG_TEST_RELEASE"] = str(release)
    process = subprocess.Popen(
        [
            "git",
            "-c",
            "user.name=Catalog Hook Test",
            "-c",
            "user.email=catalog-hook@example.test",
            "commit",
            "-q",
            "-m",
            f"signal {delivered_signal.name}",
        ],
        cwd=tmp_path,
        env=environment,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 5
    while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)

    try:
        assert ready.exists(), "the real python3 generator did not start"
        hook_pid = int(ready.read_text(encoding="utf-8").strip())
        os.kill(hook_pid, delivered_signal)
        release.write_text("release\n")
        stdout, stderr = process.communicate(timeout=5)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)

    assert process.returncode == 0
    assert stdout == ""
    assert stderr.splitlines() == [WARNING]
    assert subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == "2"
