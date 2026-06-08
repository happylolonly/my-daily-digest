from __future__ import annotations

from dataclasses import dataclass

from digest.content.fetchers.crypto import fetch_crypto_prices_usd
from digest.content.fetchers.forex import fetch_forex_vnd_per_usd
from digest.content.fetchers.news import fetch_news_last_24h
from digest.content.fetchers.weather import fetch_weather


@dataclass
class DigestData:
    weather: str | None
    prices: str | None
    forex: str | None
    news: str | None


def fetch_all() -> DigestData:
    return DigestData(
        weather=fetch_weather(),
        prices=fetch_crypto_prices_usd(),
        forex=fetch_forex_vnd_per_usd(),
        news=fetch_news_last_24h(),
    )
