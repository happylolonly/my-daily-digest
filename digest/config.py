from __future__ import annotations

import logging
import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

HTTP_TIMEOUT_S = 10
DA_NANG_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

_MONTH_GENITIVE_RU: tuple[str, ...] = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def format_report_date_ru(value: str | datetime) -> str:
    """Display date for Telegram, e.g. 2026-06-10 -> 10 июня."""
    if isinstance(value, str):
        dt = datetime.strptime(value, "%Y-%m-%d")
    else:
        dt = value
    return f"{dt.day} {_MONTH_GENITIVE_RU[dt.month - 1]}"

_TELEGRAM_BOT_URL = re.compile(
    r"(https://api\.telegram\.org/bot)[^/\s\"']+",
    re.IGNORECASE,
)


class RedactSecretsFilter(logging.Filter):
    """Masks secrets in log output while keeping INFO level for the app."""

    def __init__(self, secrets: tuple[str, ...] = ()) -> None:
        super().__init__()
        self._secrets = tuple(s for s in secrets if len(s) >= 8)

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            try:
                message = record.msg % record.args
            except Exception:
                message = str(record.msg)
            record.msg = self._redact(message)
            record.args = None
        elif isinstance(record.msg, str):
            record.msg = self._redact(record.msg)
        return True

    def _redact(self, text: str) -> str:
        text = _TELEGRAM_BOT_URL.sub(r"\1***", text)
        for secret in sorted(self._secrets, key=len, reverse=True):
            text = text.replace(secret, "***")
        return text


def setup_logging() -> None:
    secrets = tuple(
        s
        for s in (
            os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(),
            os.environ.get("GEMINI_API_KEY", "").strip(),
            os.environ.get("OPENROUTER_API_KEY", "").strip(),
            os.environ.get("LANGFUSE_SECRET_KEY", "").strip(),
            os.environ.get("CRON_SECRET", "").strip(),
        )
        if s
    )
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )
    secret_filter = RedactSecretsFilter(secrets)
    for handler in logging.root.handlers:
        handler.addFilter(secret_filter)


def load_local_env() -> None:
    """Loads .env for local runs. Skipped in CI (GitHub Actions has no app .env)."""
    if os.environ.get("GITHUB_ACTIONS"):
        return
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:
        pass
