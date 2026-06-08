from __future__ import annotations

import logging
from typing import Any

import requests

from digest.config import HTTP_TIMEOUT_S

WTTR_LOCATION = "Da+Nang,Vietnam"
USER_AGENT = "DailyDigestBot/1.0 (+https://github.com/)"


def _format_wttr_time(raw: str) -> str:
    padded = raw.zfill(4)
    return f"{padded[:2]}:{padded[2:]}"


def _format_current(current: dict[str, Any]) -> str:
    temp = current["temp_C"]
    feels = current.get("FeelsLikeC")
    humidity = current.get("humidity")
    wind_kmph = current.get("windspeedKmph")
    wind_dir = current.get("winddir16Point")
    condition = current["weatherDesc"][0]["value"]

    feels_part = f", feels like {feels}C" if feels else ""
    wind_part = f", wind {wind_kmph} km/h {wind_dir}" if wind_kmph else ""
    return f"Now: {temp}C{feels_part}, humidity {humidity}%, {condition}{wind_part}."


def _format_today_summary(day: dict[str, Any]) -> str:
    astronomy = day["astronomy"][0]
    sunrise = astronomy.get("sunrise", "")
    sunset = astronomy.get("sunset", "")
    return (
        f"Today ({day['date']}): {day['mintempC']}-{day['maxtempC']}C. "
        f"Sunrise {sunrise}, sunset {sunset}."
    )


def _format_hourly_forecast(day: dict[str, Any]) -> str:
    slots: list[str] = []
    for hour in day.get("hourly", []):
        time_label = _format_wttr_time(hour["time"])
        temp = hour["tempC"]
        rain = hour.get("chanceofrain", "0")
        desc = hour["weatherDesc"][0]["value"].lower()
        slots.append(f"{time_label} {temp}C, rain {rain}% — {desc}")

    if not slots:
        return ""
    return "Hourly: " + "; ".join(slots) + "."


def fetch_weather() -> str | None:
    try:
        response = requests.get(
            f"https://wttr.in/{WTTR_LOCATION}",
            params={"format": "j1"},
            timeout=HTTP_TIMEOUT_S,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        data = response.json()

        current = data["current_condition"][0]
        today = data["weather"][0]

        parts = [
            "Da Nang",
            _format_today_summary(today),
            _format_current(current),
            _format_hourly_forecast(today),
        ]
        return " ".join(part for part in parts if part)
    except Exception:
        logging.exception("fetch_weather failed")
        return None
