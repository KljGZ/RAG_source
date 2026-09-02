# Parser-v3 matched-size V0 rerun runbook

This runbook executes the registered exploratory reruns for Qwen3-14B and Phi-4. It
does not authorize V1, paid APIs, real-source claims, or population-level inference.

## Frozen identities

- Dataset manifest: `benchmark/manifests/v0-paired-v3.yaml`, SHA-256
  `ef72025e5259ad61d2c647680e8f5be178517eb271a3432a6be3084357337496`.
- Dataset bytes: 16 families × 15 cells = 240 trials, SHA-256
  `4ffa52856a67a77d50731843bde8e3c1e978c85999b80962845ee6c572d45028`.
- Phi-4 plan: `configs/experiments/v0_phi4_paired_v3.yaml`, SHA-256
  `1ddc5d22e396832343ddb32a5d143c2a93bd391f6ce64310be9b7d157e7c9689`.
- Qwen3-14B plan: `configs/experiments/v0_qwen3_14b_paired_v3.yaml`, SHA-256
  `ff15a4c493f98101a2cf2738edb0a8b3d8e8187f5a87260952000d60e409f8b1`.
- Phi-4 model-root SHA-256:
  `5ae5572dbbc916ad0eb44e9e755e3dd345b46262d344c32db38b133b2cd56eeb`.
- Qwen3-14B model-root SHA-256:
  `494ab49926699409cf08e0f127175353082777bb25dc163dd93ed3b55fe1afeb`.
- Physical GPU 2 is the only authorized accelerator and is mapped to logical
  `cuda:0`. Runtime model loading is offline and paid API budget is zero.

## Mandatory launch gates

For each plan, require a clean repository, strict audit with no errors or warnings,
passing tests, an exact model-asset verification, a successful plan dry run, no
active/completed/non-retryable controller entry for the plan hash, and two stable GPU
2 readings. The hard free-memory requirement is 35 GiB; the controller should prefer
at least 45 GiB. Leave unrelated processes and GPUs 0/1 untouched.

The exact launch commands are:

```bash
/home/jkl/miniforge3/envs/provtrust/bin/provtrust run-plan \
  --config configs/experiments/v0_phi4_paired_v3.yaml \
  --no-dry-run \
  --allocation configs/clusters/allocation.local.yaml

/home/jkl/miniforge3/envs/provtrust/bin/provtrust run-plan \
  --config configs/experiments/v0_qwen3_14b_paired_v3.yaml \
  --no-dry-run \
  --allocation configs/clusters/allocation.local.yaml
```

Run only one model at a time on GPU 2. Each plan disables sampling, thinking, and
error retry, uses one connection and one sample at a time, and makes exactly 480 model
calls. Do not alter a frozen plan to record operational state; append controller
events under `artifacts/controller`.

## Completion acceptance

For each raw eval require success, a clean recorded revision, exact dataset/model/
plan hashes, 240 unique frozen sample IDs, 16 complete families, all 15 cells per
family, 480 calls, zero retries/errors, and 100% structured parsing, answer-type
validity, and supplied-evidence citation validity. Favorable behavioral outcomes are
not gates.

After raw-log acceptance, extract observations and 224 paired effects with
`scripts/extract_static_results.py`, then freeze the analysis publication with
`scripts/freeze_static_analysis.py`. Only after both model analyses pass may
`scripts/compare_static_models.py` produce the preregistered descriptive comparison.
The report must retain the boundary that two matched-size open models on synthetic
closed-world claims do not establish general SDI/PGSD behavior or real-world validity.
