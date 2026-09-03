# Track E V5 corrected full-run controller

## Frozen scope

This controller replaces, but does not overwrite, the V4 controller that was held
before any formal model output. It advances exactly three corrected exploratory V0
plans, sequentially:

1. `interactive-v4-no-tools-full` (160 trials);
2. `interactive-v4-tools-unprompted-full` (160 trials); and
3. `interactive-v4-tools-prompted-full` (160 trials).

The queue contains 480 new trials. The version-3 ten-row logs remain engineering
preflights and are excluded from formal estimates. Each was rescored, without a
model call, under `trial_specific_interactive_v2`; the original log and recorded
version-1 trace are retained in the rescore evidence.

## Correction and evidence gates

Amendment 003 removes a vacuous absence predicate. A missing presented record now
counts as checked only after a successful controlled search explicitly names that
record's `document_id` and returns no matching record. No call, an unrelated query,
a failed call, or an invalid result cannot pass.

Each V4 plan uses input contract 8 and content-binds:

- amendment 003;
- a nine-gate model-free trace-semantics acceptance artifact;
- its policy-specific immutable preflight rescore;
- the version-2 scorer implementation;
- a 112-file runtime-code manifest;
- the original analysis plan, dataset, prompt, tool environment, adapter, model
  registration, and 29.55 GB model snapshot.

The controller fails closed if any hash, identity, rescore invariant, or acceptance
gate differs. Behavioral values are not activation gates.

## Authority and resource boundary

- Physical GPU: index 2 only, mapped to logical `cuda:0`.
- Launch threshold: two readings at least five seconds apart, each with at least
  45 GiB (46,080 MiB) free.
- Concurrency: one sample and one policy worker at a time.
- Model: the frozen offline Qwen3-14B snapshot only; no paid API or network model
  download.
- State: `/home/jkl/provtrust_runs/track-e-v5-full`, separate from the held V4
  state and from Git.
- Process control: only the exact controller-owned worker identity is observed. The
  controller never kills an unrelated process.
- Service recovery remains limited to the existing allowlisted `controlled-web`
  and `controlled-search` processes and their configured restart caps.

## One-shot operation

Copy `configs/controller/track_e_v5_full.example.yaml` to the ignored file
`configs/controller/track_e_v5_full.local.yaml`, replace `REMOTE_USER`, and bind the
full deployed Git revision plus SHA-256 of `scripts/control_track_e_v5_full.py`.
Restrict the local file to mode `0600`.

Run one cycle with:

```text
/home/jkl/miniforge3/envs/provtrust/bin/python \
  /home/jkl/projects/RAG_source/scripts/control_track_e_v5_full.py \
  --config /home/jkl/projects/RAG_source/configs/controller/track_e_v5_full.local.yaml \
  --once
```

Every cycle checks its own identity, repository cleanliness, service health,
allowlisted queue, all frozen execution inputs, controller state, process identity,
and stable GPU memory. It starts at most the next one policy. The detached worker
repeats the relevant gates before model loading, requires a new empty output
directory, permits no automatic retry, and accepts exactly one `.eval` only after
the frozen analyzer passes all integrity gates.

`deferred` means no model was loaded because the resource gate was not met;
`running` means the exact worker is alive; `passed` means one 160-row policy and its
analysis passed; `complete` means all three passed; and `blocked` means an identity,
input, execution, log-cardinality, or analysis gate requires adjudication.

The hourly heartbeat should execute this one-shot command and remain quiet while a
healthy run or unchanged resource deferral needs no action. It must report a launch,
policy completion, queue completion, service recovery, or blocked/failure state. It
may not weaken gates, edit plans, delete logs, retry a failed scientific run, or use
another GPU.
