from __future__ import annotations

import os

from digest.config import load_local_env, setup_logging
from digest.content.service import DigestSection, build_digest_html
from digest.observability import flush_observability, init_observability
from digest.telegram.delivery import send_telegram_message


def main() -> None:
    load_local_env()
    init_observability()
    setup_logging()

    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not telegram_bot_token or not telegram_chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required.")

    gemini_enabled = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    final_html = build_digest_html(DigestSection.FULL, use_gemini=gemini_enabled)

    send_telegram_message(
        chat_id=telegram_chat_id,
        bot_token=telegram_bot_token,
        html_text=final_html,
    )
    flush_observability()


if __name__ == "__main__":
    main()
