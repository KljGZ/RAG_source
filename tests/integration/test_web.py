from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from provtrust.web import create_app, ensure_loopback_bind


def test_web_environment_is_noindex_and_healthy() -> None:
    application = create_app(
        index_path=Path("web_env/search_index/documents.jsonl"),
        snapshot_root=Path("web_env/source_snapshots"),
        template_root=Path("web_env/sites"),
    )
    client = TestClient(application)
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.headers["x-robots-tag"].startswith("noindex")
    page = client.get("/source/fixture-001")
    assert page.status_code == 200
    assert "harmless deployment fixture" in page.text
    robots = client.get("/robots.txt")
    assert "Disallow: /" in robots.text


def test_public_bind_is_rejected() -> None:
    with pytest.raises(ValueError, match="loopback"):
        ensure_loopback_bind("0.0.0.0")
