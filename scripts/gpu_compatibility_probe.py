"""Run a bounded CUDA/BF16 probe under an explicitly reviewed GPU allocation."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from provtrust.execution.allocation import ResourceAllocation, ResourceRequirements
from provtrust.execution.atomic_io import atomic_write_json


def _query_gpu(physical_index: int) -> dict[str, Any]:
    command = [
        "nvidia-smi",
        f"--id={physical_index}",
        "--query-gpu=index,uuid,name,memory.total,memory.free,utilization.gpu,driver_version",
        "--format=csv,noheader,nounits",
    ]
    line = subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip()
    values = [value.strip() for value in line.split(",")]
    if len(values) != 7:
        raise RuntimeError(f"unexpected nvidia-smi GPU response: {line!r}")
    return {
        "physical_index": int(values[0]),
        "uuid": values[1],
        "name": values[2],
        "memory_total_mib": float(values[3]),
        "memory_free_mib": float(values[4]),
        "utilization_percent": float(values[5]),
        "driver_version": values[6],
    }


def _query_compute_processes(gpu_uuid: str) -> list[dict[str, Any]]:
    command = [
        "nvidia-smi",
        "--query-compute-apps=gpu_uuid,pid,used_gpu_memory,process_name",
        "--format=csv,noheader,nounits",
    ]
    output = subprocess.run(command, check=True, capture_output=True, text=True).stdout
    processes: list[dict[str, Any]] = []
    for line in output.splitlines():
        values = [value.strip() for value in line.split(",", maxsplit=3)]
        if len(values) != 4 or values[0] != gpu_uuid:
            continue
        processes.append(
            {
                "gpu_uuid": values[0],
                "pid": int(values[1]),
                "used_memory_mib": None if values[2] == "N/A" else float(values[2]),
                "process_name": values[3],
            }
        )
    return processes


def _load_allocation(path: Path) -> ResourceAllocation:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("allocation manifest must contain a YAML object")
    return ResourceAllocation.model_validate(value)


def _validate_preconditions(
    allocation: ResourceAllocation,
    *,
    physical_index: int,
    minimum_free_gib: float,
    gpu: dict[str, Any],
) -> None:
    errors = allocation.validate_for(
        ResourceRequirements(
            cpu_cores=1,
            ram_gib=1,
            storage_gib=1,
            gpu_count=1,
            minimum_gpu_memory_gib=1,
            estimated_gpu_hours=0.01,
        ),
        stage="v0",
        now=datetime.now(UTC),
    )
    if errors:
        raise RuntimeError(f"allocation validation failed: {', '.join(errors)}")
    if allocation.gpu_indices != (physical_index,):
        raise RuntimeError(
            "probe requires an allocation containing only the requested physical GPU: "
            f"allocation={allocation.gpu_indices}, requested={physical_index}"
        )
    visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    if visible != str(physical_index):
        raise RuntimeError(
            "CUDA_VISIBLE_DEVICES must be set by the parent process to the single allocated "
            f"physical index {physical_index}; observed {visible!r}"
        )
    free_gib = float(gpu["memory_free_mib"]) / 1024
    if free_gib < minimum_free_gib:
        raise RuntimeError(
            f"allocated GPU has only {free_gib:.2f} GiB free; {minimum_free_gib:.2f} required"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allocation", type=Path, required=True)
    parser.add_argument("--physical-index", type=int, required=True)
    parser.add_argument("--minimum-free-gib", type=float, default=1.0)
    parser.add_argument("--matrix-size", type=int, default=1024)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    allocation = _load_allocation(args.allocation)
    gpu = _query_gpu(args.physical_index)
    preexisting_processes = _query_compute_processes(str(gpu["uuid"]))
    _validate_preconditions(
        allocation,
        physical_index=args.physical_index,
        minimum_free_gib=args.minimum_free_gib,
        gpu=gpu,
    )

    # Import only after the physical-device mask and reviewed allocation are verified.
    import torch

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError(
            "the reviewed single-device mask must expose exactly one CUDA device to Torch"
        )
    torch.cuda.set_device(0)
    # CUDA 13 initializes allocator statistics lazily; create one bounded allocation first.
    torch.empty(1, device="cuda:0", dtype=torch.bfloat16)
    torch.manual_seed(20260831)
    torch.cuda.manual_seed_all(20260831)
    torch.cuda.reset_peak_memory_stats(0)
    left = torch.randn(
        (args.matrix_size, args.matrix_size), device="cuda:0", dtype=torch.bfloat16
    )
    right = torch.randn(
        (args.matrix_size, args.matrix_size), device="cuda:0", dtype=torch.bfloat16
    )
    product = left @ right
    torch.cuda.synchronize(0)
    finite = bool(torch.isfinite(product).all().item())
    if not finite:
        raise RuntimeError("BF16 CUDA matrix multiplication produced non-finite values")
    properties = torch.cuda.get_device_properties(0)
    report = {
        "schema_version": "1.0.0",
        "probe_type": "bounded_cuda_bfloat16_matmul",
        "captured_at": datetime.now(UTC).isoformat(),
        "allocation_id": allocation.allocation_id,
        "physical_gpu": gpu,
        "cuda_visible_devices": os.environ["CUDA_VISIBLE_DEVICES"],
        "torch_logical_device": 0,
        "torch_device": {
            "name": properties.name,
            "compute_capability": [properties.major, properties.minor],
            "total_memory_bytes": properties.total_memory,
        },
        "software": {
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version(),
        },
        "preexisting_compute_processes": preexisting_processes,
        "matrix_size": args.matrix_size,
        "dtype": "bfloat16",
        "finite": finite,
        "result_checksum": float(product.float().mean().item()),
        "peak_memory_bytes": torch.cuda.max_memory_allocated(0),
    }
    digest = atomic_write_json(args.output, report)
    print(json.dumps({"passed": True, "output": str(args.output), "sha256": digest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
