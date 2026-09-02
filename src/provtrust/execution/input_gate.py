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


def _task_argument(command: list[str], name: str) -> str | None:
    matches = [
        value.partition("=")[2]
        for index, value in enumerate(command)
        if index > 0
        and command[index - 1] == "-T"
        and value.partition("=")[0] == name
    ]
    return matches[0] if len(matches) == 1 else None


def _validate_tool_environment(
    manifest: dict[str, Any], root: Path, command: list[str]
) -> tuple[str, ...]:
    errors: list[str] = []
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        return ("tool_environment_files_invalid",)
    observed_paths: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            errors.append("tool_environment_file_entry_invalid")
            continue
        relative = entry.get("path")
        path, error = _project_path(root, relative, label="tool_environment_file")
        if error:
            errors.append(error)
            continue
        assert path is not None
        assert isinstance(relative, str)
        if relative in observed_paths:
            errors.append("tool_environment_file_duplicate")
        observed_paths.add(relative)
        if entry.get("sha256") != sha256_file(path):
            errors.append("tool_environment_file_hash_mismatch")
        if entry.get("bytes") != path.stat().st_size:
            errors.append("tool_environment_file_size_mismatch")

    path_arguments = {
        "search_index_path": "search_index_path",
        "source_registry_path": "source_registry_path",
        "identifier_registry_path": "identifier_registry_path",
        "provenance_registry_path": "provenance_registry_path",
    }
    for manifest_field, task_name in path_arguments.items():
        expected = manifest.get(manifest_field)
        if not isinstance(expected, str) or _task_argument(command, task_name) != expected:
            errors.append(f"tool_environment_command_mismatch:{task_name}")
    snapshot_root = manifest.get("snapshot_root")
    if not isinstance(snapshot_root, str) or Path(snapshot_root).is_absolute():
        errors.append("tool_environment_snapshot_root_invalid")
    else:
        resolved_root = (root / snapshot_root).resolve()
        if root not in resolved_root.parents or not resolved_root.is_dir():
            errors.append("tool_environment_snapshot_root_invalid")
        if _task_argument(command, "snapshot_root") != snapshot_root:
            errors.append("tool_environment_command_mismatch:snapshot_root")

    snapshot_manifest_value = manifest.get("snapshot_manifest_path")
    snapshot_manifest_path, snapshot_error = _project_path(
        root, snapshot_manifest_value, label="tool_environment_snapshot_manifest"
    )
    if snapshot_error:
        errors.append(snapshot_error)
    elif snapshot_manifest_path is not None:
        try:
            snapshot_manifest = json.loads(
                snapshot_manifest_path.read_text(encoding="utf-8")
            )
            entries = snapshot_manifest.get("files")
            if not isinstance(entries, list):
                raise TypeError("snapshot file list missing")
            expected_snapshots = {
                str(entry["path"])
                for entry in entries
                if isinstance(entry, dict) and isinstance(entry.get("path"), str)
            }
            if len(expected_snapshots) != len(entries):
                errors.append("snapshot_manifest_entries_invalid")
            if not expected_snapshots <= observed_paths:
                errors.append("snapshot_manifest_not_covered_by_tool_manifest")
            strict_root = snapshot_manifest.get("strict_root")
            if isinstance(strict_root, str):
                strict_path = (root / strict_root).resolve()
                actual_snapshots = {
                    path.relative_to(root).as_posix()
                    for path in strict_path.rglob("*.txt")
                    if path.is_file()
                }
                if actual_snapshots != expected_snapshots:
                    errors.append("snapshot_root_membership_mismatch")
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            errors.append("snapshot_manifest_parse_failure")
    return tuple(sorted(set(errors)))


