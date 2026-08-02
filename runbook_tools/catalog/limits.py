"""Frozen production limits for immutable runbook-corpus delivery.

The production object is deliberately constructed in code.  Environment
variables, command-line flags, manifests, plugins, and request data are not
inputs to it.  Tests may construct another immutable object for pure allocator
fault proofs, but every production entry point must call
``require_production_limits`` before doing any repository read.
"""

from __future__ import annotations

from dataclasses import dataclass

from runbook_tools.catalog.model import CatalogError


@dataclass(frozen=True, slots=True)
class CorpusLimits:
    manifest_bytes: int = 2_000_000
    document_bytes: int = 2_000_000
    aggregate_document_bytes: int = 64_000_000
    path_utf8_bytes: int = 192
    batch_id_j: int = 128
    objective_query_j: int = 4_000
    verify_against_items: int = 3
    verify_against_item_j: int = 120
    verify_against_aggregate_j: int = 120
    corpus_excerpt_j: int = 2_400
    initial_corpus_excerpt_j: int = 600
    supplemental_excerpt_j: int = 300
    response_bytes: int = 40_000
    response_build_proof_bytes: int = 32_000
    batch_objectives: int = 2
    mandatory_results_per_objective: int = 4
    bundle_response_bytes: int = 8_192
    compact_response_bytes: int = 1_024
    control_response_bytes: int = 24_000
    session_objectives: int = 8
    session_content_bytes: int = 120_000
    title_j: int = 64
    heading_j: int = 64
    section_id_j: int = 64
    authority_keys: int = 2
    authority_key_j: int = 64
    match_evidence_items: int = 1
    matched_tokens: int = 4
    matched_token_j: int = 24
    matched_tokens_aggregate_j: int = 96
    match_value_j: int = 96
    opaque_handle_j: int = 192


PRODUCTION_LIMITS = CorpusLimits()


def require_production_limits(limits: CorpusLimits = PRODUCTION_LIMITS) -> CorpusLimits:
    """Reject every non-singleton limits object at a production entry point."""

    if limits is not PRODUCTION_LIMITS:
        raise CatalogError("invalid_limits_override")
    return limits
