"""Least-privilege policy shared by all verification tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field


class ToolPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    allowed_file_roots: tuple[Path, ...]
    allowed_hosts: frozenset[str] = frozenset({"127.0.0.1", "localhost", "::1"})
    allowed_schemes: frozenset[str] = frozenset({"http"})
    max_read_bytes: int = Field(default=1_000_000, gt=0)
    secret_argument_names: frozenset[str] = frozenset(
        {"api_key", "authorization", "cookie", "password", "token"}
    )

    def check_path(self, path: Path) -> Path:
        target = path.resolve()
        for root in self.allowed_file_roots:
            resolved_root = root.resolve()
            if target == resolved_root or resolved_root in target.parents:
                if target.stat().st_size > self.max_read_bytes:
                    raise PermissionError("tool read exceeds configured byte limit")
                return target
        raise PermissionError(f"path is outside controlled roots: {path}")

    def check_url(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in self.allowed_schemes:
            raise PermissionError("URL scheme is not allowed")
        if parsed.hostname not in self.allowed_hosts:
            raise PermissionError("tool network access is loopback-only")
        if parsed.username or parsed.password:
            raise PermissionError("credentials in URLs are prohibited")
        return url

    def redact_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return {
            key: "[REDACTED]" if key.casefold() in self.secret_argument_names else value
            for key, value in arguments.items()
        }
