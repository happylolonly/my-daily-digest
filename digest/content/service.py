from __future__ import annotations

import logging
import os
from datetime import datetime
from enum import Enum

from digest.config import DA_NANG_TZ
from digest.content.fetchers import (
    fetch_all,
    fetch_crypto_prices_usd,
    fetch_forex_vnd_per_usd,
    fetch_news_last_24h,
    fetch_weather,
)
from digest.content.llm import (
    generate_news_summary_html,
    generate_report_html_with_gemini,
)
from digest.content.report import (
    build_news_html,
    build_plain_text_report_html,
    build_rates_html,
    build_weather_html,
    format_motivation_html,
)


class DigestSection(str, Enum):
    FULL = "full"
    WEATHER = "weather"
    RATES = "rates"
    NEWS = "news"


def _report_date() -> str:
    return datetime.now(DA_NANG_TZ).strftime("%Y-%m-%d")


def _gemini_enabled(use_gemini: bool) -> bool:
    return use_gemini and bool(os.environ.get("GEMINI_API_KEY", "").strip())


def _resolve_news_text(
    raw_news: str | None,
    report_date: str,
    *,
    use_gemini: bool,
) -> tuple[str | None, bool]:
    """Return news body text and whether it is preformatted Gemini HTML."""
    if not raw_news:
        return None, False

    if _gemini_enabled(use_gemini):
        summary = generate_news_summary_html(raw_news, report_date)
        if summary:
            return summary, True
        logging.warning(
            "News Gemini summary failed for %s, using raw RSS fallback",
            report_date,
        )

    return raw_news, False


def build_digest_html(section: DigestSection, *, use_gemini: bool = False) -> str:
    report_date = _report_date()

    if section == DigestSection.FULL:
        data = fetch_all()
        news_text, news_preformatted = _resolve_news_text(
            data.news,
            report_date,
            use_gemini=use_gemini,
        )
        plain_fallback = build_plain_text_report_html(
            report_date=report_date,
            weather_text=data.weather,
            prices_text=data.prices,
            forex_text=data.forex,
            news_text=news_text,
        )
        if _gemini_enabled(use_gemini):
            final_html = generate_report_html_with_gemini(
                report_date=report_date,
                weather_text=data.weather,
                prices_text=data.prices,
                forex_text=data.forex,
                news_text=news_text,
                news_preformatted=news_preformatted,
            )
            if final_html:
                return final_html + format_motivation_html()
            logging.warning(
                "Using plain-text report fallback for %s (Gemini unavailable)",
                report_date,
            )
        elif use_gemini:
            logging.warning(
                "Using plain-text report fallback for %s (GEMINI_API_KEY not set)",
                report_date,
            )
        return plain_fallback

    if section == DigestSection.WEATHER:
        return build_weather_html(report_date, fetch_weather())

    if section == DigestSection.RATES:
        return build_rates_html(
            report_date,
            fetch_crypto_prices_usd(),
            fetch_forex_vnd_per_usd(),
        )

    if section == DigestSection.NEWS:
        raw_news = fetch_news_last_24h()
        news_text, _ = _resolve_news_text(
            raw_news,
            report_date,
            use_gemini=use_gemini,
        )
        return build_news_html(report_date, news_text)

    raise ValueError(f"Unknown section: {section}")
