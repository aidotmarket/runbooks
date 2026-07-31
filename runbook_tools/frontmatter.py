from __future__ import annotations

# Catalog metadata shares the Markdown frontmatter with the §A agent form but
# is validated by the catalog model, not section_a_header.schema.json.
CATALOG_METADATA_FIELDS = frozenset(
    {
        "runbook_id",
        "domain",
        "status",
        "authoritative_for",
        "aliases",
        "error_signatures",
        "supersedes",
        "superseded_by",
        "owner",
        "last_verified_at",
    }
)
