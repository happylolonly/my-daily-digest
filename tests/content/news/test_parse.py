"""Characterization tests for the news parser.

Assertions target behavioral properties (link counts, whitelist membership,
no raw URLs leaking into summaries), not exact block snapshots, so cosmetic
LLM-output changes don't break the suite while real regressions still do.
"""

from __future__ import annotations

import re

from digest.content.news.parse import (
    MAX_TOPIC_LINKS,
    ParsedLink,
    SearchResultEntry,
    clean_summary_text,
    extract_citation_urls,
    extract_search_results,
    fallback_links,
    filter_links,
    hostname_label,
    normalize_url,
    parse_topic_content,
    payload_to_topic_block,
)

_URL_RE = re.compile(r"https?://\S+")


# --- normalize_url -----------------------------------------------------------


def test_normalize_url_lowercases_scheme_and_host_strips_trailing_slash() -> None:
    assert normalize_url("HTTPS://Example.COM/Path/") == "https://example.com/Path"


def test_normalize_url_preserves_query() -> None:
    assert normalize_url("https://x.com/a?b=1") == "https://x.com/a?b=1"


def test_normalize_url_without_scheme_returns_trimmed_input() -> None:
    assert normalize_url("  example.com/  ") == "example.com"


# --- hostname_label ----------------------------------------------------------


def test_hostname_label_strips_www() -> None:
    assert hostname_label("https://www.Example.com/x") == "example.com"


def test_hostname_label_falls_back_to_input_when_no_host() -> None:
    assert hostname_label("notaurl") == "notaurl"


# --- clean_summary_text ------------------------------------------------------


def test_clean_summary_strips_urls_and_citation_markers() -> None:
    cleaned = clean_summary_text("Главное https://x.com сегодня [1] и ещё [12].")
    assert "http" not in cleaned
    assert "[1]" not in cleaned and "[12]" not in cleaned
    assert "  " not in cleaned  # whitespace collapsed


# --- parse_topic_content -----------------------------------------------------


def test_parse_topic_content_pipe_separator() -> None:
    result = parse_topic_content(
        "SUMMARY: Краткая сводка.\nLINK: https://x.com/a | Заголовок"
    )
    assert result is not None
    assert result.summary == "Краткая сводка."
    assert result.links == [ParsedLink(url="https://x.com/a", title="Заголовок")]


def test_parse_topic_content_dash_separator() -> None:
    result = parse_topic_content(
        "SUMMARY: Сводка.\nLINK: Заголовок — https://x.com/a"
    )
    assert result is not None
    assert result.links == [ParsedLink(url="https://x.com/a", title="Заголовок")]


def test_parse_topic_content_without_summary_returns_none() -> None:
    assert parse_topic_content("LINK: https://x.com/a | T") is None


def test_parse_topic_content_drops_non_http_links() -> None:
    result = parse_topic_content("SUMMARY: S.\nLINK: ftp://x.com/a | T")
    assert result is not None
    assert result.links == []


def test_parse_topic_content_skips_link_without_separator() -> None:
    result = parse_topic_content("SUMMARY: S.\nLINK: https://x.com/a")
    assert result is not None
    assert result.links == []


# --- extract_citation_urls ---------------------------------------------------


def test_extract_citation_urls_merges_all_sources_normalized() -> None:
    payload = {
        "citations": ["https://A.com/p/", "not-a-url"],
        "search_results": [{"url": "https://B.com/q"}, {"no_url": 1}],
        "choices": [
            {
                "message": {
                    "annotations": [
                        {
                            "type": "url_citation",
                            "url_citation": {"url": "https://C.com/r"},
                        }
                    ]
                }
            }
        ],
    }
    assert extract_citation_urls(payload) == {
        "https://a.com/p",
        "https://b.com/q",
        "https://c.com/r",
    }


# --- extract_search_results --------------------------------------------------


def test_extract_search_results_dedupes_and_falls_back_to_hostname() -> None:
    payload = {
        "search_results": [
            {"url": "https://www.x.com/a/"},
            {"url": "https://www.x.com/a"},  # duplicate after normalization
            {"url": "https://y.com/b", "title": "Y title"},
        ]
    }
    entries = extract_search_results(payload)
    urls = [e.url for e in entries]
    assert urls == ["https://www.x.com/a", "https://y.com/b"]
    assert entries[0].title == "x.com"  # hostname fallback (www stripped)
    assert entries[1].title == "Y title"


# --- filter_links ------------------------------------------------------------


def test_filter_links_keeps_only_whitelisted() -> None:
    links = [
        ParsedLink(url="https://good.com/a/", title="G"),
        ParsedLink(url="https://bad.com/b", title="B"),
    ]
    allowed = {"https://good.com/a"}
    assert filter_links(links, allowed) == [links[0]]


def test_filter_links_passthrough_when_whitelist_empty() -> None:
    links = [ParsedLink(url="https://any.com/a", title="A")]
    assert filter_links(links, set()) == links


# --- fallback_links ----------------------------------------------------------


def test_fallback_links_uses_search_results_within_whitelist() -> None:
    allowed = {"https://x.com/a", "https://y.com/b"}
    search = [
        SearchResultEntry(url="https://x.com/a", title="X"),
        SearchResultEntry(url="https://z.com/c", title="Z"),  # not allowed
    ]
    links = fallback_links(allowed, search)
    assert [l.url for l in links] == ["https://x.com/a"]


def test_fallback_links_respects_limit_from_allowed_when_no_search() -> None:
    allowed = {f"https://x.com/{i}" for i in range(10)}
    links = fallback_links(allowed, [], limit=MAX_TOPIC_LINKS)
    assert len(links) == MAX_TOPIC_LINKS


# --- payload_to_topic_block (end-to-end on fixtures) -------------------------


def test_payload_to_topic_block_keeps_only_whitelisted_links(
    make_topic, load_fixture
) -> None:
    payload = load_fixture("sonar_ai.json")
    allowed = extract_citation_urls(payload)
    block = payload_to_topic_block(make_topic(), payload)

    assert block is not None
    assert block.startswith("ИИ:")
    # Every URL that appears in the rendered block must be whitelisted.
    block_urls = {normalize_url(u) for u in _URL_RE.findall(block)}
    assert block_urls
    assert block_urls <= allowed
    # No more links than the cap.
    assert len(block_urls) <= MAX_TOPIC_LINKS


def test_payload_to_topic_block_returns_none_when_no_summary(
    make_topic, load_fixture
) -> None:
    payload = load_fixture("sonar_empty.json")
    assert payload_to_topic_block(make_topic(), payload) is None
