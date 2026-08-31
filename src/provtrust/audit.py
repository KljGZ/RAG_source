"""Repository-level scientific, safety, and reproducibility audit."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict


class AuditReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    checks: dict[str, bool]

    @property
    def passed(self) -> bool:
        return not self.errors


REQUIRED_PATHS = (
    "SCIENTIFIC_REGISTER.yaml",
    "EXPERIMENT_PLAN.lock.yaml",
    "third_party/THIRD_PARTY_MANIFEST.yaml",
    "docs/THREAT_MODEL.md",
    "docs/ETHICS.md",
    "docs/RUNBOOK.md",
    "src/provtrust/schemas/trial.py",
    "src/provtrust/defense/pavg_agent.py",
    "web_env/search_index/documents.jsonl",
)

SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|password|secret|authorization)\s*[:=]\s*['\"]?[A-Za-z0-9_./+-]{12,}"
)


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected YAML object: {path}")
    return value


def audit_repository(root: Path) -> AuditReport:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {}
    missing = [path for path in REQUIRED_PATHS if not (root / path).exists()]
    checks["required_paths"] = not missing
    if missing:
        errors.append(f"required paths missing: {missing}")
    try:
        scientific = _load_yaml(root / "SCIENTIFIC_REGISTER.yaml")
        required_normative = {
            "claim_conditioned_reliability",
            "identity_authenticity",
            "attribution_authenticity",
            "evidence_warrant",
            "source_independence",
            "completed_verification",
        }
        observed = set(scientific.get("normative_variables", []))
        checks["six_normative_variables"] = observed == required_normative
        if observed != required_normative:
            errors.append("scientific register does not contain exactly six normative variables")
        axioms = scientific.get("axioms", {})
        checks["eight_axioms"] = isinstance(axioms, dict) and len(axioms) == 8
        if not checks["eight_axioms"]:
            errors.append("scientific register must contain eight normative axioms")
    except (OSError, ValueError, yaml.YAMLError) as error:
        errors.append(f"scientific register invalid: {error}")
    try:
        third_party = _load_yaml(root / "third_party/THIRD_PARTY_MANIFEST.yaml")
        unsafe_copy = [
            row.get("id")
            for row in third_party.get("resources", [])
            if row.get("license") == "NO-LICENSE-DETECTED" and row.get("copy_code")
        ]
        checks["unlicensed_code_not_copied"] = not unsafe_copy
        if unsafe_copy:
            errors.append(f"unlicensed repositories marked for code copying: {unsafe_copy}")
    except (OSError, ValueError, yaml.YAMLError) as error:
        errors.append(f"third-party manifest invalid: {error}")
    try:
        tracked = subprocess.run(
            ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True
        ).stdout.decode("utf-8").split("\0")
        suspect_files: list[str] = []
        for relative in tracked:
            if not relative or relative.endswith((".png", ".pdf", ".lock")):
                continue
            path = root / relative
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if SECRET_PATTERN.search(text):
                suspect_files.append(relative)
        checks["tracked_secret_scan"] = not suspect_files
        if suspect_files:
            errors.append(f"possible tracked secrets: {suspect_files}")
    except (subprocess.SubprocessError, UnicodeDecodeError) as error:
        warnings.append(f"tracked-secret scan unavailable: {error}")
        checks["tracked_secret_scan"] = False
    index_path = root / "web_env/search_index/documents.jsonl"
    if index_path.is_file():
        unsafe_urls: list[str] = []
        for line in index_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            url = str(json.loads(line)["controlled_url"])
            if not url.startswith(("http://127.0.0.1:", "http://localhost:")):
                unsafe_urls.append(url)
        checks["controlled_urls_loopback"] = not unsafe_urls
        if unsafe_urls:
            errors.append(f"non-loopback controlled URLs: {unsafe_urls}")
    return AuditReport(
        errors=tuple(errors), warnings=tuple(warnings), checks=dict(sorted(checks.items()))
    )
