from pathlib import Path

import pytest

import runbook_tools.catalog.generator as catalog_generator

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


@pytest.fixture
def synthetic_git_catalog_projection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicitly remove production Git-history trust from synthetic fixtures.

    Runtime code never infers test status from remotes, paths, manifests, or
    catalog content. Tests exercising unrelated immutable-snapshot behavior opt
    into this seam by name; projection-security tests deliberately do not.
    """

    monkeypatch.setattr(
        catalog_generator,
        "_reviewed_legacy_projection",
        lambda _root, *, revision: None,
    )
