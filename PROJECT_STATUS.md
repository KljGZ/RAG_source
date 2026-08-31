# Project status

Current stage: **V0 Qwen3-14B compatibility passed; one-sample Inspect pilot ready**

## Deployment state

- [x] Remote host, private SSH key mapping, and canonical GitHub repository configured.
- [x] Python 3.11 Conda environment installed from verified offline payloads.
- [x] Inspect AI, BrowserGym/Playwright, evaluation, formal R statistics, and the
  PyTorch CUDA 13 software layer installed and hash-locked.
- [x] `glmmTMB 1.1.14` and its build-time-compatible `TMB 1.9.19` ABI pair pinned.
- [x] Chromium 125 and FFmpeg installed; loopback Playwright smoke passed with
  `--disable-gpu`.
- [x] Controlled source/search services deployed on `127.0.0.1:18080/18081`.
- [x] Allowlisted monitor validated across repeated runs without duplicate processes.
- [x] No-GPU deployment acceptance passed; Torch was inspected through package
  metadata only and was not imported.
- [x] Physical GPU 2 was uniquely masked to logical `cuda:0`; CUDA 13 / Blackwell
  compute capability 12.0 BF16 probe passed without touching unrelated processes.
- [x] Qwen3-14B loaded fully offline in BF16, generated valid structured JSON with
  thinking disabled, and used 29,619,356,672 peak allocated bytes in the smoke.
- [x] Ruff passed, Mypy passed over 99 source files, and Pytest passed 51 tests.
- [x] CPU-only `glmmTMB` synthetic recovery converged with a positive-definite
  Hessian and recovered all five predeclared positive directions.

## Scientific implementation state

- [x] PGSD/SDI constructs, six normative variables, eight axioms, RQs, endpoints,
  and falsifiability boundaries registered.
- [x] Versioned source/claim/evidence/provenance/trial/run/tool schemas and frozen
  JSON Schema snapshots implemented.
- [x] Connected-component splitting and family/event/root leakage checks implemented.
- [x] Every core Inspect track builds without a model call.
- [x] Operational prior/evidence/posterior sequence implemented for all behavioral
  tracks; L2D has a dedicated numeric two-stage solver/scorer.
- [x] Deterministic 16-cell V0 fractional design, interventions, estimands, tool-trace
  diagnostics, PAVG constraints, checkpointing, retries, sharding, and cost gates implemented.
- [ ] Licensed real datasets and real-source snapshots acquired.
- [x] First target model weights acquired, transferred, and verified byte-for-byte:
  Qwen3-14B, 19 files, 29,552,614,406 bytes.
- [ ] V0 gold claim families annotated and frozen.
- [x] First target model registry, prompt, dataset fixture, and generation settings frozen.
- [x] Physical GPU index 2 allocated by the user for continuous use; CPU use approved.
- [ ] Additional target/judge model registries and any paid API budget approved.
- [ ] V0 empirical experiments run.
- [ ] V1 plan frozen or confirmatory outcomes inspected.

No claim-bearing V0 experiment or API call has run. CUDA and direct-model
compatibility checks have passed. The next authorized step is a one-item, two-call
Inspect orchestration pilot over the harmless smoke fixture; it cannot support an SDI,
PGSD, or model-quality conclusion and is not a V1 confirmatory run.
