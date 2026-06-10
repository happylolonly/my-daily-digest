from __future__ import annotations

import random

from digest.config import format_report_date_ru
from digest.content.news.fetch import GroupNews
from digest.content.news.topics import NewsGroup
from digest.content.telegram_html import ensure_html_safe

_NEWS_ITEM_SEP = " — "

_MOTIVATION_EN: tuple[str, ...] = (
    "The only way to do great work is to love what you do.",
    "Act as if what you do makes a difference. It does.",
    "Success is not final, failure is not fatal: it is the courage to continue that counts.",
    "The future depends on what you do today.",
    "Do one thing every day that scares you.",
    "It always seems impossible until it's done.",
    "Start where you are. Use what you have. Do what you can.",
    "You don't have to be great to start, but you have to start to be great.",
    "Progress, not perfection.",
    "Every morning is a fresh start.",
    "Dream big. Start small. Act now.",
    "Believe you can and you're halfway there.",
)


def pick_motivation_quote() -> str:
    return random.choice(_MOTIVATION_EN)


def _motivation_parts() -> list[str]:
    return [
        "",
        "<b>💪 На сегодня</b>",
        f"<i>{pick_motivation_quote()}</i>",
    ]


def format_motivation_html() -> str:
    return ensure_html_safe("\n".join(_motivation_parts()))


def _safe_or_unavailable(text: str | None) -> str:
    return text if text else "данные недоступны"


