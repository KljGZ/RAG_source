from __future__ import annotations

from scripts.export_environment_manifest import portable_conda_url


def test_local_conda_url_is_normalized() -> None:
    record = {
        "channel": "<unknown>",
        "url": "file:///offline/r-base.conda",
        "subdir": "linux-64",
        "fn": "r-base-4.5.3-build.conda",
    }
    assert portable_conda_url(record) == (
        "https://conda.anaconda.org/conda-forge/linux-64/r-base-4.5.3-build.conda"
    )


def test_existing_remote_url_is_preserved() -> None:
    record = {
        "channel": "custom",
        "url": "https://packages.example.test/linux-64/pkg.conda",
        "subdir": "linux-64",
        "fn": "pkg.conda",
    }
    assert portable_conda_url(record) == record["url"]
