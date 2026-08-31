"""Force AF_UNSPEC Python network lookups to IPv4 during remote bootstrap.

The target node has working IPv6 routes that stall under sustained HTTPS
downloads. Python imports ``sitecustomize`` automatically when this directory
is placed on ``PYTHONPATH``. The bootstrap script scopes the shim to its own
process tree, so no host-wide network configuration is changed.
"""

from __future__ import annotations

import os
import socket
from typing import Any

_original_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(
    host: str | bytes | None,
    port: str | int | None,
    family: int = 0,
    type: int = 0,
    proto: int = 0,
    flags: int = 0,
) -> list[tuple[Any, ...]]:
    if family == socket.AF_UNSPEC:
        family = socket.AF_INET
    return _original_getaddrinfo(host, port, family, type, proto, flags)


if os.environ.get("PROVTRUST_FORCE_IPV4", "1") == "1":
    socket.getaddrinfo = _ipv4_getaddrinfo
