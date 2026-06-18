"""Thin wrapper around the Anthropic SDK — the server-side equivalent of
`callClaude` in tutor_app.html.

The API key is read from settings (env) and never leaves the server. The
Anthropic client is constructed lazily so importing this module (e.g. in tests
that mock `call_claude`) never requires a key or the network.
"""
import time

from .config import settings

_client = None


def _get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic  # imported lazily

        _client = Anthropic(api_key=settings.anthropic_api_key, max_retries=0)
    return _client


def call_claude(messages, system=None, max_tokens=1400, *, timeout=None, retries=None) -> str:
    """Call the Messages API and return the concatenated text blocks.

    Mirrors the original retry semantics: retry on transient/5xx errors, bail
    immediately on 4xx (bad request/auth won't be fixed by retrying).
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
            status = getattr(e, "status_code", None)
            if status is not None and 400 <= status < 500:
                raise
            if attempt < retries:
                time.sleep(0.6)
    if last_err:
        raise last_err
    raise RuntimeError("Request failed")
