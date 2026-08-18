from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from runbook_tools.catalog.canonical_content import (
    GUIDANCE_WARNING_MESSAGE,
    WARNING_MESSAGE,
    DiscoveryHandles,
    canonical_json_bytes,
    canonical_string_bytes,
    domain_digest,
    finalize_envelope,
    finalize_verification_bundle,
    objective_digest,
    validate_opaque_handle,
    vector_reference_handle,
    verification_bundle_digest,
    verification_requirement,
)
from runbook_tools.catalog.limits import (
    PRODUCTION_LIMITS,
    CorpusLimits,
    require_production_limits,
)
from runbook_tools.catalog.model import CatalogError
from runbook_tools.catalog.sections import (
    MarkdownDocument,
    MarkdownSection,
    parse_markdown_document,
)
from runbook_tools.catalog.validator import (
    _preflight_pinned_blobs,
    load_validated_catalog,
)
from runbook_tools.corpus_manifest import (
    CorpusManifestError,
    PinnedCorpusDocument,
    PinnedCorpusManifest,
    load_pinned_corpus_manifest,
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "agent",
    "active",
    "after",
    "before",
    "current",
    "document",
    "documentation",
    "find",
    "for",
    "from",
    "handling",
    "in",
    "information",
    "of",
    "on",
    "owner",
    "or",
    "process",
    "procedure",
    "runbook",
    "system",
    "task",
    "the",
    "then",
    "through",
    "to",
    "when",
    "with",
    "without",
    "work",
}
_MAX_EXCERPT_LINES = 60
_MAX_EXCERPT_CHARS = 2400
_MAX_GUIDANCE_EXCERPT_CHARS = PRODUCTION_LIMITS.supplemental_excerpt_j
_MAX_QUERY_WIRE_CHARS = 4000
_MAX_SERIALIZED_BYTES = 40_000
_MAX_HEADING_BYTES = PRODUCTION_LIMITS.heading_j
_MAX_SECTION_ID_BYTES = PRODUCTION_LIMITS.section_id_j
_MAX_AUTHORITY_KEYS = PRODUCTION_LIMITS.authority_keys
_MAX_AUTHORITY_KEY_BYTES = PRODUCTION_LIMITS.authority_key_j
_MAX_MATCHED_TOKENS = PRODUCTION_LIMITS.matched_tokens
_MAX_MATCHED_TOKEN_BYTES = PRODUCTION_LIMITS.matched_token_j
_README_AUTHORING_HEADING = "Working on a runbook"
_MAX_BATCH_QUERIES = 2
_BATCH_EXCERPT_POOL_CHARS = PRODUCTION_LIMITS.initial_corpus_excerpt_j * 2
_MIN_BATCH_EXCERPT_CHARS = PRODUCTION_LIMITS.initial_corpus_excerpt_j
_PUBLISHED_WORST_CASE_ENVELOPE_BYTES = 32_000
_AUTHORING_ACTION_TOKENS = frozenset(
    {"author", "create", "edit", "maintain", "promote", "revise", "update", "write"}
)
_AUTHORING_ARTIFACT_TOKENS = frozenset(
    {
        "docs",
        "documentation",
        "guide",
        "guidance",
        "manual",
        "playbook",
        "procedure",
        "runbook",
        "runbooks",
    }
)
_AUTHORING_LINK_TOKENS = frozenset(
    {
        "a",
        "an",
        "authoritative",
        "clear",
        "current",
        "deployment",
        "existing",
        "new",
        "operational",
        "operator",
        "our",
        "production",
        "the",
        "their",
        "this",
    }
)
_AUTHORING_ARTIFACT_DISQUALIFIERS = frozenset(
    {
        "api",
        "backup",
        "database",
        "endpoint",
        "file",
        "health",
        "job",
        "repository",
        "server",
        "service",
        "status",
        "system",
        "table",
        "test",
        "tests",
        "tool",
    }
)
_MAX_AUTHORING_PHRASE_DISTANCE = 4

_GENERIC_INTENT_TOKENS = frozenset(
    {
        "begin",
        "check",
        "debug",
        "diagnose",
        "execute",
        "fix",
        "inspect",
        "operate",
        "operation",
        "operations",
        "recover",
        "recovery",
        "repair",
        "restore",
        "retry",
        "rollback",
        "run",
        "start",
        "verify",
    }
)


@dataclass(frozen=True, slots=True)
class _CorpusRecord:
    manifest: PinnedCorpusDocument
    catalog_entry: dict[str, Any] | None
    document: MarkdownDocument
    title: str | None


@dataclass(frozen=True, slots=True)
class _SearchUnit:
    record: _CorpusRecord
    unit_kind: str
    title: str | None
    section: MarkdownSection | None
    searchable_text: str


@dataclass(frozen=True, slots=True)
class SearchDelivery:
    """Pure runbooks output plus bounded bundles for Kóska claim persistence."""

    payload: dict[str, Any]
    text: str
    verification_bundles: dict[str, dict[str, Any]]


class SingleObjectiveSearchResult(dict[str, Any]):
    """Read-only compatibility view over one exact closed response.

    Older local callers indexed objective fields at the top level.  Section
    6.6 permits those library-fragment conveniences only when the production
    adapter cannot serialize them.  They are therefore virtual lookups: the
    underlying dict, canonical serializer, CLI, and Kóska delivery contain only
    the closed R7 envelope.
    """

    def __init__(self, payload: Mapping[str, Any], query: str):
        super().__init__(payload)
        self._query = query

    @property
    def _objective(self) -> Mapping[str, Any]:
        return dict.__getitem__(self, "results")[0]

    def __getitem__(self, key: str) -> Any:
        if key == "query":
            return self._query
        if key in self._objective:
            return self._objective[key]
        if key == "maximum_batch_queries":
            return PRODUCTION_LIMITS.batch_objectives
        if key == "worst_case_envelope_bytes":
            return 31_929
        if key == "discovery_lead_count":
            return (
                self._objective["grandfathered_qualifying_count"]
                + self._objective["archived_qualifying_count"]
            )
        if key == "discovery_leads_returned":
            return len(self._objective["discovery_leads"])
        if key == "discovery_leads_omitted_by_limit":
            return (
                self._objective["grandfathered_omitted_count"]
                + self._objective["archived_omitted_count"]
            )
        if key == "discovery_leads_omitted_by_response_budget":
            return 0
        if key == "corpus_state_counts":
            return self._compatibility_state_counts()
        return dict.__getitem__(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: object) -> bool:
        return (
            dict.__contains__(self, key)
            or key == "query"
            or key in self._objective
            or key
            in {
                "maximum_batch_queries",
                "worst_case_envelope_bytes",
                "discovery_lead_count",
                "discovery_leads_returned",
                "discovery_leads_omitted_by_limit",
                "discovery_leads_omitted_by_response_budget",
                "corpus_state_counts",
            }
        )

    def _compatibility_state_counts(self) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = {}
        rows = self._objective["candidates"] + self._objective["discovery_leads"]
        for state, wire_state in (
            ("active", "ACTIVE"),
            ("grandfathered", "grandfathered"),
            ("archived", "archived"),
        ):
            qualifying = self._objective[f"{state}_qualifying_count"]
            returned_rows = [row for row in rows if row["catalog_state"] == wire_state]
            returned_paths = {row["path"] for row in returned_rows}
            result[state] = {
                "searched_document_count": self._objective[f"{state}_searched_count"],
                "searched_section_count": 0,
                "searched_document_fallback_count": 0,
                "qualifying_document_count": qualifying,
                "qualifying_section_count": sum(
                    row["unit_kind"] == "section" for row in returned_rows
                ),
                "qualifying_document_fallback_count": sum(
                    row["unit_kind"] == "document" for row in returned_rows
                ),
                "returned_document_count": len(returned_paths),
                "returned_section_count": sum(
                    row["unit_kind"] == "section" for row in returned_rows
                ),
                "returned_document_fallback_count": sum(
                    row["unit_kind"] == "document" for row in returned_rows
                ),
                "omitted_document_count": max(0, qualifying - len(returned_paths)),
                "omitted_section_count": 0,
                "omitted_document_fallback_count": 0,
            }
        return result


HandleSupplier = Callable[[int, int], DiscoveryHandles]

_SECTION_INTENTS: dict[str, frozenset[str]] = {
    "E": frozenset(
        {
            "begin",
            "create",
            "dispatch",
            "execute",
            "invoke",
            "launch",
            "open",
            "operate",
            "run",
            "start",
            "submit",
            "resolve",
            "use",
        }
    ),
    "F": frozenset(
        {
            "check",
            "diagnose",
            "diagnostic",
            "error",
            "fail",
            "failed",
            "failure",
            "inspect",
            "isolate",
            "mismatch",
            "timeout",
            "troubleshoot",
            "verification",
            "verify",
        }
    ),
    "G": frozenset(
        {
            "fix",
            "recover",
            "recovery",
            "remediate",
            "repair",
            "restore",
            "retry",
            "rollback",
        }
    ),
    "H": frozenset(
        {
            "breaking",
            "change",
            "changing",
            "compatibility",
            "contract",
            "evolution",
            "evolve",
            "migrate",
            "redesign",
        }
    ),
}


def search_catalog(
    repo_root: Path,
    catalog_ref: str,
    query: str,
    *,
    limit: int = 3,
    handle_supplier: HandleSupplier | None = None,
    session_binding_sha256: str | None = None,
    limits: CorpusLimits = PRODUCTION_LIMITS,
) -> dict[str, Any]:
    """Return one exact closed canonical-content search envelope."""

    delivery = search_catalog_delivery(
        repo_root,
        catalog_ref,
        [query],
        limit=limit,
        handle_supplier=handle_supplier,
        session_binding_sha256=session_binding_sha256,
        limits=limits,
    )
    return SingleObjectiveSearchResult(delivery.payload, query)


def search_catalog_many(
    repo_root: Path,
    catalog_ref: str,
    queries: list[str] | tuple[str, ...],
    *,
    limit: int = 3,
    handle_supplier: HandleSupplier | None = None,
    session_binding_sha256: str | None = None,
    limits: CorpusLimits = PRODUCTION_LIMITS,
) -> dict[str, Any]:
    """Return one exact envelope for one or two objectives."""

    return search_catalog_delivery(
        repo_root,
        catalog_ref,
        queries,
        limit=limit,
        handle_supplier=handle_supplier,
        session_binding_sha256=session_binding_sha256,
        limits=limits,
    ).payload


