from __future__ import annotations

import json
import logging
import os
import time

from google import genai
from google.genai import errors as genai_errors
from langfuse import get_client, observe, propagate_attributes

from digest.content.telegram_html import ensure_html_safe
from digest.observability import langfuse_enabled

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_RETRY_ATTEMPTS = 3
GEMINI_RETRY_DELAY_S = 15


def build_news_summary_prompt(report_date: str, raw_news_text: str) -> str:
    return (
        "Ты — редактор новостной ленты для личного Telegram-дайджеста на русском языке.\n"
        f"Дата: {report_date}. По заголовкам RSS за последние 24 часа выбери самое важное.\n\n"
        "Требования к формату (обязательно):\n"
        "1) Верни ТОЛЬКО тело секции новостей в Telegram HTML. "
        "Без заголовка «📰 Новости», без markdown и без ``` блоков.\n"
        "2) Разрешены только теги <b> и <a href=\"...\">. Не используй <i>, <u>, <br>.\n"
        "3) Темы строго в порядке: <b>ИИ:</b>, <b>Крипта:</b>, <b>Геополитика:</b>. "
        "Пропусти тему, если в сырых данных по ней ничего нет.\n"
        "4) Для каждой темы:\n"
        "   — 1–2 предложения: главное за сутки своими словами на русском\n"
        "   — пустая строка\n"
        "   — 1–2 ссылки из сырых данных: • <a href=\"URL\">краткий заголовок на русском</a>\n"
        "5) URL бери только из сырых данных; не выдумывай ссылки.\n"
        "6) Пропускай обзоры, подкасты, гайды и «how to».\n"
        "7) Между темами — пустая строка.\n\n"
        "Пример структуры (не копируй текст):\n"
        "<b>ИИ:</b>\n"
        "OpenAI и регуляторы ЕС договорились о новых правилах для моделей.\n"
        "\n"
        "• <a href=\"https://…\">ЕС ужесточает требования к ИИ</a>\n"
        "• <a href=\"https://…\">OpenAI открывает новый дата-центр</a>\n"
        "\n"
        "<b>Крипта:</b>\n"
        "…\n\n"
        "Сырые заголовки RSS:\n"
        f"{raw_news_text}"
    )


def build_gemini_prompt(
    report_date: str,
    weather_text: str | None,
    prices_text: str | None,
    forex_text: str | None,
    news_text: str | None,
    *,
    news_preformatted: bool = False,
) -> str:
    weather = weather_text or "данные недоступны"
    prices = prices_text or "данные недоступны"
    forex = forex_text or "данные недоступны"
    news = news_text or "данные недоступны"

    payload: dict[str, str] = {
        "date": report_date,
        "weather": weather,
        "prices": prices,
        "forex_vnd_per_usd": forex,
    }
    if news_preformatted:
        payload["news_section_html"] = news
    else:
        payload["news_last_24h_raw"] = news

    news_rules = (
        "6) Новости уже подготовлены на русском — вставь блок из news_section_html "
        "целиком и без изменений сразу под заголовком <b>📰 Новости</b>.\n"
        if news_preformatted
        else (
            "6) Новости: подзаголовок темы — <b>ИИ:</b>, <b>Крипта:</b>, <b>Геополитика:</b>. "
            "Каждая статья — одна строка: номер + ссылка НА ЗАГОЛОВОК (URL из сырых данных):\n"
            "   1. <a href=\"https://example.com/article\">Краткий заголовок на русском</a>\n"
            "   Запрещено: «заголовок: TechCrunch» или ссылка только на название источника.\n"
            "7) Заголовки новостей переводи/сокращай на русский; URL бери только из JSON.\n"
            "8) Из каждой темы выбери 1–2 самые значимые статьи; обзоры и подкасты пропускай.\n"
        )
    )
    unavailable_rule = (
        "7) Если данных нет — «данные недоступны» в нужной секции.\n"
        if news_preformatted
        else "9) Если данных нет — «данные недоступны» в нужной секции.\n"
    )

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
        f"{news_rules}"
        f"{unavailable_rule}"
        "\n"
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


def _trace_source() -> str:
    if os.environ.get("GITHUB_ACTIONS"):
        return "github-actions"
    return "bot"


@observe(name="digest-gemini", as_type="generation")
def _generate_gemini_content(prompt: str) -> str | None:
    get_client().update_current_generation(model=GEMINI_MODEL, input=prompt)

    client = genai.Client()

    for attempt in range(1, GEMINI_RETRY_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            raw_text = (response.text or "").strip()
            if raw_text:
                usage = response.usage_metadata
                if usage is not None:
                    get_client().update_current_generation(
                        output=raw_text,
                        usage_details={
                            "input": usage.prompt_token_count or 0,
                            "output": usage.candidates_token_count or 0,
                            "total": usage.total_token_count or 0,
                        },
                    )
                else:
                    get_client().update_current_generation(output=raw_text)
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


def _run_gemini_prompt(
    prompt: str,
    *,
    trace_name: str,
    report_date: str,
    tags: list[str],
) -> str | None:
    try:
        if langfuse_enabled():
            with propagate_attributes(
                trace_name=trace_name,
                metadata={
                    "source": _trace_source(),
                    "report_date": report_date,
                },
                tags=tags,
            ):
                return _generate_gemini_content(prompt)
        return _generate_gemini_content(prompt)
    except Exception:
        logging.exception("Gemini generation failed (model=%s)", GEMINI_MODEL)
        return None


def generate_news_summary_html(
    raw_news_text: str | None,
    report_date: str,
) -> str | None:
    """
    Summarize RSS headlines into Russian Telegram HTML (topic summary + links).
    Uses google.genai.Client() which reads GEMINI_API_KEY from env.
    """
    if not raw_news_text or not raw_news_text.strip():
        return None

    prompt = build_news_summary_prompt(report_date, raw_news_text)
    return _run_gemini_prompt(
        prompt,
        trace_name="news-summary",
        report_date=report_date,
        tags=["news-summary"],
    )


def generate_report_html_with_gemini(
    report_date: str,
    weather_text: str | None,
    prices_text: str | None,
    forex_text: str | None,
    news_text: str | None,
    *,
    news_preformatted: bool = False,
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
        news_preformatted=news_preformatted,
    )

    return _run_gemini_prompt(
        prompt,
        trace_name="daily-digest",
        report_date=report_date,
        tags=["daily-digest"],
    )
