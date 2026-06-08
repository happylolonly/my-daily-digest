# Daily Digest Bot

A personal daily report delivered to Telegram on a schedule.

Each run collects fresh data, formats it with AI, and sends a single HTML message:

- Weather
- BTC / ETH prices and VND/USD
- News from the last 24 hours (AI, crypto, geopolitics)

Stateless by design — no database, one independent run per day.

## Stack

- **Python 3.11+**
- **GitHub Actions** — scheduling and hosting
- **AI (LLM)** — report formatting (`google-generativeai`)
- **python-telegram-bot** — Telegram delivery
- **requests** + **feedparser** — weather, crypto, forex, RSS feeds

## Project layout

```
main.py                 # entry point
digest/                 # fetchers, report builder, LLM, Telegram
.github/workflows/      # daily cron + manual trigger
```

## Run locally

1. Copy env template and fill in secrets:

```bash
cp .env.example .env
```

Required variables:

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Target chat ID |
| `GEMINI_API_KEY` | AI provider API key |

2. Install dependencies and run:

```bash
pip install -r requirements.txt
python main.py
```

If the AI provider is unavailable, the bot falls back to a plain HTML report built from raw data.

## Dev container

Open the repo in VS Code / Cursor and choose **Reopen in Container**.

The devcontainer (`.devcontainer/devcontainer.json`) provides:

- Python 3.11 image
- GitHub CLI
- Python extensions (Pylance, debugpy, Black)
- Auto `pip install` on create via `postCreateCommand`

Then create `.env` and run `python main.py` inside the container.

## GitHub Actions

Add repository secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `GEMINI_API_KEY`

The workflow runs on schedule or manually via **Actions → Daily Digest → Run workflow**.
