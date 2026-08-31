# Reproducibility

Reproduction uses a tagged Git commit, explicit Conda and pip locks, content hashes,
frozen prompt manifest, dataset manifest, model registry, seeds, run manifest,
append-only attempts, checkpoint database, and cost ledger. Every artifact is tied to
a run ID; provider model changes create a new run rather than overwriting old data.

The mainland node defaults to offline Hugging Face operation. Externally acquired
files are downloaded on an accessible machine, license-checked, hashed, uploaded,
and verified before use. No run may silently fetch an unpinned model or dataset.

`make lint`, `make test`, `make audit`, and an Inspect no-network smoke task form the
deployment gate. Publication releases include `artifacts/publication/REPRODUCE.yaml`
with argument-vector commands, not shell strings.
