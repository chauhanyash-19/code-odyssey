"""
i18n/language_router.py — Hindi/Hinglish detection and routing for India market.

Problem:
  Real Indian scam calls frequently code-switch mid-sentence (Hinglish —
  mixing Hindi and English). A pure English STT/LLM pipeline may miss key
  scam phrases delivered in Hindi or Hinglish.

Solutions implemented here:
  1. Language detection: use langdetect to identify the primary language
     and estimate Hindi/Hinglish presence.
  2. Prompt routing: when Hindi/Hinglish is detected, modify LLM prompts
     to explicitly handle mixed-language input.

Current multilingual approach:
  Hindi/Hinglish is handled through Groq's Whisper STT (natively multilingual)
  + Llama-3.3-70b (handles Hinglish well with the Hinglish system prompt addon).
  This is sufficient for the hackathon demo.

Language detection heuristics:
  langdetect is probabilistic and not perfect for short Hinglish text.
  We use a supplementary Devanagari character check as a reliable signal
  for Hindi script content.
"""

from __future__ import annotations

import logging
import re
from typing import Optional, TypedDict

logger = logging.getLogger(__name__)

# Devanagari Unicode block: U+0900 to U+097F
_DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")

# Common Hinglish scam keywords (Roman script Hindi commonly used in scam calls)
_HINGLISH_SCAM_KEYWORDS = [
    "aadhaar", "paisa", "otp", "upi", "pin", "account", "police",
    "arrested", "CBI", "court", "warrant", "digital arrest", "giraftaar",
    "rupees", "payment", "fake", "fraud", "scam", "cyber", "crime",
    "band", "block", "cancel", "nahin", "kyunki", "aap", "aapka",
]


class LanguageDetectionResult(TypedDict):
    detected_lang: str            # ISO 639-1 code: 'hi', 'en', etc.
    has_devanagari: bool          # True if Devanagari script found
    hinglish_confidence: float    # 0–1 estimate of Hinglish mixing
    recommended_llm_lang: str     # 'en' | 'hi' | 'hinglish'
    stt_language_hint: Optional[str]  # Language hint for Whisper: 'hi', 'en', None


def detect_language(text: str) -> LanguageDetectionResult:
    """
    Detect the language/script mix in a transcript segment.

    Parameters
    ----------
    text : str
        Transcript text (may be Hinglish/mixed).

    Returns
    -------
    LanguageDetectionResult dict
    """
    # Check for Devanagari script (definitive Hindi signal)
    has_devanagari = bool(_DEVANAGARI_PATTERN.search(text))

    # Hinglish keyword count
    text_lower = text.lower()
    keyword_hits = sum(1 for kw in _HINGLISH_SCAM_KEYWORDS if kw in text_lower)
    hinglish_confidence = min(1.0, keyword_hits / max(1, len(_HINGLISH_SCAM_KEYWORDS) * 0.3))

    # langdetect for primary language
    detected_lang = "en"
    try:
        from langdetect import detect, LangDetectException  # type: ignore[import]

        detected_lang = detect(text) if len(text.strip()) > 20 else "en"
    except Exception:
        # langdetect can fail on short/mixed text — fallback to 'en'
        detected_lang = "en"

    # Determine recommended LLM language routing
    if has_devanagari or detected_lang == "hi":
        recommended_llm_lang = "hi"
        stt_hint = "hi"
    elif hinglish_confidence > 0.2:
        recommended_llm_lang = "hinglish"
        stt_hint = "hi"  # Whisper handles Hinglish better when prompted with 'hi'
    else:
        recommended_llm_lang = "en"
        stt_hint = None  # None = auto-detect in Whisper

    logger.debug(
        "Language detection: lang=%r devanagari=%s hinglish_conf=%.2f recommended=%r",
        detected_lang, has_devanagari, hinglish_confidence, recommended_llm_lang,
    )

    return LanguageDetectionResult(
        detected_lang=detected_lang,
        has_devanagari=has_devanagari,
        hinglish_confidence=hinglish_confidence,
        recommended_llm_lang=recommended_llm_lang,
        stt_language_hint=stt_hint,
    )


def get_hinglish_system_prompt_addon() -> str:
    """
    Additional system prompt text to append when Hinglish is detected.
    Instructs the LLM to handle mixed Hindi-English input correctly.
    """
    return (
        "\nIMPORTANT: This transcript may contain Hindi, Hinglish (Hindi-English mix), "
        "or Roman-script Hindi. Parse all languages equally. Key Hindi scam terms to recognize:\n"
        "- 'giraftaar' = arrested, 'warrant' = arrest warrant\n"
        "- 'paisa' = money, 'khata' = account, 'band' = blocked/closed\n"
        "- 'OTP daalo' = enter OTP, 'PIN batao' = share PIN\n"
        "- 'CBI/police/court ne pakad liya' = CBI/police/court has caught [you]\n"
        "Treat Hinglish claims with the same seriousness as English ones."
    )


# ── Bhashini API Integration — NOT WIRED FOR THIS BUILD ───────────────────────
# Bhashini (bhashini.gov.in) is the Government of India's language AI platform.
# It provides free APIs for ASR, translation, and TTS in 22 Indian languages.
# It is a PLANNED FUTURE UPGRADE PATH for deeper Hindi/regional-language support.
#
# CURRENT STATUS: Not wired. Hindi/Hinglish handling currently goes through
# Groq's Whisper STT (natively multilingual) + Llama-3.3-70b (handles
# Hinglish well with the system prompt addon above). This is sufficient for
# the hackathon demo.
#
# TO WIRE IN FUTURE:
#   1. Register at: https://bhashini.gov.in
#   2. Get BHASHINI_USER_ID, BHASHINI_API_KEY, BHASHINI_PIPELINE_ID
#   3. Add those to .env and implement a BhashiniClient class here.
#
# class BhashiniClient: ...  (implementation intentionally removed for this build)


async def get_bhashini_transcription(
    audio_base64: str,
    source_language: str = "hi",
) -> Optional[str]:
    """
    Placeholder: Bhashini transcription is NOT WIRED in this build.
    Hindi/Hinglish is handled by Groq Whisper (native multilingual STT).
    Returns None always — callers should fall through to Groq.
    """
    # NOT WIRED — Bhashini integration is a planned future upgrade.
    # See comment block above for wiring instructions.
    logger.debug("Bhashini: not wired in this build — using Groq native multilingual STT")
    return None
