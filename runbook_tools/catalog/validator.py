from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

import runbook_tools.catalog.generator as catalog_generator
from runbook_tools.catalog.generator import (
    CATALOG_PATH,
    README_PATH,
    ROUTER_PATH,
    build_catalog,
    is_admitted_source_tree_path,
    is_source_relative_path,
    render_outputs,
)
from runbook_tools.catalog.model import CatalogError, canonical_active_path
from runbook_tools.catalog.sections import (
    declared_section_errors,
    parse_markdown_document,
)
from runbook_tools.lint.forms import (
    extract_e_entries,
    extract_f_rows,
    extract_g_entries,
    extract_i_payload,
)
from runbook_tools.parser.sections import extract_sections

CATALOG_REF_RE = re.compile(
    r"\Agit:aidotmarket/runbooks@(?P<sha>[0-9a-f]{40}):CATALOG\.json\Z"
)
MAX_PINNED_CATALOG_BYTES = 4_000_000
MAX_PINNED_MARKDOWN_BYTES = 4_000_000
MAX_PINNED_SCHEMA_BYTES = 2_000_000
MAX_PINNED_SNAPSHOT_BYTES = 16_000_000
CROSS_FILE_REF_RE = re.compile(
    r"^(?P<runbook_id>[a-z0-9]+(?:-[a-z0-9]+)*):"
    r"(?P<target>§?(?:[EFGI]-\d{2,})|§[A-K](?:\.\d+)?)$"
)
SUBSECTION_REF_RE = re.compile(r"^§(?P<section>[A-K])\.(?P<number>\d+)(?:\s|$)")


@dataclass(frozen=True, slots=True)
class ValidationReport:
    catalog_ref: str
    catalog_sha: str
    catalog_path: str
    catalog_digest: str
    checked_entry_count: int
    checked_section_count: int
    status: str = "integrity_pass_unverified"
    integrity_only: bool = True
    semantic_verification: bool = False
    authority_admission: bool = False
    action_authority_eligible: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_authority_eligible": self.action_authority_eligible,
            "authority_admission": self.authority_admission,
            "catalog_digest": self.catalog_digest,
            "catalog_path": self.catalog_path,
            "catalog_ref": self.catalog_ref,
            "catalog_sha": self.catalog_sha,
            "checked_entry_count": self.checked_entry_count,
            "checked_section_count": self.checked_section_count,
            "integrity_only": self.integrity_only,
            "semantic_verification": self.semantic_verification,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class ValidatedCatalog:
    catalog: dict[str, Any]
    report: ValidationReport