_PERIOD_LABELS_RU: dict[str, str] = {
    "morning": "Утро",
    "day": "День",
    "evening": "Вечер",
    "night": "Ночь",
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


def _translate_wind_ru(wind: str) -> str:
    wind = wind.replace(" km/h ", " км/ч ")
    parts = wind.rsplit(" ", 1)
    if len(parts) == 2:
        speed, direction = parts
        direction_ru = _WIND_DIR_RU.get(direction.strip(), direction.strip())
        return f"{speed.strip()} {direction_ru}"
    return wind


def _format_weather_today_line(raw: str) -> str:
    # TODAY: 26–29°C; sunrise 05:15; sunset 18:18
    payload = raw.removeprefix("TODAY:").strip()
    parts = [part.strip() for part in payload.split(";") if part.strip()]
    formatted: list[str] = []
    for part in parts:
        if part.startswith("sunrise "):
            formatted.append(f"восход {part.removeprefix('sunrise ').strip()}")
        elif part.startswith("sunset "):
            formatted.append(f"закат {part.removeprefix('sunset ').strip()}")
        else:
            formatted.append(part)
    return " · ".join(formatted)


def _format_weather_now_line(raw: str) -> str:
    # NOW: 30°C; feels 37°C; humidity 79%; Light Rain; wind 9 km/h N
    payload = raw.removeprefix("NOW:").strip()
    parts = [part.strip() for part in payload.split(";") if part.strip()]
    formatted: list[str] = []
    for part in parts:
        if part.startswith("feels "):
            formatted.append(f"ощущ. {part.removeprefix('feels ').strip()}")
        elif part.startswith("humidity "):
            formatted.append(f"влажность {part.removeprefix('humidity ').strip()}")
        elif part.startswith("wind "):
            wind = _translate_wind_ru(part.removeprefix("wind ").strip())
            formatted.append(f"ветер {wind}")
        else:
            formatted.append(_translate_weather_condition(part))
    return ", ".join(formatted)


def _format_weather_period_line(raw: str) -> str:
    # PERIOD morning: 27–29°C; rain max 20%; patchy rain nearby
    period_id, payload = raw.removeprefix("PERIOD ").split(": ", 1)
    label = _PERIOD_LABELS_RU.get(period_id, period_id)
    parts = [part.strip() for part in payload.split(";") if part.strip()]
    formatted: list[str] = []
    for part in parts:
        if part.startswith("rain max "):
            formatted.append(f"дождь до {part.removeprefix('rain max ').strip()}")
        else:
            formatted.append(_translate_weather_conditions(part))
    return f"<b>{label}</b>: " + ", ".join(formatted)


def _format_weather_body(weather_text: str | None) -> str:
    text = _safe_or_unavailable(weather_text)
    if text == "данные недоступны":
        return text

    lines: list[str] = []
    for raw_line in text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        if raw_line.startswith("TODAY:"):
            lines.append(_format_weather_today_line(raw_line))
        elif raw_line.startswith("NOW:"):
            lines.append(f"<b>Сейчас</b>: {_format_weather_now_line(raw_line)}")
        elif raw_line.startswith("PERIOD "):
            lines.append(_format_weather_period_line(raw_line))
        else:
            lines.append(raw_line)

    return "\n".join(lines)


def _format_rates_body(prices_text: str | None, forex_text: str | None) -> str:
    lines: list[str] = []
    prices = _safe_or_unavailable(prices_text)
    if prices == "данные недоступны":
        lines.append(prices)
    else:
        crypto_parts: list[str] = []
        for part in prices.split(" ; "):
            part = part.strip()
            if ": " in part:
                label, value = part.split(": ", 1)
                crypto_parts.append(f"<b>{label}</b>: {value}")
            elif part:
                crypto_parts.append(part)
        if crypto_parts:
            lines.append(" · ".join(crypto_parts))

    forex_value = _safe_or_unavailable(forex_text)
    lines.append(f"<b>VND/USD</b>: {forex_value}")
    return "\n".join(lines)


def _format_news_item_line(line: str) -> str:
    line = line.strip()
    if not line:
        return ""

    if _NEWS_ITEM_SEP in line:
        left, url = line.rsplit(_NEWS_ITEM_SEP, 1)
        url = url.strip()
        if url.startswith("http"):
            more = f'(<a href="{url}">подробнее</a>)'
            if ". " in left and left[0].isdigit():
                number, title = left.split(". ", 1)
                return f"{number}. {title} {more}"
            return f"{left} {more}"

    return line


def _is_preformatted_news_html(text: str) -> bool:
    return "<a href=" in text or "<b>" in text


def _format_news_body(news_text: str | None) -> str:
    text = _safe_or_unavailable(news_text)
    if text == "данные недоступны":
        return text

    if _is_preformatted_news_html(text):
        return ensure_html_safe(text)

    blocks: list[str] = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        header = lines[0].strip()
        section_lines: list[str] = []
        if header.endswith(":"):
            section_lines.append(f"<b>{header}</b>")
            for line in lines[1:]:
                item = _format_news_item_line(line)
                if item:
                    section_lines.append(item)
        else:
            for line in lines:
                item = _format_news_item_line(line)
                if item:
                    section_lines.append(item)
        blocks.append("\n".join(section_lines))

    return "\n\n".join(blocks)


def build_weather_html(report_date: str, weather_text: str | None) -> str:
    date_label = format_report_date_ru(report_date)
    parts = [
        f"<b>🌤 Погода — Da Nang</b> ({date_label})",
        "",
        _format_weather_body(weather_text),
    ]
    return ensure_html_safe("\n".join(parts).strip())


def build_rates_html(
    report_date: str,
    prices_text: str | None,
    forex_text: str | None,
) -> str:
    date_label = format_report_date_ru(report_date)
    parts = [
        f"<b>💰 Курсы</b> ({date_label})",
        "",
        _format_rates_body(prices_text, forex_text),
    ]
    return ensure_html_safe("\n".join(parts).strip())


def build_news_html(report_date: str, news_text: str | None) -> str:
    date_label = format_report_date_ru(report_date)
    parts = [
        f"<b>📰 Новости</b> ({date_label})",
        "",
        _format_news_body(news_text),
    ]
    return ensure_html_safe("\n".join(parts).strip())


def build_brief_html(
    report_date: str,
    weather_text: str | None,
    prices_text: str | None,
    forex_text: str | None,
) -> str:
    date_label = format_report_date_ru(report_date)
    parts: list[str] = [
        f"<b>📅 {date_label}</b>",
        "",
        "<b>🌤 Погода — Da Nang</b>",
        _format_weather_body(weather_text),
        "",
        "<b>💰 Курсы</b>",
        _format_rates_body(prices_text, forex_text),
    ]
    parts.extend(_motivation_parts())
    return ensure_html_safe("\n".join(parts).strip())


def build_group_news_html(
    group: NewsGroup,
    block_texts: list[str],
    report_date: str,
) -> str:
    date_label = format_report_date_ru(report_date)
    parts = [
        f"<b>{group.emoji} {group.title}</b> ({date_label})",
        "",
        _format_news_body("\n\n".join(block_texts)),
    ]
    return ensure_html_safe("\n".join(parts).strip())


def build_news_groups_html_list(
    report_date: str,
    grouped: list[GroupNews],
) -> list[str]:
    return [
        build_group_news_html(
            group_news.group,
            [block.text for block in group_news.blocks],
            report_date,
        )
        for group_news in grouped
    ]


def build_plain_text_report_html(
    report_date: str,
    weather_text: str | None,
    prices_text: str | None,
    forex_text: str | None,
    news_text: str | None,
    *,
    include_motivation: bool = True,
) -> str:
    date_label = format_report_date_ru(report_date)
    parts: list[str] = [
        f"<b>📅 {date_label}</b>",
        "",
        "<b>🌤 Погода — Da Nang</b>",
        _format_weather_body(weather_text),
        "",
        "<b>💰 Курсы</b>",
        _format_rates_body(prices_text, forex_text),
        "",
        "<b>📰 Новости</b>",
        _format_news_body(news_text),
    ]
    if include_motivation:
        parts.extend(_motivation_parts())
    return ensure_html_safe("\n".join(parts).strip())


def build_full_digest_html(
    report_date: str,
    weather_text: str | None,
    prices_text: str | None,
    forex_text: str | None,
    news_text: str | None,
) -> str:
    return build_plain_text_report_html(
        report_date=report_date,
        weather_text=weather_text,
        prices_text=prices_text,
        forex_text=forex_text,
        news_text=news_text,
        include_motivation=True,
    )
