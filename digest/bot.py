from __future__ import annotations

import asyncio
import logging
import os

from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from digest.config import load_local_env, setup_logging
from digest.service import DigestSection, build_digest_html

HELP_TEXT = (
    "<b>Daily Digest Bot</b>\n\n"
    "Команды:\n"
    "/digest — полный утренний дайджест\n"
    "/weather — погода в Da Nang\n"
    "/rates — курсы BTC, ETH и VND/USD\n"
    "/news — новости за 24 часа\n"
    "/help — эта справка"
)

BOT_COMMANDS = [
    BotCommand("start", "Справка по командам"),
    BotCommand("help", "Справка по командам"),
    BotCommand("digest", "Полный дайджест"),
    BotCommand("weather", "Погода в Da Nang"),
    BotCommand("rates", "Курсы BTC, ETH, VND/USD"),
    BotCommand("news", "Новости за 24ч"),
]


def _authorized_chat_id() -> str:
    return os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def _is_authorized(update: Update) -> bool:
    chat = update.effective_chat
    if chat is None:
        return False
    allowed = _authorized_chat_id()
    return bool(allowed) and str(chat.id) == allowed


async def _edit_html_message(message, html_text: str) -> None:
    try:
        await message.edit_text(
            html_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception:
        logging.exception(
            "Telegram edit failed with parse_mode=HTML, retrying without it"
        )
        await message.edit_text(html_text, disable_web_page_preview=True)


async def _run_section(
    update: Update,
    section: DigestSection,
    *,
    use_gemini: bool = False,
) -> None:
    if update.message is None:
        return

    if not _is_authorized(update):
        await update.message.reply_text("Нет доступа.")
        return

    status = await update.message.reply_text("⏳ Собираю данные...")
    try:
        html = await asyncio.to_thread(
            build_digest_html, section, use_gemini=use_gemini
        )
        await _edit_html_message(status, html)
    except Exception:
        logging.exception("command %s failed", section.value)
        await status.edit_text("Ошибка при сборе данных.")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        if update.message:
            await update.message.reply_text("Нет доступа.")
        return
    if update.message:
        await update.message.reply_html(HELP_TEXT, disable_web_page_preview=True)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    gemini_enabled = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    await _run_section(update, DigestSection.FULL, use_gemini=gemini_enabled)


async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_section(update, DigestSection.WEATHER)


async def cmd_rates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_section(update, DigestSection.RATES)


async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_section(update, DigestSection.NEWS)


async def _post_init(application: Application) -> None:
    await application.bot.set_my_commands(BOT_COMMANDS)


def run_bot() -> None:
    setup_logging()
    load_local_env()

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = _authorized_chat_id()
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required.")

    application = (
        Application.builder()
        .token(token)
        .post_init(_post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("digest", cmd_digest))
    application.add_handler(CommandHandler("weather", cmd_weather))
    application.add_handler(CommandHandler("rates", cmd_rates))
    application.add_handler(CommandHandler("news", cmd_news))

    logging.info("Bot polling started (authorized chat_id=%s)", chat_id)
    application.run_polling(drop_pending_updates=True)
