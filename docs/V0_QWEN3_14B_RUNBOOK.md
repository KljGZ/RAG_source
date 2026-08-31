# Qwen3-14B V0 static runbook

This runbook executes the first exploratory, single-model, closed-world static causal
decomposition. It does not authorize a multi-model, real-source, paid-API, or V1
confirmatory claim.

## Frozen identities

- Remote repository: `/home/jkl/projects/RAG_source`
- Conda environment: `/home/jkl/miniforge3/envs/provtrust`
- Physical GPU: `2`; process-visible device: `cuda:0`
- Model: `Qwen/Qwen3-14B`, offline snapshot root SHA-256
  `494ab49926699409cf08e0f127175353082777bb25dc163dd93ed3b55fe1afeb`
- Dataset: 16 families, 15 exact cells per family, 240 samples, SHA-256
  `4ffa52856a67a77d50731843bde8e3c1e978c85999b80962845ee6c572d45028`
- Preflight evidence SHA-256:
  `2ee1f9cc3ad3e735c363fc8ee51b6337f3d90d250aeb6d0da534f397644744e6`
- Full plan SHA-256:
  `ed9bd8f6210af202c06e6613f308dc7d0a9dadefa85b8a2bb96f164eeeb85e2b`

## Minimum and assigned resources

The full sequential run requires one GPU with at least 35 GiB free VRAM, 16 CPU
cores, 64 GiB RAM, 100 GiB writable storage, approximately two GPU-hours, and no API
budget. The machine-local assignment is physical GPU 2, CPU 0–31, 192 GiB RAM, and
1,200 GiB storage. The runner must leave every unrelated process untouched.

## Mandatory gates

From the repository root, first run the strict repository audit, test suite, V2 frozen-
input gate, dry run, model-asset verification, and a GPU identity/free-memory check.
The eval may start only if the plan is `ready`, every input hash matches, physical GPU
2 maps to logical `cuda:0`, and no project run with the same plan identity is active.

The canonical launch command is:

```bash
provtrust run-plan \
  --config configs/experiments/v0_qwen3_14b_paired_v1.yaml \
  --no-dry-run \
  --allocation configs/clusters/allocation.local.yaml
```

The runner supplies `CUDA_VISIBLE_DEVICES=2` from the reviewed allocation. No paid API
key is loaded. Retries are disabled, and all failures remain in the raw Inspect log.

## Monitoring authority

The general hourly heartbeat supervises only allowlisted loopback web/search services.
A separate run-specific hourly monitor may read the frozen plan identity, process
identity, log freshness, sample progress, disk space, and physical GPU 2 metrics. It
must never kill or restart a GPU process, alter the plan/data/model, or infer that an
unrelated process belongs to this project. A stalled or failed run is reported for
manual diagnosis; it is not silently replaced.

## Completion and analysis acceptance

The raw eval must report `success`, 240 unique frozen sample IDs, 16 complete families,
all 15 cells per family, 480 model calls, no retries, a clean Git revision, the exact
plan/model/dataset hashes, and 100% structured parsing, answer-type validity, and
supplied-evidence citation validity. Hypothesis-favorable outcomes are not acceptance
criteria.

After raw-log acceptance, run `scripts/extract_static_results.py` with the exact eval
path and plan hash. The extractor must produce 240 observations and 224 paired effects
(16 families × 14 contrasts), family-level bootstrap intervals, exact sign-flip tests,
Holm-adjusted p-values, and a content-addressed analysis manifest. All reporting must
retain the boundary: one open-weight model plus synthetic closed-world claims is
exploratory evidence, not a general SDI/PGSD conclusion.
