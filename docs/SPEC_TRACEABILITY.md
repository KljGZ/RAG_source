# Specification traceability

This matrix is the implementation contract derived from the theoretical and
deployment specifications. A row is complete only when code, tests, configuration,
and an auditable artifact all exist. “Implemented” never means that an empirical
claim has been established.

| Requirement | Implementation | Verification artifact | State |
|---|---|---|---|
| PGSD/SDI constructs and non-equivalences | `SCIENTIFIC_REGISTER.yaml` | schema audit | implemented |
| Six normative variables vs. heuristic cues | schemas and factorial builder | counterfactual tests | in progress |
| Eight normative axioms | scorers and PAVG constraints | axiom test report | in progress |
| Claim/source/evidence/provenance/trial/run/tool schemas | `src/provtrust/schemas` | JSON-schema snapshots | in progress |
| Group-safe split and leakage prevention | dataset split/validator | leakage audit | in progress |
| Track A: Learn2Discern replication | dataset adapter and task | dry-run manifest | in progress |
| Track B: static causal decomposition | interventions and task | paired-design audit | in progress |
| Track C: authenticity and warrant | task/scorers | monotonicity audit | in progress |
| Track D: independence/consensus laundering | provenance graph/task | root-count audit | in progress |
| Track E: interactive verification | controlled tools/web environment | trace-replay test | in progress |
| Track F: rationale causal faithfulness | rationale task/scorer | intervention agreement test | in progress |
| Track G: PAVG defense | defense pipeline | non-amplification tests | in progress |
| MIRAGE isolated stress adapter | manifest-only adapter | safety boundary test | in progress |
| Real and synthetic dual tracks | builders and snapshot manifests | provenance/hash audit | in progress |
| Inspect AI orchestration | task wrappers | no-network smoke evaluation | in progress |
| R/Python confirmatory analysis | scripts and locked estimands | synthetic recovery test | in progress |
| Atomic output, retries, costs, sharding | execution package | crash/restart tests | in progress |
| Controlled private webpages/search | loopback FastAPI services | header/isolation tests | in progress |
| Hourly process supervision | allowlisted monitor and heartbeat | monitor event log | in progress |
| Reproducibility, ethics, threat model, cards | `docs/` | documentation audit | in progress |
| Stage-level Git history | `docs/VERSIONING.md` | signed/annotated tags | active |

## Scientific boundary

The benchmark tests whether observable behavior is causally controlled by verified
source properties and verification actions. It does not claim to identify
consciousness, internal understanding, or a privileged hidden belief state.

## Safety boundary

Fabricated sources and poisoned documents remain on loopback-only services or in
offline snapshots. They are never published, indexed, injected into public corpora,
or tested against an unapproved third party.
