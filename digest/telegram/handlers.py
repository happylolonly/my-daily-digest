from __future__ import annotations

import asyncio
import logging
import os

from telegram import BotCommand, InlineKeyboardMarkup, Message, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from digest.content.telegram_html import html_to_plain_text
from digest.content.service import DigestSection, build_digest_delivery
from digest.observability import flush_observability
from digest.telegram.delivery import NEWS_CALLBACK_DATA, news_button_markup

HELP_TEXT = (
    "<b>Daily Digest Bot</b>\n\n"
    "Команды:\n"
    "/brief — дата, погода, курсы, мотивация + кнопка новостей\n"
    "/weather — погода в Da Nang\n"
    "/rates — курсы BTC, ETH и VND/USD\n"
    "/news — новости за 24 часа (3 сообщения по группам)\n"
    "/help — эта справка"
)

BOT_COMMANDS = [
    BotCommand("start", "Справка по командам"),
    BotCommand("help", "Справка по командам"),
    BotCommand("brief", "Бриф: погода, курсы, мотивация"),
    BotCommand("weather", "Погода в Da Nang"),
    BotCommand("rates", "Курсы BTC, ETH, VND/USD"),
    BotCommand("news", "Новости за 24ч"),
]

UNAUTHORIZED_TEXT = "Это личный бот. Доступ только у владельца."


def authorized_user_id() -> str:
    user_id = os.environ.get("TELEGRAM_USER_ID", "").strip()
    if user_id:
        return user_id
    return os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def is_authorized(update: Update) -> bool:
    user = update.effective_user
    if user is None:
        return False
    allowed = authorized_user_id()
    return bool(allowed) and str(user.id) == allowed


async def reply_unauthorized(update: Update) -> None:
    if update.message:
        await update.message.reply_text(UNAUTHORIZED_TEXT)


async def edit_html_message(
    message: Message,
    html_text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    try:
        await message.edit_text(
            html_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
        )
    except Exception:
        logging.exception(
            "Telegram edit failed with parse_mode=HTML, retrying as plain text"
        )
        await message.edit_text(
            html_to_plain_text(html_text),
            disable_web_page_preview=True,
            reply_markup=reply_markup,
        )


async def send_html_reply(message: Message, html_text: str) -> None:
    try:
        await message.reply_html(html_text, disable_web_page_preview=True)
    except Exception:
        logging.exception(
            "Telegram reply failed with parse_mode=HTML, retrying as plain text"
        )
        await message.reply_text(
            html_to_plain_text(html_text),
            disable_web_page_preview=True,
        )


async def _deliver_messages(status: Message, messages: list[str]) -> None:
    if not messages:
        await status.edit_text("Новости недоступны.")
        return

    await edit_html_message(status, messages[0])
    for html_text in messages[1:]:
        await send_html_reply(status, html_text)


async def deliver_section(
    status: Message,
    section: DigestSection,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    try:
        delivery = await asyncio.to_thread(build_digest_delivery, section)
        if section == DigestSection.NEWS:
            await _deliver_messages(status, delivery.messages)
            await asyncio.to_thread(flush_observability)
        elif not delivery.messages:
            await status.edit_text("Данные недоступны.")
        else:
            await edit_html_message(status, delivery.messages[0], reply_markup)
    except Exception:
        logging.exception("section %s failed", section.value)
        await status.edit_text("Ошибка при сборе данных.")


async def run_section(
    update: Update,
    section: DigestSection,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    if update.message is None:
        return

    if not is_authorized(update):
        await reply_unauthorized(update)
        return

    status = await update.message.reply_text("⏳ Собираю данные...")
    await deliver_section(status, section, reply_markup=reply_markup)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await reply_unauthorized(update)
        return
    if update.message:
        await update.message.reply_html(HELP_TEXT, disable_web_page_preview=True)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await run_section(update, DigestSection.BRIEF, reply_markup=news_button_markup())


async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await run_section(update, DigestSection.WEATHER)


async def cmd_rates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await run_section(update, DigestSection.RATES)


async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await run_section(update, DigestSection.NEWS)


async def on_get_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    if not is_authorized(update):
        await query.answer(UNAUTHORIZED_TEXT, show_alert=True)
        return

    await query.answer()
    if isinstance(query.message, Message):
        status = await query.message.reply_text("⏳ Собираю данные...")
    elif update.effective_chat is not None:
        status = await context.bot.send_message(
            update.effective_chat.id, "⏳ Собираю данные..."
        )
    else:
        return
    await deliver_section(status, DigestSection.NEWS)


async def on_unauthorized_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if is_authorized(update):
        return
    await reply_unauthorized(update)


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(BOT_COMMANDS)


def register_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("brief", cmd_brief))
    application.add_handler(CommandHandler("weather", cmd_weather))
    application.add_handler(CommandHandler("rates", cmd_rates))
    application.add_handler(CommandHandler("news", cmd_news))
    application.add_handler(
        CallbackQueryHandler(on_get_news, pattern=f"^{NEWS_CALLBACK_DATA}$")
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, on_unauthorized_message)
    )
