"""Verifies that pytest discovery and the digest package import are wired up."""

from __future__ import annotations


def test_digest_package_imports() -> None:
    import digest  # noqa: F401


def test_pure_core_modules_import() -> None:
    # Pure core covered by the safety net must import without doing I/O.
    from digest.content import report, telegram_html  # noqa: F401
    from digest.content.news import parse, prompt  # noqa: F401
