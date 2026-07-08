from __future__ import annotations

from digest.content.news.parse import MAX_TOPIC_LINKS, NO_NEWS_MARKER
from digest.content.news.topics import NewsTopic


def build_topic_prompt(topic: NewsTopic, report_date: str) -> str:
    return (
        f"Date: {report_date}. Find: {topic.search_brief}\n\n"
        "Search the web in English (international sources: US, EU, global tech media). "
        "Write the answer in Russian.\n\n"
        "Return ONLY plain text, no HTML and no markdown.\n"
        "Structured response (strict, one field per line):\n"
        "SUMMARY: 1-2 sentences in Russian — the main news of the day. "
        "Plain text only: no URLs, no [1] footnotes, no LINK lines inside summary.\n"
        f"LINK: https://... | Short article headline in Russian\n"
        f"(up to {MAX_TOPIC_LINKS - 1} more LINK lines — each on its own line)\n\n"
        "Rules:\n"
        f"- Exactly 1 SUMMARY line and 1 to {MAX_TOPIC_LINKS} LINK lines\n"
        "- Links only in LINK lines, never in SUMMARY\n"
        "- URLs only from sources found in search\n"
        "- No intro phrases or text outside this format\n"
        "- If search found no relevant news for the last 24 hours, respond with "
        f"exactly one line: SUMMARY: {NO_NEWS_MARKER} (no LINK lines, no explanations)"
    )
