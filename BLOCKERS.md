# Blockers and gated work

This file distinguishes an implementation dependency from a scientific decision.

## Resource-allocation gate

No GPU or paid-API experiment may start until the user allocates resources after
deployment acceptance. Installation and CPU-only deterministic tests are allowed.

To open the gate, the user must provide:

- one or more exact GPU indices and an allocation expiry/time window;
- at least 24 logical CPU cores, 128 GiB RAM, and 1 TiB writable storage for the
  minimum sequential V0 profile;
- confirmation of whether the first tranche is local-model-only or may use named
  API providers, plus a hard USD budget for every enabled provider;
- approval of the exact model revisions after the compatibility probe plan is reviewed.

## External artifacts

- Model weights and restricted datasets require a license/access check, a pinned
  revision, and a SHA-256 manifest before transfer to the mainland node.
- The base Playwright runtime smoke has passed; full BrowserGym/WebArena-style V2
  execution remains gated on an explicit scope, data/license audit, and resource plan.
  It is not a V0 blocker.
- Confirmatory V1 remains gated on a frozen `EXPERIMENT_PLAN.lock.yaml` produced
  before looking at V1 outcomes.
