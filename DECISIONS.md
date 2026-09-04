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

## 2026-08-31 — First static V0 outcome boundary

- Accept the full Qwen3-14B run only on execution and coverage integrity, never on
  hypothesis-favorable outcomes. The accepted run contains 240 samples, 480 calls,
  zero errors/retries, and 224 exact family-level contrasts.
- Preserve the registered multiplicity result: both warrant contrasts have raw
  effect -0.5 and exact unadjusted p=0.0078125, but Holm-adjusted p=0.109375. They are
  not reported as multiplicity-adjusted significant.
- Treat the 90% false-verification-assurance rate and the reliability confidence/
  adoption dissociation as scoped exploratory observations. Do not declare general
  SDI from one model, synthetic static claims, or a no-tool condition.
- Keep raw eval and generated analysis outside Git while tracking their SHA-256-backed
  acceptance, sanitized analysis publication, and full report. Do not modify this V0
  protocol after seeing outcomes; register any next-stage changes before new results.

## 2026-09-01 — Cross-family V0 replication

- Select Microsoft Phi-4 as the second target before generating any benchmark output.
  Its 14.66B dense architecture approximately matches Qwen3-14B scale while coming
  from an independently developed family; this remains an exploratory two-model
  comparison, not a population-level or V1 claim.
- Execute the 21-file ModelScope snapshot resolved at
  `d767c0535ebfc0c3d8f049e06f6739eb9e8a2847`. Verify every local payload hash and the
  six Microsoft weight hashes; exclude only mutable ModelScope downloader metadata
  (`.msc`, `.mv`, and partial-download state) from the portable model root.
- Retain both failed Phi-4 direct-load smokes. The model loaded successfully and
  produced schema-valid objects, but wrapped each entire response in one lowercase
  `json` Markdown fence, which the v1 raw-JSON-only parser correctly rejected.
- Version parser v2 before benchmark access. Accept raw JSON or exactly one whole-
  response lowercase `json` fence, preserve the raw completion, and record the parse
  mode. Continue to reject surrounding prose, multiple/nested/unlabeled fences,
  malformed JSON, unknown fields, and schema violations.
- Preserve the published Qwen parser-v1 manifest against its exact historical Git
  revision. Run both Qwen3-14B and Phi-4 again under the same parser-v2 manifest before
  strict cross-model comparison; do not silently mix execution manifests.
- Enforce the 35-GiB free-memory launch gate even when the reviewed GPU has sufficient
  total capacity. Preexisting jobs are read-only observations and are never stopped,
  resized, or reclassified as project processes.

## 2026-09-01 — Remote child-executable resolution

- Retain the first Phi-4 parser-v2 preflight launch as a pre-model engineering
  failure. The absolute `provtrust` entry point ran in a non-login SSH shell, but
  `taskset` could not resolve the plan's `inspect` child because that shell omitted
  the active Conda `bin` directory from `PATH`; no Inspect log or model output was
  produced and no retry budget was consumed.
- Resolve a reviewed plan's executable from the inherited `PATH` first and then from
  the directory of the active Python interpreter before applying CPU affinity. Do
  not modify the frozen experiment plan or rely on an interactive-shell activation.
- Cover both the active-environment fallback and unknown-executable refusal with
  regression tests before repeating the full preflight gate sequence.

## 2026-09-01 — Hourly experiment-control authority

- Upgrade the hourly heartbeat from service-only observation to a bounded V0
  experiment controller after explicit user authorization. It may launch and
  supervise only hash-valid, allocation-valid, local open-weight plans already marked
  `ready`; it may never start V1, paid APIs, GPU 0/1, or an unregistered plan.
- Store operational launch/running/completed/failed state outside frozen scientific
  plans. Do not mutate a plan merely to signal process state because its SHA-256 is an
  execution identity. A protocol may change a plan to a blocked status only through a
  committed, versioned amendment that retains the historical revision.
- Never infer ownership from GPU presence alone. Control only processes identified by
  project command, PID, and plan hash, and leave all unrelated processes untouched.
  Respect plan retry limits; a zero-retry output-contract failure stops automatically.

## 2026-09-01 — Parser-v3 preflight amendment

- Retain the completed Phi-4 parser-v2 preflight as failed: all 15 priors and all 15
  posteriors contained a schema-valid leading `json` fence followed by one
  `Explanation:` paragraph. Parser v2 correctly rejected the surrounding prose, so
  no accuracy, assurance, or behavioral result is extracted from that run.
