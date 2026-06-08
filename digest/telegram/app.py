from __future__ import annotations

from telegram.ext import Application

from digest.telegram.handlers import post_init, register_handlers


def build_application(token: str) -> Application:
    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )
    register_handlers(application)
    return application
