# Frozen model configurations

Each run config records provider, exact model identifier/revision, observation date,
role, temperature, token limit, and system-prompt hash. Target and primary judge may
not resolve to the same model. API keys are environment variables and never appear
here.

No model configuration is activated until the resource/API allocation decision.

`qwen3-14b-v0.yaml` is the publication-safe registration for the first V0
compatibility target. Its weight inventory is content-addressed under `assets/`.
Copy `qwen3-14b.model-args.example.yaml` to `qwen3-14b.local.yaml` on each executor;
the ignored local file contains only the machine-specific offline model path. It
must keep `local_files_only: true`, `trust_remote_code: false`, and
`enable_thinking: false` for this registered pilot.

`qwen3-14b-static-v0.yaml` reuses the same verified snapshot but independently
freezes deterministic decoding (`do_sample=false`, temperature zero) for the paired
static V0 run. Compatibility sampling and scientific deterministic decoding are not
silently conflated.

`phi-4-static-v0.yaml` is reserved for the matched-parameter, cross-family V0
replication target. It is activated only after the exact Microsoft Phi-4 snapshot,
offline structured-output smoke, and one-family deterministic preflight pass. The
machine-local runtime file is copied from `phi-4-static.model-args.example.yaml` and
keeps the same offline and no-remote-code constraints.
