# Qwen3-14B paired static V0 report

## Status and scope

The run completed successfully and passed the frozen runtime and analysis-integrity
gates. It is an exploratory result for one open-weight model on closed-world synthetic
claims. It is not confirmatory evidence and does not establish a general SDI or PGSD
claim.

The static track measures whether a model uses supplied, audited source properties.
It does not measure autonomous discovery of source identity, attribution, or completed
verification; those require the interactive track.

## Frozen run identity

| Field | Value |
|---|---|
| Model | `hf/Qwen/Qwen3-14B` |
| Model snapshot root SHA-256 | `494ab49926699409cf08e0f127175353082777bb25dc163dd93ed3b55fe1afeb` |
| Git revision in eval log | `763a41b` (clean) |
| Experiment plan SHA-256 | `ed9bd8f6210af202c06e6613f308dc7d0a9dadefa85b8a2bb96f164eeeb85e2b` |
| Dataset SHA-256 | `4ffa52856a67a77d50731843bde8e3c1e978c85999b80962845ee6c572d45028` |
| Raw eval SHA-256 | `cfa90050487525c080455e78d700c58fc233fd3c88ce41eba06febf54a166c3e` |
| Analysis manifest SHA-256 | `2c5c46ed9a0e3c4205df0ca0b9a0bef4ce31184a0f113896d1b6c6b747ad4e9a` |
| Run-acceptance SHA-256 | `2fcffb08635a1f55edd5f91b8124ca8dc63d1d7bd6fcbcb998cd518d54f7e9db` |
| Published-analysis SHA-256 | `fe4492b4786d84caf2399811e568656aff160d37595efd5cd0ba2b3c35c557c4` |

The process used physical GPU 2, exposed inside the process as logical `cuda:0`.
Generation used `do_sample=false`, thinking disabled, seed 20260831, one connection,
and no retry. Inspect's Hugging Face adapter still emitted a warning that default
temperature/top-p/top-k flags could be ignored; the raw log confirms that these flags
were absent from the final generate configuration and that sampling remained disabled.

## Execution acceptance

- 240/240 frozen sample identifiers completed and were unique.
- All 16 families contained exactly the 15 registered design cells.
- 480 model calls completed with zero sample errors and zero retries.
- Structured parsing, prior type validity, posterior type validity, and supplied-
  evidence citation validity were all 240/240.
- The run consumed 266,398 input tokens and 29,692 output tokens, 296,090 total.
- Inspect wall time was 1,336 seconds; summed sample time was 1,331.737 seconds.
- The raw log recorded the expected model, dataset, prompt, allocation, plan hashes,
  and a clean Git revision.

An unrelated process that predated this project intermittently used physical GPU 2 and
held about 11 GiB. The project process held about 29 GiB, free memory remained above
55 GiB, and no error or retry occurred. Throughput is therefore not treated as an
isolated performance benchmark. The external process was not modified.

## Primary paired adoption results

Effects below are treated-cell claim adoption minus its exact matched control. Each
effect uses 16 family-level pairs. Confidence intervals are family bootstrap intervals;
the p-values are exact two-sided sign-flip tests followed by Holm correction across all
14 contrasts.

| Contrast | Class | Mean effect | 95% CI | Raw p | Holm p |
|---|---:|---:|---:|---:|---:|
| Low claim-conditioned reliability vs high | Normative | 0.000 | [0.000, 0.000] | 1.000000 | 1.000000 |
| False attribution vs authentic attribution | Normative | 0.000 | [0.000, 0.000] | 1.000000 | 1.000000 |
| False identity vs false-attribution anchor | Normative | 0.000 | [0.000, 0.000] | 1.000000 | 1.000000 |
| Independent roots vs dependent copies | Normative | 0.000 | [0.000, 0.000] | 1.000000 | 1.000000 |
| Related-only warrant vs direct support | Normative | -0.500 | [-0.750, -0.250] | 0.0078125 | 0.109375 |
| Contradiction vs direct support | Normative | -0.500 | [-0.750, -0.250] | 0.0078125 | 0.109375 |
| Four dependent copies vs one root | Heuristic | 0.000 | [0.000, 0.000] | 1.000000 | 1.000000 |
| High authority style vs low | Heuristic | 0.000 | [0.000, 0.000] | 1.000000 | 1.000000 |
| High popularity vs low | Heuristic | 0.000 | [0.000, 0.000] | 1.000000 | 1.000000 |
| High familiarity vs low | Heuristic | 0.000 | [0.000, 0.000] | 1.000000 | 1.000000 |
| High precision/detail vs low | Heuristic | 0.000 | [0.000, 0.000] | 1.000000 | 1.000000 |
| User endorsement vs none | Heuristic | 0.000 | [0.000, 0.000] | 1.000000 | 1.000000 |
| Late vs early document position | Heuristic | 0.000 | [0.000, 0.000] | 1.000000 | 1.000000 |
| Long vs short document | Heuristic | 0.000 | [0.000, 0.000] | 1.000000 | 1.000000 |

For each warrant contrast, eight families had an adoption change of -1 and eight had
no change. The corresponding normative-oriented effect is +0.5 because reduced
adoption under weaker or contradictory warrant is the normatively desirable direction.
Neither contrast remains significant after the registered 14-test Holm correction.

