"""Validate the exhaustive source-corpus adjudication ledger.

``CORPUS-MANIFEST.yaml`` is an inventory and migration ledger.  It is never an
authority source: only a conformant ACTIVE runbook can enter the catalog.  This
module deliberately checks the ledger independently of catalog generation so a
missing, renamed, or reclassified source document cannot disappear silently.
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from runbook_tools.catalog.canonical_content import (
    canonical_string_bytes,
    requirement_mapping_digest,
)
from runbook_tools.catalog.generator import (
    _frontmatter,
    is_admitted_source_tree_path,
    is_source_relative_path,
    source_paths,
)
from runbook_tools.catalog.limits import PRODUCTION_LIMITS
from runbook_tools.catalog.model import CatalogError
from runbook_tools.parser.sections import (
    extract_fenced_yaml_block,
    extract_sections,
    extract_yaml_frontmatter,
)
from runbook_tools.strict_yaml import strict_yaml_load

MANIFEST_NAME = "CORPUS-MANIFEST.yaml"
MANIFEST_VERSION = 2
MAX_PINNED_MANIFEST_BYTES = PRODUCTION_LIMITS.manifest_bytes
MAX_PINNED_CORPUS_BLOB_BYTES = PRODUCTION_LIMITS.document_bytes
MAX_PINNED_CORPUS_BYTES = PRODUCTION_LIMITS.aggregate_document_bytes
MAX_PINNED_PATH_BYTES = PRODUCTION_LIMITS.path_utf8_bytes
MAX_PINNED_BATCH_BYTES = PRODUCTION_LIMITS.batch_id_j
MAX_PINNED_BATCH_WIRE_BYTES = PRODUCTION_LIMITS.batch_id_j
MAX_PINNED_VERIFY_AGAINST_ITEMS = PRODUCTION_LIMITS.verify_against_items
MAX_PINNED_VERIFY_AGAINST_ITEM_BYTES = PRODUCTION_LIMITS.verify_against_item_j
MAX_PINNED_VERIFY_AGAINST_BYTES = PRODUCTION_LIMITS.verify_against_aggregate_j
MAX_PINNED_VERIFY_AGAINST_ITEM_WIRE_BYTES = (
    PRODUCTION_LIMITS.verify_against_item_j
)
MAX_PINNED_VERIFY_AGAINST_WIRE_BYTES = (
    PRODUCTION_LIMITS.verify_against_aggregate_j
)
PURPOSE = (
    "Exhaustive adjudication ledger for the operational Markdown corpus; only "
    "conformant ACTIVE runbooks grant catalog authority."
)
SOURCE_SELECTOR = "runbook_tools.catalog.generator.source_paths"
HEX_OID_RE = re.compile(r"\A[0-9a-f]{40}\Z")
BATCH_RE = re.compile(r"\A[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")
PORTABLE_PATH_RE = re.compile(r"\A[A-Za-z0-9._/-]+\Z")
RECEIPT_ID_RE = re.compile(r"\Arunbook-promotion:[a-zA-Z0-9._:-]{1,200}\Z")
PROMOTION_EVIDENCE_SCHEMA = "runbook_promotion_evidence.schema.json"
PROMOTION_RECEIPT_SCHEMA = "runbook_promotion_receipt.schema.json"
PROMOTION_EVIDENCE_INFO = "promotion-evidence"
PROMOTION_EVIDENCE_FENCE_RE = re.compile(
    r"(?ms)^```yaml[ \t]+promotion-evidence[ \t]*\n(?P<body>.*?)^```[ \t]*$"
)
MATERIAL_SECTION_LETTERS = frozenset("BCDEFGHI")
LOCAL_EVIDENCE_ARTIFACTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "code": ("runbook_tools/", (".py",)),
    "test": ("tests/", (".py", ".json", ".yaml", ".yml", ".md")),
    "schema": ("schemas/", (".json",)),
    "spec": ("specs/", (".md",)),
    "workflow": (".github/workflows/", (".yaml", ".yml")),
}

TOP_LEVEL_FIELDS = frozenset(
    {"manifest_version", "purpose", "inventory", "policy", "risk_scale", "documents"}
)
INVENTORY_FIELDS = frozenset(
    {
        "repository",
        "base_sha",
        "inventory_sha",
        "blob_oid_scope",
        "inventory_path_semantics",
        "source_selector",
        "refresh_required_before_execution",
        "counts",
    }
)
COUNT_FIELDS = frozenset(
    {
        "operational_documents",
        "source_documents",
        "active",
        "grandfathered",
        "archived",
    }
)
POLICY_FIELDS = frozenset(
    {
        "pending_is_not_authority",
        "manifest_grants_no_authority",
        "archive_is_recoverable",
        "promotion_requires_ground_truth_verification",
        "merge_or_archive_requires_section_coverage",
        "high_risk_requires_independent_review",
    }
)
RISK_LEVELS = frozenset({"P0", "P1", "P2", "P3"})
DOCUMENT_FIELDS = frozenset(
    {
        "path",
        "inventory_path",
        "git_blob_oid",
        "catalog_state",
        "status",
        "proposed_disposition",
        "batch",
        "risk",
        "target_paths",
        "archive_path",
        "evidence",
        "verify_against",
        "verification_mappings",
        "independent_review_required",
    }
)
REQUIRED_DOCUMENT_FIELDS = DOCUMENT_FIELDS - {
    "inventory_path",
    "archive_path",
    "verification_mappings",
}
EVIDENCE_FIELDS = frozenset({"ref", "finding"})
VERIFICATION_MAPPING_FIELDS = frozenset(
    {
        "schema_version",
        "ordinal",
        "mapping_digest",
        "adapter_type",
        "adapter_parameters",
        "evidence_policy",
    }
)
EVIDENCE_POLICY_FIELDS = frozenset(
    {
        "minimum_receipts",
        "maximum_receipts",
        "freshness_seconds",
        "allowed_evidence_kinds",
        "require_remote_identity",
        "require_distinct_sources",
    }
)
ADAPTER_PARAMETER_FIELDS: dict[str, frozenset[str]] = {
    "git_object_v1": frozenset(
        {"repository", "commit_sha", "path", "expected_object_oid"}
    ),
    "json_schema_v1": frozenset(
        {
            "repository",
            "commit_sha",
            "path",
            "json_pointer",
            "expected_value_sha256",
        }
    ),
    "health_probe_v1": frozenset({"service_id", "probe_id", "max_age_seconds"}),
    "test_result_v1": frozenset(
        {"repository", "commit_sha", "test_id", "report_sha256"}
    ),
    "state_read_v1": frozenset(
        {"namespace", "entity_key", "field_path", "expected_value_sha256"}
    ),
    "production_probe_v1": frozenset(
        {"service_id", "probe_id", "max_age_seconds"}
    ),
    "unmapped_prose": frozenset(),
}
EVIDENCE_KINDS = ("git", "schema", "health", "test", "state", "probe")
DISPOSITIONS = frozenset(
    {
        "adjudicate_operational_or_spec",
        "archive",
        "archive_after_evidence_check",
        "evidence_only",
        "generated_projection",
        "merge_then_archive",
        "promote",
        "relocate_then_archive",
        "retain_active",
    }
)
ARCHIVE_DISPOSITIONS = frozenset(
    {
        "archive",
        "archive_after_evidence_check",
        "merge_then_archive",
        "relocate_then_archive",
    }
)


@dataclass(frozen=True)
class CorpusManifestReport:
    """Validated corpus totals from the working tree and ledger."""

    operational_documents: int
    source_documents: int
    active: int
    grandfathered: int
    archived: int
    pending: int
    promotion_bar: bool


@dataclass(frozen=True, slots=True)
class PinnedCorpusDocument:
    """One immutable operational-document record and its verified blob bytes."""

    path: str
    inventory_path: str
    git_blob_oid: str
    catalog_state: str
    status: str
    proposed_disposition: str
    batch: str
    risk: str
    verify_against: tuple[str, ...]
    verification_mappings: tuple[PinnedVerificationMapping, ...]
    markdown: str


@dataclass(frozen=True, slots=True)
class PinnedVerificationMapping:
    """One reviewed schema-v2 prose-to-adapter mapping."""

    ordinal: int
    mapping_digest: str
    adapter_type: str
    adapter_parameters: dict[str, Any]
    evidence_policy: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PinnedCorpusManifest:
    """Search-safe corpus projection loaded only from immutable Git objects."""

    search_sha: str
    manifest_blob_oid: str
    manifest_sha256: str
    base_sha: str
    inventory_sha: str
    operational_documents: int
    source_documents: int
    active: int
    grandfathered: int
    archived: int
    documents: tuple[PinnedCorpusDocument, ...]


class CorpusManifestError(ValueError):
    """One or more deterministic manifest validation failures."""

    def __init__(self, errors: Sequence[str]):
        self.errors = tuple(errors)
        super().__init__("\n".join(self.errors))


def load_pinned_corpus_manifest(
    repo_root: Path,
    search_sha: str,
) -> PinnedCorpusManifest:
    """Load the exhaustive corpus from one full immutable Git commit.

    Unlike :func:`validate_corpus_manifest`, this path deliberately has no
    working-tree dependency.  It is used by retrieval, where a dirty checkout
    and replacement refs must be unable to affect either inventory identity or
    document bytes.
    """

    errors: list[str] = []
    root = repo_root.resolve()
    if type(search_sha) is not str or HEX_OID_RE.fullmatch(search_sha) is None:
        raise CorpusManifestError(
            ["search SHA must be a lowercase full 40-character Git object ID"]
        )
    resolved_search = _resolve_exact_commit(
        root,
        search_sha,
        "search SHA",
        errors,
    )
    if resolved_search is None:
        raise CorpusManifestError(errors)

    search_tree = _pinned_git_tree(root, search_sha, "search SHA", errors)
    if search_tree is None:
        raise CorpusManifestError(errors)
    manifest_record = search_tree.get(MANIFEST_NAME)
    if manifest_record is None:
        raise CorpusManifestError(
            [f"{MANIFEST_NAME} is absent from search SHA {search_sha}"]
        )
    if manifest_record[0] not in {"100644", "100755"} or manifest_record[1] != "blob":
        raise CorpusManifestError(
            [f"{MANIFEST_NAME} at search SHA must be a regular Git blob"]
        )
    manifest_blob_oid = manifest_record[2]
    manifest_payloads = _read_pinned_blob_batch(
        root,
        [manifest_blob_oid],
        per_blob_limit=MAX_PINNED_MANIFEST_BYTES,
        aggregate_limit=MAX_PINNED_MANIFEST_BYTES,
        label="corpus manifest",
        errors=errors,
    )
    manifest_bytes = manifest_payloads.get(manifest_blob_oid)
    if manifest_bytes is None:
        raise CorpusManifestError(errors)
    manifest = _load_manifest_bytes(
        manifest_bytes,
        Path(f"{search_sha}:{MANIFEST_NAME}"),
        errors,
    )
    if manifest is None:
        raise CorpusManifestError(errors)

    _exact_keys(manifest, TOP_LEVEL_FIELDS, "manifest", errors)
    _expect_exact(
        manifest.get("manifest_version"),
        MANIFEST_VERSION,
        "manifest_version",
        errors,
    )
    _expect_exact(manifest.get("purpose"), PURPOSE, "purpose", errors)
    inventory = _mapping(manifest.get("inventory"), "inventory", errors)
    policy = _mapping(manifest.get("policy"), "policy", errors)
    risk_scale = _mapping(manifest.get("risk_scale"), "risk_scale", errors)
    raw_documents = manifest.get("documents")
    documents = raw_documents if type(raw_documents) is list else []
    if type(raw_documents) is not list:
        errors.append("documents must be a list")

    counts: dict[str, Any] = {}
    base_sha: str | None = None
    inventory_sha: str | None = None
    if inventory is not None:
        _exact_keys(inventory, INVENTORY_FIELDS, "inventory", errors)
        _nonempty_string(inventory.get("repository"), "inventory.repository", errors)
        _nonempty_string(
            inventory.get("blob_oid_scope"),
            "inventory.blob_oid_scope",
            errors,
        )
        _nonempty_string(
            inventory.get("inventory_path_semantics"),
            "inventory.inventory_path_semantics",
            errors,
        )
        _expect_exact(
            inventory.get("source_selector"),
            SOURCE_SELECTOR,
            "inventory.source_selector",
            errors,
        )
        _expect_exact(
            inventory.get("refresh_required_before_execution"),
            True,
            "inventory.refresh_required_before_execution",
            errors,
            exact_type=True,
        )
        for field in ("base_sha", "inventory_sha"):
            value = inventory.get(field)
            if type(value) is not str or HEX_OID_RE.fullmatch(value) is None:
                errors.append(
                    f"inventory.{field} must be a lowercase 40-character Git object ID"
                )
        if type(inventory.get("base_sha")) is str and HEX_OID_RE.fullmatch(
            inventory["base_sha"]
        ):
            base_sha = inventory["base_sha"]
        if type(inventory.get("inventory_sha")) is str and HEX_OID_RE.fullmatch(
            inventory["inventory_sha"]
        ):
            inventory_sha = inventory["inventory_sha"]
        parsed_counts = _mapping(inventory.get("counts"), "inventory.counts", errors)
        if parsed_counts is not None:
            counts = parsed_counts
            _exact_keys(counts, COUNT_FIELDS, "inventory.counts", errors)
            for field in sorted(COUNT_FIELDS):
                value = counts.get(field)
                if type(value) is not int or value < 0:
                    errors.append(
                        f"inventory.counts.{field} must be a non-negative integer"
                    )

    if policy is not None:
        _exact_keys(policy, POLICY_FIELDS, "policy", errors)
        for field in sorted(POLICY_FIELDS):
            _expect_exact(
                policy.get(field),
                True,
                f"policy.{field}",
                errors,
                exact_type=True,
            )
    if risk_scale is not None:
        _exact_keys(risk_scale, RISK_LEVELS, "risk_scale", errors)
        for risk in sorted(RISK_LEVELS):
            _nonempty_string(risk_scale.get(risk), f"risk_scale.{risk}", errors)

    projected: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    seen_inventory_paths: set[str] = set()
    state_counts = {"active": 0, "grandfathered": 0, "archived": 0}
    for index, raw_entry in enumerate(documents):
        label = f"documents[{index}]"
        entry = _mapping(raw_entry, label, errors)
        if entry is None:
            continue
        _exact_keys(
            entry,
            DOCUMENT_FIELDS,
            label,
            errors,
            required=REQUIRED_DOCUMENT_FIELDS,
        )
        path = _safe_markdown_path(entry.get("path"), f"{label}.path", errors)
        if path is not None:
            if len(path.encode("utf-8")) > MAX_PINNED_PATH_BYTES:
                errors.append(
                    f"{label}.path exceeds the {MAX_PINNED_PATH_BYTES}-byte limit"
                )
            if path in seen_paths:
                errors.append(f"{label}.path duplicates manifest path {path!r}")
            seen_paths.add(path)
        inventory_path = _safe_markdown_path(
            entry.get("inventory_path", path),
            f"{label}.inventory_path",
            errors,
        )
        if inventory_path is not None:
            if len(inventory_path.encode("utf-8")) > MAX_PINNED_PATH_BYTES:
                errors.append(
                    f"{label}.inventory_path exceeds the "
                    f"{MAX_PINNED_PATH_BYTES}-byte limit"
                )
            if inventory_path in seen_inventory_paths:
                errors.append(
                    f"{label}.inventory_path duplicates historical path "
                    f"{inventory_path!r}"
                )
            seen_inventory_paths.add(inventory_path)

        state = entry.get("catalog_state")
        status = entry.get("status")
        disposition = entry.get("proposed_disposition")
        if state not in state_counts:
            errors.append(
                f"{label}.catalog_state must be active, grandfathered, or archived"
            )
        else:
            state_counts[state] += 1
        if status not in {"active", "pending_verification", "archived"}:
            errors.append(f"{label}.status is not recognized")
        if state == "active" and status != "active":
            errors.append(f"{label}: active catalog_state requires status: active")
        if state == "grandfathered" and status != "pending_verification":
            errors.append(
                f"{label}: grandfathered catalog_state requires "
                "status: pending_verification"
            )
        if state == "archived":
            if status != "archived":
                errors.append(f"{label}: archived catalog_state requires status: archived")
            if "inventory_path" not in entry:
                errors.append(f"{label}: archived records require inventory_path")
            if path is not None and not _under(path, "archive"):
                errors.append(f"{label}.path must be under archive/ for archived records")
        if type(disposition) is not str or disposition not in DISPOSITIONS:
            errors.append(
                f"{label}.proposed_disposition is not a recognized disposition"
            )
        if state == "active" and disposition != "retain_active":
            errors.append(
                f"{label}: active catalog_state requires "
                "proposed_disposition: retain_active"
            )
        if state == "grandfathered" and disposition == "retain_active":
            errors.append(f"{label}: grandfathered source cannot retain active authority")

        blob_oid = entry.get("git_blob_oid")
        if type(blob_oid) is not str or HEX_OID_RE.fullmatch(blob_oid) is None:
            errors.append(
                f"{label}.git_blob_oid must be a lowercase 40-character blob ID"
            )
        batch = _validated_batch(entry.get("batch"), f"{label}.batch", errors)
        risk = entry.get("risk")
        if risk not in RISK_LEVELS:
            errors.append(f"{label}.risk must be one of P0, P1, P2, or P3")
        target_paths = _path_list(
            entry.get("target_paths"),
            f"{label}.target_paths",
            errors,
        )
        if state == "active" and path is not None and target_paths != [path]:
            errors.append(
                f"{label}: retained ACTIVE target_paths must contain only its current path"
            )
        archive_path: str | None = None
        if "archive_path" in entry:
            archive_path = _safe_markdown_path(
                entry.get("archive_path"),
                f"{label}.archive_path",
                errors,
            )
            if archive_path is not None and not _under(archive_path, "archive"):
                errors.append(f"{label}.archive_path must be under archive/")
        if disposition in ARCHIVE_DISPOSITIONS and archive_path is None:
            errors.append(f"{label}: {disposition} requires archive_path")
        if disposition not in ARCHIVE_DISPOSITIONS and "archive_path" in entry:
            errors.append(
                f"{label}: archive_path is only valid for an archive disposition"
            )
        if state == "archived" and archive_path is not None and path != archive_path:
            errors.append(f"{label}: archived path must equal archive_path")

        evidence = entry.get("evidence")
        if type(evidence) is not list:
            errors.append(f"{label}.evidence must be a list")
        else:
            for evidence_index, raw_evidence in enumerate(evidence):
                evidence_label = f"{label}.evidence[{evidence_index}]"
                item = _mapping(raw_evidence, evidence_label, errors)
                if item is None:
                    continue
                _exact_keys(item, EVIDENCE_FIELDS, evidence_label, errors)
                _nonempty_string(item.get("ref"), f"{evidence_label}.ref", errors)
                _nonempty_string(
                    item.get("finding"),
                    f"{evidence_label}.finding",
                    errors,
                )
        verify_against = _validated_verify_against(
            entry.get("verify_against"),
            f"{label}.verify_against",
            errors,
        )
        verification_mappings = _validated_verification_mappings(
            entry.get("verification_mappings"),
            verify_against,
            f"{label}.verification_mappings",
            errors,
        )
        review_required = entry.get("independent_review_required")
        if type(review_required) is not bool:
            errors.append(f"{label}.independent_review_required must be a boolean")
        elif state == "grandfathered" and risk in {"P0", "P1"} and not review_required:
            errors.append(f"{label}: pending {risk} work requires independent review")

        if all(
            value is not None
            for value in (path, inventory_path, state, status, disposition, blob_oid, batch, risk)
        ) and type(blob_oid) is str and HEX_OID_RE.fullmatch(blob_oid):
            projected.append(
                {
                    "path": path,
                    "inventory_path": inventory_path,
                    "git_blob_oid": blob_oid,
                    "catalog_state": state,
                    "status": status,
                    "proposed_disposition": disposition,
                    "batch": batch,
                    "risk": risk,
                    "verify_against": tuple(verify_against),
                    "verification_mappings": tuple(verification_mappings),
                }
            )

    expected_counts = {
        "operational_documents": len(documents),
        "source_documents": sum(
            type(entry) is dict and entry.get("catalog_state") != "archived"
            for entry in documents
        ),
        "active": state_counts["active"],
        "grandfathered": state_counts["grandfathered"],
        "archived": state_counts["archived"],
    }
    for field, actual in expected_counts.items():
        if type(counts.get(field)) is int and counts[field] != actual:
            errors.append(
                f"inventory.counts.{field} declares {counts[field]}, "
                f"but the pinned manifest has {actual}"
            )

    inventory_tree: dict[str, tuple[str, str, str]] | None = None
    if base_sha is not None:
        _resolve_exact_commit(root, base_sha, "inventory.base_sha", errors)
    if inventory_sha is not None:
        _resolve_exact_commit(root, inventory_sha, "inventory.inventory_sha", errors)
    if base_sha is not None and inventory_sha is not None:
        _require_pinned_ancestry(
            root,
            base_sha,
            inventory_sha,
            "inventory.base_sha to inventory.inventory_sha",
            errors,
        )
        _require_pinned_ancestry(
            root,
            inventory_sha,
            search_sha,
            "inventory.inventory_sha to search SHA",
            errors,
        )
        inventory_tree = _pinned_git_tree(
            root,
            inventory_sha,
            "inventory.inventory_sha",
            errors,
        )

    if inventory_tree is not None:
        expected_inventory_sources = {
            entry["inventory_path"]
            for entry in projected
            if entry["catalog_state"] != "archived"
        }
        expected_search_sources = {
            entry["path"]
            for entry in projected
            if entry["catalog_state"] != "archived"
        }
        for tree, expected, label in (
            (inventory_tree, expected_inventory_sources, "inventory"),
            (search_tree, expected_search_sources, "search"),
        ):
            actual = {
                path for path in tree if is_source_relative_path(path)
            }
            if actual != expected:
                missing = sorted(expected - actual)
                extra = sorted(actual - expected)
                details: list[str] = []
                if missing:
                    details.append("missing=" + ", ".join(missing))
                if extra:
                    details.append("extra=" + ", ".join(extra))
                errors.append(
                    f"{label} source document set mismatch: " + "; ".join(details)
                )
        for entry in projected:
            for tree, path, label in (
                (inventory_tree, entry["inventory_path"], "inventory path"),
                (search_tree, entry["path"], "search path"),
            ):
                record = tree.get(path)
                if record is None:
                    errors.append(f"{label} {path!r} is absent")
                    continue
                mode, object_type, oid = record
                if mode not in {"100644", "100755"} or object_type != "blob":
                    errors.append(
                        f"{label} {path!r} is mode {mode} {object_type}, "
                        "not a regular file"
                    )
                elif oid != entry["git_blob_oid"]:
                    errors.append(
                        f"{label} {path!r} has blob {oid}, expected "
                        f"{entry['git_blob_oid']}"
                    )

    if errors:
        raise CorpusManifestError(errors)
    assert base_sha is not None
    assert inventory_sha is not None
    blob_payloads = _read_pinned_blob_batch(
        root,
        [entry["git_blob_oid"] for entry in projected],
        per_blob_limit=MAX_PINNED_CORPUS_BLOB_BYTES,
        aggregate_limit=MAX_PINNED_CORPUS_BYTES,
        label="operational corpus",
        errors=errors,
    )
    pinned_documents: list[PinnedCorpusDocument] = []
    for entry in sorted(projected, key=lambda value: value["path"]):
        oid = entry["git_blob_oid"]
        payload = blob_payloads.get(oid)
        if payload is None:
            continue
        actual_oid = hashlib.sha1(
            f"blob {len(payload)}\0".encode("ascii") + payload,
            usedforsecurity=False,
        ).hexdigest()
        if actual_oid != oid:
            errors.append(
                f"operational corpus blob {oid} recomputes as {actual_oid}"
            )
            continue
        try:
            markdown = payload.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"operational corpus path {entry['path']!r} is not UTF-8")
            continue
        pinned_documents.append(
            PinnedCorpusDocument(
                path=entry["path"],
                inventory_path=entry["inventory_path"],
                git_blob_oid=oid,
                catalog_state=entry["catalog_state"],
                status=entry["status"],
                proposed_disposition=entry["proposed_disposition"],
                batch=entry["batch"],
                risk=entry["risk"],
                verify_against=entry["verify_against"],
                verification_mappings=entry["verification_mappings"],
                markdown=markdown,
            )
        )
    if errors:
        raise CorpusManifestError(errors)
    if len(pinned_documents) != len(documents):
        raise CorpusManifestError(
            [
                (
                    "pinned corpus materialization count differs from the manifest: "
                    f"{len(pinned_documents)} != {len(documents)}"
                )
            ]
        )
    return PinnedCorpusManifest(
        search_sha=search_sha,
        manifest_blob_oid=manifest_blob_oid,
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        base_sha=base_sha,
        inventory_sha=inventory_sha,
        operational_documents=expected_counts["operational_documents"],
        source_documents=expected_counts["source_documents"],
        active=expected_counts["active"],
        grandfathered=expected_counts["grandfathered"],
        archived=expected_counts["archived"],
        documents=tuple(pinned_documents),
    )


@dataclass(frozen=True)
class _GitTrees:
    inventory: dict[str, tuple[str, str, str]]
    head: dict[str, tuple[str, str, str]]


def pin_draft_promotion_evidence(
    repo_root: Path,
    target: Path,
    markdown: str,
    schemas_dir: Path,
) -> str:
    """Mechanically fill local evidence digests without granting authority.

    The result is still a DRAFT. The caller must commit the DRAFT and every
    evidence source, then refresh the corpus manifest from that exact content
    commit if preserving this material for future receipt work. Blob pinning is
    identity bookkeeping only; it does not verify claims or enable promotion.
    """

    errors: list[str] = []
    root = repo_root.resolve()
    frontmatter = extract_yaml_frontmatter(markdown)
    if type(frontmatter) is not dict or frontmatter.get("status") != "DRAFT":
        raise CorpusManifestError(
            ["evidence pinning requires a runbook with status DRAFT"]
        )
    matches = list(PROMOTION_EVIDENCE_FENCE_RE.finditer(markdown))
    if len(matches) != 1:
        raise CorpusManifestError(
            ["§K must contain exactly one ```yaml promotion-evidence block"]
        )
    match = matches[0]
    try:
        payload = strict_yaml_load(match.group("body"))
    except yaml.YAMLError as exc:
        raise CorpusManifestError([f"promotion evidence YAML is invalid: {exc}"]) from exc
    if type(payload) is not dict:
        raise CorpusManifestError(["promotion evidence must be a mapping"])
    rows = payload.get("verified_against")
    if type(rows) is not list or not rows:
        raise CorpusManifestError(["verified_against must be a non-empty list"])

    try:
        relative_target = target.resolve().relative_to(root).as_posix()
    except ValueError as exc:
        raise CorpusManifestError(
            ["evidence-pinning target resolves outside the repository root"]
        ) from exc
    allowed_evidence_keys = {
        "evidence_id",
        "kind",
        "artifact_type",
        "locator",
        "git_blob_oid",
        "content_sha256",
        "supports_sections",
    }
    for index, raw_evidence in enumerate(rows):
        label = f"verified_against[{index}]"
        evidence = _mapping(raw_evidence, label, errors)
        if evidence is None:
            continue
        unknown = sorted(set(evidence) - allowed_evidence_keys, key=str)
        if unknown:
            errors.append(f"{label} has unknown fields: {', '.join(map(str, unknown))}")
            continue
        for field in (
            "evidence_id",
            "kind",
            "artifact_type",
            "locator",
            "supports_sections",
        ):
            if field not in evidence:
                errors.append(f"{label} is missing field {field}")
        if any(
            field not in evidence
            for field in (
                "evidence_id",
                "kind",
                "artifact_type",
                "locator",
                "supports_sections",
            )
        ):
            continue
        if evidence["kind"] != "repository_blob":
            errors.append(f"{label}.kind must be repository_blob")
            continue
        parsed_path = _safe_repository_evidence_path(
            evidence["locator"], evidence["artifact_type"], label, errors
        )
        if parsed_path is None:
            continue
        if parsed_path == relative_target or is_source_relative_path(parsed_path):
            errors.append(
                f"{label}: operational Markdown cannot be a promotion evidence source"
            )
            continue
        symlink_component = _symlink_component(root, parsed_path)
        if symlink_component is not None:
            errors.append(
                f"{label}: locator contains symlink component {symlink_component!r}"
            )
            continue
        evidence_path = root / parsed_path
        try:
            source_stat = evidence_path.stat(follow_symlinks=False)
            source_bytes = evidence_path.read_bytes()
        except OSError as exc:
            errors.append(f"{label}: cannot read evidence source: {exc}")
            continue
        if not stat.S_ISREG(source_stat.st_mode):
            errors.append(f"{label}: evidence source must be a regular file")
            continue
        header = f"blob {len(source_bytes)}\0".encode("ascii")
        evidence["git_blob_oid"] = hashlib.sha1(
            header + source_bytes, usedforsecurity=False
        ).hexdigest()
        evidence["content_sha256"] = hashlib.sha256(source_bytes).hexdigest()

    schema = _load_json_schema(
        schemas_dir / PROMOTION_EVIDENCE_SCHEMA,
        "promotion evidence schema",
        errors,
    )
    if schema is not None:
        for finding in sorted(
            Draft202012Validator(schema).iter_errors(payload),
            key=lambda item: (list(item.absolute_path), item.message),
        ):
            location = ".".join(str(part) for part in finding.absolute_path)
            errors.append(
                f"promotion evidence{'.' + location if location else ''}: "
                f"{finding.message}"
            )
    if errors:
        raise CorpusManifestError(errors)

    rendered = yaml.dump(
        payload,
        Dumper=_ManifestDumper,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=100,
    )
    return markdown[: match.start("body")] + rendered + markdown[match.end("body") :]


class _ManifestDumper(yaml.SafeDumper):
    """Deterministic, alias-free YAML used only for mechanical pin refreshes."""

    def ignore_aliases(self, data: Any) -> bool:
        return True

    def increase_indent(
        self,
        flow: bool = False,
        indentless: bool = False,
    ) -> None:
        return super().increase_indent(flow=flow, indentless=False)


def validate_corpus_manifest(
    repo_root: Path,
    manifest_path: Path | None = None,
    *,
    promotion_bar: bool = False,
) -> CorpusManifestReport:
    """Validate the manifest against working-tree sources and its pinned Git tree.

    The default check permits the explicitly inventoried pending estate.  The
    promotion bar additionally requires that every current source is ACTIVE,
    no pending adjudication remains, and no source Markdown lives at repository
    root.  Archived ledger records are allowed outside the source selector, but
    they never count as catalog authority.
    """

    root = repo_root.resolve()
    path = manifest_path or root / MANIFEST_NAME
    if not path.is_absolute():
        path = root / path

    errors: list[str] = []
    if path.is_symlink():
        errors.append(f"{path}: manifest file must not be a symlink")
        raise CorpusManifestError(errors)
    manifest = _load_manifest(path, errors)
    if manifest is None:
        raise CorpusManifestError(errors)

    _exact_keys(manifest, TOP_LEVEL_FIELDS, "manifest", errors)
    _expect_exact(
        manifest.get("manifest_version"), MANIFEST_VERSION, "manifest_version", errors
    )
    _expect_exact(manifest.get("purpose"), PURPOSE, "purpose", errors)

    inventory = _mapping(manifest.get("inventory"), "inventory", errors)
    policy = _mapping(manifest.get("policy"), "policy", errors)
    risk_scale = _mapping(manifest.get("risk_scale"), "risk_scale", errors)
    raw_documents = manifest.get("documents")
    documents = raw_documents if type(raw_documents) is list else []
    if type(raw_documents) is not list:
        errors.append("documents must be a list")

    counts: dict[str, Any] = {}
    base_sha: str | None = None
    inventory_sha: str | None = None
    if inventory is not None:
        _exact_keys(inventory, INVENTORY_FIELDS, "inventory", errors)
        _nonempty_string(inventory.get("repository"), "inventory.repository", errors)
        _nonempty_string(
            inventory.get("blob_oid_scope"), "inventory.blob_oid_scope", errors
        )
        _nonempty_string(
            inventory.get("inventory_path_semantics"),
            "inventory.inventory_path_semantics",
            errors,
        )
        _expect_exact(
            inventory.get("source_selector"),
            SOURCE_SELECTOR,
            "inventory.source_selector",
            errors,
        )
        _expect_exact(
            inventory.get("refresh_required_before_execution"),
            True,
            "inventory.refresh_required_before_execution",
            errors,
            exact_type=True,
        )
        for field in ("base_sha", "inventory_sha"):
            value = inventory.get(field)
            if type(value) is not str or HEX_OID_RE.fullmatch(value) is None:
                errors.append(
                    f"inventory.{field} must be a lowercase 40-character Git object ID"
                )
        if type(inventory.get("base_sha")) is str and HEX_OID_RE.fullmatch(
            inventory["base_sha"]
        ):
            base_sha = inventory["base_sha"]
        if type(inventory.get("inventory_sha")) is str and HEX_OID_RE.fullmatch(
            inventory["inventory_sha"]
        ):
            inventory_sha = inventory["inventory_sha"]

        parsed_counts = _mapping(inventory.get("counts"), "inventory.counts", errors)
        if parsed_counts is not None:
            counts = parsed_counts
            _exact_keys(counts, COUNT_FIELDS, "inventory.counts", errors)
            for field in sorted(COUNT_FIELDS):
                value = counts.get(field)
                if type(value) is not int or value < 0:
                    errors.append(
                        f"inventory.counts.{field} must be a non-negative integer"
                    )

    if policy is not None:
        _exact_keys(policy, POLICY_FIELDS, "policy", errors)
        for field in sorted(POLICY_FIELDS):
            _expect_exact(
                policy.get(field), True, f"policy.{field}", errors, exact_type=True
            )

    if risk_scale is not None:
        _exact_keys(risk_scale, RISK_LEVELS, "risk_scale", errors)
        for risk in sorted(RISK_LEVELS):
            _nonempty_string(risk_scale.get(risk), f"risk_scale.{risk}", errors)

    selector_paths = _working_source_paths(root, errors)
    classifications = _working_classifications(root, selector_paths, errors)
    git_trees = (
        _git_tree(root, inventory_sha, base_sha, errors)
        if inventory_sha is not None
        else None
    )
    git_tree = git_trees.inventory if git_trees is not None else None

    ledger_source_paths: set[str] = set()
    ledger_paths: set[str] = set()
    inventory_paths: set[str] = set()
    archived_inventory_paths: set[str] = set()
    active_count = 0
    grandfathered_count = 0
    archived_count = 0
    pending_count = 0

    for index, raw_entry in enumerate(documents):
        label = f"documents[{index}]"
        entry = _mapping(raw_entry, label, errors)
        if entry is None:
            continue
        _exact_keys(
            entry,
            DOCUMENT_FIELDS,
            label,
            errors,
            required=REQUIRED_DOCUMENT_FIELDS,
        )

        document_path = _safe_markdown_path(entry.get("path"), f"{label}.path", errors)
        if document_path is not None:
            if document_path in ledger_paths:
                errors.append(
                    f"{label}.path duplicates manifest path {document_path!r}"
                )
            ledger_paths.add(document_path)

        state = entry.get("catalog_state")
        status = entry.get("status")
        disposition = entry.get("proposed_disposition")
        if state not in {"active", "grandfathered", "archived"}:
            errors.append(
                f"{label}.catalog_state must be active, grandfathered, or archived"
            )
        if type(disposition) is not str or disposition not in DISPOSITIONS:
            errors.append(
                f"{label}.proposed_disposition is not a recognized disposition"
            )

        if state == "active":
            active_count += 1
            if status != "active":
                errors.append(f"{label}: active catalog_state requires status: active")
            if disposition != "retain_active":
                errors.append(
                    f"{label}: active catalog_state requires proposed_disposition: retain_active"
                )
        elif state == "grandfathered":
            grandfathered_count += 1
            if status != "pending_verification":
                errors.append(
                    f"{label}: grandfathered catalog_state requires status: pending_verification"
                )
            if disposition == "retain_active":
                errors.append(
                    f"{label}: grandfathered source cannot retain active authority"
                )
        elif state == "archived":
            archived_count += 1
            if status != "archived":
                errors.append(
                    f"{label}: archived catalog_state requires status: archived"
                )
            if disposition not in ARCHIVE_DISPOSITIONS:
                errors.append(
                    f"{label}: archived catalog_state requires an archive disposition"
                )

        if status == "pending_verification":
            pending_count += 1
        elif status not in {"active", "archived"}:
            errors.append(f"{label}.status is not recognized")

        if document_path is not None:
            if state == "archived":
                if not _under(document_path, "archive"):
                    errors.append(
                        f"{label}.path must be under archive/ for archived records"
                    )
                if document_path in selector_paths:
                    errors.append(
                        f"{label}.path is archived but remains in the source selector"
                    )
            else:
                ledger_source_paths.add(document_path)
                actual = classifications.get(document_path)
                if actual is not None and actual != state:
                    errors.append(
                        f"{label}.catalog_state is {state!r}, but current frontmatter classifies "
                        f"{document_path!r} as {actual!r}"
                    )

        raw_inventory_path = entry.get("inventory_path", document_path)
        inventory_path = _safe_markdown_path(
            raw_inventory_path,
            f"{label}.inventory_path",
            errors,
        )
        if state == "archived" and "inventory_path" not in entry:
            errors.append(f"{label}: archived records require inventory_path")
        if inventory_path is not None:
            if inventory_path in inventory_paths:
                errors.append(
                    f"{label}.inventory_path duplicates historical source {inventory_path!r}"
                )
            inventory_paths.add(inventory_path)
            if state == "archived":
                archived_inventory_paths.add(inventory_path)

        blob_oid = entry.get("git_blob_oid")
        if type(blob_oid) is not str or HEX_OID_RE.fullmatch(blob_oid) is None:
            errors.append(
                f"{label}.git_blob_oid must be a lowercase 40-character blob ID"
            )
        elif inventory_path is not None and git_tree is not None:
            tree_record = git_tree.get(inventory_path)
            if tree_record is None:
                errors.append(
                    f"{label}: inventory path {inventory_path!r} is absent from inventory_sha"
                )
            elif tree_record[0] not in {"100644", "100755"} or tree_record[1] != "blob":
                errors.append(
                    f"{label}: inventory path {inventory_path!r} is mode "
                    f"{tree_record[0]} {tree_record[1]}, not a regular file"
                )
            elif tree_record[2] != blob_oid:
                errors.append(
                    f"{label}.git_blob_oid {blob_oid} does not match {inventory_path!r} "
                    f"at inventory_sha ({tree_record[2]})"
                )
        if (
            document_path is not None
            and type(blob_oid) is str
            and HEX_OID_RE.fullmatch(blob_oid) is not None
            and git_trees is not None
        ):
            head_record = git_trees.head.get(document_path)
            if head_record is None:
                errors.append(
                    f"{label}: current path {document_path!r} is absent from checked-out HEAD"
                )
            elif head_record[0] not in {"100644", "100755"} or head_record[1] != "blob":
                errors.append(
                    f"{label}: current path {document_path!r} is mode "
                    f"{head_record[0]} {head_record[1]} in checked-out HEAD, "
                    "not a regular file"
                )
            elif head_record[2] != blob_oid:
                errors.append(
                    f"{label}.git_blob_oid {blob_oid} does not match current path "
                    f"{document_path!r} in checked-out HEAD ({head_record[2]})"
                )
        if (
            state != "archived"
            and document_path is not None
            and document_path in selector_paths
            and type(blob_oid) is str
            and HEX_OID_RE.fullmatch(blob_oid) is not None
        ):
            current_oid = _working_blob_oid(root / document_path, label, errors)
            if current_oid is not None and current_oid != blob_oid:
                errors.append(
                    f"{label}.git_blob_oid {blob_oid} does not match current bytes for "
                    f"{document_path!r} ({current_oid}); refresh the pinned inventory before "
                    "execution"
                )

        _validated_batch(entry.get("batch"), f"{label}.batch", errors)

        risk = entry.get("risk")
        if risk not in RISK_LEVELS:
            errors.append(f"{label}.risk must be one of P0, P1, P2, or P3")

        review_required = entry.get("independent_review_required")
        if type(review_required) is not bool:
            errors.append(f"{label}.independent_review_required must be a boolean")
        elif state == "grandfathered" and risk in {"P0", "P1"} and not review_required:
            errors.append(f"{label}: pending {risk} work requires independent review")

        target_paths = _path_list(
            entry.get("target_paths"), f"{label}.target_paths", errors
        )
        if (
            state == "active"
            and document_path is not None
            and target_paths != [document_path]
        ):
            errors.append(
                f"{label}: retained ACTIVE target_paths must contain only its current path"
            )

        archive_path: str | None = None
        if "archive_path" in entry:
            archive_path = _safe_markdown_path(
                entry.get("archive_path"), f"{label}.archive_path", errors
            )
            if archive_path is not None and not _under(archive_path, "archive"):
                errors.append(f"{label}.archive_path must be under archive/")
        if disposition in ARCHIVE_DISPOSITIONS and archive_path is None:
            errors.append(f"{label}: {disposition} requires archive_path")
        if disposition not in ARCHIVE_DISPOSITIONS and "archive_path" in entry:
            errors.append(
                f"{label}: archive_path is only valid for an archive disposition"
            )
        if (
            state == "archived"
            and archive_path is not None
            and document_path != archive_path
        ):
            errors.append(f"{label}: archived path must equal archive_path")
        if (
            state == "archived"
            and document_path is not None
            and type(blob_oid) is str
            and HEX_OID_RE.fullmatch(blob_oid) is not None
        ):
            archive_file = root / document_path
            symlink_component = _symlink_component(root, document_path)
            if symlink_component is not None:
                errors.append(
                    f"{label}: archived path must not contain symlink component "
                    f"{symlink_component!r}"
                )
            elif not archive_file.is_file():
                errors.append(
                    f"{label}: archived path is not recoverable in the current tree: "
                    f"{document_path!r}"
                )
            else:
                try:
                    archive_file.resolve().relative_to(root)
                except ValueError:
                    errors.append(
                        f"{label}: archived path resolves outside the repository root"
                    )
                else:
                    archive_oid = _working_blob_oid(archive_file, label, errors)
                    if archive_oid is not None and archive_oid != blob_oid:
                        errors.append(
                            f"{label}.git_blob_oid {blob_oid} does not match current "
                            f"archived bytes for {document_path!r} ({archive_oid}); "
                            "archive must preserve the inventoried source bytes"
                        )

        evidence = entry.get("evidence")
        if type(evidence) is not list:
            errors.append(f"{label}.evidence must be a list")
        else:
            for evidence_index, raw_evidence in enumerate(evidence):
                evidence_label = f"{label}.evidence[{evidence_index}]"
                item = _mapping(raw_evidence, evidence_label, errors)
                if item is None:
                    continue
                _exact_keys(item, EVIDENCE_FIELDS, evidence_label, errors)
                _nonempty_string(item.get("ref"), f"{evidence_label}.ref", errors)
                _nonempty_string(
                    item.get("finding"), f"{evidence_label}.finding", errors
                )

        verify_against = _validated_verify_against(
            entry.get("verify_against"), f"{label}.verify_against", errors
        )
        _validated_verification_mappings(
            entry.get("verification_mappings"),
            verify_against,
            f"{label}.verification_mappings",
            errors,
        )

    missing = sorted(selector_paths - ledger_source_paths)
    extra = sorted(ledger_source_paths - selector_paths)
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append("missing=" + ", ".join(missing))
        if extra:
            details.append("extra=" + ", ".join(extra))
        errors.append("source document set mismatch: " + "; ".join(details))

    if git_trees is not None:
        pinned_source_paths = {
            relative
            for relative in git_trees.inventory
            if is_source_relative_path(relative)
        }
        expected_inventory_paths = pinned_source_paths | archived_inventory_paths
        missing_inventory = sorted(expected_inventory_paths - inventory_paths)
        extra_inventory = sorted(inventory_paths - expected_inventory_paths)
        if missing_inventory or extra_inventory:
            details = []
            if missing_inventory:
                details.append("missing=" + ", ".join(missing_inventory))
            if extra_inventory:
                details.append("extra=" + ", ".join(extra_inventory))
            errors.append(
                "pinned inventory document set mismatch: " + "; ".join(details)
            )

        head_source_paths = {
            relative for relative in git_trees.head if is_source_relative_path(relative)
        }
        missing_head = sorted(head_source_paths - ledger_source_paths)
        extra_head = sorted(ledger_source_paths - head_source_paths)
        if missing_head or extra_head:
            details = []
            if missing_head:
                details.append("missing=" + ", ".join(missing_head))
            if extra_head:
                details.append("extra=" + ", ".join(extra_head))
            errors.append(
                "checked-out HEAD source document set mismatch: "
                + "; ".join(details)
            )

    actual_counts = {
        "source_documents": len(selector_paths),
        "active": sum(value == "active" for value in classifications.values()),
        "grandfathered": sum(
            value == "grandfathered" for value in classifications.values()
        ),
        "archived": archived_count,
        "operational_documents": len(selector_paths) + archived_count,
    }
    for field, actual in actual_counts.items():
        if type(counts.get(field)) is int and counts[field] != actual:
            errors.append(
                f"inventory.counts.{field} declares {counts[field]}, but current source corpus has {actual}"
            )
    if active_count != actual_counts["active"]:
        errors.append(
            f"manifest has {active_count} active source records, but current source corpus has "
            f"{actual_counts['active']}"
        )
    if grandfathered_count != actual_counts["grandfathered"]:
        errors.append(
            f"manifest has {grandfathered_count} grandfathered source records, but current source "
            f"corpus has {actual_counts['grandfathered']}"
        )

    if promotion_bar:
        if any(
            type(entry) is dict and entry.get("catalog_state") == "active"
            for entry in documents
        ):
            errors.append(
                "promotion bar: trusted claim-bound evidence and independent review "
                "authority are not deployed; ACTIVE syntax and local evidence cannot "
                "establish promotion truth"
            )
        pending_paths = sorted(
            entry.get("path", f"documents[{index}]")
            for index, entry in enumerate(documents)
            if type(entry) is dict and entry.get("status") == "pending_verification"
        )
        if pending_paths:
            errors.append(
                "promotion bar: pending adjudication remains for "
                + ", ".join(pending_paths)
            )
        root_sources = sorted(
            path for path in selector_paths if len(PurePosixPath(path).parts) == 1
        )
        if root_sources:
            errors.append(
                "promotion bar: source Markdown remains at repository root: "
                + ", ".join(root_sources)
            )
        inactive_sources = sorted(
            path for path, state in classifications.items() if state != "active"
        )
        if inactive_sources:
            errors.append(
                "promotion bar: source documents are not ACTIVE: "
                + ", ".join(inactive_sources)
            )
        for index, raw_entry in enumerate(documents):
            if type(raw_entry) is not dict or raw_entry.get("catalog_state") != "active":
                continue
            active_path = raw_entry.get("path")
            if type(active_path) is not str:
                continue
            if type(raw_entry.get("evidence")) is not list or not raw_entry["evidence"]:
                errors.append(
                    f"promotion bar: {active_path} has empty adjudication evidence; "
                    "existing ACTIVE status is shadow/grandfathered, not proof"
                )
            try:
                active_markdown = (root / active_path).read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                errors.append(
                    f"promotion bar: cannot read ACTIVE source {active_path!r}: {exc}"
                )
                continue
            evidence_errors = _promotion_evidence_errors(
                root,
                active_path,
                active_markdown,
                raw_entry,
                repository=inventory.get("repository") if inventory is not None else None,
                inventory_sha=inventory_sha,
                trees=git_trees,
                schemas_dir=root / "schemas",
            )
            errors.extend(
                f"promotion bar: {finding}" for finding in evidence_errors
            )

    if errors:
        raise CorpusManifestError(errors)
    return CorpusManifestReport(
        operational_documents=actual_counts["operational_documents"],
        source_documents=actual_counts["source_documents"],
        active=actual_counts["active"],
        grandfathered=actual_counts["grandfathered"],
        archived=archived_count,
        pending=pending_count,
        promotion_bar=promotion_bar,
    )


def refresh_corpus_manifest(
    repo_root: Path,
    inventory_sha: str,
    manifest_path: Path | None = None,
) -> CorpusManifestReport:
    """Mechanically pin the canonical ledger to the exact checked-out HEAD.

    Adjudication fields are never inferred or changed. Only the immutable
    snapshot SHA, current inventory paths, blob IDs, and derived counts are
    refreshed. The candidate is fully validated from a temporary regular file
    before one atomic replacement, so a failed refresh preserves the old ledger.
    """

    root = repo_root.resolve()
    canonical_path = root / MANIFEST_NAME
    path = manifest_path or canonical_path
    if not path.is_absolute():
        path = root / path

    lock_path = root / ".runbook-manifest.lock"
    lock_flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        lock_flags |= os.O_NOFOLLOW
    try:
        lock_descriptor = os.open(lock_path, lock_flags, 0o600)
    except OSError as exc:
        raise CorpusManifestError(
            [f"cannot open regular repository refresh lock {lock_path}: {exc}"]
        ) from exc
    with os.fdopen(lock_descriptor, "r+b") as lock_handle:
        if not stat.S_ISREG(os.fstat(lock_handle.fileno()).st_mode):
            raise CorpusManifestError(
                [f"repository refresh lock {lock_path} must be a regular file"]
            )
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        try:
            return _refresh_corpus_manifest_locked(
                root,
                inventory_sha,
                path,
                canonical_path,
            )
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def _refresh_corpus_manifest_locked(
    root: Path,
    inventory_sha: str,
    path: Path,
    canonical_path: Path,
) -> CorpusManifestReport:
    """Refresh while the repository-specific interprocess lock is held."""

    errors: list[str] = []
    if path != canonical_path:
        errors.append(
            f"refresh target must be the canonical repository ledger {canonical_path}"
        )
    if path.is_symlink():
        errors.append(f"{path}: manifest file must not be a symlink")
    if HEX_OID_RE.fullmatch(inventory_sha) is None:
        errors.append("--refresh-from must be a lowercase full 40-character commit SHA")
    original_bytes: bytes | None = None
    original_stat: os.stat_result | None = None
    if not errors:
        try:
            original_stat = os.stat(path, follow_symlinks=False)
            if not stat.S_ISREG(original_stat.st_mode):
                errors.append(f"{path}: manifest file must be a regular file")
            else:
                original_bytes = path.read_bytes()
        except OSError as exc:
            errors.append(f"{path}: cannot read manifest for refresh: {exc}")
    manifest = (
        _load_manifest_bytes(original_bytes, path, errors)
        if original_bytes is not None
        else None
    )
    if manifest is None:
        raise CorpusManifestError(errors)
    protected_before = _protected_manifest_projection(manifest)

    head_sha = _resolve_commit(root, "HEAD", "checked-out HEAD", errors)
    resolved_inventory = _resolve_exact_commit(
        root,
        inventory_sha,
        "--refresh-from",
        errors,
    )
    if (
        head_sha is not None
        and resolved_inventory is not None
        and resolved_inventory != head_sha
    ):
        errors.append(
            f"--refresh-from must equal checked-out HEAD {head_sha}, got "
            f"{resolved_inventory}"
        )

    inventory = _mapping(manifest.get("inventory"), "inventory", errors)
    raw_documents = manifest.get("documents")
    documents = raw_documents if type(raw_documents) is list else []
    if type(raw_documents) is not list:
        errors.append("documents must be a list")
    base_sha = inventory.get("base_sha") if inventory is not None else None
    if type(base_sha) is not str or HEX_OID_RE.fullmatch(base_sha) is None:
        errors.append(
            "inventory.base_sha must be a lowercase 40-character Git object ID"
        )
        base_sha = None

    trees = (
        _git_tree(root, inventory_sha, base_sha, errors)
        if resolved_inventory is not None
        else None
    )
    selector_paths = _working_source_paths(root, errors)
    classifications = _working_classifications(root, selector_paths, errors)

    document_paths: set[str] = set()
    nonarchived_paths: set[str] = set()
    archived_count = 0
    prepared: list[tuple[dict[str, Any], str, str]] = []
    for index, raw_entry in enumerate(documents):
        label = f"documents[{index}]"
        entry = _mapping(raw_entry, label, errors)
        if entry is None:
            continue
        document_path = _safe_markdown_path(entry.get("path"), f"{label}.path", errors)
        state = entry.get("catalog_state")
        if state not in {"active", "grandfathered", "archived"}:
            errors.append(
                f"{label}.catalog_state must be active, grandfathered, or archived"
            )
        if document_path is None or state not in {
            "active",
            "grandfathered",
            "archived",
        }:
            continue
        if document_path in document_paths:
            errors.append(f"{label}.path duplicates manifest path {document_path!r}")
        document_paths.add(document_path)
        if state == "archived":
            archived_count += 1
        else:
            nonarchived_paths.add(document_path)
        prepared.append((entry, document_path, state))

    if nonarchived_paths != selector_paths:
        missing = sorted(selector_paths - nonarchived_paths)
        extra = sorted(nonarchived_paths - selector_paths)
        details: list[str] = []
        if missing:
            details.append("missing=" + ", ".join(missing))
        if extra:
            details.append("extra=" + ", ".join(extra))
        errors.append("refresh source document set mismatch: " + "; ".join(details))

    if trees is not None:
        pinned_sources = {
            relative
            for relative in trees.inventory
            if is_source_relative_path(relative)
        }
        if pinned_sources != nonarchived_paths:
            missing = sorted(pinned_sources - nonarchived_paths)
            extra = sorted(nonarchived_paths - pinned_sources)
            details = []
            if missing:
                details.append("missing=" + ", ".join(missing))
            if extra:
                details.append("extra=" + ", ".join(extra))
            errors.append(
                "refresh pinned source document set mismatch: "
                + "; ".join(details)
            )

        for entry, document_path, state in prepared:
            record = trees.inventory.get(document_path)
            if record is None:
                errors.append(
                    f"refresh path {document_path!r} is absent from --refresh-from"
                )
                continue
            mode, object_type, oid = record
            if mode not in {"100644", "100755"} or object_type != "blob":
                errors.append(
                    f"refresh path {document_path!r} is mode {mode} {object_type}, "
                    "not a regular file"
                )
                continue
            entry["git_blob_oid"] = oid
            if state == "archived":
                entry["inventory_path"] = document_path
            else:
                entry.pop("inventory_path", None)

    if inventory is not None:
        inventory["inventory_sha"] = inventory_sha
        counts = _mapping(inventory.get("counts"), "inventory.counts", errors)
        if counts is not None:
            counts.update(
                {
                    "operational_documents": len(selector_paths) + archived_count,
                    "source_documents": len(selector_paths),
                    "active": sum(
                        value == "active" for value in classifications.values()
                    ),
                    "grandfathered": sum(
                        value == "grandfathered"
                        for value in classifications.values()
                    ),
                    "archived": archived_count,
                }
            )

    if _protected_manifest_projection(manifest) != protected_before:
        errors.append(
            "refresh attempted to change protected adjudication, evidence, risk, "
            "or disposition fields"
        )

    if errors:
        raise CorpusManifestError(errors)

    rendered = yaml.dump(
        manifest,
        Dumper=_ManifestDumper,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=100,
    )
    file_mode = path.stat().st_mode & 0o777
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.refresh-",
        suffix=".yaml",
        dir=path.parent,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, file_mode)
        report = validate_corpus_manifest(root, temp_path)
        current_head = _resolve_commit(root, "HEAD", "checked-out HEAD", errors)
        if current_head != inventory_sha:
            errors.append(
                f"checked-out HEAD changed during refresh: expected {inventory_sha}, "
                f"found {current_head}"
            )
        try:
            current_stat = os.stat(path, follow_symlinks=False)
            current_bytes = path.read_bytes()
        except OSError as exc:
            errors.append(f"canonical ledger changed during refresh: {exc}")
        else:
            if (
                original_stat is None
                or original_bytes is None
                or _stat_identity(current_stat) != _stat_identity(original_stat)
                or current_bytes != original_bytes
                or not stat.S_ISREG(current_stat.st_mode)
            ):
                errors.append(
                    "canonical ledger changed during refresh; refusing to overwrite "
                    "concurrent adjudication"
                )
        if errors:
            raise CorpusManifestError(errors)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)
    return report


def _promotion_evidence_errors(
    root: Path,
    document_path: str,
    markdown: str,
    entry: dict[str, Any],
    *,
    repository: Any,
    inventory_sha: Any,
    trees: _GitTrees | None,
    schemas_dir: Path,
) -> list[str]:
    """Validate a preparatory projection; never treat it as promotion authority."""

    errors: list[str] = []
    evidence_schema = _load_json_schema(
        schemas_dir / PROMOTION_EVIDENCE_SCHEMA,
        "promotion evidence schema",
        errors,
    )
    # The receipt schema is part of the future hand-off contract even while no
    # trust roots or deployed verifier exist. Checking it here prevents a
    # malformed contract from silently shipping beside a locally admitted item.
    _load_json_schema(
        schemas_dir / PROMOTION_RECEIPT_SCHEMA,
        "promotion receipt schema",
        errors,
    )

    sections = extract_sections(markdown)
    conformance_sections = [section for section in sections if section.letter == "K"]
    payload: dict[str, Any] | None = None
    if len(conformance_sections) != 1:
        errors.append(
            f"{document_path}: promotion evidence requires exactly one §K section"
        )
    else:
        parsed = extract_fenced_yaml_block(
            conformance_sections[0], PROMOTION_EVIDENCE_INFO
        )
        if type(parsed) is not dict:
            errors.append(
                f"{document_path}: §K must contain exactly one valid "
                "```yaml promotion-evidence mapping"
            )
        else:
            payload = parsed

    if payload is None or evidence_schema is None:
        return errors

    validator = Draft202012Validator(evidence_schema)
    schema_errors = sorted(
        validator.iter_errors(payload),
        key=lambda item: (list(item.absolute_path), item.message),
    )
    for finding in schema_errors:
        location = ".".join(str(part) for part in finding.absolute_path)
        label = f"promotion evidence.{location}" if location else "promotion evidence"
        errors.append(f"{document_path}: {label}: {finding.message}")
    if schema_errors:
        return errors

    risk = payload["risk"]
    if risk != entry.get("risk"):
        errors.append(
            f"{document_path}: promotion evidence risk {risk!r} does not match "
            f"corpus ledger risk {entry.get('risk')!r}"
        )

    frontmatter = extract_yaml_frontmatter(markdown)
    authority_letters: set[str] = set()
    if type(frontmatter) is dict:
        for field in ("authoritative_for", "error_signatures"):
            rows = frontmatter.get(field)
            if type(rows) is not list:
                continue
            for row in rows:
                if type(row) is not dict or type(row.get("section")) is not str:
                    continue
                match = re.match(r"\A§([A-K])(?:\.|\s|\Z)", row["section"])
                if match is not None:
                    authority_letters.add(match.group(1))

    required_sections = set(MATERIAL_SECTION_LETTERS) | authority_letters
    coverage_rows: dict[str, dict[str, Any]] = {}
    for row in payload["section_coverage"]:
        section_letter = row["section"]
        if section_letter in coverage_rows:
            errors.append(
                f"{document_path}: duplicate promotion coverage for §{section_letter}"
            )
            continue
        coverage_rows[section_letter] = row
    missing_coverage = sorted(required_sections - coverage_rows.keys())
    if missing_coverage:
        errors.append(
            f"{document_path}: material sections lack promotion coverage: "
            + ", ".join(f"§{letter}" for letter in missing_coverage)
        )

    evidence_rows: dict[str, dict[str, Any]] = {}
    for evidence in payload["verified_against"]:
        evidence_id = evidence["evidence_id"]
        if evidence_id in evidence_rows:
            errors.append(
                f"{document_path}: duplicate verified_against evidence_id {evidence_id!r}"
            )
            continue
        evidence_rows[evidence_id] = evidence
        errors.extend(
            _resolve_local_evidence_blob(
                root,
                document_path,
                evidence,
                repository=repository,
                inventory_sha=inventory_sha,
                trees=trees,
            )
        )

    sections_by_letter = {section.letter: section for section in sections}
    for section_letter, coverage in coverage_rows.items():
        if coverage["status"] == "UNKNOWN":
            gap = coverage["gap"]
            if section_letter in authority_letters:
                errors.append(
                    f"{document_path}: §{section_letter} is declared UNKNOWN but catalog "
                    "metadata grants it authority"
                )
            section = sections_by_letter.get(section_letter)
            marker = f"Current state: UNKNOWN; gap: {gap['gap_id']}."
            if section is None or marker not in section.raw_markdown.splitlines():
                errors.append(
                    f"{document_path}: §{section_letter} UNKNOWN coverage requires the "
                    f"exact visible marker {marker!r}"
                )
            continue

        for evidence_id in coverage["evidence_ids"]:
            evidence = evidence_rows.get(evidence_id)
            if evidence is None:
                errors.append(
                    f"{document_path}: §{section_letter} references unknown evidence_id "
                    f"{evidence_id!r}"
                )
                continue
            if section_letter not in evidence["supports_sections"]:
                errors.append(
                    f"{document_path}: evidence {evidence_id!r} does not declare support "
                    f"for §{section_letter}"
                )

    receipt_id = payload.get("server_receipt_id")
    review_required = risk in {"P0", "P1"} or entry.get(
        "independent_review_required"
    ) is True
    if review_required:
        if type(receipt_id) is not str or RECEIPT_ID_RE.fullmatch(receipt_id) is None:
            errors.append(
                f"{document_path}: {risk} promotion requires an authenticated "
                "independent-review server receipt ID"
            )
        errors.append(
            f"{document_path}: trusted runbook-promotion receipt verification is not "
            "deployed; high-risk promotion is unavailable (local IDs, files, author "
            "names, and unsigned receipts are never authority)"
        )
    elif receipt_id is not None:
        errors.append(
            f"{document_path}: server_receipt_id cannot be asserted until the trusted "
            "receipt verifier is deployed"
        )
    return errors


def _load_json_schema(
    path: Path,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    if path.is_symlink() or not path.is_file():
        errors.append(f"{label} must be a regular file: {path}")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(value)
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaError) as exc:
        errors.append(f"{label} is invalid: {exc}")
        return None
    if type(value) is not dict:
        errors.append(f"{label} must be a JSON object")
        return None
    return value


def _resolve_local_evidence_blob(
    root: Path,
    document_path: str,
    evidence: dict[str, Any],
    *,
    repository: Any,
    inventory_sha: Any,
    trees: _GitTrees | None,
) -> list[str]:
    errors: list[str] = []
    evidence_id = evidence["evidence_id"]
    label = f"{document_path}: verified_against[{evidence_id}]"
    artifact_type = evidence["artifact_type"]
    locator = evidence["locator"]
    parsed_path = _safe_repository_evidence_path(locator, artifact_type, label, errors)
    if parsed_path is None:
        return errors
    if parsed_path == document_path or is_source_relative_path(parsed_path):
        errors.append(
            f"{label}: an operational Markdown source cannot verify another runbook; "
            "cite code, a test, schema, specification, or workflow"
        )
        return errors
    if type(repository) is not str or not repository:
        errors.append(f"{label}: corpus inventory repository is unavailable")
    if type(inventory_sha) is not str or HEX_OID_RE.fullmatch(inventory_sha) is None:
        errors.append(f"{label}: corpus inventory full SHA is unavailable")
        return errors
    if trees is None:
        errors.append(f"{label}: pinned Git tree is unavailable")
        return errors

    record = trees.inventory.get(parsed_path)
    if record is None:
        errors.append(
            f"{label}: locator {parsed_path!r} is not committed at the pinned "
            f"inventory SHA {inventory_sha}"
        )
        return errors
    mode, object_type, actual_oid = record
    if mode not in {"100644", "100755"} or object_type != "blob":
        errors.append(
            f"{label}: locator {parsed_path!r} is mode {mode} {object_type}, not a "
            "regular Git blob"
        )
        return errors
    if evidence["git_blob_oid"] != actual_oid:
        errors.append(
            f"{label}: declared git_blob_oid {evidence['git_blob_oid']} does not match "
            f"the pinned blob {actual_oid}"
        )

    try:
        blob_bytes = subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "-C",
                str(root),
                "cat-file",
                "blob",
                actual_oid,
            ],
            check=True,
            capture_output=True,
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        errors.append(f"{label}: cannot resolve pinned blob bytes: {exc}")
        return errors
    actual_sha256 = hashlib.sha256(blob_bytes).hexdigest()
    if evidence["content_sha256"] != actual_sha256:
        errors.append(
            f"{label}: declared content_sha256 {evidence['content_sha256']} does not "
            f"match pinned blob bytes {actual_sha256}"
        )

    working_path = root / parsed_path
    symlink_component = _symlink_component(root, parsed_path)
    if symlink_component is not None:
        errors.append(
            f"{label}: current evidence locator contains symlink component "
            f"{symlink_component!r}"
        )
        return errors
    try:
        working_stat = working_path.stat(follow_symlinks=False)
        working_bytes = working_path.read_bytes()
    except OSError as exc:
        errors.append(f"{label}: cannot read current evidence bytes: {exc}")
        return errors
    if not stat.S_ISREG(working_stat.st_mode):
        errors.append(f"{label}: current evidence locator must be a regular file")
    elif working_bytes != blob_bytes:
        errors.append(
            f"{label}: current evidence bytes differ from the pinned inventory blob; "
            "commit and refresh the content snapshot before promotion"
        )
    return errors


def _safe_repository_evidence_path(
    value: Any,
    artifact_type: str,
    label: str,
    errors: list[str],
) -> str | None:
    parsed = _nonempty_string(value, f"{label}.locator", errors)
    if parsed is None:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in parsed):
        errors.append(f"{label}.locator contains a control character")
        return None
    raw_parts = parsed.split("/")
    candidate = PurePosixPath(parsed)
    if (
        "\\" in parsed
        or candidate.is_absolute()
        or any(part in {"", ".", "..", ".git"} for part in raw_parts)
        or candidate.as_posix() != parsed
    ):
        errors.append(f"{label}.locator must be a normalized repository-relative path")
        return None
    allowed = LOCAL_EVIDENCE_ARTIFACTS.get(artifact_type)
    if allowed is None:
        errors.append(f"{label}.artifact_type is not locally resolvable")
        return None
    prefix, suffixes = allowed
    if not parsed.startswith(prefix) or not parsed.endswith(suffixes):
        errors.append(
            f"{label}.locator is not a permitted {artifact_type} path under {prefix}"
        )
        return None
    return parsed


def _load_manifest_bytes(
    payload: bytes,
    path: Path,
    errors: list[str],
) -> dict[str, Any] | None:
    try:
        value = strict_yaml_load(payload.decode("utf-8"))
    except (UnicodeError, yaml.YAMLError) as exc:
        errors.append(f"{path}: invalid strict YAML: {exc}")
        return None
    if type(value) is not dict:
        errors.append(f"{path}: manifest must be a YAML mapping")
        return None
    return value


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
    )


def _protected_manifest_projection(manifest: dict[str, Any]) -> dict[str, Any]:
    """Remove only fields the mechanical refresher is authorized to derive."""

    protected = copy.deepcopy(manifest)
    inventory = protected.get("inventory")
    if type(inventory) is dict:
        inventory.pop("inventory_sha", None)
        inventory.pop("counts", None)
    documents = protected.get("documents")
    if type(documents) is list:
        for entry in documents:
            if type(entry) is dict:
                entry.pop("git_blob_oid", None)
                entry.pop("inventory_path", None)
    return protected


def _load_manifest(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"{path}: manifest file is missing")
        return None
    try:
        value = strict_yaml_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors.append(f"{path}: invalid strict YAML: {exc}")
        return None
    if type(value) is not dict:
        errors.append(f"{path}: manifest must be a YAML mapping")
        return None
    return value


def _working_source_paths(root: Path, errors: list[str]) -> set[str]:
    try:
        selected = source_paths(root)
    except (CatalogError, OSError, ValueError) as exc:
        errors.append(f"source selector failed: {exc}")
        return set()
    result: set[str] = set()
    for path in selected:
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            errors.append(f"source selector escaped repository root: {path}")
            continue
        safe = _safe_markdown_path(
            relative, f"source selector path {relative!r}", errors
        )
        if safe is None:
            continue
        if path.is_symlink():
            errors.append(f"source selector path {relative!r} must not be a symlink")
            continue
        try:
            path.resolve().relative_to(root)
        except ValueError:
            errors.append(
                f"source selector path {relative!r} resolves outside repository root"
            )
            continue
        result.add(safe)
    return result


def _working_classifications(
    root: Path,
    selected: set[str],
    errors: list[str],
) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in sorted(selected):
        path = root / relative
        try:
            metadata = _frontmatter(path)
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{relative}: cannot classify frontmatter: {exc}")
            continue
        if metadata is None or "runbook_id" not in metadata:
            result[relative] = "grandfathered"
            continue
        if metadata.get("status") == "ACTIVE":
            result[relative] = "active"
            continue
        if metadata.get("status") == "DRAFT":
            # A DRAFT is intentionally non-authoritative. Admitting it to the
            # exhaustive ledger as grandfathered lets the content snapshot be
            # pinned before promotion without ever exposing it in the catalog.
            result[relative] = "grandfathered"
            continue
        errors.append(
            f"{relative}: catalog opt-in status {metadata.get('status')!r} is neither ACTIVE nor "
            "DRAFT"
        )
    return result


def _pinned_git_tree(
    root: Path,
    sha: str,
    label: str,
    errors: list[str],
) -> dict[str, tuple[str, str, str]] | None:
    """Return an exact commit tree without consulting replacement objects."""

    try:
        raw_tree = subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "-C",
                str(root),
                "ls-tree",
                "-r",
                "-z",
                "--full-tree",
                sha,
            ],
            check=True,
            capture_output=True,
        ).stdout
    except FileNotFoundError:
        errors.append("git executable is required to load the pinned corpus")
        return None
    except subprocess.CalledProcessError as exc:
        errors.append(
            f"cannot read {label} tree {sha}: "
            f"{exc.stderr.decode(errors='replace').strip()}"
        )
        return None
    return _parse_git_tree(raw_tree, label, errors)


def _require_pinned_ancestry(
    root: Path,
    ancestor: str,
    descendant: str,
    label: str,
    errors: list[str],
) -> None:
    try:
        completed = subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "-C",
                str(root),
                "merge-base",
                "--is-ancestor",
                ancestor,
                descendant,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        errors.append("git executable is required to verify pinned ancestry")
        return
    if completed.returncode == 1:
        errors.append(f"{label} is not an ancestor relationship")
    elif completed.returncode != 0:
        errors.append(f"cannot verify {label}: {completed.stderr.strip()}")


def _read_pinned_blob_batch(
    root: Path,
    object_ids: Sequence[str],
    *,
    per_blob_limit: int,
    aggregate_limit: int,
    label: str,
    errors: list[str],
) -> dict[str, bytes]:
    """Preflight an object batch before materializing any of its bytes."""

    reference_counts = Counter(object_ids)
    unique_ids = tuple(sorted(reference_counts))
    if not unique_ids:
        return {}
    request = "".join(f"{oid}\n" for oid in unique_ids).encode("ascii")
    try:
        checked = subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "-C",
                str(root),
                "cat-file",
                "--batch-check=%(objectname) %(objecttype) %(objectsize)",
            ],
            input=request,
            check=True,
            capture_output=True,
        ).stdout
    except FileNotFoundError:
        errors.append("git executable is required to load pinned blobs")
        return {}
    except subprocess.CalledProcessError as exc:
        errors.append(
            f"cannot preflight {label}: {exc.stderr.decode(errors='replace').strip()}"
        )
        return {}

    total = 0
    for index, line in enumerate(checked.splitlines()):
        try:
            oid, object_type, raw_size = line.decode("ascii").split(" ", 2)
            size = int(raw_size)
        except (UnicodeError, ValueError):
            errors.append(f"cannot parse {label} blob preflight row {index}")
            continue
        expected_oid = unique_ids[index] if index < len(unique_ids) else None
        if oid != expected_oid or object_type != "blob":
            errors.append(
                f"{label} object {expected_oid} resolved as {oid} {object_type}"
            )
            continue
        if size > per_blob_limit:
            errors.append(
                f"{label} blob {oid} exceeds the {per_blob_limit}-byte limit"
            )
        total += size * reference_counts[oid]
        if total > aggregate_limit:
            errors.append(
                f"{label} exceeds the {aggregate_limit}-byte aggregate limit"
            )
            break
    if len(checked.splitlines()) != len(unique_ids):
        errors.append(f"{label} blob preflight returned an incomplete object set")
    if errors:
        return {}

    try:
        materialized = subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "-C",
                str(root),
                "cat-file",
                "--batch",
            ],
            input=request,
            check=True,
            capture_output=True,
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        detail = (
            exc.stderr.decode(errors="replace").strip()
            if isinstance(exc, subprocess.CalledProcessError)
            else str(exc)
        )
        errors.append(f"cannot materialize {label}: {detail}")
        return {}

    result: dict[str, bytes] = {}
    cursor = 0
    for expected_oid in unique_ids:
        newline = materialized.find(b"\n", cursor)
        if newline < 0:
            errors.append(f"{label} batch ended before object {expected_oid}")
            break
        header = materialized[cursor:newline]
        cursor = newline + 1
        try:
            oid, object_type, raw_size = header.decode("ascii").split(" ", 2)
            size = int(raw_size)
        except (UnicodeError, ValueError):
            errors.append(f"cannot parse materialized {label} header")
            break
        if oid != expected_oid or object_type != "blob":
            errors.append(
                f"materialized {label} object {expected_oid} as {oid} {object_type}"
            )
            break
        end = cursor + size
        if end >= len(materialized) or materialized[end : end + 1] != b"\n":
            errors.append(f"materialized {label} object {oid} has invalid framing")
            break
        result[oid] = materialized[cursor:end]
        cursor = end + 1
    if cursor != len(materialized):
        errors.append(f"materialized {label} batch has trailing or incomplete bytes")
    return result


def _git_tree(
    root: Path,
    inventory_sha: str,
    base_sha: str | None,
    errors: list[str],
) -> _GitTrees | None:
    try:
        top = subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "-C",
                str(root),
                "rev-parse",
                "--show-toplevel",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if Path(top).resolve() != root:
            errors.append(f"repo_root must be the Git worktree root ({top})")
            return None
        resolved_inventory = _resolve_exact_commit(
            root, inventory_sha, "inventory.inventory_sha", errors
        )
        if resolved_inventory is None:
            return None
        if base_sha is not None:
            resolved_base = _resolve_exact_commit(
                root, base_sha, "inventory.base_sha", errors
            )
            if resolved_base is None:
                return None
            ancestry = subprocess.run(
                [
                    "git",
                    "--no-replace-objects",
                    "-C",
                    str(root),
                    "merge-base",
                    "--is-ancestor",
                    base_sha,
                    inventory_sha,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if ancestry.returncode == 1:
                errors.append(
                    f"inventory.base_sha {base_sha} is not an ancestor of "
                    f"inventory.inventory_sha {inventory_sha}"
                )
                return None
            if ancestry.returncode != 0:
                errors.append(
                    "cannot verify inventory.base_sha ancestry: "
                    f"{ancestry.stderr.strip()}"
                )
                return None
        head_sha = _resolve_commit(root, "HEAD", "checked-out HEAD", errors)
        if head_sha is None:
            return None
        head_ancestry = subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "-C",
                str(root),
                "merge-base",
                "--is-ancestor",
                inventory_sha,
                head_sha,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if head_ancestry.returncode == 1:
            errors.append(
                f"inventory.inventory_sha {inventory_sha} is not an ancestor of "
                f"checked-out HEAD {head_sha}; commit the manifest only as a descendant "
                "of its pinned content snapshot"
            )
            return None
        if head_ancestry.returncode != 0:
            errors.append(
                "cannot verify inventory.inventory_sha ancestry to checked-out HEAD: "
                f"{head_ancestry.stderr.strip()}"
            )
            return None
        raw_tree = subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "-C",
                str(root),
                "ls-tree",
                "-r",
                "-z",
                "--full-tree",
                inventory_sha,
            ],
            check=True,
            capture_output=True,
        ).stdout
        raw_head_tree = (
            raw_tree
            if head_sha == inventory_sha
            else subprocess.run(
                [
                    "git",
                    "--no-replace-objects",
                    "-C",
                    str(root),
                    "ls-tree",
                    "-r",
                    "-z",
                    "--full-tree",
                    head_sha,
                ],
                check=True,
                capture_output=True,
            ).stdout
        )
    except FileNotFoundError:
        errors.append("git executable is required to validate inventory_sha")
        return None
    except subprocess.CalledProcessError as exc:
        stderr = (
            exc.stderr.decode(errors="replace")
            if isinstance(exc.stderr, bytes)
            else exc.stderr
        )
        errors.append(
            f"cannot read inventory_sha {inventory_sha}: {(stderr or '').strip()}"
        )
        return None

    result = _parse_git_tree(raw_tree, "inventory.inventory_sha", errors)
    if result is None:
        return None
    head_tree = (
        result
        if head_sha == inventory_sha
        else _parse_git_tree(raw_head_tree, "checked-out HEAD", errors)
    )
    if head_tree is None:
        return None
    tree_views = [("inventory.inventory_sha", result)]
    if head_sha != inventory_sha:
        tree_views.append(("checked-out HEAD", head_tree))
    for label, tree in tree_views:
        for relative, (mode, object_type, _oid) in tree.items():
            if is_admitted_source_tree_path(relative) and (
                mode not in {"100644", "100755"} or object_type != "blob"
            ):
                errors.append(
                    f"{label} contains admitted path {relative!r} as mode "
                    f"{mode} {object_type}, not a regular file"
                )
    return _GitTrees(inventory=result, head=head_tree)


def _parse_git_tree(
    raw_tree: bytes,
    label: str,
    errors: list[str],
) -> dict[str, tuple[str, str, str]] | None:
    result: dict[str, tuple[str, str, str]] = {}
    try:
        for record in raw_tree.split(b"\0"):
            if not record:
                continue
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, oid = metadata.decode("ascii").split(" ", 2)
            relative = raw_path.decode("utf-8")
            result[relative] = (mode, object_type, oid)
    except (UnicodeError, ValueError) as exc:
        errors.append(f"{label} tree cannot be parsed safely: {exc}")
        return None
    return result


def _symlink_component(root: Path, relative: str) -> str | None:
    """Return the first repository-relative symlink in a path, if any."""

    current = root
    walked: list[str] = []
    for part in PurePosixPath(relative).parts:
        current /= part
        walked.append(part)
        if current.is_symlink():
            return PurePosixPath(*walked).as_posix()
    return None


def _resolve_exact_commit(
    root: Path,
    sha: str,
    label: str,
    errors: list[str],
) -> str | None:
    resolved = _resolve_commit(root, sha, f"{label} {sha}", errors)
    if resolved is None:
        return None
    if resolved != sha:
        errors.append(f"{label} resolves to {resolved}, expected exact commit {sha}")
        return None
    return resolved


def _resolve_commit(
    root: Path,
    revision: str,
    label: str,
    errors: list[str],
) -> str | None:
    try:
        resolved = subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "-C",
                str(root),
                "rev-parse",
                "--verify",
                f"{revision}^{{commit}}",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except FileNotFoundError:
        errors.append("git executable is required to validate inventory commits")
        return None
    except subprocess.CalledProcessError as exc:
        stderr = (
            exc.stderr.decode(errors="replace")
            if isinstance(exc.stderr, bytes)
            else exc.stderr
        )
        errors.append(f"cannot resolve {label} to a commit: {(stderr or '').strip()}")
        return None
    return resolved


def _working_blob_oid(path: Path, label: str, errors: list[str]) -> str | None:
    """Return the raw Git blob ID for current bytes without mutating the object DB."""

    try:
        payload = path.read_bytes()
    except OSError as exc:
        errors.append(f"{label}: cannot read current source bytes: {exc}")
        return None
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _mapping(value: Any, label: str, errors: list[str]) -> dict[str, Any] | None:
    if type(value) is not dict:
        errors.append(f"{label} must be a mapping")
        return None
    return value


def _exact_keys(
    value: dict[str, Any],
    allowed: frozenset[str],
    label: str,
    errors: list[str],
    *,
    required: frozenset[str] | None = None,
) -> None:
    actual = set(value)
    if any(type(key) is not str for key in actual):
        errors.append(f"{label} mapping keys must be strings")
    missing = sorted((required or allowed) - actual, key=str)
    unknown = sorted(actual - allowed, key=str)
    if missing:
        errors.append(f"{label} is missing fields: {', '.join(missing)}")
    if unknown:
        errors.append(f"{label} has unknown fields: {', '.join(map(str, unknown))}")


def _expect_exact(
    actual: Any,
    expected: Any,
    label: str,
    errors: list[str],
    *,
    exact_type: bool = False,
) -> None:
    if actual != expected or (exact_type and type(actual) is not type(expected)):
        errors.append(f"{label} must be {expected!r}")


def _nonempty_string(value: Any, label: str, errors: list[str]) -> str | None:
    if type(value) is not str or not value.strip() or value != value.strip():
        errors.append(f"{label} must be a non-empty, trimmed string")
        return None
    return value


def _json_string_payload_wire_bytes(value: str) -> int:
    """Return the byte width of a string inside the CLI's ASCII JSON wire form."""

    return len(json.dumps(value, ensure_ascii=True).encode("ascii")) - 2