@dataclass(frozen=True, slots=True)
class _PinnedReferenceDocument:
    path: str
    row_targets: frozenset[str]
    section_targets: frozenset[str]
    cross_file_refs: tuple[tuple[str, str], ...]


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
    tree_paths = _git_tree_paths(root, sha)
    if CATALOG_PATH not in tree_paths:
        raise CatalogError(f"{CATALOG_PATH} is missing at pinned SHA {sha}")
    materialized = _catalog_snapshot_paths(tree_paths)
    _preflight_pinned_blobs(root, sha, materialized)

    catalog_bytes = _git_show(root, sha, CATALOG_PATH)
    if len(catalog_bytes) > MAX_PINNED_CATALOG_BYTES:
        raise CatalogError(
            f"{CATALOG_PATH} at {sha} exceeds the "
            f"{MAX_PINNED_CATALOG_BYTES}-byte limit"
        )
    try:
        catalog = json.loads(catalog_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CatalogError(f"{CATALOG_PATH} at {sha} is not valid JSON: {exc}") from exc
    if not isinstance(catalog, dict):
        raise CatalogError(f"{CATALOG_PATH} at {sha} must contain a JSON object")

    commit_utc_datetime = _git_commit_utc_datetime(root, sha)
    commit_utc_date = commit_utc_datetime.date()
    errors, checked_sections = _validate_pinned_entries(
        catalog,
        tree_paths,
        lambda path: _git_show(root, sha, path),
    )
    entries = catalog.get("entries")
    projection = catalog_generator._reviewed_legacy_projection(root, revision=sha)
    if projection is not None and isinstance(entries, list):
        try:
            catalog_generator._enforce_reviewed_legacy_projection(
                [entry for entry in entries if isinstance(entry, dict)],
                projection,
            )
        except CatalogError as exc:
            errors.append(str(exc))

    with tempfile.TemporaryDirectory(prefix="runbook-catalog-validate-") as temporary:
        snapshot = Path(temporary)
        for relative in materialized:
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(_git_show(root, sha, relative))
        try:
            expected_outputs = render_outputs(
                snapshot,
                current_utc_date=commit_utc_date,
                current_utc_datetime=commit_utc_datetime,
            )
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
        runbook_id = entry.get("runbook_id")
        if (
            not isinstance(relative, str)
            or not isinstance(runbook_id, str)
            or relative != canonical_active_path(runbook_id)
        ):
            expected = (
                canonical_active_path(runbook_id)
                if isinstance(runbook_id, str)
                else "runbooks/<runbook_id>.md"
            )
            raise CatalogError(
                f"invalid ACTIVE path {relative!r}: must be canonical {expected!r}"
            )
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
    if catalog.get("schema_version") != catalog_generator.SCHEMA_VERSION:
        errors.append(
            f"schema_version must be {catalog_generator.SCHEMA_VERSION}"
        )
    expected_catalog_labels: tuple[tuple[str, object], ...] = (
        ("status", "integrity_pass_unverified"),
        ("integrity_only", True),
        ("semantic_verification", False),
        ("authority_admission", False),
        ("action_authority_eligible", False),
    )
    for field, expected in expected_catalog_labels:
        if type(catalog.get(field)) is not type(expected) or catalog.get(field) != expected:
            errors.append(f"catalog {field} must be {expected!r}")
    entries = catalog.get("entries")
    indexes = catalog.get("indexes")
    if not isinstance(entries, list):
        return errors + ["entries must be an array"], 0
    if not isinstance(indexes, dict):
        errors.append("indexes must be an object")

    seen_ids: set[str] = set()
    seen_identities: set[str] = set()
    seen_basenames: set[str] = set()
    reference_documents: dict[str, _PinnedReferenceDocument] = {}
    checked_sections = 0
    for position, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entries[{position}] must be an object")
            continue
        runbook_id = entry.get("runbook_id")
        path = entry.get("path")
        if entry.get("status") != "ACTIVE":
            errors.append(f"entries[{position}] is not ACTIVE")
        expected_entry_labels: tuple[tuple[str, object], ...] = (
            ("integrity_status", "integrity_pass_unverified"),
            ("integrity_only", True),
            ("semantic_verification", False),
            ("authority_admission", False),
            ("action_authority_eligible", False),
        )
        for field, expected in expected_entry_labels:
            if type(entry.get(field)) is not type(expected) or entry.get(field) != expected:
                errors.append(
                    f"{runbook_id or position}: {field} must be {expected!r}"
                )
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

        if (
            not isinstance(path, str)
            or not isinstance(runbook_id, str)
            or path != canonical_active_path(runbook_id)
        ):
            expected = (
                canonical_active_path(runbook_id)
                if isinstance(runbook_id, str)
                else "runbooks/<runbook_id>.md"
            )
            errors.append(
                f"{runbook_id or position}: ACTIVE path {path!r} must be "
                f"canonical {expected!r}"
            )
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
        declared_rows: list[tuple[str, str | None]] = []
        authority_rows: list[tuple[str, str | None]] = []
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
                section_id = row.get("section_id")
                if section_id is not None and not isinstance(section_id, str):
                    errors.append(
                        f"{path}: section_id {section_id!r} must be a string"
                    )
                    continue
                declared_rows.append((section, section_id))
                if collection == "authoritative_for":
                    authority_rows.append((section, section_id))
        errors.extend(
            declared_section_errors(
                markdown,
                path,
                declared_rows,
                authoritative_rows=authority_rows,
            )
        )
        if isinstance(runbook_id, str) and runbook_id not in reference_documents:
            reference_documents[runbook_id] = _pinned_reference_document(
                markdown,
                path,
            )
    errors.extend(_cross_file_reference_errors(reference_documents))
    return errors, checked_sections


def _pinned_reference_document(
    markdown: str,
    path: str,
) -> _PinnedReferenceDocument:
    """Project resolvable §I targets and refs from one immutable document.

    ``extract_sections`` is based on the rendered ACTIVE projection, so fenced,
    commented, and explicitly historical examples cannot supply a target.
    """

    sections = extract_sections(markdown)
    by_letter = {section.letter: section for section in sections}
    row_targets: set[str] = set()
    section_e = by_letter.get("E")
    if section_e is not None:
        row_targets.update(
            str(row["id"])
            for row in extract_e_entries(section_e)
            if isinstance(row, dict) and isinstance(row.get("id"), str)
        )
    section_f = by_letter.get("F")
    if section_f is not None:
        row_targets.update(
            str(row["ID"])
            for row in extract_f_rows(section_f)
            if isinstance(row.get("ID"), str)
        )
    section_g = by_letter.get("G")
    if section_g is not None:
        row_targets.update(
            str(row["id"])
            for row in extract_g_entries(section_g)
            if isinstance(row, dict) and isinstance(row.get("id"), str)
        )

    # §A is the catalog-member frontmatter. §B–§K are rendered H2 sections;
    # numeric child refs such as §H.2 must themselves be rendered headings.
    section_targets = {"§A"}
    section_targets.update(f"§{letter}" for letter in by_letter)
    for candidate in parse_markdown_document(markdown).sections:
        match = SUBSECTION_REF_RE.match(candidate.heading)
        if match is not None:
            section_targets.add(
                f"§{match.group('section')}.{match.group('number')}"
            )

    cross_file_refs: list[tuple[str, str]] = []
    section_i = by_letter.get("I")
    payload = extract_i_payload(section_i) if section_i is not None else None
    scenarios = payload.get("scenario_set") if isinstance(payload, dict) else None
    if isinstance(scenarios, list):
        for scenario in scenarios:
            if not isinstance(scenario, dict):
                continue
            scenario_id = scenario.get("id")
            if isinstance(scenario_id, str):
                row_targets.add(scenario_id)
            refs = scenario.get("refs")
            if not isinstance(refs, list):
                continue
            for raw_ref in refs:
                if isinstance(raw_ref, str) and CROSS_FILE_REF_RE.fullmatch(
                    raw_ref.strip()
                ):
                    cross_file_refs.append(
                        (
                            scenario_id
                            if isinstance(scenario_id, str)
                            else "<unknown>",
                            raw_ref.strip(),
                        )
                    )

    return _PinnedReferenceDocument(
        path=path,
        row_targets=frozenset(row_targets),
        section_targets=frozenset(section_targets),
        cross_file_refs=tuple(cross_file_refs),
    )


def _cross_file_reference_errors(
    documents: dict[str, _PinnedReferenceDocument],
) -> list[str]:
    errors: list[str] = []
    for source in documents.values():
        for scenario_id, ref in source.cross_file_refs:
            match = CROSS_FILE_REF_RE.fullmatch(ref)
            assert match is not None
            target_runbook_id = match.group("runbook_id")
            target_ref = match.group("target")
            target = documents.get(target_runbook_id)
            if target is None:
                errors.append(
                    f'{source.path}: §I scenario {scenario_id} ref "{ref}" '
                    f"does not resolve: runbook_id {target_runbook_id!r} is "
                    "absent from the pinned catalog"
                )
                continue
            normalized_target = target_ref.removeprefix("§")
            resolves = (
                normalized_target in target.row_targets
                if re.fullmatch(r"[EFGI]-\d{2,}", normalized_target)
                else target_ref in target.section_targets
            )
            if not resolves:
                errors.append(
                    f'{source.path}: §I scenario {scenario_id} ref "{ref}" '
                    f"does not resolve in pinned runbook {target_runbook_id!r}"
                )
    return errors


def _active_text(markdown: str, path: str) -> str:
    document = parse_markdown_document(markdown)
    if document.structure_errors:
        raise CatalogError(
            "; ".join(f"{path}:{error}" for error in document.structure_errors)
        )
    return document.active_text


def _stale_claim_errors(active_text: str, path: str) -> list[str]:
    soft_gap = r"(?:(?:[^\n])|\n(?![ \t]*\n)){0,160}"
    patterns = (
        (
            "primary/worker instance-slot claim",
            re.compile(
                r"(?:"
                rf"\bprimary(?:[ \t]+instance)?[ \t]+slot\b{soft_gap}"
                r"\bworker(?:\s+instance)?\s+slot\b"
                rf"|\bworker(?:[ \t]+instance)?[ \t]+slot\b{soft_gap}"
                r"\bprimary(?:\s+instance)?\s+slot\b"
                r"|\bprimary\s*/\s*worker(?:\s+(?:instance[- ]slots?|slots?|model))?\b"
                r")",
                re.IGNORECASE,
            ),
            True,
        ),
        (
            "Vulcan/Mars hierarchy or close-order claim",
            re.compile(
                rf"\b(?:Vulcan|Mars)\b{soft_gap}"
                r"\b(?:assign(?:s|ed|ment)?|approv\w*|directs?|reports?[ \t]+to|"
                r"controls?|owns?|superior|subordinate|primary|worker|lead|manager|"
                r"must[ \t]+obtain[ \t]+approval|clos\w*[ \t]+(?:before|after))\b"
                rf"{soft_gap}\b(?:Vulcan|Mars)\b",
                re.IGNORECASE,
            ),
            True,
        ),
        (
            "XAI current Council-voter claim",
            re.compile(
                r"\bXAI\s+is\s+(?:an?\s+)?(?:active|current)\s+"
                r"(?:Council\s+)?voter\b|\bactive\s+(?:Council\s+)?voters?\s*:"
                r"[^\n]*\bXAI\b",
                re.IGNORECASE,
            ),
            False,
        ),
    )
    explicit_retirement_context = re.compile(
        r"\b(?:retired|superseded|obsolete|deprecated)\b"
        r"|\bno longer\s+(?:active|current|used)\b",
        re.IGNORECASE,
    )
    affirmative_relationship = re.compile(
        r"\b(?:active|current|directs?|reports?|assign\w*|approv\w*|"
        r"controls?|owns?|superior|subordinate|lead|manager|remain\w*|required)\b"
        r"|\bin[ 	]+force\b"
        r"|\b(?:must|should)\s+(?!not\b|never\b)",
        re.IGNORECASE,
    )
    errors: list[str] = []
    for label, pattern, allow_historical_context in patterns:
        for match in pattern.finditer(active_text):
            claim_context = _sentence_for_match(
                active_text,
                match.start(),
                match.end(),
            )
            if (
                allow_historical_context
                and explicit_retirement_context.search(claim_context)
                and not _has_affirmative_relationship(
                    claim_context,
                    affirmative_relationship,
                )
            ):
                continue
            line = active_text.count("\n", 0, match.start()) + 1
            errors.append(f"{path}:{line}: stale active claim ({label})")
            break
    return errors


def _headings(markdown: str) -> set[str]:
    return {section.heading for section in parse_markdown_document(markdown).sections}


def _catalog_snapshot_paths(tree_paths: set[str]) -> list[str]:
    selected = [path for path in tree_paths if _is_catalog_snapshot_path(path)]
    return sorted(selected)


def _is_catalog_snapshot_path(path: str) -> bool:
    return (
        path in {CATALOG_PATH, ROUTER_PATH, README_PATH}
        or (path.startswith("schemas/") and path.endswith(".json"))
        or is_source_relative_path(path)
    )


def _preflight_pinned_blobs(
    repo_root: Path,
    sha: str,
    paths: list[str] | tuple[str, ...],
) -> None:
    """Bound immutable snapshot blobs before any content is materialized."""

    total = 0
    for path in sorted(set(paths)):
        size = _git_blob_size(repo_root, sha, path)
        limit, kind = _pinned_blob_limit(path)
        if size > limit:
            raise CatalogError(
                f"{path} at {sha} exceeds the {limit}-byte pinned {kind} limit"
            )
        total += size
        if total > MAX_PINNED_SNAPSHOT_BYTES:
            raise CatalogError(
                f"pinned catalog snapshot at {sha} exceeds the "
                f"{MAX_PINNED_SNAPSHOT_BYTES}-byte aggregate limit"
            )


def _pinned_blob_limit(path: str) -> tuple[int, str]:
    if path == CATALOG_PATH:
        return MAX_PINNED_CATALOG_BYTES, "catalog"
    if path.startswith("schemas/") and path.endswith(".json"):
        return MAX_PINNED_SCHEMA_BYTES, "schema"
    if PurePosixPath(path).suffix.lower() == ".md":
        return MAX_PINNED_MARKDOWN_BYTES, "Markdown"
    raise CatalogError(f"unsupported pinned snapshot path: {path}")


def _paragraph_for_match(text: str, start: int, end: int) -> str:
    paragraph_break = re.compile(r"\n[ \t]*\n")
    paragraph_start = 0
    for match in paragraph_break.finditer(text, 0, start):
        paragraph_start = match.end()
    following = paragraph_break.search(text, end)
    paragraph_end = following.start() if following is not None else len(text)
    return text[paragraph_start:paragraph_end]


def _sentence_for_match(text: str, start: int, end: int) -> str:
    """Return the sentence containing a claim, bounded within its paragraph.

    Retirement language elsewhere in a paragraph must not excuse a current
    stale claim. Soft line breaks remain part of one sentence so split-line
    claims continue to be detected.
    """

    paragraph_break = re.compile(r"\n[ \t]*\n")
    paragraph_start = 0
    for boundary in paragraph_break.finditer(text, 0, start):
        paragraph_start = boundary.end()
    following_paragraph = paragraph_break.search(text, end)
    paragraph_end = (
        following_paragraph.start()
        if following_paragraph is not None
        else len(text)
    )

    sentence_end = re.compile(r"[.!?]+(?:[\"')\]]+)?(?=\s|$)")
    sentence_start = paragraph_start
    for boundary in sentence_end.finditer(text, paragraph_start, start):
        sentence_start = boundary.end()
    following_sentence = sentence_end.search(text, end, paragraph_end)
    scope_end = (
        following_sentence.end()
        if following_sentence is not None
        else paragraph_end
    )
    return text[sentence_start:scope_end]


def _has_affirmative_relationship(
    paragraph: str,
    relationship_pattern: re.Pattern[str],
) -> bool:
    # A retirement warning such as "must not be used" is safety guidance, not
    # a current hierarchy claim. Remove only its explicitly prohibitive clause;
    # an affirmative clause after "but/however/yet" remains visible and fails.
    without_prohibitions = re.sub(
        r"\b(?:must|should)\s+(?:not|never)\b"
        r"(?:(?![.;]|\b(?:but|however|yet)\b).)*",
        " ",
        paragraph,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return relationship_pattern.search(without_prohibitions) is not None


def _git_commit_utc_datetime(repo_root: Path, sha: str) -> datetime:
    completed = _run_git(repo_root, ["show", "-s", "--format=%ct", sha])
    try:
        timestamp = int(completed.stdout.strip())
    except ValueError as exc:
        raise CatalogError(f"cannot determine committer UTC date for {sha}") from exc
    return datetime.fromtimestamp(timestamp, tz=UTC)


def _git_tree_paths(repo_root: Path, sha: str) -> set[str]:
    completed = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "ls-tree",
            "-r",
            "-z",
            "--full-tree",
            sha,
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode(errors="replace").strip()
        raise CatalogError(f"git ls-tree failed for {sha}: {detail}")
    result: set[str] = set()
    try:
        for record in completed.stdout.split(b"\0"):
            if not record:
                continue
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, _oid = metadata.decode("ascii").split(" ", 2)
            path = raw_path.decode("utf-8")
            if (
                _is_catalog_snapshot_path(path)
                or is_admitted_source_tree_path(path)
            ) and (
                object_type != "blob" or mode not in {"100644", "100755"}
            ):
                raise CatalogError(
                    f"pinned snapshot path {path!r} is {object_type} mode {mode}, "
                    "not a regular file"
                )
            result.add(path)
    except CatalogError:
        raise
    except (UnicodeError, ValueError) as exc:
        raise CatalogError(f"Git tree for {sha} cannot be parsed safely: {exc}") from exc
    return result


def _git_blob_size(repo_root: Path, sha: str, path: str) -> int:
    completed = _run_git(repo_root, ["cat-file", "-s", f"{sha}:{path}"])
    try:
        size = int(completed.stdout.strip())
    except ValueError as exc:
        raise CatalogError(f"cannot determine blob size for {sha}:{path}") from exc
    if size < 0:
        raise CatalogError(f"invalid negative blob size for {sha}:{path}")
    return size


def _git_show(repo_root: Path, sha: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "--no-replace-objects", "show", f"{sha}:{path}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.decode(errors="replace").strip()
        raise CatalogError(f"git show {sha}:{path} failed: {message}")
    return completed.stdout


def _run_git(repo_root: Path, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", "--no-replace-objects", *arguments],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise CatalogError(f"git {' '.join(arguments)} failed: {completed.stderr.strip()}")
    return completed
