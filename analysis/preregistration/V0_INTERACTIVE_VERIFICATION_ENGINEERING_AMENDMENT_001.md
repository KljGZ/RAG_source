# V0 interactive-verification engineering amendment 001

## Reason and timing

This amendment is frozen after the first `tools_unprompted` compatibility preflight
failed and before any replacement tool-enabled preflight is generated. It is an
engineering correction under the failure policy in
`V0_INTERACTIVE_VERIFICATION.md`; it does not alter a scientific hypothesis or use a
behavioral outcome as an activation criterion.

The retained failed run is:

- plan SHA-256: `0489543f315bf25ed3c5350578afe6687b0a8b07f5bb01708cbe1087bea4212e`;
- raw log SHA-256: `906eeba52e6670b389ca7647a7b1ffa0e83c243a0a7ee4e29a6b5b7834e824d2`;
- failed validation artifact SHA-256:
  `b2c3d71b0945c8e3b52feddaa858a9391e0b38f202d901e95797ef32ebad39c2`;
- model turns: 140 across 10 samples; parseable posterior outputs: 0/10.

Raw trace inspection establishes the mechanism: Qwen3 emitted the required final
answer JSON, but Inspect AI 0.3.261 routed `Qwen/Qwen3-14B` through its generic Hugging
Face parser. That parser interpreted fenced JSON as an unknown tool call, returned an
empty assistant completion, and repeated the same parse-error loop until the message
limit. This is an interface failure, not evidence that the model did or did not verify
sources.

## Authorized correction

The replacement protocol may only register the unchanged model identifier
`Qwen/Qwen3-14B` with Inspect's `Qwen3-Instruct` model-family metadata before the
first tool-enabled generation. The registration must:

1. change parser routing only, never the model identifier, weights, tokenizer,
   decoding parameters, prompt, dataset, tools, scorer, sample order, or seed;
2. be implemented in a separately hashed project file;
3. be validated without loading a model or GPU against both final-answer JSON and a
   real tagged `<tool_call>` payload;
4. pin and verify the exact Inspect AI runtime version used by the parser; and
5. abort task construction if the model-family registration is not observable.

The model-free acceptance must also reproduce the original generic-parser failure
mechanism, so the correction remains tied to the observed defect rather than being an
unmotivated post-outcome change.

## Replacement and comparability policy

The original raw log and failed artifact remain immutable. New plans use input
contract version 5, a new model-registration version, new plan names, new output
directories, and a new committed Git revision. All three ten-row policy preflights
(`no_tools`, `tools_unprompted`, and `tools_prompted`) are rerun under that one
revision before any 160-row policy plan is activated. The no-tools rerun is required
for same-revision comparability even though the adapter cannot affect a no-tools
generation.

Preflight gates remain limited to execution integrity. Tool triggering, strict
completion, correctness, confidence, abstention, and false assurance remain
descriptive observations and may not determine activation. No V1, PAVG, gated-policy,
API-model, or real-world-source run is authorized by this amendment.
