"""Regression: malformed YAML in frontmatter or a fenced block must yield a
clean None (-> a FAIL finding downstream), never an uncaught YAMLError crash.
Repro source: runbooks/agent-dispatch.md + dual-brand-vectoraiz-aim-channel.md
crashed the linter (parser/sections.py yaml.safe_load unguarded)."""
from runbook_tools.parser.sections import (
    extract_yaml_frontmatter,
    extract_sections,
    extract_fenced_yaml_block,
)

_MALFORMED = "| Product | Type | Purpose |\n| a | b | c |"

def test_malformed_frontmatter_returns_none_not_raises():
    md = f"---\n{_MALFORMED}\n---\nbody\n"
    assert extract_yaml_frontmatter(md) is None

def test_malformed_fenced_block_returns_none_not_raises():
    md = (
        "## §B. Capability Matrix\n\n"
        "```yaml capability-matrix\n"
        f"{_MALFORMED}\n"
        "```\n"
    )
    sections = extract_sections(md)
    assert len(sections) == 1
    assert extract_fenced_yaml_block(sections[0], "capability-matrix") is None
