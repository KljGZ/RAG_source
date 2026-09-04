# Track E V6 fault-contained replacement full-run controller

## Why this is a replacement

The V5 controller retained two integrity-passed version-4 policy runs, then failed
closed when the prompted-tools run encountered an uncaught `KeyError` after 18 normal
samples. The missing document was an intentional C5 condition and the model's direct
open was a behavioral tool error, but the tool wrapper incorrectly allowed that error
to terminate the task. V5 state, evidence, worker logs, and raw evals remain immutable.

Amendment 004 changes only the model-facing exception class for an unknown controlled
document. It maps the strict store-level `KeyError` to a nonfatal Inspect `ToolError`
with a deterministic `not_found` payload. The call remains failed, cannot establish
absence, and does not satisfy any verification component. Digest, path, I/O, index,
and other infrastructure faults remain fatal.

## Frozen replacement scope

The controller advances exactly three version-5 exploratory V0 plans, sequentially:

1. `interactive-v5-no-tools-full` (160 trials);
2. `interactive-v5-tools-unprompted-full` (160 trials); and
3. `interactive-v5-tools-prompted-full` (160 trials).

All 480 rows are generated again because the frozen combined analyzer requires one
Git revision and because tool behavior is part of the policy environment. V4 and V5
observations are never selected, averaged, or mixed. The old passed policy evidence
remains separately reportable; the old prompted prefix remains integrity-invalid.

## Frozen evidence gates

Every plan uses input contract 9 and content-binds:

- the original protocol and frozen full-run analysis plan;
- amendments 001 through 004;
- the unchanged `trial_specific_interactive_v2` scorer and its nine-gate acceptance;
- the 11-gate `open_snapshot_fault_containment_v1` model-free acceptance;
- its policy-specific immutable preflight rescore under amendment 003;
- the 113-file version-3 runtime-code manifest;
- the unchanged dataset, prompt, tool corpus, model registration, and 29.55 GB model
  snapshot.

The controller fails closed on any identity, path, hash, semantic acceptance,
preflight lineage, plan, environment, or output mismatch. Behavioral outcomes are not
activation gates.

## Authority and resources

- Physical GPU: index 2 only, mapped to logical `cuda:0`.
- Launch threshold: two readings at least five seconds apart, each with at least
  45 GiB (46,080 MiB) free.
- Concurrency: one sample and one policy worker at a time.
- Model: frozen offline Qwen3-14B only; no API or network model download.
- State: `/home/jkl/provtrust_runs/track-e-v6-full`, separate from all V4/V5 state.
- Outputs: new version-5 run and analysis directories; they must be absent or empty
  before launch.
- Process control: only the exact controller-owned worker identity may be observed.
  No unrelated user or process may be stopped or changed.
- Service recovery remains limited to allowlisted `controlled-web` and
  `controlled-search` processes and their configured restart caps.

## Deployment and one-shot operation

Copy `configs/controller/track_e_v6_full.example.yaml` to the ignored file
`configs/controller/track_e_v6_full.local.yaml`, replace `REMOTE_USER`, and bind the
full deployed Git revision plus SHA-256 of `scripts/control_track_e_v6_full.py`.
Restrict the local file to mode `0600`.

Before launch, run on the clean deployed revision:

```text
/home/jkl/miniforge3/envs/provtrust/bin/python \
  scripts/validate_open_snapshot_fault_containment.py \
  --output /tmp/open_snapshot_fault_containment_acceptance.json
```

The temporary artifact must be byte-identical to the committed acceptance. Then run
one controller cycle with:

```text
/home/jkl/miniforge3/envs/provtrust/bin/python \
  /home/jkl/projects/RAG_source/scripts/control_track_e_v6_full.py \
  --config /home/jkl/projects/RAG_source/configs/controller/track_e_v6_full.local.yaml \
  --once
```

Every cycle validates controller identity, clean Git state, services, allocation,
compiled queue, all frozen inputs, external state, output emptiness, and stable GPU
memory. It starts at most one next policy. The detached worker repeats the relevant
gates before importing the model and accepts exactly one `.eval` only after the frozen
analyzer passes all integrity gates.

`deferred` means no model was loaded because the GPU threshold was not met; `running`
means the exact worker is alive; `passed` means one complete policy and analysis were
accepted; `complete` means all three passed; and `blocked` means adjudication is
required. There is no automatic retry. In particular, the V5 invalid log must never
be supplied to `eval-retry` or copied into a V6 output directory.

After all three policies pass, execute the unchanged combined analyzer once against
the three V6 evidence artifacts. Preserve the complete report, every null result, and
the disclosure that amendment 004 was written after viewing the prior exploratory
outcomes and failed prefix.
