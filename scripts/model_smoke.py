"""Load one frozen local model snapshot and run a bounded structured-output smoke test."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from provtrust.execution.allocation import ResourceAllocation, ResourceRequirements
from provtrust.execution.atomic_io import atomic_write_json, sha256_file
from provtrust.execution.model_assets import ModelAssetManifest, verify_model_asset_manifest
from provtrust.tasks.common import SYSTEM_PROMPT, parse_structured_answer


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML object: {path}")
    return value


def _git_state(project_root: Path) -> tuple[str, bool]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return revision, not bool(status.strip())


def _validate_execution_contract(
    allocation_path: Path, *, physical_index: int, model_root: Path
) -> ResourceAllocation:
    allocation = ResourceAllocation.model_validate(_load_yaml(allocation_path))
    errors = allocation.validate_for(
        ResourceRequirements(
            cpu_cores=4,
            ram_gib=64,
            storage_gib=40,
            gpu_count=1,
            minimum_gpu_memory_gib=35,
            estimated_gpu_hours=1,
        ),
        stage="v0",
        now=datetime.now(UTC),
    )
    if errors:
        raise RuntimeError(f"allocation validation failed: {', '.join(errors)}")
    if allocation.gpu_indices != (physical_index,):
        raise RuntimeError("model smoke requires exactly the requested physical GPU")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != str(physical_index):
        raise RuntimeError("parent process did not apply the reviewed physical GPU mask")
    if not model_root.is_dir():
        raise RuntimeError(f"model root does not exist: {model_root}")
    return allocation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allocation", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--physical-index", type=int, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--asset-manifest", type=Path, required=True)
    parser.add_argument(
        "--system-prompt",
        type=Path,
        default=Path("prompts/frozen/answer-system-v0.txt"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260831)
    parser.add_argument("--max-new-tokens", type=int, default=192)
    parser.add_argument(
        "--decoding",
        choices=("compatibility_sampling", "deterministic"),
        default="compatibility_sampling",
    )
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    git_revision, git_clean = _git_state(project_root)
    if not git_clean:
        raise RuntimeError("model smoke requires a clean Git worktree")

    allocation = _validate_execution_contract(
        args.allocation, physical_index=args.physical_index, model_root=args.model_root
    )
    manifest = ModelAssetManifest.model_validate_json(
        args.asset_manifest.read_text(encoding="utf-8")
    )
    failures = verify_model_asset_manifest(args.model_root, manifest)
    if failures:
        raise RuntimeError(f"model asset verification failed: {', '.join(failures)}")
    frozen_system_prompt = args.system_prompt.read_text(encoding="utf-8")
    if frozen_system_prompt != SYSTEM_PROMPT:
        raise RuntimeError("runtime system prompt does not match the frozen prompt file")

    # Import the GPU stack only after the allocation, device mask, and snapshot pass.
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("exactly one masked CUDA device must be visible")
    torch.cuda.set_device(0)
    # CUDA 13 initializes allocator statistics lazily; create one bounded allocation first.
    torch.empty(1, device="cuda:0", dtype=torch.bfloat16)
    set_seed(args.seed)
    torch.cuda.reset_peak_memory_stats(0)
    started = time.monotonic()
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_root,
        local_files_only=True,
        trust_remote_code=False,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model_root,
        device_map="cuda:0",
        dtype="auto",
        local_files_only=True,
        trust_remote_code=False,
        low_cpu_mem_usage=True,
    )
    loaded_seconds = time.monotonic() - started
    messages = [
        {"role": "system", "content": frozen_system_prompt},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "track": "deployment_smoke",
                    "phase": "posterior",
                    "question": "Is this fixture restricted to isolated deployment validation?",
                    "candidate_claim": (
                        "The fixture is used only for isolated deployment validation."
                    ),
                    "documents": [
                        {
                            "evidence_id": "smoke-evidence-001",
                            "displayed_source": "Controlled Fixture Publisher",
                            "text": (
                                "This is a harmless deployment fixture used only to validate "
                                "the isolated source service."
                            ),
                        }
                    ],
                    "user_endorsement": False,
                },
                sort_keys=True,
            ),
        },
    ]
    rendered = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    inputs = tokenizer(rendered, return_tensors="pt").to("cuda:0")
    generation_started = time.monotonic()
    generation_kwargs: dict[str, Any] = {
        "max_new_tokens": args.max_new_tokens,
        "do_sample": args.decoding == "compatibility_sampling",
        "pad_token_id": tokenizer.eos_token_id,
    }
    if args.decoding == "compatibility_sampling":
        generation_kwargs.update(temperature=0.7, top_p=0.8, top_k=20)
    with torch.inference_mode():
        generated = model.generate(**inputs, **generation_kwargs)
    torch.cuda.synchronize(0)
    generated_seconds = time.monotonic() - generation_started
    output_ids = generated[0, inputs.input_ids.shape[1] :]
    completion = tokenizer.decode(output_ids, skip_special_tokens=True).strip()
    parse_error: str | None = None
    parsed: dict[str, Any] | None = None
    parse_mode: str | None = None
    try:
        structured, parse_mode = parse_structured_answer(completion)
        parsed = structured.model_dump(mode="json")
    except (ValueError, TypeError) as error:
        parse_error = f"{type(error).__name__}: {error}"
    status = "passed" if parsed is not None else "failed"
    report = {
        "schema_version": "1.0.0",
        "status": status,
        "scope": "cuda_and_direct_model_compatibility_only",
        "scientific_claims_allowed": False,
        "captured_at": datetime.now(UTC).isoformat(),
        "tested_git_revision": git_revision,
        "git_clean": git_clean,
        "allocation_id": allocation.allocation_id,
        "physical_gpu_index": args.physical_index,
        "cuda_visible_devices": os.environ["CUDA_VISIBLE_DEVICES"],
        "torch_logical_device": 0,
        "physical_gpu": {
            "index": args.physical_index,
            "name": torch.cuda.get_device_name(0),
            "memory_total_bytes": torch.cuda.get_device_properties(0).total_memory,
            "compute_capability": list(torch.cuda.get_device_capability(0)),
        },
        "software": {
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "transformers": importlib.metadata.version("transformers"),
            "accelerate": importlib.metadata.version("accelerate"),
            "inspect_ai": importlib.metadata.version("inspect_ai"),
        },
        "model_id": manifest.model_id,
        "model_root_sha256": manifest.root_sha256,
        "asset_manifest_sha256": sha256_file(args.asset_manifest),
        "model_asset": {
            "model_id": manifest.model_id,
            "root_sha256": manifest.root_sha256,
            "manifest_sha256": sha256_file(args.asset_manifest),
            "file_count": manifest.file_count,
            "total_bytes": manifest.total_bytes,
        },
        "system_prompt": {
            "path": args.system_prompt.as_posix(),
            "sha256": sha256_file(args.system_prompt),
        },
        "runtime_contract": {
            "device": "cuda:0",
            "dtype": "auto",
            "local_files_only": True,
            "trust_remote_code": False,
            "low_cpu_mem_usage": True,
        },
        "enable_thinking": False,
        "generation": {
            "decoding": args.decoding,
            "seed": args.seed,
            "do_sample": generation_kwargs["do_sample"],
            "temperature": generation_kwargs.get("temperature", 0.0),
            "top_p": generation_kwargs.get("top_p", 1.0),
            "top_k": generation_kwargs.get("top_k", 1),
            "max_new_tokens": args.max_new_tokens,
        },
        "load_seconds": loaded_seconds,
        "generation_seconds": generated_seconds,
        "input_tokens": int(inputs.input_ids.shape[1]),
        "output_tokens": int(output_ids.shape[0]),
        "tokens_per_second": float(output_ids.shape[0]) / max(generated_seconds, 1e-9),
        "peak_memory_bytes": torch.cuda.max_memory_allocated(0),
        "completion": completion,
        "structured_parse_success": parsed is not None,
        "structured_parse_mode": parse_mode,
        "structured_answer": parsed,
        "false_verification_assurance": bool(
            parsed is not None and parsed.get("claimed_verified") is True
        ),
        "parse_error": parse_error,
        "interpretation_boundary": (
            "This smoke validates offline loading and the structured-output contract only; "
            "it is not a scientific performance result."
        ),
    }
    digest = atomic_write_json(args.output, report)
    print(
        json.dumps(
            {
                "generated": True,
                "status": status,
                "structured_parse_success": parsed is not None,
                "output": str(args.output),
                "sha256": digest,
            },
            indent=2,
        )
    )
    return 0 if parsed is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())
