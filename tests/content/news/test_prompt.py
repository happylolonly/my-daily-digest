"""Characterization tests for topic prompt assembly."""

from __future__ import annotations

from digest.content.news.parse import MAX_TOPIC_LINKS
from digest.content.news.prompt import build_topic_prompt


def test_build_topic_prompt_includes_date_and_search_brief(make_topic) -> None:
    topic = make_topic(search_brief="latest robotics news")
    prompt = build_topic_prompt(topic, "2026-06-13")

    assert "2026-06-13" in prompt
    assert "latest robotics news" in prompt


def test_build_topic_prompt_carries_output_scaffold(make_topic) -> None:
    prompt = build_topic_prompt(make_topic(), "2026-06-13")

    assert "SUMMARY:" in prompt
    assert "LINK:" in prompt
    # The link cap from parse.py must flow into the prompt instructions.
    assert str(MAX_TOPIC_LINKS) in prompt
