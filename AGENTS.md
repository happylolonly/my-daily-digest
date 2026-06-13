# AGENTS.md

## Проект

**Daily Digest Bot** — персональный утренний брифинг в Telegram.

GitHub Actions **2 раза в день** (8:00 и 18:00 Da Nang, UTC+7) дергает `POST /cron/digest` на Railway; сборка и отправка — на сервере:

- Погода в Da Nang
- Курсы: BTC, ETH, VND/USD
- Кнопка «📰 Получить новости» — новости (9 тем в 3 группах, отдельный LLM-запрос на тему) фетчатся только по нажатию или по `/news`

**Стек:** Python 3.11+, GitHub Actions, Railway (webhook + Serverless), OpenRouter (`perplexity/sonar`), Langfuse (опционально), Telegram Bot API, wttr.in, CoinGecko.

**БД нет** — каждый запуск stateless.

**Настройка и секреты:** см. [`SETUP.md`](SETUP.md).

## GitHub

- **Repo:** https://github.com/happylolonly/my-daily-digest

## Структура

```
main.py                  # локально: дайджест → Telegram (как cron)
digest/scheduled.py      # deliver_scheduled_digest() — cron + main.py
bot.py                   # entry point → digest.telegram.bot.run_bot()
digest/
  config.py              # logging, timezone, load_local_env
  observability.py       # Langfuse init / flush
  content/
    service.py           # build_digest_delivery() — multi-message
    report.py            # Telegram HTML (brief, группы новостей)
    openrouter.py        # OpenRouter chat/completions + retry + Langfuse
    news/
      topics.py          # 9 тем, 3 группы (tech / world / politics)
      prompt.py          # промпт SUMMARY + LINK (поиск EN, ответ RU)
      parse.py           # парсинг, citations whitelist, format block
      fetch.py           # fetch_grouped_news() — 9 параллельных запросов
    llm.py               # Gemini (не в hot path, оставлен на будущее)
    fetchers/            # wttr.in, CoinGecko, forex, news.py (RSS — не в hot path)
  telegram/              # бот: команды, webhook, доставка
scripts/
  openrouter_call.py     # dev: вызов OpenRouter + Langfuse
requirements.txt
railway.toml
.github/workflows/daily.yml
```

Это дерево — **canonical** источник по структуре проекта; `README.md` ссылается сюда, а не дублирует.

**Источники правды (не дублировать факты в прозе):**

- **Темы и группы новостей** — `digest/content/news/topics.py`
- **Команды бота** — `digest/telegram/handlers.py` (регистрация + `HELP_TEXT`)
- **Переменные окружения** — `.env.example` + `SETUP.md`

Доки описывают *поведение и связи*; конкретные списки тем/команд держим в коде, чтобы они не расходились.

**Два режима работы**

| Режим | Entry point | Где запускать |
|-------|-------------|---------------|
| Бриф по расписанию | `POST /cron/digest` | GitHub Actions → Railway |
| Команды `/brief`, `/news`, … и кнопка новостей | `python bot.py` | Railway (webhook) или локально (polling) |

**Режим бота:** если задан `WEBHOOK_URL` или `RAILWAY_PUBLIC_DOMAIN` + `WEBHOOK_SECRET` → webhook; иначе polling.

## Новости (hot path)

**9 тем, 3 группы:**

| Группа | Темы |
|--------|------|
| Технологии | ИИ, Крипта, Технологии, Робототехника |
| Мировое | Экономика, Геополитика, Дубай |
| Политика | Война (RU–UA), Беларусь |

```
fetch_grouped_news()
  → 9× OpenRouter (perplexity/sonar, parallel, 30s timeout)
  → модель: SUMMARY (RU) + LINK (url | title), до 4 ссылок
  → parse: annotations/citations whitelist, format plain block
  → group by NEWS_GROUPS → report.build_news_groups_html_list()
```

## Доставка в Telegram

Cron и `/brief` — **1 сообщение**: дата, погода, курсы, мотивация + inline-кнопка «📰 Получить новости» (без новостей, LLM не вызывается).

Кнопка и `/news` — **до 3 сообщений** (один путь, `deliver_section(NEWS)`):

1. Технологии (4 темы)
2. Мировое (3 темы)
3. Политика (2 темы)

Пустая группа (все темы упали) — сообщение не отправляется. Кнопка после нажатия остаётся — новости можно запросить повторно.

RSS (`fetchers/news.py`) и Gemini (`llm.py`) в репозитории, но **не вызываются** из `service.py`.

## Идиоматичный Python

- **Функции, не классы** — каждый источник данных = одна функция `fetch_*() -> str | None`
- **`dataclasses`** — для данных между слоями
- **`os.environ`** — конфиг из env; локально `.env` через `python-dotenv` только в dev
- **`logging`**, не `print`
- **`requests`** с явным `timeout` (fetchers: 10s; OpenRouter: 30s)
- **Type hints** на публичных функциях
- **stdlib first** — не тащить лишние зависимости (OpenRouter через `requests`, не SDK)

## Тесты

Конвенции и запуск — см. [`TESTING.md`](TESTING.md). Кратко: `pytest`, тесты в `tests/`, dev-зависимости в `requirements-dev.txt` (не в прод).

## Правила кода

1. **Graceful degradation** — каждый fetch в своём `try/except`; падение одной темы новостей не роняет остальные
2. **Telegram HTML** — только `<b>` и `<a href>` в новостях; `parse_mode=HTML`
3. **VND/USD** — отдельный forex API, не CoinGecko
4. **Новости** — plain text от модели, HTML собираем в `report.py`
5. **Citations** — whitelist URL из `citations`, `search_results`, `message.annotations` (OpenRouter)

## Секреты

См. [`SETUP.md`](SETUP.md). Кратко:

- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `OPENROUTER_API_KEY` — обязательные на Railway
- `CRON_SECRET` — GitHub Actions + Railway (`Authorization: Bearer`)
- `RAILWAY_PUBLIC_DOMAIN` — в GitHub secrets для cron workflow
- `TELEGRAM_USER_ID` — авторизация команд бота
- `LANGFUSE_*` — опционально
- `WEBHOOK_*` — Railway prod

Не коммитить секреты.

## Workflow

- **GitHub Actions:** cron 8:00 и 18:00 Da Nang; `workflow_dispatch`; `curl POST /cron/digest`
- **Railway:** `python bot.py`; Serverless; `GET /health`
- **Отладка новостей:** `python scripts/openrouter_call.py --topic ai`

## Рефакторинг и улучшения

Агенты **проактивно замечают** возможности улучшить систему и **кратко предлагают** их — не ждут явного запроса.

**На что смотреть:** надёжность, таймауты, консистентность с этим файлом, лишние LLM-вызовы, логирование cost в OpenRouter.

**Границы:** stateless, без БД, без over-engineering.

## Чего не делать

- БД, Redis, очереди
- NewsAPI без явного запроса
- Over-engineering: DI, фабрики для fetchers
- Доки сверх запроса пользователя
- Крупный рефакторинг без согласования
