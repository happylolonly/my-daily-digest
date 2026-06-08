from __future__ import annotations

import logging

import requests

from digest.config import HTTP_TIMEOUT_S


def fetch_crypto_prices_usd() -> str | None:
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "bitcoin,ethereum",
            "vs_currencies": "usd",
        }
        r = requests.get(url, params=params, timeout=HTTP_TIMEOUT_S)
        r.raise_for_status()
        data = r.json()

        btc = data.get("bitcoin", {}).get("usd")
        eth = data.get("ethereum", {}).get("usd")
        if btc is None or eth is None:
            return None

        return f"BTC: ${btc:,} ; ETH: ${eth:,}"
    except Exception:
        logging.exception("fetch_crypto_prices_usd failed")
        return None
