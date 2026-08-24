"""Pure tests for news grouping and failure-reason picking."""

from __future__ import annotations

from digest.content.news.fetch import (
    TopicBlock,
    TopicFailure,
    _pick_reason,
    group_topic_results,
)
from digest.content.news.topics import NEWS_GROUPS, TOPIC_BY_ID


def test_pick_reason_majority_wins() -> None:
    assert _pick_reason(["timeout", "HTTP 402", "HTTP 402"]) == "HTTP 402"


def test_pick_reason_empty_is_error() -> None:
    assert _pick_reason([]) == "error"


def test_group_topic_results_includes_dead_group() -> None:
    tech = NEWS_GROUPS[0]
    world = NEWS_GROUPS[1]
    politics = NEWS_GROUPS[2]

    ai = TOPIC_BY_ID["ai"]
    economy = TOPIC_BY_ID["economy"]
    war = TOPIC_BY_ID["war_ua"]
    belarus = TOPIC_BY_ID["belarus"]

    blocks = {
        "ai": TopicBlock(topic=ai, text="ИИ:\nok"),
        "war_ua": TopicBlock(topic=war, text="Война:\nok"),
        "belarus": TopicBlock(topic=belarus, text="Беларусь:\nok"),
    }
    failures = {
        "crypto": TopicFailure(topic=TOPIC_BY_ID["crypto"], reason="timeout"),
        "economy": TopicFailure(topic=economy, reason="HTTP 402"),
        "geopolitics": TopicFailure(topic=TOPIC_BY_ID["geopolitics"], reason="HTTP 402"),
        "dubai": TopicFailure(topic=TOPIC_BY_ID["dubai"], reason="HTTP 402"),
    }

    grouped = group_topic_results(blocks, failures)
    by_id = {g.group.id: g for g in grouped}

    assert set(by_id) == {tech.id, world.id, politics.id}
    assert len(by_id[tech.id].blocks) == 1
    assert [f.topic.id for f in by_id[tech.id].failures] == ["crypto"]
    assert by_id[world.id].blocks == []
    assert len(by_id[world.id].failures) == 3
    assert by_id[politics.id].failures == []
