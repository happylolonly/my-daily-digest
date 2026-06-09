# Настройка Daily Digest Bot

Пошаговая инструкция: локальный запуск, секреты, GitHub Actions, Railway, OpenRouter, Langfuse.

## 1. Переменные окружения

Скопируй шаблон и заполни значения:

```bash
cp .env.example .env
```

### Обязательные

| Переменная | Где нужна | Описание |
|------------|-----------|----------|
| `TELEGRAM_BOT_TOKEN` | везде | Токен от [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | cron (`main.py`) | Chat ID для утреннего дайджеста |
| `OPENROUTER_API_KEY` | новости | Ключ [OpenRouter](https://openrouter.ai/keys); модель по умолчанию `perplexity/sonar` |

### Для бота (Railway / локально)

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_USER_ID` | Кто может вызывать команды (`/digest`, `/news`, …). Fallback: `TELEGRAM_CHAT_ID` |
| `WEBHOOK_URL` + `WEBHOOK_SECRET` | Railway prod (webhook). Локально не задавать → polling |
| `RAILWAY_PUBLIC_DOMAIN` | Альтернатива `WEBHOOK_URL` (ставит Railway) |

### Опциональные

| Переменная | Описание |
|------------|----------|
| `OPENROUTER_NEWS_MODEL` | Модель новостей (default: `perplexity/sonar`) |
| `OPENROUTER_HTTP_REFERER` | Referer для OpenRouter (рейтинги на openrouter.ai) |
| `OPENROUTER_APP_TITLE` | Название приложения в OpenRouter (default: `Daily Digest Bot`) |
| `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` | [Langfuse Cloud](https://cloud.langfuse.com) — трейсинг OpenRouter |
| `LANGFUSE_BASE_URL` | Default: `https://cloud.langfuse.com` (без кавычек в значении) |
| `GEMINI_API_KEY` | Зарезервировано; сейчас **не используется** в hot path (`digest/content/llm.py`) |
| `RAILWAY_TOKEN` | Только локально: для `sync-secrets.sh` и Railway CLI |

Не коммить `.env` в git.

## 2. Локальный запуск

```bash
pip install -r requirements.txt
```

**Утренний дайджест (как cron):**

```bash
python main.py
```

**Telegram-бот (команды):**

```bash
python bot.py
```

Без `WEBHOOK_URL` / `WEBHOOK_SECRET` бот работает в режиме **polling**.

### Проверка новостей (OpenRouter + Langfuse)

```bash
python scripts/openrouter_call.py --topic ai      # одна тема
python scripts/openrouter_call.py --topic all     # все 3 темы
python scripts/openrouter_call.py --topic ai --raw  # сырой JSON API
```

Скрипт сам вызывает `init_observability()` и `flush_observability()` — трейс появится в Langfuse, если ключи заданы.

## 3. Синхронизация секретов

Скрипт пушит значения из `.env` в GitHub Actions и Railway:

```bash
./scripts/sync-secrets.sh --dry-run                    # посмотреть, что уйдёт
./scripts/sync-secrets.sh --only OPENROUTER_API_KEY     # один ключ
./scripts/sync-secrets.sh --github-only                # только GitHub
./scripts/sync-secrets.sh --railway-only               # только Railway
```

**Требования:**

- GitHub: `gh auth login` или `GH_TOKEN`
- Railway: `RAILWAY_TOKEN` в `.env` или `railway link`

**GitHub secrets:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `OPENROUTER_API_KEY`, `LANGFUSE_*` (опционально)

**Railway variables:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_USER_ID`, `OPENROUTER_API_KEY`, `LANGFUSE_*`, `WEBHOOK_*`

## 4. GitHub Actions (cron)

Workflow: [`.github/workflows/daily.yml`](.github/workflows/daily.yml)

- **08:00 и 18:00 Da Nang** (UTC+7) — два cron в день
- Ручной запуск: **Actions → Daily Digest → Run workflow**

Секреты репозитория (минимум):

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `OPENROUTER_API_KEY`

Опционально: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`

## 5. Railway (бот)

Конфиг: [`railway.toml`](railway.toml)

- **Start command:** `python bot.py`
- **Healthcheck:** `GET /health`
- Включить **Serverless** в UI Railway
- Задать переменные (см. sync-secrets выше)

Режим webhook: `WEBHOOK_URL` или `RAILWAY_PUBLIC_DOMAIN` + `WEBHOOK_SECRET`.

## 6. Langfuse

Если ключи пустые — трейсинг отключён (`LANGFUSE_TRACING_ENABLED=false`).

Трейсы новостей:

- `openrouter-news` — запросы по темам (ИИ / Крипта / Геополитика)
- `openrouter-chat` — низкоуровневый вызов API

Типичная ошибка: лишние кавычки в `.env`:

```bash
# плохо
LANGFUSE_BASE_URL="https://cloud.langfuse.com"

# хорошо
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

Код также срезает кавычки в `digest/observability.py`.

## 7. Dev container

VS Code / Cursor → **Reopen in Container**.

- Python 3.11, GitHub CLI, `pip install` при создании
- Создай `.env` и запускай команды внутри контейнера

## 8. Команды бота

| Команда | Описание |
|---------|----------|
| `/digest` | Полный дайджест |
| `/news` | Новости за 24ч |
| `/weather` | Погода Da Nang |
| `/rates` | BTC, ETH, VND/USD |
| `/help` | Справка |

Доступ только у `TELEGRAM_USER_ID`.

## Troubleshooting

| Проблема | Что проверить |
|----------|----------------|
| Новости «данные недоступны» | `OPENROUTER_API_KEY` в `.env` / Railway / GitHub |
| Langfuse не пишет трейсы | ключи, `LANGFUSE_BASE_URL` без кавычек, `flush` после запроса |
| Бот не отвечает | `TELEGRAM_USER_ID`, polling vs webhook, логи Railway |
| Пустой cron | secrets в GitHub, лог workflow run |

Подробнее про архитектуру новостей — [`AGENTS.md`](AGENTS.md).
