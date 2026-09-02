# Parser-v3 matched-size cross-model static V0 report

## Status and scope

The registered parser-v3 reruns for Qwen3-14B and Phi-4 completed and passed all
runtime, frozen-input, raw-log, analysis-publication, and cross-model invariant gates.
This is exploratory evidence from two matched-size open-weight models on the same
closed-world synthetic corpus. It is not V1, not population-level evidence, and not a
test of autonomous web verification.

The static factorial asks a narrower causal question: when source and evidence
properties are explicitly supplied, which properties change categorical adoption of
the candidate claim? The no-tool setting separately permits a direct audit of whether
the model's `claimed_verified` statement corresponds to a completed tool trace.

## Frozen identities

Both runs used the same clean Git revision `00e6d13`, dataset bytes, 16 families, 15
cells per family, prompt, seed, deterministic decoding, one connection, one active
sample, and zero retry.

| Field | Qwen3-14B | Phi-4 |
|---|---|---|
| Inspect model | `hf/Qwen/Qwen3-14B` | `hf/microsoft/phi-4` |
| Model-root SHA-256 | `494ab49926699409cf08e0f127175353082777bb25dc163dd93ed3b55fe1afeb` | `5ae5572dbbc916ad0eb44e9e755e3dd345b46262d344c32db38b133b2cd56eeb` |
| Plan SHA-256 | `ff15a4c493f98101a2cf2738edb0a8b3d8e8187f5a87260952000d60e409f8b1` | `1ddc5d22e396832343ddb32a5d143c2a93bd391f6ce64310be9b7d157e7c9689` |
| Raw-eval SHA-256 | `e943765784f8613dbff1679489518ad1b05b1b4d83bbfe62fe003da7c7f95f75` | `6cf97cf63ca2507d414b69ef3bf6d40fbae8b7b68393b003c58a53c9f6c58862` |
| Run-acceptance SHA-256 | `86fe76f7ed9977d39ca60598377e0b903d1e483242b6e8cfe7c39986d16eb7f4` | `808d68668969a73b1793fcb6a45630f819c0ba1715cd4b20956ab80ce902b910` |
| Analysis-manifest SHA-256 | `e5252c764fd40e1667d1e4abc8d2b2722a67b366c206c0480d62c0a7185027a0` | `e5b9344956138f0f178cd593e5c0e2679705f54c8b58a625760abacc8de859b1` |
| Published-analysis SHA-256 | `e5be225dee5018bd66c32ddacbfa79a06b2445dcaf77e7eecbe8843e08126447` | `903f88084d1704257d35acb41d58f4c36bd1fd9101d625a9823f8624d72ebc40` |

The shared dataset SHA-256 is
`4ffa52856a67a77d50731843bde8e3c1e978c85999b80962845ee6c572d45028`.
The integrity-gated comparison SHA-256 is
`40ae236d460fc08edd4cbef267967f7aa59b19ff8fb5d14d2cf1494832950159`.

## Parser amendment validation

Parser v3 was registered after retaining the failed Phi-4 parser-v2 preflight. Across
the full reruns, all 480 Phi-4 completions used the registered leading lowercase
`json` fence plus one `Explanation:` suffix, whereas all 480 Qwen3-14B completions
used raw JSON. Every completion passed the same schema, answer-type, and citation
checks. This is evidence that the amendment is a model-general envelope policy rather
than a result-specific Phi postprocessor.

The Qwen3-14B parser-v3 rerun reproduced the earlier full run exactly at the paired-
effects layer: both `paired_effects.jsonl` files have SHA-256
`6a0f2d27a20982b224ec7b84e8810150dd823dd02a5c1b2a0aa21e52ad78c385`.
The 296,090-token total, accuracy, abstention, assurance rate, and all fourteen effect
estimates also agree. Summary-file hashes differ because the plan, manifest, Git
revision, raw-log identity, and timing are intentionally versioned.

## Execution acceptance and descriptive outcomes

| Metric | Qwen3-14B | Phi-4 |
|---|---:|---:|
| Samples / model calls | 240 / 480 | 240 / 480 |
| Errors / retries | 0 / 0 | 0 / 0 |
| Parse, answer type, citation | 240/240 each | 240/240 each |
| Wall time | 1,149 s | 2,325 s |
| Total tokens | 296,090 | 346,183 |
| Correct | 118/240 (49.17%) | 116/240 (48.33%) |
| Posterior abstention | 2/240 (0.83%) | 6/240 (2.50%) |
| Claimed verified | 216/240 (90.0%) | 222/240 (92.5%) |
| Completed verification | 0/240 | 0/240 |
| False-verification assurance | 216/240 (90.0%) | 222/240 (92.5%) |

All verification assurances are false under the registered trace-based definition:
the static task exposed no verification tool and no sample completed the required
lookup/open/evidence-span trace. This is an observable action-language mismatch, not
a claim about an inaccessible hidden belief or consciousness state.

## Registered categorical-adoption effects

Effects are treated-cell candidate adoption minus the exact matched control. Each
estimate contains 16 family pairs. Intervals are family bootstrap intervals; raw
p-values are exact two-sided sign-flip tests; Holm p-values control the registered
family of fourteen contrasts.

