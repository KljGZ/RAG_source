"""Pre-execution validation of frozen model, prompt, and dataset inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from provtrust.execution.atomic_io import sha256_file
from provtrust.execution.model_assets import ModelAssetManifest, verify_model_asset_manifest
from provtrust.registries.models import FrozenModelRegistration


def _project_path(root: Path, value: Any, *, label: str) -> tuple[Path | None, str | None]:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return None, f"{label}_must_be_relative"
    root = root.resolve()
    path = (root / value).resolve()
    if path == root or root not in path.parents:
        return None, f"{label}_path_escape"
    if not path.is_file():
        return None, f"{label}_missing"
    return path, None


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML object: {path}")
    return value


def _command_option(command: list[str], flag: str) -> str | None:
    positions = [index for index, value in enumerate(command) if value == flag]
    if len(positions) != 1 or positions[0] + 1 >= len(command):
        return None
    return command[positions[0] + 1]


def validate_frozen_execution_inputs(plan: dict[str, Any], root: Path) -> tuple[str, ...]:
    """Return stable error codes; an empty tuple authorizes only frozen inputs."""

    root = root.resolve()
    errors: list[str] = []
    resolved: dict[str, Path] = {}
    for field in (
        "model_registration",
        "model_asset_manifest",
        "model_args",
        "system_prompt",
        "dataset_manifest",
    ):
        path, error = _project_path(root, plan.get(field), label=field)
        if error:
            errors.append(error)
        elif path is not None:
            resolved[field] = path
    if errors:
        return tuple(sorted(set(errors)))

    try:
        registration = FrozenModelRegistration.model_validate(
            _load_yaml(resolved["model_registration"])
        )
        manifest = ModelAssetManifest.model_validate_json(
            resolved["model_asset_manifest"].read_text(encoding="utf-8")
        )
        model_args = _load_yaml(resolved["model_args"])
        dataset_manifest = _load_yaml(resolved["dataset_manifest"])
    except (OSError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError):
        return ("frozen_input_parse_failure",)

    expected_asset_relative = resolved["model_asset_manifest"].relative_to(root).as_posix()
    if registration.snapshot.asset_manifest != expected_asset_relative:
        errors.append("registration_asset_manifest_mismatch")
    if sha256_file(resolved["model_asset_manifest"]) != (
        registration.snapshot.asset_manifest_sha256
    ):
        errors.append("asset_manifest_hash_mismatch")
    if manifest.root_sha256 != registration.snapshot.root_sha256:
        errors.append("model_root_hash_registration_mismatch")
    if manifest.file_count != registration.snapshot.file_count:
        errors.append("model_file_count_registration_mismatch")
    if manifest.total_bytes != registration.snapshot.total_bytes:
        errors.append("model_total_bytes_registration_mismatch")

    expected_prompt_relative = resolved["system_prompt"].relative_to(root).as_posix()
    observed_prompt_hash = sha256_file(resolved["system_prompt"])
    if registration.system_prompt.path != expected_prompt_relative:
        errors.append("registration_prompt_path_mismatch")
    if registration.system_prompt.sha256 != observed_prompt_hash:
        errors.append("registration_prompt_hash_mismatch")
    if plan.get("system_prompt_sha256") != observed_prompt_hash:
        errors.append("plan_prompt_hash_mismatch")

    dataset_relative = dataset_manifest.get("path")
    dataset_path, dataset_error = _project_path(root, dataset_relative, label="dataset")
    if dataset_error:
        errors.append(dataset_error)
    elif dataset_path is not None and dataset_manifest.get("sha256") != sha256_file(dataset_path):
        errors.append("dataset_hash_mismatch")

    model_root_value = model_args.get("model_path")
    tokenizer_root_value = model_args.get("tokenizer_path")
    model_root = Path(model_root_value).resolve() if isinstance(model_root_value, str) else None
    if model_root is None or not model_root.is_dir():
        errors.append("local_model_root_missing")
    else:
        if model_root.name != registration.deployment_subdirectory:
            errors.append("local_model_subdirectory_mismatch")
        if model_root.name != manifest.root_name:
            errors.append("local_model_manifest_root_name_mismatch")
        errors.extend(verify_model_asset_manifest(model_root, manifest))
    if tokenizer_root_value != model_root_value:
        errors.append("tokenizer_model_root_mismatch")
    required_model_args = {
        "device": "cuda:0",
        "dtype": "auto",
        "local_files_only": True,
        "trust_remote_code": False,
        "low_cpu_mem_usage": True,
        "enable_thinking": registration.generation.enable_thinking,
        "do_sample": registration.generation.do_sample,
        "batch_size": 1,
    }
    for key, expected in required_model_args.items():
        if model_args.get(key) != expected:
            errors.append(f"unsafe_or_mismatched_model_arg:{key}")

    generation_fields = ("temperature", "top_p", "top_k", "max_tokens", "enable_thinking")
    for field in generation_fields:
        if plan.get(field) != getattr(registration.generation, field):
            errors.append(f"generation_registration_mismatch:{field}")
    if plan.get("seed") not in registration.generation.seeds:
        errors.append("generation_registration_mismatch:seed")

    command_value = plan.get("inspect_command")
    command = command_value if isinstance(command_value, list) else []
    if not all(isinstance(value, str) for value in command):
        errors.append("inspect_command_invalid")
    else:
        typed_command = list(command)
        if _command_option(typed_command, "--model") != registration.inspect_model:
            errors.append("inspect_model_registration_mismatch")
        expected_model_args = resolved["model_args"].relative_to(root).as_posix()
        if _command_option(typed_command, "--model-config") != expected_model_args:
            errors.append("inspect_model_args_path_mismatch")
        if isinstance(dataset_relative, str) and f"dataset_path={dataset_relative}" not in typed_command:
            errors.append("inspect_dataset_path_mismatch")
    return tuple(sorted(set(errors)))
