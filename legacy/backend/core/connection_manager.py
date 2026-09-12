"""
core/connection_manager.py — Per-call state machine and buffer registry.

Tracks all active calls:
  - AudioBufferManager (shared audio ring buffer for all DSP consumers)
  - Active asyncio Tasks (bispectrum loop, tremor loop, STT loop)
  - Call state: IDLE → ACTIVE → SCAMBAITER_ACTIVE → ENDED
  - Connected WebSocket reference
  - Scambaiter exchange log (for dossier)
  - Escalation state (drafted/confirmed)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import WebSocket

from dsp.audio_buffer import AudioBufferManager

logger = logging.getLogger(__name__)


class CallState(str, Enum):
    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    SCAMBAITER_ACTIVE = "SCAMBAITER_ACTIVE"
    ENDED = "ENDED"


@dataclass
class EscalationRecord:
    drafted_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    destination: Optional[str] = None
    delivery_status: Optional[str] = None
    payload_summary: Optional[str] = None


@dataclass
class CallSession:
    call_id: str
    state: CallState = CallState.IDLE

    # Audio pipeline
    buffer: AudioBufferManager = field(default_factory=AudioBufferManager)
    websocket: Optional[WebSocket] = None

    # Per-call asyncio background tasks
    bispectrum_task: Optional[asyncio.Task] = None
    tremor_task: Optional[asyncio.Task] = None
    stt_task: Optional[asyncio.Task] = None

    # Latest DSP results (for dossier)
    latest_pdi: float = 0.0
    latest_tremor_energy: float = 0.0
    peak_pdi: float = 0.0
    peak_tremor: float = 0.0
    latest_ensemble_label: str = "UNCERTAIN"

    # Fact-check results
    factcheck_history: List[Dict[str, Any]] = field(default_factory=list)

    # Scambaiter exchange log
    scambaiter_log: List[Dict[str, Any]] = field(default_factory=list)

    # Forensics
    recorded_audio_bytes: bytes = b""       # accumulated raw PCM for hashing
    transcript_history: List[str] = field(default_factory=list)
    extracted_identifiers: Optional[Dict[str, Any]] = None

    # Escalation chain-of-custody
    escalation_records: List[EscalationRecord] = field(default_factory=list)
    escalation_drafted: bool = False
    escalation_confirmed: bool = False

    # Ingestion source info
    ingestion_mode: str = "browser_mic"


class ConnectionManager:
    """
    Registry for all active call sessions.  Thread-safe via asyncio (single-
    threaded event loop) — do NOT access from worker threads directly.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, CallSession] = {}

    # ── Session lifecycle ──────────────────────────────────────────────────────

    def create_session(self, call_id: str, ingestion_mode: str = "browser_mic") -> CallSession:
        """Create and register a new CallSession."""
        if call_id in self._sessions:
            logger.warning("Session %r already exists — returning existing", call_id)
            return self._sessions[call_id]

        session = CallSession(call_id=call_id, ingestion_mode=ingestion_mode)
        # Register DSP consumers on the buffer
        session.buffer.register_cursor("bispectrum")
        session.buffer.register_cursor("tremor")
        session.buffer.register_cursor("stt")

        self._sessions[call_id] = session
        logger.info("Session created: call_id=%r mode=%r", call_id, ingestion_mode)
        return session

    def get_session(self, call_id: str) -> Optional[CallSession]:
        return self._sessions.get(call_id)

    def require_session(self, call_id: str) -> CallSession:
        session = self._sessions.get(call_id)
        if session is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"Call session {call_id!r} not found")
        return session

    async def connect(self, call_id: str, websocket: WebSocket) -> CallSession:
        """Associate a WebSocket with an existing session and mark it ACTIVE."""
        session = self.require_session(call_id)
        session.websocket = websocket
        session.state = CallState.ACTIVE
        logger.info("WS connected: call_id=%r", call_id)
        return session

    async def disconnect(self, call_id: str) -> None:
        """Cancel all background tasks and mark session ENDED."""
        session = self._sessions.get(call_id)
        if session is None:
            return

        session.state = CallState.ENDED

        for task_attr in ("bispectrum_task", "tremor_task", "stt_task"):
            task: Optional[asyncio.Task] = getattr(session, task_attr)
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

        logger.info("Session ended: call_id=%r", call_id)

    def remove_session(self, call_id: str) -> None:
        """Remove a session from the registry (call after disconnect + cleanup)."""
        self._sessions.pop(call_id, None)

    # ── State transitions ──────────────────────────────────────────────────────

    def activate_scambaiter(self, call_id: str) -> None:
        """
        Transition a call into SCAMBAITER_ACTIVE state.
        Guard: only allowed when state == ACTIVE.
        """
        session = self.require_session(call_id)
        if session.state != CallState.ACTIVE:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=409,
                detail=f"Cannot activate scambaiter: call is in state {session.state.value}",
            )
        session.state = CallState.SCAMBAITER_ACTIVE
        logger.info("Scambaiter activated: call_id=%r", call_id)

    # ── Broadcast helpers ─────────────────────────────────────────────────────

    async def send_json(self, call_id: str, payload: dict) -> None:
        """Send a JSON message to the call's WebSocket (if still connected)."""
        session = self._sessions.get(call_id)
        if session and session.websocket and session.state not in (CallState.ENDED,):
            try:
                await session.websocket.send_json(payload)
            except Exception as exc:
                logger.warning("send_json failed for call_id=%r: %s", call_id, exc)

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def active_calls(self) -> List[str]:
        return [k for k, v in self._sessions.items() if v.state != CallState.ENDED]


# Module-level singleton
manager = ConnectionManager()
