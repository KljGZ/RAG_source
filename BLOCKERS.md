# Blockers and gated work

This file distinguishes an implementation dependency from a scientific decision.

## First local-model resource gate — satisfied

The user assigned physical GPU index 2 for continuous use, allowed direct CPU use,
authorized project-selected storage, and requested an open-weight first tranche. The
frozen Qwen3-14B V0 static plan therefore has the following accepted allocation:

- physical GPU 2 only (mapped by the process to logical `cuda:0`), with at least
  35 GiB usable VRAM;
- 16 CPU cores, 64 GiB RAM, and 100 GiB writable run storage minimum;
- zero paid API budget and no external provider calls;
- frozen local model, dataset, prompt, activation evidence, and plan hashes.

The actual machine-local allocation reserves CPU 0–31, 192 GiB RAM, and 1,200 GiB
storage, exceeding the run minimum. Existing unrelated GPU processes are outside this
project's authority and must never be terminated or restarted.

Additional GPUs/models, paid APIs, a primary judge, or a broader empirical matrix
remain separately gated and are not implied by this first-tranche authorization.

## External artifacts

- Model weights and restricted datasets require a license/access check, a pinned
  revision, and a SHA-256 manifest before transfer to the mainland node.
- The base Playwright runtime smoke has passed; full BrowserGym/WebArena-style V2
  execution remains gated on an explicit scope, data/license audit, and resource plan.
  It is not a V0 blocker.
- Confirmatory V1 remains gated on a frozen `EXPERIMENT_PLAN.lock.yaml` produced
  before looking at V1 outcomes.
