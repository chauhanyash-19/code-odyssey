"""
security/rate_limit.py — Per-IP and per-call rate limiting for PhaseGuard.

Rationale: LLM (Groq), search (Tavily), and TTS endpoints cost real money
per call and are prime abuse targets. Rate limiting prevents:
  - Accidental runaway loops draining API budgets
  - Deliberate abuse of the fact-checker or TTS as a free LLM proxy

Uses slowapi (Starlette-compatible limiter backed by in-memory storage by
default; swap to Redis for multi-instance deployments by setting
RATE_LIMIT_STORAGE_URI=redis://...).
"""

from __future__ import annotations

import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_client_ip(request: Request) -> str:
    """
    Key function for the rate limiter.
    Respects X-Forwarded-For if behind a trusted reverse proxy.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Storage URI — use Redis in production for multi-process deployments.
# Rationale: in-memory storage is per-process and resets on restart,
# adequate for single-instance demo/hackathon deployment.
_storage_uri = os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")

limiter = Limiter(
    key_func=_get_client_ip,
    storage_uri=_storage_uri,
    default_limits=[],  # No global default; limits set per-route
)

# ── Preset limit strings (reuse across routers) ───────────────────────────────
# These are tuned for the cost profile of each backend:

# LLM endpoints: Groq has free-tier rate limits (~30 RPM on Llama-3.3-70B).
# We further cap at 20 RPM per IP to leave headroom for burst and retries.
LIMIT_LLM = "20/minute"

# Search endpoints: Tavily free tier is 1000 calls/month ≈ ~1.4/minute steady.
# We allow short bursts but enforce a per-minute cap.
LIMIT_SEARCH = "15/minute"

# TTS endpoints: typically billed per character; cap requests aggressively.
LIMIT_TTS = "10/minute"

# WebSocket upgrade: prevent connection flooding per IP.
LIMIT_WS_UPGRADE = "5/minute"

# General API endpoints (init, dossier, escalation confirm).
LIMIT_API = "30/minute"
