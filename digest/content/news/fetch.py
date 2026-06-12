from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import Any

from langfuse import propagate_attributes

from digest.content.news.parse import payload_to_topic_block
from digest.content.news.prompt import build_topic_prompt
from digest.content.news.topics import NEWS_GROUPS, NEWS_TOPICS, NewsGroup, NewsTopic
from digest.content.openrouter import chat_completion, openrouter_api_key, usage_cost
from digest.observability import langfuse_enabled
from digest.trace_source import trace_source

DEFAULT_NEWS_MODEL = "perplexity/sonar"
TOPIC_TIMEOUT_S = 30


@dataclass
class TopicBlock:
    topic: NewsTopic
    text: str


@dataclass
class GroupNews:
    group: NewsGroup
    blocks: list[TopicBlock]


def news_model() -> str:
    return os.environ.get("OPENROUTER_NEWS_MODEL", DEFAULT_NEWS_MODEL).strip() or DEFAULT_NEWS_MODEL


def _chat_extra() -> dict[str, Any]:
    return {
        "search_recency_filter": "day",
        "web_search_options": {"search_context_size": "low"},
    }


def _fetch_topic_payload(topic: NewsTopic, report_date: str) -> dict[str, Any] | None:
    prompt = build_topic_prompt(topic, report_date)
    label = topic.label.rstrip(":")

    def _call() -> dict[str, Any] | None:
        return chat_completion(
            model=news_model(),
            messages=[{"role": "user", "content": prompt}],
            extra=_chat_extra(),
            label=label,
        )

    if langfuse_enabled():
        with propagate_attributes(
            trace_name="openrouter-news",
            metadata={
                "source": trace_source(),
                "report_date": report_date,
                "topic": label,
                "topic_id": topic.id,
                "group_id": topic.group_id,
                "model": news_model(),
            },
            tags=["openrouter-news", topic.group_id, label],
        ):
            return _call()
    return _call()


def _fetch_topic_block(topic: NewsTopic, report_date: str) -> tuple[str | None, float]:
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_fetch_topic_payload, topic, report_date)
            payload = future.result(timeout=TOPIC_TIMEOUT_S)
    except FuturesTimeoutError:
        logging.warning("OpenRouter %s timed out after %ss", topic.label.rstrip(":"), TOPIC_TIMEOUT_S)
        return None, 0.0
    except Exception:
        logging.exception("OpenRouter %s failed", topic.label.rstrip(":"))
        return None, 0.0

    if payload is None:
        return None, 0.0

    cost = usage_cost(payload) or 0.0
    block = payload_to_topic_block(topic, payload)
    if block is None:
        logging.warning("OpenRouter %s: failed to parse SUMMARY", topic.label.rstrip(":"))
    return block, cost


def fetch_all_topic_blocks(report_date: str) -> dict[str, TopicBlock]:
    """Fetch all news topics in parallel; returns successful blocks keyed by topic id."""
    if not openrouter_api_key():
        logging.warning("OPENROUTER_API_KEY not set, news unavailable")
        return {}

    blocks: dict[str, TopicBlock] = {}
    total_cost = 0.0

    def _fetch_one(topic: NewsTopic) -> tuple[str, TopicBlock | None, float]:
        text, cost = _fetch_topic_block(topic, report_date)
        if text is None:
            return topic.id, None, cost
        return topic.id, TopicBlock(topic=topic, text=text), cost

    with ThreadPoolExecutor(max_workers=len(NEWS_TOPICS)) as executor:
        for topic_id, block, cost in executor.map(lambda t: _fetch_one(t), NEWS_TOPICS):
            total_cost += cost
            if block is not None:
                blocks[topic_id] = block

    if total_cost:
        logging.info(
            "OpenRouter news total cost: $%.6f (%s/%s topics)",
            total_cost,
            len(blocks),
            len(NEWS_TOPICS),
        )
    return blocks


def group_topic_blocks(blocks: dict[str, TopicBlock]) -> list[GroupNews]:
    """Group topic blocks by NEWS_GROUPS order; skip empty groups."""
    grouped: list[GroupNews] = []
    for group in NEWS_GROUPS:
        group_blocks = [
            blocks[topic_id] for topic_id in group.topic_ids if topic_id in blocks
        ]
        if group_blocks:
            grouped.append(GroupNews(group=group, blocks=group_blocks))
    return grouped


def fetch_grouped_news(report_date: str) -> list[GroupNews]:
    """Fetch all topics and return non-empty groups."""
    blocks = fetch_all_topic_blocks(report_date)
    if not blocks:
        logging.warning("OpenRouter news: all topics failed for %s", report_date)
        return []
    return group_topic_blocks(blocks)


def _ordered_block_texts(blocks: dict[str, TopicBlock]) -> list[str]:
    texts: list[str] = []
    for group in NEWS_GROUPS:
        for topic_id in group.topic_ids:
            block = blocks.get(topic_id)
            if block is not None:
                texts.append(block.text)
    return texts


def fetch_news_body(report_date: str) -> str | None:
    """Fetch Russian news summary as plain text for report._format_news_body."""
    blocks = fetch_all_topic_blocks(report_date)
    texts = _ordered_block_texts(blocks)
    if not texts:
        logging.warning("OpenRouter news: all topics failed for %s", report_date)
        return None
    return "\n\n".join(texts)
