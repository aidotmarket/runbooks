from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Callable

import click
import yaml

from runbook_tools.harness.dispatch import make_council_request_fn
from runbook_tools.harness.loader import (
    ConfigurationError,
    ScenarioLoadConfig,
    load_scenarios,
)
from runbook_tools.harness.runner import Response, run_dispatch_for_scenario
from runbook_tools.harness.scorer import score_response
from runbook_tools.harness.writer import write_result
from runbook_tools.lint import CheckContext, Finding
from runbook_tools.lint.checks import ALL_CHECKS
from runbook_tools.parser.sections import extract_sections, extract_yaml_frontmatter
from runbook_tools.scaffold.template import generate_scaffold, validate_system_name
from runbook_tools.version import LINTER_VERSION


README_STATUS_RE = re.compile(r"^\|\s*(?P<system>.+?)\s*\|\s*(?P<runbook>.+?)\s*\|\s*(?P<status>[A-Z0-9_]+)\s*\|")
VALID_README_STATUSES = {
    "NOT_STARTED",
    "GATE_1_IN_PROGRESS",
    "GATE_1_APPROVED",
    "GATE_2_IN_PROGRESS",
    "GATE_3_IN_PROGRESS",
    "GATE_4_IN_PROGRESS",
    "CONFORMANT",
    "RETROFIT_CANDIDATE",
    "LEGACY_NOT_UNDER_STANDARD",
    "DEPRECATED",
}


@click.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=False))
@click.option("--version", is_flag=True)
@click.option("--mode", type=click.Choice(["strict", "probationary", "legacy"]), default=None)
@click.option("--format", "output_format", type=click.Choice(["text", "json", "github"]), default="text")
@click.option("--fix-hints/--no-fix-hints", default=True)
@click.option("--update-lifecycle", is_flag=True, default=False)
@click.option("--schemas-dir", type=click.Path(exists=False), default=None)
@click.option("--readme", type=click.Path(exists=False), default=None)
@click.option("--summary", is_flag=True, default=False)
def lint_cmd(paths, version, mode, output_format, fix_hints, update_lifecycle, schemas_dir, readme, summary):
    if version:
        click.echo(LINTER_VERSION)
        raise SystemExit(0)

    try:
        repo_root = Path.cwd()
        resolved_schemas_dir = Path(schemas_dir) if schemas_dir else repo_root / "schemas"
        resolved_readme = Path(readme) if readme else repo_root / "README.md"
        if not resolved_schemas_dir.exists():
            raise click.UsageError(f"schemas directory not found: {resolved_schemas_dir}")

        target_paths = _resolve_lint_targets(paths, mode, resolved_readme)
        findings_by_path: dict[Path, list[Finding]] = {}
        had_fail = False

        for target in target_paths:
            path = target.resolve()
            markdown = path.read_text()
            sections = extract_sections(markdown)
            frontmatter = extract_yaml_frontmatter(markdown)
            ctx = CheckContext(
                schemas_dir=resolved_schemas_dir.resolve(),
                readme_path=path,
                mode=mode or "strict",
                frontmatter=frontmatter,
                git_head=_git_head(repo_root),
                now=datetime.now(timezone.utc),
                update_lifecycle=update_lifecycle,
            )
            findings: list[Finding] = []
            for check in ALL_CHECKS:
                findings.extend(check(sections, ctx))
            findings_by_path[path] = findings
            had_fail = had_fail or any(finding.severity == "FAIL" for finding in findings)

        _emit_findings(findings_by_path, output_format=output_format, summary=summary, fix_hints=fix_hints)
    except click.ClickException as exc:
        raise SystemExit(exc.exit_code)
    except OSError as exc:
        click.echo(f"usage error: {exc}", err=True)
        raise SystemExit(2)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"internal error: {exc}", err=True)
        raise SystemExit(3)

    raise SystemExit(1 if had_fail else 0)


