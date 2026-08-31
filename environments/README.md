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

The matching `.requirements.txt` files are the canonical inputs for an offline
Linux wheelhouse. The YAML layers retain the same top-level pins for normal
online Conda workflows.

The GPU layer is pinned to the official PyTorch 2.12.1 CUDA 13.0 Linux wheel,
whose published support matrix includes Blackwell compute capability 12.0 through
PTX. Installation is allowed during deployment, but CUDA execution and the final
compatibility probe remain resource-gated so they cannot disturb another user's
GPU job. V0 API-model experiments do not require PyTorch.
The requirement file also pins every Linux CUDA runtime wheel declared by that
Torch build. NVIDIA publishes these across several equivalent manylinux tags;
the offline wheelhouse records the exact files and validates them on the target
host before installation.

BrowserGym is pinned to release 0.14.3 together with its declared
`playwright==1.44` and `lxml<6` constraints. Trafilatura is pinned to 2.0.0,
the newest selected release whose `lxml>=5.3` constraint overlaps that range.
These packages are installed from Linux Python wheels rather than Conda: the
Conda Playwright 1.44 build constrains Node and shared libraries in a way that
would downgrade the Arrow 25 ABI required by the formal R layer. The wheel
driver is self-contained and preserves the base Conda transaction.
Browser binaries are installed into the project cache and validated separately;
V0/V1 use the lighter loopback FastAPI environment even when the V2 browser
layer is available.
The Playwright-managed Chromium revision, canonical download URL, byte size,
and SHA-256 are fixed in `environments/browser-artifacts.tsv`. In an offline
deployment, serve the verified archive from target loopback and let Playwright's
own installer perform extraction and permission setup.

The Conda index does not publish `r-clubsandwich` for the locked Linux solve.
`clubSandwich` is therefore downloaded from the canonical CRAN source URL,
hash-locked in `environments/r-source.requirements.txt`, and installed with
`R CMD INSTALL` after the binary R layer. This packaging exception does not
change the registered model, contrasts, or uncertainty estimands.

When the compute node cannot reach package hosts, generate a Conda dry-run JSON
on the target platform, convert its `FETCH` records to
`url<TAB>sha256<TAB>size`, and use `scripts/offline/download_manifest.py` on an
internet-connected machine. Verify again on the target with
`scripts/offline/verify_manifest.py` before placing packages in Conda's cache.
For wheelhouses and other already downloaded artifacts, pair
`scripts/offline/build_local_manifest.py` with
`scripts/offline/verify_local_manifest.py`; this variant intentionally records
filenames rather than origins so the receiving host verifies the exact uploaded
payload.

After each major stage, export the portable environment record, exact Linux
Conda URLs, and the Pip-only lock:

```bash
bash scripts/export_environment_locks.sh
```

The editable project package is intentionally omitted from the Pip lock because
the bootstrap installs it from the checked-out repository after dependencies.
