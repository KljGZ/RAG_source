# Environment layers

`environment.yml` is the mandatory V0 environment. It contains experiment
orchestration, data handling, statistical Python packages, tests, and the local
web-service runtime.

Apply optional layers only when their track begins:

```bash
conda env update -n provtrust -f environments/browser.yml
conda env update -n provtrust -f environments/statistics.yml
```

GPU packages are deliberately not guessed in the bootstrap environment. The
server uses Blackwell GPUs, so the PyTorch/CUDA combination must pass a dedicated
compatibility probe before it is frozen. V0 API-model experiments do not require
PyTorch.

After each major stage, export the portable environment record, exact Linux
Conda URLs, and the Pip-only lock:

```bash
bash scripts/export_environment_locks.sh
```

The editable project package is intentionally omitted from the Pip lock because
the bootstrap installs it from the checked-out repository after dependencies.
