"""Pure tests for which digest sections a scheduled run sends."""

from __future__ import annotations

from digest.content.service import DigestSection
from digest.scheduled import scheduled_sections


def test_scheduled_sections_include_news_by_default() -> None:
    assert scheduled_sections() == (DigestSection.BRIEF, DigestSection.NEWS)


def test_scheduled_sections_evening_is_brief_only() -> None:
    assert scheduled_sections(include_news=False) == (DigestSection.BRIEF,)
