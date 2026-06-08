from __future__ import annotations

import dataclasses
import os

import tornado.web
from telegram.ext._utils import webhookhandler as ptb_webhook


class HealthHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ("GET", "HEAD")

    def get(self) -> None:
        self.set_status(200)
        self.set_header("Content-Type", "text/plain; charset=utf-8")
        self.write("ok")

    def head(self) -> None:
        self.set_status(200)


class WebhookAppWithHealth(ptb_webhook.WebhookAppClass):
    """PTB webhook app + /health for Railway deploy checks."""

    def __init__(
        self,
        webhook_path: str,
        bot: object,
        update_queue: object,
        secret_token: str | None = None,
    ) -> None:
        self.shared_objects = {
            "bot": bot,
            "update_queue": update_queue,
            "secret_token": secret_token,
        }
        path = webhook_path if webhook_path.startswith("/") else f"/{webhook_path}"
        handlers = [
            (r"/health/?", HealthHandler),
            (r"/?", HealthHandler),
            (rf"{path}/?", ptb_webhook.TelegramHandler, self.shared_objects),
        ]
        tornado.web.Application.__init__(self, handlers)  # type: ignore[misc]


def install_health_routes() -> None:
    """PTB's updater imports WebhookAppClass by value — patch both modules."""
    ptb_webhook.WebhookAppClass = WebhookAppWithHealth
    import telegram.ext._updater as ptb_updater

    ptb_updater.WebhookAppClass = WebhookAppWithHealth


@dataclasses.dataclass(frozen=True)
class WebhookConfig:
    listen: str
    port: int
    url_path: str
    webhook_url: str
    secret_token: str


def is_railway_runtime() -> bool:
    return bool(os.environ.get("RAILWAY_PROJECT_ID", "").strip())


def resolve_webhook_config() -> WebhookConfig | None:
    """
    Webhook on Railway (always). Polling locally when webhook env is absent.
    """
    explicit_url = os.environ.get("WEBHOOK_URL", "").strip().rstrip("/")
    railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
    on_railway = is_railway_runtime()

    if explicit_url:
        public_base = explicit_url
    elif railway_domain:
        public_base = f"https://{railway_domain}"
    elif on_railway:
        raise RuntimeError(
            "Railway requires webhook mode: generate a public domain "
            "(Networking → Generate Domain) or set WEBHOOK_URL."
        )
    else:
        return None

    secret = os.environ.get("WEBHOOK_SECRET", "").strip()
    if not secret:
        raise RuntimeError(
            "WEBHOOK_SECRET is required for webhook mode (set it in Railway Variables)."
        )

    port_str = os.environ.get("PORT", "").strip()
    if not port_str:
        raise RuntimeError("PORT is required for webhook mode (Railway sets it automatically).")

    path = os.environ.get("WEBHOOK_PATH", "telegram").strip().strip("/")
    return WebhookConfig(
        listen="0.0.0.0",
        port=int(port_str),
        url_path=path,
        webhook_url=f"{public_base}/{path}",
        secret_token=secret,
    )
