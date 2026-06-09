from __future__ import annotations

import logging
import os

LANGFUSE_CLOUD_HOST = "https://cloud.langfuse.com"


def init_observability() -> None:
    """Configure Langfuse Cloud tracing. No-op when keys are absent."""
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()

    if not public_key or not secret_key:
        os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
        return

    os.environ.setdefault("LANGFUSE_BASE_URL", LANGFUSE_CLOUD_HOST)


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
