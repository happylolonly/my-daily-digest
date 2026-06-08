from __future__ import annotations

import logging
from calendar import timegm
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

from digest.config import DA_NANG_TZ, HTTP_TIMEOUT_S

MAX_ARTICLES_PER_TOPIC = 5
NEWS_LOOKBACK_HOURS = 24
USER_AGENT = "DailyDigestBot/1.0 (+https://github.com/)"

# Reuters RSS is no longer available; BBC World is a stable geopolitics substitute.
FEEDS: dict[str, str] = {
    "AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "Крипта": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Геополитика": "http://feeds.bbci.co.uk/news/world/rss.xml",
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


def _select_recent_items(items: list[NewsItem], cutoff_utc: datetime) -> list[NewsItem]:
    items = _dedupe_items(items)
    recent = [
        item
        for item in items
        if item.published is not None and item.published >= cutoff_utc
    ]
    if recent:
        recent.sort(key=lambda item: item.published or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return recent[:MAX_ARTICLES_PER_TOPIC]

    return items[:MAX_ARTICLES_PER_TOPIC]


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
        selected = _select_recent_items(items, cutoff_utc)
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
