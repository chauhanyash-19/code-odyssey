"""
escalation/send_bridge.py — Human-confirmed escalation dispatch.

Critical design decision (§7):
  NO escalation payload is ever dispatched automatically.
  All sends require an explicit human confirmation click from the frontend.

  Rationale:
    1. India's National Cyber Crime Portal has no public API for third-party
       auto-submission — so "auto-filing" is not technically possible.
    2. Auto-sending emails to law enforcement or officials without human
       review is legally risky and could be considered harassment.
    3. For a demo: the "human confirms → then it sends" beat is MORE compelling
       than silent auto-filing — it puts the user in control.

  This module acts as the gated dispatch point:
    - drafter.py builds the payload
    - The frontend shows the user exactly what will be sent and to whom
    - User clicks confirm → POST /call/{call_id}/escalate/confirm
    - send_bridge.dispatch() is called with the pre-drafted payload
    - Dispatch is logged to the dossier chain-of-custody log

Chain of custody logging:
  Every attempt (successful or failed) is logged with:
    - ISO timestamp
    - Destination (email address / webhook URL)
    - Payload summary
    - Delivery status
  This log is embedded in the forensic PDF (pdf_report.py).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TypedDict

import httpx

from escalation.drafter import EscalationPayload

logger = logging.getLogger(__name__)


class DispatchResult(TypedDict):
    success: bool
    dispatched_at: Optional[str]
    destination: str
    delivery_status: str
    error: Optional[str]


async def dispatch_escalation(
    payload: EscalationPayload,
    call_session=None,  # CallSession — optional, for chain-of-custody logging
) -> DispatchResult:
    """
    Dispatch a pre-drafted escalation payload AFTER human confirmation.

    This function should ONLY be called from the /escalate/confirm endpoint,
    after verifying the confirmation token from the frontend.

    Parameters
    ----------
    payload : EscalationPayload
        The drafted payload from drafter.py.
    call_session : CallSession or None
        If provided, the dispatch record is appended to the session's
        escalation_records list for chain-of-custody tracking.

    Returns
    -------
    DispatchResult dict
    """
    now = datetime.now(timezone.utc).isoformat()
    fmt = payload.get("format", "webhook")
    destination = payload.get("destination", "")

    logger.info(
        "Escalation dispatch: call_id=%r format=%r destination=%r",
        payload.get("call_id"),
        fmt,
        destination[:60],
    )

    result: DispatchResult

    try:
        if fmt == "email":
            result = await _dispatch_email(payload, now)
        elif fmt in ("slack", "discord", "webhook"):
            result = await _dispatch_webhook(payload, now)
        else:
            result = DispatchResult(
                success=False,
                dispatched_at=now,
                destination=destination,
                delivery_status="ERROR",
                error=f"Unknown escalation format: {fmt!r}",
            )
    except Exception as exc:
        logger.error("Escalation dispatch error: %s", exc)
        result = DispatchResult(
            success=False,
            dispatched_at=now,
            destination=destination,
            delivery_status="ERROR",
            error=str(exc),
        )

    # Chain-of-custody: log to session
    if call_session is not None:
        from core.connection_manager import EscalationRecord

        record = EscalationRecord(
            drafted_at=payload.get("drafted_at"),
            confirmed_at=now,
            destination=destination,
            delivery_status=result.get("delivery_status", "UNKNOWN"),
            payload_summary=(
                f"format={fmt}, verdict={payload.get('verdict')}, "
                f"call_id={payload.get('call_id')}"
            ),
        )
        call_session.escalation_records.append(record)
        call_session.escalation_confirmed = result.get("success", False)
        logger.info(
            "Chain of custody: escalation record added to call_id=%r",
            payload.get("call_id"),
        )

    return result


async def _dispatch_email(payload: EscalationPayload, dispatched_at: str) -> DispatchResult:
    """
    Dispatch via email using SMTP (smtplib) or an email API.
    Uses environment variables: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD.
    """
    import os
    import smtplib
    from email.mime.application import MIMEApplication
    from email.mime.image import MIMEImage
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")

    if not smtp_host or not smtp_user:
        logger.warning("Email escalation: SMTP not configured — logging payload only")
        logger.info("EMAIL PAYLOAD (not sent):\nTo: %s\nSubject: %s\n%s",
                    payload.get("destination"),
                    payload.get("subject"),
                    payload.get("body_text", "")[:500])
        return DispatchResult(
            success=False,
            dispatched_at=dispatched_at,
            destination=payload.get("destination", ""),
            delivery_status="SMTP_NOT_CONFIGURED",
            error="SMTP credentials not set",
        )

    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = payload.get("subject", "")
        msg["From"] = smtp_user
        msg["To"] = payload.get("destination", "")

        # Text/HTML alternatives
        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(payload.get("body_text", ""), "plain"))
        if payload.get("body_html"):
            alt_part.attach(MIMEText(payload.get("body_html", ""), "html"))
        msg.attach(alt_part)

        # Attach video frame images when present and still on disk
        video_frames = payload.get("video_frames") or []
        for i, frame in enumerate(video_frames):
            local_path = frame.get("local_path", "")
            if local_path and os.path.exists(local_path):
                try:
                    with open(local_path, "rb") as img_f:
                        img_data = img_f.read()
                    ext = os.path.splitext(local_path)[1].lower().lstrip(".")
                    mime_img = MIMEImage(img_data, _subtype=ext or "jpeg")
                    mime_img.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=f"evidence_frame_{i+1}.{ext or 'jpg'}",
                    )
                    msg.attach(mime_img)
                    logger.info("Attached video frame %d to email: %s", i + 1, local_path)
                except Exception as attach_err:
                    logger.warning("Could not attach frame %d: %s", i + 1, attach_err)

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, payload.get("destination", ""), msg.as_string())

        logger.info("Email escalation sent to %s", payload.get("destination"))
        return DispatchResult(
            success=True,
            dispatched_at=dispatched_at,
            destination=payload.get("destination", ""),
            delivery_status="SENT",
            error=None,
        )
    except Exception as exc:
        logger.error("Email dispatch failed: %s", exc)
        return DispatchResult(
            success=False,
            dispatched_at=dispatched_at,
            destination=payload.get("destination", ""),
            delivery_status="ERROR",
            error=str(exc),
        )


async def _dispatch_webhook(payload: EscalationPayload, dispatched_at: str) -> DispatchResult:
    """Dispatch to a Slack / Discord / generic webhook URL."""
    destination = payload.get("destination", "")
    json_payload = payload.get("json_payload", {})

    if not destination:
        return DispatchResult(
            success=False,
            dispatched_at=dispatched_at,
            destination=destination,
            delivery_status="ERROR",
            error="No webhook URL configured",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(destination, json=json_payload)
            response.raise_for_status()

        logger.info("Webhook escalation sent to %s — status %d", destination[:60], response.status_code)
        return DispatchResult(
            success=True,
            dispatched_at=dispatched_at,
            destination=destination,
            delivery_status=f"HTTP_{response.status_code}",
            error=None,
        )
    except Exception as exc:
        logger.error("Webhook dispatch failed to %s: %s", destination[:60], exc)
        return DispatchResult(
            success=False,
            dispatched_at=dispatched_at,
            destination=destination,
            delivery_status="ERROR",
            error=str(exc),
        )
