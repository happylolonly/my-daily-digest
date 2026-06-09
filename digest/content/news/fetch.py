from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any

from langfuse import propagate_attributes

from digest.content.news.parse import payload_to_topic_block
from digest.content.news.prompt import build_topic_prompt
from digest.content.news.topics import NEWS_TOPICS, NewsTopic
from digest.content.openrouter import chat_completion, openrouter_api_key
from digest.observability import langfuse_enabled
from digest.trace_source import trace_source

DEFAULT_NEWS_MODEL = "perplexity/sonar"
TOPIC_TIMEOUT_S = 30


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
                "model": news_model(),
            },
            tags=["openrouter-news", label],
        ):
            return _call()
    return _call()


def _fetch_topic_block(topic: NewsTopic, report_date: str) -> str | None:
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_fetch_topic_payload, topic, report_date)
            payload = future.result(timeout=TOPIC_TIMEOUT_S)
    except FuturesTimeoutError:
        logging.warning("OpenRouter %s timed out after %ss", topic.label.rstrip(":"), TOPIC_TIMEOUT_S)
        return None
    except Exception:
        logging.exception("OpenRouter %s failed", topic.label.rstrip(":"))
        return None

    if payload is None:
        return None

    block = payload_to_topic_block(topic, payload)
    if block is None:
        logging.warning("OpenRouter %s: failed to parse SUMMARY", topic.label.rstrip(":"))
    return block


def fetch_news_body(report_date: str) -> str | None:
    """Fetch Russian news summary as plain text for report._format_news_body."""
    if not openrouter_api_key():
        logging.warning("OPENROUTER_API_KEY not set, news unavailable")
        return None

    with ThreadPoolExecutor(max_workers=len(NEWS_TOPICS)) as executor:
        results = executor.map(
            lambda topic: _fetch_topic_block(topic, report_date),
            NEWS_TOPICS,
        )
        blocks = [block for block in results if block]

    if not blocks:
        logging.warning("OpenRouter news: all topics failed for %s", report_date)
        return None

    return "\n\n".join(blocks)
