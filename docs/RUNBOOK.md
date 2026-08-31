# Runbook

## Bootstrap and checks

```bash
source /home/jkl/miniforge3/etc/profile.d/conda.sh
conda activate provtrust
python -m pip install --no-deps -e .
make lint
make test
make audit
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
provtrust monitor --config configs/monitoring/remote.yaml --once
```

Only commands listed in that file are managed. The monitor verifies PID creation
time and executable identity, rate-limits restarts, writes an audit report/event log,
and never kills unrelated processes.

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

No V1 run starts until `EXPERIMENT_PLAN.lock.yaml` is frozen, hashed, committed, and
tagged before outcomes are inspected.

## Failure handling

- Do not delete failed attempts or retry until only a success remains.
- Resume through the checkpoint store; never overwrite a completed run directory.
- On API budget exhaustion, stop before issuing the next request.
- On service failure, inspect the allowlisted monitor log and exact run manifest.
- On dataset/hash drift, create a new dataset version; do not update a manifest in
  place after results exist.
