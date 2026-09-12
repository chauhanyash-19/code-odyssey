"""
ws/call_socket.py — WebSocket handler for live call audio processing.

Route: /ws/call/{call_id}

Per connection, up to four independent asyncio tasks are spawned:
  1. bispectrum_loop      — EXPERIMENTAL, only when DSP_VOICE_DETECTION_ENABLED=true.
                            Runs every ~150ms, emits pdi_update + ensemble_update.
  2. tremor_loop          — EXPERIMENTAL, only when DSP_VOICE_DETECTION_ENABLED=true.
                            Runs every ~1.5s, emits tremor_update.
  3. stt_loop             — PRIMARY feature. Always runs. Emits factcheck_update
                            (Whisper STT → Llama claim extraction → search → verdict).
  4. evidence_capture_loop— Always runs. Polls every 200ms. While the latest verdict
                            is CRITICAL, drains video_frames_buffer → video_frames
                            (permanent record). Decoupled from STT cadence so frames
                            arriving mid-pipeline are never dropped.

All tasks share one AudioBufferManager via independent read cursors.
No task blocks another — each sleeps independently.

WebSocket message types sent to client:
  {type:"connected",         call_id, dsp_enabled, ts}
  {type:"pdi_update",        pdi_score, is_synthetic, ts}          — DSP only
  {type:"tremor_update",     tremor_energy, has_tremor, ts}        — DSP only
  {type:"ensemble_update",   ensemble_score, label, reason, ts}    — DSP only
  {type:"factcheck_update",  status, message, evidence_urls, ts}   — always
  {type:"video_frame_captured", sha256_hash, face_detected, timestamp, ts} — CRITICAL only
  {type:"rate_limited",      retry_after_ms, ts}
  {type:"error",             message, ts}
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional
import httpx

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
from intel.voip_pattern_detector import detect_voip_pattern
from intel.number_reputation import get_reputation, report_number

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
                 
    uncertain_streak = 0

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

            if ensemble["label"] == "UNCERTAIN":
                uncertain_streak += 1
                if uncertain_streak == 3:
                    await manager.send_json(call_id, {
                        "type": "factcheck_update",
                        "status": "WARNING",
                        "message": "⚠️ Audio authenticity uncertain (potential voice cloning or heavy noise). Do not share sensitive information while we fact-check the conversation.",
                        "evidence_urls": [],
                        "ts": _ts(),
                    })
            else:
                uncertain_streak = 0

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


# ── HuggingFace ML loop ────────────────────────────────────────────────────────

async def _hf_ml_loop(call_id: str) -> None:
    """
    Independent asyncio task: reads audio window every ~3.0s,
    sends to HuggingFace Inference API for deepfake/spoof detection.
    """
    cfg = get_settings()
    session = manager.get_session(call_id)
    if not session or not cfg.hf_api_token:
        return

    buf = session.buffer
    # Use a 3s window for better ML context
    window_n = int(3.0 * cfg.sample_rate)
    cadence = 3.0

    from dsp.hf_ml import analyze_audio_hf

    logger.debug("hf_ml_loop started: call_id=%r window=%d cadence=%.1fs",
                 call_id, window_n, cadence)

    while session.state not in (CallState.ENDED,):
        try:
            window = buf.get_window("hf_ml", window_n)
            if window is None:
                await asyncio.sleep(cadence / 2)
                continue

            result = await analyze_audio_hf(window, fs=cfg.sample_rate)
            
            if result.get("status") == "success":
                await manager.send_json(call_id, {
                    "type": "hf_ml_update",
                    "is_synthetic": result.get("is_synthetic"),
                    "top_label": result.get("top_label"),
                    "score": round(result.get("score", 0), 4),
                    "compute_ms": round(result.get("compute_ms", 0), 1),
                    "ts": _ts(),
                })
            
            await asyncio.sleep(cadence)

        except asyncio.CancelledError:
            logger.debug("hf_ml_loop cancelled: call_id=%r", call_id)
            break
        except Exception as exc:
            logger.error("hf_ml_loop error [%s]: %s", call_id, exc)
            await asyncio.sleep(cadence)


# ── Continuous Video Evidence Capture loop ─────────────────────────────────────

async def _evidence_capture_loop(call_id: str) -> None:
    """
    Independent asyncio task: polls every 200ms and, whenever the latest
    factcheck verdict is CRITICAL, drains video_frames_buffer into the
    permanent video_frames list.

    Design rationale
    ─────────────────
    Previously this logic lived inside _stt_loop, which runs at STT cadence
    (0.5 s/chunk + 1.5–4 s for the full claim → search → verdict pipeline).
    That created a race: if a screen-share frame arrived *while* the pipeline
    was mid-flight, the capture check would not run for several seconds —
    exactly the timing gap that caused Test 3 failures in live demos.

    By moving capture into its own 200 ms tight loop we guarantee:
      • Frames that land in video_frames_buffer are committed to permanent
        storage within at most 200 ms after the verdict turns CRITICAL.
      • The rolling buffer in video_frames_buffer (last N frames, populated
        by the /frame HTTP endpoint) is drained continuously, not just at
        STT boundaries.
      • Timing mismatches — e.g., "scam" uttered, then screen-share starts
        200 ms–3 s later — are robustly handled regardless of where the STT
        pipeline is in its cycle.

    cadence : 200ms  (5 Hz)  — fast enough to cover any realistic frame rate
              from the client, slow enough to have negligible CPU cost.
    """
    CADENCE = 0.20  # seconds between polls

    session = manager.get_session(call_id)
    if not session:
        return

    logger.debug("evidence_capture_loop started: call_id=%r cadence=%.2fs", call_id, CADENCE)

    while session.state not in (CallState.ENDED,):
        try:
            # Only commit frames while the active verdict is CRITICAL.
            # We intentionally check the *full* factcheck_history so that a
            # SAFE verdict after a CRITICAL one stops further capture — but
            # while CRITICAL persists, every incoming buffer frame is saved.
            if (
                session.factcheck_history
                and session.factcheck_history[-1]["status"] == "CRITICAL"
                and session.video_frames_buffer
            ):
                # Snapshot and drain the rolling buffer atomically.
                # video_frames_buffer keeps receiving new frames from the
                # /frame endpoint (rolling, capped at 3–5); we drain them all
                # into the permanent record on each tick.
                frames_to_commit = session.video_frames_buffer.copy()
                session.video_frames_buffer.clear()
                session.video_frames.extend(frames_to_commit)

                for frame in frames_to_commit:
                    logger.info(
                        "[evidence_capture] Committed frame to permanent record: "
                        "call_id=%r hash=%s face=%s total_permanent=%d",
                        call_id,
                        frame["sha256_hash"][:12],
                        frame["face_detected"],
                        len(session.video_frames),
                    )
                    await manager.send_json(call_id, {
                        "type": "video_frame_captured",
                        "sha256_hash": frame["sha256_hash"],
                        "face_detected": frame["face_detected"],
                        "timestamp": frame["timestamp"],
                        "total_permanent_frames": len(session.video_frames),
                        "ts": _ts(),
                    })

            await asyncio.sleep(CADENCE)

        except asyncio.CancelledError:
            logger.debug("evidence_capture_loop cancelled: call_id=%r", call_id)
            break
        except Exception as exc:
            logger.error("evidence_capture_loop error [%s]: %s", call_id, exc)
            await asyncio.sleep(CADENCE)


# ── Scambaiter Turn Execution ──────────────────────────────────────────────────

async def _fire_scambaiter_turn(call_id: str, caller_speech: str) -> None:
    """
    Generate and synthesize a scambaiter response, then stream binary audio 
    directly back over the WebSocket.
    """
    session = manager.get_session(call_id)
    if not session or not caller_speech.strip():
        return
        
    from scambaiter.persona import generate_scambaiter_response
    from scambaiter.tts import synthesize_speech
    
    logger.info("Scambaiter Turn Started for call_id=%r with input: %r", call_id, caller_speech)
    
    # 1. Generate text response
    response_text = await generate_scambaiter_response(
        caller_speech=caller_speech,
        exchange_history=session.scambaiter_log,
        call_id=call_id
    )
    if not response_text:
        return
        
    # Append to history
    session.scambaiter_log.append({"role": "user", "content": caller_speech})
    session.scambaiter_log.append({"role": "assistant", "content": response_text})

    # Broadcast the text exchange to frontend BEFORE audio so UI is ready
    try:
        await manager.send_json(call_id, {
            "type": "scambaiter_turn",
            "caller_text": caller_speech,
            "ai_text": response_text,
            "ts": _ts(),
        })
    except Exception as exc:
        logger.warning("Failed to send scambaiter_turn JSON: %s", exc)

    # 2. Synthesize audio
    audio_bytes = await synthesize_speech(response_text, call_id=call_id)
    if not audio_bytes:
        return
        
    # 3. Send binary audio to frontend
    if session.websocket and session.state not in (CallState.ENDED,):
        try:
            await session.websocket.send_bytes(audio_bytes)
            # Add verifiable logging as requested by user
            logger.info("[Scambaiter] Generated reply: %r | Audio bytes: %d | Sent over WS", response_text, len(audio_bytes))
        except Exception as exc:
            logger.error("Scambaiter failed to send audio: %s", exc)


async def _scambaiter_loop(call_id: str) -> None:
    """
    Independent asyncio task: waits for transcribed caller speech,
    then executes the Scambaiter persona loop sequentially.
    """
    session = manager.get_session(call_id)
    if not session:
        return

    logger.debug("scambaiter_loop started: call_id=%r", call_id)

    while session.state not in (CallState.ENDED,):
        try:
            try:
                # Use a timeout so we can periodically check session.state
                transcript_window = await asyncio.wait_for(session.scambaiter_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            # Process the turn
            await _fire_scambaiter_turn(call_id, transcript_window)

        except asyncio.CancelledError:
            logger.debug("scambaiter_loop cancelled: call_id=%r", call_id)
            break
        except Exception as exc:
            logger.error("scambaiter_loop error [%s]: %s", call_id, exc)
            await asyncio.sleep(1.0)


# ── STT + Fact-Check loop ──────────────────────────────────────────────────────

async def _stt_loop(call_id: str) -> None:
    """
    Independent asyncio task: accumulates audio into utterance chunks,
    runs Whisper STT, then feeds into claim extraction → search → verdict.

    Latency: 1.5–4s end-to-end (see §1.5). Never blocks DSP loops.
    The UI shows "verifying…" (factcheck_update with status="VERIFYING") until done.

    Video evidence capture is handled by the dedicated _evidence_capture_loop
    task (200 ms cadence) — NOT here — so frame commits are never gated on
    STT pipeline latency.
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

            # Broadcast transcript chunk to frontend for live display
            await manager.send_json(call_id, {
                "type": "transcript_update",
                "text": transcript,
                "is_final": True,
                "ts": _ts(),
            })

            if session.state == CallState.SCAMBAITER_ACTIVE:
                # Bypass fact-checking and queue the transcript directly for the scambaiter loop
                # We do this immediately instead of waiting for claim_extractor to accumulate 50 chars
                session.scambaiter_queue.put_nowait(transcript)
                continue

            # Accumulate in claim extractor (debounced)
            claim_extractor.add_transcript(transcript)

            if not claim_extractor.ready():
                continue

            transcript_window = claim_extractor.get_and_reset()

            # Claim extraction + search + verdict (1.5–4s pipeline)
            claim = await claim_extractor.extract(transcript_window, full_transcript=full_transcript, call_id=call_id)
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
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
            logger.warning("Network failure in STT loop [%s]: %s. Falling back to LIMITED mode.", call_id, exc)
            if session.mode != "limited":
                session.mode = "limited"
                await manager.send_json(call_id, {
                    "type": "mode_update",
                    "mode": "limited",
                    "ts": _ts()
                })
                # Send UNCERTAIN for current claim
                await manager.send_json(call_id, {
                    "type": "factcheck_update",
                    "status": "UNCERTAIN",
                    "message": "Network unavailable. Fact-checker is offline. Relying on local DSP.",
                    "evidence_urls": [],
                    "category": "UNKNOWN",
                    "ts": _ts()
                })
            await asyncio.sleep(2.0)
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

    cfg = get_settings()

    # Notify client of successful connection
    await manager.send_json(call_id, {
        "type": "connected",
        "call_id": call_id,
        "ts": _ts(),
    })

    # Send configuration information
    await manager.send_json(call_id, {
        "type": "config_info",
        "dsp_enabled": cfg.dsp_voice_detection_enabled,
        "ts": _ts(),
    })

    # Perform and broadcast Number Intel if caller_number is provided
    if session.caller_number:
        voip_info = detect_voip_pattern(session.caller_number)
        rep = get_reputation(session.caller_number)
        await manager.send_json(call_id, {
            "type": "number_intel",
            "is_likely_voip": voip_info["is_likely_voip"],
            "voip_confidence": voip_info["confidence"],
            "times_reported": rep.get("times_reported", 0),
            "registration_circle": "Delhi NCR" if session.caller_number.startswith("9198") else "Unknown",
            "ts": _ts(),
        })

    # ── PRIMARY: STT / Fact-Check loop — ALWAYS runs ──────────────────────────
    stt_task = asyncio.create_task(_stt_loop(call_id))
    session.stt_task = stt_task

    # ── SCAMBAITER: Dedicated audio loop ──────────────────────────────────────
    scambaiter_task = asyncio.create_task(_scambaiter_loop(call_id))
    session.scambaiter_task = scambaiter_task

    # ── ALWAYS: Video evidence capture loop — runs at 200ms cadence ───────────
    # Decoupled from STT so frames are committed to permanent record within
    # 200ms of a CRITICAL verdict, regardless of STT pipeline latency.
    evidence_task = asyncio.create_task(_evidence_capture_loop(call_id))
    session.evidence_task = evidence_task  # type: ignore[attr-defined]

    # ── EXPERIMENTAL: DSP loops — only when flag is on ────────────────────────
    bispectrum_task = None
    tremor_task = None
    if cfg.dsp_voice_detection_enabled:
        bispectrum_task = asyncio.create_task(_bispectrum_loop(call_id))
        tremor_task = asyncio.create_task(_tremor_loop(call_id))
        session.bispectrum_task = bispectrum_task
        session.tremor_task = tremor_task
        logger.info("DSP loops ENABLED for call_id=%r", call_id)
    else:
        logger.info("DSP loops DISABLED for call_id=%r (DSP_VOICE_DETECTION_ENABLED=false)", call_id)

    # ── HF ML loop — only when token is present ───────────────────────────────
    hf_task = None
    if cfg.hf_api_token:
        hf_task = asyncio.create_task(_hf_ml_loop(call_id))
        session.hf_task = hf_task  # type: ignore[attr-defined]
        logger.info("HF ML loop ENABLED for call_id=%r", call_id)

    try:
        while True:
            # Idle timeout: terminate connection if no audio received for 30 seconds
            try:
                message = await asyncio.wait_for(websocket.receive_bytes(), timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning("WebSocket idle timeout: call_id=%r", call_id)
                break

            # Payload validation: limit frame size to prevent memory abuse (e.g., max 64KB)
            if len(message) > 65536:
                logger.error("WebSocket abuse detected: frame size %d > 64KB, call_id=%r", len(message), call_id)
                break

            # Ingest binary audio frame safely
            try:
                n = ingestion.ingest_frame(message)
                # Accumulate raw bytes for forensic hash
                session.recorded_audio_bytes += message
                logger.debug("Audio frame: %d bytes → %d samples (call_id=%r)", len(message), n, call_id)
            except Exception as frame_exc:
                logger.error("Malformed audio frame dropped (call_id=%r): %s", call_id, frame_exc)
                continue

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
