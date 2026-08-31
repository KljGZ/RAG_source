"""Portable normalization helpers for installed environment records."""

from __future__ import annotations

from typing import Any

CONDA_FORGE_BASE = "https://conda.anaconda.org/conda-forge"


def portable_conda_url(record: dict[str, Any]) -> str:
    """Replace machine-local offline URLs with their canonical channel URL."""
    url = str(record.get("url") or "")
    channel = str(record.get("channel") or "")
    filename = str(record.get("fn") or "")
    subdir = str(record.get("subdir") or "")
    conda_forge = channel == "conda-forge" or "/conda-forge/" in url
    if filename and subdir and (
        url.startswith("file:") or channel == "<unknown>" or not url or conda_forge
    ):
        return f"{CONDA_FORGE_BASE}/{subdir}/{filename}"
    return url
