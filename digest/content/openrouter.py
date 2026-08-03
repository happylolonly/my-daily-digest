from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import requests
from langfuse import get_client, observe

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_TIMEOUT_S = 30
OPENROUTER_RETRY_ATTEMPTS = 3
OPENROUTER_RETRY_DELAY_S = 15


@dataclass(frozen=True)
class ChatCompletionOutcome:
    """Result of an OpenRouter chat call; payload is set on success."""

    payload: dict[str, Any] | None = None
    reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.payload is not None


def openrouter_api_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


def _request_headers() -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {openrouter_api_key()}",
        "Content-Type": "application/json",
    }
    referer = os.environ.get("OPENROUTER_HTTP_REFERER", "").strip()
    title = os.environ.get("OPENROUTER_APP_TITLE", "Daily Digest Bot").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-OpenRouter-Title"] = title
    return headers


def _is_retryable_status(status_code: int) -> bool:
    return status_code in (429, 503)


def usage_cost(payload: dict[str, Any]) -> float | None:
    """Request cost in USD from an OpenRouter response, if reported."""
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None

    cost = usage.get("cost")
    if isinstance(cost, (int, float)):
        return float(cost)
    if isinstance(cost, dict) and isinstance(cost.get("total_cost"), (int, float)):
        return float(cost["total_cost"])
    return None


def _log_usage(payload: dict[str, Any], *, label: str) -> None:
    cost = usage_cost(payload)
    if cost is not None:
        logging.info("OpenRouter %s cost: $%.6f", label, cost)
        return

    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return

    logging.info(
        "OpenRouter %s tokens: prompt=%s completion=%s total=%s",
        label,
        usage.get("prompt_tokens"),
        usage.get("completion_tokens"),
        usage.get("total_tokens"),
    )


@observe(name="openrouter-chat", as_type="generation")
def chat_completion(
    *,
    model: str,
    messages: list[dict[str, str]],
    extra: dict[str, Any] | None = None,
    timeout_s: int = OPENROUTER_TIMEOUT_S,
    label: str = "chat",
) -> ChatCompletionOutcome:
    """POST /chat/completions; returns payload on success or a short failure reason."""
    if not openrouter_api_key():
        logging.warning("OPENROUTER_API_KEY not set")
        return ChatCompletionOutcome(reason="no key")

    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    if extra:
        body.update(extra)

    get_client().update_current_generation(model=model, input=messages)

    last_reason = "error"
    for attempt in range(1, OPENROUTER_RETRY_ATTEMPTS + 1):
        try:
            response = requests.post(
                OPENROUTER_API_URL,
                headers=_request_headers(),
                json=body,
                timeout=timeout_s,
            )
            if not response.ok:
                last_reason = f"HTTP {response.status_code}"
                if _is_retryable_status(response.status_code) and attempt < OPENROUTER_RETRY_ATTEMPTS:
                    logging.warning(
                        "OpenRouter %s HTTP %s, retry in %ss (%s/%s)",
                        label,
                        response.status_code,
                        OPENROUTER_RETRY_DELAY_S,
                        attempt,
                        OPENROUTER_RETRY_ATTEMPTS,
                    )
                    time.sleep(OPENROUTER_RETRY_DELAY_S)
                    continue
                logging.warning(
                    "OpenRouter %s failed: HTTP %s %s",
                    label,
                    response.status_code,
                    response.text[:200],
                )
                return ChatCompletionOutcome(reason=last_reason)

            payload = response.json()
            _log_usage(payload, label=label)

            choices = payload.get("choices") or []
            if not choices:
                logging.warning("OpenRouter %s returned no choices", label)
                return ChatCompletionOutcome(reason="empty")

            content = ((choices[0].get("message") or {}).get("content") or "").strip()
            if not content:
                logging.warning("OpenRouter %s returned empty content", label)
                return ChatCompletionOutcome(reason="empty")

            usage = payload.get("usage") or {}
            get_client().update_current_generation(
                output=content,
                usage_details={
                    "input": usage.get("prompt_tokens") or 0,
                    "output": usage.get("completion_tokens") or 0,
                    "total": usage.get("total_tokens") or 0,
                },
            )
            return ChatCompletionOutcome(payload=payload)
        except requests.Timeout:
            last_reason = "timeout"
            if attempt >= OPENROUTER_RETRY_ATTEMPTS:
                logging.exception("OpenRouter %s timed out", label)
                return ChatCompletionOutcome(reason=last_reason)
            logging.warning(
                "OpenRouter %s timeout, retry in %ss (%s/%s)",
                label,
                OPENROUTER_RETRY_DELAY_S,
                attempt,
                OPENROUTER_RETRY_ATTEMPTS,
            )
            time.sleep(OPENROUTER_RETRY_DELAY_S)
        except requests.RequestException:
            last_reason = "error"
            if attempt >= OPENROUTER_RETRY_ATTEMPTS:
                logging.exception("OpenRouter %s request failed", label)
                return ChatCompletionOutcome(reason=last_reason)
            logging.warning(
                "OpenRouter %s request error, retry in %ss (%s/%s)",
                label,
                OPENROUTER_RETRY_DELAY_S,
                attempt,
                OPENROUTER_RETRY_ATTEMPTS,
            )
            time.sleep(OPENROUTER_RETRY_DELAY_S)

    return ChatCompletionOutcome(reason=last_reason)
