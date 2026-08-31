# Decision log

## 2026-08-31 — Compute environment

- Use a user-owned Miniforge installation and a Conda environment named
  `provtrust` with Python 3.11.
- Keep GPU, browser, and formal R statistics dependencies as explicit layers.
- Treat the remote host as a single-machine executor because no scheduler or
  container runtime is installed.
- Keep controlled web services private and access them through SSH forwarding.
- Use the USTC conda-forge mirror and a bootstrap-scoped IPv4 resolver shim on
  this node; its sustained IPv6 HTTPS route stalls while IPv4 is healthy.
- Install the hash-locked PyTorch 2.12.1+cu130/CUDA 13 software layer without
  importing Torch or creating a CUDA context. Defer the actual Blackwell CUDA
  compatibility probe until the user assigns an exact GPU index and time window.
- Preserve the exact Linux solve and transfer package payloads from an
  internet-connected workstation when the compute node's outbound HTTPS is
  unavailable. Every payload must pass declared byte-size and SHA-256 checks on
  both sides.
- Install `clubSandwich` 0.7.0 from a hash-locked canonical CRAN source archive
  because the locked conda-forge index has no `r-clubsandwich` package. Keep all
  other formal statistics dependencies in the Conda transaction.
- Lock the BrowserGym 0.14.3 layer to Playwright 1.44, lxml 5.x, and
  Trafilatura 2.0.0. BrowserGym's declared upper bound on lxml and exact
  Playwright requirement conflict with the newest standalone versions, so these
  four packages are treated as one compatibility set.
- Install that BrowserGym compatibility set from Linux Python wheels. The
  Playwright 1.44 Conda build forces a Node/shared-library solve that downgrades
  Arrow 25 to 21 and conflicts with `r-arrow`; the Python wheel contains its own
  driver and leaves the Conda Arrow ABI unchanged.
- Pin `glmmTMB 1.1.14` with `TMB 1.9.19`, the exact build-time ABI reported by
  the package. A CPU synthetic recovery test detected the solver-selected TMB
  1.9.23 mismatch even though fitting succeeded; the compatible pair removes
  the warning and remains frozen in the explicit lock.
- Treat remote outbound HTTPS as unavailable after bootstrap. All subsequent
  third-party archives, browser runtimes, CUDA wheels, and model/data assets use
  local download, declared size/SHA-256 verification, upload, and remote recheck.

## 2026-08-31 — Controlled webpages

- Do not provision a separate public server for V0/V1.
- Bind controlled source, search, and Inspect services to remote loopback and
  reach them through SSH forwarding.
- Consider a separate CPU VM only for persistent multi-user access or an
  explicitly approved external-validity stage.

## 2026-08-31 — Repository strategy

- Use `KljGZ/RAG_source` as the canonical GitHub repository.
- Version at auditable stage boundaries rather than after individual runs.
- Never commit passwords, API keys, model caches, generated poison documents,
  or unrestricted raw run outputs.

## 2026-08-31 — First open-weight compatibility pilot

- Allocate physical CUDA index 2 only. The execution process masks it with
  `CUDA_VISIBLE_DEVICES=2`, so Torch and Inspect correctly address it as logical
  `cuda:0`; every probe and run record retains both identities.
- Use `Qwen/Qwen3-14B` as the first moderate-size target model. It is an
  Apache-2.0, 14.8B-parameter open-weight model that fits a single allocated
  96-GiB GPU in BF16 with substantial safety headroom. It is a compatibility and
  throughput pilot, not a representative multi-model result or a primary judge.
- Acquire the snapshot from the official ModelScope repository because the
  compute node cannot reach Hugging Face. Record ModelScope `master`, capture
  time, every file's SHA-256, and the corresponding official Hugging Face commit
  `cc692f40d59e239c60676c8947c5f9f75493e02b`; content hashes, rather than the
  mutable ModelScope branch name, define the deployed snapshot.
- Disable Qwen thinking mode for this benchmark so latent reasoning-token length
  does not become an uncontrolled source condition. Use the model card's
  non-thinking sampling settings (`temperature=0.7`, `top_p=0.8`, `top_k=20`)
  with fixed seeds and record every parse failure.
- Synchronize the runtime structured-output system prompt with its frozen text
  before the first model call and enforce equality with a regression test. This
  corrects a pre-execution manifest/runtime drift; no empirical outcome had been
  generated under the earlier mismatch.
- Pin Accelerate 1.14.0 in the evaluation layer. The first guarded load exposed
  that Inspect's Hugging Face `device_map` path requires Accelerate; the failed
  attempt stopped before weights were loaded or a model response was generated.
- Re-block the Inspect pilot after the direct smoke returned structurally valid
  JSON but encoded a yes/no answer as string `"Yes"`. Freeze an explicit
  boolean/number/null answer-type contract and rerun the smoke before activation;
  otherwise a formatting mismatch would be counted as substantive model error.

## 2026-08-31 — Deterministic paired V0 activation

- Treat the earlier model-card sampling configuration as compatibility-only. For the
  exact paired static estimand, use deterministic greedy decoding (`do_sample=false`,
  `temperature=0`, fixed seed) so within-model sampling noise does not obscure paired
  stimulus effects.
- Require a one-family preflight covering all 15 exact cells before the 16-family run.
  Activation gates cover execution integrity, frozen inputs, coverage, parse/type/
  citation validity, and error-free completion. Accuracy and hypothesis-favorable
  behavior are explicitly excluded from the gate.
- The preflight passed all gates on physical GPU 2. Preserve the observed 13/15 false
  verification-assurance cases as data; they neither prove SDI nor authorize a general
  model claim.
- Keep the preflight plan and its log immutable. The full-run command omits redundant
  temperature/top-p/top-k CLI flags because Transformers reports them as ignored when
  sampling is disabled; the frozen registration and plan still record their canonical
  deterministic values.
