# AGENTS.md

## Проект

**Daily Digest Bot** — персональный утренний брифинг в Telegram.

Каждый день в **8:00 Da Nang (UTC+7)** GitHub Actions запускает скрипт, собирает данные и шлёт репорт в Telegram:

- Погода в Da Nang
- Курсы: BTC, ETH, VND/USD
- Новости за 24ч: AI, крипта, геополитика

**Стек:** Python 3.11+, GitHub Actions, Railway (webhook + Serverless), Gemini 2.5 Flash, Telegram Bot API, wttr.in, CoinGecko, RSS.

**БД нет** — каждый запуск stateless.

Подробнее: `doc.txt` (может отставать от кода).

## Структура

```
main.py                  # cron: утренний дайджест → Telegram
bot.py                   # entry point → digest.telegram.bot.run_bot()
digest/
  config.py              # logging, timezone, load_local_env
  content/               # дайджест: данные, HTML, LLM
    service.py           # сборка HTML по секции
    report.py            # plain HTML без LLM
    llm.py               # Gemini
    fetchers/            # wttr.in, CoinGecko, RSS, forex
  telegram/              # бот: команды, webhook, доставка
    bot.py               # webhook (prod) / polling (local)
    runtime.py           # run_polling / run_webhook
    webhook.py           # WebhookConfig, /health для Railway
    app.py               # build_application()
    handlers.py          # команды, авторизация по user id
    delivery.py          # отправка сообщения (cron)
requirements.txt
railway.toml             # railpack builder, startCommand, healthcheck
runtime.txt
.github/workflows/daily.yml
```

**Два режима работы**

| Режим | Entry point | Где запускать |
|-------|-------------|---------------|
| Утренний дайджест по расписанию | `python main.py` | GitHub Actions |
| Команды `/digest`, `/weather`, … | `python bot.py` | Railway (webhook) или локально (polling) |

**Режим бота:** если задан `WEBHOOK_URL` или `RAILWAY_PUBLIC_DOMAIN` + `WEBHOOK_SECRET` → webhook; иначе polling.

Логика — в `digest/content/` и `digest/telegram/`; корневые `main.py` / `bot.py` — тонкие entry points.

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

GitHub Secrets / Railway Variables / `.env` локально:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID` — куда слать cron-дайджест (`main.py`)
- `TELEGRAM_USER_ID` — кто может вызывать команды бота (fallback: `TELEGRAM_CHAT_ID`)
- `GEMINI_API_KEY`
- `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` — Langfuse Cloud (опционально, трейсинг Gemini)
- `WEBHOOK_URL` + `WEBHOOK_SECRET` — Railway prod (webhook); локально не задавать

Не коммитить секреты. Не добавлять `.env` в git.

## Workflow

- **GitHub Actions:** cron `0 1 * * *` (UTC) = 8:00 Da Nang; `workflow_dispatch` для ручного теста; `python main.py`
- **Railway:** `python bot.py` в webhook-режиме; включить **Serverless** в UI; `GET /health` на том же `PORT`

## Рефакторинг и улучшения

Агенты **проактивно замечают** возможности улучшить систему и **кратко предлагают** их — не ждут явного запроса.

**Когда предлагать**

- После выполнения задачи пользователя — блок «Возможные улучшения» в конце ответа (2–5 пунктов, если есть что сказать)
- Во время работы — если находишь явный баг, дублирование или риск (падение run, утечка секрета, сломанный fallback), упомяни сразу

**На что смотреть**

- Надёжность: отсутствующий `try/except`, нет таймаута, слабый fallback без LLM
- Консистентность: расхождение с правилами из этого файла и `doc.txt` (HTML vs markdown, forex отдельно от crypto и т.д.)
- Поддерживаемость: дублирование, «божественные» функции, мёртвый код
- Операционка: логирование ошибок в Actions, `workflow_dispatch`, понятные сообщения при деградации
- Экономия: лишние токены в промпт, слишком много RSS-статей, лишние HTTP-вызовы

**Как предлагать**

- Формат: **что** → **зачем** → **оценка усилий** (мелочь / средне / крупно)
- Не внедрять крупный рефакторинг без запроса — только предложить
- Мелкие очевидные фиксы в рамках текущей задачи можно сделать сразу, если не раздувают diff

**Границы**

- Предложения должны укладываться в философию проекта: stateless, без БД, без over-engineering
- Не предлагать стек ради стека (Redis, Celery, микросервисы) без веской причины

## Чего не делать

- БД, Redis, очереди, полноценный веб-сервер/API (кроме минимального `/health` для Railway)
- NewsAPI и платные API без явного запроса
- Over-engineering: фабрики, DI-контейнеры, абстрактные базовые классы для fetchers
- Тесты и доки сверх запроса пользователя
- Крупный рефакторинг «по ходу» без согласования с пользователем
