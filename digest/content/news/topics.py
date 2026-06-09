from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NewsTopic:
    label: str
    search_brief: str


NEWS_TOPICS: tuple[NewsTopic, ...] = (
    NewsTopic(
        label="ИИ:",
        search_brief=(
            "главные новости искусственного интеллекта за последние 24 часа: "
            "релизы моделей, регуляция, крупные сделки; без гайдов, обзоров и how-to"
        ),
    ),
    NewsTopic(
        label="Крипта:",
        search_brief=(
            "главные новости криптовалют, Bitcoin и Ethereum за последние 24 часа: "
            "ETF, SEC, взломы, макро; без листингов мелких монет"
        ),
    ),
    NewsTopic(
        label="Геополитика:",
        search_brief=(
            "главные геополитические новости за последние 24 часа: "
            "войны, санкции, выборы, саммиты; без спорта и локальной криминальной хроники"
        ),
    ),
)
