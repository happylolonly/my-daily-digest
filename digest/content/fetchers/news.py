from __future__ import annotations

import logging
from calendar import timegm
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

from digest.config import DA_NANG_TZ, HTTP_TIMEOUT_S

MAX_ARTICLES_PER_TOPIC = 10
NEWS_LOOKBACK_HOURS = 24
USER_AGENT = "DailyDigestBot/1.0 (+https://github.com/)"

SKIP_TITLE_PATTERNS = ("how to", "review", "best ", "opinion", "podcast", "quiz", "sponsored")

BOOST_BY_TOPIC: dict[str, tuple[str, ...]] = {
    "AI": ("openai", "google", "anthropic", "regulation", "lawsuit", "nvidia", "meta"),
    "Крипта": ("sec", "etf", "hack", "billion", "ban", "bitcoin", "ethereum"),
    "Геополитика": ("war", "sanctions", "election", "nuclear", "ceasefire", "summit", "attack"),
}

# Reuters RSS is no longer available; BBC top stories for curated geopolitics headlines.
FEEDS: dict[str, str] = {
    "AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "Крипта": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Геополитика": "http://feeds.bbci.co.uk/news/rss.xml",
}


@dataclass
class NewsItem:
    title: str
    link: str
    published: datetime | None


def _parse_entry_date(entry: feedparser.FeedParserDict) -> datetime | None:
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            return datetime.fromtimestamp(timegm(parsed), tz=timezone.utc)

    for field in ("published", "updated"):
        raw = entry.get(field)
        if not raw:
            continue
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (TypeError, ValueError, IndexError):
            continue

    return None


def _fetch_feed_entries(url: str) -> list[NewsItem]:
    response = requests.get(
        url,
        timeout=HTTP_TIMEOUT_S,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    parsed = feedparser.parse(response.content)

    items: list[NewsItem] = []
    for entry in parsed.entries:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if not title:
            continue
        items.append(NewsItem(title=title, link=link, published=_parse_entry_date(entry)))

    return items


def _dedupe_items(items: list[NewsItem]) -> list[NewsItem]:
    seen: set[str] = set()
    unique: list[NewsItem] = []
    for item in items:
        key = item.link or item.title
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _should_skip_title(title: str) -> bool:
    lowered = title.lower()
    return any(pattern in lowered for pattern in SKIP_TITLE_PATTERNS)


def _score_item(label: str, title: str, feed_index: int) -> int:
    lowered = title.lower()
    score = max(0, 10 - feed_index)
    score += sum(2 for keyword in BOOST_BY_TOPIC.get(label, ()) if keyword in lowered)
    return score


def _select_recent_items(
    items: list[NewsItem],
    label: str,
    cutoff_utc: datetime,
) -> list[NewsItem]:
    items = _dedupe_items(items)

    dated_recent = [
        item
        for item in items
        if item.published is not None and item.published >= cutoff_utc
    ]
    candidates = dated_recent if dated_recent else items

    scored: list[tuple[int, int, NewsItem]] = []
    for index, item in enumerate(candidates):
        if _should_skip_title(item.title):
            continue
        scored.append((_score_item(label, item.title, index), index, item))

    scored.sort(key=lambda row: (-row[0], row[1]))
    selected = [item for _, _, item in scored[:MAX_ARTICLES_PER_TOPIC]]

    if not selected:
        selected = [
            item for item in candidates if not _should_skip_title(item.title)
        ][:MAX_ARTICLES_PER_TOPIC]
    if not selected:
        selected = candidates[:MAX_ARTICLES_PER_TOPIC]

    return selected


def _format_topic(label: str, items: list[NewsItem]) -> str:
    lines = [f"{label}:"]
    for index, item in enumerate(items, start=1):
        if item.link:
            lines.append(f"{index}. {item.title} — {item.link}")
        else:
            lines.append(f"{index}. {item.title}")
    return "\n".join(lines)


def _fetch_topic(label: str, url: str, cutoff_utc: datetime) -> str | None:
    try:
        items = _fetch_feed_entries(url)
        selected = _select_recent_items(items, label, cutoff_utc)
        if not selected:
            return None
        return _format_topic(label, selected)
    except Exception:
        logging.exception("fetch news topic %s failed", label)
        return None


def fetch_news_last_24h() -> str | None:
    try:
        now = datetime.now(DA_NANG_TZ)
        cutoff_utc = (now - timedelta(hours=NEWS_LOOKBACK_HOURS)).astimezone(timezone.utc)

        sections: list[str] = []
        for label, url in FEEDS.items():
            section = _fetch_topic(label, url, cutoff_utc)
            if section:
                sections.append(section)

        if not sections:
            return None
        return "\n\n".join(sections)
    except Exception:
        logging.exception("fetch_news_last_24h failed")
        return None
