from __future__ import annotations

from datetime import datetime
from enum import Enum

from digest.config import DA_NANG_TZ
from digest.content.fetchers import (
    fetch_crypto_prices_usd,
    fetch_forex_vnd_per_usd,
    fetch_weather,
)
from digest.content.news import fetch_news_body
from digest.content.report import (
    build_full_digest_html,
    build_news_html,
    build_rates_html,
    build_weather_html,
)


class DigestSection(str, Enum):
    FULL = "full"
    WEATHER = "weather"
    RATES = "rates"
    NEWS = "news"


def _report_date() -> str:
    return datetime.now(DA_NANG_TZ).strftime("%Y-%m-%d")


def build_digest_html(section: DigestSection) -> str:
    report_date = _report_date()

    if section == DigestSection.FULL:
        return build_full_digest_html(
            report_date=report_date,
            weather_text=fetch_weather(),
            prices_text=fetch_crypto_prices_usd(),
            forex_text=fetch_forex_vnd_per_usd(),
            news_text=fetch_news_body(report_date),
        )

    if section == DigestSection.WEATHER:
        return build_weather_html(report_date, fetch_weather())

    if section == DigestSection.RATES:
        return build_rates_html(
            report_date,
            fetch_crypto_prices_usd(),
            fetch_forex_vnd_per_usd(),
        )

    if section == DigestSection.NEWS:
        return build_news_html(report_date, fetch_news_body(report_date))

    raise ValueError(f"Unknown section: {section}")