@click.command()
@click.argument("system_name")
@click.option("--owner", default="max")
@click.option("--dry-run", is_flag=True)
def new_cmd(system_name, owner, dry_run):
    if not validate_system_name(system_name):
        click.echo("invalid system_name: must match [a-z0-9][a-z0-9-]*[a-z0-9]", err=True)
        raise SystemExit(2)

    output_path = Path.cwd() / f"{system_name}.md"
    scaffold = generate_scaffold(system_name, owner)
    if dry_run:
        click.echo(scaffold)
        raise SystemExit(0)

    if output_path.exists():
        click.echo(f"refusing to overwrite existing file: {output_path}", err=True)
        raise SystemExit(1)

    output_path.write_text(scaffold)
    click.echo(str(output_path))
    raise SystemExit(0)


@click.command()
@click.option("--mode", type=click.Choice(["conformant", "probationary"]), default="conformant")
@click.option("--session", default=None)
@click.option("--runbook", default=None, type=click.Path(exists=False))
@click.option(
    "--external-scenario-set",
    "external_scenario_set",
    default=None,
    type=click.Path(exists=False),
    help="Use scenarios from an external YAML file or directory instead of §I.",
)
@click.option(
    "--external-scenarios-from-state",
    "external_scenarios_from_state",
    default=None,
    help="Materialize scenarios from a Living State entity's body.scenarios and use as external set.",
)
def harness_cmd(mode, session, runbook, external_scenario_set, external_scenarios_from_state):
    if external_scenario_set and external_scenarios_from_state:
        click.echo(
            "--external-scenario-set and --external-scenarios-from-state are mutually exclusive",
            err=True,
        )
        raise SystemExit(2)

    repo_root = Path.cwd()
    session_id = session or f"LOCAL-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
    run_started_at = datetime.now(timezone.utc)
    runbook_paths = [Path(runbook)] if runbook else _resolve_harness_targets(mode, repo_root / "README.md")

    dispatch_fn = make_council_request_fn()
    external_mode = external_scenario_set is not None or external_scenarios_from_state is not None

    try:
        with ExitStack() as stack:
            external_path = _resolve_external_source(
                external_scenario_set,
                external_scenarios_from_state,
                stack,
            )
            exit_code = _run_harness_loop(
                runbook_paths=runbook_paths,
                repo_root=repo_root,
                session_id=session_id,
                run_started_at=run_started_at,
                dispatch_fn=dispatch_fn,
                external_path=external_path,
                external_mode=external_mode,
            )
    except click.UsageError as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(2)

    raise SystemExit(exit_code)


def _run_harness_loop(
    *,
    runbook_paths: list[Path],
    repo_root: Path,
    session_id: str,
    run_started_at: datetime,
    dispatch_fn: Callable[[str, dict[str, Any]], Any],
    external_path: Path | None,
    external_mode: bool,
) -> int:
    overall_exit = 0
    for runbook_path in runbook_paths:
        config = ScenarioLoadConfig(
            runbook_path=runbook_path,
            scenarios_dir=_default_scenarios_dir(repo_root),
            external_set_path=external_path,
        )
        try:
            scenarios = load_scenarios(config)
        except ConfigurationError as exc:
            click.echo(str(exc), err=True)
            overall_exit = 1
            continue

        scenario_results: list[dict[str, Any]] = []
        aggregate_score = 0.0
        result = "PASS"
        infra_failure = False
        for scenario in scenarios:
            response = run_dispatch_for_scenario(scenario, runbook_path, dispatch_fn)
            if response.kind == "INFRASTRUCTURE_FAILURE":
                click.echo(response.error or "council_request dispatch failure", err=True)
                score, matched_index, reason = 0.0, None, "dispatch_failure"
                infra_failure = True
            else:
                score, matched_index, reason = score_response(response, scenario)
            aggregate_score += score * scenario.weight
            scenario_results.append(
                {
                    "id": scenario.id,
                    "weight": scenario.weight,
                    "response": _response_to_dict(response),
                    "score": score,
                    "matched_answer_index": matched_index,
                    "reason": reason,
                }
            )

        if infra_failure:
            result = "INFRASTRUCTURE_FAILURE"
            overall_exit = 1
        else:
            result = "PASS" if aggregate_score >= 0.80 else "FAIL"
            if result != "PASS":
                overall_exit = 1

        written = write_result(
            {
                "session_id": session_id,
                "runbook": runbook_path.name,
                "linter_version": LINTER_VERSION,
                "run_started_at": run_started_at.isoformat().replace("+00:00", "Z"),
                "run_finished_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "scenarios": scenario_results,
                "aggregate_score": aggregate_score,
                "pass_threshold": 0.80,
                "result": result,
                "external_mode": external_mode,
            },
            repo_root / "harness" / "results",
        )
        click.echo(str(written))

    return overall_exit


