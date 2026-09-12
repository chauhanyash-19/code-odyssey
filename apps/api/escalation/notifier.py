"""
escalation/notifier.py — Family/emergency contact SMS alert.

Simulated SMS provider for hackathon build.
"""

from __future__ import annotations

import logging
import httpx
from datetime import datetime
from core.config import get_settings

logger = logging.getLogger(__name__)

async def send_family_alert(destination_number: str, call_id: str, verdict: str, message: str) -> dict:
    """
    Send an SMS or WhatsApp alert to a family/emergency contact.
    """
    if verdict != "CRITICAL":
        return {"status": "skipped", "reason": "not critical"}
        
    cfg = get_settings()

    if cfg.sms_backend == "whatsapp" and cfg.whatsapp_phone_number_id and cfg.whatsapp_access_token:
        # Use Meta WhatsApp Business API for real notifications without credit card
        url = f"https://graph.facebook.com/v17.0/{cfg.whatsapp_phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {cfg.whatsapp_access_token}",
            "Content-Type": "application/json"
        }
        # Strip '+' if needed by graph API (though it usually handles it)
        target_number = destination_number.replace("+", "")
        payload = {
            "messaging_product": "whatsapp",
            "to": target_number,
            "type": "text",
            "text": {"body": message}
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                logger.info(f"[WHATSAPP SENT] To: {destination_number} | {message}")
                return {
                    "to": destination_number,
                    "status": "whatsapp_sent",
                    "ts": datetime.utcnow().isoformat(),
                    "provider_response": resp.json()
                }
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            # Fall through to simulated if failed
            
    # Fallback to simulated
    log_entry = {
        "to": destination_number,
        "message": message,
        "status": "simulated",
        "ts": datetime.utcnow().isoformat()
    }
    logger.info(f"[SIMULATED SMS] To: {destination_number} | {message}")
    return log_entry
