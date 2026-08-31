"""Loopback-only controlled source and search service."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from provtrust.tools.controlled_search import ControlledSearchIndex

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def ensure_loopback_bind(host: str) -> None:
    if host not in LOOPBACK_HOSTS:
        raise ValueError("controlled experiment services must bind to loopback")


def create_app(*, index_path: Path, snapshot_root: Path, template_root: Path) -> FastAPI:
    index = ControlledSearchIndex.from_jsonl(index_path)
    documents = {document.document_id: document for document in index.documents}
    snapshot_root = snapshot_root.resolve()
    environment = Environment(
        loader=FileSystemLoader(template_root),
        autoescape=select_autoescape(("html", "xml")),
        enable_async=False,
    )
    template = environment.get_template("source.html")
    app = FastAPI(
        title="ProvenanceTrustBench controlled source service",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.middleware("http")
    async def isolation_headers(request: Request, call_next: object) -> Response:
        # `call_next` is supplied by Starlette; keeping the annotation generic avoids
        # binding project code to an internal protocol.
        response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/healthz")
    async def health() -> dict[str, str | int]:
        return {"status": "ok", "documents": len(documents)}

    @app.get("/robots.txt", response_class=PlainTextResponse)
    async def robots() -> str:
        return "User-agent: *\nDisallow: /\n"

    @app.get("/api/search")
    async def search(q: str = Query(min_length=1, max_length=500), limit: int = 5) -> JSONResponse:
        try:
            hits = index.search(q, limit=limit)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return JSONResponse([hit.model_dump(mode="json") for hit in hits])

    @app.get("/source/{document_id}", response_class=HTMLResponse)
    async def source(document_id: str) -> HTMLResponse:
        document = documents.get(document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="unknown controlled document")
        content_path = (snapshot_root / f"{document.snapshot_hash}.txt").resolve()
        if snapshot_root not in content_path.parents or not content_path.is_file():
            raise HTTPException(status_code=500, detail="snapshot unavailable")
        content = content_path.read_bytes()
        if hashlib.sha256(content).hexdigest() != document.snapshot_hash:
            raise HTTPException(status_code=500, detail="snapshot integrity failure")
        html = template.render(
            title=document.title,
            source_id=document.source_id,
            body=content.decode("utf-8"),
            document_id=document.document_id,
        )
        return HTMLResponse(html)

    @app.get("/manifest")
    async def manifest() -> JSONResponse:
        payload = {
            "schema_version": "1.0.0",
            "isolated": True,
            "public_indexing_disabled": True,
            "document_ids": sorted(documents),
            "index_sha256": hashlib.sha256(index_path.read_bytes()).hexdigest(),
        }
        return JSONResponse(payload)

    return app
