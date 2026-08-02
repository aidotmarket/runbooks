"""Closed canonical-content primitives for runbook-first delivery.

This module owns the byte representation shared by the runbooks library and
Kóska.  It intentionally does not know about MCP or authenticated session
state: Kóska supplies already-minted opaque values, while this module validates
their lexical form and fixes the exact ``TextContent.text`` bytes.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from runbook_tools.catalog.limits import PRODUCTION_LIMITS
from runbook_tools.catalog.model import CatalogError

_HEX40_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_HEX64_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_OID_RE = re.compile(r"\A(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_PORTABLE_PATH_RE = re.compile(r"\A[A-Za-z0-9._/-]+\Z")
_HANDLE_RE = re.compile(r"\A[A-Za-z0-9_-]+\Z")

WARNING_MESSAGE = "DISCOVERY ONLY — NOT VERIFIED OPERATING AUTHORITY"
GUIDANCE_WARNING_MESSAGE = "SUPPLEMENTAL GUIDANCE — NOT RUNBOOK AUTHORITY"

HANDLE_VERSION = 1
HANDLE_KINDS = {"lead": 1, "bundle": 2, "receipt": 3}
_HANDLE_DOMAIN = b"runbook-reference-vector-v1"


@dataclass(frozen=True, slots=True)
class DiscoveryHandles:
    """Opaque values supplied by the authenticated Kóska issuer."""

    discovery_lead_id: str
    verification_bundle_ref: str


def canonical_string_bytes(value: str) -> bytes:
    """Return the exact RFC-8259 ASCII JSON-string payload (J measure)."""

    if type(value) is not str:
        raise CatalogError("canonical string value must be a string")
    return json.dumps(value, ensure_ascii=True)[1:-1].encode("ascii")


def canonical_json_bytes(value: Any, *, final_newline: bool = False) -> bytes:
    """Serialize with the production ASCII, sorted, compact JSON profile."""

    text = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    if final_newline:
        text += "\n"
    return text.encode("utf-8")


def domain_digest(domain: str, value: Any) -> str:
    """Hash a closed projection under an explicit NUL-separated domain."""

    if not domain or "\0" in domain:
        raise CatalogError("digest domain must be a non-empty NUL-free string")
    return hashlib.sha256(
        domain.encode("ascii") + b"\0" + canonical_json_bytes(value)
    ).hexdigest()


def normalize_objective(value: str) -> str:
    """Normalize only insignificant outer/line whitespace, preserving words."""

    if type(value) is not str or not value.strip():
        raise CatalogError("search query must be a non-empty string")
    return " ".join(value.split()).casefold()


def objective_digest(value: str) -> str:
    return domain_digest(
        "runbook-objective-v1",
        {"schema_version": 1, "normalized_objective": normalize_objective(value)},
    )


def finalize_envelope(
    envelope: Mapping[str, Any],
    *,
    maximum_bytes: int,
    validate: bool = True,
) -> tuple[dict[str, Any], str]:
    """Populate exact size/delivery digest and return payload plus wire text."""

    if "serialized_bytes" in envelope or "delivery_digest" in envelope:
        raise CatalogError(
            "canonical envelope input must omit serialized_bytes and delivery_digest"
        )
    result = dict(envelope)
    result["serialized_bytes"] = 0
    result["delivery_digest"] = "0" * 64
    for _ in range(16):
        wire = canonical_json_bytes(result, final_newline=True)
        measured = len(wire)
        if result["serialized_bytes"] == measured:
            break
        result["serialized_bytes"] = measured
    else:  # pragma: no cover - decimal width converges in at most two passes
        raise CatalogError("canonical serialized byte count did not converge")

    zero_wire = canonical_json_bytes(result, final_newline=True)
    result["delivery_digest"] = hashlib.sha256(zero_wire).hexdigest()
    final_wire = canonical_json_bytes(result, final_newline=True)
    if len(final_wire) != result["serialized_bytes"]:
        raise CatalogError("canonical serialized byte count is unstable")
    if len(final_wire) > maximum_bytes:
        raise CatalogError("response_budget_exceeded")
    if validate:
        validate_closed_envelope(result)
    return result, final_wire.decode("utf-8")


def serialize_finalized_envelope(envelope: Mapping[str, Any]) -> str:
    """Return bytes for an already-finalized and validated envelope."""

    validate_closed_envelope(envelope)
    wire = canonical_json_bytes(envelope, final_newline=True)
    if len(wire) != envelope["serialized_bytes"]:
        raise CatalogError("canonical serialized byte count does not match payload")
    zeroed = dict(envelope)
    zeroed["delivery_digest"] = "0" * 64
    if hashlib.sha256(canonical_json_bytes(zeroed, final_newline=True)).hexdigest() != envelope[
        "delivery_digest"
    ]:
        raise CatalogError("canonical delivery digest does not match payload")
    return wire.decode("utf-8")


def mint_reference_handle(
    kind: str,
    *,
    key: bytes,
    session_binding: bytes,
    nonce: bytes,
    padding: bytes = b"",
) -> str:
    """Pure issuer primitive used by Kóska and the executable vectors.

    Production Kóska is responsible for random nonce generation, key lookup,
    uniqueness, claim persistence, and expiry.  Runbooks owns only this binary
    container/MAC encoding contract.
    """

    kind_byte = HANDLE_KINDS.get(kind)
    if kind_byte is None:
        raise CatalogError("unknown opaque reference kind")
    if len(key) != 32:
        raise CatalogError("opaque reference HMAC key must contain 32 bytes")
    if len(nonce) < 16:
        raise CatalogError("opaque reference nonce must contain at least 16 bytes")
    body = bytes((HANDLE_VERSION, kind_byte)) + nonce + padding
    container_size = len(body) + hashlib.sha256().digest_size
    if container_size > 144:
        raise CatalogError("opaque reference container exceeds the 192-J maximum")
    mac_input = (
        _HANDLE_DOMAIN
        + b"\0"
        + bytes((HANDLE_VERSION, kind_byte))
        + session_binding
        + body
    )
    tag = hmac.new(key, mac_input, hashlib.sha256).digest()
    value = base64.urlsafe_b64encode(body + tag).decode("ascii").rstrip("=")
    validate_opaque_handle(value)
    return value


def authenticate_reference_handle(
    value: str,
    kind: str,
    *,
    key: bytes,
    session_binding: bytes,
) -> bool:
    """Authenticate one opaque container without resolving its server claim."""

    try:
        raw = decode_opaque_handle(value)
    except CatalogError:
        return False
    kind_byte = HANDLE_KINDS.get(kind)
    if kind_byte is None or len(raw) < 50:
        return False
    body, supplied_tag = raw[:-32], raw[-32:]
    if body[0] != HANDLE_VERSION or body[1] != kind_byte or len(body[2:]) < 16:
        return False
    expected = hmac.new(
        key,
        _HANDLE_DOMAIN
        + b"\0"
        + bytes((HANDLE_VERSION, kind_byte))
        + session_binding
        + body,
        hashlib.sha256,
    ).digest()
    return hmac.compare_digest(supplied_tag, expected)


def validate_opaque_handle(value: str) -> None:
    if (
        type(value) is not str
        or not 67 <= len(value) <= PRODUCTION_LIMITS.opaque_handle_j
        or len(value) % 4 == 1
        or _HANDLE_RE.fullmatch(value) is None
    ):
        raise CatalogError("opaque reference has an invalid lexical form")
    decode_opaque_handle(value)


def decode_opaque_handle(value: str) -> bytes:
    if type(value) is not str or _HANDLE_RE.fullmatch(value) is None:
        raise CatalogError("opaque reference has an invalid lexical form")
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, binascii.Error) as exc:
        raise CatalogError("opaque reference is not valid base64url") from exc


def vector_reference_handle(kind: str, seed: int = 1) -> str:
    """Return the issuer-valid 192-J R6 proof fixture."""

    if not 0 <= seed <= 255:
        raise CatalogError("vector seed must fit one byte")
    pad = {"lead": b"L", "bundle": b"R", "receipt": b"V"}.get(kind)
    if pad is None:
        raise CatalogError("unknown opaque reference kind")
    return mint_reference_handle(
        kind,
        key=b"K" * 32,
        session_binding=b"a" * 64,
        nonce=bytes((seed,)) * 16,
        padding=pad * 94,
    )


def requirement_mapping_digest(
    *,
    adapter_type: str,
    adapter_parameters: Mapping[str, Any],
    evidence_policy: Mapping[str, Any],
) -> str:
    return domain_digest(
        "runbook-verification-mapping-v2",
        {
            "schema_version": 2,
            "adapter_type": adapter_type,
            "adapter_parameters": dict(adapter_parameters),
            "evidence_policy": dict(evidence_policy),
        },
    )


def verification_requirement(
    *,
    ordinal: int,
    prose: str,
    path: str,
    manifest_sha256: str,
    source_blob_oid: str,
    objective_digest_value: str,
    session_binding_sha256: str,
    catalog_sha: str,
    inventory_sha: str,
    adapter_type: str,
    adapter_parameters: Mapping[str, Any],
    evidence_policy: Mapping[str, Any],
) -> dict[str, Any]:
    prose_sha256 = hashlib.sha256(prose.encode("utf-8")).hexdigest()
    mapping_digest = requirement_mapping_digest(
        adapter_type=adapter_type,
        adapter_parameters=adapter_parameters,
        evidence_policy=evidence_policy,
    )
    requirement_id = domain_digest(
        "runbook-verification-requirement-v2",
        {
            "schema_version": 2,
            "ordinal": ordinal,
            "path": path,
            "prose_sha256": prose_sha256,
            "mapping_digest": mapping_digest,
            "manifest_sha256": manifest_sha256,
            "source_blob_oid": source_blob_oid,
            "objective_digest": objective_digest_value,
            "session_binding_sha256": session_binding_sha256,
            "catalog_sha": catalog_sha,
            "inventory_sha": inventory_sha,
        },
    )
    return {
        "schema_version": 2,
        "ordinal": ordinal,
        "prose": prose,
        "prose_sha256": prose_sha256,
        "requirement_id": requirement_id,
        "mapping_digest": mapping_digest,
        "adapter_type": adapter_type,
        "adapter_parameters": dict(adapter_parameters),
        "evidence_policy": dict(evidence_policy),
    }


def verification_bundle_digest(
    *,
    catalog_sha: str,
    manifest_sha256: str,
    inventory_sha: str,
    objective_digest_value: str,
    source_blob_oid: str,
    discovery_digest: str,
    discovery_lead_id: str,
    verification_requirements: Sequence[Mapping[str, Any]],
) -> str:
    return domain_digest(
        "runbook-verification-bundle-v1",
        {
            "schema_version": 1,
            "response_kind": "verification_bundle",
            "catalog_sha": catalog_sha,
            "manifest_sha256": manifest_sha256,
            "inventory_sha": inventory_sha,
            "objective_digest": objective_digest_value,
            "source_blob_oid": source_blob_oid,
            "discovery_digest": discovery_digest,
            "discovery_lead_id": discovery_lead_id,
            "verification_requirements": [dict(row) for row in verification_requirements],
        },
    )


def finalize_verification_bundle(
    envelope: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    return finalize_envelope(
        envelope,
        maximum_bytes=PRODUCTION_LIMITS.bundle_response_bytes,
    )


def finalize_compact_control(
    envelope: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    return finalize_envelope(
        envelope,
        maximum_bytes=PRODUCTION_LIMITS.compact_response_bytes,
    )


_SUCCESS_FIELDS = frozenset(
    {
        "schema_version",
        "catalog_sha",
        "manifest_sha256",
        "inventory_sha",
        "results",
        "searched_entry_count",
        "searched_section_count",
        "complete",
        "response_budget_bytes",
        "response_budget_truncated",
        "dropped_candidate_count",
        "serialized_bytes",
        "delivery_digest",
    }
)
_OBJECTIVE_FIELDS = frozenset(
    {
        "objective_ordinal",
        "objective_digest",
        "status",
        "discovery_status",
        "authoritative_gap",
        "qualifying_result_count",
        "eligible_candidate_count",
        "eligible_candidates_returned",
        "eligible_candidates_omitted_by_limit",
        "eligible_candidates_omitted_by_response_budget",
        "active_searched_count",
        "active_qualifying_count",
        "active_returned_count",
        "active_omitted_count",
        "grandfathered_searched_count",
        "grandfathered_qualifying_count",
        "grandfathered_returned_count",
        "grandfathered_omitted_count",
        "archived_searched_count",
        "archived_qualifying_count",
        "archived_returned_count",
        "archived_omitted_count",
        "candidates",
        "discovery_leads",
        "supplemental_guidance",
        "supplemental_guidance_returned",
        "supplemental_guidance_omitted_by_response_budget",
        "corpus_response_digest",
    }
)
_COMMON_RESULT_FIELDS = frozenset(
    {
        "retrieval_digest",
        "relevance_rank",
        "path",
        "candidate_kind",
        "catalog_state",
        "status",
        "action_authority_eligible",
        "authority_admission",
        "candidate_id_eligible",
        "catalog_declared",
        "declaration_kinds",
        "integrity_only",
        "integrity_status",
        "semantic_verification",
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
    }
)
_SECTION_FIELDS = frozenset(
    {
        "heading",
        "heading_sha256",
        "heading_truncated",
        "heading_line",
        "section_id",
        "section_id_source",
    }
)
_ACTIVE_FIELDS = frozenset(
    {
        "candidate_digest",
        "runbook_id",
        "owner",
        "last_verified_at",
        "authority_keys",
        "authority_keys_truncated",
        "rank",
    }
)
_DISCOVERY_FIELDS = frozenset(
    {
        "discovery_digest",
        "discovery_lead_id",
        "requires_ground_truth_verification",
        "historical_only",
        "manifest_risk",
        "manifest_batch",
        "warning",
    }
)
_WARNING_FIELDS = frozenset(
    {
        "warning_id",
        "code",
        "message",
        "catalog_state",
        "manifest_risk",
        "requires_ground_truth_verification",
        "requirement_count",
        "verification_bundle_digest",
        "verification_bundle_ref",
    }
)
_MATCH_FIELDS = frozenset(
    {"kind", "matched_tokens", "matched_tokens_truncated", "value", "weight"}
)
_GUIDANCE_FIELDS = frozenset(
    {
        "candidate_kind",
        "supplemental",
        "candidate_id_eligible",
        "action_authority_eligible",
        "authority_admission",
        "semantic_verification",
        "path",
        "catalog_sha",
        "source_blob_oid",
        "excerpt",
        "excerpt_sha256",
        "excerpt_truncated",
        "guidance_digest",
        "warning_id",
        "warning_code",
        "warning_message",
    }
)
_BUNDLE_FIELDS = frozenset(
    {
        "schema_version",
        "response_kind",
        "catalog_sha",
        "manifest_sha256",
        "inventory_sha",
        "objective_digest",
        "source_blob_oid",
        "discovery_digest",
        "discovery_lead_id",
        "verification_bundle_ref_sha256",
        "verification_bundle_digest",
        "requirement_count",
        "verification_requirements",
        "serialized_bytes",
        "delivery_digest",
    }
)
_REQUIREMENT_FIELDS = frozenset(
    {
        "schema_version",
        "ordinal",
        "prose",
        "prose_sha256",
        "requirement_id",
        "mapping_digest",
        "adapter_type",
        "adapter_parameters",
        "evidence_policy",
    }
)
_POLICY_FIELDS = frozenset(
    {
        "minimum_receipts",
        "maximum_receipts",
        "freshness_seconds",
        "allowed_evidence_kinds",
        "require_remote_identity",
        "require_distinct_sources",
    }
)
_CONFIRMATION_FIELDS = frozenset(
    {
        "schema_version",
        "response_kind",
        "session_binding_sha256",
        "objective_digest",
        "activation_digest",
        "verification_bundle_digest",
        "requirement_set_digest",
        "outcome",
        "discovery_verification_receipt_id",
        "serialized_bytes",
        "delivery_digest",
    }
)
_REPLAY_FIELDS = frozenset(
    {
        "schema_version",
        "response_kind",
        "session_binding_sha256",
        "objective_digest",
        "replay_of_delivery_digest",
        "reference_kind",
        "reference_value",
        "serialized_bytes",
        "delivery_digest",
    }
)
_FAIL_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "error_code",
        "message",
        "serialized_bytes",
        "delivery_digest",
    }
)

_ADAPTER_FIELDS: dict[str, frozenset[str]] = {
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


def validate_closed_envelope(envelope: Mapping[str, Any]) -> None:
    """Reject unknown/omitted fields for every canonical response variant."""

    kind = envelope.get("response_kind")
    if kind == "verification_bundle":
        _exact_fields(envelope, _BUNDLE_FIELDS, "verification bundle")
        _validate_bundle(envelope)
        return
    if kind == "discovery_verification_receipt":
        _exact_fields(envelope, _CONFIRMATION_FIELDS, "confirmation receipt")
        _validate_compact(envelope)
        return
    if kind == "compact_replay_receipt":
        _exact_fields(envelope, _REPLAY_FIELDS, "compact replay receipt")
        _validate_compact(envelope)
        return
    if envelope.get("status") == "fail":
        fields = _FAIL_FIELDS | ({"changed_paths"} if "changed_paths" in envelope else set())
        _exact_fields(envelope, fields, "failure envelope")
        return
    _exact_fields(envelope, _SUCCESS_FIELDS, "search envelope")
    if envelope.get("schema_version") != 4 or envelope.get("complete") is not True:
        raise CatalogError("search envelope has an invalid schema or completion state")
    _hex(envelope.get("catalog_sha"), 40, "catalog_sha")
    _hex(envelope.get("manifest_sha256"), 64, "manifest_sha256")
    _hex(envelope.get("inventory_sha"), 40, "inventory_sha")
    results = envelope.get("results")
    if type(results) is not list or not 1 <= len(results) <= 2:
        raise CatalogError("search envelope results must contain one or two objectives")
    for index, result in enumerate(results):
        _validate_objective(result, index + 1)
    expected_dropped = sum(
        result["active_omitted_count"]
        + result["grandfathered_omitted_count"]
        + result["archived_omitted_count"]
        for result in results
    )
    if envelope.get("dropped_candidate_count") != expected_dropped:
        raise CatalogError("dropped_candidate_count violates the exact omission equation")


def _validate_objective(result: Any, ordinal: int) -> None:
    _exact_fields(result, _OBJECTIVE_FIELDS, f"objective {ordinal}")
    if result.get("objective_ordinal") != ordinal:
        raise CatalogError("objective ordinal does not match request order")
    _hex(result.get("objective_digest"), 64, "objective_digest")
    candidates = result.get("candidates")
    discoveries = result.get("discovery_leads")
    if type(candidates) is not list or type(discoveries) is not list:
        raise CatalogError("objective corpus lanes must be arrays")
    if len(candidates) + len(discoveries) > 4:
        raise CatalogError("objective contains more than four corpus results")
    state_values = {
        "active": "ACTIVE",
        "grandfathered": "grandfathered",
        "archived": "archived",
    }
    all_rows = candidates + discoveries
    for state, serialized_state in state_values.items():
        qualifying = result.get(f"{state}_qualifying_count")
        returned = result.get(f"{state}_returned_count")
        omitted = result.get(f"{state}_omitted_count")
        if (
            type(qualifying) is not int
            or type(returned) is not int
            or type(omitted) is not int
            or qualifying - returned != omitted
            or returned
            != sum(row.get("catalog_state") == serialized_state for row in all_rows)
        ):
            raise CatalogError(f"objective {state} counters violate the exact equation")
    if result.get("qualifying_result_count") != sum(
        result[f"{state}_qualifying_count"] for state in state_values
    ):
        raise CatalogError("objective qualifying_result_count is inconsistent")
    if result.get("eligible_candidate_count") != (
        result.get("eligible_candidates_returned")
        + result.get("eligible_candidates_omitted_by_limit")
        + result.get("eligible_candidates_omitted_by_response_budget")
    ):
        raise CatalogError("objective ACTIVE compatibility counters are inconsistent")
    for row in candidates:
        _validate_result(row, discovery=False)
    for row in discoveries:
        _validate_result(row, discovery=True)
    guidance = result.get("supplemental_guidance")
    if type(guidance) is not list or len(guidance) > 1:
        raise CatalogError("supplemental guidance must contain zero or one item")
    for item in guidance:
        _exact_fields(item, _GUIDANCE_FIELDS, "supplemental guidance")
        if item.get("candidate_kind") != "repository_authoring_guidance":
            raise CatalogError("supplemental guidance kind is invalid")
        if item.get("warning_message") != GUIDANCE_WARNING_MESSAGE:
            raise CatalogError("supplemental guidance warning text is not exact")
        if len(canonical_string_bytes(item.get("excerpt"))) > 300:
            raise CatalogError("supplemental guidance excerpt exceeds 300 J")


def _validate_result(row: Any, *, discovery: bool) -> None:
    if not isinstance(row, Mapping):
        raise CatalogError("corpus result must be an object")
    section_fields = _SECTION_FIELDS if row.get("unit_kind") == "section" else frozenset()
    kind_fields = _DISCOVERY_FIELDS if discovery else _ACTIVE_FIELDS
    _exact_fields(row, _COMMON_RESULT_FIELDS | section_fields | kind_fields, "corpus result")
    _portable_path(row.get("path"), "path")
    _oid(row.get("source_blob_oid"), "source_blob_oid")
    for field in ("retrieval_digest", "excerpt_sha256"):
        _hex(row.get(field), 64, field)
    if row.get("unit_kind") not in {"section", "document"}:
        raise CatalogError("corpus unit_kind is invalid")
    if len(canonical_string_bytes(row.get("document_title"))) > 64:
        raise CatalogError("document_title exceeds 64 J")
    if len(canonical_string_bytes(row.get("excerpt"))) > 2_400:
        raise CatalogError("corpus excerpt exceeds 2,400 J")
    matches = row.get("match_evidence")
    if type(matches) is not list or len(matches) > 1:
        raise CatalogError("match_evidence must contain at most one item")
    for match in matches:
        _exact_fields(match, _MATCH_FIELDS, "match evidence")
        if match.get("kind") not in {
            "path",
            "title",
            "heading",
            "excerpt",
            "structured_literal",
            "intent",
            "legacy_active",
        }:
            raise CatalogError("match evidence kind is invalid")
        tokens = match.get("matched_tokens")
        if type(tokens) is not list or len(tokens) > 4:
            raise CatalogError("match evidence matched_tokens exceeds four items")
        if any(len(canonical_string_bytes(token)) > 24 for token in tokens):
            raise CatalogError("match evidence token exceeds 24 J")
        if sum(len(canonical_string_bytes(token)) for token in tokens) > 96:
            raise CatalogError("match evidence tokens exceed 96 J aggregate")
        if len(canonical_string_bytes(match.get("value"))) > 96:
            raise CatalogError("match evidence value exceeds 96 J")
    relevance = row.get("relevance_evidence")
    allowed_relevance = {
        "path",
        "title",
        "heading",
        "phrase",
        "structured_literal",
        "token_threshold",
        "single_strong_token",
    }
    if (
        type(relevance) is not list
        or not 1 <= len(relevance) <= 7
        or len(relevance) != len(set(relevance))
        or any(value not in allowed_relevance for value in relevance)
    ):
        raise CatalogError("relevance_evidence is invalid")
    if discovery:
        _hex(row.get("discovery_digest"), 64, "discovery_digest")
        validate_opaque_handle(row.get("discovery_lead_id"))
        warning = row.get("warning")
        _exact_fields(warning, _WARNING_FIELDS, "discovery warning")
        if warning.get("message") != WARNING_MESSAGE:
            raise CatalogError("discovery warning text is not exact")
        if warning.get("code") != "DISCOVERY_ONLY_NOT_VERIFIED":
            raise CatalogError("discovery warning code is not exact")
        if warning.get("catalog_state") != row.get("catalog_state"):
            raise CatalogError("discovery warning catalog state does not match result")
        if warning.get("manifest_risk") != row.get("manifest_risk"):
            raise CatalogError("discovery warning risk does not match result")
        if type(warning.get("requirement_count")) is not int or not 1 <= warning[
            "requirement_count"
        ] <= 3:
            raise CatalogError("discovery warning requirement_count is invalid")
        _hex(
            warning.get("verification_bundle_digest"),
            64,
            "verification_bundle_digest",
        )
        validate_opaque_handle(warning.get("verification_bundle_ref"))
    else:
        _hex(row.get("candidate_digest"), 64, "candidate_digest")
        if row.get("catalog_state") != "ACTIVE" or row.get("status") != "ACTIVE":
            raise CatalogError("ACTIVE result state/status is invalid")
        if row.get("owner") not in {
            "vulcan",
            "mars",
            "kd",
            "mp",
            "max",
            "sysadmin",
        }:
            raise CatalogError("ACTIVE result owner is invalid")
        if len(canonical_string_bytes(row["owner"])) > 8:
            raise CatalogError("ACTIVE result owner exceeds the R7 maximum")
        authority_keys = row.get("authority_keys")
        if type(authority_keys) is not list or len(authority_keys) > 2:
            raise CatalogError("ACTIVE authority_keys exceeds two items")
        if any(len(canonical_string_bytes(value)) > 64 for value in authority_keys):
            raise CatalogError("ACTIVE authority key exceeds 64 J")
    if row.get("unit_kind") == "section":
        if len(canonical_string_bytes(row.get("heading"))) > 64:
            raise CatalogError("section heading exceeds 64 J")
        if len(canonical_string_bytes(row.get("section_id"))) > 64:
            raise CatalogError("section_id exceeds 64 J")


def _validate_bundle(envelope: Mapping[str, Any]) -> None:
    requirements = envelope.get("verification_requirements")
    if type(requirements) is not list or not 1 <= len(requirements) <= 3:
        raise CatalogError("verification bundle must contain one through three requirements")
    if envelope.get("requirement_count") != len(requirements):
        raise CatalogError("verification bundle requirement_count is inconsistent")
    aggregate = 0
    for index, requirement in enumerate(requirements, start=1):
        _exact_fields(requirement, _REQUIREMENT_FIELDS, "verification requirement")
        if requirement.get("schema_version") != 2 or requirement.get("ordinal") != index:
            raise CatalogError("verification requirement ordinal/schema is invalid")
        prose = requirement.get("prose")
        if type(prose) is not str:
            raise CatalogError("verification requirement prose must be a string")
        prose_j = len(canonical_string_bytes(prose))
        if prose_j > 120:
            raise CatalogError("verification requirement prose exceeds 120 J")
        aggregate += prose_j
        adapter = requirement.get("adapter_type")
        expected_parameters = _ADAPTER_FIELDS.get(adapter)
        if expected_parameters is None:
            raise CatalogError("verification requirement adapter is unknown")
        _exact_fields(
            requirement.get("adapter_parameters"),
            expected_parameters,
            "adapter parameters",
        )
        _exact_fields(requirement.get("evidence_policy"), _POLICY_FIELDS, "evidence policy")
    if aggregate > 120:
        raise CatalogError("verification requirement prose exceeds 120 J aggregate")


def _validate_compact(envelope: Mapping[str, Any]) -> None:
    _hex(envelope.get("session_binding_sha256"), 64, "session_binding_sha256")
    _hex(envelope.get("objective_digest"), 64, "objective_digest")
    if envelope.get("response_kind") == "discovery_verification_receipt":
        validate_opaque_handle(envelope.get("discovery_verification_receipt_id"))
    else:
        validate_opaque_handle(envelope.get("reference_value"))


def _exact_fields(value: Any, expected: set[str] | frozenset[str], label: str) -> None:
    if not isinstance(value, Mapping):
        raise CatalogError(f"{label} must be an object")
    actual = set(value)
    if actual != set(expected):
        missing = sorted(set(expected) - actual)
        unknown = sorted(actual - set(expected))
        detail: list[str] = []
        if missing:
            detail.append("missing=" + ",".join(missing))
        if unknown:
            detail.append("unknown=" + ",".join(unknown))
        raise CatalogError(f"{label} is not closed: {'; '.join(detail)}")


def _hex(value: Any, length: int, label: str) -> None:
    matcher = _HEX40_RE if length == 40 else _HEX64_RE
    if type(value) is not str or matcher.fullmatch(value) is None:
        raise CatalogError(f"{label} must be lowercase {length}-hex")


def _oid(value: Any, label: str) -> None:
    if type(value) is not str or _OID_RE.fullmatch(value) is None:
        raise CatalogError(f"{label} must be a lowercase Git object ID")


def _portable_path(value: Any, label: str) -> None:
    if type(value) is not str or _PORTABLE_PATH_RE.fullmatch(value) is None:
        raise CatalogError(f"{label} must be a portable repository path")
    if len(value.encode("utf-8")) > PRODUCTION_LIMITS.path_utf8_bytes:
        raise CatalogError(f"{label} exceeds 192 UTF-8 bytes")
    components = value.split("/")
    if value.startswith("/") or value.endswith("/") or any(
        component in {"", ".", ".."} for component in components
    ):
        raise CatalogError(f"{label} must be a normalized portable repository path")
