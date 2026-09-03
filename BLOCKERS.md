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

## Track E scorer blocker discovered during public-data review — resolved

- The version-1 missing-page component could mark
  `presented_record_existence_checked=true` when no controlled search occurred. The
  issue is visible in both zero-tool-call preflights for the two
  `c5_missing_reference` rows. Overall preflight completion remains 0/10 for every
  policy, so no reported completion outcome changes.
- Amendment 003 and `trial_specific_interactive_v2` now require a successful,
  JSON-list-valued search explicitly naming the presented `document_id`. Nine
  model-free semantics gates passed. All three immutable logs passed 25 rescore gates;
  exactly their six C5 component values changed from true to false, while trigger,
  tool-call, and strict-completion counts remained invariant.
- Three input-contract-8 replacement plans, a 112-file runtime manifest, and the V5
  allowlisted controller are frozen. The scorer defect no longer blocks execution.
- The independent resource blocker remains: physical GPU 2 must provide at
  least 46,080 MiB free in two consecutive controller samples.
