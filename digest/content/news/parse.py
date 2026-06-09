from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from digest.content.news.topics import NewsTopic

_URL_IN_TEXT_RE = re.compile(r"https?://\S+")
_CITATION_MARKER_RE = re.compile(r"\[\d+\]")

MAX_TOPIC_LINKS = 4
_NEWS_ITEM_SEP = " — "


@dataclass
class ParsedLink:
    url: str
    title: str


@dataclass
class TopicParseResult:
    summary: str
    links: list[ParsedLink]


@dataclass
class SearchResultEntry:
    url: str
    title: str


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip().rstrip("/")
    path = parsed.path.rstrip("/")
    normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"
    if parsed.query:
        normalized = f"{normalized}?{parsed.query}"
    return normalized


def hostname_label(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or url


def clean_summary_text(text: str) -> str:
    text = _URL_IN_TEXT_RE.sub("", text)
    text = _CITATION_MARKER_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def _message_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    choices = payload.get("choices") or []
    if not choices:
        return {}
    message = choices[0].get("message")
    return message if isinstance(message, dict) else {}


def _iter_annotation_citations(payload: dict[str, Any]) -> list[tuple[str, str]]:
    """OpenRouter / Perplexity url_citation annotations: (url, title)."""
    entries: list[tuple[str, str]] = []
    for ann in _message_from_payload(payload).get("annotations") or []:
        if not isinstance(ann, dict) or ann.get("type") != "url_citation":
            continue
        cite = ann.get("url_citation")
        if not isinstance(cite, dict):
            continue
        url = (cite.get("url") or "").strip()
        if not url.startswith("http"):
            continue
        title = (cite.get("title") or "").strip() or hostname_label(url)
        entries.append((url, title))
    return entries


def parse_topic_content(content: str) -> TopicParseResult | None:
    summary = ""
    links: list[ParsedLink] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        upper = line.upper()
        if upper.startswith("SUMMARY:"):
            summary = clean_summary_text(line.split(":", 1)[1])
        elif upper.startswith("LINK:"):
            link_part = line.split(":", 1)[1].strip()
            if "|" in link_part:
                url, title = link_part.split("|", 1)
                url = url.strip()
                title = title.strip()
            elif _NEWS_ITEM_SEP in link_part:
                title, url = link_part.rsplit(_NEWS_ITEM_SEP, 1)
                url = url.strip()
                title = title.strip()
            else:
                continue
            if url.startswith("http") and title:
                links.append(ParsedLink(url=url, title=title))

    if not summary:
        return None
    return TopicParseResult(summary=summary, links=links)


def extract_citation_urls(payload: dict[str, Any]) -> set[str]:
    urls: set[str] = set()

    for citation in payload.get("citations") or []:
        if isinstance(citation, str) and citation.startswith("http"):
            urls.add(normalize_url(citation))

    for item in payload.get("search_results") or []:
        if not isinstance(item, dict):
            continue
        url = (item.get("url") or "").strip()
        if url.startswith("http"):
            urls.add(normalize_url(url))

    for url, _ in _iter_annotation_citations(payload):
        urls.add(normalize_url(url))

    return urls


def extract_search_results(payload: dict[str, Any]) -> list[SearchResultEntry]:
    entries: list[SearchResultEntry] = []
    seen: set[str] = set()

    for item in payload.get("search_results") or []:
        if not isinstance(item, dict):
            continue
        url = (item.get("url") or "").strip()
        if not url.startswith("http"):
            continue
        normalized = normalize_url(url)
        if normalized in seen:
            continue
        seen.add(normalized)
        title = (item.get("title") or "").strip() or hostname_label(url)
        entries.append(SearchResultEntry(url=normalized, title=title))

    for url, title in _iter_annotation_citations(payload):
        normalized = normalize_url(url)
        if normalized in seen:
            continue
        seen.add(normalized)
        entries.append(SearchResultEntry(url=normalized, title=title))

    return entries


def filter_links(links: list[ParsedLink], allowed_urls: set[str]) -> list[ParsedLink]:
    if not allowed_urls:
        return links
    return [
        link for link in links if normalize_url(link.url) in allowed_urls
    ]


def fallback_links(
    allowed_urls: set[str],
    search_results: list[SearchResultEntry],
    *,
    limit: int = MAX_TOPIC_LINKS,
) -> list[ParsedLink]:
    links: list[ParsedLink] = []
    seen: set[str] = set()

    for entry in search_results:
        normalized = normalize_url(entry.url)
        if normalized not in allowed_urls or normalized in seen:
            continue
        links.append(ParsedLink(url=entry.url, title=entry.title))
        seen.add(normalized)
        if len(links) >= limit:
            break

    if links:
        return links

    for url in sorted(allowed_urls):
        if url in seen:
            continue
        links.append(ParsedLink(url=url, title=hostname_label(url)))
        seen.add(url)
        if len(links) >= limit:
            break

    return links


def format_topic_block(topic: NewsTopic, parsed: TopicParseResult) -> str:
    lines = [topic.label, parsed.summary, ""]
    for index, link in enumerate(parsed.links, start=1):
        lines.append(f"{index}. {link.title}{_NEWS_ITEM_SEP}{link.url}")
    return "\n".join(lines)


def payload_to_topic_block(topic: NewsTopic, payload: dict[str, Any]) -> str | None:
    choices = payload.get("choices") or []
    if not choices:
        return None

    content = ((choices[0].get("message") or {}).get("content") or "").strip()
    parsed = parse_topic_content(content)
    if parsed is None:
        return None

    allowed_urls = extract_citation_urls(payload)
    search_results = extract_search_results(payload)
    valid_links = filter_links(parsed.links, allowed_urls)

    if not valid_links and allowed_urls:
        valid_links = fallback_links(allowed_urls, search_results)

    parsed.links = valid_links[:MAX_TOPIC_LINKS]
    return format_topic_block(topic, parsed)
