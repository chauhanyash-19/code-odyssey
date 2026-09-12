"""
core/auth.py — Short-lived JWT call tokens for PhaseGuard.

Security rationale:
  - call_id alone is NOT authentication — it is guessable/enumerable.
  - Every WebSocket upgrade and REST endpoint requires a signed token issued
    only after the initiating client presents a valid call_id + (optionally)
    a user credential.
  - Tokens are HS256, short-lived (default 15 min), and tied to a specific
    call_id claim so a stolen token for call A cannot be used to hijack call B.
  - In production: set JWT_SECRET to a 256-bit random value managed by your
    secret manager, never committed to source.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from core.config import get_settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


# ── Token issuance ─────────────────────────────────────────────────────────────

def create_call_token(call_id: str) -> str:
    """
    Issue a short-lived JWT scoped to a specific call_id.

    Claims:
      sub  — call_id
      iat  — issued-at
      exp  — expires-at (now + JWT_TTL_MINUTES)
    """
    cfg = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": call_id,
        "iat": now,
        "exp": now + timedelta(minutes=cfg.jwt_ttl_minutes),
    }
    return jwt.encode(payload, cfg.jwt_secret, algorithm=cfg.jwt_algorithm)


# ── Token validation ───────────────────────────────────────────────────────────

def decode_call_token(token: str) -> dict[str, Any]:
    """
    Validate a call token and return its payload.
    Raises HTTPException 401 on any failure.
    """
    cfg = get_settings()
    try:
        payload = jwt.decode(token, cfg.jwt_secret, algorithms=[cfg.jwt_algorithm])
        return payload
    except JWTError as exc:
        logger.warning("JWT decode failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired call token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_call_token_for_call(token: str, call_id: str) -> None:
    """
    Validate token AND assert it was issued for the given call_id.
    Raises HTTPException 403 if the token is valid but scoped to a different call.
    """
    payload = decode_call_token(token)
    if payload.get("sub") != call_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token is not scoped to this call_id",
        )


# ── FastAPI dependency: REST bearer token ──────────────────────────────────────

async def require_call_token(
    credentials: HTTPAuthorizationCredentials | None = None,
) -> dict[str, Any]:
    """
    FastAPI dependency that extracts and validates a Bearer token from the
    Authorization header.  Usage::

        @router.get("/call/{call_id}/dossier")
        async def get_dossier(call_id: str, token_payload=Depends(require_call_token)):
            ...
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_call_token(credentials.credentials)


# ── WebSocket upgrade token guard ──────────────────────────────────────────────

async def verify_ws_token(websocket: WebSocket, call_id: str) -> dict[str, Any]:
    """
    Extract and validate a JWT from the WS upgrade query param (?token=...).
    Call this at the top of every WebSocket endpoint before accepting the
    connection — if it raises, FastAPI will close the WS with 4001.

    Also enforces WSS in non-development environments (plaintext WS is
    acceptable only during local dev).
    """
    cfg = get_settings()

    # Enforce WSS in non-dev — rationale: call audio is legally sensitive once
    # used to generate FIR dossiers; plaintext transmission is unacceptable.
    if cfg.environment != "development" and websocket.url.scheme == "ws":
        await websocket.close(code=4003)
        raise HTTPException(
            status_code=status.HTTP_426_UPGRADE_REQUIRED,
            detail="Plaintext WebSocket (ws://) is not allowed outside development. Use wss://",
        )

    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing ?token= query parameter on WS upgrade",
        )

    payload = decode_call_token(token)
    if payload.get("sub") != call_id:
        await websocket.close(code=4003)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token not scoped to this call_id",
        )

    return payload
