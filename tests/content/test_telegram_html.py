"""Characterization tests for Telegram HTML normalization and safety.

These lock in the current escaping / tag-closing / safe-href behavior so the
parser and report formatting can be refactored without silently regressing
what gets sent to Telegram.
"""

from __future__ import annotations

from digest.content.telegram_html import (
    ensure_html_safe,
    html_to_plain_text,
    normalize_telegram_html,
)


# --- normalize_telegram_html -------------------------------------------------


def test_normalize_strips_html_fence() -> None:
    assert normalize_telegram_html("```html\n<b>x</b>\n```") == "<b>x</b>"


def test_normalize_converts_literal_escapes_and_br() -> None:
    assert normalize_telegram_html("a\\nb") == "a\nb"
    assert normalize_telegram_html("a<br>b") == "a\nb"


def test_normalize_converts_markdown() -> None:
    assert normalize_telegram_html("**bold**") == "<b>bold</b>"
    assert normalize_telegram_html("*italic*") == "<i>italic</i>"
    assert (
        normalize_telegram_html("[t](https://x.com)") == '<a href="https://x.com">t</a>'
    )


# --- ensure_html_safe --------------------------------------------------------


def test_ensure_html_safe_escapes_plain_text() -> None:
    assert ensure_html_safe("a & b < c") == "a &amp; b &lt; c"


def test_ensure_html_safe_keeps_supported_tags() -> None:
    assert ensure_html_safe("<b>bold</b> <i>it</i> <code>c</code>") == (
        "<b>bold</b> <i>it</i> <code>c</code>"
    )


def test_ensure_html_safe_canonicalizes_tag_aliases() -> None:
    assert ensure_html_safe("<strong>x</strong> <em>y</em>") == "<b>x</b> <i>y</i>"


def test_ensure_html_safe_closes_open_tag() -> None:
    assert ensure_html_safe("<b>bold") == "<b>bold</b>"


def test_ensure_html_safe_keeps_https_link_and_escapes_href() -> None:
    result = ensure_html_safe('<a href="https://x.com/a?b=1&c=2">link</a>')
    assert result == '<a href="https://x.com/a?b=1&amp;c=2">link</a>'


def test_ensure_html_safe_rejects_javascript_href() -> None:
    result = ensure_html_safe('<a href="javascript:alert(1)">x</a>')
    # The unsafe anchor is escaped as plain text, never emitted as a real tag.
    assert "<a " not in result
    assert "&lt;a" in result
    assert "x" in result


# --- html_to_plain_text ------------------------------------------------------


def test_html_to_plain_text_inlines_links() -> None:
    assert (
        html_to_plain_text('<a href="https://x.com">Title</a>')
        == "Title (https://x.com)"
    )


def test_html_to_plain_text_strips_tags_and_unescapes() -> None:
    assert html_to_plain_text("<b>bold</b> a &amp; b") == "bold a & b"
