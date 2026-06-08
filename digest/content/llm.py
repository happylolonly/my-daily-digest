from __future__ import annotations

import json
import logging
import time

from google import genai
from google.genai import errors as genai_errors

from digest.content.report import ensure_html_safe

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
        "2) Используй только теги <b>, <i> и <a href=\"...\"> для ссылок.\n"
        "3) Переносы строк — через \\n, не через <br>.\n"
        "4) Секции: дата, Погода (Da Nang), Курсы (BTC/ETH и VND/USD), Новости.\n"
        "5) Если данных нет — напиши 'данные недоступны' в соответствующем месте.\n\n"
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
