import copy
import hashlib
import json

from runbook_tools.catalog.canonical_content import (
    canonical_json_bytes,
    vector_reference_handle,
)


def wire(obj):
    return canonical_json_bytes(obj, final_newline=True)


def jmax(n):
    return "\n" * (n // 2) + ("x" if n % 2 else "")


H40 = "a" * 40
H64 = "b" * 64
D64 = "f" * 64
PATH = "p" * 189 + ".md"


def handle(kind, seed=1):
    return vector_reference_handle(kind, seed)


def match_evidence():
    return {
        "kind": "structured_literal",
        "matched_tokens": [jmax(24) for _ in range(4)],
        "matched_tokens_truncated": True,
        "value": jmax(96),
        "weight": 9999.999999,
    }


def common(kind, excerpt_j):
    discovery = kind == "discovery"
    return {
        "action_authority_eligible": not discovery,
        "authority_admission": not discovery,
        "candidate_id_eligible": not discovery,
        "candidate_kind": ("grandfathered_discovery_lead" if discovery
                           else "active_catalog_section"),
        "catalog_declared": not discovery,
        "catalog_state": "grandfathered" if discovery else "ACTIVE",
        "declaration_kinds": ["topic", "error_signature"],
        "document_title": jmax(64),
        "document_title_sha256": D64,
        "document_title_truncated": True,
        "excerpt": jmax(excerpt_j),
        "excerpt_end_column_exclusive": 999999,
        "excerpt_end_line": 999999,
        "excerpt_sha256": D64,
        "excerpt_start_line": 999999,
        "excerpt_truncated": True,
        "heading": jmax(64),
        "heading_line": 999999,
        "heading_sha256": D64,
        "heading_truncated": True,
        "integrity_only": discovery,
        "integrity_status": "integrity_pass_unverified",
        "match_evidence": [match_evidence()],
        "path": PATH,
        "relevance_evidence": ["path", "title", "heading", "phrase",
                               "structured_literal", "token_threshold",
                               "single_strong_token"],
        "relevance_rank": 999999,
        "retrieval_digest": D64,
        "score": 999999.999999,
        "section_id": jmax(64),
        "section_id_source": "legacy-derived",
        "semantic_verification": False,
        "source_blob_oid": H64,
        "status": "pending_verification" if discovery else "ACTIVE",
        "unit_kind": "section",
    }


def active(excerpt_j=600):
    value = common("active", excerpt_j)
    value.update({
        "authority_keys": [jmax(64) for _ in range(2)],
        "authority_keys_truncated": True,
        "candidate_digest": D64,
        "last_verified_at": "9999-12-31",
        "owner": "sysadmin",
        "rank": 999999,
        "runbook_id": jmax(64),
    })
    return value


def discovery(excerpt_j=600, seed=1):
    value = common("discovery", excerpt_j)
    value.update({
        "discovery_digest": D64,
        "discovery_lead_id": handle("lead", seed),
        "historical_only": False,
        "manifest_batch": jmax(128),
        "manifest_risk": "P3",
        "requires_ground_truth_verification": True,
        "warning": {
            "catalog_state": "grandfathered",
            "code": "DISCOVERY_ONLY_NOT_VERIFIED",
            "manifest_risk": "P3",
            "message": "DISCOVERY ONLY \u2014 NOT VERIFIED OPERATING AUTHORITY",
            "requirement_count": 3,
            "requires_ground_truth_verification": True,
            "verification_bundle_digest": D64,
            "verification_bundle_ref": handle("bundle", seed),
            "warning_id": D64,
        },
    })
    return value


def supplemental():
    return {
        "action_authority_eligible": False,
        "authority_admission": False,
        "candidate_id_eligible": False,
        "candidate_kind": "repository_authoring_guidance",
        "catalog_sha": H40,
        "excerpt": jmax(300),
        "excerpt_sha256": D64,
        "excerpt_truncated": True,
        "guidance_digest": D64,
        "path": "README.md",
        "semantic_verification": False,
        "source_blob_oid": H64,
        "supplemental": True,
        "warning_code": "SUPPLEMENTAL_GUIDANCE_NOT_AUTHORITY",
        "warning_id": D64,
        "warning_message": "SUPPLEMENTAL GUIDANCE \u2014 NOT RUNBOOK AUTHORITY",
    }


def objective(shape, ordinal):
    if shape == "3a1d":
        candidates = [active() for _ in range(3)]
        leads = [discovery(seed=ordinal * 8 + 1)]
        returned = (3, 1, 0)
        global_ranks = [1, 2, 3, 999999]
    else:
        candidates = [active()]
        leads = [
            discovery(seed=ordinal * 8 + lane_ordinal)
            for lane_ordinal in range(1, 4)
        ]
        returned = (1, 3, 0)
        global_ranks = [999999, 1, 2, 3]
    all_results = candidates + leads
    for i, (item, global_rank) in enumerate(zip(all_results, global_ranks)):
        item["path"] = str(i) + item["path"][1:]
        item["relevance_rank"] = global_rank
        item["retrieval_digest"] = format(i + 1, "x") * 64
        item["retrieval_digest"] = item["retrieval_digest"][:64]
        if "candidate_digest" in item:
            item["candidate_digest"] = format(i + 5, "x") * 64
            item["candidate_digest"] = item["candidate_digest"][:64]
            item["rank"] = 999997 + i
        else:
            item["discovery_digest"] = format(i + 9, "x") * 64
            item["discovery_digest"] = item["discovery_digest"][:64]
    aq, gq, rq = 333333, 333333, 333333
    ar, gr, rr = returned
    return {
        "active_omitted_count": aq - ar,
        "active_qualifying_count": aq,
        "active_returned_count": ar,
        "active_searched_count": 20,
        "archived_omitted_count": rq - rr,
        "archived_qualifying_count": rq,
        "archived_returned_count": rr,
        "archived_searched_count": 1,
        "authoritative_gap": True,
        "candidates": candidates,
        "corpus_response_digest": D64,
        "discovery_leads": leads,
        "discovery_status": "discovery_leads_returned_unverified",
        "eligible_candidate_count": aq,
        "eligible_candidates_omitted_by_limit": (aq - ar) // 2,
        "eligible_candidates_omitted_by_response_budget": (
            aq - ar - (aq - ar) // 2),
        "eligible_candidates_returned": ar,
        "grandfathered_omitted_count": gq - gr,
        "grandfathered_qualifying_count": gq,
        "grandfathered_returned_count": gr,
        "grandfathered_searched_count": 81,
        "objective_digest": D64,
        "objective_ordinal": ordinal,
        "qualifying_result_count": aq + gq + rq,
        "status": "no_usable_corpus_result_response_budget",
        "supplemental_guidance": [supplemental()],
        "supplemental_guidance_omitted_by_response_budget": False,
        "supplemental_guidance_returned": True,
    }


def finalize_delivery(obj):
    result = copy.deepcopy(obj)
    result["delivery_digest"] = "0" * 64
    for _ in range(4):
        result["serialized_bytes"] = len(wire(result))
    zeroed = copy.deepcopy(result)
    zeroed["delivery_digest"] = "0" * 64
    result["delivery_digest"] = hashlib.sha256(wire(zeroed)).hexdigest()
    assert result["serialized_bytes"] == len(wire(result))
    return result


def response(order):
    results = [objective(shape, i + 1) for i, shape in enumerate(order)]
    dropped = sum(
        o["active_omitted_count"] + o["grandfathered_omitted_count"]
        + o["archived_omitted_count"] for o in results
    )
    return finalize_delivery({
        "catalog_sha": H40,
        "complete": True,
        "delivery_digest": "0" * 64,
        "dropped_candidate_count": dropped,
        "inventory_sha": H40,
        "manifest_sha256": H64,
        "response_budget_bytes": 40000,
        "response_budget_truncated": False,
        "results": results,
        "schema_version": 4,
        "searched_entry_count": 102,
        "searched_section_count": 999999,
        "serialized_bytes": 40000,
    })


def params(adapter):
    return {
        "git_object_v1": {
            "commit_sha": H40, "expected_object_oid": H64,
            "path": PATH, "repository": jmax(64)},
        "json_schema_v1": {
            "commit_sha": H40, "expected_value_sha256": H64,
            "json_pointer": jmax(128), "path": PATH,
            "repository": jmax(64)},
        "health_probe_v1": {
            "max_age_seconds": 86400, "probe_id": jmax(96),
            "service_id": jmax(64)},
        "test_result_v1": {
            "commit_sha": H40, "report_sha256": H64,
            "repository": jmax(64), "test_id": jmax(128)},
        "state_read_v1": {
            "entity_key": jmax(128), "expected_value_sha256": H64,
            "field_path": jmax(128), "namespace": jmax(64)},
        "production_probe_v1": {
            "max_age_seconds": 86400, "probe_id": jmax(96),
            "service_id": jmax(64)},
        "unmapped_prose": {},
    }[adapter]


def policy(which):
    if which == "min":
        return {
            "allowed_evidence_kinds": ["git"],
            "freshness_seconds": 0,
            "maximum_receipts": 1,
            "minimum_receipts": 1,
            "require_distinct_sources": False,
            "require_remote_identity": False,
        }
    return {
        "allowed_evidence_kinds": ["schema", "health", "state", "probe"],
        "freshness_seconds": 86400,
        "maximum_receipts": 4,
        "minimum_receipts": 4,
        "require_distinct_sources": True,
        "require_remote_identity": True,
    }


def bundle(adapter, policy_shape):
    requirements = []
    for ordinal in range(1, 4):
        requirements.append({
            "adapter_parameters": params(adapter),
            "adapter_type": adapter,
            "evidence_policy": policy(policy_shape),
            "mapping_digest": D64,
            "ordinal": ordinal,
            "prose": jmax(40),
            "prose_sha256": D64,
            "requirement_id": D64,
            "schema_version": 2,
        })
    return finalize_delivery({
        "catalog_sha": H40,
        "delivery_digest": "0" * 64,
        "discovery_digest": D64,
        "discovery_lead_id": handle("lead"),
        "inventory_sha": H40,
        "manifest_sha256": H64,
        "objective_digest": D64,
        "requirement_count": 3,
        "response_kind": "verification_bundle",
        "schema_version": 1,
        "serialized_bytes": 8192,
        "source_blob_oid": H64,
        "verification_bundle_digest": D64,
        "verification_bundle_ref_sha256": D64,
        "verification_requirements": requirements,
    })


def control():
    paths = []
    for i in range(102):
        prefix = f"{i:03d}-"
        paths.append(prefix + "p" * (189 - len(prefix)) + ".md")
    assert all(len(p.encode("utf-8")) == 192 for p in paths)
    return finalize_delivery({
        "changed_paths": paths,
        "delivery_digest": "0" * 64,
        "error_code": "mandatory_corpus_envelope_too_large",
        "message": jmax(256),
        "schema_version": 4,
        "serialized_bytes": 24000,
        "status": "fail",
    })


def confirmation():
    return finalize_delivery({
        "activation_digest": "c" * 64,
        "delivery_digest": "0" * 64,
        "discovery_verification_receipt_id": handle("receipt"),
        "objective_digest": "b" * 64,
        "outcome": "confirmed_for_objective",
        "requirement_set_digest": "e" * 64,
        "response_kind": "discovery_verification_receipt",
        "schema_version": 1,
        "serialized_bytes": 1024,
        "session_binding_sha256": "a" * 64,
        "verification_bundle_digest": "d" * 64,
    })


def compact_replay():
    return finalize_delivery({
        "delivery_digest": "0" * 64,
        "objective_digest": "b" * 64,
        "reference_kind": "discovery_verification_receipt_id",
        "reference_value": handle("receipt"),
        "replay_of_delivery_digest": "c" * 64,
        "response_kind": "compact_replay_receipt",
        "schema_version": 1,
        "serialized_bytes": 1024,
        "session_binding_sha256": "a" * 64,
    })


def fault():
    n = 32001 - len(wire({"fault_padding": ""}))
    obj = {"fault_padding": "x" * n}
    assert len(wire(obj)) == 32001
    return obj


vectors = {
    "active.max": active(2400),
    "discovery.compact.max": discovery(2400),
    "objective.3_active_1_discovery": objective("3a1d", 1),
    "objective.1_active_3_discovery": objective("1a3d", 1),
    "response.3a1d_then_1a3d": response(["3a1d", "1a3d"]),
    "response.1a3d_then_3a1d": response(["1a3d", "3a1d"]),
    "control.changed_paths.max": control(),
    "confirmation.max": confirmation(),
    "compact_replay.max": compact_replay(),
    "private.fault_32001": fault(),
}

for adapter in ["git_object_v1", "json_schema_v1", "health_probe_v1",
                "test_result_v1", "state_read_v1", "production_probe_v1",
                "unmapped_prose"]:
    for shape in ["min", "max"]:
        vectors[f"bundle.{adapter}.policy_{shape}"] = bundle(adapter, shape)

rows = []
for name, obj in vectors.items():
    payload = wire(obj)
    rows.append({"name": name, "bytes": len(payload),
                 "sha256": hashlib.sha256(payload).hexdigest()})

if __name__ == "__main__":
    print(json.dumps(rows, indent=2))
