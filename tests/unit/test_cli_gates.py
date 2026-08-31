from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from provtrust.cli import app

runner = CliRunner()


def test_blocked_plan_allows_dry_run_but_refuses_execution() -> None:
    path = Path("configs/experiments/v0_static.yaml")
    dry = runner.invoke(app, ["run-plan", "--config", str(path), "--dry-run"])
    assert dry.exit_code == 0
    assert '"dry_run": true' in dry.stdout

    actual = runner.invoke(app, ["run-plan", "--config", str(path), "--no-dry-run"])
    assert actual.exit_code != 0
    assert "experiment plan is not execution-ready" in actual.output


def test_ready_plan_still_requires_reviewed_allocation(tmp_path: Path) -> None:
    path = tmp_path / "ready.yaml"
    path.write_text(
        """\
stage: v0
execution_status: ready
inspect_command: [inspect, eval, harmless-task]
minimum_resources:
  cpu_cores: 1
  ram_gib: 1
  storage_gib: 1
  gpu_count: 0
""",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["run-plan", "--config", str(path), "--no-dry-run"],
        terminal_width=200,
    )
    assert result.exit_code != 0
    assert "requires a reviewed resource allocation manifest" in result.output