- Version parser v3 as a model-general structured envelope, not a Phi-specific
  postprocessor. In addition to v2 forms, it accepts exactly one leading lowercase
  `json` fence, a blank line, and one non-empty `Explanation:` suffix. It still rejects
  leading/arbitrary prose, empty explanations, multiple or nested fences, malformed
  JSON, unknown fields, and schema violations; raw output and parse mode are retained.
- Mark both parser-v2 preflight plans blocked, preserve their manifest at execution
  revision `58b5cbc`, and require new Phi-4 and Qwen3-14B parser-v3 preflights before
  either full run or strict cross-model comparison.

## 2026-09-01 — Parser-v3 full-run activation

- Accept both parser-v3 engineering preflights only after their registered validators
  passed every frozen-input, model-asset, allocation, Git, sample, call-count, parser,
  answer-type, citation, and zero-retry gate. The Inspect headline score is legacy
  answer correctness and is not used as a parsing or activation metric.
- Retain the preflight behavioral observations without treating them as scientific
  effects: Phi-4 produced 14/15 and Qwen3-14B 13/15 unsupported verification
  assurances, while neither run contained a completed verification tool trace.
- Freeze separate 240-sample parser-v3 full plans for both models before either full
  outcome is generated. Require both full reruns and integrity-accepted analyses
  before the preregistered descriptive cross-model comparison.

## 2026-09-01 — Retain parser-v3 cross-model V0 outcomes

- Retain both complete full runs and all null/non-null results. Both models produced
  exact-zero categorical adoption effects for twelve contrasts and negative warrant
  effects; Qwen's two warrant effects did not survive Holm correction, while Phi's
  did. Do not use this heterogeneity to replace either target or analysis.
- Treat the 90.0% Qwen and 92.5% Phi false-verification-assurance rates as replicated
  static action-language mismatches, not as proof of hidden beliefs or autonomous
  verification inability.
- Do not claim proxy dominance: every registered heuristic adoption contrast was
  zero. Do not claim broad PGSD: reliability, identity, attribution, and independence
  were also zero, and the binary baseline adoption rate was saturated.
- Record that Qwen's parser-v3 paired-effects artifact exactly matches its historical
  paired-effects SHA-256. This validates result preservation for raw-JSON outputs but
  does not remove the requirement to retain both versioned raw logs.

## 2026-09-02 — Track E identification and activation boundary

- Freeze the interactive development matrix before model output: 16 independent
  families, five diagnostic source states, paired low/high risk, and separate
  `no_tools`, `tools_unprompted`, and `tools_prompted` policies. Defer the structured
  gate and PAVG until these baselines finish so forced verification is not mistaken
  for intrinsic capability.
- Treat risk within a `paired_scene_id` and policy on matched cells as identified
  interventions. Do not interpret C1--C5 marginal differences as a pure authenticity
  effect because candidate truth, warrant, identity, attribution, page existence,
  identifier validity, and temporal claims co-vary by construction.
- Define completion from the actual tool transcript only. Require canonical source
  resolution, canonical and presented-record search checks, a hash-verified canonical
  snapshot, identifier match/non-match, an exact canonical evidence span, and the
  necessary temporal/provenance check. Verbal assurance and search alone are
  insufficient.
- Require a model-free acceptance for each policy dataset before GPU execution. The
  three acceptances passed 1,120 trial-level semantic checks each and verified both
  loopback services against the frozen 81-document index without loading a model or
  CUDA.
- Gate the 10-row preflights only on execution integrity. Tool triggering,
  completion, model-selected tool errors, accuracy, abstention, confidence, and false
  assurance remain observable behavior and cannot be used to accept, retry, or reject
  a preflight.

## 2026-09-02 — Track E full-run release boundary

- Accept all three hybrid-parser preflights because every registered engineering gate
  passed, not because of their behavior. Retain the descriptive pattern: no tool was
  triggered without an explicit verification prompt; prompting triggered all ten
  trials and 28 successful calls, but completed no strict seven-component trace and
  produced ten unsupported verification assurances.
- Do not alter the dataset, prompt, policy matrix, completion rule, model, decoding,
  or sample order in response to this pattern. Exclude every preflight response from
  full-run estimates and generate all 160 rows again for each policy.
- Freeze answer-missingness and trace-recomputation rules before the full run. Trace
  outcomes retain the 160-trial denominator; parse-dependent outcomes use explicit
  observed denominators and never silently encode a parse failure as a substantive
  zero or false value.
- Use family-cluster bootstrap intervals and family-level sign flips for paired risk
  and policy contrasts. Apply Holm only to the five analysis-plan tests; keep all
  other p-values secondary and never interpret a degenerate zero effect as
  equivalence.
