# Track E V4 full-run controller

## Frozen scope

This controller advances exactly three exploratory V0 plans, sequentially:

1. `interactive-v3-no-tools-full` (160 trials);
2. `interactive-v3-tools-unprompted-full` (160 trials); and
3. `interactive-v3-tools-prompted-full` (160 trials).

The queue therefore contains 480 new trials. The ten-row engineering preflights are
activation evidence only and are not pooled. The full plans, plan hashes, policy
order, analysis plan, runtime-code manifest, model snapshot, datasets, prompt, tools,
seed, decoding, and resource limits are frozen before the first full-run response.

The controller cannot launch V1, PAVG, `tools_gated`, MIRAGE stress, a paid API, a
different model, or a different GPU. A new experiment requires a new committed
controller identity and queue.

## Authority and safety boundary

- Physical GPU: index 2 only, mapped to logical `cuda:0`.
- Launch threshold: two readings at least five seconds apart, each with at least
  45 GiB (46,080 MiB) free.
- Concurrency: one sample and one policy worker at a time.
- Model: the frozen offline Qwen3-14B snapshot only.
- Services: the existing monitor may recover only allowlisted `controlled-web` and
  `controlled-search` processes within its restart limits.
- Process control: identity is established by PID, creation time, command line,
  working directory, plan hash, controller ID, and Git revision. The controller never
  kills a process and never modifies an unrelated process.
- State: operational state is written under
  `/home/jkl/provtrust_runs/track-e-v4-full`, outside Git. Raw eval and generated
  analyses remain in Git-ignored directories. Accepted evidence is synchronized into
  Git only after outcome-independent integrity validation.

## One-shot cycle

Every invocation acquires the external controller lock, verifies its own SHA-256 and
the exact deployed Git revision, runs the allowlisted health monitor, validates the
compiled plan queue, and checks prior state. If one exact worker is alive, it reports
`running` and starts nothing. If no worker is alive, it applies the stable GPU gate,
validates every frozen execution input (including all 29.55 GB of model assets),
repeats the GPU gate, and starts only the next plan.

The detached worker repeats health, concurrency, model-asset, and GPU checks before
model loading. It requires an empty plan-specific log directory, executes with zero
automatic retries, requires exactly one new `.eval` file, and runs the frozen full-run
analyzer. The analyzer accepts a run only on identity, coverage, trace, ledger, and
environment integrity. Triggering, completion, parsing, accuracy, confidence,
abstention, assurance, and effect direction are explicitly excluded from acceptance
gates.

States have the following meaning:

- `deferred`: no model was loaded because GPU or concurrency was temporarily
  unavailable;
- `running`: the exact recorded worker is alive;
- `passed`: one complete 160-row policy run and its analysis passed integrity gates;
- `complete`: all three policy runs passed;
- `blocked`: a frozen-input, identity, execution, log-cardinality, or analysis gate
  failed and requires adjudication.

There is no automatic retry for a failed scientific run. The raw log and state are
retained. A justified replacement must receive a new run identity and amendment.

## Deployment-local configuration

Copy `configs/controller/track_e_v4_full.example.yaml` to the ignored file
`configs/controller/track_e_v4_full.local.yaml`. Replace `REMOTE_USER`, then set the
full deployed commit and the SHA-256 of `scripts/control_track_e_full.py`. The file
must be mode `0600`.

Run one cycle with:

```text
/home/jkl/miniforge3/envs/provtrust/bin/python \
  /home/jkl/projects/RAG_source/scripts/control_track_e_full.py \
  --config /home/jkl/projects/RAG_source/configs/controller/track_e_v4_full.local.yaml \
  --once
```

The hourly heartbeat executes this command exactly once. It stays quiet for an
unchanged healthy `running` or `deferred` state and reports a newly started plan, a
newly passed plan, queue completion, a service recovery, or any blocked/failure
state. It must not edit plan files, allocation files, raw logs, evidence, or state to
force progress.

## Completion analysis

After all three plans pass, run the already-frozen
`scripts/combine_interactive_results.py` once against the three external acceptance
files. It verifies their analysis manifests and exact 160-cell policy matching before
producing policy contrasts and the five-test Holm family registered in
`V0_INTERACTIVE_VERIFICATION_ANALYSIS_PLAN.md`. Combined conclusions remain
single-model, synthetic, closed-world, and exploratory.
