"""Shared test helpers.

The NewsTopic factory is centralized here so the multi-user migration (which
removes digest/content/news/topics.py as a static catalog) only needs to touch
one place in the test suite.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest

from digest.content.news.topics import NewsTopic

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def make_topic() -> Callable[..., NewsTopic]:
    """Return a factory for NewsTopic with sensible defaults."""

    def _make(
        *,
        id: str = "ai",
        group_id: str = "tech",
        label: str = "ИИ:",
        search_brief: str = "latest AI and LLM news",
    ) -> NewsTopic:
        return NewsTopic(
            id=id, group_id=group_id, label=label, search_brief=search_brief
        )

    return _make


@pytest.fixture
def load_fixture() -> Callable[[str], dict[str, Any]]:
    """Return a loader for JSON payload fixtures under tests/fixtures/."""

    def _load(name: str) -> dict[str, Any]:
        return json.loads((_FIXTURES_DIR / name).read_text(encoding="utf-8"))

    return _load
