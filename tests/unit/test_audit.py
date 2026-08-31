from __future__ import annotations

from pathlib import Path

from provtrust.audit import SECRET_PATTERN, audit_repository


def test_blank_env_template_is_not_a_secret() -> None:
    content = Path(".env.example").read_text(encoding="utf-8")
    assert SECRET_PATTERN.search(content) is None


def test_repository_audit_passes() -> None:
    assert audit_repository(Path(".")).passed
