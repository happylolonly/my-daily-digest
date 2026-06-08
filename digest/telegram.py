from __future__ import annotations

import asyncio
import logging

from telegram import Bot


async def _send_telegram_message_async(
    chat_id: str, bot_token: str, html_text: str
) -> None:
    bot = Bot(token=bot_token)
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=html_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception:
        logging.exception(
            "Telegram send failed with parse_mode=HTML, retrying without it"
        )
        await bot.send_message(
            chat_id=chat_id,
            text=html_text,
            disable_web_page_preview=True,
        )


def send_telegram_message(chat_id: str, bot_token: str, html_text: str) -> None:
    asyncio.run(_send_telegram_message_async(chat_id, bot_token, html_text))