def validate_frozen_execution_inputs(plan: dict[str, Any], root: Path) -> tuple[str, ...]:
    """Return stable error codes; an empty tuple authorizes only frozen inputs."""

    root = root.resolve()
    errors: list[str] = []
    resolved: dict[str, Path] = {}
    required_fields = [
        "model_registration",
        "model_asset_manifest",
        "model_args",
        "system_prompt",
        "dataset_manifest",
        "activation_evidence",
    ]
    tool_track = plan.get("track") in {"interactive_verification", "pavg_defense"}
    if tool_track:
        required_fields.append("tool_environment_manifest")
    for field in required_fields:
        path, error = _project_path(root, plan.get(field), label=field)
        if error:
            errors.append(error)
        elif path is not None:
            resolved[field] = path
    if errors:
        return tuple(sorted(set(errors)))

    contract_version = plan.get("input_contract_version")
    if isinstance(contract_version, int) and contract_version >= 2:
        frozen_hash_fields = {
            "model_registration": "model_registration_sha256",
            "model_asset_manifest": "model_asset_manifest_sha256",
            "dataset_manifest": "dataset_manifest_sha256",
            "activation_evidence": "activation_evidence_sha256",
        }
        if tool_track:
            frozen_hash_fields["tool_environment_manifest"] = (
                "tool_environment_manifest_sha256"
            )
        for resolved_field, plan_field in frozen_hash_fields.items():
            expected = plan.get(plan_field)
            if not isinstance(expected, str) or expected != sha256_file(resolved[resolved_field]):
                errors.append(f"frozen_file_hash_mismatch:{resolved_field}")

    try:
        registration = FrozenModelRegistration.model_validate(
            _load_yaml(resolved["model_registration"])
        )
        manifest = ModelAssetManifest.model_validate_json(
            resolved["model_asset_manifest"].read_text(encoding="utf-8")
        )
        model_args = _load_yaml(resolved["model_args"])
        dataset_manifest = _load_yaml(resolved["dataset_manifest"])
        activation_evidence = json.loads(
            resolved["activation_evidence"].read_text(encoding="utf-8")
        )
        if not isinstance(activation_evidence, dict):
            raise TypeError("activation evidence must contain a JSON object")
        tool_environment = (
            _load_yaml(resolved["tool_environment_manifest"])
            if tool_track
            else None
        )
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
    if activation_evidence.get("status") != "passed":
        errors.append("activation_evidence_not_passed")
    activation_asset = activation_evidence.get("model_asset")
    if not isinstance(activation_asset, dict) or activation_asset.get("root_sha256") != (
        manifest.root_sha256
    ):
        errors.append("activation_model_root_hash_mismatch")

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
    for path_field, hash_field in (
        ("config_path", "config_sha256"),
        ("splits_path", "splits_sha256"),
        ("audit_path", "audit_sha256"),
    ):
        if path_field not in dataset_manifest and hash_field not in dataset_manifest:
            continue
        support_path, support_error = _project_path(
            root, dataset_manifest.get(path_field), label=f"dataset_{path_field}"
        )
        if support_error:
            errors.append(support_error)
        elif support_path is not None and dataset_manifest.get(hash_field) != sha256_file(
            support_path
        ):
            errors.append(f"dataset_{path_field}_hash_mismatch")
    source_hashes = dataset_manifest.get("source_code_sha256")
    if source_hashes is not None:
        if not isinstance(source_hashes, dict) or not source_hashes:
            errors.append("dataset_source_code_hashes_invalid")
        else:
            for relative, expected in source_hashes.items():
                source_path, source_error = _project_path(
                    root, relative, label="dataset_source_code"
                )
                if source_error:
                    errors.append(source_error)
                elif (
                    source_path is not None
                    and (not isinstance(expected, str) or sha256_file(source_path) != expected)
                ):
                    errors.append("dataset_source_code_hash_mismatch")

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
        if tool_track:
            assert isinstance(tool_environment, dict)
            errors.extend(_validate_tool_environment(tool_environment, root, typed_command))
            expected_tool_manifest = resolved["tool_environment_manifest"].relative_to(
                root
            ).as_posix()
            if dataset_manifest.get("tool_environment_manifest") != expected_tool_manifest:
                errors.append("dataset_tool_environment_manifest_mismatch")
            if dataset_manifest.get("tool_environment_manifest_sha256") != sha256_file(
                resolved["tool_environment_manifest"]
            ):
                errors.append("dataset_tool_environment_hash_mismatch")
            if dataset_manifest.get("environment_version") != tool_environment.get(
                "environment_version"
            ):
                errors.append("tool_environment_version_mismatch")
            if _task_argument(typed_command, "system_prompt_path") != expected_prompt_relative:
                errors.append("inspect_system_prompt_path_mismatch")
            policy = dataset_manifest.get("interactive_policy")
            if plan.get("track") == "interactive_verification" and (
                not isinstance(policy, str)
                or _task_argument(typed_command, "policy") != policy
            ):
                errors.append("interactive_policy_mismatch")
    return tuple(sorted(set(errors)))
