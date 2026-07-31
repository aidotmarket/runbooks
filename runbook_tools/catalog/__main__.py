"""Clean-checkout module entry point for the runbook catalog CLI."""

from runbook_tools.cli import catalog_cmd

if __name__ == "__main__":
    catalog_cmd(prog_name="python -m runbook_tools.catalog")
