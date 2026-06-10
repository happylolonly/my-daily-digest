from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from digest.config import DA_NANG_TZ
from digest.content.fetchers import (
    fetch_crypto_prices_usd,
    fetch_forex_vnd_per_usd,
    fetch_weather,
)
from digest.content.news import fetch_grouped_news
from digest.content.report import (
    build_brief_html,
    build_news_groups_html_list,
    build_rates_html,
    build_weather_html,
)


class DigestSection(str, Enum):
    FULL = "full"
    WEATHER = "weather"
    RATES = "rates"
    NEWS = "news"


@dataclass
class DigestDelivery:
    messages: list[str]


def _report_date() -> str:
    return datetime.now(DA_NANG_TZ).strftime("%Y-%m-%d")


def _fetch_brief_data(report_date: str) -> tuple[str | None, str | None, str | None]:
    with ThreadPoolExecutor(max_workers=3) as executor:
        weather_future = executor.submit(fetch_weather)
        prices_future = executor.submit(fetch_crypto_prices_usd)
        forex_future = executor.submit(fetch_forex_vnd_per_usd)
        return (
            weather_future.result(),
            prices_future.result(),
            forex_future.result(),
        )


def _build_full_delivery(report_date: str) -> DigestDelivery:
    with ThreadPoolExecutor(max_workers=2) as executor:
        brief_future = executor.submit(_fetch_brief_data, report_date)
        news_future = executor.submit(fetch_grouped_news, report_date)
        weather, prices, forex = brief_future.result()
        grouped = news_future.result()

    messages = [
        build_brief_html(report_date, weather, prices, forex),
        *build_news_groups_html_list(report_date, grouped),
    ]
    return DigestDelivery(messages=messages)


def _build_news_delivery(report_date: str) -> DigestDelivery:
    grouped = fetch_grouped_news(report_date)
    return DigestDelivery(messages=build_news_groups_html_list(report_date, grouped))


def build_digest_delivery(section: DigestSection) -> DigestDelivery:
    report_date = _report_date()

    if section == DigestSection.FULL:
        return _build_full_delivery(report_date)

    if section == DigestSection.NEWS:
        return _build_news_delivery(report_date)

    if section == DigestSection.WEATHER:
        return DigestDelivery(
            messages=[build_weather_html(report_date, fetch_weather())],
        )

    if section == DigestSection.RATES:
        return DigestDelivery(
            messages=[
                build_rates_html(
                    report_date,
                    fetch_crypto_prices_usd(),
                    fetch_forex_vnd_per_usd(),
                )
            ],
        )

    raise ValueError(f"Unknown section: {section}")


def build_digest_html(section: DigestSection) -> str:
    """Single-message HTML for weather/rates; first message only for full/news."""
    delivery = build_digest_delivery(section)
    if not delivery.messages:
        return ""
    return delivery.messages[0]
