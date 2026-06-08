from __future__ import annotations

import logging
import os
from zoneinfo import ZoneInfo

HTTP_TIMEOUT_S = 10
DA_NANG_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def setup_logging() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(message)s",
    )


def load_local_env() -> None:
    """Loads .env only for local runs. In GitHub Actions we rely on Actions env/secrets."""
    if os.environ.get("GITHUB_ACTIONS"):
        return
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:
        pass
