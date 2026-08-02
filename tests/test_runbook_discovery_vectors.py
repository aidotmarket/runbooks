from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from runbook_tools.catalog.canonical_content import (
    authenticate_reference_handle,
    canonical_json_bytes,
    finalize_compact_control,
    finalize_verification_bundle,
    serialize_finalized_envelope,
    vector_reference_handle,
)

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PATH = ROOT / "tests/fixtures/catalog/runbook_discovery_vectors.json"
GENERATOR_PATH = ROOT / "scripts/generate_runbook_discovery_vectors.py"


def _generator_module():
    spec = importlib.util.spec_from_file_location(
        "generate_runbook_discovery_vectors",
        GENERATOR_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_r7_exact_serializer_vector_matches_the_committed_fixture() -> None:
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    module = _generator_module()
    actual = {
        name: {
            "bytes": len(canonical_json_bytes(value, final_newline=True)),
            "sha256": hashlib.sha256(
                canonical_json_bytes(value, final_newline=True)
            ).hexdigest(),
        }
        for name, value in module.vectors.items()
    }

    assert actual == expected


def test_r7_vector_handles_are_issuer_valid_and_kind_separated() -> None:
    values = {
        kind: vector_reference_handle(kind, 1)
        for kind in ("lead", "bundle", "receipt")
    }

    assert len(set(values.values())) == 3
    assert all(len(value) == 192 for value in values.values())
    for kind, value in values.items():
        assert authenticate_reference_handle(
            value,
            kind,
            key=b"K" * 32,
            session_binding=b"a" * 64,
        )
        assert all(
            not authenticate_reference_handle(
                value,
                other,
                key=b"K" * 32,
                session_binding=b"a" * 64,
            )
            for other in {"lead", "bundle", "receipt"} - {kind}
        )


def test_public_finalizers_reproduce_r7_bundle_and_compact_control_vectors() -> None:
    module = _generator_module()
    for name, expected in module.vectors.items():
        if name.startswith("bundle."):
            finalizer = finalize_verification_bundle
        elif name in {"confirmation.max", "compact_replay.max"}:
            finalizer = finalize_compact_control
        else:
            continue
        unfinalized = {
            key: value
            for key, value in expected.items()
            if key not in {"serialized_bytes", "delivery_digest"}
        }
        payload, text = finalizer(unfinalized)

        assert payload == expected, name
        assert text == serialize_finalized_envelope(expected), name
