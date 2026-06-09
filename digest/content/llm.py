from __future__ import annotations

import json
import logging
import time

from google import genai
from google.genai import errors as genai_errors

from digest.content.telegram_html import ensure_html_safe

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_RETRY_ATTEMPTS = 3
GEMINI_RETRY_DELAY_S = 15


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
        "1) Верни ТОЛЬКО Telegram HTML (parse_mode=HTML). Без markdown и без ``` блоков.\n"
        "2) Разрешены только теги <b> и <a href=\"...\">. Не используй <i>, <u>, <br>.\n"
        "3) Между секциями — пустая строка. Пиши настоящие переносы строк в ответе, "
        "не текст «\\n» и не <br>.\n"
        "4) Секции строго в таком виде (с эмодзи и <b>):\n"
        "   <b>📅 ДД.ММ.ГГГГ</b>\n"
        "   <b>🌤 Погода — Da Nang</b>\n"
        "   <b>💰 Курсы</b>\n"
        "   <b>📰 Новости</b>\n"
        "5) Курсы: <b>BTC</b>: $…, <b>ETH</b>: $…, <b>VND/USD</b>: …\n"
        "6) Новости: подзаголовок темы — <b>ИИ:</b>, <b>Крипта:</b>, <b>Геополитика:</b>. "
        "Каждая статья — одна строка: номер + ссылка НА ЗАГОЛОВОК (URL из сырых данных):\n"
        "   1. <a href=\"https://example.com/article\">Краткий заголовок на русском</a>\n"
        "   Запрещено: «заголовок: TechCrunch» или ссылка только на название источника.\n"
        "7) Заголовки новостей переводи/сокращай на русский; URL бери только из JSON.\n"
        "8) Если данных нет — «данные недоступны» в нужной секции.\n"
        "9) Из каждой темы выбери 1–2 самые значимые статьи; обзоры и подкасты пропускай.\n\n"
        "Пример фрагмента (структура, не копируй текст):\n"
        "<b>📅 09.06.2026</b>\n"
        "\n"
        "<b>🌤 Погода — Da Nang</b>\n"
        "27–32°C, сейчас 31°C, облачно.\n"
        "\n"
        "<b>💰 Курсы</b>\n"
        "<b>BTC</b>: $63,000\n"
        "<b>ETH</b>: $1,700\n"
        "<b>VND/USD</b>: данные недоступны\n"
        "\n"
        "<b>📰 Новости</b>\n"
        "\n"
        "<b>ИИ:</b>\n"
        "1. <a href=\"https://…\">OpenAI подала заявку на IPO</a>\n"
        "\n"
        "Сырые данные (JSON):\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )


def _is_retryable_error(exc: Exception) -> bool:
    if isinstance(exc, genai_errors.ClientError) and exc.code == 429:
        return True
    return isinstance(exc, genai_errors.ServerError) and exc.code == 503


def generate_report_html_with_gemini(
    report_date: str,
    weather_text: str | None,
    prices_text: str | None,
    forex_text: str | None,
    news_text: str | None,
) -> str | None:
    """
    Uses google.genai.Client() which reads GEMINI_API_KEY (or GOOGLE_API_KEY) from env.
    Call only after load_local_env() / GitHub Actions env is set.
    """
    prompt = build_gemini_prompt(
        report_date=report_date,
        weather_text=weather_text,
        prices_text=prices_text,
        forex_text=forex_text,
        news_text=news_text,
    )

    try:
        client = genai.Client()

        for attempt in range(1, GEMINI_RETRY_ATTEMPTS + 1):
            try:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                )
                raw_text = (response.text or "").strip()
                if raw_text:
                    return ensure_html_safe(raw_text)
                logging.warning(
                    "Gemini model %s returned empty text (attempt %s/%s)",
                    GEMINI_MODEL,
                    attempt,
                    GEMINI_RETRY_ATTEMPTS,
                )
            except (genai_errors.ClientError, genai_errors.ServerError) as exc:
                if not _is_retryable_error(exc) or attempt >= GEMINI_RETRY_ATTEMPTS:
                    raise
                logging.warning(
                    "Gemini error %s, retry in %ss (%s/%s)",
                    exc.code,
                    GEMINI_RETRY_DELAY_S,
                    attempt,
                    GEMINI_RETRY_ATTEMPTS,
                )
                time.sleep(GEMINI_RETRY_DELAY_S)

        return None
    except Exception:
        logging.exception("Gemini generation failed (model=%s)", GEMINI_MODEL)
        return None
