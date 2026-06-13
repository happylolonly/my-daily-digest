---
title: "feat: Тестовый сетап (pytest) и страховочная сетка на чистое ядро"
type: feat
date: 2026-06-13
origin: docs/brainstorms/2026-06-13-testing-setup-requirements.md
depth: standard
---

# feat: Тестовый сетап (pytest) и страховочная сетка на чистое ядро

## Summary

Поставить лёгкую тестовую инфраструктуру на `pytest` (dev-only, не в прод) и покрыть характеризационными тестами рисковое чистое ядро текущего кода — парсинг ответов sonar, сборку Telegram HTML, форматирование новостей, построение промпта. Цель — страховочная сетка перед рефакторингом под multi-user. Новый multi-user-код (планировщик, SQLite, cost) пишется test-first **позже и вне scope этого плана**.

Подход — характеризация-first: фиксируем текущее поведение, ассерты на свойства (не точное совпадение блоков). Сетка вешается на стабильные поверхности, не на каталог тем `topics.py`, который удаляется в multi-user.

---

## Problem Frame

Тестов в проекте нет; `AGENTS.md` сейчас прямо запрещает «тесты сверх запроса». Это осознанный пересмотр (см. origin): код растёт, надвигается multi-user-сдвиг (`docs/brainstorms/2026-06-13-multi-user-digest-requirements.md`), и нужна страховочная сетка, чтобы свободно рефакторить, не ломая поведение. Самое регрессо-опасное — чистая логика парсинга/форматирования, которую и покрываем в первую очередь.

I/O-обвязку (фетчеры, HTTP к OpenRouter, доставка в Telegram) тестами не покрываем — контракт там «что вернёт API»; максимум для парсера — снэпшот-фикстуры реальных ответов.

---

## Requirements

- **R1.** `pytest` ставится как dev-зависимость, не попадает в прод-`requirements.txt` (Railway).
- **R2.** Тесты лежат в top-level `tests/`, зеркалящем `digest/`; `pytest` их авто-дискаверит, импорт `digest` работает без установки пакета.
- **R3.** Сетка покрывает чистые функции `parse.py` (citations whitelist, парсинг ссылок, нормализация URL) — приоритет №1.
- **R4.** Сетка покрывает `telegram_html.py` (экранирование, закрытие тегов, безопасные href, конверсия markdown).
- **R5.** Сетка покрывает news-форматтеры `report.py` (нумерованные пункты, «подробнее»-ссылки, группировка) и `build_topic_prompt` в `prompt.py`.
- **R6.** Снэпшоты парсера используют реальные ответы sonar как фикстуры; ассерты — на свойства, не на точное совпадение блока.
- **R7.** CI прогоняет `pytest` на push и PR, отдельным workflow, не трогая cron-`daily.yml`.
- **R8.** `AGENTS.md` обновлён: убран запрет «тесты сверх запроса», добавлена короткая секция-конвенция про тесты.

---

## Key Technical Decisions

- **Раннер — `pytest`, не `unittest` stdlib.** De-facto стандарт Python, лаконичные ассерты, авто-дискавери. `AGENTS.md` «stdlib first» относится к прод-зависимостям; для dev-only тулинга, не уезжающего в прод, исключение оправдано (фиксируется в R8).
- **Dev-зависимости — `requirements-dev.txt` с `-r requirements.txt`.** Соответствует существующей конвенции плоских `requirements*.txt`; `pyproject.toml` build-system в проекте нет, городить его ради зависимостей не нужно.
- **Импорт пакета — `pyproject.toml` с `[tool.pytest.ini_options] pythonpath = ["."]`.** Однострочник, не требует установки пакета и `src`-layout; чище, чем хак с `sys.path` в `conftest.py`. (Закрывает Outstanding Question №1 из origin.)
- **`tests/` top-level, зеркалит `digest/`** (не тесты рядом с исходниками). Тест-файлы не уезжают в импортируемый пакет на Railway; это дефолт pytest.
- **Ассерты на свойства, не точные снэпшоты.** Устойчиво к косметике LLM-вывода, ловит реальные регрессии: число ссылок ≤ 4, все URL из whitelist, нет неэкранированного HTML, формат блока соблюдён. (Решено в origin.)
- **Изоляция зависимости от `NewsTopic`.** `parse.format_topic_block` / `payload_to_topic_block` и `prompt.build_topic_prompt` требуют `NewsTopic` (frozen dataclass). Конструируем его через один тестовый хелпер/фикстуру, чтобы удаление `topics.py` в multi-user правилось в одном месте, а не по всем тестам.
- **CI ставит полный `requirements-dev.txt`** (включая telegram/langfuse/genai) ради реальных импортов — проще и честнее, чем минимальный тест-набор, расходящийся с прод-импортами.
- **Покрытие `report.py` — минимальное:** только чистые news-форматтеры; date/weather-glue (`build_brief_html` и пр.) держим вне сетки (низкий риск, завязки на `config`/`weather`).

