"""Allowlisted process supervision that never touches unrelated jobs."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from datetime import UTC, datetime
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
    startup_grace_seconds: float = Field(default=10.0, ge=0.0, le=60.0)
    stop_grace_seconds: float = Field(default=10.0, ge=0.0, le=60.0)

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
    minimum_free_disk_gib: float = Field(default=10.0, ge=0.0)
    require_clean_git: bool = True
    lock_manifest: Path | None = None
    processes: tuple[ManagedProcess, ...]


def load_monitor_config(path: Path) -> MonitorConfig:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    config = MonitorConfig.model_validate(value)
    project_root = config.project_root.resolve()
    for process in config.processes:
        cwd = process.cwd.resolve()
        if cwd != project_root and project_root not in cwd.parents:
            raise ValueError(f"managed process cwd escapes project root: {process.name}")
    if config.lock_manifest is not None:
        lock_manifest = config.lock_manifest.resolve()
        if lock_manifest != project_root and project_root not in lock_manifest.parents:
            raise ValueError("lock manifest escapes project root")
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
            configured_command = tuple(str(part) for part in value["configured_command"])
            if configured_command != process.command:
                return None
            if candidate.exe() != str(value["actual_executable"]):
                return None
            if tuple(candidate.cmdline()) != tuple(str(part) for part in value["actual_cmdline"]):
                return None
            if candidate.cwd() != str(process.cwd.resolve()):
                return None
            return pid if candidate.is_running() else None
        except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError, psutil.Error):
            return None

    def _healthy(self, process: ManagedProcess, pid: int) -> tuple[bool, str | None]:
        try:
            candidate = psutil.Process(pid)
            if not candidate.is_running() or candidate.status() == psutil.STATUS_ZOMBIE:
                return False, "process_not_running"
            if process.health.kind == "http":
                response = httpx.get(
                    str(process.health.url),
                    timeout=process.health.timeout_seconds,
                    follow_redirects=False,
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

    def _wait_healthy(self, process: ManagedProcess, pid: int) -> tuple[bool, str | None]:
        deadline = time.monotonic() + process.startup_grace_seconds
        last_error: str | None = None
        while True:
            healthy, last_error = self._healthy(process, pid)
            if healthy or time.monotonic() >= deadline:
                return healthy, last_error
            time.sleep(0.25)

    def _start(self, process: ManagedProcess) -> int:
        if self._recent_restart_count(process) >= process.max_restarts_per_hour:
            raise RuntimeError("restart_rate_limit")
        logs = self.config.state_dir / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        stdout = (logs / f"{process.name}.stdout.log").open("ab")
        stderr = (logs / f"{process.name}.stderr.log").open("ab")
        environment = os.environ.copy()
        environment.update(process.environment)
        try:
            candidate = subprocess.Popen(
                list(process.command),
                cwd=process.cwd,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
        finally:
            stdout.close()
            stderr.close()
        managed = psutil.Process(candidate.pid)
        create_time = managed.create_time()
        atomic_write_json(
            self._pid_path(process),
            {
                "pid": candidate.pid,
                "create_time": create_time,
                "configured_command": list(process.command),
                "actual_executable": managed.exe(),
                "actual_cmdline": managed.cmdline(),
            },
        )
        append_jsonl(
            self._restart_path(process),
            {"unix_time": time.time(), "pid": candidate.pid, "reason": "monitor_start"},
        )
        return candidate.pid

    def _stop(self, process: ManagedProcess, pid: int) -> None:
        """Stop only the exact process whose persisted identity still validates."""

        if self._read_managed_pid(process) != pid:
            raise RuntimeError("managed_process_identity_changed")
        candidate = psutil.Process(pid)
        candidate.terminate()
        try:
            candidate.wait(timeout=process.stop_grace_seconds)
        except psutil.TimeoutExpired:
            candidate.kill()
            candidate.wait(timeout=max(process.stop_grace_seconds, 1.0))

    def _verify_lock_manifest(self) -> tuple[bool, str | None]:
        manifest = self.config.lock_manifest
        if manifest is None:
            return True, None
        try:
            manifest = manifest.resolve()
            for line_number, line in enumerate(
                manifest.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if not line.strip():
                    continue
                digest, separator, relative = line.partition("  ")
                if not separator or len(digest) != 64:
                    return False, f"invalid_lock_line:{line_number}"
                target = (manifest.parent / relative).resolve()
                if manifest.parent not in target.parents or not target.is_file():
                    return False, f"lock_target_missing:{relative}"
                observed = hashlib.sha256(target.read_bytes()).hexdigest()
                if observed != digest:
                    return False, f"lock_hash_mismatch:{relative}"
            return True, None
        except OSError as error:
            return False, type(error).__name__

    def _system_checks(self) -> dict[str, object]:
        disk = os.statvfs(self.config.state_dir)
        free_gib = disk.f_bavail * disk.f_frsize / (1024**3)
        disk_ok = free_gib >= self.config.minimum_free_disk_gib
        git_clean = True
        git_error: str | None = None
        if self.config.require_clean_git:
            try:
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=self.config.project_root,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                git_clean = not result.stdout.strip()
            except (OSError, subprocess.SubprocessError) as error:
                git_clean = False
                git_error = type(error).__name__
        locks_ok, lock_error = self._verify_lock_manifest()
        return {
            "healthy": disk_ok and git_clean and locks_ok,
            "free_disk_gib": round(free_gib, 3),
            "minimum_free_disk_gib": self.config.minimum_free_disk_gib,
            "disk_ok": disk_ok,
            "git_clean": git_clean,
            "git_error": git_error,
            "locks_ok": locks_ok,
            "lock_error": lock_error,
        }

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
                        was_running = pid is not None
                        if pid is not None:
                            self._stop(process, pid)
                        pid = self._start(process)
                        healthy, error = self._wait_healthy(process, pid)
                        action = "restarted" if was_running else "started"
                    except (
                        OSError,
                        RuntimeError,
                        psutil.Error,
                        psutil.TimeoutExpired,
                    ) as start_error:
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
        system_checks = self._system_checks()
        report = {
            "schema_version": "1.0.0",
            "checked_at": datetime.now(UTC).isoformat(),
            "healthy": bool(system_checks["healthy"])
            and all((not row["enabled"]) or row["healthy"] for row in records),
            "system_checks": system_checks,
            "processes": records,
        }
        atomic_write_json(self.config.report_path, report)
        append_jsonl(self.config.event_log_path, report)
        return report
