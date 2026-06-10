#!/usr/bin/env python3
"""Call OpenRouter with Langfuse tracing (local dev / debug).

Examples:
  python scripts/openrouter_call.py --topic ai
  python scripts/openrouter_call.py --topic all
  python scripts/openrouter_call.py --prompt "What happened in AI today?"
  python scripts/openrouter_call.py --topic crypto --raw
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar

from langfuse import propagate_attributes

from digest.config import DA_NANG_TZ, load_local_env, setup_logging
from digest.content.news.fetch import (
    _chat_extra,
    _fetch_topic_payload,
    fetch_news_body,
    news_model,
)
from digest.content.news.parse import payload_to_topic_block
from digest.content.news.topics import TOPIC_BY_ID, NewsTopic
from digest.content.openrouter import chat_completion, openrouter_api_key
from digest.observability import flush_observability, init_observability, langfuse_enabled

T = TypeVar("T")

TOPIC_BY_KEY: dict[str, NewsTopic] = dict(TOPIC_BY_ID)


def _report_date(value: str | None) -> str:
    if value:
        return value
    return datetime.now(DA_NANG_TZ).strftime("%Y-%m-%d")


def _with_langfuse_trace(
    *,
    trace_name: str,
    metadata: dict[str, str],
    tags: list[str],
    fn: Callable[[], T],
) -> T:
    if langfuse_enabled():
        with propagate_attributes(
            trace_name=trace_name,
            metadata=metadata,
            tags=tags,
        ):
            return fn()
    return fn()


def _run_news_topic(topic_key: str, report_date: str, *, raw: bool) -> int:
    topic = TOPIC_BY_KEY[topic_key]
    label = topic.label.rstrip(":")

    def _work() -> dict[str, Any] | None:
        return _fetch_topic_payload(topic, report_date)

    payload = _with_langfuse_trace(
        trace_name="openrouter-news",
        metadata={
            "source": "openrouter-call-script",
            "report_date": report_date,
            "topic": label,
            "topic_id": topic.id,
            "group_id": topic.group_id,
            "model": news_model(),
        },
        tags=["openrouter-news", topic.group_id, label, "script"],
        fn=_work,
    )
    if payload is None:
        print("Request failed.", file=sys.stderr)
        return 1

    if raw:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    block = payload_to_topic_block(topic, payload)
    if not block:
        print("Failed to format topic block.", file=sys.stderr)
        return 1
    print(block)
    return 0


def _run_news_all(report_date: str) -> int:
    def _work() -> str | None:
        return fetch_news_body(report_date)

    body = _with_langfuse_trace(
        trace_name="openrouter-news",
        metadata={
            "source": "openrouter-call-script",
            "report_date": report_date,
            "topic": "all",
            "model": news_model(),
        },
        tags=["openrouter-news", "all", "script"],
        fn=_work,
    )
    if not body:
        print("All topics failed.", file=sys.stderr)
        return 1
    print(body)
    return 0


def _run_raw_prompt(prompt: str, model: str, *, raw: bool) -> int:
    def _work() -> dict[str, Any] | None:
        return chat_completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            extra=_chat_extra(),
            label="script",
        )

    payload = _with_langfuse_trace(
        trace_name="openrouter-cli",
        metadata={"source": "openrouter-call-script", "model": model},
        tags=["openrouter-cli", "script"],
        fn=_work,
    )
    if payload is None:
        print("Request failed.", file=sys.stderr)
        return 1

    if raw:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    content = payload["choices"][0]["message"]["content"]
    print(content)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Call OpenRouter with Langfuse tracing.")
    parser.add_argument(
        "--topic",
        choices=[*TOPIC_BY_KEY.keys(), "all"],
        help="News topic preset (uses production news prompt)",
    )
    parser.add_argument("--prompt", help="Custom user prompt (overrides --topic)")
    parser.add_argument("--model", help=f"Model id (default: {news_model()})")
    parser.add_argument("--date", help="Report date YYYY-MM-DD (default: today Da Nang)")
    parser.add_argument("--raw", action="store_true", help="Print full API JSON response")
    args = parser.parse_args()

    if not args.topic and not args.prompt:
        parser.error("Provide --topic or --prompt")

    load_local_env()
    init_observability()
    setup_logging()

    if not openrouter_api_key():
        print("OPENROUTER_API_KEY is not set.", file=sys.stderr)
        return 1

    report_date = _report_date(args.date)
    model = (args.model or news_model()).strip()

    try:
        if args.prompt:
            return _run_raw_prompt(args.prompt, model, raw=args.raw)
        if args.topic == "all":
            return _run_news_all(report_date)
        return _run_news_topic(args.topic, report_date, raw=args.raw)
    finally:
        flush_observability()


if __name__ == "__main__":
    raise SystemExit(main())
