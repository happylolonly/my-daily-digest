from __future__ import annotations

import json
import logging

from google.generativeai import GenerativeModel
from google.generativeai import configure as genai_configure

from digest.report import ensure_html_safe


def build_gemini_prompt(
    report_date: str,
    weather_text: str | None,
    prices_text: str | None,
    forex_text: str | None,
    news_text: str | None,
) -> str:
    weather = weather_text or "данные недоступны"
    prices = prices_text or "данные недоступны"
    forex = forex_text or "данные недоступны"
    news = news_text or "данные недоступны"

    payload = {
        "date": report_date,
        "weather": weather,
        "prices": prices,
        "forex_vnd_per_usd": forex,
        "news_last_24h_raw": news,
    }

    return (
        "Ты — редактор утреннего Telegram-дайджеста. "
        "Используй предоставленные сырые данные и сделай красивый, краткий репорт на русском языке.\n\n"
        "Требования к формату (обязательно):\n"
        "1) Верни ТОЛЬКО Telegram HTML (parse_mode=HTML). Без markdown и без кода в блоках.\n"
        "2) Используй только теги <b> и <i> для выделений.\n"
        "3) Секции: дата, Погода (Da Nang), Курсы (BTC/ETH и VND/USD), Новости.\n"
        "4) Если данных нет — напиши 'данные недоступны' в соответствующем месте.\n\n"
        "Сырые данные (JSON):\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )


def generate_report_html_with_gemini(
    gemini_api_key: str,
    gemini_model: str,
    report_date: str,
    weather_text: str | None,
    prices_text: str | None,
    forex_text: str | None,
    news_text: str | None,
) -> str | None:
    try:
        genai_configure(api_key=gemini_api_key)
        model = GenerativeModel(gemini_model)
        prompt = build_gemini_prompt(
            report_date=report_date,
            weather_text=weather_text,
            prices_text=prices_text,
            forex_text=forex_text,
            news_text=news_text,
        )

        resp = model.generate_content(prompt)
        raw_text = getattr(resp, "text", None) or str(resp)
        return ensure_html_safe(str(raw_text).strip())
    except Exception:
        logging.exception("Gemini generation failed")
        return None
