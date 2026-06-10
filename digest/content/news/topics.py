from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NewsTopic:
    id: str
    group_id: str
    label: str
    search_brief: str


@dataclass(frozen=True)
class NewsGroup:
    id: str
    title: str
    emoji: str
    topic_ids: tuple[str, ...]


NEWS_TOPICS: tuple[NewsTopic, ...] = (
    NewsTopic(
        id="ai",
        group_id="tech",
        label="ИИ:",
        search_brief=(
            "главные новости искусственного интеллекта за последние 24 часа: "
            "релизы моделей, регуляция, крупные сделки; без гайдов, обзоров и how-to"
        ),
    ),
    NewsTopic(
        id="crypto",
        group_id="tech",
        label="Крипта:",
        search_brief=(
            "главные новости криптовалют, Bitcoin и Ethereum за последние 24 часа: "
            "ETF, SEC, взломы, макро; без листингов мелких монет"
        ),
    ),
    NewsTopic(
        id="tech",
        group_id="tech",
        label="Технологии:",
        search_brief=(
            "главные мировые технологические новости за последние 24 часа: "
            "стартапы, hardware, chips, cloud, cybersecurity, regulation, крупные релизы; "
            "включая Google, Apple, Microsoft, но не только их; без гайдов и обзоров"
        ),
    ),
    NewsTopic(
        id="robotics",
        group_id="tech",
        label="Робототехника:",
        search_brief=(
            "главные новости робототехники за последние 24 часа: "
            "humanoids, industrial robots, automation, Figure, Boston Dynamics, "
            "Tesla Optimus, factory robotics"
        ),
    ),
    NewsTopic(
        id="economy",
        group_id="world",
        label="Экономика:",
        search_brief=(
            "главные макроэкономические новости за последние 24 часа: "
            "ФРС, ECB, инфляция, нефть Brent/WTI, PMI, рынки, крупные IPO; "
            "без персональных финансов и stock picks"
        ),
    ),
    NewsTopic(
        id="geopolitics",
        group_id="world",
        label="Геополитика:",
        search_brief=(
            "главные геополитические новости за последние 24 часа: "
            "войны, санкции, выборы, саммиты, Китай–Тайвань; "
            "без спорта и локальной криминальной хроники"
        ),
    ),
    NewsTopic(
        id="dubai",
        group_id="world",
        label="Дубай:",
        search_brief=(
            "главные новости UAE/Dubai за последние 24 часа: "
            "smart city, gov tech funding, AI strategy, mega-projects, "
            "startup ecosystem, DIFC; Gulf and international sources"
        ),
    ),
    NewsTopic(
        id="war_ua",
        group_id="politics",
        label="Война:",
        search_brief=(
            "главные новости войны России и Украины за последние 24 часа: "
            "фронт, удары, дипломатия, военная помощь, санкции"
        ),
    ),
    NewsTopic(
        id="belarus",
        group_id="politics",
        label="Беларусь:",
        search_brief=(
            "главные политические новости Беларуси за последние 24 часа: "
            "оппозиция, политзаключённые, Лукашенко, диаспора, санкции ЕС"
        ),
    ),
)

NEWS_GROUPS: tuple[NewsGroup, ...] = (
    NewsGroup(
        id="tech",
        title="Технологии",
        emoji="🤖",
        topic_ids=("ai", "crypto", "tech", "robotics"),
    ),
    NewsGroup(
        id="world",
        title="Мировое",
        emoji="🌍",
        topic_ids=("economy", "geopolitics", "dubai"),
    ),
    NewsGroup(
        id="politics",
        title="Политика",
        emoji="⚡",
        topic_ids=("war_ua", "belarus"),
    ),
)

TOPIC_BY_ID: dict[str, NewsTopic] = {topic.id: topic for topic in NEWS_TOPICS}

GROUP_BY_ID: dict[str, NewsGroup] = {group.id: group for group in NEWS_GROUPS}
