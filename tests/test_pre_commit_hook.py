from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
HOOK = REPO_ROOT / "scripts" / "hooks" / "pre-commit"
WARNING = (
    "WARNING: catalog regeneration failed; commit continues with advisory "
    "generated-index drift."
)


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    source = root / "runbooks" / "member.md"
    source.parent.mkdir()
    source.write_text("# Member\n")
    subprocess.run(["git", "add", str(source.relative_to(root))], cwd=root, check=True)


def _fake_python(bin_dir: Path, body: str) -> None:
    executable = bin_dir / "python"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n" + body)
    executable.chmod(0o755)


def _run_hook(root: Path, bin_dir: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PATH"] = f"{bin_dir}:{environment['PATH']}"
    return subprocess.run(
        [str(HOOK)],
        cwd=root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def test_hook_is_tracked_as_executable() -> None:
    assert HOOK.stat().st_mode & stat.S_IXUSR


def test_generation_failure_warns_once_and_never_blocks(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    _fake_python(bin_dir, "exit 23\n")

    result = _run_hook(tmp_path, bin_dir)

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr.splitlines() == [WARNING]


def test_success_stages_both_generated_indexes(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    _fake_python(
        bin_dir,
        "printf 'catalog\\n' > CATALOG.json\n"
        "printf 'router\\n' > TOPIC-ROUTER.md\n",
    )

    result = _run_hook(tmp_path, bin_dir)

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert result.returncode == 0
    assert result.stderr == ""
    assert staged == ["CATALOG.json", "TOPIC-ROUTER.md", "runbooks/member.md"]
