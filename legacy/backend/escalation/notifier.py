"""
escalation/notifier.py — Family/emergency contact SMS alert.

Sends an SMS to a registered family or emergency contact when a CRITICAL
verdict fires. The SMS is brief, clear, and actionable — designed for a
non-technical family member who receives it.

SMS providers (configurable via SMS_BACKEND env var):
  - "msg91"   : MSG91 (Indian SMS provider, TRAI-registered, INR billing)
                Recommended for India market — lower latency, local support.
  - "twilio"  : Twilio SMS API (global, USD billing)
  - "mock"    : Log only (for testing without credentials)

Rationale:
  Indian mobile networks have variable internet connectivity, but SMS delivery
  is extremely reliable even on 2G. For a system protecting elderly users,
  SMS to a family contact is a critical safety net.
"""

from __future__ import annotations

import logging
import os
from typing import Optional, TypedDict

import httpx

logger = logging.getLogger(__name__)

_SMS_BACKEND = os.getenv("SMS_BACKEND", "msg91")


class SMSResult(TypedDict):
    success: bool
    provider: str
    destination: str
    message_id: Optional[str]
    error: Optional[str]


def _build_family_sms(call_id: str, verdict: str, message: str) -> str:
    """Build a short, clear SMS for a family member."""
    return (
        f"[PhaseGuard ALERT] "
        f"URGENT: A CRITICAL scam call was detected on your family member's phone. "
        f"Call ID: {call_id}. "
        f"Details: {message[:100]}. "
        f"Please check on them immediately. "
        f"Report at: cybercrime.gov.in or call 1930."
    )


async def send_family_alert(
    destination_number: str,
    call_id: str,
    verdict: str,
    message: str,
) -> SMSResult:
    """
    Send an SMS alert to a family/emergency contact.

    Parameters
    ----------
    destination_number : str
        Phone number to send SMS to (E.164 format: +919876543210).
    call_id : str
        Call identifier for reference.
    verdict : str
        Verdict status (should be "CRITICAL" to trigger this).
    message : str
        Human-readable verdict message to include in SMS.

    Returns
    -------
    SMSResult dict
    """
    if verdict != "CRITICAL":
        logger.debug(
            "SMS notifier: verdict is %r (not CRITICAL) — skipping family alert", verdict
        )
        return SMSResult(success=False, provider=_SMS_BACKEND, destination=destination_number,
                         message_id=None, error="Non-CRITICAL verdict — no SMS sent")

    sms_text = _build_family_sms(call_id, verdict, message)
    backend = _SMS_BACKEND.lower()

    if backend == "msg91":
        return await _send_msg91(destination_number, sms_text)
    elif backend == "twilio":
        return await _send_twilio(destination_number, sms_text)
    else:
        return _send_mock(destination_number, sms_text)


async def _send_msg91(to: str, text: str) -> SMSResult:
    """
    Send SMS via MSG91 API.
    Requires MSG91_AUTH_KEY env var.
    MSG91 is an Indian SMS provider compliant with TRAI DLT regulations.
    Rationale: lower latency within India, INR billing, Indian support.
    """
    from core.config import get_settings
    cfg = get_settings()

    if not cfg.msg91_auth_key:
        logger.warning("MSG91: MSG91_AUTH_KEY not set — falling back to mock")
        return _send_mock(to, text)

    # MSG91 requires DLT-registered sender ID and approved template.
    # In production: register your template at https://msg91.com/help/dlt
    url = "https://api.msg91.com/api/v5/otp"
    payload = {
        "authkey": cfg.msg91_auth_key,
        "mobiles": to.lstrip("+"),  # MSG91 accepts numbers without leading +
        "message": text,
        "sender": cfg.msg91_sender_id,
        "route": "4",  # Transactional route
        "country": "91",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            data = response.json()

        if data.get("type") == "success":
            logger.info("MSG91 SMS sent to %s, request_id=%s", to, data.get("request_id"))
            return SMSResult(
                success=True, provider="msg91", destination=to,
                message_id=data.get("request_id"), error=None,
            )
        else:
            logger.error("MSG91 SMS failed: %s", data)
            return SMSResult(
                success=False, provider="msg91", destination=to,
                message_id=None, error=str(data),
            )
    except Exception as exc:
        logger.error("MSG91 SMS error: %s", exc)
        return SMSResult(success=False, provider="msg91", destination=to,
                         message_id=None, error=str(exc))


async def _send_twilio(to: str, text: str) -> SMSResult:
    """
    Send SMS via Twilio API.
    Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER env vars.
    """
    from core.config import get_settings
    cfg = get_settings()

    if not cfg.twilio_account_sid:
        logger.warning("Twilio: credentials not set — falling back to mock")
        return _send_mock(to, text)

    try:
        from twilio.rest import Client

        client = Client(cfg.twilio_account_sid, cfg.twilio_auth_token)
        msg = client.messages.create(body=text, from_=cfg.twilio_phone_number, to=to)
        logger.info("Twilio SMS sent to %s, sid=%s", to, msg.sid)
        return SMSResult(
            success=True, provider="twilio", destination=to,
            message_id=msg.sid, error=None,
        )
    except Exception as exc:
        logger.error("Twilio SMS error: %s", exc)
        return SMSResult(success=False, provider="twilio", destination=to,
                         message_id=None, error=str(exc))


def _send_mock(to: str, text: str) -> SMSResult:
    """Mock SMS sender — logs the message without actual delivery (for testing)."""
    logger.info("MOCK SMS to %s: %s", to, text[:120])
    return SMSResult(
        success=True, provider="mock", destination=to,
        message_id="mock-00000", error=None,
    )
