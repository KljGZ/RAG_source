# Blockers and gated work

This file distinguishes an implementation dependency from a scientific decision.

## Resource-allocation gate

No GPU or paid-API experiment may start until the user allocates resources after
deployment acceptance. Installation and CPU-only deterministic tests are allowed.

## External artifacts

- Model weights and restricted datasets require a license/access check, a pinned
  revision, and a SHA-256 manifest before transfer to the mainland node.
- V2 BrowserGym execution remains gated on a successful browser-runtime smoke test.
- Confirmatory V1 remains gated on a frozen `EXPERIMENT_PLAN.lock.yaml` produced
  before looking at V1 outcomes.
