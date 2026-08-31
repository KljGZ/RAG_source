# Runbook

## Bootstrap and checks

```bash
source /home/jkl/miniforge3/etc/profile.d/conda.sh
conda activate provtrust
python -m pip install --no-deps -e .
make lint
make test
make audit
python scripts/export_schemas.py --output-dir benchmark/schemas
```

## Controlled service

The service must remain on loopback:

```bash
provtrust serve --host 127.0.0.1 --port 18080
curl --fail http://127.0.0.1:18080/healthz
```

Reach it from the local machine only through the checked-in SSH mapping described in
`docs/REMOTE_SETUP.md`.

## Monitor

```bash
provtrust monitor --config configs/monitoring/remote.local.yaml --once
```

Only commands listed in that file are managed. The monitor verifies PID creation
time, the observed executable/command line, current configuration, lock hashes, Git
cleanliness, and free disk. It rate-limits restarts, writes an audit report/event log,
and never touches a process whose persisted identity no longer matches. The deployed
machine-local filename is `configs/monitoring/remote.local.yaml`.

## No-GPU deployment acceptance

With both loopback services healthy:

```bash
PLAYWRIGHT_BROWSERS_PATH=/home/jkl/provtrust_cache/ms-playwright \
LIBGL_ALWAYS_SOFTWARE=1 \
python scripts/browser_smoke.py \
  --output artifacts/system/BROWSER_SMOKE.remote.json

python scripts/deployment_acceptance.py \
  --root /home/jkl/projects/RAG_source \
  --prefix /home/jkl/miniforge3/envs/provtrust \
  --browser-root /home/jkl/provtrust_cache/ms-playwright \
  --output artifacts/system/DEPLOYMENT_ACCEPTANCE.remote.json

Rscript analysis/r/synthetic_recovery.R \
  artifacts/system/STATISTICS_RECOVERY.remote.json
```

The acceptance script reads Torch/CUDA distribution metadata but never imports Torch,
creates a CUDA context, loads a model, or executes an experiment.

## Experiment gate

Dry-run validation is allowed before resource allocation:

```bash
provtrust run-plan --config configs/experiments/v0_static.yaml --dry-run
```

Actual execution requires an untracked, user-approved allocation manifest:

```bash
provtrust run-plan \
  --config configs/experiments/v0_static.yaml \
  --no-dry-run \
  --allocation configs/clusters/allocation.local.yaml
```

Copy `configs/clusters/allocation.example.yaml` to
`configs/clusters/allocation.local.yaml`, fill exact CPU/GPU indices, approval and
expiry, and keep it ignored. The CLI masks all unallocated GPUs with
`CUDA_VISIBLE_DEVICES` and constrains CPU affinity with `taskset` when available.
Allocation alone does not make a plan runnable: its checked-in `execution_status`
stays blocked until the exact dataset/prompt/model revisions and their hashes are
reviewed. Only then may a separate reviewed commit change it to `ready`.

No V1 run starts until `EXPERIMENT_PLAN.lock.yaml` is frozen, hashed, committed, and
tagged before outcomes are inspected.

## Failure handling

- Do not delete failed attempts or retry until only a success remains.
- Resume through the checkpoint store; never overwrite a completed run directory.
- On API budget exhaustion, stop before issuing the next request.
- On service failure, inspect the allowlisted monitor log and exact run manifest.
- On dataset/hash drift, create a new dataset version; do not update a manifest in
  place after results exist.