def _validated_batch(value: Any, label: str, errors: list[str]) -> str | None:
    if type(value) is not str or BATCH_RE.fullmatch(value) is None:
        errors.append(f"{label} must be a lowercase kebab-case identifier")
        return None
    valid = True
    if len(value.encode("utf-8")) > MAX_PINNED_BATCH_BYTES:
        errors.append(f"{label} exceeds the {MAX_PINNED_BATCH_BYTES}-byte limit")
        valid = False
    if _json_string_payload_wire_bytes(value) > MAX_PINNED_BATCH_WIRE_BYTES:
        errors.append(
            f"{label} exceeds the {MAX_PINNED_BATCH_WIRE_BYTES}-byte JSON-wire limit"
        )
        valid = False
    return value if valid else None


def _validated_verify_against(
    value: Any,
    label: str,
    errors: list[str],
) -> list[str]:
    verify_against = _nonempty_string_list(value, label, errors)
    if len(verify_against) > MAX_PINNED_VERIFY_AGAINST_ITEMS:
        errors.append(
            f"{label} exceeds the {MAX_PINNED_VERIFY_AGAINST_ITEMS}-item limit"
        )
    verify_bytes = sum(len(item.encode("utf-8")) for item in verify_against)
    if verify_bytes > MAX_PINNED_VERIFY_AGAINST_BYTES:
        errors.append(
            f"{label} exceeds the {MAX_PINNED_VERIFY_AGAINST_BYTES}-byte aggregate limit"
        )
    verify_wire_bytes = sum(
        _json_string_payload_wire_bytes(item) for item in verify_against
    )
    if verify_wire_bytes > MAX_PINNED_VERIFY_AGAINST_WIRE_BYTES:
        errors.append(
            f"{label} exceeds the "
            f"{MAX_PINNED_VERIFY_AGAINST_WIRE_BYTES}-byte JSON-wire aggregate limit"
        )
    for index, item in enumerate(verify_against):
        if len(item.encode("utf-8")) > MAX_PINNED_VERIFY_AGAINST_ITEM_BYTES:
            errors.append(
                f"{label}[{index}] exceeds the "
                f"{MAX_PINNED_VERIFY_AGAINST_ITEM_BYTES}-byte limit"
            )
        if (
            _json_string_payload_wire_bytes(item)
            > MAX_PINNED_VERIFY_AGAINST_ITEM_WIRE_BYTES
        ):
            errors.append(
                f"{label}[{index}] exceeds the "
                f"{MAX_PINNED_VERIFY_AGAINST_ITEM_WIRE_BYTES}-byte JSON-wire limit"
            )
        if any(unicodedata.category(character) == "Cc" for character in item):
            errors.append(f"{label}[{index}] contains a control character")
    return verify_against