def _resolve_external_source(
    external_scenario_set: str | None,
    external_scenarios_from_state: str | None,
    stack: ExitStack,
    state_reader: Callable[[str], dict[str, Any]] | None = None,
) -> Path | None:
    if external_scenario_set:
        candidate = Path(external_scenario_set)
        if not candidate.exists():
            raise click.UsageError(
                f"--external-scenario-set path does not exist: {candidate}"
            )
        if candidate.is_file() and candidate.suffix.lower() not in {".yaml", ".yml"}:
            raise click.UsageError(
                f"--external-scenario-set must be a YAML file or directory: {candidate}"
            )
        if not candidate.is_file() and not candidate.is_dir():
            raise click.UsageError(
                f"--external-scenario-set must be a YAML file or directory: {candidate}"
            )
        return candidate

    if external_scenarios_from_state:
        reader = state_reader or _default_state_reader
        entity = reader(external_scenarios_from_state)
        return _materialize_state_scenarios(
            external_scenarios_from_state, entity, stack
        )

    return None


def _default_state_reader(entity_key: str) -> dict[str, Any]:
    raise click.UsageError(
        "--external-scenarios-from-state is only supported when a state reader is configured; "
        "pass scenarios via --external-scenario-set or inject a reader in tests"
    )


def _materialize_state_scenarios(
    entity_key: str,
    entity: dict[str, Any],
    stack: ExitStack,
) -> Path:
    body = entity.get("body") if isinstance(entity, dict) else None
    scenarios = None
    if isinstance(body, dict):
        scenarios = body.get("scenarios")
    if scenarios is None:
        raise click.UsageError(
            f"state entity {entity_key} body.scenarios is required for --external-scenarios-from-state"
        )
    if not isinstance(scenarios, list):
        raise click.UsageError(
            f"state entity {entity_key} body.scenarios must be a list"
        )

    tempdir = stack.enter_context(tempfile.TemporaryDirectory(prefix="runbook-harness-external-"))
    tempdir_path = Path(tempdir)
    seen_ids: set[str] = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise click.UsageError(
                f"state entity {entity_key} scenario entries must be objects"
            )
        scenario_id = str(scenario.get("id", "")).strip()
        if not scenario_id or not re.match(r"^[A-Za-z0-9_\-]+$", scenario_id):
            raise click.UsageError(
                f"state entity {entity_key} scenario has unsafe or missing id: {scenario_id!r}"
            )
        if scenario_id in seen_ids:
            raise click.UsageError(
                f"state entity {entity_key} has duplicate scenario id: {scenario_id}"
            )
        seen_ids.add(scenario_id)
        target = tempdir_path / f"{scenario_id}.yaml"
        target.write_text(yaml.safe_dump(scenario, sort_keys=False))
    return tempdir_path


def _resolve_lint_targets(paths: tuple[str, ...], mode: str | None, readme_path: Path) -> list[Path]:
    if paths:
        expanded: list[Path] = []
        for raw in paths:
            candidate = Path(raw)
            if candidate.is_dir():
                expanded.extend(sorted(path for path in candidate.glob("*.md") if path.is_file()))
            else:
                expanded.append(candidate)
        return expanded
    selected_mode = mode or "strict"
    return _runbooks_for_mode(readme_path, selected_mode)


def _resolve_harness_targets(mode: str, readme_path: Path) -> list[Path]:
    selected_mode = "strict" if mode == "conformant" else "probationary"
    return _runbooks_for_mode(readme_path, selected_mode)


