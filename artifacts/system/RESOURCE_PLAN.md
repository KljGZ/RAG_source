# Resource allocation gate

Status: **awaiting user allocation; no GPU work is authorized**

## Minimum allocation to start V0 sequentially

| Resource | Hard minimum | Purpose |
|---|---:|---|
| GPU | 1 exact GPU index, RTX PRO 6000 Blackwell, 96 GB | Open-weight generator/judge compatibility pilot and sequential evaluation |
| GPU time | 100 GPU-hours initial tranche | Compatibility, throughput, cost calibration, then the first V0 shard |
| CPU | 24 assigned logical cores | Retrieval, tool services, preprocessing, scoring, and dataloading |
| RAM | 128 GiB | Model loading headroom plus Arrow/R/Inspect workloads |
| Storage | 1 TiB writable persistent/scratch space | Multiple model revisions, snapshots, logs, checkpoints, and analyses |
| Paid API | USD 0 if all models are local | Closed-model tracks remain disabled until provider access and a hard budget are approved |

This is the smallest scientifically useful allocation for a sequential V0 start. The
100-hour tranche is a gate-controlled first allocation, not a promise that every
4–6-model V0 cell will finish inside it. After the smoke/pilot measures tokens per
second and average tool turns, the cost ledger produces a revised full-stage estimate.

## Recommended allocation

For parallel V0 execution and failure recovery: 2 exact 96-GB GPUs, 48 logical CPU
cores, 256 GiB RAM, 1.5 TiB storage, and 250–400 aggregate GPU-hours. V1 should not be
allocated until V0 design review and preregistration freeze.

## Allocation controls

- The user must name exact GPU indices and an expiration/time window; the host is shared.
- Actual execution requires an ignored `configs/clusters/allocation.local.yaml` that
  validates against the experiment's minimums.
- `provtrust run-plan --no-dry-run` sets `CUDA_VISIBLE_DEVICES` to only the approved
  indices and prefixes the command with `taskset --cpu-list` when available.
- A hard API cost ledger and per-run Inspect limits remain active.
- The monitoring/web services need less than one CPU core and roughly 1 GiB RAM and
  do not justify a separate server.

## Web-server decision

No additional public server is required for V0/V1. The existing compute host serves
the controlled source and search fixtures on remote loopback; researchers access them
only through SSH forwarding. A separate CPU VM is warranted only for later persistent
multi-user annotation or an explicitly approved external-validity stage. Fabricated
sources must never be publicly indexed.
