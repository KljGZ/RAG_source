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