---

## Implementation Units

### U1. Тестовая инфраструктура (pytest scaffold)

**Goal:** Поставить pytest, dev-зависимости и каталог тестов так, чтобы `pytest` собирал и импортировал `digest`.
**Requirements:** R1, R2.
**Dependencies:** —
**Files:**
- `requirements-dev.txt` (создать: `-r requirements.txt` + `pytest>=8.0.0`)
- `pyproject.toml` (создать: `[tool.pytest.ini_options]` с `pythonpath = ["."]`, `testpaths = ["tests"]`)
- `tests/__init__.py`, `tests/content/__init__.py`, `tests/content/news/__init__.py` (создать)
- `tests/test_smoke.py` (создать: тривиальный тест, что `import digest` и сбор работают)

**Approach:** Зеркальная структура `tests/` под `digest/`. `pythonpath = ["."]` даёт импорт `digest` без установки пакета. Smoke-тест существует только чтобы убедиться, что дискавери и импорт-путь настроены (его можно удалить, когда появятся реальные тесты, либо оставить как guard).
**Patterns to follow:** Существующая плоская конвенция `requirements.txt`, `.env.example` (плоские конфиги в корне).
**Test scenarios:** `Covers R2.` Smoke: `import digest` не падает; `pytest` собирает ≥1 тест из `tests/`. *(юнит инфраструктурный — содержательного поведения нет, кроме проверки самого сетапа)*
**Verification:** `pytest` запускается из корня, находит и проходит smoke-тест; `pytest` не появляется в прод-`requirements.txt`.

---

### U2. Сетка: `parse.py` + sonar-фикстуры (приоритет №1)

**Goal:** Покрыть чистые функции парсинга и citations-whitelist, включая end-to-end через реальный payload.
**Requirements:** R3, R6.
**Dependencies:** U1.
**Files:**
- `tests/content/news/test_parse.py` (создать)
- `tests/fixtures/sonar_ai.json`, `tests/fixtures/sonar_empty.json` (создать — снятые через `scripts/openrouter_call.py`, очищенные от секретов/PII; 1–2 «нормальных» + 1 пустой/упавший; закрывает Outstanding Question №2 из origin)
- хелпер конструирования `NewsTopic` (в `conftest.py` или локально в файле теста)

**Approach:** Тестируем `NewsTopic`-независимые функции напрямую; `payload_to_topic_block` — через фикстуру-payload и тестовый `NewsTopic`. Фикстуры читаются в тесте как JSON.
**Execution note:** Характеризация-first — фиксируем текущее поведение. Если тест вскрывает латентный баг, отметить в комментарии/issue, **не чинить в этом юните**.
**Patterns to follow:** Сигнатуры из `digest/content/news/parse.py`; форматы payload OpenRouter (`citations`, `search_results`, `message.annotations`).
**Test scenarios:**
- `normalize_url`: lowercase scheme+host; срезается хвостовой `/`; query сохраняется; строка без scheme/netloc возвращается как есть (trim + rstrip `/`).
- `hostname_label`: срезается `www.`; пустой netloc → исходный url.
- `clean_summary_text`: удаляются URL и маркеры `[1]`; пробелы схлопываются.
- `parse_topic_content`: парсит `SUMMARY:` + `LINK: url | title`; альтернативный сепаратор `title — url`; строка без `SUMMARY` → `None`; не-http ссылки отбрасываются; пустой/мусорный LINK пропускается.
- `extract_citation_urls`: собирает URL из `citations` (строки), `search_results[].url`, `annotations` url_citation; нормализует; не-http отбрасываются.
- `extract_search_results`: дедуп по нормализованному URL; title из `title` или fallback на hostname.
- `filter_links`: оставляет только ссылки с нормализованным URL в whitelist; пустой whitelist → passthrough.
- `fallback_links`: берёт из `search_results` в пределах whitelist до `limit`; при отсутствии — sorted(allowed) до `limit`; уважает `MAX_TOPIC_LINKS`.
- `Covers R6.` `payload_to_topic_block` на `sonar_ai.json`: summary непустой; все ссылки из whitelist; ≤ `MAX_TOPIC_LINKS`; нет голого URL в summary. На `sonar_empty.json` (нет choices / нет SUMMARY): возвращает `None`.

