"""Logging setup.

Gives the `tutor.*` loggers their own stdout handler so generation timing and
retry/error logs show up regardless of how uvicorn configures the root logger.
"""
import logging
import os

_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return
    level = os.environ.get("LOG_LEVEL", "INFO").upper()

    logger = logging.getLogger("tutor")
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.propagate = False  # avoid duplicate lines via the root logger

    _configured = True