def _validated_verification_mappings(
    value: Any,
    verify_against: list[str],
    label: str,
    errors: list[str],
) -> list[PinnedVerificationMapping]:
    """Validate the closed, ordinal-aligned schema-v2 adapter projection."""

    if value is None:
        fallback_policy = {
            "minimum_receipts": 1,
            "maximum_receipts": 1,
            "freshness_seconds": 0,
            "allowed_evidence_kinds": ["git"],
            "require_remote_identity": False,
            "require_distinct_sources": False,
        }
        fallback_digest = requirement_mapping_digest(
            adapter_type="unmapped_prose",
            adapter_parameters={},
            evidence_policy=fallback_policy,
        )
        return [
            PinnedVerificationMapping(
                ordinal=index,
                mapping_digest=fallback_digest,
                adapter_type="unmapped_prose",
                adapter_parameters={},
                evidence_policy=copy.deepcopy(fallback_policy),
            )
            for index in range(1, len(verify_against) + 1)
        ]
    if type(value) is not list:
        errors.append(f"{label} must be a list when present")
        return []
    if len(value) != len(verify_against):
        errors.append(
            f"{label} must contain exactly one mapping for each verify_against item"
        )
    result: list[PinnedVerificationMapping] = []
    for index, raw_mapping in enumerate(value):
        item_label = f"{label}[{index}]"
        mapping = _mapping(raw_mapping, item_label, errors)
        if mapping is None:
            continue
        _exact_keys(mapping, VERIFICATION_MAPPING_FIELDS, item_label, errors)
        _expect_exact(
            mapping.get("schema_version"),
            2,
            f"{item_label}.schema_version",
            errors,
            exact_type=True,
        )
        ordinal = mapping.get("ordinal")
        if type(ordinal) is not int or ordinal != index + 1:
            errors.append(f"{item_label}.ordinal must equal {index + 1}")
        adapter_type = mapping.get("adapter_type")
        expected_parameter_fields = ADAPTER_PARAMETER_FIELDS.get(adapter_type)
        if expected_parameter_fields is None:
            errors.append(f"{item_label}.adapter_type is not release-frozen")
            expected_parameter_fields = frozenset()
        parameters = _mapping(
            mapping.get("adapter_parameters"),
            f"{item_label}.adapter_parameters",
            errors,
        )
        if parameters is not None:
            _exact_keys(
                parameters,
                expected_parameter_fields,
                f"{item_label}.adapter_parameters",
                errors,
            )
            _validate_adapter_parameters(
                adapter_type,
                parameters,
                f"{item_label}.adapter_parameters",
                errors,
            )
        policy = _mapping(
            mapping.get("evidence_policy"),
            f"{item_label}.evidence_policy",
            errors,
        )
        if policy is not None:
            _exact_keys(
                policy,
                EVIDENCE_POLICY_FIELDS,
                f"{item_label}.evidence_policy",
                errors,
            )
            _validate_evidence_policy(
                policy,
                f"{item_label}.evidence_policy",
                errors,
            )
        mapping_digest = mapping.get("mapping_digest")
        if type(mapping_digest) is not str or SHA256_RE.fullmatch(mapping_digest) is None:
            errors.append(f"{item_label}.mapping_digest must be lowercase 64-hex")
        if (
            type(adapter_type) is str
            and parameters is not None
            and policy is not None
        ):
            expected_digest = requirement_mapping_digest(
                adapter_type=adapter_type,
                adapter_parameters=parameters,
                evidence_policy=policy,
            )
            if mapping_digest != expected_digest:
                errors.append(
                    f"{item_label}.mapping_digest is {mapping_digest!r}, "
                    f"expected {expected_digest}"
                )
            if (
                type(ordinal) is int
                and ordinal == index + 1
                and type(mapping_digest) is str
                and SHA256_RE.fullmatch(mapping_digest) is not None
            ):
                result.append(
                    PinnedVerificationMapping(
                        ordinal=ordinal,
                        mapping_digest=mapping_digest,
                        adapter_type=adapter_type,
                        adapter_parameters=copy.deepcopy(parameters),
                        evidence_policy=copy.deepcopy(policy),
                    )
                )
    return result


