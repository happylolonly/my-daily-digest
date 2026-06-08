from __future__ import annotations

import logging

from digest.app import build_application
from digest.handlers import authorized_user_id
from digest.webhook import WebhookConfig, install_health_routes


def run_polling(token: str, user_id: str) -> None:
    application = build_application(token)
    logging.info("Starting bot in polling mode (authorized user_id=%s)", user_id)
    application.run_polling(drop_pending_updates=True)


def run_webhook(token: str, user_id: str, config: WebhookConfig) -> None:
    install_health_routes()
    application = build_application(token)
    logging.info(
        "Starting bot in webhook mode (authorized user_id=%s, url=%s)",
        user_id,
        config.webhook_url,
    )
    application.run_webhook(
        listen=config.listen,
        port=config.port,
        url_path=config.url_path,
        webhook_url=config.webhook_url,
        secret_token=config.secret_token,
        drop_pending_updates=True,
    )