def search_catalog_delivery(
    repo_root: Path,
    catalog_ref: str,
    queries: list[str] | tuple[str, ...],
    *,
    limit: int = 3,
    handle_supplier: HandleSupplier | None = None,
    session_binding_sha256: str | None = None,
    limits: CorpusLimits = PRODUCTION_LIMITS,
) -> SearchDelivery:
    """Build the pure payload Kóska admits unchanged as ``TextContent.text``.

    ``handle_supplier`` is the production ownership boundary: Kóska mints the
    values before calling this pure serializer.  The deterministic default is
    solely for the repository's read-only CLI/tests; its values have no
    persisted claim and therefore cannot be fetched or confirmed.
    """

    require_production_limits(limits)
    if (
        not isinstance(queries, (list, tuple))
        or not 1 <= len(queries) <= limits.batch_objectives
    ):
        raise CatalogError(
            "search queries must contain from 1 to "
            f"{limits.batch_objectives} items"
        )
    query_tokens = [_validated_query_tokens(query) for query in queries]
    _validate_limit(limit)
    binding_digest = session_binding_sha256 or hashlib.sha256(
        b"runbooks-read-only-diagnostic-session-v1"
    ).hexdigest()
    if re.fullmatch(r"[0-9a-f]{64}", binding_digest) is None:
        raise CatalogError("session_binding_sha256 must be lowercase 64-hex")
    supplier = handle_supplier or _diagnostic_handle_supplier

    # All caller-controlled failures above precede catalog, manifest, README,
    # and document reads.
    validated = load_validated_catalog(repo_root, catalog_ref)
    sha = validated.report.catalog_sha
    resolved_root = repo_root.resolve()
    manifest, snapshot = _load_corpus_snapshot(
        resolved_root,
        validated.catalog,
        sha,
    )
    guidance_document, guidance_blob_oid = _load_repository_guidance(
        resolved_root,
        sha,
    )
    source_by_path = {document.path: document for document in manifest.documents}
    raw_results: list[dict[str, Any]] = []
    for ordinal, (query, tokens) in enumerate(
        zip(queries, query_tokens, strict=True),
        start=1,
    ):
        raw_results.append(
            _search_corpus(
                sha,
                manifest,
                snapshot,
                query,
                tokens,
                excerpt_char_limit=limits.corpus_excerpt_j,
            )
        )

    selected_results = _allocate_r7_residual_excerpts(
        raw_results,
        searched_entry_count=len(snapshot),
        searched_section_count=_searched_section_count(snapshot),
        limits=limits,
    )

    results: list[dict[str, Any]] = []
    bundles: dict[str, dict[str, Any]] = {}
    for ordinal, (query, raw, selected) in enumerate(
        zip(queries, raw_results, selected_results, strict=True),
        start=1,
    ):
        objective, objective_bundles = _assemble_r6_objective(
            sha=sha,
            manifest=manifest,
            source_by_path=source_by_path,
            raw=raw,
            selected=selected,
            query=query,
            ordinal=ordinal,
            guidance=None,
            handle_supplier=supplier,
            session_binding_sha256=binding_digest,
        )
        overlap = set(bundles) & set(objective_bundles)
        if overlap:
            raise CatalogError("opaque bundle reference was reused within one response")
        bundles.update(objective_bundles)
        results.append(objective)

    dropped = sum(
        result["active_omitted_count"]
        + result["grandfathered_omitted_count"]
        + result["archived_omitted_count"]
        for result in results
    )
    envelope = {
        "schema_version": 4,
        "catalog_sha": sha,
        "manifest_sha256": manifest.manifest_sha256,
        "inventory_sha": manifest.inventory_sha,
        "results": results,
        "searched_entry_count": len(snapshot),
        "searched_section_count": _searched_section_count(snapshot),
        "complete": True,
        "response_budget_bytes": limits.response_bytes,
        "response_budget_truncated": False,
        "dropped_candidate_count": dropped,
    }
    # Fix and validate the complete corpus projection before optional README
    # guidance is even considered.  A guidance fit/omit decision is therefore
    # unable to reallocate an excerpt or alter a corpus digest.
    payload, text = finalize_envelope(
        envelope,
        maximum_bytes=limits.response_bytes,
    )
    for objective, query in zip(envelope["results"], queries, strict=True):
        guidance = _repository_authoring_guidance_candidate(
            sha,
            guidance_document,
            guidance_blob_oid,
            query,
            limits.supplemental_excerpt_j,
        )
        if guidance is None:
            continue
        objective["supplemental_guidance"] = [_r6_guidance(guidance)]
        objective["supplemental_guidance_returned"] = True
        try:
            payload, text = finalize_envelope(
                envelope,
                maximum_bytes=limits.response_bytes,
            )
        except CatalogError as exc:
            if str(exc) != "response_budget_exceeded":
                raise
            objective["supplemental_guidance"] = []
            objective["supplemental_guidance_returned"] = False
            objective["supplemental_guidance_omitted_by_response_budget"] = True
            payload, text = finalize_envelope(
                envelope,
                maximum_bytes=limits.response_bytes,
            )
    return SearchDelivery(
        payload=payload,
        text=text,
        verification_bundles=bundles,
    )


