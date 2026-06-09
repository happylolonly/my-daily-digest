from __future__ import annotations

import os

from digest.config import load_local_env, setup_logging
from digest.observability import init_observability
from digest.telegram.handlers import authorized_user_id
from digest.telegram.runtime import run_polling, run_webhook
from digest.telegram.webhook import resolve_webhook_config


def run_bot() -> None:
    load_local_env()
    init_observability()
    setup_logging()

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    user_id = authorized_user_id()
    if not token or not user_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_USER_ID (or TELEGRAM_CHAT_ID) are required."
        )

    webhook_config = resolve_webhook_config()
    if webhook_config:
        run_webhook(token, user_id, webhook_config)
    else:
        run_polling(token, user_id)
