# Annotation guide

Annotate one atomic claim and one exact evidence span at a time.

1. Resolve the actual publisher separately from the displayed/attributed publisher.
2. Mark identity authenticity using canonical publisher evidence.
3. Mark attribution authenticity only if the canonical record actually asserts the
   claim in the relevant time scope.
4. Label warrant as direct support, partial support, related only, unsupported, or
   contradiction. Topic relevance alone is not support.
5. Record the upstream provenance root and any copied/derived/paraphrased edge.
6. Preserve source and time uncertainty; use escalation rather than guessing.
7. Store character offsets, snapshot digest, annotator ID, timestamp, confidence, and
   adjudication state.

Annotators do not infer trustworthiness from fluent style, precise numbers, a logo,
or a claimed identifier. At least two independent labels and adjudication are used
for the confirmatory human subset. Report raw agreement, Cohen's kappa, MCC/F1 where
applicable, prevalence, and confusion matrices.
