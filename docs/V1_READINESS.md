# V1 confirmatory scope and readiness

This document records the boundary between exploratory V0 work and a future
confirmatory V1. It is a readiness checklist, **not** a frozen preregistration and
must not be represented as `EXPERIMENT_PLAN.lock.yaml`.

## What V1 is for

V1 is the first outcome-blind, preregistered test of the core PGSD/SDI claims. It is
not a larger rerun of the first model. Before any V1 outcome is inspected, the exact
hypotheses, primary endpoints, factor coding, exclusions, missing-data policy,
equivalence margins, multiplicity procedure, model revisions, prompts, sample sizes,
stopping rules, and analysis commands must be frozen, hashed, committed, and tagged.

The confirmatory design must test whether observable trust behavior is controlled by
verified claim-conditioned reliability, identity authenticity, attribution
authenticity, evidence warrant, source independence, and completed verification, and
whether those normative controls dominate matched proxy cues. It must also test
whether verification assurances correspond to completed tool traces and whether risk
increases actual verification or calibrated abstention.

PAVG defense efficacy and MIRAGE stress testing remain separately versioned stages.
Their exploratory components can inform V1 design, but their outcome claims must not
be silently folded into the core V1 confirmation.

## Evidence currently established by V0

The Qwen3-14B and Phi-4 parser-v3 static V0 runs establish the following facts within
their registered two-model, closed-world scope:

- The 16-family, 15-cell paired design contains 240 unique trials, balanced 120/120
  on claim truth, with invariant priors, isolated intervention channels, no detected
  gold leakage, and no connected-component split leakage.
- The frozen run completed 240/240 samples and 480 model calls with zero sample
  errors or retries. Every structured output parsed, every answer type was valid, and
  every citation referred to supplied evidence.
- Qwen3-14B accuracy was 118/240 (49.17%) and posterior abstention was 2/240 (0.83%).
- Twelve of fourteen registered paired adoption contrasts had a raw mean effect of
  exactly zero in this model and corpus.
- `warrant_contradiction` and `warrant_related` each had a raw mean adoption effect
  of -0.5 with a family-bootstrap interval of [-0.75, -0.25] and an exact unadjusted
  two-sided p-value of 0.0078125. Both Holm-adjusted p-values were 0.109375, so neither
  contrast passed the registered family-wise multiplicity correction.
- The model asserted `claimed_verified=true` in 216/240 cases while the static track
  completed no verification trace, yielding a protocol-defined false-verification-
  assurance rate of 90%.
- Phi-4 independently completed the same 240 trials and 480 calls with zero errors or
  retries and 100% parser, answer-type, and citation validity. Its accuracy was
  116/240 (48.33%), abstention was 6/240 (2.50%), and false-verification assurance was
  222/240 (92.5%).
- Phi-4 also had twelve exact-zero contrasts. Its two warrant effects were each
  -0.875 with a bootstrap interval of [-1.0, -0.6875], exact raw p=0.0001220703125,
  and Holm-adjusted p=0.001708984375.
- Both models agreed on the negative direction of the two warrant effects and were
  exactly equal at zero on the other twelve contrasts. The warrant-effect magnitude
  differed by 0.375. Exact zero is not treated as equivalence.
- The Qwen parser-v3 paired-effects artifact is byte-identical to the historical
  parser-v1 paired-effects artifact, demonstrating result preservation for its raw-
  JSON outputs while retaining both versioned raw logs.

These are integrity-accepted exploratory observations for two open-weight models on a
closed-world synthetic corpus. Citation validity here means that cited evidence IDs
were supplied; it does not mean that source identity, attribution, or warrant was
externally verified.

## Claims not established by V0

V0 does not establish a general SDI diagnosis, general PGSD competence or failure,
population-level cross-model or cross-task effects, real-world external validity,
causal rationale faithfulness, risk-responsive tool use, consensus laundering, PAVG
benefit, or MIRAGE robustness. The static no-tool track cannot identify actual
verification ability, and 16 independent families provide limited power for
heterogeneous effects.

The reported normative-factor control ratio of 1.0 is degenerate in this run: all
heuristic effects were zero and only the two warrant contrasts were nonzero. It must
not be interpreted as broad normative control.

## Gates before freezing V1

- The outcome-blind Phi-4 cross-family replication protocol is fixed in
  `analysis/preregistration/V0_PHI4_REPLICATION.md`; its results remain V0 evidence.
- The matched-size Qwen3-14B/Phi-4 static replication is complete. Add further model
  families only under a separately frozen V0 extension; do not reinterpret two models
  as a model-population sample.
- Run controlled interactive-verification development experiments with identity,
  attribution, identifier, canonical-record, and evidence-span trace checks.
- Validate real-source snapshots, licenses, timestamps, provenance roots, and a
  human-adjudicated confirmatory subset without family/event/root leakage.
- Use V0 only to choose estimands, power assumptions, equivalence margins, diagnostic
  thresholds, and failure policies; retain all null and opposite-direction results.
- Register independent target and judge revisions and ensure that primary conclusions
  do not depend on one LLM judge.
- Freeze the complete V1 plan and untouched confirmatory split before inspecting any
  V1 outcome.