**Verification:** Все сценарии парсера зелёные; фикстуры в репозитории без секретов.

---

### U3. Сетка: `telegram_html.py`

**Goal:** Покрыть нормализацию и безопасную сборку Telegram HTML.
**Requirements:** R4.
**Dependencies:** U1.
**Files:** `tests/content/test_telegram_html.py` (создать)
**Approach:** Чистые функции, конструировать ничего не надо — вход строка, выход строка.
**Execution note:** Характеризация-first (см. U2).
**Patterns to follow:** `digest/content/telegram_html.py` — поддерживаемые теги `b/i/u/code`, алиасы `strong→b`/`em→i`, безопасные href только `http(s)`.
**Test scenarios:**
- `normalize_telegram_html`: ` ```html ` fence снимается; `\n`/`\t` literal → реальные; `<br>` → `\n`; markdown `[t](url)` → `<a>`, `**b**` → `<b>`, `*i*` → `<i>`.
- `ensure_html_safe`: голый текст экранируется (`&`, `<`, `>`); поддерживаемые теги сохраняются; незакрытый тег закрывается в конце; `em`/`strong` канонизируются в `i`/`b`; неподдерживаемый тег экранируется как текст.
- `ensure_html_safe` href: `javascript:`-href не превращается в ссылку (экранируется как текст); `https://`-href сохраняется, значение href экранируется по quote.
- `html_to_plain_text`: `<a href="u">t</a>` → `t (u)`; прочие теги срезаются; HTML-entity разэкранируются.

**Verification:** Все сценарии зелёные; ни один не утверждает небезопасный вывод как ожидаемый.

---

### U4. Сетка: news-форматтеры `report.py` + `prompt.py`

**Goal:** Покрыть чистое форматирование новостей и построение промпта (минимальный объём).
**Requirements:** R5.
**Dependencies:** U1.
**Files:**
- `tests/content/test_report.py` (создать)
- `tests/content/news/test_prompt.py` (создать)

**Approach:** `report.py` — только news-форматтеры (`_format_news_item_line`, `_format_news_body`, `build_group_news_html`/`build_news_groups_html_list`). Для групповых функций конструируем `NewsGroup` и `GroupNews`/blocks (dataclasses). Date/weather-glue (`build_brief_html` и пр.) — вне сетки. `prompt.build_topic_prompt` — через тестовый `NewsTopic` (тот же хелпер, что в U2).
**Execution note:** Характеризация-first (см. U2).
**Patterns to follow:** `digest/content/report.py`, `digest/content/news/prompt.py`; dataclasses `GroupNews`/`NewsGroup` из `digest/content/news/fetch.py` и `topics.py`.
**Test scenarios:**
- `_format_news_item_line`: `"1. Заголовок — https://x"` → нумерованный пункт с `(<a href>подробнее</a>)`; строка без сепаратора возвращается как есть; не-http в хвосте → без ссылки.
- `_format_news_body`: блок с заголовком на `:` оборачивает заголовок в `<b>`; preformatted-вход (`<a href=`/`<b>`) проходит через `ensure_html_safe`; `данные недоступны` при пустом входе.
- `build_news_groups_html_list`: на списке `GroupNews` отдаёт по одному HTML-сообщению на группу; заголовок группы с emoji присутствует.
- `Covers R5.` `build_topic_prompt`: содержит `report_date`, `topic.search_brief`, строки `SUMMARY:`/`LINK:`, корректный лимит ссылок из `MAX_TOPIC_LINKS`.

**Verification:** Все сценарии зелёные; date/weather-glue осознанно не покрыт.

---