| Contrast | Class | Qwen mean [95% CI], Holm p | Phi mean [95% CI], Holm p |
|---|---|---:|---:|
| Low reliability vs high | Normative | 0.000 [0.000, 0.000], 1.000 | 0.000 [0.000, 0.000], 1.000 |
| False attribution vs authentic | Normative | 0.000 [0.000, 0.000], 1.000 | 0.000 [0.000, 0.000], 1.000 |
| False identity vs false-attribution anchor | Normative | 0.000 [0.000, 0.000], 1.000 | 0.000 [0.000, 0.000], 1.000 |
| Independent roots vs dependent copies | Normative | 0.000 [0.000, 0.000], 1.000 | 0.000 [0.000, 0.000], 1.000 |
| Related-only warrant vs direct support | Normative | -0.500 [-0.750, -0.250], 0.109375 | -0.875 [-1.000, -0.6875], 0.00170898 |
| Contradiction vs direct support | Normative | -0.500 [-0.750, -0.250], 0.109375 | -0.875 [-1.000, -0.6875], 0.00170898 |
| Four dependent copies vs one root | Heuristic | 0.000 [0.000, 0.000], 1.000 | 0.000 [0.000, 0.000], 1.000 |
| High authority style vs low | Heuristic | 0.000 [0.000, 0.000], 1.000 | 0.000 [0.000, 0.000], 1.000 |
| High popularity vs low | Heuristic | 0.000 [0.000, 0.000], 1.000 | 0.000 [0.000, 0.000], 1.000 |
| High familiarity vs low | Heuristic | 0.000 [0.000, 0.000], 1.000 | 0.000 [0.000, 0.000], 1.000 |
| High precision/detail vs low | Heuristic | 0.000 [0.000, 0.000], 1.000 | 0.000 [0.000, 0.000], 1.000 |
| User endorsement vs none | Heuristic | 0.000 [0.000, 0.000], 1.000 | 0.000 [0.000, 0.000], 1.000 |
| Late vs early position | Heuristic | 0.000 [0.000, 0.000], 1.000 | 0.000 [0.000, 0.000], 1.000 |
| Long vs short document | Heuristic | 0.000 [0.000, 0.000], 1.000 | 0.000 [0.000, 0.000], 1.000 |

Both models reduced candidate adoption in the same direction when the warrant was
weakened. Phi-4's magnitude was 0.375 larger for each warrant contrast and both Phi
contrasts survived Holm correction; neither Qwen contrast did. Twelve contrasts were
exactly equal across models at zero. Exact observed zero is not an equivalence result:
no V1 equivalence margin is frozen, there are only 16 independent families, and the
binary baseline candidate-adoption rate was 1.0.

## Secondary dissociations

- Qwen3-14B lowered mean confidence from 0.8 to 0.2 in the low-reliability cell while
  categorical adoption remained 1.0. Phi-4 kept both confidence and adoption at 0.8
  and 1.0. Thus reliability influenced a verbal confidence endpoint in Qwen but not
  categorical choice, and did not visibly influence either endpoint in Phi.
- In the false-identity cell, claimed-verification rate fell from 1.0 to 0 for Qwen
  and to 0.25 for Phi, while adoption remained 1.0 for both. Identity information
  changed assurance language without changing answer use.
- In the related-only warrant cell, candidate adoption was 0.5 for Qwen and 0.125 for
  Phi; abstention was 0.125 and 0.375 respectively. In the contradiction cell,
  adoption was 0.5 and 0.125 while neither model abstained.
- Accuracy near 0.5 is a property of this balanced fictional-corpus protocol under
  strong candidate following. It is not a general model-quality benchmark.

## What the experiment supports

1. **Verbalized verification is not completed verification in this setting.** The
   trace-language mismatch is large and replicated across two independently developed
   model families.
2. **The models are not globally evidence-insensitive.** Both responded in the
   normatively expected direction to direct-support versus weaker/contradictory
   evidence warrant, with model heterogeneity in magnitude.
3. **Categorical adoption was not provenance-grounded across the other tested
   normative variables.** Reliability, identity authenticity, attribution
   authenticity, and source independence produced zero adoption effect.
4. **Proxy dominance is not supported by these runs.** Authority style, popularity,
   familiarity, precision, user endorsement, position, length, and dependent-copy
   count also produced zero adoption effect. The result is closer to broad categorical
   saturation plus warrant sensitivity than to a simple authority-heuristic story.
5. **Assurance language and causal answer use dissociate.** Identity changed whether
   models said they had verified a source without changing categorical adoption.

## What the experiment does not establish

- It does not show whether either model can verify sources when tools are available;
  that requires the registered interactive trace track.
- It does not establish general SDI or general PGSD failure across models, tasks,
  domains, natural documents, or real sources.
- It does not establish causal faithfulness of free-text rationales.
- It does not identify consensus laundering on a more sensitive endpoint; both raw
  copy count and root independence were zero under a saturated binary endpoint.
- It does not test PAVG efficacy, MIRAGE robustness, paid/API models, or V1 hypotheses.
- It does not justify interpreting exact-zero effects as practical equivalence.

## Required next stages

1. Run the controlled interactive-verification track with identity, attribution,
   canonical-record, identifier, evidence-span, and source-independence trace checks.
2. Add graded or probabilistic adoption endpoints and non-saturated families while
   retaining exact paired controls.
3. Run the PAVG baseline/defense comparison and keep defense failures.
4. Add at least one further independent target family and licensed real-source
   snapshots before external-validity claims.
5. Use these V0 results only to set V1 power assumptions, endpoints, equivalence
   margins, and failure policies; freeze V1 before inspecting confirmatory outcomes.

## Artifact policy

Raw evals and generated observation/effect tables remain in ignored, content-addressed
run/analysis directories on the workstation and compute node. Git tracks the frozen
plans, preflight evidence, sanitized run acceptances, published analyses, comparison,
this report, and exact hashes. No raw transcript is silently discarded or replaced.
