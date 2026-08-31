# Environment layers

`environment.yml` is the mandatory V0 environment. It contains experiment
orchestration, data handling, statistical Python packages, tests, and the local
web-service runtime.

Apply optional layers only when their track begins:

```bash
conda env update -n provtrust -f environments/browser.yml
conda env update -n provtrust -f environments/statistics.yml
conda env update -n provtrust -f environments/evaluation.yml
python -m pip install -r environments/gpu.requirements.txt
```

The GPU layer is pinned to the official PyTorch 2.12.1 CUDA 13.0 Linux wheel,
whose published support matrix includes Blackwell compute capability 12.0 through
PTX. Installation is allowed during deployment, but CUDA execution and the final
compatibility probe remain resource-gated so they cannot disturb another user's
GPU job. V0 API-model experiments do not require PyTorch.

BrowserGym is pinned to release 0.14.3. Browser binaries are installed into the
project cache and validated separately; V0/V1 use the lighter loopback FastAPI
environment even when the V2 browser layer is available.

After each major stage, export the portable environment record, exact Linux
Conda URLs, and the Pip-only lock:

```bash
bash scripts/export_environment_locks.sh
```

The editable project package is intentionally omitted from the Pip lock because
the bootstrap installs it from the checked-out repository after dependencies.
