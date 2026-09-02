# Track E V3 hourly controller

## Scope

The controller advances only the following engineering-preflight queue, in order:

1. `interactive-v3-no-tools-preflight`
2. `interactive-v3-tools-unprompted-preflight`
3. `interactive-v3-tools-prompted-preflight`

The names, project-relative plan paths, and SHA-256 digests are compiled into
`scripts/control_track_e.py`. The deployment-local YAML cannot add, remove, reorder, or replace a
plan. These preflights are engineering and observability checks; their behavioral observations are
not confirmatory V1 evidence.

## Authorized resources and actions

- Physical GPU index: `2` only.
- Stable launch gate: at least two readings, at least five seconds apart, each reporting at least
  45 GiB (46,080 MiB) free.
- CPU and storage: the already approved allocation in
  `configs/clusters/allocation.local.yaml`.
- Service recovery: only `controlled-web` and `controlled-search`, and only through the existing
  monitor's allowlist and restart limits.
- Experiment execution: exactly one queued preflight worker at a time.

The controller never kills a process, never uses another GPU, never changes Git state or allocation
files, never edits a plan's `execution_status`, never makes an API call, and never launches V1,
PAVG, gated, or MIRAGE stress-test work.

## One-shot control sequence

Each invocation:

1. acquires an external controller lock;
2. verifies its own file hash and the exact Git revision;
3. runs the deployment monitor once and requires clean Git, matching environment locks, adequate
   disk, and healthy controlled services;
4. verifies the compiled plan queue and any prior worker/evidence state;
5. refuses to proceed when another project interactive evaluation is active;
6. applies the stable 45 GiB GPU gate;
7. validates every frozen execution input, including the 29.55 GB model asset tree;
8. applies the stable GPU gate again;
9. starts one detached worker and records its PID, creation time, exact command line, Git revision,
   and log path.

The worker waits for the parent launch ticket before doing any work. It then repeats the health,
concurrency, frozen-input, and GPU gates immediately before model loading. A completed run must
produce exactly one `.eval` log and pass the frozen preflight validator. State advancement requires
the state record, evidence hash, raw-log hash, plan hash, and revision to agree.

## State semantics

- `deferred`: no model was loaded; a resource or concurrency gate was not satisfied. A future
  hourly invocation may reassess it.
- `running`: the exact recorded worker identity is alive. The controller observes it but starts
  nothing else.
- `passed`: one plan produced exactly one integrity-valid log and evidence record.
- `complete`: all three preflights passed.
- `blocked`: human adjudication is required. The controller does not repair state or retry a failed
  experiment.

Examples of blocking conditions include unreadable state, a dead or replaced worker, an existing
unadjudicated log, Git or lock drift, a failed frozen-input gate, model execution failure, OOM,
unexpected log cardinality, and validation failure.

## Deployment

Copy `configs/controller/track_e_v3.example.yaml` to the ignored
`configs/controller/track_e_v3.local.yaml`, replace `REMOTE_USER`, and set:

- `controller_sha256` to the deployed controller file's SHA-256;
- `expected_git_revision` to the full deployed commit hash.

The local config must remain mode `0600`. Runtime state is deliberately outside Git at
`/home/jkl/provtrust_runs/track-e-v3` and is mode `0700`.

Run exactly one control cycle with:

```text
/home/jkl/miniforge3/envs/provtrust/bin/python \
  /home/jkl/projects/RAG_source/scripts/control_track_e.py \
  --config /home/jkl/projects/RAG_source/configs/controller/track_e_v3.local.yaml \
  --once
```

The hourly automation should execute that one command over the pinned SSH alias and interpret its
JSON report. Repeated healthy `deferred` or `running` reports are non-actionable. Notify on a newly
started plan, a newly passed plan, queue completion, restart/recovery, or any blocked/failure state.

## Failure handling

Do not edit external state to force progress. Preserve the raw worker log, latest report, event log,
state record, evidence record, GPU/process snapshot, plan hash, and Git revision. Diagnose and record
the event in Git. If a replacement run is scientifically and operationally justified, freeze a new
controller/version or an explicit engineering amendment before removing or archiving the old state.
