"""
ws/call_socket.py — WebSocket handler for live call audio processing.

Route: /ws/call/{call_id}

Per connection, three independent asyncio tasks are spawned:
  1. bispectrum_loop  — runs every ~150ms, emits pdi_update + ensemble_update
  2. tremor_loop      — runs every ~1.5s, emits tremor_update
  3. stt_loop         — runs utterance-gated, emits factcheck_update

All tasks share one AudioBufferManager via independent read cursors.
No task blocks another — each sleeps independently.

WebSocket message types sent to client:
  {type:"pdi_update", pdi_score, is_synthetic, ts}
  {type:"tremor_update", tremor_energy, has_tremor, peak_tremor_hz, ts}
  {type:"ensemble_update", ensemble_score, label, reason, ts}
  {type:"factcheck_update", status, message, evidence_urls, category, ts}
  {type:"rate_limited", retry_after_ms, ts}
  {type:"error", message, ts}
  {type:"connected", call_id, ts}
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.auth import verify_ws_token
from core.config import get_settings
from core.connection_manager import CallState, manager
from dsp.async_dsp import analyze_bispectrum, analyze_ensemble, analyze_tremor
from factcheck.claim_extraction import ClaimExtractor
from factcheck.search import SearchVerifier
from factcheck.stt import STTAccumulator, transcribe_chunk
from factcheck.verdict import generate_verdict
from i18n.language_router import detect_language, get_hinglish_system_prompt_addon
from ingestion.browser_mic import BrowserMicIngestion

logger = logging.getLogger(__name__)
router = APIRouter()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Bispectrum loop ────────────────────────────────────────────────────────────

async def _bispectrum_loop(call_id: str) -> None:
    """
    Independent asyncio task: reads bispectrum-window audio every ~150ms,
    computes PDI + ensemble score, sends updates to client.
    """
    cfg = get_settings()
    session = manager.get_session(call_id)
    if not session:
        return

    buf = session.buffer
    window_n = cfg.bispectrum_window_samples
    cadence = cfg.bispectrum_cadence_ms / 1000.0

    logger.debug("bispectrum_loop started: call_id=%r window=%d cadence=%.3fs",
                 call_id, window_n, cadence)

    while session.state not in (CallState.ENDED,):
        try:
            window = buf.get_window("bispectrum", window_n)
            if window is None:
                # Not enough audio yet — wait and retry
                await asyncio.sleep(cadence / 2)
                continue

            # Run PDI analysis (non-blocking via executor)
            pdi_result = await analyze_bispectrum(window, fs=cfg.sample_rate)
            pdi_score = pdi_result["pdi_score"]

            # Update session peak
            session.latest_pdi = pdi_score
            if pdi_score > session.peak_pdi:
                session.peak_pdi = pdi_score

            # Ensemble score (uses latest tremor too)
            ensemble = await analyze_ensemble(
                pdi_score,
                session.latest_tremor_energy,
                window,
                fs=cfg.sample_rate,
            )
            session.latest_ensemble_label = ensemble["label"]

            await manager.send_json(call_id, {
                "type": "pdi_update",
                "pdi_score": round(pdi_score, 4),
                "is_synthetic": pdi_result["is_synthetic"],
                "n_triads": pdi_result.get("n_triads_analysed", 0),
                "compute_ms": round(pdi_result.get("compute_time_ms", 0), 1),
                "ts": _ts(),
            })

            await manager.send_json(call_id, {
                "type": "ensemble_update",
                "ensemble_score": round(ensemble["ensemble_score"], 4),
                "label": ensemble["label"],
                "disagreement": round(ensemble["disagreement"], 4),
                "reason": ensemble["reason"],
                "ts": _ts(),
            })

            await asyncio.sleep(cadence)

        except asyncio.CancelledError:
            logger.debug("bispectrum_loop cancelled: call_id=%r", call_id)
            break
        except Exception as exc:
            logger.error("bispectrum_loop error [%s]: %s", call_id, exc)
            await asyncio.sleep(cadence)


# ── Tremor loop ────────────────────────────────────────────────────────────────

async def _tremor_loop(call_id: str) -> None:
    """
    Independent asyncio task: reads 1.5s audio every ~1.5s,
    computes micro-tremor score, sends update to client.

    Cadence is INDEPENDENT of bispectrum loop — both run concurrently.
    Tremor needs a longer window and slower cadence (see micro_tremor.py).
    """
    cfg = get_settings()
    session = manager.get_session(call_id)
    if not session:
        return

    buf = session.buffer
    window_n = int(cfg.tremor_window_seconds * cfg.sample_rate)
    cadence = cfg.tremor_cadence_seconds

    logger.debug("tremor_loop started: call_id=%r window=%d cadence=%.1fs",
                 call_id, window_n, cadence)

    while session.state not in (CallState.ENDED,):
        try:
            window = buf.get_window("tremor", window_n)
            if window is None:
                await asyncio.sleep(cadence / 2)
                continue

            tremor_result = await analyze_tremor(window, fs=cfg.sample_rate)
            session.latest_tremor_energy = tremor_result["tremor_energy"]
            if tremor_result["tremor_energy"] > session.peak_tremor:
                session.peak_tremor = tremor_result["tremor_energy"]

            await manager.send_json(call_id, {
                "type": "tremor_update",
                "tremor_energy": round(tremor_result["tremor_energy"], 4),
                "has_tremor": tremor_result["has_tremor"],
                "peak_tremor_hz": round(tremor_result.get("peak_tremor_hz", 0), 1),
                "compute_ms": round(tremor_result.get("compute_time_ms", 0), 1),
                "ts": _ts(),
            })

            await asyncio.sleep(cadence)

        except asyncio.CancelledError:
            logger.debug("tremor_loop cancelled: call_id=%r", call_id)
            break
        except Exception as exc:
            logger.error("tremor_loop error [%s]: %s", call_id, exc)
            await asyncio.sleep(cadence)


# ── STT + Fact-Check loop ──────────────────────────────────────────────────────

async def _stt_loop(call_id: str) -> None:
    """
    Independent asyncio task: accumulates audio into utterance chunks,
    runs Whisper STT, then feeds into claim extraction → search → verdict.

    Latency: 1.5–4s end-to-end (see §1.5). Never blocks DSP loops.
    The UI shows "verifying…" (factcheck_update with status="VERIFYING") until done.
    """
    cfg = get_settings()
    session = manager.get_session(call_id)
    if not session:
        return

    buf = session.buffer
    stt_acc = STTAccumulator(fs=cfg.sample_rate)
    claim_extractor = ClaimExtractor(debounce_chars=200)
    search_verifier = SearchVerifier()

    # Read chunk size: 0.5s at a time for the accumulator
    read_n = cfg.sample_rate // 2

    # Track language for adaptive prompting
    detected_lang_hint: Optional[str] = None
    full_transcript = ""

    logger.debug("stt_loop started: call_id=%r", call_id)

    while session.state not in (CallState.ENDED,):
        try:
            chunk = buf.get_window("stt", read_n)
            if chunk is None:
                await asyncio.sleep(0.5)
                continue

            stt_acc.add(chunk)

            if not stt_acc.ready():
                await asyncio.sleep(0.1)
                continue

            audio_chunk = stt_acc.get_chunk()
            if audio_chunk is None:
                continue

            # Language detection for adaptive prompting
            if len(full_transcript) > 50:
                lang_result = detect_language(full_transcript[-200:])
                detected_lang_hint = lang_result["stt_language_hint"]

            # Signal "verifying" to client
            await manager.send_json(call_id, {
                "type": "factcheck_update",
                "status": "VERIFYING",
                "message": "Analyzing caller claims…",
                "evidence_urls": [],
                "ts": _ts(),
            })

            # STT transcription (non-blocking, runs in executor via Groq async client)
            transcript = await transcribe_chunk(
                audio_chunk,
                fs=cfg.sample_rate,
                language=detected_lang_hint,
                call_id=call_id,
            )

            if not transcript:
                continue

            full_transcript += " " + transcript
            session.transcript_history.append(transcript)

            # Accumulate in claim extractor (debounced)
            claim_extractor.add_transcript(transcript)

            if not claim_extractor.ready():
                continue

            transcript_window = claim_extractor.get_and_reset()

            # Claim extraction + search + verdict (1.5–4s pipeline)
            claim = await claim_extractor.extract(transcript_window, call_id=call_id)
            search_result = None
            if claim:
                search_result = await search_verifier.verify_claim(claim, call_id=call_id)

            verdict = await generate_verdict(
                transcript=transcript_window,
                claim=claim,
                search_result=search_result,
                call_id=call_id,
            )

            # Store verdict history
            verdict_entry = {
                "status": verdict["status"],
                "message": verdict["message"],
                "evidence_urls": verdict["evidence_urls"],
                "category": verdict.get("category", "UNKNOWN"),
                "ts": _ts(),
            }
            session.factcheck_history.append(verdict_entry)

            # Broadcast to client
            await manager.send_json(call_id, {
                "type": "factcheck_update",
                **verdict_entry,
            })

            # Auto-trigger family SMS on CRITICAL (notifier will check state)
            if verdict["status"] == "CRITICAL":
                if cfg.family_contact_number:
                    from escalation.notifier import send_family_alert
                    asyncio.create_task(
                        send_family_alert(
                            destination_number=cfg.family_contact_number,
                            call_id=call_id,
                            verdict=verdict["status"],
                            message=verdict["message"],
                        )
                    )

        except asyncio.CancelledError:
            logger.debug("stt_loop cancelled: call_id=%r", call_id)
            break
        except Exception as exc:
            logger.error("stt_loop error [%s]: %s", call_id, exc)
            await asyncio.sleep(1.0)


# ── Main WebSocket endpoint ────────────────────────────────────────────────────

@router.websocket("/ws/call/{call_id}")
async def call_websocket(websocket: WebSocket, call_id: str) -> None:
    """
    Main WebSocket endpoint for live call audio analysis.

    Client connects with: ws://host/ws/call/{call_id}?token=<jwt>

    Accepts binary frames (PCM16LE, 20-50ms chunks).
    Sends JSON analysis updates.
    """
    # JWT validation before accepting — rejects invalid/expired tokens
    try:
        await verify_ws_token(websocket, call_id)
    except Exception:
        # verify_ws_token already called websocket.close()
        return

    await websocket.accept()

    # Get or create session
    session = manager.get_session(call_id)
    if session is None:
        logger.warning("WS connect for unknown call_id=%r — creating new session", call_id)
        session = manager.create_session(call_id)

    await manager.connect(call_id, websocket)
    ingestion = BrowserMicIngestion(call_id, session.buffer)

    # Notify client of successful connection
    await manager.send_json(call_id, {
        "type": "connected",
        "call_id": call_id,
        "ts": _ts(),
    })

    # Spawn independent analysis tasks
    bispectrum_task = asyncio.create_task(_bispectrum_loop(call_id))
    tremor_task = asyncio.create_task(_tremor_loop(call_id))
    stt_task = asyncio.create_task(_stt_loop(call_id))

    session.bispectrum_task = bispectrum_task
    session.tremor_task = tremor_task
    session.stt_task = stt_task

    try:
        async for message in websocket.iter_bytes():
            # Ingest binary audio frame
            n = ingestion.ingest_frame(message)

            # Accumulate raw bytes for forensic hash
            session.recorded_audio_bytes += message

            logger.debug("Audio frame: %d bytes → %d samples (call_id=%r)", len(message), n, call_id)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: call_id=%r", call_id)
    except Exception as exc:
        logger.error("WebSocket error [%s]: %s", call_id, exc)
        try:
            await manager.send_json(call_id, {"type": "error", "message": str(exc), "ts": _ts()})
        except Exception:
            pass
    finally:
        await manager.disconnect(call_id)
        logger.info("Call session cleanup complete: call_id=%r", call_id)
