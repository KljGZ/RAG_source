# Stage-level versioning

`main` contains completed, auditable stage checkpoints. Work between checkpoints
uses a stage branch and does not produce release tags.

Planned checkpoints:

| Stage | Branch | Annotated tag |
|---|---|---|
| Infrastructure bootstrap | `codex/bootstrap` | `bootstrap-v0.1.0` |
| V0 exploratory pilot | `codex/v0` | `v0.1.0` |
| Frozen V1 design and confirmatory run | `codex/v1` | `v1.0.0` |
| PAVG evaluation | `codex/pavg` | `pavg-v1.0.0` |
| MIRAGE stress test | `codex/mirage-stress` | `mirage-stress-v1.0.0` |

Each checkpoint must include code, configuration, dataset manifests, prompt
hashes, environment locks, tests, analysis scripts, and a stage report. Raw
model weights, webpage snapshots with redistribution restrictions, secrets, and
large run outputs are not committed; their manifests and hashes are committed.
