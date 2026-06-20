"""Thin wrapper around the Anthropic SDK — the server-side equivalent of
`callClaude` in tutor_app.html.

The API key is read from settings (env) and never leaves the server. The client
is constructed lazily so importing this module (e.g. in tests that mock
`call_claude`) never requires a key or the network.

Retries use exponential backoff and only fire for transient failures —
timeouts, connection errors, rate limits (429), and 5xx. Auth / bad-request
(other 4xx) errors fail fast.
"""
import logging
import time

from .config import settings

log = logging.getLogger("tutor.anthropic")

_client = None

# Matched by class name so we don't need to import anthropic's exception types
# (keeps this importable without the SDK, and resilient across SDK versions).
_TIMEOUT_NAMES = {
    "APITimeoutError",
    "APIConnectionError",
    "ConnectError",
    "ConnectTimeout",
    "ReadTimeout",
    "Timeout",
}


def is_timeout_error(e: BaseException) -> bool:
    return type(e).__name__ in _TIMEOUT_NAMES


def is_retryable_error(e: BaseException) -> bool:
    """Retry timeouts, connection errors, rate limits (429), and 5xx. Do NOT
    retry other 4xx (auth, bad request) — they won't be fixed by waiting."""
    if is_timeout_error(e):
        return True
    status = getattr(e, "status_code", None)
    if status == 429:
        return True
    if status is not None and 400 <= status < 500:
        return False
    return True


def _get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic  # imported lazily

        _client = Anthropic(api_key=settings.anthropic_api_key, max_retries=0)
    return _client


def call_claude(messages, system=None, max_tokens=1400, *, timeout=None, retries=None, backoff=2.0) -> str:
    """Call the Messages API and return the concatenated text blocks.

    `retries` additional attempts after the first, with exponential backoff
    (`backoff * 2**attempt` seconds: 2, 4, 8, …). Transient errors are retried;
    auth/4xx fail fast.
    """
    retries = settings.anthropic_max_retries if retries is None else retries
    timeout = settings.anthropic_timeout if timeout is None else timeout

    params = {
        "model": settings.anthropic_model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        params["system"] = system

    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = _get_client().messages.create(timeout=timeout, **params)
            return "".join(
                getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text"
            )
        except Exception as e:  # noqa: BLE001 - mirror the JS catch-all
            last_err = e
            if not is_retryable_error(e):
                raise
            if attempt < retries:
                wait = backoff * (2 ** attempt)
                log.warning(
                    "Anthropic call failed (%s); retry %d/%d in %.0fs",
                    type(e).__name__, attempt + 1, retries, wait,
                )
                if wait > 0:
                    time.sleep(wait)
    if last_err:
        raise last_err
    raise RuntimeError("Request failed")
