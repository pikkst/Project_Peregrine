"""
API key authentication for the Peregrine backend.

Set the PEREGRINE_API_KEY environment variable to enable authentication.
When the variable is absent or empty, all requests are allowed (dev mode).

HTTP routes:   Authorization: Bearer <key>
WebSocket:     ws://...?token=<key>
"""

import os

from fastapi import HTTPException, Query, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)

# Loaded once at import time so the key can be rotated by restarting the server.
API_KEY: str = os.environ.get("PEREGRINE_API_KEY", "").strip()


def _dev_mode() -> bool:
    return not API_KEY


def require_api_key(
    cred: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> None:
    """FastAPI dependency for HTTP routes. Raises 401 on invalid key."""
    if _dev_mode():
        return
    if cred is None or cred.credentials != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_ws_token(token: str = Query(default="")) -> None:
    """FastAPI dependency for WebSocket endpoints (key passed as ?token=)."""
    if _dev_mode():
        return
    if token != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key",
        )
