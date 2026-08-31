# Project status

Current stage: **Qwen3-14B deterministic preflight passed; 240-sample V0 static run ready**

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
- [x] The native hourly heartbeat is active; its acceptance run found clean Git/locks,
  2,463 GiB free disk, and both allowlisted services healthy with no recovery action.
- [x] No-GPU deployment acceptance passed; Torch was inspected through package
  metadata only and was not imported.
- [x] Physical GPU 2 was uniquely masked to logical `cuda:0`; CUDA 13 / Blackwell
  compute capability 12.0 BF16 probe passed without touching unrelated processes.
- [x] Qwen3-14B loaded fully offline in BF16 with thinking disabled and used
  29,619,356,672 peak allocated bytes in the smoke.
- [x] Typed-answer posterior smoke passed with JSON boolean `true`; its unsupported
  `claimed_verified=true` report is retained as a false-assurance observation.
- [x] The frozen one-item/two-call Inspect pilot completed with 709 tokens, a 1.0
  structured-parse score, and complete allocation/input hashes in the eval log.
- [x] The exact 15-cell/one-family deterministic preflight completed on physical GPU 2:
  15/15 samples, 30 model calls, zero errors/retries, and all frozen-input,
  structured-output, answer-type, citation, and design-coverage gates passed.
- [x] The preflight's 13/15 unsupported verification claims are retained as descriptive
  observations; neither that rate nor answer accuracy was used as an activation gate.
- [x] Inspect task resources are resolved from the project root after validation;
  the initial pre-inference relative-path failure and its remediation are retained.
- [x] Ruff passed, strict checks pass on all changed sources, and Pytest passed 57 tests;
  full Linux Mypy validation is repeated after remote synchronization.
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
- [x] Pre-outcome audit rejected the non-identifying 16-cell maximin scaffold and
  replaced it with a deterministic 15-cell exact paired design.
- [x] All 13 static factors have isolated model-visible channels; recursive audits
  reject collapsed factors, extra-path changes, prior drift, and gold leakage.
- [x] Interventions, estimands, tool-trace diagnostics, PAVG constraints,
  checkpointing, retries, sharding, and cost gates are implemented.
- [ ] Licensed real datasets and real-source snapshots acquired.
- [x] First target model weights acquired, transferred, and verified byte-for-byte:
  Qwen3-14B, 19 files, 29,552,614,406 bytes.
- [x] Sixteen deterministic closed-world V0 gold families and 240 paired trials are
  frozen, hash-verified, balanced, and split without component leakage.
- [x] Compatibility and deterministic-static target registrations, prompt, dataset
  fixture/corpus, and generation settings are independently frozen.
- [x] Physical GPU index 2 allocated by the user for continuous use; CPU use approved.
- [ ] Additional target/judge model registries and any paid API budget approved.
- [ ] Full 16-family/240-sample V0 static experiment run (preflight passed; plan ready).
- [ ] V1 plan frozen or confirmatory outcomes inspected.

No full claim-bearing V0 experiment or paid API call has run. CUDA, direct-model
loading, typed output, the end-to-end Inspect fixture, and the exact one-family static
preflight have passed. The preflight cannot support a general SDI, PGSD, or model-
quality conclusion and is not a V1 confirmatory run. The next scientific gates are the
ready 240-sample static run, licensed/validated real datasets, and additional
target/judge registrations.
