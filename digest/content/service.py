from __future__ import annotations

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
from digest.content.llm import generate_report_html_with_gemini
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


def build_digest_html(section: DigestSection, *, use_gemini: bool = False) -> str:
    report_date = _report_date()

    if section == DigestSection.FULL:
        data = fetch_all()
        plain_fallback = build_plain_text_report_html(
            report_date=report_date,
            weather_text=data.weather,
            prices_text=data.prices,
            forex_text=data.forex,
            news_text=data.news,
        )
        if use_gemini and os.environ.get("GEMINI_API_KEY", "").strip():
            final_html = generate_report_html_with_gemini(
                report_date=report_date,
                weather_text=data.weather,
                prices_text=data.prices,
                forex_text=data.forex,
                news_text=data.news,
            )
            if final_html:
                return final_html + format_motivation_html()
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
        return build_news_html(report_date, fetch_news_last_24h())

    raise ValueError(f"Unknown section: {section}")
