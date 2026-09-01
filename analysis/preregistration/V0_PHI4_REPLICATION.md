# Phi-4 cross-family static V0 replication protocol

Status: **outcome-blind exploratory protocol; model responses not yet generated**

This protocol was written after publishing the Qwen3-14B V0 result and before any
Phi-4 compatibility, preflight, or benchmark response was generated. It prevents the
second target from being selected or analyzed according to whether it reproduces the
first target's effects. This is an exploratory cross-model replication, not V1.

## Target selection

The second target is Microsoft Phi-4, a dense 14.66-billion-parameter decoder model.
It was selected because it is close in parameter count to Qwen3-14B while belonging to
an independently developed model family. This reduces, but does not eliminate,
architecture, organization, and scale confounding. No smaller Phi model is substituted
after outcomes are observed.

The execution asset is the ModelScope mirror `LLM-Research/phi-4` resolved at commit
`d767c0535ebfc0c3d8f049e06f6739eb9e8a2847`. The six weight files must match the
published Microsoft Phi-4 weight hashes associated with Hugging Face revision
`2db69c1c3e91a05d2c64a3185acfbaf36f744e25`. The complete local snapshot, including
tokenizer and configuration files, receives a separate content-addressed manifest;
the mirror revision remains the authoritative identity for the complete execution
asset. A mirror label is not treated as proof of byte identity.

The model is loaded only from the verified local directory, with network access
disabled at model runtime and `trust_remote_code=false`. Physical GPU 2 is mapped to
logical `cuda:0`; no other GPU or unrelated process is modified.

## Invariant scientific inputs

The replication retains, without outcome-dependent changes:

- `benchmark/synthetic/v0-paired-v1.jsonl` and its frozen manifest;
- all 240 samples, 16 counterfactual families, and 15 cells per family;
- `prompts/frozen/answer-system-v0.txt`;
- prior-then-posterior paired prompting and the same structured-answer schema;
- seed 20260831, one epoch, sampling disabled, thinking disabled, one connection,
  one sample at a time, maximum 256 output tokens, and zero error retry;
- the same binary claim-adoption coding and the same fourteen registered contrasts;
- family-level 2,000-replicate bootstrap intervals, exact two-sided sign-flip tests,
  and Holm adjustment across all fourteen contrasts.

The cross-model comparison is descriptive and fixed before Phi-4 outcomes: it reports
each model's effect and interval, exact effect equality, nonzero direction agreement,
effect range, accuracy, abstention, false-verification assurance, and the number of
Holm-supported contrasts. It performs no population-level pooling over two models.

Model-specific chat formatting supplied by the frozen tokenizer is unavoidable and
is recorded as part of the model asset. The prompt semantics, evidence, and scoring
are not rewritten to improve Phi-4's apparent performance.

## Activation gates

No full run is authorized until all of the following pass:

1. the final snapshot inventory and all file hashes verify;
2. an offline direct-load smoke produces exactly parseable structured output;
3. the Git worktree and registered input hashes are clean and fixed;
4. a deterministic one-family, 15-sample preflight completes 30 model calls with no
   retry or sample error, exact cell mapping, valid answer types, and citations limited
   to supplied evidence identifiers;
5. the allocation still authorizes physical GPU 2 and at least 35 GiB of free device
   memory is available immediately before loading.

Compatibility sampling and the one-family preflight are engineering gates only.
Their responses are retained but cannot be cited as scientific effects.

## Retention and interpretation

The full result is retained if the frozen run passes integrity checks, including a
null result, an opposite-direction result, poor accuracy, unsupported assurances, or
model heterogeneity. A failed engineering gate is reported and repaired by a
versioned protocol amendment; benchmark outcomes are not inspected through an
unvalidated path.

The replication can show whether a pattern is observed in two matched-size open
model families under this synthetic static protocol. It cannot establish population-
level generality, verification ability, equivalence from exact-zero estimates, real-
source external validity, rationale faithfulness, PAVG efficacy, or MIRAGE robustness.
