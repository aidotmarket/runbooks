from __future__ import annotations

import re
from pathlib import Path

from runbook_tools.version import LINTER_VERSION


TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "runbook.template.md"
SYSTEM_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")


def generate_scaffold(system_name: str, owner_agent: str = "max") -> str:
    """Produce a new-runbook scaffold from the repository template."""
    text = TEMPLATE_PATH.read_text()
    text = text.replace("<<SYSTEM_NAME:required>>", system_name)
    text = text.replace("<<OWNER:required>>", owner_agent)
    text = text.replace("<<LINTER_VERSION:required>>", LINTER_VERSION)
    return text


def validate_system_name(name: str) -> bool:
    return bool(SYSTEM_NAME_PATTERN.match(name))

