"""
factcheck/stt.py — Speech-to-text ingestion via Groq Whisper.

Design:
  - A third AudioBufferManager consumer ("stt") accumulates audio until a
    configurable utterance chunk size is reached (default 3-5 seconds).
  - Silence gating: skip sending all-zero (silent) chunks to avoid wasting
    Groq API calls on silence.
  - Groq Whisper (whisper-large-v3) handles Hindi and English natively;
    code-switching/Hinglish is handled reasonably well by the model.
  - For heavily Hindi/non-English audio, language_router.py can redirect
    to Bhashini (Government of India API) or Sarvam AI as a fallback.

Rate limit awareness:
  - Groq Whisper has a free-tier limit (~100 hours/day, ~40 RPM).
  - We gate on minimum chunk size to avoid rapid-fire tiny requests.
  - Exponential backoff on 429 responses.

This module is called from the STT asyncio task in ws/call_socket.py,
which runs on its own cadence independent of bispectrum and tremor loops.
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
import wave
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Minimum audio length before sending to Whisper (seconds)
_MIN_CHUNK_SECONDS = 3.0
# Maximum (send anyway to avoid unbounded accumulation)
_MAX_CHUNK_SECONDS = 5.0
# Silence threshold: RMS below this → skip Whisper call
_SILENCE_RMS_THRESHOLD = 0.005


def _float32_to_wav_bytes(audio: np.ndarray, fs: int = 16_000) -> bytes:
    """Convert float32 numpy array to WAV bytes (PCM16) for Whisper upload."""
    pcm16 = (audio * 32768.0).clip(-32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(fs)
        wf.writeframes(pcm16.tobytes())
    return buf.getvalue()


def _is_silent(audio: np.ndarray, threshold: float = _SILENCE_RMS_THRESHOLD) -> bool:
    """Return True if the audio chunk is effectively silent (save API calls)."""
    rms = float(np.sqrt(np.mean(audio ** 2)))
    return rms < threshold


async def transcribe_chunk(
    audio: np.ndarray,
    fs: int = 16_000,
    language: Optional[str] = None,
    call_id: str = "",
) -> Optional[str]:
    """
    Send an audio chunk to Groq Whisper for transcription.

    Parameters
    ----------
    audio : np.ndarray
        Float32 audio chunk (mono, fs Hz).
    fs : int
        Sample rate.
    language : str or None
        ISO language code hint ('hi' for Hindi, 'en' for English, None = auto).
        Auto-detection is used when language_router hasn't determined the language.
    call_id : str
        For logging only.

    Returns
    -------
    str or None
        Transcribed text, or None if silent / API error.
    """
    if _is_silent(audio):
        logger.debug("STT: silent chunk skipped for call_id=%r", call_id)
        return None

    from core.config import get_settings
    cfg = get_settings()

    if not cfg.groq_api_key:
        logger.warning("STT: GROQ_API_KEY not set — transcription unavailable")
        return None

    from groq import AsyncGroq, RateLimitError

    client = AsyncGroq(api_key=cfg.groq_api_key)
    wav_bytes = _float32_to_wav_bytes(audio, fs)

    # Exponential backoff for Groq rate limits
    max_retries = 3
    backoff = 1.0

    for attempt in range(max_retries):
        try:
            transcription = await client.audio.transcriptions.create(
                file=("audio.wav", wav_bytes, "audio/wav"),
                model=cfg.groq_stt_model,
                response_format="text",
                language=language,  # None = auto-detect
                temperature=0.0,    # Deterministic for forensic reliability
            )
            text = transcription.strip() if transcription else ""
            logger.info("STT[%s]: %r (attempt %d)", call_id, text[:80], attempt + 1)
            return text if text else None

        except RateLimitError:
            if attempt < max_retries - 1:
                logger.warning(
                    "STT: Groq rate limit hit (attempt %d/%d), backing off %.1fs",
                    attempt + 1,
                    max_retries,
                    backoff,
                )
                await asyncio.sleep(backoff)
                backoff *= 2.0
            else:
                logger.error("STT: Groq rate limit — all retries exhausted for call_id=%r", call_id)
                return None

        except Exception as exc:
            logger.error("STT: Whisper API error for call_id=%r: %s", call_id, exc)
            return None

    return None


class STTAccumulator:
    """
    Manages utterance-level audio accumulation for STT.

    The STT task calls get_utterance_chunk() periodically; it returns audio
    only when enough has accumulated (avoiding spamming Whisper with 100ms chunks).
    """

    def __init__(self, fs: int = 16_000) -> None:
        self._fs = fs
        self._min_samples = int(_MIN_CHUNK_SECONDS * fs)
        self._max_samples = int(_MAX_CHUNK_SECONDS * fs)
        self._accumulated: list[np.ndarray] = []
        self._total_samples: int = 0

    def add(self, chunk: np.ndarray) -> None:
        """Add an audio chunk to the accumulator."""
        self._accumulated.append(chunk)
        self._total_samples += len(chunk)

    def ready(self) -> bool:
        """Return True if enough audio has accumulated for a Whisper call."""
        return self._total_samples >= self._min_samples

    def get_chunk(self) -> Optional[np.ndarray]:
        """
        Return the accumulated audio if ready, and reset the accumulator.
        Returns None if not yet ready.
        """
        if not self.ready():
            return None
        audio = np.concatenate(self._accumulated)
        # Trim to max length to avoid very long segments
        if len(audio) > self._max_samples:
            audio = audio[: self._max_samples]
        self._accumulated = []
        self._total_samples = 0
        return audio

    def force_get(self) -> Optional[np.ndarray]:
        """Return whatever has accumulated (used on call end)."""
        if not self._accumulated:
            return None
        audio = np.concatenate(self._accumulated)
        self._accumulated = []
        self._total_samples = 0
        return audio
