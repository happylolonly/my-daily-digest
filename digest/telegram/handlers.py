from __future__ import annotations

import asyncio
import logging
import os

from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from digest.content.report import html_to_plain_text
from digest.content.service import DigestSection, build_digest_html

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


async def edit_html_message(message, html_text: str) -> None:
    try:
        await message.edit_text(
            html_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception:
        logging.exception(
            "Telegram edit failed with parse_mode=HTML, retrying as plain text"
        )
        await message.edit_text(
            html_to_plain_text(html_text),
            disable_web_page_preview=True,
        )


async def run_section(
    update: Update,
    section: DigestSection,
    *,
    use_gemini: bool = False,
) -> None:
    if update.message is None:
        return

    if not is_authorized(update):
        await reply_unauthorized(update)
        return

    status = await update.message.reply_text("⏳ Собираю данные...")
    try:
        html = await asyncio.to_thread(
            build_digest_html, section, use_gemini=use_gemini
        )
        await edit_html_message(status, html)
    except Exception:
        logging.exception("command %s failed", section.value)
        await status.edit_text("Ошибка при сборе данных.")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await reply_unauthorized(update)
        return
    if update.message:
        await update.message.reply_html(HELP_TEXT, disable_web_page_preview=True)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    gemini_enabled = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    await run_section(update, DigestSection.FULL, use_gemini=gemini_enabled)


async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await run_section(update, DigestSection.WEATHER)


async def cmd_rates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await run_section(update, DigestSection.RATES)


async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await run_section(update, DigestSection.NEWS)


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
    application.add_handler(CommandHandler("digest", cmd_digest))
    application.add_handler(CommandHandler("weather", cmd_weather))
    application.add_handler(CommandHandler("rates", cmd_rates))
    application.add_handler(CommandHandler("news", cmd_news))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, on_unauthorized_message)
    )
