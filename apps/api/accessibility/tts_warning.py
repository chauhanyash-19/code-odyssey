"""
accessibility/tts_warning.py — TTS spoken warnings for the protected user.

Design:
  - On CRITICAL verdict, plays a short spoken warning to the PROTECTED USER.
  - Keeps the phrase set configurable per language (Hindi/English).
  - IMPORTANT: This audio path MUST be strictly separated from the scambaiter's
    outbound TTS path. Scambaiter audio goes TO the scammer; this warning
    goes TO the protected user (e.g., played locally on their device speaker).
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Pre-defined warning phrases
WARNING_PHRASES = {
    "en": "Warning. This call has been identified as a potential scam. Do not share personal information or make payments.",
    "hi": "चेतावनी। यह कॉल एक संभावित घोटाला (scam) है। कृपया अपनी निजी जानकारी साझा न करें और कोई भुगतान न करें।"
}

async def generate_warning_audio(language: str = "hi") -> Optional[bytes]:
    """
    Generate spoken warning audio using TTS API.
    
    Returns raw audio bytes (mp3 or pcm) that the client should play locally
    to warn the protected user.
    """
    phrase = WARNING_PHRASES.get(language, WARNING_PHRASES["en"])
    logger.info("Generating spoken warning in %s: %s", language, phrase)
    
    from core.config import get_settings
    cfg = get_settings()
    
    # We use gtts as a default/fallback since it doesn't strictly require an API key
    try:
        from gtts import gTTS
        import io
        
        tts = gTTS(text=phrase, lang=language)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        audio_bytes = fp.getvalue()
        return audio_bytes
    except Exception as exc:
        logger.error("Failed to generate TTS warning: %s", exc)
        return None
