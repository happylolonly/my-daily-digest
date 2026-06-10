from __future__ import annotations

_PERIOD_EMOJI: dict[str, str] = {
    "morning": "🌅",
    "day": "☀️",
    "evening": "🌇",
    "night": "🌙",
}

_CONDITION_RU: dict[str, str] = {
    "clear": "ясно",
    "sunny": "солнечно",
    "partly cloudy": "переменная облачность",
    "cloudy": "облачно",
    "overcast": "пасмурно",
    "mist": "туман",
    "fog": "туман",
    "haze": "дымка",
    "patchy rain nearby": "местами дождь",
    "patchy light drizzle": "местами лёгкая морось",
    "patchy light rain": "местами лёгкий дождь",
    "patchy light rain with thunder": "местами лёгкий дождь с грозой",
    "light drizzle": "лёгкая морось",
    "light rain": "лёгкий дождь",
    "light rain shower": "лёгкий ливень",
    "moderate rain": "умеренный дождь",
    "moderate rain at times": "временами умеренный дождь",
    "heavy rain": "сильный дождь",
    "heavy rain at times": "временами сильный дождь",
    "thundery outbreaks in nearby": "гроза поблизости",
    "thunderstorm": "гроза",
    "thunderstorm in vicinity": "гроза поблизости",
    "rain with thunderstorm": "дождь с грозой",
    "freezing fog": "изморозь",
    "blowing snow": "метель",
    "blizzard": "метель",
}

_WIND_DIR_RU: dict[str, str] = {
    "N": "С",
    "NNE": "ССВ",
    "NE": "СВ",
    "ENE": "ВСВ",
    "E": "В",
    "ESE": "ВЮВ",
    "SE": "ЮВ",
    "SSE": "ЮЮВ",
    "S": "Ю",
    "SSW": "ЮЮЗ",
    "SW": "ЮЗ",
    "WSW": "ЗЮЗ",
    "W": "З",
    "WNW": "ЗСЗ",
    "NW": "СЗ",
    "NNW": "ССЗ",
}


def _translate_weather_condition(en: str) -> str:
    key = en.strip().lower()
    if not key:
        return en.strip()
    if key in _CONDITION_RU:
        return _CONDITION_RU[key]
    for pattern, ru in sorted(_CONDITION_RU.items(), key=lambda item: -len(item[0])):
        if pattern in key:
            return ru
    return en.strip()


def _translate_weather_conditions(text: str) -> str:
    return ", ".join(
        _translate_weather_condition(part) for part in text.split(",") if part.strip()
    )


def _wind_compact(wind: str) -> str:
    parts = wind.replace(" km/h ", " ").rsplit(" ", 1)
    if len(parts) == 2:
        speed, direction = parts
        direction_ru = _WIND_DIR_RU.get(direction.strip(), direction.strip())
        return f"{speed.strip()} {direction_ru}"
    return wind.replace(" km/h ", "")


def _short_condition(ru: str) -> str:
    shortcuts = {
        "переменная облачность": "облачно",
        "местами дождь": "дождь",
        "местами лёгкая морось": "морось",
        "местами лёгкий дождь": "дождь",
        "местами лёгкий дождь с грозой": "гроза",
        "лёгкая морось": "морось",
        "лёгкий дождь": "дождь",
        "лёгкий ливень": "ливень",
        "умеренный дождь": "дождь",
        "временами умеренный дождь": "дождь",
        "сильный дождь": "ливень",
        "временами сильный дождь": "ливень",
        "гроза поблизости": "гроза",
        "дождь с грозой": "гроза",
    }
    return shortcuts.get(ru.lower(), ru)


def _primary_condition(ru_text: str) -> str:
    first = ru_text.split(",")[0].strip()
    return _short_condition(_translate_weather_condition(first))


def _format_today_line(raw: str) -> str:
    payload = raw.removeprefix("TODAY:").strip()
    parts = [part.strip() for part in payload.split(";") if part.strip()]
    temp_line = ""
    sunrise = ""
    sunset = ""
    for part in parts:
        if part.startswith("sunrise "):
            sunrise = part.removeprefix("sunrise ").strip()
        elif part.startswith("sunset "):
            sunset = part.removeprefix("sunset ").strip()
        else:
            temp_line = part

    chunks = [temp_line] if temp_line else []
    if sunrise:
        chunks.append(f"🌅{sunrise}")
    if sunset:
        chunks.append(f"🌇{sunset}")
    return " · ".join(chunks)


def _format_now_line(raw: str) -> str:
    payload = raw.removeprefix("NOW:").strip()
    parts = [part.strip() for part in payload.split(";") if part.strip()]
    temp = ""
    feels = ""
    humidity = ""
    condition = ""
    wind = ""
    for part in parts:
        if part.startswith("feels "):
            feels = part.removeprefix("feels ").strip().removesuffix("°C")
        elif part.startswith("humidity "):
            humidity = part.removeprefix("humidity ").strip()
        elif part.startswith("wind "):
            wind = _wind_compact(part.removeprefix("wind ").strip())
        elif "°C" in part and not temp:
            temp = part.removesuffix("°C")
        else:
            condition = _primary_condition(part)

    chunks: list[str] = []
    if temp:
        temp_chunk = f"🌡 {temp}°C"
        if feels:
            temp_chunk += f" ({feels}°)"
        chunks.append(temp_chunk)
    if humidity:
        chunks.append(f"💧{humidity}")
    if condition:
        chunks.append(condition)
    if wind:
        chunks.append(f"💨{wind}")
    return " · ".join(chunks)


def _format_period_line(raw: str) -> str:
    period_id, payload = raw.removeprefix("PERIOD ").split(": ", 1)
    emoji = _PERIOD_EMOJI.get(period_id, "•")
    parts = [part.strip() for part in payload.split(";") if part.strip()]
    temp = ""
    rain = ""
    condition = ""
    for part in parts:
        if part.startswith("rain max "):
            rain = part.removeprefix("rain max ").strip()
        elif "°C" in part:
            temp = part
        else:
            condition = _primary_condition(_translate_weather_conditions(part))

    chunks = [emoji, temp]
    if rain:
        chunks.append(f"☔{rain}")
    if condition:
        chunks.append(condition)
    return " ".join(chunk for chunk in chunks if chunk)


def format_weather_body(weather_text: str | None) -> str:
    """Format fetch_weather() plain text for Telegram HTML body."""
    if not weather_text:
        return "данные недоступны"

    lines: list[str] = []
    for raw_line in weather_text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        if raw_line.startswith("TODAY:"):
            lines.append(_format_today_line(raw_line))
        elif raw_line.startswith("NOW:"):
            lines.append(_format_now_line(raw_line))
        elif raw_line.startswith("PERIOD "):
            lines.append(_format_period_line(raw_line))
        else:
            lines.append(raw_line)

    return "\n".join(lines)
