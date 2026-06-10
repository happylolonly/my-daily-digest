from __future__ import annotations

import logging
from typing import Any

import requests

from digest.config import HTTP_TIMEOUT_S

WTTR_LOCATION = "Da+Nang,Vietnam"
USER_AGENT = "DailyDigestBot/1.0 (+https://github.com/)"

# wttr hourly slots: 0, 300, 600, ... — grouped for digest periods
_PERIOD_HOURS: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("morning", (600, 900)),
    ("day", (1200, 1500)),
    ("evening", (1800, 2100)),
    ("night", (0, 300)),
)


def _normalize_time_12h(raw: str) -> str:
    raw = raw.strip()
    if " " not in raw:
        return raw
    clock, meridiem = raw.rsplit(" ", 1)
    parts = clock.split(":")
    if len(parts) != 2:
        return raw
    hour = int(parts[0])
    minute = parts[1]
    if meridiem.upper() == "PM" and hour != 12:
        hour += 12
    elif meridiem.upper() == "AM" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute}"


def _hourly_by_time(day: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(hour["time"]): hour for hour in day.get("hourly", [])}


def _temp_range_label(temps: list[int]) -> str:
    low, high = min(temps), max(temps)
    if low == high:
        return f"{low}°C"
    return f"{low}–{high}°C"


def _unique_conditions(hours: list[dict[str, Any]]) -> str:
    seen: set[str] = set()
    labels: list[str] = []
    for hour in hours:
        label = hour["weatherDesc"][0]["value"].strip().lower()
        if label in seen:
            continue
        seen.add(label)
        labels.append(label)
    return ", ".join(labels)


def _format_today_line(day: dict[str, Any]) -> str:
    astronomy = day["astronomy"][0]
    sunrise = _normalize_time_12h(astronomy.get("sunrise", ""))
    sunset = _normalize_time_12h(astronomy.get("sunset", ""))
    return (
        f"TODAY: {day['mintempC']}–{day['maxtempC']}°C; "
        f"sunrise {sunrise}; sunset {sunset}"
    )


def _format_now_line(current: dict[str, Any]) -> str:
    temp = current["temp_C"]
    feels = current.get("FeelsLikeC")
    humidity = current.get("humidity")
    wind_kmph = current.get("windspeedKmph")
    wind_dir = current.get("winddir16Point")
    condition = current["weatherDesc"][0]["value"].strip()
    if "," in condition:
        condition = condition.split(",", 1)[0].strip()

    feels_part = f"; feels {feels}°C" if feels else ""
    wind_part = f"; wind {wind_kmph} km/h {wind_dir}" if wind_kmph else ""
    return f"NOW: {temp}°C{feels_part}; humidity {humidity}%; {condition}{wind_part}"


def _format_period_line(period_id: str, hours: list[dict[str, Any]]) -> str:
    temps = [int(hour["tempC"]) for hour in hours]
    rains = [int(hour.get("chanceofrain", 0) or 0) for hour in hours]
    return (
        f"PERIOD {period_id}: {_temp_range_label(temps)}; "
        f"rain max {max(rains)}%; {_unique_conditions(hours)}"
    )


def _format_period_forecast(day: dict[str, Any]) -> list[str]:
    by_time = _hourly_by_time(day)
    lines: list[str] = []
    for period_id, hour_keys in _PERIOD_HOURS:
        hours = [by_time[key] for key in hour_keys if key in by_time]
        if hours:
            lines.append(_format_period_line(period_id, hours))
    return lines


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

        lines = [
            _format_today_line(today),
            _format_now_line(current),
            *_format_period_forecast(today),
        ]
        return "\n".join(lines)
    except Exception:
        logging.exception("fetch_weather failed")
        return None
