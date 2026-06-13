"""Characterization tests for the news-formatting helpers in report.py.

Scope is deliberately limited to the pure news formatters; the date/weather
glue (build_brief_html etc.) is left out of the safety net per the plan.
"""

from __future__ import annotations

from digest.content.news.fetch import GroupNews, TopicBlock
from digest.content.news.topics import NewsGroup
from digest.content.report import (
    _format_news_body,
    _format_news_item_line,
    build_news_groups_html_list,
)


# --- _format_news_item_line --------------------------------------------------


def test_format_news_item_line_wraps_numbered_link() -> None:
    line = _format_news_item_line("1. Большая новость — https://x.com/a")
    assert line == '1. Большая новость (<a href="https://x.com/a">подробнее</a>)'


def test_format_news_item_line_without_separator_returns_input() -> None:
    assert _format_news_item_line("Просто текст") == "Просто текст"


def test_format_news_item_line_non_http_tail_is_left_alone() -> None:
    assert _format_news_item_line("Заголовок — ftp://x") == "Заголовок — ftp://x"


# --- _format_news_body -------------------------------------------------------


def test_format_news_body_bolds_section_header() -> None:
    body = _format_news_body("Технологии:\n1. A — https://x.com/a")
    assert "<b>Технологии:</b>" in body
    assert "подробнее" in body


def test_format_news_body_passes_preformatted_html_through() -> None:
    assert _format_news_body("<b>уже</b> готово") == "<b>уже</b> готово"


def test_format_news_body_unavailable_when_empty() -> None:
    assert _format_news_body(None) == "данные недоступны"


# --- build_news_groups_html_list ---------------------------------------------


def test_build_news_groups_html_list_one_message_per_group() -> None:
    group = NewsGroup(id="tech", title="Технологии", emoji="💡", topic_ids=("ai",))
    topic_block = TopicBlock(topic=None, text="ИИ:\n1. Новость — https://x.com/a")
    grouped = [GroupNews(group=group, blocks=[topic_block])]

    messages = build_news_groups_html_list("2026-06-13", grouped)

    assert len(messages) == 1
    assert "Технологии" in messages[0]
    assert "💡" in messages[0]
    assert '<a href="https://x.com/a">подробнее</a>' in messages[0]
