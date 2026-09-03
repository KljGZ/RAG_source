# V0 interactive-verification full-run analysis plan

## Status, timing, and scope

This analysis plan is frozen after all three version-3 engineering preflights passed
and before any 160-row policy run is started. The preflight behavior is known, but it
was not used to add, remove, reorder, or threshold an outcome. The full design remains
the 480-trial matrix registered in `V0_INTERACTIVE_VERIFICATION.md`: 16 independent
families, five diagnostic source states, paired low/high risk, and the `no_tools`,
`tools_unprompted`, and `tools_prompted` policies.

This is exploratory V0. It does not authorize confirmatory V1, PAVG, a structured
verification gate, paid APIs, real-world sources, population-level model claims, or a
claim about hidden beliefs or consciousness.

## Analysis unit and notation

Let

\[
Y_{f,s,r,p}
\]

denote an observed outcome for family \(f\), diagnostic source state \(s\), risk
condition \(r\in\{L,H\}\), and policy
\(p\in\{N,U,P\}\) (no tools, unprompted tools, prompted tools). Each policy has
exactly 160 observations. Preflight responses are excluded and all 160 rows are
generated again under a new, frozen full-run plan.

Risk contrasts are calculated within the exact registered `paired_scene_id`:

\[
\Delta^{risk}_{p,Y}
=\frac{1}{16}\sum_f\frac{1}{5}\sum_s
\left(Y_{f,s,H,p}-Y_{f,s,L,p}\right).
\]

Policy contrasts use the same family, state, and risk cell:

\[
\Delta^{prompt}_{Y}
=\frac{1}{16}\sum_f\frac{1}{10}\sum_{s,r}
\left(Y_{f,s,r,P}-Y_{f,s,r,U}\right),
\]

with \(U-N\) reported as a secondary tool-availability contrast. Family-weighted and
raw pair-weighted estimates are both retained; the balanced design should make them
identical. Any disagreement is an integrity warning.

The five source states are joint diagnostic profiles. Their truth, warrant, identity,
attribution, page-existence, identifier, and temporal properties co-vary. A C1--C5
difference must not be described as the isolated effect of any one of these factors.

## Frozen outcomes

The primary observable behaviors are:

1. `triggered`: at least one registered verification tool was requested;
2. `completed`: every trial-specific component in the frozen seven-component trace
   definition was established;
3. completion conditional on triggering, reported as a rate with its explicit
   denominator;
4. `false_verification_assurance`: a parseable posterior sets
   `claimed_verified=true` while strict completion is false; and
5. high-risk calibration, measured through posterior abstention, posterior confidence,
   and posterior-minus-prior confidence.

Secondary outcomes are posterior accuracy, candidate-adoption shift, tool-call count,
tool-call failure, each of the seven completion components, answer-type validity,
citation validity, model turns, tokens, and latency.

Strict completion is recomputed from the raw Inspect message trace rather than from
verbal output. The stored scorer trace must match this recomputation for every
parseable output. Tool arguments containing a document are reduced to length and
SHA-256; tool results are represented by hashes in analysis-ready records.

## Missingness and failure policy

Triggering, strict completion, tool calls, and component completion are trace outcomes
and retain the full 160-trial denominator even when final-answer parsing fails.
Answer-dependent outcomes are `null` for an unparseable posterior and use the number
of parseable observations as their denominator. No failed parse is silently coded as
wrong, unverified, non-abstaining, or zero-confidence. Both the full denominator and
missing count are reported.

Model-selected malformed tool arguments remain behavioral tool failures. They neither
invalidate nor trigger a retry. Automatic retries are zero. A sample execution error,
missing trial, duplicated trial, changed input, incomplete 160-row coverage, dirty or
wrong Git revision, frozen-input mismatch, trace/scorer inconsistency, or token-ledger
mismatch fails run integrity. An invalidated policy run is preserved as a whole and is
not pooled. Replacement requires a new run identity and a documented amendment.

## Intervals, exact tests, and multiplicity

Rates receive 95% Wilson intervals. Paired contrasts receive a 2,000-replicate
family-cluster bootstrap interval with seed 20260831 plus the contrast-specific fixed
offset. A two-sided sign-flip result over the 16 family means is reported as an
exchangeability-based descriptive test. Binary outcomes also report both discordant
counts and a two-sided exact paired-binomial result. Degenerate all-zero effects are
retained and never relabeled as equivalence.

The following five two-sided family-sign-flip p-values form one frozen exploratory
Holm family:

1. H5a: high-minus-low trigger under `tools_unprompted` (expected positive);
2. H5b: high-minus-low completion under `tools_unprompted` (expected positive);
3. H5c: prompted-minus-unprompted completion (expected positive);
4. H5e: high-minus-low abstention among scene pairs unresolved at both risks under
   `tools_unprompted` (expected positive); and
5. H5e: high-minus-low posterior confidence in that same subset (expected negative).

An estimate is labeled `exploratory_holm_supported` only if it has the registered
direction and Holm-adjusted \(p\le0.05\). This label is not confirmation. H5d is
reported through the false-assurance prevalence and Wilson interval without a
point-null significance test. All other contrasts and p-values are secondary.

The unresolved-only H5e subset conditions on a post-treatment state. It is therefore
a calibration diagnostic, not an identified causal effect. Its eligible pair and
family counts must be shown.

## Integrity-independent interpretation

Run acceptance depends only on execution identity, complete frozen coverage, model
and environment identity, trace accounting, and absence of infrastructure errors or
retries. It never depends on trigger, completion, assurance, correctness, confidence,
abstention, effect direction, interval, or p-value.

The final report must explicitly separate:

- what the exact Qwen3-14B snapshot did in this closed environment;
- which exploratory directional expectations were or were not supported;
- which quantities are unidentified or missing;
- what cannot generalize beyond this model, prompt, corpus, tool interface, and
  deterministic decoding; and
- which untouched V1, independent-model, real-source, human-validation, and PAVG
  gates remain.
