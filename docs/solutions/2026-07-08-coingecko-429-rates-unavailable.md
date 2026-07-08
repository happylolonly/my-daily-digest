---
title: "Курсы: «данные недоступны» — 429 от CoinGecko на Railway"
date: 2026-07-08
status: diagnosed # решение не выбрано, см. варианты ниже
tags: [rates, coingecko, rate-limit, railway, fetchers]
files:
  - digest/content/fetchers/crypto.py
---

# Курсы «данные недоступны»: CoinGecko 429 на Railway

## Симптом

В дайджесте секция «💰 Курсы» периодически показывает «данные недоступны»
(крипта; VND/USD при этом обычно на месте).

## Диагноз (подтверждён логами Railway 2026-07-08)

`fetch_crypto_prices_usd()` получает **`429 Too Many Requests`** от
`api.coingecko.com/api/v3/simple/price`. В логах Railway ошибка
`fetch_crypto_prices_usd failed` повторяется почти ежедневно
(1, 2, 5, 6, 7×2, 8 июля) — как правило, на cron-запусках дайджеста.

Причина: бесплатный публичный эндпоинт CoinGecko лимитируется **по IP**
(~5–15 req/min), а исходящий IP Railway общий для многих клиентов — лимит
выедают чужие запросы. Наш собственный трафик (2 запуска в день) ни при чём.

Forex (`open.er-api.com`) не падает — ошибок по
`fetch_forex_vnd_per_usd` в логах нет.

Как проверить снова:

```bash
railway logs --service my-daily-digest --lines 2000 --json \
  | grep -i "fetch_crypto\|429"
```

## Варианты решения (по нарастанию усилий)

1. **Ретрай с паузой 2–3 с** — дёшево, но помогает не всегда:
   лимит по чужому трафику может держаться дольше окна ретрая.
2. **Demo-ключ CoinGecko** (бесплатный) — параметр `x_cg_demo_api_key`,
   лимит становится персональным (~30 req/min, 10k/мес), а не на общий IP.
   Требует регистрации и нового секрета в Railway.
3. **Сменить источник на Binance** — `api.binance.com/api/v3/ticker/price`
   отдаёт BTC/ETH без ключа, лимиты щедрые. Меняется только `crypto.py`,
   новых секретов не нужно. **Рекомендуемый вариант.**

## Контекст

- Graceful degradation работает как задумано: падение фетча не роняет
  репорт, секция просто деградирует в «данные недоступны»
  (`report._format_rates_body`).
