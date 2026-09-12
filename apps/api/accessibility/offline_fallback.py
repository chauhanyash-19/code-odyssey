"""
accessibility/offline_fallback.py — Offline-first fallback mechanism.

Design:
  - Detects network or LLM API failures mid-call.
  - Automatically switches the session to a "limited" mode.
  - In limited mode, DSP math (bispectrum, tremor) continues to run entirely
    locally/offline, maintaining basic threat detection.
  - Sends a state update to the frontend so it can honestly reflect the degraded state.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def handle_network_failure(call_id: str, manager_ref: Any) -> None:
    """
    Triggered when an external API (like Groq STT/LLM) consistently times out
    or fails due to network issues.
    
    Downgrades the call session to 'limited' mode where only local DSP runs.
    """
    session = manager_ref.get_session(call_id)
    if not session:
        return

    if getattr(session, 'mode', 'full') == 'limited':
        # Already in limited mode
        return

    logger.warning("Network/LLM failure detected for call_id=%s. Switching to LIMITED offline fallback mode.", call_id)
    
    session.mode = 'limited'
    
    # Notify the client of the mode downgrade
    await manager_ref.broadcast_to_client(call_id, {
        "type": "mode_update",
        "mode": "limited",
        "ts": __import__('time').time()
    })
    
    # Optionally trigger a TTS warning (if cached or using local TTS engine)
    # that verification is degraded.
