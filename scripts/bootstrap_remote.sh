#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROVTRUST_PROJECT_ROOT:-/home/jkl/projects/RAG_source}"
CONDA_BIN="${PROVTRUST_CONDA_BIN:-/home/jkl/miniforge3/bin/conda}"
ENV_NAME="${PROVTRUST_ENV_NAME:-provtrust}"
CONDA_CONFIG="${PROVTRUST_CONDARC:-$PROJECT_ROOT/configs/conda/mainland.yml}"
NETWORK_SHIM_DIR="$PROJECT_ROOT/scripts/network"

if [[ ! -x "$CONDA_BIN" ]]; then
  printf 'Conda executable not found: %s\n' "$CONDA_BIN" >&2
  exit 2
fi

if [[ ! -f "$CONDA_CONFIG" ]]; then
  printf 'Conda configuration not found: %s\n' "$CONDA_CONFIG" >&2
  exit 3
fi

export CONDARC="$CONDA_CONFIG"

if [[ "${PROVTRUST_FORCE_IPV4:-1}" == "1" ]]; then
  export PROVTRUST_FORCE_IPV4=1
  export PYTHONPATH="$NETWORK_SHIM_DIR${PYTHONPATH:+:$PYTHONPATH}"
fi

cd "$PROJECT_ROOT"

ENV_PREFIX="$($CONDA_BIN info --base)/envs/$ENV_NAME"

if "$CONDA_BIN" env list --json | grep -Fq "\"$ENV_PREFIX\""; then
  "$CONDA_BIN" env update --solver libmamba -n "$ENV_NAME" -f environment.yml
else
  "$CONDA_BIN" env create --solver libmamba -f environment.yml
fi

"$CONDA_BIN" run -n "$ENV_NAME" python -m pip install --no-build-isolation --no-deps -e .
"$CONDA_BIN" run -n "$ENV_NAME" python scripts/verify_environment.py
bash scripts/export_environment_locks.sh