### U5. CI: прогон pytest на push/PR

**Goal:** Запускать тесты автоматически, отдельным workflow.
**Requirements:** R7.
**Dependencies:** U1 (и реально полезно после U2–U4).
**Files:** `.github/workflows/tests.yml` (создать)
**Approach:** `on: [push, pull_request]`; setup Python 3.11; `pip install -r requirements-dev.txt`; `pytest`. Cron-`daily.yml` не трогаем. Полный dev-стек ставится ради реальных импортов (KTD).
**Patterns to follow:** Стиль существующего `.github/workflows/daily.yml` (минимальный, явный).
**Test scenarios:** `Test expectation: none — конфигурация CI; проверяется тем, что workflow зелёный на тестовом push/PR.`
**Verification:** Workflow появляется в Actions, прогоняет `pytest`, краснеет при падающем тесте.

---

### U6. AGENTS.md: снять запрет, добавить конвенцию

**Goal:** Привести правила проекта в соответствие с появлением тестов.
**Requirements:** R8.
**Dependencies:** —
**Files:** `AGENTS.md` (изменить)
**Approach:** Убрать пункт «Тесты и доки сверх запроса пользователя» из «Чего не делать» (доки оставить, если уместно переформулировать). Добавить короткую секцию-конвенцию: `pytest`, `tests/` зеркалит `digest/`, dev-зависимости в `requirements-dev.txt`, тестируем чистое ядро (не I/O), снэпшоты — ассерты на свойства, характеризация-first для legacy.
**Patterns to follow:** Тон и структура существующего `AGENTS.md` (короткие маркированные правила, RU).
**Test scenarios:** `Test expectation: none — документация.`
**Verification:** Раздел «Чего не делать» больше не запрещает тесты; новая секция отражает принятые решения.

---

## Scope Boundaries

**В scope:** pytest-сетап, характеризационные тесты на `parse`/`telegram_html`/`report`(news-форматтеры)/`prompt`, sonar-фикстуры, CI на push/PR, правка `AGENTS.md`.

**Вне scope (не-цели из origin):**
- DDD / доменное моделирование, классы-сущности, слои.
- Тесты на I/O-фетчеры и реальные HTTP-вызовы (кроме снэпшот-фикстур парсера).
- Тесты, завязанные на `topics.py`/`NEWS_GROUPS` как статический каталог (переезжает в конфиг).
- Строгий test-first на ретрофит; coverage-проценты как гейт.
- Покрытие date/weather-glue `report.py`.

**Deferred to Follow-Up Work (multi-user, отдельный план):**
- TDD-цели: «кому пора» (локальное время + слот), идемпотентность доставки, парсинг `USERS_CONFIG`, `usage_cost()`. Пишутся test-first, когда стартует multi-user.

---

## Risks & Dependencies

- **Удаление `topics.py` в multi-user сломает импорты тестов, конструирующих `NewsTopic`.** Митигация: единый тестовый хелпер для `NewsTopic` (U2), правка в одном месте. *(parse-функции, не зависящие от `NewsTopic`, остаются валидны.)*
- **Характеризация может зафиксировать латентный баг как «ожидаемое».** Митигация: при написании смотрим на поведение осознанно; подозрительное — флажком в issue, не ассертим вслепую (Execution note в U2–U4).
- **CI ставит тяжёлый dev-стек** (telegram/langfuse/genai) → медленнее. Принято осознанно ради реальных импортов; при необходимости урезается позже.
- **Допущение (из origin):** `parse.py` и формат вывода остаются заморожены в multi-user → сетка на парсер долговечна.

---

## System-Wide Impact

- `AGENTS.md` меняет правило поведения агентов (тесты перестают быть «сверх запроса») — влияет на будущие сессии.
- Новый CI-гейт на push/PR: красный `pytest` теперь виден до мержа.
- Прод-`requirements.txt` и Railway-деплой не затронуты (pytest только в dev).

---

## Sources & Research

- Origin: `docs/brainstorms/2026-06-13-testing-setup-requirements.md`
- Связанный план-сосед: `docs/brainstorms/2026-06-13-multi-user-digest-requirements.md` (заморозка `parse.py`, удаление `topics.py`).
- Внешний ресёрч не проводился — путь стандартный (pytest), локальные конвенции достаточны.
