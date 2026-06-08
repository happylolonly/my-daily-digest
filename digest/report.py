from __future__ import annotations

import html


def ensure_html_safe(text: str) -> str:
    """
    Telegram HTML parse_mode accepts only a subset of tags.
    We allow <b>/<i>/<u> and escape everything else.
    """
    placeholders = {
        "<b>": "__TAG_B_OPEN__",
        "</b>": "__TAG_B_CLOSE__",
        "<i>": "__TAG_I_OPEN__",
        "</i>": "__TAG_I_CLOSE__",
        "<u>": "__TAG_U_OPEN__",
        "</u>": "__TAG_U_CLOSE__",
    }

    normalized = text
    for tag, ph in placeholders.items():
        normalized = normalized.replace(tag, ph)

    escaped = html.escape(normalized)

    for tag, ph in placeholders.items():
        escaped = escaped.replace(ph, tag)

    return escaped


def build_plain_text_report_html(
    report_date: str,
    weather_text: str | None,
    prices_text: str | None,
    forex_text: str | None,
    news_text: str | None,
) -> str:
    def safe_or_unavailable(s: str | None) -> str:
        return s if s else "данные недоступны"

    parts: list[str] = []
    parts.append(f"<b>📅 {html.escape(report_date)}</b>")
    parts.append("")
    parts.append("<b>🌤 Погода — Da Nang</b>")
    parts.append(html.escape(safe_or_unavailable(weather_text)))
    parts.append("")
    parts.append("<b>💰 Курсы</b>")
    parts.append(html.escape(safe_or_unavailable(prices_text)))
    parts.append(html.escape(f"VND/USD: {safe_or_unavailable(forex_text)}"))
    parts.append("")
    parts.append("<b>📰 Новости</b>")
    parts.append(html.escape(safe_or_unavailable(news_text)))

    return ensure_html_safe("\n".join(parts).strip())
