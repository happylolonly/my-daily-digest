from __future__ import annotations

import logging
import os

LANGFUSE_CLOUD_HOST = "https://cloud.langfuse.com"


def _strip_env(value: str) -> str:
    return value.strip().strip('"').strip("'")


def init_observability() -> None:
    """Configure Langfuse Cloud tracing. No-op when keys are absent."""
    public_key = _strip_env(os.environ.get("LANGFUSE_PUBLIC_KEY", ""))
    secret_key = _strip_env(os.environ.get("LANGFUSE_SECRET_KEY", ""))

    if not public_key or not secret_key:
        os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
        return

    base_url = _strip_env(os.environ.get("LANGFUSE_BASE_URL", "")) or LANGFUSE_CLOUD_HOST
    os.environ["LANGFUSE_BASE_URL"] = base_url


def langfuse_enabled() -> bool:
    return os.environ.get("LANGFUSE_TRACING_ENABLED", "true").lower() != "false"


def flush_observability() -> None:
    if not langfuse_enabled():
        return
    try:
        from langfuse import get_client

        get_client().flush()
    except Exception:
        logging.exception("Langfuse flush failed")