def _default_scenarios_dir(repo_root: Path) -> Path:
    primary = repo_root / "harness" / "scenarios"
    if any(primary.rglob("*.yaml")):
        return primary
    return repo_root / "tests" / "fixtures" / "harness_scenarios"


def _runbooks_for_mode(readme_path: Path, mode: str) -> list[Path]:
    rows = _parse_readme_status_rows(readme_path)
    selected_statuses = {
        "strict": {"CONFORMANT"},
        "probationary": {
            "GATE_1_IN_PROGRESS",
            "GATE_1_APPROVED",
            "GATE_2_IN_PROGRESS",
            "GATE_3_IN_PROGRESS",
            "GATE_4_IN_PROGRESS",
        },
        "legacy": {"LEGACY_NOT_UNDER_STANDARD"},
    }[mode]
    return [row["path"] for row in rows if row["status"] in selected_statuses and row["path"] is not None]


def _parse_readme_status_rows(readme_path: Path) -> list[dict[str, Any]]:
    if not readme_path.exists():
        raise click.UsageError(f"README not found: {readme_path}")

    rows: list[dict[str, Any]] = []
    for line in readme_path.read_text().splitlines():
        match = README_STATUS_RE.match(line.strip())
        if match is None:
            continue
        status = match.group("status")
        if status not in VALID_README_STATUSES:
            raise click.ClickException(f"unknown README status value: {status}")
        runbook_cell = match.group("runbook").strip()
        path = _extract_runbook_path(runbook_cell, readme_path.parent)
        rows.append({"status": status, "path": path})
    return rows


def _extract_runbook_path(cell: str, base_dir: Path) -> Path | None:
    link_match = re.search(r"\(([^)]+\.md)\)", cell)
    if link_match is not None:
        return (base_dir / link_match.group(1)).resolve()
    stripped = cell.strip()
    if stripped.endswith(".md"):
        return (base_dir / stripped).resolve()
    return None


def _emit_findings(findings_by_path: dict[Path, list[Finding]], *, output_format: str, summary: bool, fix_hints: bool) -> None:
    flattened = [(path, finding) for path, findings in findings_by_path.items() for finding in findings]
    counts = Counter(finding.severity for _, finding in flattened)

    if output_format == "json":
        payload = [
            {
                "path": str(path),
                "severity": finding.severity,
                "check": finding.check,
                "message": finding.message,
                "line": finding.line,
                "hint": finding.hint if fix_hints else None,
            }
            for path, finding in flattened
        ]
        click.echo(json.dumps(payload, indent=2))
        return

    if not summary:
        for path, finding in flattened:
            line_suffix = f":{finding.line}" if finding.line else ""
            if output_format == "github":
                level = "error" if finding.severity == "FAIL" else "warning"
                message = f"check #{finding.check}: {finding.message}"
                click.echo(f"::{level} file={path}{line_suffix}::{message}")
            else:
                hint = f" hint={finding.hint}" if fix_hints and finding.hint else ""
                click.echo(f"{finding.severity} {path}{line_suffix} check#{finding.check} {finding.message}{hint}")

    if output_format != "github" or summary:
        click.echo(f"Summary: fail={counts['FAIL']} warn={counts['WARN']} info={counts['INFO']}")


def _response_to_dict(response: Response) -> dict[str, Any]:
    payload = {"kind": response.kind}
    if response.tool is not None:
        payload["tool"] = response.tool
    if response.arguments:
        payload["arguments"] = response.arguments
    if response.verb is not None:
        payload["verb"] = response.verb
    if response.object is not None:
        payload["object"] = response.object
    if response.target is not None:
        payload["target"] = response.target
    if response.verdict is not None:
        payload["verdict"] = response.verdict
    if response.label is not None:
        payload["label"] = response.label
    if response.error is not None:
        payload["error"] = response.error
    if response.tool_use_trace is not None:
        payload["tool_use_trace"] = response.tool_use_trace
    return payload


def _git_head(workdir: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=workdir,
            capture_output=True,
            check=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return completed.stdout.strip() or None
