"""Content-addressed contracts for offline model snapshots."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from provtrust.execution.atomic_io import sha256_file

SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
IGNORED_MODEL_DIRECTORIES = frozenset({"._____temp", ".cache", ".git"})
IGNORED_MODEL_FILES = frozenset({".msc", ".mv"})


def _safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError(f"model asset path must be normalized and relative: {value!r}")
    return path


class ModelAssetFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1)
    bytes: int = Field(ge=0)
    sha256: str

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        _safe_relative_path(value)
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("sha256 must contain 64 lowercase hexadecimal characters")
        return value


def root_digest(files: tuple[ModelAssetFile, ...]) -> str:
    """Hash a canonical inventory without depending on a deployment path."""

    digest = hashlib.sha256()
    for record in sorted(files, key=lambda value: value.path):
        digest.update(record.path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record.bytes).encode("ascii"))
        digest.update(b"\0")
        digest.update(record.sha256.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


class ModelAssetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    model_id: str = Field(min_length=1)
    source_platform: str = Field(min_length=1)
    source_repository: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    upstream_huggingface_revision: str | None = None
    license: str = Field(min_length=1)
    captured_at: datetime
    root_name: str = Field(min_length=1)
    file_count: int = Field(gt=0)
    total_bytes: int = Field(gt=0)
    files: tuple[ModelAssetFile, ...]
    root_sha256: str

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware")
        return value

    @field_validator("root_name")
    @classmethod
    def validate_root_name(cls, value: str) -> str:
        if value in {".", ".."} or "/" in value or "\\" in value:
            raise ValueError("root_name must be a single directory name")
        return value

    @field_validator("root_sha256")
    @classmethod
    def validate_root_sha256(cls, value: str) -> str:
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("root_sha256 must contain 64 lowercase hexadecimal characters")
        return value

    @model_validator(mode="after")
    def validate_inventory(self) -> ModelAssetManifest:
        paths = tuple(record.path for record in self.files)
        if len(paths) != len(set(paths)):
            raise ValueError("model asset paths must be unique")
        if tuple(sorted(paths)) != paths:
            raise ValueError("model asset files must be sorted by path")
        if self.file_count != len(self.files):
            raise ValueError("file_count does not match the model asset inventory")
        if self.total_bytes != sum(record.bytes for record in self.files):
            raise ValueError("total_bytes does not match the model asset inventory")
        if self.root_sha256 != root_digest(self.files):
            raise ValueError("root_sha256 does not match the model asset inventory")
        return self


def discover_model_files(root: Path) -> tuple[Path, ...]:
    """Return the exact portable snapshot payload, excluding hub-local caches."""

    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"model root is not a directory: {root}")
    files: list[Path] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in IGNORED_MODEL_DIRECTORIES for part in relative.parts):
            continue
        if relative.as_posix() in IGNORED_MODEL_FILES:
            continue
        if path.is_symlink():
            raise ValueError(f"model snapshot contains a symlink: {relative.as_posix()}")
        if path.is_file():
            files.append(path)
    return tuple(sorted(files, key=lambda value: value.relative_to(root).as_posix()))


def build_model_asset_manifest(
    root: Path,
    *,
    model_id: str,
    source_platform: str,
    source_repository: str,
    source_revision: str,
    upstream_huggingface_revision: str | None,
    license_name: str,
    captured_at: datetime,
) -> ModelAssetManifest:
    root = root.resolve()
    records = tuple(
        ModelAssetFile(
            path=path.relative_to(root).as_posix(),
            bytes=path.stat().st_size,
            sha256=sha256_file(path),
        )
        for path in discover_model_files(root)
    )
    if not records:
        raise ValueError("model snapshot contains no portable files")
    return ModelAssetManifest(
        model_id=model_id,
        source_platform=source_platform,
        source_repository=source_repository,
        source_revision=source_revision,
        upstream_huggingface_revision=upstream_huggingface_revision,
        license=license_name,
        captured_at=captured_at,
        root_name=root.name,
        file_count=len(records),
        total_bytes=sum(record.bytes for record in records),
        files=records,
        root_sha256=root_digest(records),
    )


def verify_model_asset_manifest(root: Path, manifest: ModelAssetManifest) -> tuple[str, ...]:
    """Detect missing, modified, unexpected, and non-portable snapshot files."""

    root = root.resolve()
    failures: list[str] = []
    try:
        observed_files = discover_model_files(root)
    except ValueError as error:
        return (str(error),)
    observed = {path.relative_to(root).as_posix(): path for path in observed_files}
    expected = {record.path: record for record in manifest.files}
    for relative in sorted(expected.keys() - observed.keys()):
        failures.append(f"missing:{relative}")
    for relative in sorted(observed.keys() - expected.keys()):
        failures.append(f"unexpected:{relative}")
    for relative in sorted(expected.keys() & observed.keys()):
        record = expected[relative]
        path = observed[relative]
        if path.stat().st_size != record.bytes:
            failures.append(f"size_mismatch:{relative}")
        elif sha256_file(path) != record.sha256:
            failures.append(f"hash_mismatch:{relative}")
    return tuple(failures)
