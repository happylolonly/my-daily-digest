from __future__ import annotations

import html
import re

_NEWS_ITEM_SEP = " — "
_FENCE_RE = re.compile(r"^```(?:html)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_MARKDOWN_BOLD_RE = re.compile(r"\*\*([^*\n][^*]*?)\*\*")
_MARKDOWN_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n][^*]*?)\*(?!\*)")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_OPEN_SIMPLE_TAG_RE = re.compile(r"^<\s*(b|i|u|strong|em|code)\s*>$", re.IGNORECASE)
_CLOSE_SIMPLE_TAG_RE = re.compile(r"^<\s*/\s*(b|i|u|strong|em|code)\s*>$", re.IGNORECASE)
_OPEN_LINK_RE = re.compile(r'^<\s*a\s+href\s*=\s*"([^"]+)"\s*>$', re.IGNORECASE)
_CLOSE_LINK_RE = re.compile(r"^<\s*/\s*a\s*>$", re.IGNORECASE)


def normalize_telegram_html(text: str) -> str:
    """Strip LLM artifacts and normalize line breaks for Telegram HTML."""
    text = text.strip()
    text = _FENCE_RE.sub("", text).strip()
    text = _BR_RE.sub("\n", text)
    text = _MARKDOWN_LINK_RE.sub(r'<a href="\2">\1</a>', text)
    text = _MARKDOWN_BOLD_RE.sub(r"<b>\1</b>", text)
    text = _MARKDOWN_ITALIC_RE.sub(r"<i>\1</i>", text)
    return text


def ensure_html_safe(text: str) -> str:
    """
    Return Telegram-safe HTML.

    Telegram HTML accepts only a small subset of tags. This escapes plain text
    and href values, preserves only supported tags, and balances tags that an
    LLM may leave open.
    """
    text = normalize_telegram_html(text)
    result: list[str] = []
    stack: list[str] = []
    position = 0

    def append_text(value: str) -> None:
        if value:
            result.append(html.escape(value))

    for match in _HTML_TAG_RE.finditer(text):
        append_text(text[position : match.start()])
        token = match.group(0)

        open_link = _OPEN_LINK_RE.match(token)
        if open_link:
            href = html.escape(open_link.group(1), quote=True)
            result.append(f'<a href="{href}">')
            stack.append("a")
            position = match.end()
            continue

        if _CLOSE_LINK_RE.match(token):
            if stack and stack[-1] == "a":
                result.append("</a>")
                stack.pop()
            else:
                append_text(token)
            position = match.end()
            continue

        open_simple = _OPEN_SIMPLE_TAG_RE.match(token)
        if open_simple:
            tag = open_simple.group(1).lower()
            if stack and stack[-1] == "a":
                position = match.end()
                continue
            result.append(f"<{tag}>")
            stack.append(tag)
            position = match.end()
            continue

        close_simple = _CLOSE_SIMPLE_TAG_RE.match(token)
        if close_simple:
            tag = close_simple.group(1).lower()
            if stack and stack[-1] == "a":
                position = match.end()
                continue
            if stack and stack[-1] == tag:
                result.append(f"</{tag}>")
                stack.pop()
            else:
                append_text(token)
            position = match.end()
            continue

        append_text(token)
        position = match.end()

    append_text(text[position:])

    while stack:
        result.append(f"</{stack.pop()}>")

    return "".join(result)


def html_to_plain_text(text: str) -> str:
    """Convert report HTML to readable plain text for Telegram fallback sends."""
    text = normalize_telegram_html(text)
    text = re.sub(
        r'<a\s+href="([^"]+)">(.*?)</a>',
        lambda match: f"{match.group(2)} ({match.group(1)})",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = _HTML_TAG_RE.sub("", text)
    return html.unescape(text).strip()


def _esc(text: str) -> str:
    return text


def _safe_or_unavailable(text: str | None) -> str:
    return text if text else "данные недоступны"


def _format_weather_body(weather_text: str | None) -> str:
    text = _safe_or_unavailable(weather_text)
    if text == "данные недоступны":
        return _esc(text)

    body = text
    if body.startswith("Da Nang "):
        body = body[len("Da Nang ") :]

    lines: list[str] = []
    if " Now: " in body:
        summary, rest = body.split(" Now: ", 1)
        lines.append(_esc(summary.strip().rstrip(".")))
        if " Hourly: " in rest:
            now_part, hourly = rest.split(" Hourly: ", 1)
            lines.append(f"<b>Сейчас</b>: {_esc(now_part.strip().rstrip('.'))}")
            hourly_slots = [
                slot.strip()
                for slot in hourly.strip().rstrip(".").split(";")
                if slot.strip()
            ]
            if hourly_slots:
                lines.append("<b>По часам</b>:")
                lines.extend(f"• {_esc(slot)}" for slot in hourly_slots)
        else:
            lines.append(f"<b>Сейчас</b>: {_esc(rest.strip())}")
    else:
        lines.append(_esc(body))

    return "\n".join(lines)


def _format_rates_body(prices_text: str | None, forex_text: str | None) -> str:
    lines: list[str] = []
    prices = _safe_or_unavailable(prices_text)
    if prices == "данные недоступны":
        lines.append(_esc(prices))
    else:
        for part in prices.split(" ; "):
            part = part.strip()
            if ": " in part:
                label, value = part.split(": ", 1)
                lines.append(f"<b>{_esc(label)}</b>: {_esc(value)}")
            elif part:
                lines.append(_esc(part))

    forex_value = _safe_or_unavailable(forex_text)
    lines.append(f"<b>VND/USD</b>: {_esc(forex_value)}")
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
                return f"{_esc(number)}. " + f'<a href="{url}">{_esc(title)}</a>'
            return f'<a href="{url}">{_esc(left)}</a>'

    return _esc(line)


def _format_news_body(news_text: str | None) -> str:
    text = _safe_or_unavailable(news_text)
    if text == "данные недоступны":
        return _esc(text)

    blocks: list[str] = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        header = lines[0].strip()
        section_lines: list[str] = []
        if header.endswith(":"):
            section_lines.append(f"<b>{_esc(header)}</b>")
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
        f"<b>🌤 Погода — Da Nang</b> ({_esc(report_date)})",
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
        f"<b>💰 Курсы</b> ({_esc(report_date)})",
        "",
        _format_rates_body(prices_text, forex_text),
    ]
    return ensure_html_safe("\n".join(parts).strip())


def build_news_html(report_date: str, news_text: str | None) -> str:
    parts = [
        f"<b>📰 Новости</b> ({_esc(report_date)})",
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
        f"<b>📅 {_esc(report_date)}</b>",
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
