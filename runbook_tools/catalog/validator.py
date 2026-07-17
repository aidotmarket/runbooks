from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
from typing import Any, Callable

from runbook_tools.catalog.generator import (
    CATALOG_PATH,
    README_PATH,
    ROUTER_PATH,
    build_catalog,
    render_outputs,
)
from runbook_tools.catalog.model import CatalogError


CATALOG_REF_RE = re.compile(
    r"\Agit:aidotmarket/runbooks@(?P<sha>[0-9a-f]{40}):CATALOG\.json\Z"
)
HISTORICAL_BEGIN = "<!-- catalog:historical -->"
HISTORICAL_END = "<!-- /catalog:historical -->"


@dataclass(frozen=True, slots=True)
class ValidationReport:
    catalog_ref: str
    catalog_sha: str
    catalog_path: str
    catalog_digest: str
    checked_entry_count: int
    checked_section_count: int
    status: str = "pass"

    def as_dict(self) -> dict[str, Any]:
        return {
            "catalog_digest": self.catalog_digest,
            "catalog_path": self.catalog_path,
            "catalog_ref": self.catalog_ref,
            "catalog_sha": self.catalog_sha,
            "checked_entry_count": self.checked_entry_count,
            "checked_section_count": self.checked_section_count,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class ValidatedCatalog:
    catalog: dict[str, Any]
    report: ValidationReport


def parse_catalog_ref(catalog_ref: str) -> str:
    """Validate the exact Boot Kernel pin grammar without doing I/O."""
    match = CATALOG_REF_RE.fullmatch(catalog_ref)
    if match is None:
        raise CatalogError(
            "catalog ref must match "
            "git:aidotmarket/runbooks@<40-lowercase-hex>:CATALOG.json"
        )
    return match.group("sha")


def validate_catalog_ref(repo_root: Path, catalog_ref: str) -> ValidationReport:
    return load_validated_catalog(repo_root, catalog_ref).report


def load_validated_catalog(repo_root: Path, catalog_ref: str) -> ValidatedCatalog:
    sha = parse_catalog_ref(catalog_ref)
    root = repo_root.resolve()
    catalog_bytes = _git_show(root, sha, CATALOG_PATH)
    try:
        catalog = json.loads(catalog_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CatalogError(f"{CATALOG_PATH} at {sha} is not valid JSON: {exc}") from exc
    if not isinstance(catalog, dict):
        raise CatalogError(f"{CATALOG_PATH} at {sha} must contain a JSON object")

    tree_paths = _git_tree_paths(root, sha)
    errors, checked_sections = _validate_pinned_entries(
        catalog,
        tree_paths,
        lambda path: _git_show(root, sha, path),
    )

    with tempfile.TemporaryDirectory(prefix="runbook-catalog-validate-") as temporary:
        snapshot = Path(temporary)
        materialized = _catalog_snapshot_paths(tree_paths)
        for relative in materialized:
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(_git_show(root, sha, relative))
        try:
            expected_outputs = render_outputs(snapshot)
        except (CatalogError, OSError) as exc:
            errors.append(f"ACTIVE frontmatter at {sha} is invalid: {exc}")
        else:
            for relative, expected in expected_outputs.items():
                if relative not in tree_paths:
                    errors.append(f"{relative} is missing at pinned SHA {sha}")
                    continue
                actual = _git_show(root, sha, relative)
                if actual != expected:
                    errors.append(
                        f"{relative} differs from ACTIVE frontmatter/generated links at pinned SHA {sha}"
                    )

    if errors:
        raise CatalogError("catalog validation failed: " + "; ".join(dict.fromkeys(errors)))

    entries = catalog.get("entries")
    assert isinstance(entries, list)
    report = ValidationReport(
        catalog_ref=catalog_ref,
        catalog_sha=sha,
        catalog_path=CATALOG_PATH,
        catalog_digest=hashlib.sha256(catalog_bytes).hexdigest(),
        checked_entry_count=len(entries),
        checked_section_count=checked_sections,
    )
    return ValidatedCatalog(catalog=catalog, report=report)


def active_catalog_paths(repo_root: Path) -> list[Path]:
    """Load default lint/harness targets from the working catalog, failing closed."""
    root = repo_root.resolve()
    catalog_path = root / CATALOG_PATH
    if not catalog_path.is_file():
        raise CatalogError(f"missing required {CATALOG_PATH}")
    try:
        catalog = json.loads(catalog_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"invalid {CATALOG_PATH}: {exc}") from exc
    if not isinstance(catalog, dict):
        raise CatalogError(f"invalid {CATALOG_PATH}: root must be an object")

    expected, _ = build_catalog(root)
    if catalog != expected:
        raise CatalogError(f"invalid {CATALOG_PATH}: content differs from ACTIVE frontmatter")
    entries = catalog.get("entries")
    if not isinstance(entries, list):
        raise CatalogError(f"invalid {CATALOG_PATH}: entries must be an array")

    selected: list[Path] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("status") != "ACTIVE":
            raise CatalogError(f"invalid {CATALOG_PATH}: every entry must be ACTIVE")
        relative = entry.get("path")
        if not isinstance(relative, str) or not _bounded_active_path(relative):
            raise CatalogError(f"invalid ACTIVE path: {relative!r}")
        path = root / relative
        if not path.is_file():
            raise CatalogError(f"ACTIVE path is missing: {relative}")
        selected.append(path)
    return selected


def _validate_pinned_entries(
    catalog: dict[str, Any],
    tree_paths: set[str],
    loader: Callable[[str], bytes],
) -> tuple[list[str], int]:
    errors: list[str] = []
    if catalog.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    entries = catalog.get("entries")
    indexes = catalog.get("indexes")
    if not isinstance(entries, list):
        return errors + ["entries must be an array"], 0
    if not isinstance(indexes, dict):
        errors.append("indexes must be an object")

    seen_ids: set[str] = set()
    seen_identities: set[str] = set()
    seen_basenames: set[str] = set()
    checked_sections = 0
    for position, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entries[{position}] must be an object")
            continue
        runbook_id = entry.get("runbook_id")
        path = entry.get("path")
        if entry.get("status") != "ACTIVE":
            errors.append(f"entries[{position}] is not ACTIVE")
        if not isinstance(runbook_id, str) or not runbook_id:
            errors.append(f"entries[{position}] has invalid runbook_id")
        elif runbook_id in seen_ids:
            errors.append(f"duplicate runbook_id {runbook_id!r}")
        else:
            seen_ids.add(runbook_id)
        identities = [runbook_id] if isinstance(runbook_id, str) else []
        aliases = entry.get("aliases")
        if not isinstance(aliases, list) or not all(isinstance(alias, str) for alias in aliases):
            errors.append(f"{runbook_id or position}: aliases must be an array of strings")
            aliases = []
        identities.extend(aliases)
        for identity in identities:
            if identity in seen_identities:
                errors.append(f"duplicate runbook id/alias {identity!r}")
            seen_identities.add(identity)

        if not isinstance(path, str) or not _bounded_active_path(path):
            errors.append(f"{runbook_id or position}: ACTIVE path is outside bounded roots: {path!r}")
            continue
        basename = PurePosixPath(path).name
        if basename in seen_basenames:
            errors.append(f"duplicate ACTIVE basename {basename!r}")
        seen_basenames.add(basename)
        if path not in tree_paths:
            errors.append(f"{runbook_id or position}: ACTIVE path is missing at pinned SHA: {path}")
            continue
        try:
            markdown = loader(path).decode()
        except (CatalogError, UnicodeDecodeError) as exc:
            errors.append(str(exc))
            continue

        try:
            active_text = _active_text(markdown, path)
        except CatalogError as exc:
            errors.append(str(exc))
            active_text = ""
        errors.extend(_stale_claim_errors(active_text, path))
        headings = _headings(markdown)
        for collection in ("authoritative_for", "error_signatures"):
            rows = entry.get(collection)
            if not isinstance(rows, list):
                errors.append(f"{runbook_id or position}: {collection} must be an array")
                continue
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get("section"), str):
                    errors.append(f"{runbook_id or position}: malformed {collection} row")
                    continue
                checked_sections += 1
                section = row["section"]
                if section not in headings:
                    errors.append(f"{path}: dangling section {section!r}")
    return errors, checked_sections


def _bounded_active_path(path: str) -> bool:
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        return False
    if "archive" in pure.parts:
        return False
    if len(pure.parts) == 1:
        return pure.suffix == ".md" and pure.name not in {README_PATH, ROUTER_PATH}
    return pure.parts[0] == "runbooks" and pure.suffix == ".md"


def _active_text(markdown: str, path: str) -> str:
    active_lines: list[str] = []
    inside = False
    for line_number, line in enumerate(markdown.splitlines(keepends=True), start=1):
        marker = line.strip()
        if marker == HISTORICAL_BEGIN:
            if inside:
                raise CatalogError(f"{path}:{line_number}: nested historical marker")
            inside = True
            active_lines.append("\n")
            continue
        if marker == HISTORICAL_END:
            if not inside:
                raise CatalogError(f"{path}:{line_number}: unmatched historical end marker")
            inside = False
            active_lines.append("\n")
            continue
        active_lines.append("\n" if inside else line)
    if inside:
        raise CatalogError(f"{path}: unclosed historical marker")
    return "".join(active_lines)


def _stale_claim_errors(active_text: str, path: str) -> list[str]:
    patterns = (
        ("primary/worker instance-slot claim", re.compile(r"\b(?:primary|worker)(?:\s+instance)?\s+slot\b|\bprimary\s*/\s*worker\b", re.I)),
        ("Vulcan/Mars assignment or close-order claim", re.compile(r"\b(?:Vulcan|Mars)\b[^\n]{0,100}\b(?:assign(?:s|ed|ment)?|approv\w*|clos\w*\s+(?:before|after))\b[^\n]{0,100}\b(?:Vulcan|Mars)\b", re.I)),
        ("XAI current Council-voter claim", re.compile(r"\bXAI\s+is\s+(?:an?\s+)?(?:active|current)\s+(?:Council\s+)?voter\b|\bactive\s+(?:Council\s+)?voters?\s*:[^\n]*\bXAI\b", re.I)),
    )
    errors: list[str] = []
    for label, pattern in patterns:
        match = pattern.search(active_text)
        if match is not None:
            line = active_text.count("\n", 0, match.start()) + 1
            errors.append(f"{path}:{line}: stale active claim ({label})")
    return errors


def _headings(markdown: str) -> set[str]:
    headings: set[str] = set()
    fence: str | None = None
    for line in markdown.splitlines():
        fence_match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence_match is not None:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker[0]
            elif marker[0] == fence:
                fence = None
            continue
        if fence is not None:
            continue
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if match is not None:
            headings.add(match.group(1).strip().rstrip("#").rstrip())
    return headings


def _catalog_snapshot_paths(tree_paths: set[str]) -> list[str]:
    selected = [
        path
        for path in tree_paths
        if path in {CATALOG_PATH, ROUTER_PATH, README_PATH}
        or ("/" not in path and path.endswith(".md"))
        or (path.startswith("runbooks/") and path.endswith(".md"))
    ]
    return sorted(selected)


def _git_tree_paths(repo_root: Path, sha: str) -> set[str]:
    completed = _run_git(repo_root, ["ls-tree", "-r", "--name-only", sha])
    return {line for line in completed.stdout.splitlines() if line}


def _git_show(repo_root: Path, sha: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{sha}:{path}"],
        cwd=repo_root,
        capture_output=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.decode(errors="replace").strip()
        raise CatalogError(f"git show {sha}:{path} failed: {message}")
    return completed.stdout


def _run_git(repo_root: Path, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise CatalogError(f"git {' '.join(arguments)} failed: {completed.stderr.strip()}")
    return completed
