from __future__ import annotations

import asyncio
import logging

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from digest.content.telegram_html import html_to_plain_text

NEWS_CALLBACK_DATA = "get_news"


def news_button_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📰 Получить новости", callback_data=NEWS_CALLBACK_DATA)]]
    )


async def _send_telegram_message_async(
    chat_id: str,
    bot_token: str,
    html_text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    bot = Bot(token=bot_token)
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=html_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=reply_markup,
        )
    except Exception:
        logging.exception(
            "Telegram send failed with parse_mode=HTML, retrying as plain text"
        )
        await bot.send_message(
            chat_id=chat_id,
            text=html_to_plain_text(html_text),
            disable_web_page_preview=True,
            reply_markup=reply_markup,
        )


def send_telegram_message(
    chat_id: str,
    bot_token: str,
    html_text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    asyncio.run(
        _send_telegram_message_async(chat_id, bot_token, html_text, reply_markup)
    )
