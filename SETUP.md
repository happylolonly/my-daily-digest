# Daily Digest Bot Setup

Step-by-step guide: local run, secrets, GitHub Actions, Railway, OpenRouter, Langfuse.

## 1. Environment variables

Copy the template and fill in values:

```bash
cp .env.example .env
```

### Required

| Variable | Where | Description |
|----------|-------|-------------|
| `TELEGRAM_BOT_TOKEN` | everywhere | Token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Railway / `main.py` | Chat ID for scheduled digest delivery |
| `OPENROUTER_API_KEY` | news | [OpenRouter](https://openrouter.ai/keys) key; default model `perplexity/sonar` |

### Bot (Railway / local)

| Variable | Description |
|----------|-------------|
| `TELEGRAM_USER_ID` | Who can run commands (`/brief`, `/news`, …). Fallback: `TELEGRAM_CHAT_ID` |
| `WEBHOOK_URL` + `WEBHOOK_SECRET` | Railway prod (webhook). Leave unset locally → polling |
| `RAILWAY_PUBLIC_DOMAIN` | Alternative to `WEBHOOK_URL` (set automatically on Railway) |

### Optional

| Variable | Description |
|----------|-------------|
| `OPENROUTER_NEWS_MODEL` | News model (default: `perplexity/sonar`) |
| `OPENROUTER_HTTP_REFERER` | Referer for OpenRouter (rankings on openrouter.ai) |
| `OPENROUTER_APP_TITLE` | App title in OpenRouter (default: `Daily Digest Bot`) |
| `LOG_LEVEL` | Logging level (default: `INFO`) |
| `WEBHOOK_PATH` | Telegram webhook path (default: `telegram`) |
| `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` | [Langfuse Cloud](https://cloud.langfuse.com) — OpenRouter tracing |
| `LANGFUSE_BASE_URL` | Default: `https://cloud.langfuse.com` (no quotes in value) |
| `GEMINI_API_KEY` | Reserved; **not used** in hot path (`digest/content/llm.py`) |
| `RAILWAY_TOKEN` | Dev container only: `.env.railway` — Railway CLI (`railway link`, `railway variable set`) |
| `CRON_SECRET` | Shared secret for `POST /cron/digest` (GitHub Actions + Railway) |

Do not commit `.env` to git.

## 2. Local run

```bash
pip install -r requirements.txt
```

**Scheduled digest (same as cron):**

```bash
python main.py
```

**Telegram bot (commands):**

```bash
python bot.py
```

Without `WEBHOOK_URL` / `WEBHOOK_SECRET`, the bot runs in **polling** mode.

### News debug (OpenRouter + Langfuse)

```bash
python scripts/openrouter_call.py --topic ai      # one topic
python scripts/openrouter_call.py --topic all     # all topics (9)
python scripts/openrouter_call.py --topic ai --raw  # raw API JSON
```

The script calls `init_observability()` and `flush_observability()` — traces appear in Langfuse when keys are set.

## 3. Secrets (CLI)

**GitHub** (cron only, 2 secrets):

```bash
cp .env.production.example .env.production   # fill CRON_SECRET, RAILWAY_PUBLIC_DOMAIN
gh secret set CRON_SECRET < .env.production
gh secret set RAILWAY_PUBLIC_DOMAIN --body "my-app.up.railway.app"
```

**Railway** (bot + digest):

```bash
railway variable set TELEGRAM_BOT_TOKEN=... OPENROUTER_API_KEY=... CRON_SECRET=...
```

Full Railway variable list: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_USER_ID`, `OPENROUTER_API_KEY`, `LANGFUSE_*`, `WEBHOOK_*`, `CRON_SECRET`

## 4. GitHub Actions (cron)

Workflow: [`.github/workflows/daily.yml`](.github/workflows/daily.yml)

- **08:00 and 18:00 Da Nang** (UTC+7) — two runs per day
- Manual run: **Actions → Daily Digest → Run workflow**

Repository secrets:

- `CRON_SECRET` — same random string as on Railway
- `RAILWAY_PUBLIC_DOMAIN` — e.g. `my-app.up.railway.app` (no `https://`)

The workflow only wakes Railway and waits for a response (up to 180 s). All API keys stay on Railway.

## 5. Railway (bot)

Config: [`railway.toml`](railway.toml)

- **Start command:** `python bot.py`
- **Healthcheck:** `GET /health`
- Enable **Serverless** in the Railway UI
- Set variables (see §3)

Webhook mode: `WEBHOOK_URL` or `RAILWAY_PUBLIC_DOMAIN` + `WEBHOOK_SECRET`.

Cron endpoint: `POST /cron/digest` with `Authorization: Bearer <CRON_SECRET>`.

## 6. Langfuse

If keys are empty, tracing is disabled (`LANGFUSE_TRACING_ENABLED=false`).

News traces:

- `openrouter-news` — per-topic requests (9 topics in 3 groups)
- `openrouter-chat` — low-level API call

Common mistake: extra quotes in `.env`:

```bash
# bad
LANGFUSE_BASE_URL="https://cloud.langfuse.com"

# good
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

The code also strips quotes in `digest/observability.py`.

## 7. Dev container

VS Code / Cursor → **Reopen in Container**.

- Python 3.11, GitHub CLI, Railway CLI, `pip install` on create
- App secrets: `.env` (read by `load_local_env()` from the mounted workspace)
- Railway CLI: `cp .env.railway.example .env.railway` — only `RAILWAY_TOKEN` is injected into the container

## 8. Bot commands

| Command | Description |
|---------|-------------|
| `/brief` | Date, weather, rates, motivation |
| `/news` | News (last 24h), 3 messages by group |
| `/weather` | Da Nang weather |
| `/rates` | BTC, ETH, VND/USD |
| `/help` | Help |

Access restricted to `TELEGRAM_USER_ID`.

## Troubleshooting

| Issue | What to check |
|-------|---------------|
| News shows "data unavailable" | `OPENROUTER_API_KEY` in `.env` / Railway |
| Langfuse not recording traces | keys, `LANGFUSE_BASE_URL` without quotes, `flush` after request |
| Bot not responding | `TELEGRAM_USER_ID`, polling vs webhook, Railway logs |
| Empty cron | `CRON_SECRET`, `RAILWAY_PUBLIC_DOMAIN` in GitHub; `TELEGRAM_CHAT_ID`, `CRON_SECRET` on Railway; workflow / Railway logs |

For news architecture details, see [`AGENTS.md`](AGENTS.md).
