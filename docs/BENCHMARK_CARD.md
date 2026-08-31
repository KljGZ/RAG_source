# Benchmark card

## Name and purpose

ProvenanceTrustBench evaluates Provenance-Grounded Source Discernment and Source
Discernment Illusion through matched causal interventions.

## Tracks

1. Learn2Discern replication: prior, attributed numeric claim, posterior.
2. Static factorial decomposition of normative and heuristic variables.
3. Identity/attribution authenticity and evidence warrant.
4. Source dependence, duplication, and consensus laundering.
5. Interactive verification with controlled search/snapshots/registries.
6. Declared-factor rationale faithfulness under counterfactual intervention.
7. PAVG defense versus no-verification and always-verify baselines.
8. Isolated MIRAGE retrieval-and-generation stress test.

## Unit and splits

The unit is a trial variant. `family_id`, `event_id`, and `root_claim_id` induce a
connected component; the whole component belongs to one split. Inference clusters by
`family_id`. Duplicate pages derived from one source remain one provenance root.

## Intended uses

Research evaluation, mechanism-oriented behavioral testing, safety auditing, and
defense comparison. Not intended for ranking publishers, making high-stakes decisions
without experts, or deploying synthetic misinformation.

## Known limits

Operational probabilities are outputs, not direct internal beliefs. Synthetic tracks
maximize identification but may reduce realism; real tracks increase external
validity but contain confounding. Source reliability is claim-, role-, domain-, and
time-conditioned. Tool availability is part of the evaluated system.
