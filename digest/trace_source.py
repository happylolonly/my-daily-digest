from __future__ import annotations

import threading

_local = threading.local()


def trace_source() -> str:
    return getattr(_local, "name", "bot")


def set_trace_source(name: str) -> None:
    _local.name = name
