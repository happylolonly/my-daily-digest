from __future__ import annotations

import html
import re

_FENCE_RE = re.compile(r"^```(?:html)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_MARKDOWN_BOLD_RE = re.compile(r"\*\*([^*\n][^*]*?)\*\*")
_MARKDOWN_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n][^*]*?)\*(?!\*)")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_OPEN_INLINE_RE = re.compile(r"^<\s*(b|i|u|strong|em|code)\s*>$", re.IGNORECASE)
_CLOSE_INLINE_RE = re.compile(r"^<\s*/\s*(b|i|u|strong|em|code)\s*>$", re.IGNORECASE)
_OPEN_LINK_RE = re.compile(r'^<\s*a\s+href\s*=\s*"([^"]+)"\s*>$', re.IGNORECASE)
_CLOSE_LINK_RE = re.compile(r"^<\s*/\s*a\s*>$", re.IGNORECASE)
_INLINE_LINK_RE = re.compile(
    r'<a\s+href="([^"]+)">(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

_INLINE_TAGS = frozenset({"b", "i", "u", "code"})
_TAG_ALIASES = {"strong": "b", "em": "i"}


def _canonical_tag(name: str) -> str:
    return _TAG_ALIASES.get(name.lower(), name.lower())


def _safe_href(href: str) -> bool:
    lowered = href.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def normalize_telegram_html(text: str) -> str:
    """Strip LLM artifacts, normalize breaks, convert common markdown."""
    text = text.strip()
    text = text.replace("\\n", "\n").replace("\\t", "\t")
    text = _FENCE_RE.sub("", text).strip()
    text = _BR_RE.sub("\n", text)
    text = _MARKDOWN_LINK_RE.sub(r'<a href="\2">\1</a>', text)
    text = _MARKDOWN_BOLD_RE.sub(r"<b>\1</b>", text)
    text = _MARKDOWN_ITALIC_RE.sub(r"<i>\1</i>", text)
    return text


def ensure_html_safe(text: str) -> str:
    """
    Return Telegram-safe HTML.

    Escapes plain text and href values, keeps supported tags, and closes tags
    the LLM may leave open.
    """
    text = normalize_telegram_html(text)
    parts: list[str] = []
    open_tags: list[str] = []
    cursor = 0

    def emit_text(chunk: str) -> None:
        if chunk:
            parts.append(html.escape(chunk))

    def emit_open(tag: str) -> None:
        parts.append(f"<{tag}>")
        open_tags.append(tag)

    def emit_close(tag: str) -> None:
        parts.append(f"</{tag}>")
        open_tags.pop()

    for match in _HTML_TAG_RE.finditer(text):
        emit_text(text[cursor : match.start()])
        token = match.group(0)

        if link := _OPEN_LINK_RE.match(token):
            href = link.group(1)
            if _safe_href(href):
                parts.append(f'<a href="{html.escape(href, quote=True)}">')
                open_tags.append("a")
            else:
                emit_text(token)
            cursor = match.end()
            continue

        if _CLOSE_LINK_RE.match(token):
            if open_tags and open_tags[-1] == "a":
                emit_close("a")
            else:
                emit_text(token)
            cursor = match.end()
            continue

        if inline := _OPEN_INLINE_RE.match(token):
            tag = _canonical_tag(inline.group(1))
            if tag in _INLINE_TAGS:
                emit_open(tag)
            else:
                emit_text(token)
            cursor = match.end()
            continue

        if inline := _CLOSE_INLINE_RE.match(token):
            tag = _canonical_tag(inline.group(1))
            if tag in _INLINE_TAGS and open_tags and open_tags[-1] == tag:
                emit_close(tag)
            else:
                emit_text(token)
            cursor = match.end()
            continue

        emit_text(token)
        cursor = match.end()

    emit_text(text[cursor:])

    while open_tags:
        parts.append(f"</{open_tags.pop()}>")

    return "".join(parts)


def html_to_plain_text(text: str) -> str:
    """Convert report HTML to readable plain text for Telegram fallback sends."""
    text = normalize_telegram_html(text)
    text = _INLINE_LINK_RE.sub(
        lambda match: f"{match.group(2)} ({match.group(1)})",
        text,
    )
    text = _HTML_TAG_RE.sub("", text)
    return html.unescape(text).strip()
