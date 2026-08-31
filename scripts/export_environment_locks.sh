#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROVTRUST_PROJECT_ROOT:-/home/jkl/projects/RAG_source}"
CONDA_BIN="${PROVTRUST_CONDA_BIN:-/home/jkl/miniforge3/bin/conda}"
ENV_NAME="${PROVTRUST_ENV_NAME:-provtrust}"
LOCK_DIR="$PROJECT_ROOT/environments/locks"
ENV_PREFIX="$($CONDA_BIN info --base)/envs/$ENV_NAME"

mkdir -p "$LOCK_DIR"

"$CONDA_BIN" env export -n "$ENV_NAME" --no-builds \
  | sed '/^prefix:/d' \
  > "$LOCK_DIR/conda-linux-64.yml"

"$CONDA_BIN" list -n "$ENV_NAME" --explicit \
  > "$LOCK_DIR/conda-linux-64.explicit.txt"

"$ENV_PREFIX/bin/python" "$PROJECT_ROOT/scripts/export_environment_manifest.py" \
  --prefix "$ENV_PREFIX" \
  --output "$LOCK_DIR/environment-linux-64.json" \
  --pip-lock "$LOCK_DIR/pip-linux-64.txt"

"$ENV_PREFIX/bin/Rscript" -e '
  output <- commandArgs(trailingOnly = TRUE)[1]
  packages <- as.data.frame(installed.packages()[, c("Package", "Version", "LibPath")])
  packages <- packages[order(packages$Package), ]
  write.table(packages, file = output, sep = "\t", row.names = FALSE, quote = FALSE)
' "$LOCK_DIR/r-linux-64.tsv"

(
  cd "$LOCK_DIR"
  sha256sum \
    conda-linux-64.yml \
    conda-linux-64.explicit.txt \
    environment-linux-64.json \
    pip-linux-64.txt \
    r-linux-64.tsv \
    > LOCKS.sha256
)
