# AGENTS.md

## Проект

**Daily Digest Bot** — персональный утренний брифинг в Telegram.

Каждый день в **8:00 Da Nang (UTC+7)** GitHub Actions запускает скрипт, собирает данные и шлёт репорт в Telegram:

- Погода в Da Nang
- Курсы: BTC, ETH, VND/USD
- Новости за 24ч: AI, крипта, геополитика

**Стек:** Python 3.11+, GitHub Actions, Gemini 2.0 Flash, Telegram Bot API, OpenWeatherMap, CoinGecko, RSS.

**БД нет** — каждый запуск stateless.

Подробнее: `doc.txt`.

## Структура

```
main.py
requirements.txt
.github/workflows/daily.yml
```

На MVP — один `main.py`. Не дробить на пакеты, пока файл не станет реально нечитаемым.

## Идиоматичный Python

- **Функции, не классы** — каждый источник данных = одна функция `fetch_*() -> str | None`
- **`dataclasses` или `TypedDict`** — для сырых данных между fetch и LLM, не dict-суп
- **`os.environ`** — конфиг из env; локально `.env` через `python-dotenv` только в dev
- **`logging`**, не `print` — в Actions логи видны в run output
- **`requests`** с явным `timeout=10` на все HTTP-вызовы
- **`feedparser`** для RSS — не парсить XML вручную
- **Type hints** на публичных функциях
- **stdlib first** — `datetime`, `zoneinfo`, `json`; не тащить лишние зависимости

## Правила кода

1. **Graceful degradation** — каждый fetch в своём `try/except`; падение одного источника не роняет run
2. **Fallback без LLM** — если Gemini недоступен, отправить plain-text репорт из сырых данных
3. **Telegram HTML** — промпт просит HTML (`<b>`, `<i>`), не markdown; `parse_mode=HTML`
4. **VND/USD** — отдельный forex API (exchangerate-api и т.п.), не CoinGecko
5. **RSS** — фильтр по `published` за 24ч; без даты — топ 3–5 свежих записей
6. **Лимит новостей** — 3–5 статей на тему в промпт, чтобы не раздувать токены

## Секреты

GitHub Secrets (и `.env` локально):

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `OPENWEATHER_API_KEY`
- `GEMINI_API_KEY`

Не коммитить секреты. Не добавлять `.env` в git.

## Workflow

- Cron: `0 1 * * *` (UTC) = 8:00 Da Nang
- Добавить `workflow_dispatch` для ручного теста
- `pip install -r requirements.txt` → `python main.py`

## Чего не делать

- БД, Redis, очереди, веб-сервер
- NewsAPI и платные API без явного запроса
- Over-engineering: фабрики, DI-контейнеры, абстрактные базовые классы для fetchers
- Тесты и доки сверх запроса пользователя
