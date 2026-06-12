from __future__ import annotations

import os

from digest.content.service import DigestSection, build_digest_delivery
from digest.observability import flush_observability
from digest.telegram.delivery import news_button_markup, send_telegram_message
from digest.trace_source import set_trace_source


def deliver_scheduled_digest(*, source: str = "local") -> None:
    """Build the brief and send it with a "get news" button to TELEGRAM_CHAT_ID
    (cron or local main.py). News is fetched only when the button is pressed."""
    set_trace_source(source)
    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not telegram_bot_token or not telegram_chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required.")

    delivery = build_digest_delivery(DigestSection.BRIEF)
    for html_text in delivery.messages:
        send_telegram_message(
            chat_id=telegram_chat_id,
            bot_token=telegram_bot_token,
            html_text=html_text,
            reply_markup=news_button_markup(),
        )
    flush_observability()
