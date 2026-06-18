"""Shared-secret auth.

Every /api endpoint (except /health) requires the `X-API-Key` header to match
`API_SHARED_SECRET`. Simple by design — one family. Note: a secret embedded in
a public SPA is visible to anyone who loads the page, so this deters casual
access, not a determined visitor; a password->cookie login is the next step if
stronger privacy is wanted.
"""
from fastapi import Header, HTTPException

from .config import settings


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> bool:
    if not settings.api_shared_secret or x_api_key != settings.api_shared_secret:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True
