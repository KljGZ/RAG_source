#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROVTRUST_PROJECT_ROOT:-/home/jkl/projects/RAG_source}"
CONDA_BIN="${PROVTRUST_CONDA_BIN:-/home/jkl/miniforge3/bin/conda}"
ENV_NAME="${PROVTRUST_ENV_NAME:-provtrust}"
LOCK_DIR="$PROJECT_ROOT/environments/locks"

mkdir -p "$LOCK_DIR"

"$CONDA_BIN" env export -n "$ENV_NAME" --no-builds \
  | sed '/^prefix:/d' \
  > "$LOCK_DIR/conda-linux-64.yml"

"$CONDA_BIN" list -n "$ENV_NAME" --explicit \
  > "$LOCK_DIR/conda-linux-64.explicit.txt"

awk '
  /^  - pip:/ { capture = 1; next }
  capture {
    sub(/^      - /, "")
    if ($0 != "provenance-trust-bench==0.0.1") print
  }
' "$LOCK_DIR/conda-linux-64.yml" \
  > "$LOCK_DIR/pip-linux-64.txt"
