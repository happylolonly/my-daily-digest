---
date: 2026-08-03
topic: news-failure-visibility
---

# News failure visibility — Requirements

## Summary

When OpenRouter (or parsing) fails, the digest must not swallow news silence. Full failure becomes one stub message; partial failure adds a short footer on each affected news group, including groups where every topic failed.

## Problem Frame

Weather and rates already show «данные недоступны» inside the brief. News groups with zero successful topics send nothing, and cron therefore looks as if news were skipped on purpose. `/news` only says «Новости недоступны.» without a reason. Balance / HTTP errors stay in logs only.

## Key Decisions

- **Short reason, not prose.** Surface `HTTP N` or a compact label (`timeout`, `empty`, `parse`, `no key`) — no «пополни баланс» copy.
- **Dead group still ships.** If every topic in a group failed but other groups have content, send that group with header + failure footer only.
- **Total failure overrides group messages.** If all topics across all groups failed, send one stub — not three empty-group messages.

## Requirements

**Total failure**

- R1. When every news topic fails, Telegram receives exactly one news-related message (cron and `/news`).
- R2. That message states news are unavailable and includes a short machine reason (e.g. `OpenRouter HTTP 402` or a non-HTTP label).

**Partial failure**

- R3. Successful topics still appear in their group messages as today.
- R4. Each group that had at least one failed topic ends with a footer listing failed topic labels and per-topic short reasons.
- R5. A group with only failures still produces a group message (header + footer), as long as this is not a total failure under R1.

**Reason labels**

- R6. HTTP failures use `HTTP <status>`; non-HTTP use one of: `timeout`, `empty`, `parse`, `no key` (and a generic `error` only if nothing else fits).

## Key Flows

- F1. Cron / local scheduled digest, all topics fail
  - **Trigger:** Scheduled deliver builds NEWS after BRIEF.
  - **Outcome:** Brief as usual; one stub news message; no group news messages.
- F2. Cron / `/news`, mixed success
  - **Trigger:** Some topics succeed, some fail.
  - **Outcome:** One message per non-empty-of-success-or-failures group; live topics + footer of failures; dead-only groups still sent (R5).
- F3. `/news`, all topics fail
  - **Trigger:** User runs `/news`.
  - **Outcome:** Same single stub as R1–R2 (replaces today's generic «Новости недоступны.» without reason).

## Acceptance Examples

- AE1. Covers R1, R2, F1 — OpenRouter returns HTTP 402 for all 9 topics → one message containing `HTTP 402`; zero group news messages.
- AE2. Covers R3–R5 — Tech: 3 ok, 1 fail `(timeout)`; World: all fail `(HTTP 402)`; Politics: all ok → three messages; Tech and World have failure footers; Politics has none.
- AE3. Covers R6, F3 — Missing API key → stub with `no key` (or equivalent), not an empty reply.

## Scope Boundaries

- No actionable «top up balance» / setup instructions in Telegram.
- No alerts outside Telegram (email, Slack, Langfuse notifications).
- No change to weather/rates unavailable wording.
- No special retry policy for 402 / billing errors.
- No per-topic error messages as separate Telegram messages.

## Dependencies / Assumptions

- Failure reason is knowable at the fetch/parse boundary today mostly as log text; planning may need a small structured failure signal so report/delivery can format footers and stubs without scraping logs.
- Topic display names in the footer are the existing human labels (e.g. «ИИ»), not internal ids.

## Outstanding Questions

**Deferred to Planning**

- Exact Russian stub/footer wording and HTML formatting (bold header vs plain line).
- How mixed reasons collapse in one footer line when many topics fail.
- Whether `error` is ever shown to users or only logged.
