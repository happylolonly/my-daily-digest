# Daily Digest Bot

Personal morning briefing in Telegram: weather, crypto/forex rates, and news (AI, crypto, geopolitics).

Stateless — no database, each run is independent.

## What it sends

- **Weather** — Da Nang (wttr.in)
- **Rates** — BTC, ETH (CoinGecko), VND/USD (forex API)
- **News** — 3 topics via [OpenRouter](https://openrouter.ai) (`perplexity/sonar`): Russian summary + links; search in English

Full digest HTML is assembled in code (`report.py`) — no LLM for weather/rates layout.

## Stack

- Python 3.11+
- **GitHub Actions** — cron trigger (`curl POST /cron/digest`)
- **Railway** — digest execution + Telegram bot (`bot.py`, webhook or polling)
- **OpenRouter** — news (Perplexity Sonar)
- **Langfuse** — optional tracing
- python-telegram-bot, requests, feedparser

## Quick start

```bash
cp .env.example .env   # fill TELEGRAM_* and OPENROUTER_API_KEY
pip install -r requirements.txt
python main.py         # send full digest once (local)
python bot.py          # bot (polling locally)
```

**Full setup** (secrets, GitHub, Railway, Langfuse, debug scripts): see **[SETUP.md](SETUP.md)**.

## Project layout

```
main.py              # local: full digest → Telegram
digest/scheduled.py  # deliver_scheduled_digest() — cron + main.py
bot.py               # bot entry: /digest, /news, …
digest/
  content/
    service.py       # build sections
    report.py        # Telegram HTML
    openrouter.py    # OpenRouter client
    news/            # news topics, prompt, parse, fetch
    fetchers/        # weather, crypto, forex, RSS (RSS unused in hot path)
    llm.py           # Gemini (reserved, not used in hot path)
  telegram/          # bot, webhook, delivery
scripts/
  openrouter_call.py # debug OpenRouter + Langfuse
.github/workflows/   # daily cron → Railway
```

## Modes

| Mode | Entry | Where |
|------|-------|-------|
| Scheduled digest | `POST /cron/digest` | GitHub Actions → Railway |
| Local digest | `python main.py` | dev machine |
| Bot commands | `python bot.py` | Railway or local |

Agent / contributor notes: **[AGENTS.md](AGENTS.md)**.
