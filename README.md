# ProvenanceTrustBench

Research infrastructure for provenance-grounded source discernment (PGSD),
source discernment illusion (SDI), and provenance-aware verification.

The repository implements a versioned V0 framework for causal source interventions,
interactive provenance verification, PAVG defense, isolated MIRAGE stress adapters,
cluster-safe inference, and auditable execution. No benchmark result is claimed until
an experiment is run under an approved resource allocation.

The central distinction is:

```text
source sensitivity != source preference != source discernment != verification
```

See `docs/THEORY.md` for the formal variables, axioms, estimands, and limits, and
`docs/SPEC_TRACEABILITY.md` for the requirement-to-implementation matrix.
`docs/DEPLOYMENT_AUDIT.md` gives the complete theory-to-code-to-acceptance review.
`docs/V1_READINESS.md` separates integrity-accepted V0 observations from claims that
still require an outcome-blind confirmatory V1.
The outcome-blind second-model protocol is recorded in
`analysis/preregistration/V0_PHI4_REPLICATION.md` before any Phi-4 response is generated.

The current evidence release is documented in
`reports/V0_TO_CURRENT_COMPREHENSIVE_REPORT_ZH.md`. Its audit-safe, row-level tables,
data dictionary, raw-eval hash index, and checksums are under
`reports/data/v0_to_current/`. Full Track E execution is held until the missing-record
component amendment recorded in `BLOCKERS.md` is completed; no formal interactive
outcome has been generated.

## Remote environment

The canonical compute environment is a Conda environment named `provtrust`
created from `environment.yml`:

```bash
bash scripts/bootstrap_remote.sh
conda run -n provtrust python scripts/verify_environment.py
```

Optional dependency layers are documented in `environments/README.md`.
The deployed host currently uses verified offline transfers and the exact locks under
`environments/locks/`; the generic bootstrap command is not a replacement for those locks.

Core deployment checks:

```bash
python -m pip install --no-deps -e .
make lint
make test
make audit
provtrust validate-dataset --dataset benchmark/synthetic/smoke.jsonl
provtrust run-plan --config configs/experiments/v0_static.yaml --dry-run
```

Actual model execution is deliberately resource-gated and requires an untracked,
user-approved allocation manifest. See `artifacts/system/RESOURCE_PLAN.md` for the
minimum and recommended profiles. Current status is recorded in `PROJECT_STATUS.md`.

## Repository map

- `src/provtrust/schemas`: strict source, claim, evidence, provenance, trial, run,
  and tool-trace contracts.
- `src/provtrust/interventions`: minimal counterfactual transformations.
- `src/provtrust/tasks` and `tools`: Inspect AI tracks and controlled tools.
- `src/provtrust/scorers` and `analysis`: primary metrics and cluster-aware inference.
- `src/provtrust/defense`: Provenance-Aware Verification Gate.
- `web_env`: loopback-only source/search environment.
- `cluster` and `src/provtrust/monitoring.py`: allowlisted process supervision.
- `third_party`: pinned commits and license decisions; no vendored upstream code.

## Safety

Spoofed sources, fabricated citations, and poisoning documents must remain in
an isolated local environment. They must never be published, indexed by public
search engines, or injected into third-party systems.

The controlled service refuses non-loopback binds. Monitoring verifies exact PID
identity and never manages unrelated server processes.
