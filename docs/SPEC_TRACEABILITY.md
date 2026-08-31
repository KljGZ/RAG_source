# Specification traceability

This is the implementation contract derived from the theoretical and deployment
specifications. “Verified” means that code, a deterministic test/configuration, and
deployment evidence exist. It never means that an empirical hypothesis has already
been supported.

| Requirement | Implementation | Deployment evidence | Implementation state | Empirical state |
|---|---|---|---|---|
| PGSD/SDI constructs and non-equivalences | `docs/THEORY.md`, `SCIENTIFIC_REGISTER.yaml` | repository audit | verified | untested |
| Six normative variables vs. heuristic cues | Trial schema, explicit intervention vector, fractional builder | schema snapshots; property test | verified | untested |
| Eight normative axioms | deterministic scorers and PAVG constraints | defense/scorer unit tests | verified | untested |
| Claim/source/evidence/provenance/trial/run/tool schemas | `src/provtrust/schemas` | `benchmark/schemas/MANIFEST.json` | verified | not applicable |
| Group-safe split and leakage prevention | connected-component splitter/validator | leakage tests | verified | no final dataset |
| Track A: Learn2Discern replication | adapter, two-stage solver, numeric update scorer | build/parser tests | verified | upstream data/model runs pending |
| Track B: static causal decomposition | 16-cell deterministic fractional design and paired task | fractional-design and all-track build tests | verified | gold V0 families pending |
| Track C: authenticity and warrant | interventions, tasks, gaps/monotonicity scorers | counterfactual/scorer tests | verified | untested |
| Track D: independence/consensus laundering | provenance graphs, idempotent aggregation, task/scorers | root and non-amplification tests | verified | untested |
| Track E: interactive verification | controlled tools, prior/posterior solver, trace diagnostics | loopback service and browser smoke | verified | model runs pending |
| Track F: rationale causal faithfulness | declared-factor output plus counterfactual consistency scorer | scorer test | verified | model runs pending |
| Track G: PAVG defense | risk gate, attribution/warrant/root aggregation, abstention, tool protocol | defense tests and task build | verified | baseline comparison pending |
| MIRAGE isolated stress adapter | safety-gated manifest reader and task | harmless safety manifest build test | verified | upstream/license/resource gated |
| Real and synthetic dual tracks | content-addressed real-source manifests and synthetic builder | snapshot/hash tests | partial: machinery verified | licensed real corpus and annotations pending |
| Inspect AI orchestration | registered tasks, paired solver, structured scorer | every track builds; one frozen one-item/two-call Qwen3-14B eval passed | verified | deployment fixture only; scientific runs pending |
| R/Python confirmatory analysis | GLMM, contrasts, equivalence, bootstrap/randomization/power | `STATISTICS_RECOVERY.remote.json` | verified | V1 not frozen |
| Atomic output, retries, costs, sharding | execution package and SQLite state machines | crash/state/budget tests | verified | no production run |
| Resource authorization and isolation | reviewed allocation, physical-to-logical GPU mask, frozen-input CLI gate | allocation/input-tamper tests and CUDA probe | verified | GPU 2 allocated; compatibility passed |
| Controlled private webpages/search | loopback FastAPI services | `BROWSER_SMOKE.remote.json` | deployed | only harmless fixture loaded |
| Hourly process supervision | PID identity, allowlist, restart rate, lock/disk checks | active hourly heartbeat plus healthy manual acceptance run | deployed | service-only guardrail; run-specific GPU monitor deferred until a long run starts |
| Reproducibility, ethics, threat model, cards | `docs/`, locks, prompt/dataset manifests | strict audit/tests | verified | publication artifacts pending |
| Stage-level Git history | `docs/VERSIONING.md` | logical commits on `codex/v0` | active | V0 scientific checkpoint/tag deferred until datasets and the exploratory matrix finish |

## Scientific boundary

The benchmark tests whether observable behavior is causally controlled by verified
source properties and verification actions. It does not identify consciousness,
internal understanding, or a privileged hidden belief state.

## Safety boundary

Fabricated sources and poisoned documents remain on loopback-only services or in
offline snapshots. They are never published, indexed, injected into public corpora,
or tested against an unapproved third party.

## Honest remaining gates

The implementation is deployable, but full empirical completion cannot be generated
by infrastructure alone. It still requires licensed upstream data, human/deterministic
gold validation, additional target/judge model revisions, and any paid API budget.
The first target (Qwen3-14B) and physical GPU 2 are now frozen/allocated for a
compatibility pilot. Remaining inputs are represented as explicit gates rather than
placeholders silently treated as completed work.
