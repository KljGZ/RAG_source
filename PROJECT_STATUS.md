# Project status

Current stage: **Track E fault-containment repair accepted; V6 replacement gated on clean deployment**

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
- [x] The full deterministic static run completed with 240/240 samples, 480 calls,
  zero errors/retries, 296,090 tokens, and exact 16-family × 15-cell coverage.
- [x] Parser-v3 engineering preflights independently passed for Phi-4 and Qwen3-14B:
  each completed 15/15 samples and 30 calls with zero errors/retries and 100% parser,
  answer-type, citation, frozen-input, model-asset, and allocation acceptance.
- [x] Parser-v3 full plans for both models were frozen before either new full-run
  response; each retains the same 240 trials, prompt, decoding, and 14 estimands.
- [x] Both parser-v3 full reruns completed on the same clean revision: each has
  240/240 samples, 480 calls, zero errors/retries, 100% parsing/type/citation validity,
  an accepted 224-effect analysis, and a passed cross-model invariant comparison.
- [x] The Qwen parser-v3 paired-effects artifact exactly reproduced the earlier run's
  SHA-256, while Phi independently exercised the registered fenced-envelope path.
- [x] Raw-log acceptance and the 224-effect analysis publication gates passed; the raw
  eval, observations, paired effects, summary, and manifests agree by SHA-256 on the
  workstation and compute node.
- [x] Inspect task resources are resolved from the project root after validation;
  the initial pre-inference relative-path failure and its remediation are retained.
- [x] Ruff passed, strict checks pass on all changed sources, and Pytest passed 57 tests;
  full Linux Mypy validation is repeated after remote synchronization.
- [x] CPU-only `glmmTMB` synthetic recovery converged with a positive-definite
  Hessian and recovered all five predeclared positive directions.
- [x] All three Qwen3-14B Track E V3 engineering preflights passed exact execution,
  frozen-input, parser, trace, allocation, and zero-retry gates on one clean revision.
- [x] Preflight evidence and raw-log identities were synchronized byte-for-byte and
  retained without pooling their behavioral observations into the full experiment.
- [x] A full-run analysis plan was frozen before any 160-row policy response, with
  explicit missingness, family-cluster, exact-pair, and five-test Holm rules.
- [x] Three hash-bound 160-row full policy plans and an allowlisted GPU-2 controller
  were prepared for sequential hourly execution.
- [x] Amend the missing-record component predicate before full Track E execution.
  Definition `trial_specific_interactive_v2` now requires a successful target-bound
  search to establish absence. Nine model-free semantic gates and three sets of 25
  immutable-log rescore gates passed. Exactly six C5 component values were corrected;
  trigger, call, and strict-completion counts were unchanged.
- [x] Freeze three replacement 160-row V4 plans behind input contract 8, amendment
  003, scorer acceptance, policy-specific rescore evidence, and a 112-file runtime
  manifest. The V5 allowlisted controller uses a new external state directory and
  cannot consume or overwrite the held V4-controller state.
- [x] Retain two integrity-passed V5 policy runs and one integrity-invalid prompted
  run. The invalid prefix, root `KeyError`, cancelled pair, analyzer refusal, and raw
  hashes remain auditable and are not pooled.
- [x] Register amendment 004, convert unknown model-selected snapshot identifiers to
  nonfatal Inspect tool errors, and pass 11 model-free fault-containment gates plus
  single-call, parallel-sibling, and scorer regression tests without importing Torch.
- [x] Freeze three input-contract-9 version-5 plans, a 113-file runtime manifest, and
  the V6 GPU-2-only controller in new run, analysis, and state namespaces.
- [ ] Complete and jointly analyze the 480-row V6 same-revision replacement matrix.

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
- [x] First full 16-family/240-sample V0 static experiment run and reported.
- [x] Parser-v3 full reruns and strict descriptive cross-model comparison run.
- [ ] The 480-trial interactive-verification full matrix run and jointly analyzed.
- [ ] PAVG experiments run after the three baseline policies complete.
- [ ] V1 plan frozen or confirmatory outcomes inspected.

The first exploratory static V0 experiment has run; no paid API call or V1
confirmatory experiment has run. Qwen3-14B showed zero adoption effects for 12/14
contrasts, a -0.5 raw adoption effect for each weaker-warrant contrast, and a 90%
false-verification-assurance rate. Neither warrant contrast survived the registered
14-test Holm correction. These results cannot support a general SDI, PGSD, or model-
quality conclusion. The parser-v3 replication adds Phi-4: false-verification assurance
was 92.5%, twelve contrasts were again exactly zero, and the two warrant effects were
-0.875 with Holm-adjusted p=0.00170898. Both models agree in warrant-effect direction
and show no categorical adoption effect for the tested provenance or proxy cues, but
the saturated binary endpoint prevents equivalence claims. Next gates are interactive
verification, PAVG baselines, graded endpoints, licensed/validated real data, and
independent target/judge registries.

Track E preflight behavior is descriptive only: `no_tools` and `tools_unprompted`
triggered no verification tools in 10/10 trials, while `tools_prompted` triggered in
10/10 trials and made 28 successful calls. None of the prompted traces completed all
seven required components, and all ten prompted posteriors claimed verification.
These values neither gate nor alter the full run. Component-level publication review
subsequently exposed a vacuous missing-record predicate: all three policies marked
their two absent-page cells as having checked existence without a target-bound
successful search. Amendment 003, negative and positive tests, the V2 semantic
acceptance, immutable-log rescoring, and replacement runtime/plan/controller freezing
are now complete. The correction changed exactly those six component values from true
to false and changed no policy's trigger count, call count, or 0/10 strict-completion
count. V5 subsequently completed the no-tools and unprompted-tools policies but the
prompted policy was invalidated when a model-selected direct open of an intentionally
absent C5 document escaped as a fatal `KeyError`. Amendment 004 preserves that call as
a failed behavioral event while routing it through Inspect's recoverable `ToolError`
channel. Because joint analysis requires one Git revision and the tool wrapper is part
of the treatment environment, V6 must regenerate all 480 rows; V5 and V6 observations
will not be mixed. Formal execution remains governed by the independent 46,080 MiB
stable-free-memory gate on physical GPU 2. No V1 or PAVG run is authorized at this
boundary.
