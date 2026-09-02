# V0 interactive-verification engineering amendment 002

## Triggering evidence

This amendment is frozen after the version-2 `tools_prompted` compatibility
preflight failed and before any replacement response is generated. The retained
evidence is:

- Git revision: `85acc033e8d3752af3cd8332c302eadc57f89655`;
- plan SHA-256: `796d33f2c5fc0d47dd0e561c0229ab7e13daa55ae45f78827c4866aeffa984ce`;
- raw log SHA-256: `9c9ea05738735760684e97affc383796760bfe25a7c049166120cec6e5b611f4`;
- failed validation artifact SHA-256:
  `9e994d94fcb27bfa2c8aa0a0bbb25192ba2de274110e1a7a053d68356da19bf4`.

The first adapter corrected the original false classification of final-answer JSON.
In the prompted preflight, 4/10 samples then produced parseable final answers and 10
real tool calls were recorded. The remaining 6/10 emitted a subsequent
`find_evidence` call as a fenced top-level `{"name": ..., "arguments": ...}` object
rather than an official `<tool_call>` envelope. Inspect's Qwen-Instruct branch
returned those envelopes as ordinary answer content. Thus 6/10 final records failed
the answer schema even though the intended tool name and arguments were recoverable
without semantic inference.

This is a second representation-level compatibility failure. The four behavioral
records that happened to parse are retained but are not used to tune a hypothesis,
threshold, tool, prompt, dataset, or outcome definition.

## Authorized hybrid normalization

A new project-scoped adapter may recognize both representations observed from the
unchanged Qwen3 snapshot:

1. one or more explicit `<tool_call>JSON</tool_call>` envelopes; and
2. raw or fenced JSON whose top-level object contains a non-empty `name` and an
   `arguments` field.

All other JSON, including the frozen final-answer schema, must be preserved exactly
as assistant content. The adapter may classify syntax only. It may not repair tool
names, infer missing arguments, change argument values, select tools, synthesize
results, continue a stopped trace, or repair a final answer. Malformed or invalid
tool arguments remain model-visible failures.

The patch must be restricted to the registered Qwen3 family and must delegate every
other model family to the unmodified upstream parser. Installation must fail closed
if another component has already replaced the upstream parser. Acceptance must be
model-free, reproduce the old final-JSON failure, cover tagged, fenced, and raw tool
envelopes, cover ordinary JSON containing the words “name” and “arguments,” and verify
the actually installed dispatch path under Inspect AI 0.3.261.

## Replacement, freezing, and interpretation

Version-3 replacement plans use a new adapter ID, model registration, code manifest,
plan name, output directory, and Git revision. All three ten-row policies are rerun
under that single revision. Runtime code for task construction, answer parsing,
trace scoring, tools, and the adapter is content-hashed before execution.

No behavioral value is an activation gate. The original two amendments, all passed
and failed logs, and all validation artifacts remain in the audit history. The scope
remains exploratory V0 on one open-weight snapshot in the fictional closed world;
V1, PAVG, gated-policy, API-model, and real-world-source claims remain unauthorized.