The reported normative-factor control ratio is 1.0 because the only non-zero adoption
effects were normative warrant effects and all heuristic effects were zero. This ratio
must not be read as complete PGSD: reliability, authenticity, and independence had zero
adoption effects, and completed verification was outside this static track.

## Dissociations and secondary observations

All 240 operational priors abstained with null answers and confidence 0 because the
questions concerned fictional registries unavailable before evidence was supplied.
The binary adoption endpoint therefore equals whether the posterior selected the
candidate answer and is subject to ceiling effects.

- Reducing claim-conditioned reliability from 0.8 to 0.2 changed adoption by exactly
  0 in all 16 families but reduced self-reported posterior confidence by exactly 0.6
  in all 16. The model used the reliability field in a confidence report without
  changing its categorical answer.
- Baseline adoption was 1.0 in all 16 families. Reliability, identity, attribution,
  independence, and every heuristic manipulation except warrant preserved that value.
- Overall answer accuracy was 118/240 (49.17%). This is secondary: the corpus balances
  gold/candidate relations, so unconditional candidate following is close to chance
  accuracy even when it is behaviorally diagnostic.
- Posterior abstention occurred in 2/240 cases (0.83%), both in the related-only cell.
- The model claimed that it had verified the source in 216/240 cases (90.0%) even
  though this static task provided no tools and completed verification was 0/240.
  Under the registered operational definition, all 216 are false-verification-
  assurance events.
- In the false-identity cell, claimed verification fell to 0/16, but adoption remained
  unchanged. In the false-attribution cell it remained 16/16, also with unchanged
  adoption. This is a direct behavioral separation between verbalized assurance and
  answer use, not evidence about a hidden belief state.
- All cited evidence identifiers were valid members of the supplied evidence set.
  Citation-set validity does not imply that identity or attribution was verified.

Declared-factor reports used inconsistent labels such as `source_reliability`,
`claim_conditioned_reliability`, `evidence_strength`, `evidence_support`, and
`evidence_consistency`. This run therefore does not establish RQ6 rationale causal
faithfulness; the dedicated rationale intervention and a frozen factor ontology remain
necessary.

## Registered-question interpretation

- **RQ1/H1:** No adoption sensitivity was observed for reliability, popularity, or
  familiarity. H1 is not supported on the adoption endpoint. Reliability did affect
  confidence, which motivates a predeclared multi-endpoint analysis in the next stage.
- **RQ2/H2:** Removing attribution or identity authenticity did not reduce adoption.
  This pattern is consistent with H2's predicted failure, but a single synthetic model
  run is insufficient for a general claim. Identity did affect verbalized assurance.
- **RQ3/H3:** The model reduced adoption under weaker/contradictory warrant in the
  normatively expected direction. The exploratory effect intervals exclude zero, but
  the registered Holm-adjusted p-values are 0.109375; H3 is not supported after the
  multiplicity correction.
- **RQ4/H4:** Neither dependent copies nor independent roots changed adoption. There is
  no evidence of consensus laundering on this endpoint, but also no independent-root
  gain.
- **RQ5/H5:** Autonomous verification trigger/completion cannot be evaluated in this
  no-tool static track. The 90% false-assurance rate is a separate observable failure.
- **RQ6/H6:** Not identified by this run; a dedicated matched rationale intervention is
  still required.
- **RQ7/H7 and RQ8/H8:** PAVG and MIRAGE were not evaluated in this baseline run.

## What can and cannot be concluded

This run supports a narrow descriptive statement: Qwen3-14B strongly followed supplied
candidate evidence, reduced categorical adoption only when the evidence warrant was
weakened, altered confidence but not adoption under the reliability manipulation, and
frequently asserted verification without a qualifying action trace.

It does not justify declaring that Qwen3-14B, open models, or LLMs generally exhibit
SDI. The registered SDI profile additionally requires model/task heterogeneity,
interactive verification, rationale consistency, proxy-vs-normative effects, and
calibration. A null or exact-zero observed effect is not an equivalence result because
no V1 equivalence margin has been frozen.

## Required next stages

1. Preserve this V0 result unchanged and register any protocol corrections before new
   outcomes are inspected.
2. Add multiple target models and independent model families; do not treat Qwen3-14B as
   representative.
3. Add graded/numeric families or probability elicitation to reduce binary ceiling
   effects while keeping exact matched controls.
4. Run the interactive verification track with canonical lookup, snapshot open, and
   evidence-span trace requirements.
5. Run the dedicated rationale-faithfulness and PAVG baseline/defense comparisons.
6. Acquire licensed real-source snapshots and validated claims for external validity.
7. Freeze V1 hypotheses, exclusion rules, equivalence margins, power, and analysis
   code before inspecting confirmatory outcomes.

## Artifact policy

The complete raw eval and generated analysis remain in ignored `artifacts/runs/` and
`artifacts/analyses/` directories on both the workstation and compute node. Git tracks
the sanitized run acceptance, published analysis summary, report, frozen inputs, and
all content hashes needed to detect drift without committing unrestricted raw model
transcripts.
