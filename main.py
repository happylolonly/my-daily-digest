from __future__ import annotations

import os
from datetime import datetime

from digest.config import DA_NANG_TZ, load_local_env, setup_logging
from digest.fetchers import fetch_all
from digest.llm import generate_report_html_with_gemini
from digest.report import build_plain_text_report_html
from digest.telegram import send_telegram_message


def main() -> None:
    setup_logging()
    load_local_env()

    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not telegram_bot_token or not telegram_chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required.")

    gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()

    now = datetime.now(DA_NANG_TZ)
    report_date = now.strftime("%Y-%m-%d")

    data = fetch_all()

    plain_fallback = build_plain_text_report_html(
        report_date=report_date,
        weather_text=data.weather,
        prices_text=data.prices,
        forex_text=data.forex,
        news_text=data.news,
    )

    final_html = None
    if gemini_api_key:
        final_html = generate_report_html_with_gemini(
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
            report_date=report_date,
            weather_text=data.weather,
            prices_text=data.prices,
            forex_text=data.forex,
            news_text=data.news,
        )

    if not final_html:
        final_html = plain_fallback

    send_telegram_message(
        chat_id=telegram_chat_id,
        bot_token=telegram_bot_token,
        html_text=final_html,
    )


if __name__ == "__main__":
    main()
