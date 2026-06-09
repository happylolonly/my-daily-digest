from __future__ import annotations

import logging

import requests

from digest.config import HTTP_TIMEOUT_S


def fetch_forex_vnd_per_usd() -> str | None:
    try:
        r = requests.get(
            "https://open.er-api.com/v6/latest/USD",
            timeout=HTTP_TIMEOUT_S,
        )
        r.raise_for_status()
        vnd = r.json()["rates"]["VND"]
        return f"{vnd:,.0f} VND per USD"
    except Exception:
        logging.exception("fetch_forex_vnd_per_usd failed")
        return None
