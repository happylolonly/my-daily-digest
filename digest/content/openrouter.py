from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests
from langfuse import get_client, observe

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_TIMEOUT_S = 30
OPENROUTER_RETRY_ATTEMPTS = 3
OPENROUTER_RETRY_DELAY_S = 15


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


def _log_usage(payload: dict[str, Any], *, label: str) -> None:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return

    cost = usage.get("cost")
    if isinstance(cost, (int, float)):
        logging.info("OpenRouter %s cost: $%.6f", label, cost)
        return
    if isinstance(cost, dict) and cost.get("total_cost") is not None:
        logging.info(
            "OpenRouter %s cost: $%.6f",
            label,
            cost.get("total_cost", 0),
        )
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
) -> dict[str, Any] | None:
    """POST /chat/completions; returns raw JSON or None on failure."""
    if not openrouter_api_key():
        logging.warning("OPENROUTER_API_KEY not set")
        return None

    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    if extra:
        body.update(extra)

    get_client().update_current_generation(model=model, input=messages)

    for attempt in range(1, OPENROUTER_RETRY_ATTEMPTS + 1):
        try:
            response = requests.post(
                OPENROUTER_API_URL,
                headers=_request_headers(),
                json=body,
                timeout=timeout_s,
            )
            if not response.ok:
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
                return None

            payload = response.json()
            _log_usage(payload, label=label)

            choices = payload.get("choices") or []
            if not choices:
                logging.warning("OpenRouter %s returned no choices", label)
                return None

            content = ((choices[0].get("message") or {}).get("content") or "").strip()
            if not content:
                logging.warning("OpenRouter %s returned empty content", label)
                return None

            usage = payload.get("usage") or {}
            get_client().update_current_generation(
                output=content,
                usage_details={
                    "input": usage.get("prompt_tokens") or 0,
                    "output": usage.get("completion_tokens") or 0,
                    "total": usage.get("total_tokens") or 0,
                },
            )
            return payload
        except requests.RequestException:
            if attempt >= OPENROUTER_RETRY_ATTEMPTS:
                logging.exception("OpenRouter %s request failed", label)
                return None
            logging.warning(
                "OpenRouter %s request error, retry in %ss (%s/%s)",
                label,
                OPENROUTER_RETRY_DELAY_S,
                attempt,
                OPENROUTER_RETRY_ATTEMPTS,
            )
            time.sleep(OPENROUTER_RETRY_DELAY_S)

    return None
