"""Allowlisted process supervision that never touches unrelated jobs."""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import httpx
import psutil
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from provtrust.execution.atomic_io import append_jsonl, atomic_write_json


class HealthCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["process", "http"] = "process"
    url: str | None = None
    timeout_seconds: float = Field(default=5.0, gt=0.0, le=30.0)

    @model_validator(mode="after")
    def require_url(self) -> HealthCheck:
        if self.kind == "http" and not self.url:
            raise ValueError("HTTP health checks require a URL")
        if self.url and not self.url.startswith(("http://127.0.0.1:", "http://localhost:")):
            raise ValueError("monitor health checks are loopback-only")
        return self


class ManagedProcess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(pattern=r"^[a-zA-Z0-9_.-]+$")
    enabled: bool
    command: tuple[str, ...]
    cwd: Path
    environment: dict[str, str] = Field(default_factory=dict)
    restart_policy: Literal["never", "on-failure"] = "on-failure"
    health: HealthCheck = HealthCheck()
    max_restarts_per_hour: int = Field(default=3, ge=0, le=10)

    @model_validator(mode="after")
    def require_command(self) -> ManagedProcess:
        if not self.command:
            raise ValueError("managed process command must not be empty")
        return self


class MonitorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    project_root: Path
    state_dir: Path
    report_path: Path
    event_log_path: Path
    processes: tuple[ManagedProcess, ...]


def load_monitor_config(path: Path) -> MonitorConfig:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    config = MonitorConfig.model_validate(value)
    project_root = config.project_root.resolve()
    for process in config.processes:
        cwd = process.cwd.resolve()
        if cwd != project_root and project_root not in cwd.parents:
            raise ValueError(f"managed process cwd escapes project root: {process.name}")
    return config


class Monitor:
    def __init__(self, config: MonitorConfig) -> None:
        self.config = config
        self.config.state_dir.mkdir(parents=True, exist_ok=True)

    def _pid_path(self, process: ManagedProcess) -> Path:
        return self.config.state_dir / f"{process.name}.pid.json"

    def _restart_path(self, process: ManagedProcess) -> Path:
        return self.config.state_dir / f"{process.name}.restarts.jsonl"

    def _read_managed_pid(self, process: ManagedProcess) -> int | None:
        path = self._pid_path(process)
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            pid = int(value["pid"])
            expected_create_time = float(value["create_time"])
            candidate = psutil.Process(pid)
            if abs(candidate.create_time() - expected_create_time) > 1e-3:
                return None
            expected_executable = Path(process.command[0]).name.casefold()
            actual_executable = Path(candidate.exe()).name.casefold()
            if expected_executable != actual_executable:
                return None
            return pid if candidate.is_running() else None
        except (OSError, ValueError, KeyError, json.JSONDecodeError, psutil.Error):
            return None

    def _healthy(self, process: ManagedProcess, pid: int) -> tuple[bool, str | None]:
        try:
            candidate = psutil.Process(pid)
            if not candidate.is_running() or candidate.status() == psutil.STATUS_ZOMBIE:
                return False, "process_not_running"
            if process.health.kind == "http":
                response = httpx.get(
                    str(process.health.url), timeout=process.health.timeout_seconds, follow_redirects=False
                )
                if response.status_code != 200:
                    return False, f"health_http_{response.status_code}"
            return True, None
        except (psutil.Error, httpx.HTTPError) as error:
            return False, type(error).__name__

    def _recent_restart_count(self, process: ManagedProcess) -> int:
        path = self._restart_path(process)
        if not path.is_file():
            return 0
        cutoff = time.time() - 3600.0
        count = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                if float(json.loads(line)["unix_time"]) >= cutoff:
                    count += 1
            except (ValueError, KeyError, json.JSONDecodeError):
                continue
        return count

    def _start(self, process: ManagedProcess) -> int:
        if self._recent_restart_count(process) >= process.max_restarts_per_hour:
            raise RuntimeError("restart_rate_limit")
        logs = self.config.state_dir / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        stdout = (logs / f"{process.name}.stdout.log").open("ab")
        stderr = (logs / f"{process.name}.stderr.log").open("ab")
        environment = os.environ.copy()
        environment.update(process.environment)
        candidate = subprocess.Popen(
            list(process.command),
            cwd=process.cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
        create_time = psutil.Process(candidate.pid).create_time()
        atomic_write_json(
            self._pid_path(process),
            {"pid": candidate.pid, "create_time": create_time, "command": list(process.command)},
        )
        append_jsonl(
            self._restart_path(process),
            {"unix_time": time.time(), "pid": candidate.pid, "reason": "monitor_start"},
        )
        return candidate.pid

    def run_once(self) -> dict[str, object]:
        records: list[dict[str, object]] = []
        for process in self.config.processes:
            pid = self._read_managed_pid(process)
            action = "none"
            error: str | None = None
            healthy = False
            if pid is not None:
                healthy, error = self._healthy(process, pid)
            if process.enabled and (pid is None or not healthy):
                if process.restart_policy == "on-failure":
                    try:
                        pid = self._start(process)
                        healthy, error = self._healthy(process, pid)
                        action = "started"
                    except (OSError, RuntimeError, psutil.Error) as start_error:
                        error = str(start_error)
                        action = "start_failed"
            elif not process.enabled:
                action = "disabled"
            records.append(
                {
                    "name": process.name,
                    "enabled": process.enabled,
                    "pid": pid,
                    "healthy": healthy,
                    "action": action,
                    "error": error,
                }
            )
        report = {
            "schema_version": "1.0.0",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "healthy": all((not row["enabled"]) or row["healthy"] for row in records),
            "processes": records,
        }
        atomic_write_json(self.config.report_path, report)
        append_jsonl(self.config.event_log_path, report)
        return report