def _validate_adapter_parameters(
    adapter_type: Any,
    parameters: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    if adapter_type in {"git_object_v1", "json_schema_v1", "test_result_v1"}:
        _bounded_j_string(parameters.get("repository"), 64, f"{label}.repository", errors)
        commit = parameters.get("commit_sha")
        if type(commit) is not str or HEX_OID_RE.fullmatch(commit) is None:
            errors.append(f"{label}.commit_sha must be lowercase 40-hex")
    if adapter_type in {"git_object_v1", "json_schema_v1"}:
        path = _safe_portable_path(parameters.get("path"), f"{label}.path", errors)
        if path is not None and len(path.encode("utf-8")) > MAX_PINNED_PATH_BYTES:
            errors.append(f"{label}.path exceeds the {MAX_PINNED_PATH_BYTES}-byte limit")
    if adapter_type == "git_object_v1":
        _git_oid(parameters.get("expected_object_oid"), f"{label}.expected_object_oid", errors)
    elif adapter_type == "json_schema_v1":
        _bounded_j_string(parameters.get("json_pointer"), 128, f"{label}.json_pointer", errors)
        _sha256(parameters.get("expected_value_sha256"), f"{label}.expected_value_sha256", errors)
    elif adapter_type in {"health_probe_v1", "production_probe_v1"}:
        _bounded_j_string(parameters.get("service_id"), 64, f"{label}.service_id", errors)
        _bounded_j_string(parameters.get("probe_id"), 96, f"{label}.probe_id", errors)
        _bounded_integer(parameters.get("max_age_seconds"), 0, 86_400, f"{label}.max_age_seconds", errors)
    elif adapter_type == "test_result_v1":
        _bounded_j_string(parameters.get("test_id"), 128, f"{label}.test_id", errors)
        _sha256(parameters.get("report_sha256"), f"{label}.report_sha256", errors)
    elif adapter_type == "state_read_v1":
        _bounded_j_string(parameters.get("namespace"), 64, f"{label}.namespace", errors)
        _bounded_j_string(parameters.get("entity_key"), 128, f"{label}.entity_key", errors)
        _bounded_j_string(parameters.get("field_path"), 128, f"{label}.field_path", errors)
        _sha256(parameters.get("expected_value_sha256"), f"{label}.expected_value_sha256", errors)


def _validate_evidence_policy(
    policy: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    minimum = policy.get("minimum_receipts")
    maximum = policy.get("maximum_receipts")
    _bounded_integer(minimum, 1, 4, f"{label}.minimum_receipts", errors)
    _bounded_integer(maximum, 1, 4, f"{label}.maximum_receipts", errors)
    if type(minimum) is int and type(maximum) is int and maximum < minimum:
        errors.append(f"{label}.maximum_receipts must be at least minimum_receipts")
    _bounded_integer(
        policy.get("freshness_seconds"),
        0,
        86_400,
        f"{label}.freshness_seconds",
        errors,
    )
    kinds = policy.get("allowed_evidence_kinds")
    if type(kinds) is not list or not 1 <= len(kinds) <= 4:
        errors.append(f"{label}.allowed_evidence_kinds must contain one through four items")
    else:
        recognized = all(
            type(kind) is str and kind in EVIDENCE_KINDS for kind in kinds
        )
        if not recognized or kinds != sorted(set(kinds), key=EVIDENCE_KINDS.index):
            errors.append(
                f"{label}.allowed_evidence_kinds must be unique and in frozen enum order"
            )
        for kind in kinds:
            if type(kind) is not str or kind not in EVIDENCE_KINDS:
                errors.append(f"{label}.allowed_evidence_kinds contains an unknown kind")
    for field in ("require_remote_identity", "require_distinct_sources"):
        if type(policy.get(field)) is not bool:
            errors.append(f"{label}.{field} must be a boolean")


def _bounded_j_string(
    value: Any,
    maximum: int,
    label: str,
    errors: list[str],
) -> None:
    if type(value) is not str or not value:
        errors.append(f"{label} must be a non-empty string")
    elif len(canonical_string_bytes(value)) > maximum:
        errors.append(f"{label} exceeds the {maximum}-J limit")


def _bounded_integer(
    value: Any,
    minimum: int,
    maximum: int,
    label: str,
    errors: list[str],
) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        errors.append(f"{label} must be an integer from {minimum} to {maximum}")


def _sha256(value: Any, label: str, errors: list[str]) -> None:
    if type(value) is not str or SHA256_RE.fullmatch(value) is None:
        errors.append(f"{label} must be lowercase 64-hex")


def _git_oid(value: Any, label: str, errors: list[str]) -> None:
    if type(value) is not str or re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", value) is None:
        errors.append(f"{label} must be a lowercase Git object ID")


def _nonempty_string_list(value: Any, label: str, errors: list[str]) -> list[str]:
    if type(value) is not list or not value:
        errors.append(f"{label} must be a non-empty list")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        parsed = _nonempty_string(item, f"{label}[{index}]", errors)
        if parsed is not None:
            result.append(parsed)
    return result


def _safe_markdown_path(value: Any, label: str, errors: list[str]) -> str | None:
    parsed = _safe_portable_path(value, label, errors)
    if parsed is None:
        return None
    candidate = PurePosixPath(parsed)
    if candidate.suffix.lower() != ".md":
        errors.append(f"{label} must name a Markdown file")
        return None
    return parsed


def _safe_portable_path(value: Any, label: str, errors: list[str]) -> str | None:
    parsed = _nonempty_string(value, label, errors)
    if parsed is None:
        return None
    if len(parsed.encode("utf-8")) > MAX_PINNED_PATH_BYTES:
        errors.append(f"{label} exceeds the {MAX_PINNED_PATH_BYTES}-byte limit")
        return None
    if PORTABLE_PATH_RE.fullmatch(parsed) is None:
        errors.append(f"{label} contains a character outside the portable path alphabet")
        return None
    raw_parts = parsed.split("/")
    candidate = PurePosixPath(parsed)
    if (
        candidate.is_absolute()
        or parsed.endswith("/")
        or any(part in {"", ".", "..", ".git"} for part in raw_parts)
        or candidate.as_posix() != parsed
    ):
        errors.append(f"{label} must be a normalized repository-relative path")
        return None
    return parsed


def _path_list(value: Any, label: str, errors: list[str]) -> list[str]:
    if type(value) is not list or not value:
        errors.append(f"{label} must be a non-empty list")
        return []
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        parsed = _safe_markdown_path(item, f"{label}[{index}]", errors)
        if parsed is None:
            continue
        if parsed in seen:
            errors.append(f"{label}[{index}] duplicates target path {parsed!r}")
        seen.add(parsed)
        result.append(parsed)
    return result


def _under(path: str, directory: str) -> bool:
    parts = PurePosixPath(path).parts
    return bool(parts) and parts[0] == directory


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promotion-bar", action="store_true")
    parser.add_argument(
        "--refresh-from",
        metavar="FULL_SHA",
        help="atomically refresh mechanical pins from the exact checked-out HEAD",
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.refresh_from is not None:
            if args.promotion_bar:
                parser.error("--refresh-from and --promotion-bar are mutually exclusive")
            report = refresh_corpus_manifest(
                args.repo_root,
                args.refresh_from,
                args.manifest,
            )
        else:
            report = validate_corpus_manifest(
                args.repo_root,
                args.manifest,
                promotion_bar=args.promotion_bar,
            )
    except CorpusManifestError as exc:
        for error in exc.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    action = "refreshed-and-validated" if args.refresh_from is not None else "pass"
    print(
        f"{MANIFEST_NAME}: {action}; operational_documents={report.operational_documents}; "
        f"source_documents={report.source_documents}; "
        f"active={report.active}; grandfathered={report.grandfathered}; "
        f"archived={report.archived}; pending={report.pending}; "
        f"promotion_bar={'pass' if report.promotion_bar else 'not-requested'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
