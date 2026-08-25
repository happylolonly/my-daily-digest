"""Characterization tests for the news-formatting helpers in report.py.

Scope is deliberately limited to the pure news formatters; the date/weather
glue (build_brief_html etc.) is left out of the safety net per the plan.
"""

from __future__ import annotations

from digest.content.news.fetch import GroupNews, GroupedNewsResult, TopicBlock, TopicFailure
from digest.content.news.topics import NewsGroup, NewsTopic
from digest.content.report import (
    _format_failures_footer,
    _format_news_body,
    _format_news_item_line,
    build_group_news_html,
    build_news_delivery_messages,
    build_news_groups_html_list,
    build_news_unavailable_html,
    build_openrouter_cost_html,
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


# --- failure visibility ------------------------------------------------------


def _topic(topic_id: str = "ai", label: str = "ИИ:") -> NewsTopic:
    return NewsTopic(
        id=topic_id,
        group_id="tech",
        label=label,
        search_brief="x",
    )


def test_build_news_unavailable_html_includes_openrouter_http_reason() -> None:
    html = build_news_unavailable_html("2026-08-03", "HTTP 402")
    assert "Новости недоступны" in html
    assert "(OpenRouter HTTP 402)" in html


def test_build_news_unavailable_html_uses_short_non_http_label() -> None:
    html = build_news_unavailable_html("2026-08-03", "no key")
    assert "(no key)" in html
    assert "OpenRouter" not in html.split("(")[-1]


def test_format_failures_footer_lists_labels_and_reasons() -> None:
    footer = _format_failures_footer(
        [
            TopicFailure(topic=_topic("ai", "ИИ:"), reason="timeout"),
            TopicFailure(topic=_topic("crypto", "Крипта:"), reason="HTTP 402"),
        ]
    )
    assert footer == "не загрузилось: ИИ (timeout), Крипта (HTTP 402)"


def test_build_group_news_html_appends_failure_footer() -> None:
    group = NewsGroup(id="tech", title="Технологии", emoji="💡", topic_ids=("ai",))
    html = build_group_news_html(
        group,
        ["ИИ:\n1. Новость — https://x.com/a"],
        "2026-08-03",
        failures=[TopicFailure(topic=_topic(), reason="timeout")],
    )
    assert "подробнее" in html
    assert "не загрузилось: ИИ (timeout)" in html


def test_build_group_news_html_dead_group_is_header_plus_footer() -> None:
    group = NewsGroup(id="world", title="Мировое", emoji="🌍", topic_ids=("economy",))
    html = build_group_news_html(
        group,
        [],
        "2026-08-03",
        failures=[
            TopicFailure(
                topic=_topic("economy", "Экономика:"),
                reason="HTTP 402",
            )
        ],
    )
    assert "Мировое" in html
    assert "не загрузилось: Экономика (HTTP 402)" in html
    assert "данные недоступны" not in html


# --- build_news_groups_html_list ---------------------------------------------


def test_build_news_groups_html_list_one_message_per_group() -> None:
    group = NewsGroup(id="tech", title="Технологии", emoji="💡", topic_ids=("ai",))
    topic_block = TopicBlock(topic=_topic(), text="ИИ:\n1. Новость — https://x.com/a")
    grouped = [GroupNews(group=group, blocks=[topic_block])]

    messages = build_news_groups_html_list("2026-06-13", grouped)

    assert len(messages) == 1
    assert "Технологии" in messages[0]
    assert "💡" in messages[0]
    assert '<a href="https://x.com/a">подробнее</a>' in messages[0]


# --- OpenRouter cost footer --------------------------------------------------


def test_build_openrouter_cost_html_formats_usd() -> None:
    assert "OpenRouter" in build_openrouter_cost_html(0.01234)
    assert "$0.0123" in build_openrouter_cost_html(0.01234)


def test_build_news_delivery_messages_appends_cost_after_groups() -> None:
    group = NewsGroup(id="tech", title="Технологии", emoji="💡", topic_ids=("ai",))
    topic_block = TopicBlock(topic=_topic(), text="ИИ:\n1. Новость — https://x.com/a")
    result = GroupedNewsResult(
        groups=[GroupNews(group=group, blocks=[topic_block])],
        total_cost=0.042,
    )

    messages = build_news_delivery_messages("2026-06-13", result)

    assert len(messages) == 2
    assert "Технологии" in messages[0]
    assert messages[1] == build_openrouter_cost_html(0.042)


def test_build_news_delivery_messages_skips_zero_cost() -> None:
    group = NewsGroup(id="tech", title="Технологии", emoji="💡", topic_ids=("ai",))
    topic_block = TopicBlock(topic=_topic(), text="ИИ:\n1. Новость — https://x.com/a")
    result = GroupedNewsResult(
        groups=[GroupNews(group=group, blocks=[topic_block])],
    )

    messages = build_news_delivery_messages("2026-06-13", result)

    assert len(messages) == 1
    assert "OpenRouter" not in messages[0]


def test_build_news_delivery_messages_appends_cost_after_unavailable() -> None:
    result = GroupedNewsResult(
        groups=[],
        unavailable_reason="parse",
        total_cost=0.01,
    )

    messages = build_news_delivery_messages("2026-08-03", result)

    assert len(messages) == 2
    assert "Новости недоступны" in messages[0]
    assert "$0.0100" in messages[1]
