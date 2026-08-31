# ProvenanceTrustBench

Research infrastructure for provenance-grounded source discernment (PGSD),
source discernment illusion (SDI), and provenance-aware verification.

The repository is currently in the infrastructure bootstrap stage. No benchmark
results are claimed yet.

## Remote environment

The canonical compute environment is a Conda environment named `provtrust`
created from `environment.yml`:

```bash
bash scripts/bootstrap_remote.sh
conda run -n provtrust python scripts/verify_environment.py
```

Optional dependency layers are documented in `environments/README.md`.

## Safety

Spoofed sources, fabricated citations, and poisoning documents must remain in
an isolated local environment. They must never be published, indexed by public
search engines, or injected into third-party systems.
