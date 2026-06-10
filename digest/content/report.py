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


def _format_weather_body(weather_text: str | None) -> str:
    text = _safe_or_unavailable(weather_text)
    if text == "данные недоступны":
        return text

    body = text
    if body.startswith("Da Nang "):
        body = body[len("Da Nang ") :]

    lines: list[str] = []
    if " Now: " in body:
        summary, rest = body.split(" Now: ", 1)
        lines.append(summary.strip().rstrip("."))
        if " Hourly: " in rest:
            now_part, hourly = rest.split(" Hourly: ", 1)
            lines.append(f"<b>Сейчас</b>: {now_part.strip().rstrip('.')}")
            hourly_slots = [
                slot.strip()
                for slot in hourly.strip().rstrip(".").split(";")
                if slot.strip()
            ]
            if hourly_slots:
                lines.append("<b>По часам</b>:")
                lines.extend(f"• {slot}" for slot in hourly_slots)
        else:
            lines.append(f"<b>Сейчас</b>: {rest.strip()}")
    else:
        lines.append(body)

    return "\n".join(lines)


def _format_rates_body(prices_text: str | None, forex_text: str | None) -> str:
    lines: list[str] = []
    prices = _safe_or_unavailable(prices_text)
    if prices == "данные недоступны":
        lines.append(prices)
    else:
        for part in prices.split(" ; "):
            part = part.strip()
            if ": " in part:
                label, value = part.split(": ", 1)
                lines.append(f"<b>{label}</b>: {value}")
            elif part:
                lines.append(part)

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
            if ". " in left and left[0].isdigit():
                number, title = left.split(". ", 1)
                return f"{number}. <a href=\"{url}\">{title}</a>"
            return f'<a href="{url}">{left}</a>'

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
