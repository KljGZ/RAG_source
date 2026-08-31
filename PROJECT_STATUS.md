# Project status

Current stage: **V0 deployment accepted; empirical execution resource-gated**

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
- [x] Ruff passed, Mypy passed over 97 source files, and Pytest passed 42 tests.
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
- [ ] Licensed real datasets, real-source snapshots, and model weights acquired.
- [ ] V0 gold claim families annotated and frozen.
- [ ] Exact model registry and any paid API budget approved.
- [ ] GPU index/time window allocated by the user.
- [ ] V0 empirical experiments run.
- [ ] V1 plan frozen or confirmatory outcomes inspected.

No model/API call, CUDA probe, GPU allocation, or empirical experiment has run. The
next authorized step is resource assignment followed by a small compatibility/cost
pilot; it is not a V1 confirmatory run.