def _select_r7_mandatory_rows(raw: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Select top three globally plus the highest missing policy class."""

    candidate_pool = raw["candidates"]
    discovery_pool = raw["discovery_leads"]
    combined = sorted(
        candidate_pool + discovery_pool,
        key=lambda row: row["relevance_rank"],
    )
    selected = combined[: min(3, len(combined))]
    if candidate_pool and discovery_pool:
        selected_is_discovery = {
            row["catalog_state"] != "active" for row in selected
        }
        if len(selected_is_discovery) == 1:
            missing_discovery = not next(iter(selected_is_discovery))
            selected.append(
                next(
                    row
                    for row in combined
                    if (row["catalog_state"] != "active") == missing_discovery
                )
            )
    return sorted(selected, key=lambda row: row["relevance_rank"])


def _with_r7_excerpt_limit(
    row: Mapping[str, Any],
    maximum_j: int,
) -> dict[str, Any]:
    """Return one source-faithful prefix with reconstructed line bounds."""

    result = dict(row)
    excerpt, cropped = _truncate_json_wire(row["excerpt"], maximum_j)
    result["excerpt"] = excerpt
    result["excerpt_sha256"] = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
    result["excerpt_truncated"] = bool(row["excerpt_truncated"] or cropped)
    parts = excerpt.split("\n") if excerpt else []
    result["excerpt_end_line"] = row["excerpt_start_line"] + max(0, len(parts) - 1)
    result["excerpt_end_column_exclusive"] = len(parts[-1]) + 1 if parts else 1
    return result


def _r7_max_j_string(maximum_j: int) -> str:
    """Construct a string whose canonical JSON payload is exactly maximum_j."""

    return "\n" * (maximum_j // 2) + ("x" if maximum_j % 2 else "")


def _r7_conservative_result_bytes(row: Mapping[str, Any]) -> int:
    """Charge the larger frozen policy wrapper around one retrieval result.

    The common retrieval bytes are real.  Every policy-only value is replaced
    by its reviewed maximum, independently of the row's current catalog state.
    This shadow value is accounting only; it is never returned or persisted.
    """

    common = _r6_common_result(row)
    common.update(
        {
            "action_authority_eligible": False,
            "authority_admission": False,
            "candidate_id_eligible": False,
            "candidate_kind": "grandfathered_discovery_lead",
            "catalog_declared": False,
            "catalog_state": "grandfathered",
            "declaration_kinds": ["error_signature", "topic"],
            "integrity_only": False,
            "integrity_status": "integrity_pass_unverified",
            "semantic_verification": False,
            "score": 999999.999999,
            "status": "pending_verification",
        }
    )
    if common["unit_kind"] == "section":
        common["section_id_source"] = "legacy-derived"

    active = {
        **common,
        "authority_keys": [
            _r7_max_j_string(PRODUCTION_LIMITS.authority_key_j)
            for _ in range(PRODUCTION_LIMITS.authority_keys)
        ],
        "authority_keys_truncated": True,
        "candidate_digest": "f" * 64,
        "last_verified_at": "9999-12-31",
        "owner": "sysadmin",
        "rank": 999999,
        "runbook_id": _r7_max_j_string(64),
    }
    discovery = {
        **common,
        "discovery_digest": "f" * 64,
        "discovery_lead_id": vector_reference_handle("lead", 1),
        "historical_only": False,
        "manifest_batch": _r7_max_j_string(PRODUCTION_LIMITS.batch_id_j),
        "manifest_risk": "P3",
        "requires_ground_truth_verification": True,
        "warning": {
            "warning_id": "f" * 64,
            "code": "DISCOVERY_ONLY_NOT_VERIFIED",
            "message": WARNING_MESSAGE,
            "catalog_state": "grandfathered",
            "manifest_risk": "P3",
            "requires_ground_truth_verification": True,
            "requirement_count": PRODUCTION_LIMITS.verify_against_items,
            "verification_bundle_digest": "f" * 64,
            "verification_bundle_ref": vector_reference_handle("bundle", 1),
        },
    }
    return max(
        len(canonical_json_bytes(active)),
        len(canonical_json_bytes(discovery)),
    )


def _r7_conservative_allocation_bytes(
    raw_results: Sequence[Mapping[str, Any]],
    selected_results: Sequence[Sequence[Mapping[str, Any]]],
    *,
    searched_entry_count: int,
    searched_section_count: int,
    limits: CorpusLimits,
) -> int:
    """Measure a state-neutral maximum-policy shadow response."""

    objectives: list[dict[str, Any]] = []
    result_bytes = 0
    separator_bytes = 0
    total_qualifying = 0
    for ordinal, (raw, selected) in enumerate(
        zip(raw_results, selected_results, strict=True),
        start=1,
    ):
        qualifying = len(raw["candidates"]) + len(raw["discovery_leads"])
        total_qualifying += qualifying
        widest_count = max(999999, qualifying, searched_entry_count)
        objectives.append(
            {
                "objective_ordinal": ordinal,
                "objective_digest": "f" * 64,
                "status": "no_usable_corpus_result_response_budget",
                "discovery_status": "discovery_leads_returned_unverified",
                "authoritative_gap": False,
                "qualifying_result_count": widest_count,
                "eligible_candidate_count": widest_count,
                "eligible_candidates_returned": len(selected),
                "eligible_candidates_omitted_by_limit": widest_count,
                "eligible_candidates_omitted_by_response_budget": widest_count,
                "active_searched_count": widest_count,
                "active_qualifying_count": widest_count,
                "active_returned_count": len(selected),
                "active_omitted_count": widest_count,
                "grandfathered_searched_count": widest_count,
                "grandfathered_qualifying_count": widest_count,
                "grandfathered_returned_count": len(selected),
                "grandfathered_omitted_count": widest_count,
                "archived_searched_count": widest_count,
                "archived_qualifying_count": widest_count,
                "archived_returned_count": len(selected),
                "archived_omitted_count": widest_count,
                "candidates": [],
                "discovery_leads": [],
                "supplemental_guidance": [],
                "supplemental_guidance_returned": False,
                "supplemental_guidance_omitted_by_response_budget": False,
                "corpus_response_digest": "f" * 64,
            }
        )
        result_bytes += sum(_r7_conservative_result_bytes(row) for row in selected)
        separator_bytes += max(0, len(selected) - 1)

    widest_total = max(999999, total_qualifying)
    shadow = {
        "schema_version": 4,
        "catalog_sha": "a" * 40,
        "manifest_sha256": "b" * 64,
        "inventory_sha": "c" * 40,
        "results": objectives,
        "searched_entry_count": max(999999, searched_entry_count),
        "searched_section_count": max(999999, searched_section_count),
        "complete": True,
        "response_budget_bytes": limits.response_bytes,
        "response_budget_truncated": False,
        "dropped_candidate_count": widest_total,
        "serialized_bytes": limits.response_build_proof_bytes,
        "delivery_digest": "f" * 64,
    }
    return (
        len(canonical_json_bytes(shadow, final_newline=True))
        + result_bytes
        + separator_bytes
    )


def _allocate_r7_residual_excerpts(
    raw_results: Sequence[Mapping[str, Any]],
    *,
    searched_entry_count: int,
    searched_section_count: int,
    limits: CorpusLimits,
) -> list[list[dict[str, Any]]]:
    """Allocate initial breadth, then residual excerpt depth deterministically."""

    full = [_select_r7_mandatory_rows(raw) for raw in raw_results]
    allocated = [
        [
            _with_r7_excerpt_limit(row, limits.initial_corpus_excerpt_j)
            for row in selected
        ]
        for selected in full
    ]

    def charged() -> int:
        return _r7_conservative_allocation_bytes(
            raw_results,
            allocated,
            searched_entry_count=searched_entry_count,
            searched_section_count=searched_section_count,
            limits=limits,
        )

    if charged() > limits.response_build_proof_bytes:
        raise CatalogError("mandatory_corpus_envelope_too_large")

    for objective_index, selected in enumerate(full):
        for result_index, full_row in enumerate(selected):
            maximum = len(canonical_string_bytes(full_row["excerpt"]))
            current = len(
                canonical_string_bytes(
                    allocated[objective_index][result_index]["excerpt"]
                )
            )
            if maximum <= current:
                continue

            allocated[objective_index][result_index] = dict(full_row)
            if charged() <= limits.response_build_proof_bytes:
                continue

            lower = current
            upper = maximum
            while lower < upper:
                midpoint = (lower + upper + 1) // 2
                allocated[objective_index][result_index] = _with_r7_excerpt_limit(
                    full_row,
                    midpoint,
                )
                if charged() <= limits.response_build_proof_bytes:
                    lower = midpoint
                else:
                    upper = midpoint - 1
            allocated[objective_index][result_index] = _with_r7_excerpt_limit(
                full_row,
                lower,
            )
    return allocated


def _diagnostic_handle_supplier(
    objective_ordinal: int,
    discovery_ordinal: int,
) -> DiscoveryHandles:
    seed = objective_ordinal * 8 + discovery_ordinal
    return DiscoveryHandles(
        discovery_lead_id=vector_reference_handle("lead", seed),
        verification_bundle_ref=vector_reference_handle("bundle", seed),
    )


def _assemble_r6_objective(
    *,
    sha: str,
    manifest: PinnedCorpusManifest,
    source_by_path: Mapping[str, PinnedCorpusDocument],
    raw: dict[str, Any],
    selected: Sequence[Mapping[str, Any]],
    query: str,
    ordinal: int,
    guidance: dict[str, Any] | None,
    handle_supplier: HandleSupplier,
    session_binding_sha256: str,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    candidate_pool = raw["candidates"]
    discovery_pool = raw["discovery_leads"]
    if len(selected) > PRODUCTION_LIMITS.mandatory_results_per_objective:
        raise CatalogError("mandatory corpus selection exceeds four results")

    digest = objective_digest(query)
    candidates: list[dict[str, Any]] = []
    discoveries: list[dict[str, Any]] = []
    bundles: dict[str, dict[str, Any]] = {}
    discovery_ordinal = 0
    for row in selected:
        common = _r6_common_result(row)
        if row["catalog_state"] == "active":
            candidates.append(_r6_active_result(row, common, sha, manifest))
            continue
        discovery_ordinal += 1
        source = source_by_path[row["path"]]
        handles = handle_supplier(ordinal, discovery_ordinal)
        result, bundle = _r6_discovery_result(
            row=row,
            common=common,
            source=source,
            sha=sha,
            manifest=manifest,
            objective_digest_value=digest,
            session_binding_sha256=session_binding_sha256,
            handles=handles,
        )
        reference = result["warning"]["verification_bundle_ref"]
        if reference in bundles:
            raise CatalogError("opaque bundle reference was reused within one objective")
        bundles[reference] = bundle
        discoveries.append(result)
    candidates.sort(key=lambda row: row["relevance_rank"])
    discoveries.sort(key=lambda row: row["relevance_rank"])

    qualifying_by_state = {
        "active": len(candidate_pool),
        "grandfathered": sum(
            row["catalog_state"] == "grandfathered" for row in discovery_pool
        ),
        "archived": sum(
            row["catalog_state"] == "archived" for row in discovery_pool
        ),
    }
    returned_by_state = {
        "active": len(candidates),
        "grandfathered": sum(
            row["catalog_state"] == "grandfathered" for row in discoveries
        ),
        "archived": sum(
            row["catalog_state"] == "archived" for row in discoveries
        ),
    }
    guidance_projection = _r6_guidance(guidance) if guidance is not None else None
    result = {
        "objective_ordinal": ordinal,
        "objective_digest": digest,
        "status": (
            "candidates_returned_unverified"
            if candidate_pool
            else "no_positive_candidate_in_active_catalog"
            if discovery_pool
            else "no_relevant_result"
        ),
        "discovery_status": (
            "discovery_leads_returned_unverified"
            if discovery_pool
            else "no_qualifying_discovery_lead"
        ),
        "authoritative_gap": bool(discovery_pool and not candidate_pool),
        "qualifying_result_count": len(candidate_pool) + len(discovery_pool),
        "eligible_candidate_count": len(candidate_pool),
        "eligible_candidates_returned": len(candidates),
        "eligible_candidates_omitted_by_limit": len(candidate_pool) - len(candidates),
        "eligible_candidates_omitted_by_response_budget": 0,
        "active_searched_count": manifest.active,
        "active_qualifying_count": qualifying_by_state["active"],
        "active_returned_count": returned_by_state["active"],
        "active_omitted_count": (
            qualifying_by_state["active"] - returned_by_state["active"]
        ),
        "grandfathered_searched_count": manifest.grandfathered,
        "grandfathered_qualifying_count": qualifying_by_state["grandfathered"],
        "grandfathered_returned_count": returned_by_state["grandfathered"],
        "grandfathered_omitted_count": (
            qualifying_by_state["grandfathered"]
            - returned_by_state["grandfathered"]
        ),
        "archived_searched_count": manifest.archived,
        "archived_qualifying_count": qualifying_by_state["archived"],
        "archived_returned_count": returned_by_state["archived"],
        "archived_omitted_count": (
            qualifying_by_state["archived"] - returned_by_state["archived"]
        ),
        "candidates": candidates,
        "discovery_leads": discoveries,
        "supplemental_guidance": (
            [guidance_projection] if guidance_projection is not None else []
        ),
        "supplemental_guidance_returned": guidance_projection is not None,
        "supplemental_guidance_omitted_by_response_budget": False,
    }
    corpus_projection = {
        key: value
        for key, value in result.items()
        if key
        not in {
            "supplemental_guidance",
            "supplemental_guidance_returned",
            "supplemental_guidance_omitted_by_response_budget",
        }
    }
    result["corpus_response_digest"] = domain_digest(
        "runbook-corpus-response-v1",
        corpus_projection,
    )
    return result, bundles


def _r6_common_result(row: Mapping[str, Any]) -> dict[str, Any]:
    evidence = _r6_match_evidence(row.get("relevance_evidence", []))
    relevance_evidence = _r6_relevance_evidence(row.get("relevance_evidence", []))
    common = {
        "relevance_rank": row["relevance_rank"],
        "path": row["path"],
        "candidate_kind": row["candidate_kind"],
        "catalog_state": (
            "ACTIVE" if row["catalog_state"] == "active" else row["catalog_state"]
        ),
        "status": "ACTIVE" if row["status"] == "active" else row["status"],
        "action_authority_eligible": row["action_authority_eligible"],
        "authority_admission": row["authority_admission"],
        "candidate_id_eligible": row["candidate_id_eligible"],
        "catalog_declared": row.get("catalog_declared", False),
        "declaration_kinds": row.get("declaration_kinds", []),
        "integrity_only": row["integrity_only"],
        "integrity_status": row["integrity_status"],
        "semantic_verification": row["semantic_verification"],
        "unit_kind": row["unit_kind"],
        "document_title": row["document_title"],
        "document_title_sha256": row["document_title_sha256"],
        "document_title_truncated": row["document_title_truncated"],
        "excerpt_start_line": row["excerpt_start_line"],
        "excerpt_end_line": row["excerpt_end_line"],
        "excerpt_end_column_exclusive": row["excerpt_end_column_exclusive"],
        "excerpt": row["excerpt"],
        "excerpt_sha256": row["excerpt_sha256"],
        "excerpt_truncated": row["excerpt_truncated"],
        "match_evidence": [evidence] if evidence is not None else [],
        "relevance_evidence": relevance_evidence,
        "score": round(min(float(row["relevance_score"]), 999999.999999), 6),
        "source_blob_oid": row["source_blob_oid"],
    }
    if row["unit_kind"] == "section":
        common.update(
            {
                "heading": row["heading"],
                "heading_sha256": row["heading_sha256"],
                "heading_truncated": row["heading_truncated"],
                "heading_line": row["heading_line"],
                "section_id": row["section_id"],
                "section_id_source": row["section_id_source"],
            }
        )
    retrieval_projection = {
        key: common[key]
        for key in (
            "relevance_rank",
            "path",
            "unit_kind",
            "document_title",
            "document_title_sha256",
            "document_title_truncated",
            "excerpt_start_line",
            "excerpt_end_line",
            "excerpt_end_column_exclusive",
            "excerpt",
            "excerpt_sha256",
            "excerpt_truncated",
            "match_evidence",
            "relevance_evidence",
            "score",
            "source_blob_oid",
        )
    }
    for field in (
        "heading",
        "heading_sha256",
        "heading_truncated",
        "heading_line",
        "section_id",
        "section_id_source",
    ):
        if field in common:
            retrieval_projection[field] = common[field]
    common["retrieval_digest"] = domain_digest(
        "runbook-retrieval-v1",
        retrieval_projection,
    )
    return common


def _r6_active_result(
    row: Mapping[str, Any],
    common: dict[str, Any],
    sha: str,
    manifest: PinnedCorpusManifest,
) -> dict[str, Any]:
    result = {
        **common,
        "candidate_digest": "",
        "runbook_id": row["runbook_id"],
        "owner": row["owner"],
        "last_verified_at": row["last_verified_at"],
        "authority_keys": row["authority_keys"],
        "authority_keys_truncated": row["authority_keys_truncated"],
        "rank": row.get("rank"),
    }
    result["candidate_digest"] = domain_digest(
        "runbook-active-candidate-v1",
        {
            "catalog_sha": sha,
            "manifest_sha256": manifest.manifest_sha256,
            "inventory_sha": manifest.inventory_sha,
            **{key: value for key, value in result.items() if key != "candidate_digest"},
        },
    )
    return result


def _r6_discovery_result(
    *,
    row: Mapping[str, Any],
    common: dict[str, Any],
    source: PinnedCorpusDocument,
    sha: str,
    manifest: PinnedCorpusManifest,
    objective_digest_value: str,
    session_binding_sha256: str,
    handles: DiscoveryHandles,
) -> tuple[dict[str, Any], dict[str, Any]]:
    validate_opaque_handle(handles.discovery_lead_id)
    validate_opaque_handle(handles.verification_bundle_ref)
    if handles.discovery_lead_id == handles.verification_bundle_ref:
        raise CatalogError("lead and bundle opaque references must be distinct")
    policy_projection = {
        **common,
        "requires_ground_truth_verification": True,
        "historical_only": source.catalog_state == "archived",
        "manifest_risk": source.risk,
        "manifest_batch": source.batch,
        "catalog_sha": sha,
        "manifest_sha256": manifest.manifest_sha256,
        "inventory_sha": manifest.inventory_sha,
    }
    discovery_digest_value = domain_digest(
        "runbook-discovery-policy-v1",
        policy_projection,
    )
    requirements = []
    for prose, mapping in zip(
        source.verify_against,
        source.verification_mappings,
        strict=True,
    ):
        requirement = verification_requirement(
            ordinal=mapping.ordinal,
            prose=prose,
            path=source.path,
            manifest_sha256=manifest.manifest_sha256,
            source_blob_oid=source.git_blob_oid,
            objective_digest_value=objective_digest_value,
            session_binding_sha256=session_binding_sha256,
            catalog_sha=sha,
            inventory_sha=manifest.inventory_sha,
            adapter_type=mapping.adapter_type,
            adapter_parameters=mapping.adapter_parameters,
            evidence_policy=mapping.evidence_policy,
        )
        if requirement["mapping_digest"] != mapping.mapping_digest:
            raise CatalogError("validated manifest mapping digest changed during projection")
        requirements.append(requirement)
    bundle_digest = verification_bundle_digest(
        catalog_sha=sha,
        manifest_sha256=manifest.manifest_sha256,
        inventory_sha=manifest.inventory_sha,
        objective_digest_value=objective_digest_value,
        source_blob_oid=source.git_blob_oid,
        discovery_digest=discovery_digest_value,
        discovery_lead_id=handles.discovery_lead_id,
        verification_requirements=requirements,
    )
    warning_without_id = {
        "code": "DISCOVERY_ONLY_NOT_VERIFIED",
        "message": WARNING_MESSAGE,
        "catalog_state": source.catalog_state,
        "manifest_risk": source.risk,
        "requires_ground_truth_verification": True,
        "requirement_count": len(requirements),
        "verification_bundle_digest": bundle_digest,
        "verification_bundle_ref": handles.verification_bundle_ref,
    }
    warning = {
        "warning_id": domain_digest(
            "runbook-discovery-warning-v1",
            {
                "catalog_sha": sha,
                "manifest_sha256": manifest.manifest_sha256,
                "inventory_sha": manifest.inventory_sha,
                "discovery_digest": discovery_digest_value,
                **warning_without_id,
            },
        ),
        **warning_without_id,
    }
    result = {
        **common,
        "discovery_digest": discovery_digest_value,
        "discovery_lead_id": handles.discovery_lead_id,
        "requires_ground_truth_verification": True,
        "historical_only": source.catalog_state == "archived",
        "manifest_risk": source.risk,
        "manifest_batch": source.batch,
        "warning": warning,
    }
    bundle_envelope = {
        "schema_version": 1,
        "response_kind": "verification_bundle",
        "catalog_sha": sha,
        "manifest_sha256": manifest.manifest_sha256,
        "inventory_sha": manifest.inventory_sha,
        "objective_digest": objective_digest_value,
        "source_blob_oid": source.git_blob_oid,
        "discovery_digest": discovery_digest_value,
        "discovery_lead_id": handles.discovery_lead_id,
        "verification_bundle_ref_sha256": hashlib.sha256(
            handles.verification_bundle_ref.encode("ascii")
        ).hexdigest(),
        "verification_bundle_digest": bundle_digest,
        "requirement_count": len(requirements),
        "verification_requirements": requirements,
    }
    bundle, _ = finalize_verification_bundle(bundle_envelope)
    return result, bundle


def _r6_guidance(guidance: Mapping[str, Any]) -> dict[str, Any]:
    projection = {
        "candidate_kind": "repository_authoring_guidance",
        "supplemental": True,
        "candidate_id_eligible": False,
        "action_authority_eligible": False,
        "authority_admission": False,
        "semantic_verification": False,
        "path": "README.md",
        "catalog_sha": guidance["catalog_sha"],
        "source_blob_oid": guidance["source_blob_oid"],
        "excerpt": guidance["excerpt"],
        "excerpt_sha256": guidance["excerpt_sha256"],
        "excerpt_truncated": guidance["excerpt_truncated"],
    }
    projection["guidance_digest"] = domain_digest(
        "runbook-supplemental-guidance-v1",
        projection,
    )
    projection["warning_id"] = domain_digest(
        "runbook-supplemental-warning-v1",
        {
            "guidance_digest": projection["guidance_digest"],
            "warning_code": "SUPPLEMENTAL_GUIDANCE_NOT_AUTHORITY",
            "warning_message": GUIDANCE_WARNING_MESSAGE,
        },
    )
    projection["warning_code"] = "SUPPLEMENTAL_GUIDANCE_NOT_AUTHORITY"
    projection["warning_message"] = GUIDANCE_WARNING_MESSAGE
    return projection


def _r6_match_evidence(rows: Any) -> dict[str, Any] | None:
    if type(rows) is not list or not rows:
        return None
    row = max(rows, key=lambda value: float(value.get("weight", 0)))
    kind = {
        "exact_path": "path",
        "path": "path",
        "title": "title",
        "heading": "heading",
        "text": "excerpt",
        "exact_phrase": "excerpt",
        "structured_literal": "structured_literal",
        "exact_structured_literal": "structured_literal",
        "intent_tiebreak": "intent",
        "single_strong_token": "title",
    }.get(row.get("kind"), "excerpt")
    matched = []
    for token in row.get("matched_tokens", [])[: PRODUCTION_LIMITS.matched_tokens]:
        bounded, _ = _truncate_json_wire(token, PRODUCTION_LIMITS.matched_token_j)
        matched.append(bounded)
    value, _ = _truncate_json_wire(
        str(row.get("value", "")),
        PRODUCTION_LIMITS.match_value_j,
    )
    return {
        "kind": kind,
        "matched_tokens": matched,
        "matched_tokens_truncated": bool(row.get("matched_tokens_truncated"))
        or len(row.get("matched_tokens", [])) > len(matched),
        "value": value,
        "weight": round(min(float(row.get("weight", 0)), 9999.999999), 6),
    }


def _r6_relevance_evidence(rows: Any) -> list[str]:
    kinds = {row.get("kind") for row in rows if isinstance(row, Mapping)}
    result: list[str] = []
    for evidence in (
        "path",
        "title",
        "heading",
        "phrase",
        "structured_literal",
        "token_threshold",
        "single_strong_token",
    ):
        if evidence == "path" and kinds & {"path", "exact_path"} or evidence == "title" and "title" in kinds or evidence == "heading" and "heading" in kinds or evidence == "phrase" and "exact_phrase" in kinds or evidence == "structured_literal" and kinds & {
            "structured_literal",
            "exact_structured_literal",
        } or evidence == "single_strong_token" and "single_strong_token" in kinds:
            result.append(evidence)
    if not result or not kinds & {
        "exact_path",
        "exact_phrase",
        "exact_structured_literal",
        "single_strong_token",
    }:
        result.append("token_threshold")
    return result


def _batch_excerpt_char_limit(query_count: int) -> int:
    """Reserve useful excerpt space across objectives before adding depth."""

    return max(
        _MIN_BATCH_EXCERPT_CHARS,
        min(_MAX_EXCERPT_CHARS, _BATCH_EXCERPT_POOL_CHARS // query_count),
    )


def _load_snapshot(
    repo_root: Path,
    catalog: dict[str, Any],
    sha: str,
) -> list[tuple[dict[str, Any], MarkdownDocument]]:
    entries = [
        entry for entry in catalog["entries"] if entry.get("status") == "ACTIVE"
    ]
    paths = [entry["path"] for entry in entries]
    _preflight_pinned_blobs(repo_root, sha, paths)
    return [
        (
            entry,
            parse_markdown_document(_git_show_text(repo_root, sha, entry["path"])),
        )
        for entry in entries
    ]


def _load_corpus_snapshot(
    repo_root: Path,
    catalog: dict[str, Any],
    sha: str,
) -> tuple[PinnedCorpusManifest, list[_CorpusRecord]]:
    try:
        manifest = load_pinned_corpus_manifest(repo_root, sha)
    except CorpusManifestError as exc:
        raise CatalogError(f"pinned corpus manifest is invalid: {exc}") from exc
    catalog_by_path = {
        entry["path"]: entry
        for entry in catalog["entries"]
        if entry.get("status") == "ACTIVE"
    }
    active_paths = {
        document.path
        for document in manifest.documents
        if document.catalog_state == "active"
    }
    if active_paths != set(catalog_by_path):
        missing = sorted(active_paths - set(catalog_by_path))
        extra = sorted(set(catalog_by_path) - active_paths)
        details = []
        if missing:
            details.append("catalog_missing=" + ", ".join(missing))
        if extra:
            details.append("catalog_extra=" + ", ".join(extra))
        raise CatalogError("catalog/manifest ACTIVE path drift: " + "; ".join(details))
    snapshot: list[_CorpusRecord] = []
    for source in manifest.documents:
        document = parse_markdown_document(source.markdown)
        title = next(
            (section.heading for section in document.sections if section.level == 1),
            None,
        )
        snapshot.append(
            _CorpusRecord(
                manifest=source,
                catalog_entry=catalog_by_path.get(source.path),
                document=document,
                title=title,
            )
        )
    return manifest, snapshot


def _load_repository_guidance(
    repo_root: Path,
    sha: str,
) -> tuple[MarkdownDocument, str]:
    """Load non-authoritative repository workflow guidance from the same pin."""

    _preflight_pinned_blobs(repo_root, sha, ["README.md"])
    blob_oid = _git_blob_oid(repo_root, sha, "README.md")
    return (
        parse_markdown_document(_git_show_text(repo_root, sha, "README.md")),
        blob_oid,
    )


def _searched_section_count(snapshot: list[_CorpusRecord]) -> int:
    return sum(
        sum(section.level != 1 for section in record.document.sections)
        for record in snapshot
    )


def _search_corpus(
    sha: str,
    manifest: PinnedCorpusManifest,
    snapshot: list[_CorpusRecord],
    query: str,
    query_tokens: set[str],
    *,
    excerpt_char_limit: int = _MAX_EXCERPT_CHARS,
) -> dict[str, Any]:
    path_query = _exact_path_query(query)
    subject_tokens = query_tokens - _GENERIC_INTENT_TOKENS
    candidates: list[dict[str, Any]] = []
    discovery_leads: list[dict[str, Any]] = []

    for record in snapshot:
        matched_rows: list[tuple[_SearchUnit, float, list[dict[str, Any]]]] = []
        sections = [
            section for section in record.document.sections if section.level != 1
        ]
        for section in sections:
            unit = _SearchUnit(
                record=record,
                unit_kind="section",
                title=record.title,
                section=section,
                searchable_text=section.direct_text,
            )
            common = _common_relevance(
                unit,
                query,
                subject_tokens,
                path_query,
            )
            if common is not None and _has_section_evidence(common[1]):
                matched_rows.append((unit, common[0], common[1]))

        # Path/title is an honest document identity, not a manufactured section.
        # Use it only when no body section qualifies, or when the document has no
        # body section at all.
        if not matched_rows:
            fallback = _SearchUnit(
                record=record,
                unit_kind="document",
                title=record.title,
                section=None,
                searchable_text=" ".join(
                    value for value in (record.manifest.path, record.title) if value
                ),
            )
            common = _common_relevance(
                fallback,
                query,
                subject_tokens,
                path_query,
            )
            if common is not None:
                matched_rows.append((fallback, common[0], common[1]))

        for unit, relevance_score, relevance_evidence in matched_rows:
            item = _project_corpus_result(
                sha,
                manifest,
                unit,
                query,
                query_tokens,
                relevance_score,
                relevance_evidence,
                excerpt_char_limit,
            )
            if record.manifest.catalog_state == "active":
                candidates.append(item)
            else:
                discovery_leads.append(item)

    combined = _diversify_global_results(candidates + discovery_leads)
    relevance_ranks = {
        _result_identity(item): rank
        for rank, item in enumerate(combined, start=1)
    }
    candidates = [
        {**item, "relevance_rank": relevance_ranks[_result_identity(item)]}
        for item in candidates
    ]
    discovery_leads = [
        {**item, "relevance_rank": relevance_ranks[_result_identity(item)]}
        for item in discovery_leads
    ]

    legacy_order = sorted(
        candidates,
        key=lambda row: (
            -row["score"],
            row["path"],
            row.get("section_id", ""),
            row.get("heading_line", 0),
            row["excerpt_sha256"],
        ),
    )
    legacy_ranks = {
        _result_identity(item): rank
        for rank, item in enumerate(_diversify_candidates(legacy_order), start=1)
    }
    candidates = [
        {**item, "rank": legacy_ranks[_result_identity(item)]}
        for item in candidates
    ]
    candidates.sort(key=lambda row: row["relevance_rank"])
    discovery_leads.sort(key=lambda row: row["relevance_rank"])

    searched_counts = _searched_state_counts(snapshot)
    qualifying_counts = _qualifying_state_counts(candidates, discovery_leads)
    return {
        "catalog_sha": sha,
        "manifest_sha256": manifest.manifest_sha256,
        "inventory_sha": manifest.inventory_sha,
        "candidates": candidates,
        "discovery_leads": discovery_leads,
        "supplemental_guidance": [],
        "query": query,
        "searched_entry_count": len(snapshot),
        "searched_section_count": _searched_section_count(snapshot),
        "corpus_state_counts": _initial_state_count_envelope(
            searched_counts,
            qualifying_counts,
        ),
        "status": (
            "candidates_returned_unverified"
            if candidates
            else "no_positive_candidate_in_active_catalog"
        ),
        "discovery_status": (
            "discovery_leads_returned_unverified"
            if discovery_leads
            else "no_discovery_leads_returned"
        ),
        "authoritative_gap": bool(discovery_leads and not candidates),
    }


def _exact_path_query(query: str) -> str | None:
    stripped = query.strip()
    if not stripped.casefold().startswith("path:"):
        return None
    value = stripped[5:]
    if not value or value != value.strip():
        raise CatalogError("path query must contain one trimmed exact path")
    if any(character.isspace() for character in value):
        raise CatalogError("path query must contain one exact path without whitespace")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise CatalogError("path query contains a control character")
    if (
        len(value.encode("utf-8")) > PRODUCTION_LIMITS.path_utf8_bytes
        or re.fullmatch(r"[A-Za-z0-9._/-]+", value) is None
    ):
        raise CatalogError("path query exceeds the portable 192-byte path contract")
    parts = value.split("/")
    candidate = PurePosixPath(value)
    if (
        "\\" in value
        or candidate.is_absolute()
        or any(part in {"", ".", "..", ".git"} for part in parts)
        or candidate.as_posix() != value
        or candidate.suffix.casefold() != ".md"
    ):
        raise CatalogError("path query must be a normalized repository-relative Markdown path")
    return value


def _common_relevance(
    unit: _SearchUnit,
    query: str,
    subject_tokens: set[str],
    path_query: str | None,
) -> tuple[float, list[dict[str, Any]]] | None:
    path = unit.record.manifest.path
    if path_query is not None:
        if path_query != path:
            return None
        return 1000.0, [{"kind": "exact_path", "value": path, "weight": 1000.0}]

    section_heading = unit.section.heading if unit.section is not None else ""
    literals = _structured_literals(unit.searchable_text)
    sources = [
        ("path", path.replace("-", " "), 12.0),
        ("title", unit.title or "", 10.0),
        ("heading", section_heading, 8.0),
        ("text", unit.searchable_text, 2.0),
    ]
    sources.extend(("structured_literal", value, 7.0) for value in literals)
    projection = " ".join(value for _, value, _ in sources)
    projection_tokens = _tokens(projection)
    overlap = subject_tokens & projection_tokens
    normalized_query = _normalized_search_text(query)
    normalized_projection = _normalized_search_text(projection)
    phrase_qualified = (
        len(subject_tokens) >= 2
        and bool(normalized_query)
        and normalized_query in normalized_projection
    )
    qualifying_literals = sorted(
        literal
        for literal in literals
        if len(_TOKEN_RE.findall(literal.casefold())) >= 2
        and _normalized_search_text(literal) in normalized_query
        and bool(subject_tokens & _tokens(literal))
    )
    literal_qualified = bool(qualifying_literals)
    threshold = max(2, math.ceil(0.4 * len(subject_tokens)))
    token_qualified = len(overlap) >= threshold
    strong_token: str | None = None
    strong_value = ""
    if len(subject_tokens) == 1:
        token = next(iter(subject_tokens))
        path_value = PurePosixPath(path)
        path_identity = f"{path_value.name} {path_value.stem}"
        if token in _tokens(path_identity):
            strong_token = token
            strong_value = path
        elif token in _tokens(unit.title or ""):
            strong_token = token
            strong_value = unit.title or ""
    strong_qualified = strong_token is not None
    if not (
        phrase_qualified
        or literal_qualified
        or token_qualified
        or strong_qualified
    ):
        return None

    best_by_kind: dict[str, tuple[float, dict[str, Any]]] = {}
    denominator = max(1, len(subject_tokens))
    for kind, value, weight in sources:
        matched = sorted(subject_tokens & _tokens(value))
        if not matched:
            continue
        contribution = weight * len(matched) / denominator
        bounded_tokens = [
            _truncate_utf8(token, _MAX_MATCHED_TOKEN_BYTES)[0]
            for token in matched[:_MAX_MATCHED_TOKENS]
        ]
        row = {
            "kind": kind,
            "matched_tokens": bounded_tokens,
            "matched_tokens_truncated": (
                len(matched) > len(bounded_tokens)
                or any(
                    original != bounded
                    for original, bounded in zip(
                        matched,
                        bounded_tokens,
                        strict=False,
                    )
                )
            ),
            "value": _truncate_utf8(value, 240)[0],
            "weight": weight,
        }
        previous = best_by_kind.get(kind)
        candidate_key = (contribution, len(matched), _normalized_search_text(value))
        previous_key = (
            previous[0],
            len(previous[1].get("matched_tokens", [])),
            _normalized_search_text(previous[1]["value"]),
        ) if previous is not None else None
        if previous_key is None or candidate_key > previous_key:
            best_by_kind[kind] = (contribution, row)
    score = sum(row[0] for row in best_by_kind.values())
    evidence = [best_by_kind[kind][1] for kind in sorted(best_by_kind)]
    if phrase_qualified:
        score += 20.0
        evidence.append(
            {
                "kind": "exact_phrase",
                "value": _truncate_utf8(normalized_query, 240)[0],
                "weight": 20.0,
            }
        )
    if literal_qualified:
        score += 15.0
        evidence.append(
            {
                "kind": "exact_structured_literal",
                "value": _truncate_utf8(qualifying_literals[0], 240)[0],
                "weight": 15.0,
            }
        )
    if strong_qualified:
        score += 11.0
        evidence.append(
            {
                "kind": "single_strong_token",
                "matched_tokens": [strong_token],
                "matched_tokens_truncated": False,
                "value": strong_value,
                "weight": 11.0,
            }
        )
    # Generic intent is deliberately too small to cross a domain-score tier.
    intent_overlap = _tokens(query) & _GENERIC_INTENT_TOKENS
    if intent_overlap:
        score += min(len(intent_overlap), 4) * 0.0001
        evidence.append(
            {
                "kind": "intent_tiebreak",
                "matched_tokens": sorted(intent_overlap),
                "matched_tokens_truncated": False,
                "value": " ".join(sorted(intent_overlap)),
                "weight": 0.0001,
            }
        )
    evidence.sort(key=lambda row: (row["kind"], row["value"]))
    return round(score, 6), evidence


def _normalized_search_text(value: str) -> str:
    return " ".join(_TOKEN_RE.findall(value.casefold()))


def _has_section_evidence(evidence: list[dict[str, Any]]) -> bool:
    """Keep path/title-only matches at honest document granularity."""

    return any(
        row["kind"]
        in {"heading", "text", "structured_literal", "exact_structured_literal"}
        for row in evidence
    )


def _project_corpus_result(
    sha: str,
    manifest: PinnedCorpusManifest,
    unit: _SearchUnit,
    query: str,
    query_tokens: set[str],
    relevance_score: float,
    relevance_evidence: list[dict[str, Any]],
    excerpt_char_limit: int,
) -> dict[str, Any]:
    record = unit.record
    source = record.manifest
    section = unit.section
    full_document_title = record.title or source.path
    document_title, document_title_truncated = _truncate_json_wire(
        full_document_title,
        PRODUCTION_LIMITS.title_j,
    )
    if section is not None:
        (
            excerpt,
            start_line,
            end_line,
            end_column_exclusive,
            truncated,
        ) = _bounded_excerpt(
            unit.searchable_text,
            section,
            query_tokens,
            maximum_chars=excerpt_char_limit,
        )
        section_id = _section_id(section.heading)
        unit_identity = {
            "unit_kind": "section",
            "heading": section.heading,
            "heading_line": section.heading_line,
            "section_id": section_id,
            "excerpt_start_line": start_line,
            "excerpt_end_line": end_line,
            "excerpt_end_column_exclusive": end_column_exclusive,
        }
    else:
        raw_excerpt = record.title or source.path
        excerpt, truncated = _truncate_json_wire(
            raw_excerpt,
            excerpt_char_limit,
        )
        section_id = ""
        title_section = next(
            (
                candidate
                for candidate in record.document.sections
                if candidate.level == 1
            ),
            None,
        )
        title_line = title_section.heading_line if title_section is not None else 1
        unit_identity = {
            "unit_kind": "document",
            "excerpt_start_line": title_line,
            "excerpt_end_line": title_line,
            "excerpt_end_column_exclusive": len(excerpt) + 1,
        }
    excerpt_sha256 = hashlib.sha256(excerpt.encode()).hexdigest()
    common = {
        "catalog_sha": sha,
        "manifest_sha256": manifest.manifest_sha256,
        "inventory_sha": manifest.inventory_sha,
        "source_blob_oid": source.git_blob_oid,
        "path": source.path,
        "excerpt": excerpt,
        "excerpt_sha256": excerpt_sha256,
        "excerpt_truncated": truncated,
        "document_title": document_title,
        "document_title_sha256": hashlib.sha256(
            full_document_title.encode("utf-8")
        ).hexdigest(),
        "document_title_truncated": document_title_truncated,
        "relevance_score": relevance_score,
        "relevance_evidence": relevance_evidence,
        **unit_identity,
    }
    if source.catalog_state == "active":
        entry = record.catalog_entry
        if entry is None:
            raise CatalogError(f"ACTIVE manifest path lacks catalog entry: {source.path}")
        declarations = _matching_declarations(entry, section) if section is not None else []
        if declarations:
            explicit_ids = {
                row["section_id"] for _, row in declarations if "section_id" in row
            }
            if explicit_ids:
                common["section_id"] = min(explicit_ids)
                common["section_id_source"] = "catalog"
            else:
                common["section_id_source"] = "legacy-derived"
        elif section is not None:
            common["section_id_source"] = "legacy-derived"
        authority_keys, authority_keys_truncated = _bounded_authority_keys(declarations)
        legacy_sources = _entry_sources(entry)
        legacy_sources.extend(
            [
                ("heading", section.heading if section is not None else (record.title or ""), 8.0),
                ("excerpt", excerpt, 2.0),
            ]
        )
        for kind, row in declarations:
            if kind == "topic":
                legacy_sources.append(("topic", row["topic"].replace("-", " "), 9.0))
            else:
                legacy_sources.append(("error_signature", row["signature"], 10.0))
        legacy_score, legacy_evidence = _score_sources(
            query,
            query_tokens,
            legacy_sources,
        )
        digest_section = common.get("section_id", "document")
        candidate_digest = hashlib.sha256(
            "\0".join(
                (
                    sha,
                    entry["runbook_id"],
                    digest_section,
                    str(common.get("heading_line", 0)),
                    excerpt_sha256,
                )
            ).encode()
        ).hexdigest()
        candidate = {
            **common,
            "action_authority_eligible": entry["action_authority_eligible"],
            "authority_admission": entry["authority_admission"],
            "candidate_digest": candidate_digest,
            "candidate_id_eligible": True,
            "candidate_kind": (
                "active_catalog_section"
                if section is not None
                else "active_catalog_document"
            ),
            "catalog_declared": bool(declarations),
            "catalog_state": "active",
            "status": "active",
            "declaration_kinds": sorted({kind for kind, _ in declarations}),
            "integrity_only": entry["integrity_only"],
            "integrity_status": entry["integrity_status"],
            "authority_keys": authority_keys,
            "authority_keys_truncated": authority_keys_truncated,
            "last_verified_at": entry["last_verified_at"],
            "match_evidence": legacy_evidence,
            "owner": entry["owner"],
            "runbook_id": entry["runbook_id"],
            "score": round(legacy_score, 6),
            "semantic_verification": entry["semantic_verification"],
        }
        if section is not None:
            heading, heading_truncated = _bounded_display_value(
                section.heading,
                _MAX_HEADING_BYTES,
            )
            candidate.update(
                {
                    "heading": heading,
                    "heading_sha256": hashlib.sha256(section.heading.encode()).hexdigest(),
                    "heading_truncated": heading_truncated,
                }
            )
        return candidate

    digest_payload = {
        "digest_domain": "runbook-discovery-v1",
        "catalog_sha": sha,
        "manifest_sha256": manifest.manifest_sha256,
        "inventory_sha": manifest.inventory_sha,
        "source_blob_oid": source.git_blob_oid,
        "path": source.path,
        "catalog_state": source.catalog_state,
        "status": source.status,
        "risk": source.risk,
        "batch": source.batch,
        "verify_against": list(source.verify_against),
        "excerpt_sha256": excerpt_sha256,
        "unit_identity": unit_identity,
    }
    lead = {
        **common,
        "candidate_kind": (
            "grandfathered_discovery_lead"
            if source.catalog_state == "grandfathered"
            else "archived_discovery_lead"
        ),
        "catalog_state": source.catalog_state,
        "status": source.status,
        "candidate_id_eligible": False,
        "action_authority_eligible": False,
        "authority_admission": False,
        "integrity_only": True,
        "integrity_status": "integrity_pass_unverified",
        "semantic_verification": False,
        "requires_ground_truth_verification": True,
        "historical_only": source.catalog_state == "archived",
        "risk": source.risk,
        "batch": source.batch,
        "verify_against": list(source.verify_against),
        "verification_mappings": source.verification_mappings,
        "discovery_digest": hashlib.sha256(_canonical_json(digest_payload)).hexdigest(),
    }
    if section is not None:
        heading, heading_truncated = _bounded_display_value(
            section.heading,
            _MAX_HEADING_BYTES,
        )
        lead.update(
            {
                "heading": heading,
                "heading_sha256": hashlib.sha256(section.heading.encode()).hexdigest(),
                "heading_truncated": heading_truncated,
                "section_id_source": "legacy-derived",
            }
        )
    return lead


def _result_identity(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        item["path"],
        item["unit_kind"],
        item.get("section_id", ""),
        item.get("heading_line", 0),
        item["excerpt_sha256"],
    )


def _global_result_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        -item["relevance_score"],
        item["path"],
        item["unit_kind"],
        item.get("section_id", ""),
        item.get("heading_line", 0),
        item["excerpt_sha256"],
    )


def _diversify_global_results(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ordered = sorted(items, key=_global_result_sort_key)
    first: list[dict[str, Any]] = []
    remainder: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for item in ordered:
        if item["path"] in seen_paths:
            remainder.append(item)
        else:
            seen_paths.add(item["path"])
            first.append(item)
    return first + remainder


def _searched_state_counts(
    snapshot: list[_CorpusRecord],
) -> dict[str, dict[str, int]]:
    result = {
        state: {
            "searched_document_count": 0,
            "searched_section_count": 0,
            "searched_document_fallback_count": 0,
        }
        for state in ("active", "grandfathered", "archived")
    }
    for record in snapshot:
        state = record.manifest.catalog_state
        sections = sum(section.level != 1 for section in record.document.sections)
        result[state]["searched_document_count"] += 1
        result[state]["searched_section_count"] += sections
        result[state]["searched_document_fallback_count"] += int(sections == 0)
    return result


def _qualifying_state_counts(
    candidates: list[dict[str, Any]],
    discovery_leads: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    result = {
        state: {
            "qualifying_document_count": 0,
            "qualifying_section_count": 0,
            "qualifying_document_fallback_count": 0,
        }
        for state in ("active", "grandfathered", "archived")
    }
    for state, counts in result.items():
        rows = [
            row
            for row in candidates + discovery_leads
            if row["catalog_state"] == state
        ]
        counts["qualifying_document_count"] = len({row["path"] for row in rows})
        counts["qualifying_section_count"] = sum(
            row["unit_kind"] == "section" for row in rows
        )
        counts["qualifying_document_fallback_count"] = sum(
            row["unit_kind"] == "document" for row in rows
        )
    return result


def _initial_state_count_envelope(
    searched: dict[str, dict[str, int]],
    qualifying: dict[str, dict[str, int]],
) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for state in ("active", "grandfathered", "archived"):
        result[state] = {
            **searched[state],
            **qualifying[state],
            "returned_document_count": 0,
            "returned_section_count": 0,
            "returned_document_fallback_count": 0,
            "omitted_document_count": qualifying[state]["qualifying_document_count"],
            "omitted_section_count": qualifying[state]["qualifying_section_count"],
            "omitted_document_fallback_count": qualifying[state][
                "qualifying_document_fallback_count"
            ],
        }
    return result


def _search_snapshot(
    sha: str,
    snapshot: list[tuple[dict[str, Any], MarkdownDocument]],
    query: str,
    query_tokens: set[str],
    *,
    excerpt_char_limit: int = _MAX_EXCERPT_CHARS,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    searched_section_count = 0
    for entry, document in snapshot:
        entry_sources = _entry_sources(entry)
        section_rows: list[
            tuple[
                MarkdownSection,
                list[tuple[str, dict[str, Any]]],
                str,
                str,
                str,
                int,
                int,
                int,
                bool,
                list[tuple[str, str, float]],
                float,
            ]
        ] = []
        for section in document.sections:
            if section.level == 1:
                continue
            searched_section_count += 1
            declarations = _matching_declarations(entry, section)
            explicit_ids = {
                row["section_id"]
                for _, row in declarations
                if "section_id" in row
            }
            if explicit_ids:
                section_id = min(explicit_ids)
                section_id_source = "catalog"
            else:
                section_id = _section_id(section.heading)
                section_id_source = "legacy-derived"

            searchable_text = section.text if declarations else section.direct_text
            (
                excerpt,
                start_line,
                end_line,
                end_column_exclusive,
                truncated,
            ) = _bounded_excerpt(
                searchable_text,
                section,
                query_tokens,
                maximum_chars=excerpt_char_limit,
            )
            section_sources = _section_sources(
                section,
                excerpt,
                searchable_text,
                declarations,
                query_tokens,
            )
            section_score, _ = _score_sources(query, query_tokens, section_sources)
            section_rows.append(
                (
                    section,
                    declarations,
                    section_id,
                    section_id_source,
                    excerpt,
                    start_line,
                    end_line,
                    end_column_exclusive,
                    truncated,
                    section_sources,
                    section_score,
                )
            )

        if not section_rows:
            continue
        selected_index = _selected_section_index(entry, section_rows)
        for index, row in enumerate(section_rows):
            (
                section,
                declarations,
                section_id,
                section_id_source,
                excerpt,
                start_line,
                end_line,
                end_column_exclusive,
                truncated,
                section_sources,
                _,
            ) = row
            sources = list(section_sources)
            if index == selected_index:
                sources.extend(entry_sources)
            score, evidence = _score_sources(query, query_tokens, sources)
            if score <= 0:
                continue
            excerpt_bytes = excerpt.encode()
            excerpt_sha256 = hashlib.sha256(excerpt_bytes).hexdigest()
            heading, heading_truncated = _bounded_display_value(
                section.heading,
                _MAX_HEADING_BYTES,
            )
            authority_keys, authority_keys_truncated = _bounded_authority_keys(
                declarations
            )
            candidate_digest = hashlib.sha256(
                "\0".join(
                    (
                        sha,
                        entry["runbook_id"],
                        section_id,
                        str(section.heading_line),
                        excerpt_sha256,
                    )
                ).encode()
            ).hexdigest()
            candidates.append(
                {
                    "action_authority_eligible": entry[
                        "action_authority_eligible"
                    ],
                    "authority_admission": entry["authority_admission"],
                    "candidate_digest": candidate_digest,
                    "candidate_id_eligible": True,
                    "candidate_kind": "active_catalog_section",
                    "catalog_declared": bool(declarations),
                    "declaration_kinds": sorted({kind for kind, _ in declarations}),
                    "excerpt": excerpt,
                    "excerpt_end_column_exclusive": end_column_exclusive,
                    "excerpt_end_line": end_line,
                    "excerpt_sha256": excerpt_sha256,
                    "excerpt_start_line": start_line,
                    "excerpt_truncated": truncated,
                    "heading": heading,
                    "heading_sha256": hashlib.sha256(
                        section.heading.encode()
                    ).hexdigest(),
                    "heading_truncated": heading_truncated,
                    "heading_line": section.heading_line,
                    "integrity_only": entry["integrity_only"],
                    "integrity_status": entry["integrity_status"],
                    "authority_keys": authority_keys,
                    "authority_keys_truncated": authority_keys_truncated,
                    "last_verified_at": entry["last_verified_at"],
                    "match_evidence": evidence,
                    "owner": entry["owner"],
                    "path": entry["path"],
                    "runbook_id": entry["runbook_id"],
                    "score": round(score, 6),
                    "semantic_verification": entry["semantic_verification"],
                    "section_id": section_id,
                    "section_id_source": section_id_source,
                }
            )

    candidates.sort(
        key=lambda row: (
            -row["score"],
            row["runbook_id"],
            row["section_id"],
            row["heading_line"],
            row["excerpt_sha256"],
        )
    )
    candidates = _diversify_candidates(candidates)
    candidates = [
        {**candidate, "rank": rank}
        for rank, candidate in enumerate(candidates, start=1)
    ]
    return {
        "catalog_sha": sha,
        "candidates": candidates,
        "query": query,
        "searched_entry_count": len(snapshot),
        "searched_section_count": searched_section_count,
        "status": (
            "candidates_returned_unverified"
            if candidates
            else "no_positive_candidate_in_active_catalog"
        ),
    }


def _repository_authoring_guidance_candidate(
    sha: str,
    document: MarkdownDocument,
    source_blob_oid: str,
    query: str,
    excerpt_char_limit: int,
) -> dict[str, Any] | None:
    """Return supplemental pinned README context for a local authoring phrase.

    README guidance is deliberately labeled non-authoritative and ineligible for
    a future consultation ID. It closes the cold-start usability gap without
    pretending that a non-ACTIVE document is catalog authority.
    """

    section = next(
        (
            item
            for item in document.sections
            if item.level == 2 and item.heading == _README_AUTHORING_HEADING
        ),
        None,
    )
    if section is None:
        return None
    guidance_intent_tokens = _authoring_intent_tokens(query)
    if not guidance_intent_tokens:
        return None
    raw_query_tokens = {
        token for token in _TOKEN_RE.findall(query.casefold()) if len(token) > 1
    }

    excerpt, start_line, end_line, end_column, truncated = _bounded_excerpt(
        section.text,
        section,
        raw_query_tokens,
        maximum_chars=excerpt_char_limit,
    )
    score, evidence = _score_sources(
        query,
        raw_query_tokens,
        [
            (
                "repository_guidance_intent",
                " ".join(guidance_intent_tokens),
                12.0,
            ),
            ("heading", section.heading, 8.0),
            ("excerpt", excerpt, 2.0),
        ],
    )
    if score <= 0:
        return None
    excerpt_sha256 = hashlib.sha256(excerpt.encode()).hexdigest()
    guidance_digest = hashlib.sha256(
        _canonical_json(
            {
                "digest_domain": "runbook-supplemental-guidance-v1",
                "catalog_sha": sha,
                "source_blob_oid": source_blob_oid,
                "excerpt_sha256": excerpt_sha256,
            }
        )
    ).hexdigest()
    candidate = {
        "catalog_sha": sha,
        "source_blob_oid": source_blob_oid,
        "action_authority_eligible": False,
        "authority_admission": False,
        "candidate_id_eligible": False,
        "candidate_kind": "supplemental_repository_guidance",
        "catalog_declared": False,
        "declaration_kinds": [],
        "excerpt": excerpt,
        "excerpt_end_column_exclusive": end_column,
        "excerpt_end_line": end_line,
        "excerpt_sha256": excerpt_sha256,
        "excerpt_start_line": start_line,
        "excerpt_truncated": truncated,
        "heading": section.heading,
        "heading_line": section.heading_line,
        "heading_sha256": hashlib.sha256(section.heading.encode()).hexdigest(),
        "heading_truncated": False,
        "integrity_only": True,
        "integrity_status": "integrity_pass_unverified",
        "match_evidence": evidence,
        "path": "README.md",
        "score": round(score, 6),
        "semantic_verification": False,
        "supplemental": True,
        "guidance_digest": guidance_digest,
    }
    return candidate


def _authoring_intent_tokens(query: str) -> list[str]:
    """Match one local action→artifact phrase, never cross-clause co-occurrence."""

    for clause in re.split(r"[\n,;:.!?]+", query.casefold()):
        tokens = _TOKEN_RE.findall(clause)
        for artifact_index, artifact in enumerate(tokens):
            if artifact not in _AUTHORING_ARTIFACT_TOKENS:
                continue
            if (
                artifact_index + 1 < len(tokens)
                and tokens[artifact_index + 1]
                in _AUTHORING_ARTIFACT_DISQUALIFIERS
            ):
                continue
            lower_bound = max(0, artifact_index - _MAX_AUTHORING_PHRASE_DISTANCE)
            for action_index in range(artifact_index - 1, lower_bound - 1, -1):
                action = tokens[action_index]
                if action not in _AUTHORING_ACTION_TOKENS:
                    continue
                between = tokens[action_index + 1 : artifact_index]
                if all(token in _AUTHORING_LINK_TOKENS for token in between):
                    return [action, artifact]
    return []


def _refresh_result_status(
    result: dict[str, Any],
) -> None:
    candidates = result["candidates"]
    discovery_leads = result["discovery_leads"]
    if candidates:
        result["status"] = "candidates_returned_unverified"
    elif result["eligible_candidate_count"]:
        result["status"] = "no_usable_candidate_id_response_budget"
    else:
        result["status"] = "no_positive_candidate_in_active_catalog"
    result["discovery_status"] = (
        "discovery_leads_returned_unverified"
        if discovery_leads
        else "no_discovery_leads_returned"
    )
    result["authoritative_gap"] = bool(discovery_leads and not candidates)


def _matching_declarations(
    entry: dict[str, Any],
    section: MarkdownSection,
) -> list[tuple[str, dict[str, Any]]]:
    declarations: list[tuple[str, dict[str, Any]]] = []
    for kind, rows in (
        ("topic", entry["authoritative_for"]),
        ("error_signature", entry["error_signatures"]),
    ):
        declarations.extend(
            (kind, row)
            for row in rows
            if _declaration_matches(row, section)
        )
    return declarations


def _declaration_matches(row: dict[str, Any], section: MarkdownSection) -> bool:
    if row["section"] != section.heading:
        return False
    section_id = row.get("section_id")
    return section_id is None or section.adjacent_anchor_id == section_id


def _authority_key(kind: str, row: dict[str, Any]) -> str:
    key = row["topic"] if kind == "topic" else row["signature"]
    return f"{kind}:{key}"


def _validated_query_tokens(query: str) -> set[str]:
    if not isinstance(query, str) or not query.strip():
        raise CatalogError("search query must be a non-empty string")
    if len(canonical_string_bytes(query)) > _MAX_QUERY_WIRE_CHARS:
        raise CatalogError(
            "search query canonical JSON-string payload must not exceed "
            f"{_MAX_QUERY_WIRE_CHARS} bytes"
        )
    tokens = _tokens(query)
    if not tokens:
        raise CatalogError("search query must contain at least one searchable token")
    return tokens


def _validate_limit(limit: int) -> None:
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 3:
        raise CatalogError("search limit must be an integer from 1 to 3")


def _entry_sources(entry: dict[str, Any]) -> list[tuple[str, str, float]]:
    sources: list[tuple[str, str, float]] = [
        ("runbook_id", entry["runbook_id"].replace("-", " "), 9.0),
        ("path", entry["path"].replace("-", " "), 4.0),
        ("domain", entry["domain"].replace("-", " "), 4.0),
    ]
    sources.extend(
        ("alias", value.replace("-", " "), 9.0) for value in entry["aliases"]
    )
    sources.extend(
        ("topic", row["topic"].replace("-", " "), 8.0)
        for row in entry["authoritative_for"]
    )
    return sources


def _section_sources(
    section: MarkdownSection,
    excerpt: str,
    searchable_text: str,
    declarations: list[tuple[str, dict[str, Any]]],
    query_tokens: set[str],
) -> list[tuple[str, str, float]]:
    sources: list[tuple[str, str, float]] = [
        ("heading", section.heading, 8.0),
        ("excerpt", excerpt, 2.0),
    ]
    for kind, row in declarations:
        if kind == "topic":
            sources.append(("topic", row["topic"].replace("-", " "), 9.0))
        else:
            sources.append(("error_signature", row["signature"], 10.0))
    sources.extend(
        ("structured_literal", literal, 7.0)
        for literal in _structured_literals(searchable_text)
    )
    section_letter = _section_letter(section.heading)
    intent_tokens = _SECTION_INTENTS.get(section_letter or "", frozenset())
    matched_intents = sorted(query_tokens & intent_tokens)
    has_candidate_evidence = any(
        query_tokens & _tokens(value)
        for _, value, _ in sources
    )
    if matched_intents and has_candidate_evidence:
        sources.append(("intent", " ".join(matched_intents), 80.0))
    return sources


def _score_sources(
    query: str,
    query_tokens: set[str],
    sources: list[tuple[str, str, float]],
) -> tuple[float, list[dict[str, Any]]]:
    normalized_query = " ".join(_TOKEN_RE.findall(query.casefold()))
    best_by_kind: dict[str, tuple[float, dict[str, Any]]] = {}
    for kind, value, weight in sources:
        source_tokens = _tokens(value)
        overlap = sorted(query_tokens & source_tokens)
        if not overlap:
            continue
        contribution = (
            weight * len(overlap)
            if kind == "intent"
            else weight * len(overlap) / len(query_tokens)
        )
        normalized_value = " ".join(_TOKEN_RE.findall(value.casefold()))
        if kind != "intent" and len(source_tokens) > 1 and normalized_query and (
            normalized_query in normalized_value or normalized_value in normalized_query
        ):
            contribution += weight
        bounded_tokens = [
            _truncate_utf8(token, _MAX_MATCHED_TOKEN_BYTES)[0]
            for token in overlap[:_MAX_MATCHED_TOKENS]
        ]
        evidence = {
            "kind": kind,
            "matched_tokens": bounded_tokens,
            "matched_tokens_truncated": len(overlap) > len(bounded_tokens),
            "value": _truncate_utf8(value, 240)[0],
            "weight": weight,
        }
        previous = best_by_kind.get(kind)
        candidate_key = (
            contribution,
            len(overlap),
            normalized_value,
        )
        previous_key = (
            previous[0],
            len(previous[1]["matched_tokens"]),
            " ".join(_TOKEN_RE.findall(previous[1]["value"].casefold())),
        ) if previous is not None else None
        if previous_key is None or candidate_key > previous_key:
            best_by_kind[kind] = (contribution, evidence)
    score = sum(value[0] for value in best_by_kind.values())
    evidence = [best_by_kind[kind][1] for kind in sorted(best_by_kind)]
    return score, evidence


def _structured_literals(text: str) -> list[str]:
    literals: set[str] = set()
    for match in re.finditer(r"`([^`\n]{1,240})`", text):
        literals.add(match.group(1).strip())
    for match in re.finditer(
        r"(?m)^[ \t]*(?:tool_or_endpoint|repair_entry_point|action|mode|tool|"
        r"endpoint|verification)[ \t]*:[ \t]*([^\n]{1,240})$",
        text,
    ):
        literals.add(match.group(1).strip())
    return sorted(value for value in literals if value)[:64]


def _section_letter(heading: str) -> str | None:
    match = re.match(r"^§([A-K])(?:\.|\b)", heading)
    return match.group(1) if match is not None else None


def _section_selection_key(row: tuple[Any, ...]) -> tuple[Any, ...]:
    section = row[0]
    section_score = row[-1]
    preferred_order = {"E": 0, "F": 1, "G": 2, "H": 3}
    letter = _section_letter(section.heading)
    return (
        -section_score,
        preferred_order.get(letter or "", 4),
        section.heading_line,
        section.heading,
    )


def _selected_section_index(
    entry: dict[str, Any],
    section_rows: list[tuple[Any, ...]],
) -> int:
    """Choose lexical/intent evidence first, then an honest catalog fallback.

    Entry-wide identity evidence does not itself identify a section. When every
    section has zero evidence, route that evidence to the first declared
    authority instead of manufacturing an operational §E match. This is a
    fallback only: any positive section evidence still wins normally.
    """

    if any(row[-1] > 0 for row in section_rows):
        return min(
            range(len(section_rows)),
            key=lambda index: _section_selection_key(section_rows[index]),
        )

    authorities = entry.get("authoritative_for")
    if isinstance(authorities, list):
        for authority in authorities:
            if not isinstance(authority, dict):
                continue
            for index, row in enumerate(section_rows):
                if _declaration_matches(authority, row[0]):
                    return index

    declared = [
        index for index, row in enumerate(section_rows) if bool(row[1])
    ]
    if declared:
        return min(declared, key=lambda index: section_rows[index][0].heading_line)
    return min(
        range(len(section_rows)),
        key=lambda index: _section_selection_key(section_rows[index]),
    )


def _diversify_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    best: list[dict[str, Any]] = []
    remainder: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        runbook_id = candidate["runbook_id"]
        if runbook_id in seen:
            remainder.append(candidate)
        else:
            seen.add(runbook_id)
            best.append(candidate)
    return best + remainder


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(value.casefold())
        if len(token) > 1 and token not in _STOP_WORDS
    }


def _section_id(heading: str) -> str:
    normalized = heading.casefold().replace("§", "")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    normalized = normalized or "document"
    if len(normalized.encode()) <= _MAX_SECTION_ID_BYTES:
        return normalized
    suffix = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    prefix, _ = _truncate_utf8(
        normalized,
        _MAX_SECTION_ID_BYTES - len(suffix) - 1,
    )
    return f"{prefix.rstrip('-')}-{suffix}"


def _truncate_utf8(value: str, maximum_bytes: int) -> tuple[str, bool]:
    encoded = value.encode("utf-8")
    if len(encoded) <= maximum_bytes:
        return value, False
    return encoded[:maximum_bytes].decode("utf-8", errors="ignore"), True


def _truncate_json_wire(value: str, maximum_chars: int) -> tuple[str, bool]:
    """Bound one string by its actual ``json.dumps`` payload width."""

    if len(json.dumps(value, ensure_ascii=True)) - 2 <= maximum_chars:
        return value, False
    lower = 0
    upper = len(value)
    while lower < upper:
        midpoint = (lower + upper + 1) // 2
        if (
            len(json.dumps(value[:midpoint], ensure_ascii=True)) - 2
            <= maximum_chars
        ):
            lower = midpoint
        else:
            upper = midpoint - 1
    return value[:lower], True


def _bounded_display_value(value: str, maximum: int) -> tuple[str, bool]:
    """Bound a displayed identity by UTF-8 bytes and JSON wire characters."""

    bounded, byte_truncated = _truncate_utf8(value, maximum)
    bounded, wire_truncated = _truncate_json_wire(bounded, maximum)
    return bounded, byte_truncated or wire_truncated


def _bounded_authority_keys(
    declarations: list[tuple[str, dict[str, Any]]],
) -> tuple[list[str], bool]:
    raw = sorted({_authority_key(kind, row) for kind, row in declarations})
    result: list[str] = []
    truncated = len(raw) > _MAX_AUTHORITY_KEYS
    for value in raw[:_MAX_AUTHORITY_KEYS]:
        bounded, was_truncated = _truncate_utf8(value, _MAX_AUTHORITY_KEY_BYTES)
        result.append(bounded)
        truncated = truncated or was_truncated
    return result, truncated


def _bounded_excerpt(
    searchable_text: str,
    section: MarkdownSection,
    query_tokens: set[str],
    *,
    maximum_chars: int = _MAX_EXCERPT_CHARS,
) -> tuple[str, int, int, int, bool]:
    lines = searchable_text.splitlines()
    best_index = 0
    best_overlap = 0
    for index, line in enumerate(lines):
        overlap = len(query_tokens & _tokens(line))
        if overlap > best_overlap:
            best_index = index
            best_overlap = overlap

    excluded_offsets = {
        line_number - section.heading_line
        for line_number in section.excluded_line_numbers
        if section.heading_line <= line_number < section.heading_line + len(lines)
    }
    segment_start = max(
        (offset + 1 for offset in excluded_offsets if offset < best_index),
        default=0,
    )
    segment_end = min(
        (offset for offset in excluded_offsets if offset > best_index),
        default=len(lines),
    )
    start = max(segment_start, best_index - 8)
    if segment_end - start < _MAX_EXCERPT_LINES:
        start = max(segment_start, segment_end - _MAX_EXCERPT_LINES)
    end = min(segment_end, start + _MAX_EXCERPT_LINES)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    excerpt = "\n".join(lines[start:end])
    cropped_by_chars = len(excerpt) > maximum_chars
    if cropped_by_chars:
        excerpt = excerpt[:maximum_chars]
    excerpt, cropped_by_wire = _truncate_json_wire(excerpt, maximum_chars)
    excerpt_parts = excerpt.split("\n") if excerpt else []
    excerpt_line_count = len(excerpt_parts)
    start_line = section.heading_line + start
    end_line = start_line + max(0, excerpt_line_count - 1)
    end_column_exclusive = len(excerpt_parts[-1]) + 1 if excerpt_parts else 1
    truncated = (
        start > 0
        or end < len(lines)
        or bool(excluded_offsets)
        or cropped_by_chars
        or cropped_by_wire
    )
    return excerpt, start_line, end_line, end_column_exclusive, truncated


def _finalize_response(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["serialized_bytes"] = _response_size_with_digest(result)
    digest_payload = dict(result)
    digest_payload.pop("delivery_digest", None)
    result["delivery_digest"] = hashlib.sha256(
        _canonical_json(digest_payload)
    ).hexdigest()
    wire = _cli_wire_json(result)
    if len(wire.encode()) != result["serialized_bytes"]:
        raise CatalogError("search response serialized byte count is unstable")
    if len(wire.encode()) > _MAX_SERIALIZED_BYTES or len(wire) > _MAX_SERIALIZED_BYTES:
        raise CatalogError("search response exceeds the serialized response budget")
    return result


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _response_size_with_digest(payload: dict[str, Any]) -> int:
    candidate = dict(payload)
    candidate["delivery_digest"] = "0" * 64
    size = -1
    while candidate.get("serialized_bytes") != size:
        candidate["serialized_bytes"] = size
        size = len(_cli_wire_json(candidate).encode())
    return size


def _cli_wire_json(payload: dict[str, Any]) -> str:
    """Match the CLI JSON line encoding exactly."""

    return json.dumps(payload, sort_keys=True) + "\n"


def _sync_result_budget_metadata(
    result: dict[str, Any],
    candidate_pool: list[dict[str, Any]],
    discovery_pool: list[dict[str, Any]],
    skipped_candidate_digests: set[str],
    skipped_discovery_digests: set[str],
    guidance_budget_omitted: bool,
    limit: int,
) -> int:
    eligible_returned = len(result["candidates"])
    discovery_returned = len(result["discovery_leads"])
    candidate_budget_omitted = len(skipped_candidate_digests)
    discovery_budget_omitted = len(skipped_discovery_digests)
    candidate_limit_omitted = max(
        0,
        len(candidate_pool) - min(len(candidate_pool), limit),
    )
    discovery_limit_omitted = max(
        0,
        len(discovery_pool) - min(len(discovery_pool), limit),
    )
    result.update(
        {
            "eligible_candidate_count": len(candidate_pool),
            "eligible_candidates_returned": eligible_returned,
            "eligible_candidates_omitted_by_limit": candidate_limit_omitted,
            "eligible_candidates_omitted_by_response_budget": (
                candidate_budget_omitted
            ),
            "discovery_lead_count": len(discovery_pool),
            "discovery_leads_returned": discovery_returned,
            "discovery_leads_omitted_by_limit": discovery_limit_omitted,
            "discovery_leads_omitted_by_response_budget": (
                discovery_budget_omitted
            ),
            "supplemental_guidance_returned": bool(
                result["supplemental_guidance"]
            ),
            "supplemental_guidance_omitted_by_response_budget": (
                guidance_budget_omitted
            ),
        }
    )
    _sync_state_return_counts(result, candidate_pool, discovery_pool)
    _refresh_result_status(result)
    return (
        candidate_budget_omitted
        + discovery_budget_omitted
        + int(guidance_budget_omitted)
    )


def _sync_state_return_counts(
    result: dict[str, Any],
    candidate_pool: list[dict[str, Any]],
    discovery_pool: list[dict[str, Any]],
) -> None:
    qualifying_rows = candidate_pool + discovery_pool
    returned_rows = result["candidates"] + result["discovery_leads"]
    for state in ("active", "grandfathered", "archived"):
        counts = result["corpus_state_counts"][state]
        qualified = [row for row in qualifying_rows if row["catalog_state"] == state]
        returned = [row for row in returned_rows if row["catalog_state"] == state]
        qualified_paths = {row["path"] for row in qualified}
        returned_paths = {row["path"] for row in returned}
        counts.update(
            {
                "returned_document_count": len(returned_paths),
                "returned_section_count": sum(
                    row["unit_kind"] == "section" for row in returned
                ),
                "returned_document_fallback_count": sum(
                    row["unit_kind"] == "document" for row in returned
                ),
                "omitted_document_count": len(qualified_paths - returned_paths),
                "omitted_section_count": max(
                    0,
                    sum(row["unit_kind"] == "section" for row in qualified)
                    - sum(row["unit_kind"] == "section" for row in returned),
                ),
                "omitted_document_fallback_count": max(
                    0,
                    sum(row["unit_kind"] == "document" for row in qualified)
                    - sum(row["unit_kind"] == "document" for row in returned),
                ),
            }
        )


def _sync_single_budget_metadata(
    response: dict[str, Any],
    candidate_pool: list[dict[str, Any]],
    discovery_pool: list[dict[str, Any]],
    skipped_candidate_digests: set[str],
    skipped_discovery_digests: set[str],
    guidance_budget_omitted: bool,
    limit: int,
) -> None:
    dropped = _sync_result_budget_metadata(
        response,
        candidate_pool,
        discovery_pool,
        skipped_candidate_digests,
        skipped_discovery_digests,
        guidance_budget_omitted,
        limit,
    )
    response["dropped_candidate_count"] = dropped
    response["response_budget_truncated"] = dropped > 0


def _sync_batch_budget_metadata(
    response: dict[str, Any],
    candidate_pools: list[list[dict[str, Any]]],
    discovery_pools: list[list[dict[str, Any]]],
    skipped_candidate_digests: list[set[str]],
    skipped_discovery_digests: list[set[str]],
    guidance_budget_omitted: list[bool],
    limit: int,
) -> None:
    dropped = sum(
        _sync_result_budget_metadata(
            result,
            candidate_pool,
            discovery_pool,
            skipped_candidates,
            skipped_discovery,
            guidance_omitted,
            limit,
        )
        for (
            result,
            candidate_pool,
            discovery_pool,
            skipped_candidates,
            skipped_discovery,
            guidance_omitted,
        ) in zip(
            response["results"],
            candidate_pools,
            discovery_pools,
            skipped_candidate_digests,
            skipped_discovery_digests,
            guidance_budget_omitted,
            strict=True,
        )
    )
    response["dropped_candidate_count"] = dropped
    response["response_budget_truncated"] = dropped > 0


def _allocate_single_response(
    response: dict[str, Any],
    candidate_pool: list[dict[str, Any]],
    discovery_pool: list[dict[str, Any]],
    guidance_candidate: dict[str, Any] | None,
    limit: int,
) -> None:
    response["candidates"] = []
    response["discovery_leads"] = []
    response["supplemental_guidance"] = []
    skipped_candidates: set[str] = set()
    skipped_discovery: set[str] = set()
    guidance_omitted = False
    _sync_single_budget_metadata(
        response,
        candidate_pool,
        discovery_pool,
        skipped_candidates,
        skipped_discovery,
        False,
        limit,
    )
    if _response_size_with_digest(response) > _MAX_SERIALIZED_BYTES:
        raise CatalogError("search query exceeds the serialized response budget")

    def try_add(lane: str, item: dict[str, Any], *, mandatory: bool = False) -> bool:
        target = response[lane]
        target.append(item)
        _sync_single_budget_metadata(
            response,
            candidate_pool,
            discovery_pool,
            skipped_candidates,
            skipped_discovery,
            guidance_omitted,
            limit,
        )
        if _response_size_with_digest(response) <= _MAX_SERIALIZED_BYTES:
            return True
        target.pop()
        if mandatory:
            raise CatalogError(
                "mandatory corpus breadth exceeds the serialized response budget"
            )
        if lane == "candidates":
            skipped_candidates.add(item["candidate_digest"])
        elif lane == "discovery_leads":
            skipped_discovery.add(item["discovery_digest"])
        _sync_single_budget_metadata(
            response,
            candidate_pool,
            discovery_pool,
            skipped_candidates,
            skipped_discovery,
            guidance_omitted,
            limit,
        )
        return False

    if candidate_pool:
        try_add("candidates", candidate_pool[0], mandatory=True)
    if discovery_pool:
        try_add("discovery_leads", discovery_pool[0], mandatory=True)

    depth = [
        ("candidates", item)
        for item in candidate_pool[1 : min(len(candidate_pool), limit)]
    ] + [
        ("discovery_leads", item)
        for item in discovery_pool[1 : min(len(discovery_pool), limit)]
    ]
    depth.sort(key=lambda pair: pair[1]["relevance_rank"])
    for lane, item in depth:
        try_add(lane, item)

    if guidance_candidate is not None:
        response["supplemental_guidance"].append(guidance_candidate)
        _sync_single_budget_metadata(
            response,
            candidate_pool,
            discovery_pool,
            skipped_candidates,
            skipped_discovery,
            False,
            limit,
        )
        if _response_size_with_digest(response) > _MAX_SERIALIZED_BYTES:
            response["supplemental_guidance"].pop()
            guidance_omitted = True
    _sync_single_budget_metadata(
        response,
        candidate_pool,
        discovery_pool,
        skipped_candidates,
        skipped_discovery,
        guidance_omitted,
        limit,
    )
    response["candidates"].sort(key=lambda item: item["relevance_rank"])
    response["discovery_leads"].sort(key=lambda item: item["relevance_rank"])


def _allocate_batch_response(
    response: dict[str, Any],
    candidate_pools: list[list[dict[str, Any]]],
    discovery_pools: list[list[dict[str, Any]]],
    guidance_candidates: list[dict[str, Any] | None],
    limit: int,
) -> None:
    skipped_candidates: list[set[str]] = [set() for _ in candidate_pools]
    skipped_discovery: list[set[str]] = [set() for _ in discovery_pools]
    guidance_omitted = [False for _ in guidance_candidates]
    _sync_batch_budget_metadata(
        response,
        candidate_pools,
        discovery_pools,
        skipped_candidates,
        skipped_discovery,
        guidance_omitted,
        limit,
    )
    if _response_size_with_digest(response) > _MAX_SERIALIZED_BYTES:
        raise CatalogError("search queries exceed the global serialized response budget")

    def try_add(
        result_index: int,
        lane: str,
        item: dict[str, Any],
        *,
        mandatory: bool = False,
    ) -> bool:
        result = response["results"][result_index]
        result[lane].append(item)
        _sync_batch_budget_metadata(
            response,
            candidate_pools,
            discovery_pools,
            skipped_candidates,
            skipped_discovery,
            guidance_omitted,
            limit,
        )
        if _response_size_with_digest(response) <= _MAX_SERIALIZED_BYTES:
            return True
        result[lane].pop()
        if mandatory:
            raise CatalogError(
                "published batch maximum cannot preserve mandatory corpus breadth"
            )
        if lane == "candidates":
            skipped_candidates[result_index].add(item["candidate_digest"])
        elif lane == "discovery_leads":
            skipped_discovery[result_index].add(item["discovery_digest"])
        _sync_batch_budget_metadata(
            response,
            candidate_pools,
            discovery_pools,
            skipped_candidates,
            skipped_discovery,
            guidance_omitted,
            limit,
        )
        return False

    # Mandatory corpus breadth is allocated before any depth or guidance.
    for result_index, pool in enumerate(candidate_pools):
        if pool:
            try_add(result_index, "candidates", pool[0], mandatory=True)
    for result_index, pool in enumerate(discovery_pools):
        if pool:
            try_add(result_index, "discovery_leads", pool[0], mandatory=True)

    # Then corpus depth round-robin by objective and global relevance.
    depth_rows: list[list[tuple[str, dict[str, Any]]]] = []
    for candidate_pool, discovery_pool in zip(
        candidate_pools,
        discovery_pools,
        strict=True,
    ):
        rows = [
            ("candidates", item)
            for item in candidate_pool[1 : min(len(candidate_pool), limit)]
        ] + [
            ("discovery_leads", item)
            for item in discovery_pool[1 : min(len(discovery_pool), limit)]
        ]
        rows.sort(key=lambda pair: pair[1]["relevance_rank"])
        depth_rows.append(rows)
    depth_index = 0
    while any(depth_index < len(rows) for rows in depth_rows):
        for result_index, rows in enumerate(depth_rows):
            if depth_index < len(rows):
                lane, item = rows[depth_index]
                try_add(result_index, lane, item)
        depth_index += 1

    # Supplemental material is optional and always last.
    for index, candidate in enumerate(guidance_candidates):
        if candidate is None:
            continue
        response["results"][index]["supplemental_guidance"].append(candidate)
        _sync_batch_budget_metadata(
            response,
            candidate_pools,
            discovery_pools,
            skipped_candidates,
            skipped_discovery,
            guidance_omitted,
            limit,
        )
        if _response_size_with_digest(response) > _MAX_SERIALIZED_BYTES:
            response["results"][index]["supplemental_guidance"].pop()
            guidance_omitted[index] = True

    _sync_batch_budget_metadata(
        response,
        candidate_pools,
        discovery_pools,
        skipped_candidates,
        skipped_discovery,
        guidance_omitted,
        limit,
    )
    for result in response["results"]:
        result["candidates"].sort(key=lambda item: item["relevance_rank"])
        result["discovery_leads"].sort(key=lambda item: item["relevance_rank"])


def _git_show_text(repo_root: Path, sha: str, path: str) -> str:
    completed = subprocess.run(
        ["git", "--no-replace-objects", "show", f"{sha}:{path}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode(errors="replace").strip()
        raise CatalogError(f"cannot read {path!r} at {sha}: {detail}")
    try:
        return completed.stdout.decode()
    except UnicodeDecodeError as exc:
        raise CatalogError(f"{path!r} at {sha} is not UTF-8 text") from exc


def _git_blob_oid(repo_root: Path, sha: str, path: str) -> str:
    completed = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "ls-tree",
            "-z",
            sha,
            "--",
            path,
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode(errors="replace").strip()
        raise CatalogError(f"cannot resolve {path!r} at {sha}: {detail}")
    rows = [row for row in completed.stdout.split(b"\0") if row]
    if len(rows) != 1:
        raise CatalogError(f"cannot resolve one regular Git blob for {path!r} at {sha}")
    try:
        metadata, raw_path = rows[0].split(b"\t", 1)
        mode, object_type, oid = metadata.decode("ascii").split(" ", 2)
        resolved_path = raw_path.decode("utf-8")
    except (UnicodeError, ValueError) as exc:
        raise CatalogError(f"cannot parse Git identity for {path!r} at {sha}") from exc
    if resolved_path != path or mode not in {"100644", "100755"} or object_type != "blob":
        raise CatalogError(f"{path!r} at {sha} is not one regular Git blob")
    return oid
