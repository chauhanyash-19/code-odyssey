"""
main.py — FastAPI application entry point for PhaseGuard API.

Wires together:
  - All REST routers
  - WebSocket endpoint (ws/call_socket.py)
  - Lifespan: executor startup/shutdown
  - Exotel webhook ingestion endpoint
  - Rate limiting middleware
  - CORS

REST endpoints:
  POST /call/init                    — Issue JWT, create call session
  POST /call/{call_id}/scambait      — Activate scambaiter (JWT required)
  GET  /call/{call_id}/dossier       — Download forensic PDF
  POST /call/{call_id}/escalate/draft  — Draft escalation payload
  POST /call/{call_id}/escalate/confirm — Confirm & dispatch escalation
  POST /exotel/stream/{call_id}      — Exotel Voice Streaming webhook
  WS   /ws/call/{call_id}            — Live call audio WebSocket
"""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Body, Depends, FastAPI, HTTPException, Request, Response, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

import io
import logging

from core.auth import create_call_token, require_call_token, verify_call_token_for_call
from core.config import get_settings
from core.connection_manager import CallState, manager
from security.rate_limit import LIMIT_API, LIMIT_LLM, LIMIT_WS_UPGRADE, limiter
from workers.executor import get_executor, shutdown_executor
from ws.call_socket import router as ws_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: pre-warm the executor. Shutdown: drain it cleanly."""
    logger.info("PhaseGuard API starting up…")
    
    from core.config import get_settings
    get_settings().log_startup_summary()
    
    get_executor()  # Pre-create the ThreadPoolExecutor
    yield
    logger.info("PhaseGuard API shutting down…")
    shutdown_executor()


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PhaseGuard Anti-Scam API",
    description=(
        "360° multi-modal anti-scam OS: real-time voice deepfake detection (bispectrum DSP), "
        "physiological micro-tremor analysis, LLM fact-checking, AI scambaiter, "
        "and forensic PDF dossier generation for India's National Cyber Crime Portal (1930)."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiting
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded: " + str(exc)},
    )

# CORS — temporarily allow all origins until deployed frontend URL is known
# TODO: Restrict to the specific frontend domain once deployed
cfg = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include WebSocket router
app.include_router(ws_router)

# Include WhatsApp router
try:
    from channels.whatsapp_scanner import router as whatsapp_router
    app.include_router(whatsapp_router)
except ImportError:
    pass


# ── Request / Response Models ─────────────────────────────────────────────────

class CallInitRequest(BaseModel):
    """Body for POST /call/init"""
    ingestion_mode: str = "browser_mic"  # "browser_mic" | "exotel" | "twilio"
    call_id: Optional[str] = None
    caller_number: Optional[str] = None

class CallInitResponse(BaseModel):
    call_id: str
    token: str
    ws_url: str
    expires_in_seconds: int

class ScambaitRequest(BaseModel):
    pass  # No body needed; call_id from path, token from header

class EscalationDraftRequest(BaseModel):
    destination_email: Optional[str] = None
    webhook_url: Optional[str] = None
    format: str = "webhook"  # "email" | "slack" | "discord" | "webhook"

class EscalationConfirmRequest(BaseModel):
    draft_id: str  # Echoed from draft response for idempotency

class EscalationDraftResponse(BaseModel):
    draft_id: str
    payload_summary: str
    destination: str
    verdict: str
    drafted_at: str
    video_frame_count: int = 0
    video_frames_summary: list = []
    warning: str = (
        "This payload has NOT been sent. Click confirm to dispatch. "
        "Nothing is auto-filed — you are always in control."
    )


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check — no auth required."""
    return {
        "status": "ok",
        "active_calls": len(manager.active_calls()),
        "ts": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/call/init", response_model=CallInitResponse)
@limiter.limit(LIMIT_WS_UPGRADE)
async def init_call(request: Request, body: CallInitRequest = Body(...)) -> CallInitResponse:
    """
    Initialize a call session and issue a short-lived JWT.

    Returns a call_id and token that the client uses to open the WebSocket.
    Rate limited: 5 new calls/minute per IP.
    """
    cfg = get_settings()
    call_id = body.call_id if body.call_id else str(uuid.uuid4())
    token = create_call_token(call_id)

    # Create session in connection manager
    manager.create_session(call_id, ingestion_mode=body.ingestion_mode, caller_number=body.caller_number)

    ws_url = f"ws://{cfg.ws_host}:{cfg.ws_port}/ws/call/{call_id}?token={token}"
    logger.info("Call initialized: call_id=%r mode=%r", call_id, body.ingestion_mode)

    return CallInitResponse(
        call_id=call_id,
        token=token,
        ws_url=ws_url,
        expires_in_seconds=cfg.jwt_ttl_minutes * 60,
    )


@app.post("/call/{call_id}/scambait")
@limiter.limit(LIMIT_API)
async def activate_scambait(
    request: Request,
    call_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """
    Activate the AI scambaiter for a CRITICAL call.

    Requires JWT scoped to call_id.
    State-machine guard: only allowed when call is ACTIVE.
    """
    if credentials:
        verify_call_token_for_call(credentials.credentials, call_id)
    else:
        raise HTTPException(status_code=401, detail="Missing token")

    session = manager.get_session(call_id)
    if not session:
        raise HTTPException(status_code=404, detail="Call session not found")

    manager.activate_scambaiter(call_id)
    logger.info("Scambaiter activated via REST: call_id=%r", call_id)
    return {"status": "scambaiter_active", "call_id": call_id, "ts": datetime.now(timezone.utc).isoformat()}


@app.post("/call/{call_id}/test_inject")
async def test_inject(
    request: Request,
    call_id: str,
    text: str,
) -> dict:
    """
    Test endpoint to inject text as if it came from STT.
    """
    session = manager.get_session(call_id)
    if not session:
        raise HTTPException(status_code=404, detail="Call session not found")

    session.transcript_history.append(text)
    if session.state == CallState.SCAMBAITER_ACTIVE:
        session.scambaiter_queue.put_nowait(text)
    else:
        # Fake a critical alert to trigger the scambaiter logic in tests
        await manager.send_json(call_id, {
            "type": "factcheck_update",
            "status": "CRITICAL",
            "message": "critical_alert",
            "evidence_urls": [],
            "ts": datetime.now(timezone.utc).isoformat(),
        })

    logger.info("Injected test speech: call_id=%r text=%r", call_id, text)
    return {"status": "injected", "text": text}


@app.post("/call/{call_id}/frame")
@limiter.limit(LIMIT_API)
async def upload_video_frame(
    request: Request,
    call_id: str,
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """
    Accepts an uploaded video frame via user-consented screen capture.
    Runs the Haar Cascade pipeline and saves it to the rolling buffer.
    """
    if credentials:
        verify_call_token_for_call(credentials.credentials, call_id)
    else:
        raise HTTPException(status_code=401, detail="Missing token")

    session = manager.get_session(call_id)
    if not session:
        raise HTTPException(status_code=404, detail="Call session not found")

    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Invalid content type. Expected JPEG, PNG, or WEBP.")
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Payload too large. Maximum size is 5MB.")

    image_bytes = await file.read()
    if len(image_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Payload too large. Maximum size is 5MB.")

    import cv2
    import numpy as np
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("cv2.imdecode returned None")
    except Exception as e:
        logger.error("Failed to decode uploaded image: %s", e)
        raise HTTPException(status_code=400, detail="Invalid image content or corruption detected.")

    from workers.executor import get_executor
    from forensics.video_evidence import process_frame_bytes
    import asyncio

    loop = asyncio.get_event_loop()
    frame_meta = await loop.run_in_executor(
        get_executor(),
        process_frame_bytes,
        image_bytes,
        call_id,
        None
    )

    if frame_meta:
        # Keep a rolling buffer of the last 3 uploaded frames per call session
        session.video_frames_buffer.append(frame_meta)
        if len(session.video_frames_buffer) > 3:
            session.video_frames_buffer.pop(0)

        logger.info(
            "Video frame evidence buffered: call_id=%r hash=%s face=%s",
            call_id,
            frame_meta["sha256_hash"][:12],
            frame_meta["face_detected"],
        )
        return {"status": "ok", "sha256_hash": frame_meta["sha256_hash"]}

    raise HTTPException(status_code=400, detail="Failed to process frame")

@app.get("/call/{call_id}/dossier")
@limiter.limit(LIMIT_API)
async def get_dossier(
    request: Request,
    call_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> Response:
    """
    Generate and return the forensic PDF dossier for a call.

    Returns application/pdf.
    Requires JWT scoped to call_id.
    """
    if credentials:
        verify_call_token_for_call(credentials.credentials, call_id)
    else:
        raise HTTPException(status_code=401, detail="Missing token")

    session = manager.get_session(call_id)
    if not session:
        raise HTTPException(status_code=404, detail="Call session not found")

    # Compute hash
    from forensics.hashing import compute_audio_hash
    hash_result = compute_audio_hash(session.recorded_audio_bytes)

    # Extract identifiers
    from forensics.extraction import extract_identifiers
    full_transcript = " ".join(session.transcript_history)
    identifiers = await extract_identifiers(full_transcript, call_id=call_id)

    # Build entity verification signals for impersonated entities (if any)
    from intel.company_verification import verify_entity
    entity_verification_data = []
    impersonated_entities = identifiers.get("impersonated_entities", [])
    if impersonated_entities:
        # Verify up to 3 entities to keep latency reasonable
        for entity_name in impersonated_entities[:3]:
            try:
                ev = await verify_entity(entity_name)
                entity_verification_data.append(ev)
            except Exception as _ev_err:
                logger.warning("Entity verification failed for %r: %s", entity_name, _ev_err)
    elif session.factcheck_history:
        # Fallback: scan factcheck history for claimed entities in messages
        seen_entities: set = set()
        for entry in session.factcheck_history:
            msg = entry.get("message", "")
            # Extract quoted entity names like 'Google HR', 'RBI', 'SBI'
            import re as _re
            for match in _re.findall(r"(?:from|as|claiming to be|impersonating)\s+([A-Z][\w\s]{2,40}?)(?:\s|,|\.|$)", msg):
                name = match.strip()
                if name and name not in seen_entities:
                    seen_entities.add(name)
                    try:
                        ev = await verify_entity(name)
                        entity_verification_data.append(ev)
                    except Exception:
                        pass
                    if len(entity_verification_data) >= 2:
                        break

    # Build PDF
    from forensics.pdf_report import generate_forensic_pdf
    pdf_bytes = generate_forensic_pdf(
        call_id=call_id,
        call_start_time=session.factcheck_history[0].get("ts", "N/A") if session.factcheck_history else "N/A",
        call_duration_seconds=hash_result["duration_seconds"],
        ingestion_mode=session.ingestion_mode,
        hash_result=dict(hash_result),
        peak_pdi=session.peak_pdi,
        tremor_findings={"tremor_energy": session.peak_tremor, "has_tremor": session.peak_tremor > 0.15,
                         "peak_tremor_hz": 10.0},
        ensemble_label=session.latest_ensemble_label,
        identifiers=dict(identifiers),
        factcheck_history=session.factcheck_history,
        transcript_summary=full_transcript[:2000],
        scambaiter_log=session.scambaiter_log,
        escalation_records=[
            {
                "drafted_at": r.drafted_at,
                "confirmed_at": r.confirmed_at,
                "destination": r.destination,
                "delivery_status": r.delivery_status,
            }
            for r in session.escalation_records
        ],
        pcm16_bytes=session.recorded_audio_bytes,
        video_frames=session.video_frames if session.video_frames else None,
        entity_verification=entity_verification_data,
    )

    # Store extracted identifiers on session
    session.extracted_identifiers = dict(identifiers)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="phaseguard-{call_id}.pdf"'},
    )


@app.get("/call/{call_id}/chakshu-export")
@limiter.limit(LIMIT_API)
async def get_chakshu_export(
    request: Request,
    call_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> Response:
    """Download Chakshu CSV format report."""
    if credentials:
        verify_call_token_for_call(credentials.credentials, call_id)
    else:
        raise HTTPException(status_code=401, detail="Missing token")
        
    from govt_export.chakshu_export import generate_chakshu_csv
    csv_bytes = generate_chakshu_csv(call_id)
    
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="chakshu-{call_id}.csv"'},
    )


@app.post("/call/{call_id}/escalate/draft", response_model=EscalationDraftResponse)
@limiter.limit(LIMIT_API)
async def draft_escalation(
    request: Request,
    call_id: str,
    body: EscalationDraftRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> EscalationDraftResponse:
    """
    Draft (but DO NOT send) an escalation payload.

    Returns a draft_id and summary for the frontend confirmation modal.
    Requires JWT scoped to call_id.
    """
    if credentials:
        verify_call_token_for_call(credentials.credentials, call_id)
    else:
        raise HTTPException(status_code=401, detail="Missing token")

    session = manager.get_session(call_id)
    if not session:
        raise HTTPException(status_code=404, detail="Call session not found")

    # Allow reporting even if factcheck_history is empty (e.g. pure deepfake detected)
    if not session.factcheck_history:
        logger.warning("Drafting report with empty factcheck_history")

    from forensics.hashing import compute_audio_hash
    from escalation.drafter import draft_email_payload, draft_webhook_payload

    hash_result = compute_audio_hash(session.recorded_audio_bytes)
    verdict = session.factcheck_history[-1].get("status", "UNKNOWN") if session.factcheck_history else "UNKNOWN"
    identifiers = session.extracted_identifiers or {}
    pdf_filename = f"phaseguard-{call_id}.pdf"

    cfg = get_settings()

    # Collect video frames metadata for the draft payload
    vf = session.video_frames
    video_frames_summary = [
        {
            "timestamp": f.get("timestamp"),
            "sha256_hash": f.get("sha256_hash"),
            "face_detected": f.get("face_detected"),
            "local_path": f.get("local_path"),
        }
        for f in vf
    ]

    if body.format == "email":
        dest = body.destination_email or cfg.cybercrime_cell_email or "cybercrime@example.gov.in"
        payload = draft_email_payload(
            call_id=call_id,
            verdict=verdict,
            identifiers=identifiers,
            hash_result=dict(hash_result),
            factcheck_history=session.factcheck_history,
            destination_email=dest,
            pdf_filename=pdf_filename,
            video_frames=vf,
        )
    else:
        dest = body.webhook_url or cfg.escalation_webhook_url or ""
        payload = draft_webhook_payload(
            call_id=call_id,
            verdict=verdict,
            identifiers=identifiers,
            hash_result=dict(hash_result),
            webhook_url=dest,
            pdf_filename=pdf_filename,
            format=body.format,
            video_frames=vf,
        )

    # Store draft on session
    session.escalation_drafted = True
    draft_id = str(uuid.uuid4())

    # Store the payload temporarily (in-memory; production should use Redis/DB)
    if not hasattr(app.state, "escalation_drafts"):
        app.state.escalation_drafts = {}
    app.state.escalation_drafts[draft_id] = payload

    summary = f"Format: {body.format} | To: {dest} | Verdict: {verdict}"
    if vf:
        summary += f" | Video Frames: {len(vf)} captured"
    if cfg.sms_backend == "simulated":
        summary += "\n\nNote: SMS will be simulated (logged only) — no real message will be sent."

    return EscalationDraftResponse(
        draft_id=draft_id,
        payload_summary=summary,
        destination=dest,
        verdict=verdict,
        drafted_at=payload["drafted_at"],
        video_frame_count=len(vf),
        video_frames_summary=video_frames_summary,
    )


@app.post("/call/{call_id}/escalate/confirm")
@limiter.limit(LIMIT_API)
async def confirm_escalation(
    request: Request,
    call_id: str,
    body: EscalationConfirmRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """
    Human-confirmed escalation dispatch.

    IMPORTANT: This is the ONLY place where escalation payloads are actually sent.
    Nothing is auto-filed without explicit human confirmation.

    Rationale: India's National Cyber Crime Portal has no public API for third-party
    auto-submission. Human-confirmed is both legally honest and a stronger demo beat.
    """
    if credentials:
        verify_call_token_for_call(credentials.credentials, call_id)
    else:
        raise HTTPException(status_code=401, detail="Missing token")

    session = manager.get_session(call_id)
    if not session:
        raise HTTPException(status_code=404, detail="Call session not found")

    drafts = getattr(app.state, "escalation_drafts", {})
    payload = drafts.get(body.draft_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Draft not found or already dispatched")

    from escalation.send_bridge import dispatch_escalation
    result = await dispatch_escalation(payload, call_session=session)

    # Remove draft after dispatch (idempotency)
    drafts.pop(body.draft_id, None)

    logger.info(
        "Escalation confirmed: call_id=%r success=%s dest=%r",
        call_id, result["success"], result["destination"][:60],
    )

    return {
        "success": result["success"],
        "delivery_status": result["delivery_status"],
        "dispatched_at": result.get("dispatched_at"),
        "error": result.get("error"),
    }


@app.post("/exotel/stream/{call_id}")
async def exotel_stream_webhook(call_id: str, request: Request) -> dict:
    """
    Exotel Voice Streaming webhook endpoint.

    Exotel sends raw audio chunks as the POST body.
    No JWT required on this endpoint — Exotel authenticates via shared webhook secret
    (validate X-Exotel-Signature in production).
    """
    body = await request.body()
    session = manager.get_session(call_id)

    if session is None:
        # Auto-create session for Exotel-initiated calls
        session = manager.create_session(call_id, ingestion_mode="exotel")

    from ingestion.exotel_adapter import ExotelAdapter
    adapter = ExotelAdapter(call_id, session.buffer)
    n = adapter.ingest_exotel_chunk(body)

    # Accumulate for forensic hash
    session.recorded_audio_bytes += body

    return {"status": "ok", "samples_ingested": n}


@app.post("/twilio/stream/{call_id}")
async def twilio_stream_webhook(call_id: str, request: Request) -> dict:
    """
    Twilio Media Streams WebSocket webhook.
    Accepts JSON events from Twilio.
    """
    event = await request.json()
    session = manager.get_session(call_id)

    if session is None:
        session = manager.create_session(call_id, ingestion_mode="twilio")

    from ingestion.exotel_adapter import ExotelAdapter
    adapter = ExotelAdapter(call_id, session.buffer, source_sample_rate=8000)
    n = adapter.ingest_twilio_media_event(event)

    return {"status": "ok", "samples_ingested": n}


@app.get("/call/{call_id}/status")
@limiter.limit(LIMIT_API)
async def get_call_status(
    request: Request,
    call_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """Get current status of a call session."""
    if credentials:
        verify_call_token_for_call(credentials.credentials, call_id)
    else:
        raise HTTPException(status_code=401, detail="Missing token")

    session = manager.require_session(call_id)
    return {
        "call_id": call_id,
        "state": session.state.value,
        "latest_pdi": round(session.latest_pdi, 4),
        "peak_pdi": round(session.peak_pdi, 4),
        "latest_tremor_energy": round(session.latest_tremor_energy, 4),
        "ensemble_label": session.latest_ensemble_label,
        "factcheck_count": len(session.factcheck_history),
        "latest_verdict": session.factcheck_history[-1] if session.factcheck_history else None,
        "buffer_stats": session.buffer.stats(),
        "ts": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/metrics")
@limiter.limit(LIMIT_API)
async def get_metrics(request: Request) -> dict:
    """Cost-efficiency dashboard aggregation."""
    # Dummy aggregation for MVP
    total_calls = len(manager.active_calls())
    total_groq_tokens = 500 * total_calls
    total_tts_chars = 150 * total_calls
    
    # Estimate costs in INR (1 USD = ~83 INR)
    cost_llm = total_groq_tokens * 0.0000415
    cost_tts = total_tts_chars * 0.0001
    
    cost_per_call = (cost_llm + cost_tts) / total_calls if total_calls > 0 else 0
    
    return {
        "total_calls_analyzed": total_calls,
        "total_groq_tokens": total_groq_tokens,
        "total_tts_chars": total_tts_chars,
        "cost_per_call_inr": round(cost_per_call, 2),
        "total_cost_inr": round(cost_llm + cost_tts, 2)
    }
