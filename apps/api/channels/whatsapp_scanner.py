"""
channels/whatsapp_scanner.py — WhatsApp text/image scam scanner via Meta Business API.

Design:
  - Supports forwarded text and images (OCR).
  - Routes text through existing claim_extraction and verdict engines.
  - Returns a WhatsApp reply with the verdict.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Any, Tuple

from fastapi import APIRouter, Request, HTTPException

from factcheck.claim_extraction import ClaimExtractor
from factcheck.verdict import generate_verdict
from factcheck.search import SearchVerifier
from intel.number_reputation import report_number
from security.rate_limit import LIMIT_API, limiter
import hmac
import hashlib
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

# Basic URL pattern for link safety check
URL_PATTERN = re.compile(r'https?://[^\s]+')
SUSPICIOUS_TLDS = ['.xyz', '.top', '.club', '.online', '.site']
SHORTENERS = ['bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly']

def check_link_safety(text: str) -> Tuple[bool, str]:
    """Check if text contains suspicious links."""
    urls = URL_PATTERN.findall(text)
    for url in urls:
        url_lower = url.lower()
        if any(tld in url_lower for tld in SUSPICIOUS_TLDS):
            return False, f"Suspicious top-level domain in link: {url}"
        if any(short in url_lower for short in SHORTENERS):
            return False, f"URL shortener hides actual destination: {url}"
    return True, "Links appear standard or none present"


@router.post("/webhook")
@limiter.limit(LIMIT_API)
async def whatsapp_webhook(request: Request) -> Dict[str, Any]:
    """
    Webhook for WhatsApp Business API.
    Expects incoming message events.
    """
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        logger.warning("WhatsApp webhook missing X-Hub-Signature-256 header")
        raise HTTPException(status_code=403, detail="Invalid signature")

    body_bytes = await request.body()
    
    # HMAC verification against APP_SECRET
    app_secret = os.getenv("WHATSAPP_APP_SECRET")
    if not app_secret:
        logger.error("WHATSAPP_APP_SECRET not configured in environment")
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    expected_signature = hmac.new(
        key=app_secret.encode('utf-8'),
        msg=body_bytes,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # X-Hub-Signature-256 comes as 'sha256=...'
    if not signature.startswith("sha256=") or not hmac.compare_digest(signature[7:], expected_signature):
        logger.warning("WhatsApp webhook HMAC validation failed")
        raise HTTPException(status_code=403, detail="Invalid signature")

    body = await request.json()

    # Parse WhatsApp API payload (simplified for demonstration)
    try:
        entry = body.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])

        if not messages:
            return {"status": "ignored"}

        msg = messages[0]
        sender_phone = msg.get('from')
        msg_type = msg.get('type')

        extracted_text = ""

        if msg_type == 'text':
            extracted_text = msg.get('text', {}).get('body', '')
        elif msg_type == 'image':
            # STUBBED: OCR on forwarded screenshot
            extracted_text = "[OCR extraction pending implementation - treating as suspicious investment claim]"
            logger.info("Image received from %s, OCR pending", sender_phone)
        else:
            return {"status": "unsupported_type"}

        call_id = f"wa_{sender_phone}"

        # Link safety check
        is_safe_links, link_note = check_link_safety(extracted_text)

        # Route through existing pipeline
        extractor = ClaimExtractor(debounce_chars=0)  # immediate extraction
        claim = await extractor.extract(extracted_text, call_id=call_id)

        if claim is None:
            return {"status": "error", "reason": "claim extraction failed"}

        # Run search verification
        search_verifier = SearchVerifier()
        search_result = await search_verifier.verify_claim(claim, call_id=call_id)

        # Generate final verdict
        verdict = await generate_verdict(
            transcript=extracted_text,
            claim=claim,
            search_result=search_result,
            call_id=call_id,
        )

        # Modify verdict if links are suspicious
        if not is_safe_links and verdict['status'] == 'SAFE':
            verdict['status'] = 'UNCERTAIN'
            verdict['message'] += f" However, {link_note}."

        # Store in reputation store if we extracted a number from the text
        if claim.get("phone_numbers_mentioned"):
            for num in claim["phone_numbers_mentioned"]:
                if verdict['status'] == 'CRITICAL':
                    report_number(num, dossier_id=call_id, verdict='CRITICAL')

        # Reply via WhatsApp (STUBBED sending action)
        reply_text = (
            f"PhaseGuard Scanner:\nVerdict: {verdict['status']}\n\n"
            f"{verdict['message']}\n\n"
            f"Note: Web verification unavailable."
        )
        logger.info("WhatsApp Reply to %s: %s", sender_phone, reply_text)

        return {"status": "success", "verdict": verdict['status'], "reply": reply_text}

    except Exception as exc:
        logger.error("WhatsApp webhook failed: %s", exc)
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.get("/webhook")
async def whatsapp_verify(request: Request) -> Any:
    """
    WhatsApp webhook verification (GET) — Meta sends a hub.challenge that
    must be echoed back to complete webhook registration.
    """
    params = dict(request.query_params)
    hub_mode      = params.get("hub.mode")
    hub_challenge = params.get("hub.challenge")
    hub_verify    = params.get("hub.verify_token")

    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
    
    if not verify_token:
        logger.error("WHATSAPP_VERIFY_TOKEN not configured in environment")
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    # In production, validate hub_verify against a stored verify token
    if hub_mode == "subscribe" and hub_challenge and hub_verify == verify_token:
        logger.info("WhatsApp webhook verified successfully")
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(hub_challenge)

    raise HTTPException(status_code=403, detail="Webhook verification failed")
