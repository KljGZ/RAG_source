"""Operational CLI. Model execution remains resource-gated."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
import uvicorn
import yaml

from provtrust.audit import audit_repository
from provtrust.datasets.io import read_jsonl
from provtrust.datasets.split import assign_grouped_splits
from provtrust.datasets.validate import validate_trials
from provtrust.execution.allocation import ResourceAllocation, ResourceRequirements
from provtrust.monitoring import Monitor, load_monitor_config
from provtrust.schemas.trial import Trial
from provtrust.web import create_app, ensure_loopback_bind

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


def _json(value: Any) -> None:
    typer.echo(json.dumps(value, ensure_ascii=False, indent=2, default=str))


@app.command()
def audit(
    root: Annotated[Path, typer.Option()] = Path("."),
    strict: Annotated[bool, typer.Option()] = False,
) -> None:
    """Audit scientific registrations, licenses, secrets, and isolation."""

    report = audit_repository(root)
    _json(report.model_dump(mode="json"))
    if not report.passed or (strict and report.warnings):
        raise typer.Exit(code=1)


@app.command("validate-dataset")
def validate_dataset(
    dataset: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    seed: Annotated[int, typer.Option()] = 20260831,
) -> None:
    """Validate schemas and connected-component split leakage."""

    trials = tuple(Trial.model_validate(row) for row in read_jsonl(dataset))
    assignments = assign_grouped_splits(trials, seed=seed)
    report = validate_trials(trials, assignments)
    _json(
        {
            "audit": report.model_dump(mode="json"),
            "assignments": [assignment.__dict__ for assignment in assignments],
        }
    )
    if not report.valid:
        raise typer.Exit(code=1)


@app.command()
def serve(
    host: Annotated[str, typer.Option()] = "127.0.0.1",
    port: Annotated[int, typer.Option(min=1024, max=65535)] = 18080,
    index: Annotated[Path, typer.Option()] = Path("web_env/search_index/documents.jsonl"),
    snapshots: Annotated[Path, typer.Option()] = Path("web_env/source_snapshots"),
    templates: Annotated[Path, typer.Option()] = Path("web_env/sites"),
) -> None:
    """Serve controlled source pages and search on loopback only."""

    ensure_loopback_bind(host)
    uvicorn.run(
        create_app(index_path=index, snapshot_root=snapshots, template_root=templates),
        host=host,
        port=port,
        access_log=True,
    )


@app.command()
def monitor(
    config: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    once: Annotated[bool, typer.Option()] = True,
) -> None:
    """Check/recover only allowlisted project processes."""

    if not once:
        raise typer.BadParameter("continuous loops are disabled; schedule --once externally")
    report = Monitor(load_monitor_config(config)).run_once()
    _json(report)
    if not bool(report["healthy"]):
        raise typer.Exit(code=1)


def _load_object(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise typer.BadParameter(f"expected YAML object: {path}")
    return value


@app.command("run-plan")
def run_plan(
    config: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    dry_run: Annotated[bool, typer.Option()] = True,
    allocation: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """Validate/print an experiment invocation; execution requires allocation."""

    plan = _load_object(config)
    command = plan.get("inspect_command")
    if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
        raise typer.BadParameter("experiment config requires inspect_command as a string list")
    _json({"config": str(config), "dry_run": dry_run, "inspect_command": command})
    if dry_run:
        return
    execution_status = plan.get("execution_status")
    if execution_status != "ready":
        raise typer.BadParameter(
            "experiment plan is not execution-ready: " f"execution_status={execution_status!r}"
        )
    if allocation is None or not allocation.is_file():
        raise typer.BadParameter(
            "actual execution requires a reviewed resource allocation manifest"
        )
    allocation_value = _load_object(allocation)
    reviewed = ResourceAllocation.model_validate(allocation_value)
    requirements = ResourceRequirements.model_validate(plan.get("minimum_resources", {}))
    errors = reviewed.validate_for(
        requirements, stage=str(plan.get("stage", "")), now=datetime.now(UTC)
    )
    if errors:
        raise typer.BadParameter(f"resource allocation failed validation: {', '.join(errors)}")
    environment = os.environ.copy()
    environment.update(
        {
            "CUDA_VISIBLE_DEVICES": ",".join(str(index) for index in reviewed.gpu_indices),
            "OMP_NUM_THREADS": str(len(reviewed.cpu_cores)),
            "PROVTRUST_ALLOCATION_ID": reviewed.allocation_id,
        }
    )
    constrained_command = list(command)
    taskset = shutil.which("taskset")
    if taskset and reviewed.cpu_cores:
        constrained_command = [
            taskset,
            "--cpu-list",
            ",".join(str(index) for index in reviewed.cpu_cores),
            *constrained_command,
        ]
    subprocess.run(constrained_command, check=True, env=environment)


@app.command()
def reproduce(
    manifest: Annotated[Path, typer.Option()], dry_run: Annotated[bool, typer.Option()] = True
) -> None:
    """Replay only commands listed in a publication reproduction manifest."""

    if not manifest.is_file():
        if dry_run:
            _json({"manifest": str(manifest), "status": "not_yet_published", "dry_run": True})
            return
        raise typer.BadParameter("reproduction manifest does not exist")
    value = _load_object(manifest)
    commands = value.get("commands", [])
    if not isinstance(commands, list):
        raise typer.BadParameter("reproduction commands must be a list")
    _json({"manifest": str(manifest), "commands": commands, "dry_run": dry_run})
    if not dry_run:
        for command in commands:
            if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
                raise typer.BadParameter("each reproduction command must be a string list")
            subprocess.run(command, check=True)


if __name__ == "__main__":
    app()
