from __future__ import annotations

import logging
import os

import requests

from digest.config import HTTP_TIMEOUT_S


def fetch_weather() -> str | None:
    api_key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": "Da Nang,VN",
            "appid": api_key,
            "lang": "en",
            "units": "metric",
        }
        r = requests.get(url, params=params, timeout=HTTP_TIMEOUT_S)
        r.raise_for_status()
        data = r.json()

        temp = data["main"]["temp"]
        feels = data["main"].get("feels_like")
        humidity = data["main"].get("humidity")
        wind = data.get("wind", {}).get("speed")
        condition = (data.get("weather") or [{}])[0].get("description", "")

        feels_part = f", feels like {feels}C" if feels is not None else ""
        wind_part = f", wind {wind} m/s" if wind is not None else ""
        return (
            f"Da Nang: {temp}C{feels_part}, humidity {humidity}%, {condition}{wind_part}."
        )
    except Exception:
        logging.exception("fetch_weather failed")
        return None
