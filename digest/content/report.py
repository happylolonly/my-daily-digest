from __future__ import annotations

from digest.content.telegram_html import ensure_html_safe

_NEWS_ITEM_SEP = " — "


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


def _format_news_body(news_text: str | None) -> str:
    text = _safe_or_unavailable(news_text)
    if text == "данные недоступны":
        return text

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
    parts = [
        f"<b>🌤 Погода — Da Nang</b> ({report_date})",
        "",
        _format_weather_body(weather_text),
    ]
    return ensure_html_safe("\n".join(parts).strip())


def build_rates_html(
    report_date: str,
    prices_text: str | None,
    forex_text: str | None,
) -> str:
    parts = [
        f"<b>💰 Курсы</b> ({report_date})",
        "",
        _format_rates_body(prices_text, forex_text),
    ]
    return ensure_html_safe("\n".join(parts).strip())


def build_news_html(report_date: str, news_text: str | None) -> str:
    parts = [
        f"<b>📰 Новости</b> ({report_date})",
        "",
        _format_news_body(news_text),
    ]
    return ensure_html_safe("\n".join(parts).strip())


def build_plain_text_report_html(
    report_date: str,
    weather_text: str | None,
    prices_text: str | None,
    forex_text: str | None,
    news_text: str | None,
) -> str:
    parts: list[str] = [
        f"<b>📅 {report_date}</b>",
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
    return ensure_html_safe("\n".join(parts).strip())
