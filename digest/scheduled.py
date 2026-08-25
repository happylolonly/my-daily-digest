from __future__ import annotations

import os

from digest.content.service import DigestSection, build_digest_delivery
from digest.observability import flush_observability
from digest.telegram.delivery import send_telegram_message
from digest.trace_source import set_trace_source


def scheduled_sections(*, include_news: bool = True) -> tuple[DigestSection, ...]:
    if include_news:
        return (DigestSection.BRIEF, DigestSection.NEWS)
    return (DigestSection.BRIEF,)


def deliver_scheduled_digest(*, source: str = "local", include_news: bool = True) -> None:
    """Send the brief, and news unless include_news is false (evening cron)."""
    set_trace_source(source)
    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not telegram_bot_token or not telegram_chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required.")

    for section in scheduled_sections(include_news=include_news):
        delivery = build_digest_delivery(section)
        for html_text in delivery.messages:
            send_telegram_message(
                chat_id=telegram_chat_id,
                bot_token=telegram_bot_token,
                html_text=html_text,
            )
    flush_observability()