- Authorize the V4 controller to advance exactly the no-tools, unprompted-tools, and
  prompted-tools 160-row plans, sequentially on physical GPU 2 after two stable
  45-GiB free-memory readings. It may recover only the existing allowlisted services,
  cannot kill a process, and cannot launch V1, PAVG, gated, paid-API, other-model, or
  MIRAGE work.

## 2026-09-03 — Public V0 data release and Track E scorer hold

- Publish audit-safe structured data from V0 through the accepted Track E preflights:
  480 static observations, 448 family-level paired effects, all 28 model-contrast
  summaries, and 30 interactive preflight observations with component/tool summaries.
  Do not publish raw prompts, free-text model messages, tool payloads, or unrestricted
  `.eval` archives; retain their paths, byte sizes, and SHA-256 identities in Git.
- During component-level publication review, retain the discovery that
  `presented_record_existence_checked` can pass for an absent page when no search was
  attempted. This is a scorer semantic defect, not a new model outcome. It does not
  change any retained preflight's overall `completed=false` value because every such
  trial lacks multiple other mandatory components.
- Hold the outcome-free 480-trial matrix before execution. Require an engineering
  amendment, target-bound negative-absence semantics, regression tests, refreshed
  runtime/plan hashes, and rescoring of the retained preflight logs before re-enabling
  the V4 launch controller. Preserve the independent 45-GiB stable GPU-memory gate.
- Keep the hourly heartbeat active as a service/integrity monitor while the hold is
  in effect, but remove its authority to invoke `control_track_e_full.py` or start any
  model process. This reversible hold prevents an old frozen scorer from producing
  formal outcomes if GPU 2 becomes free unexpectedly.

## 2026-09-03 — Accept scorer V2 correction and release replacement Track E queue

- Register amendment 003 before any formal Track E response. Define absent presented
  records as checked only when a successful list-valued `controlled_search` query
  explicitly contains the trial's presented `document_id` and every such result omits
  that identifier. Reject no call, unrelated search, failed search, invalid output, or
  a contradictory hit.
- Accept the correction because all nine model-free semantics gates and all 25 gates
  on each immutable-log rescore passed. The only component changes are the two C5 rows
  per policy. Preserve the original logs and V1 scorer metadata; never overwrite or
  relabel them.
- Record that rescore definition IDs changed for all 30 rows, but behavioral trace
  invariants did not: trigger counts remain 0, 0, and 10; tool-call counts remain 0,
  0, and 28; strict completion remains 0/10 for every policy. These preflight values
  remain engineering observations and are excluded from formal estimates.
- Supersede the unexecuted V3 full plans with input-contract-8 V4 plans. Bind amendment
  003, policy-specific rescore evidence, the model-free scorer acceptance, and the
  112-file V2 runtime manifest. Use a V5 controller and new state/output directories;
  retain the old controller and state for audit only.
- Restore hourly launch authority only to the exact V5 queue and only after deployment
  at a clean bound revision. Preserve the two-reading 46,080-MiB GPU-2 gate, sequential
  policy order, zero automatic retries, and all existing process/service boundaries.

## 2026-09-03 — Retain V5 failure and freeze fault-contained replacement

- Retain the V5 `no_tools` and `tools_unprompted` full runs as integrity-passed
  exploratory artifacts. Retain the V5 `tools_prompted` raw log as integrity-invalid:
  an intentional missing-reference item caused a model-selected direct
  `open_snapshot` call, whose store-level `KeyError` escaped the wrapper and cancelled
  the paired sample. Do not treat the subsequent missing-model-usage analyzer error
  as the root cause and do not infer a prompted-policy effect from the censored prefix.
- Classify the direct open as behavioral misuse but the fatal propagation as a tool
  fault-containment defect. Map only an unknown document to Inspect `ToolError` with a
  deterministic JSON `not_found` message. Keep the call failed; do not count it as a
  successful absence check or weaken amendment 003. Preserve all other exceptions as
  fatal infrastructure failures.
- Accept the repair only after a model-free mixed-parallel call proves that the failed
  missing open and valid canonical open are both retained, the valid hash matches,
  trace accounting records one failure and one success, and strict completion remains
  false. Bind the exact Inspect version and runtime sources in the acceptance artifact.
- Generate all three policies again under one clean V6 revision rather than combining
  the new prompted run with old-revision controls. This preserves the frozen combined
  analyzer's same-revision contract and avoids selective replacement. Never mix the
  V5 and V6 observations; disclose that amendment 004 follows observed V5 outcomes.
