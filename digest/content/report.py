from __future__ import annotations

import random

from digest.content.telegram_html import ensure_html_safe

_NEWS_ITEM_SEP = " — "

_MOTIVATION_RU: tuple[str, ...] = (
    "Делай сегодня то, что другие не хотят — завтра будешь жить так, как другие не могут.",
    "Лучший способ предсказать будущее — создать его.",
    "Начни с необходимого, сделай возможное — и внезапно окажешься на пороге невозможного.",
    "Успех — это умение переходить от одной неудачи к другой, не теряя энтузиазма.",
    "Не откладывай на завтра то, что можешь сделать сегодня.",
    "Единственный способ делать великую работу — любить то, что ты делаешь.",
    "Трудности готовят обычных людей к необычной судьбе.",
    "Мечты не работают, пока не работаешь ты.",
    "Каждое утро — новый шанс изменить свою жизнь.",
    "Маленькие шаги каждый день приводят к большим результатам.",
    "Смелость — не отсутствие страха, а решение действовать вопреки ему.",
    "Ты сильнее, чем думаешь, и ближе к цели, чем кажется.",
)

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


def pick_motivation_quotes() -> tuple[str, str]:
    return random.choice(_MOTIVATION_RU), random.choice(_MOTIVATION_EN)


def _motivation_parts() -> list[str]:
    ru, en = pick_motivation_quotes()
    return [
        "",
        "<b>💪 На сегодня</b>",
        f"«{ru}»",
        f"<i>{en}</i>",
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
        *_motivation_parts(),
    ]
    return ensure_html_safe("\n".join(parts).strip())
