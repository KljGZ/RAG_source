from __future__ import annotations

from datetime import UTC, datetime, timedelta

from provtrust.execution.allocation import ResourceAllocation, ResourceRequirements


def allocation(**changes: object) -> ResourceAllocation:
    now = datetime(2026, 8, 31, tzinfo=UTC)
    values: dict[str, object] = {
        "allocation_id": "v0-reviewed",
        "approved": True,
        "approved_by": "research-owner",
        "approved_at": now,
        "expires_at": now + timedelta(days=7),
        "stage": "v0",
        "host": "compute.example",
        "cpu_cores": tuple(range(24)),
        "ram_gib": 128,
        "storage_gib": 1000,
        "gpu_indices": (2,),
        "gpu_model": "RTX PRO 6000 Blackwell",
        "gpu_memory_gib_each": 96,
        "gpu_hours": 100,
        "api_budget_usd": 0,
    }
    values.update(changes)
    return ResourceAllocation.model_validate(values)


def test_reviewed_allocation_satisfies_exact_minimum() -> None:
    requirements = ResourceRequirements(
        cpu_cores=24,
        ram_gib=128,
        storage_gib=1000,
        gpu_count=1,
        minimum_gpu_memory_gib=90,
        estimated_gpu_hours=100,
    )
    now = datetime(2026, 9, 1, tzinfo=UTC)
    assert allocation().validate_for(requirements, stage="v0", now=now) == ()


def test_unapproved_or_undersized_allocation_is_rejected() -> None:
    requirements = ResourceRequirements(
        cpu_cores=24,
        ram_gib=128,
        storage_gib=1000,
        gpu_count=1,
        minimum_gpu_memory_gib=90,
        estimated_gpu_hours=100,
    )
    now = datetime(2026, 9, 1, tzinfo=UTC)
    errors = allocation(
        approved=False,
        cpu_cores=(0,),
        ram_gib=64,
        storage_gib=100,
        gpu_indices=(),
        gpu_model=None,
        gpu_memory_gib_each=0,
        gpu_hours=10,
    ).validate_for(requirements, stage="v0", now=now)
    assert set(errors) == {
        "allocation_not_approved",
        "insufficient_cpu_cores",
        "insufficient_ram",
        "insufficient_storage",
        "insufficient_gpu_count",
        "insufficient_gpu_memory",
        "insufficient_gpu_hours",
    }
