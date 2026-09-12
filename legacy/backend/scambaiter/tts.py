"""
scambaiter/tts.py — Text-to-speech for scambaiter audio responses.

Supports multiple TTS backends (configurable via TTS_BACKEND env var):
  - "gtts"        : gTTS (Google TTS, free, requires internet, no key)
  - "elevenlabs"  : ElevenLabs API (best quality, requires key)
  - "google"      : Google Cloud TTS (requires GCP credentials)
  - "mock"        : Returns silence bytes (for testing without TTS credentials)

For an Indian-market deployment, gTTS is the pragmatic default:
  - Free, no API key required
  - Supports Hindi (lang='hi') for authentic-sounding scambaiter responses
  - Adequate quality for a demo; upgrade to ElevenLabs for production

Audio output: PCM16LE bytes at 16kHz mono (same format as the ingestion pipeline),
ready to be sent back over the call's outbound audio path.
"""

from __future__ import annotations

import io
import logging
import os
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_TTS_BACKEND = os.getenv("TTS_BACKEND", "gtts")
_TTS_LANGUAGE = os.getenv("TTS_LANGUAGE", "hi")  # Hindi default for India-market


async def synthesize_speech(text: str, call_id: str = "") -> Optional[bytes]:
    """
    Convert text to PCM16LE audio bytes.

    Parameters
    ----------
    text : str
        Text to synthesize (scambaiter response).
    call_id : str
        For logging.

    Returns
    -------
    bytes or None
        PCM16LE audio at 16kHz mono, or None on failure.
    """
    backend = _TTS_BACKEND.lower()
    logger.info("TTS[%s]: backend=%r text=%r", call_id, backend, text[:60])

    if backend == "gtts":
        return await _gtts_synthesize(text)
    elif backend == "elevenlabs":
        return await _elevenlabs_synthesize(text)
    elif backend == "google":
        return await _gcloud_tts_synthesize(text)
    elif backend == "mock":
        return _mock_silence(duration_seconds=2.0)
    else:
        logger.warning("TTS: unknown backend %r — falling back to gTTS", backend)
        return await _gtts_synthesize(text)


async def _gtts_synthesize(text: str) -> Optional[bytes]:
    """
    Synthesize via gTTS (free, no key).
    Returns PCM16LE bytes resampled to 16kHz.
    """
    try:
        import asyncio
        from gtts import gTTS  # type: ignore[import]
        import io as _io
        import wave

        def _sync_gtts() -> bytes:
            tts = gTTS(text=text, lang=_TTS_LANGUAGE, slow=True)
            mp3_buf = _io.BytesIO()
            tts.write_to_fp(mp3_buf)
            return mp3_buf.getvalue()

        loop = asyncio.get_running_loop()
        # gTTS is synchronous — run in executor
        from workers.executor import run_in_dsp_executor
        mp3_bytes = await run_in_dsp_executor(_sync_gtts)

        # Convert MP3 → PCM16LE via pydub (if available) or return raw
        try:
            from pydub import AudioSegment  # type: ignore[import]

            segment = AudioSegment.from_mp3(_io.BytesIO(mp3_bytes))
            segment = segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            return segment.raw_data
        except ImportError:
            # pydub not installed — return MP3 bytes with a warning
            logger.warning("pydub not installed — returning MP3 bytes from gTTS, not PCM16LE")
            return mp3_bytes

    except Exception as exc:
        logger.error("gTTS synthesis failed: %s", exc)
        return None


async def _elevenlabs_synthesize(text: str) -> Optional[bytes]:
    """
    Synthesize via ElevenLabs API.
    Requires ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID env vars.
    """
    import httpx

    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # default voice

    if not api_key:
        logger.warning("ElevenLabs: ELEVENLABS_API_KEY not set — falling back to gTTS")
        return await _gtts_synthesize(text)

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={"xi-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.6, "similarity_boost": 0.7},
                },
            )
            response.raise_for_status()
            audio_bytes = response.content

            # ElevenLabs returns MP3; convert to PCM16LE
            try:
                from pydub import AudioSegment
                import io as _io

                segment = AudioSegment.from_mp3(_io.BytesIO(audio_bytes))
                segment = segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)
                return segment.raw_data
            except ImportError:
                return audio_bytes

    except Exception as exc:
        logger.error("ElevenLabs synthesis failed: %s", exc)
        return None


async def _gcloud_tts_synthesize(text: str) -> Optional[bytes]:
    """
    Synthesize via Google Cloud Text-to-Speech API.
    Requires GCP credentials (GOOGLE_APPLICATION_CREDENTIALS env var).
    """
    try:
        import asyncio
        from google.cloud import texttospeech  # type: ignore[import]

        def _sync_gcloud() -> bytes:
            client = texttospeech.TextToSpeechClient()
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="hi-IN",
                ssml_gender=texttospeech.SsmlVoiceGender.MALE,
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
            )
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            return response.audio_content  # PCM16LE bytes, already at 16kHz

        from workers.executor import run_in_dsp_executor
        return await run_in_dsp_executor(_sync_gcloud)

    except Exception as exc:
        logger.error("Google Cloud TTS failed: %s", exc)
        return None


def _mock_silence(duration_seconds: float = 2.0, fs: int = 16_000) -> bytes:
    """Return PCM16LE silence bytes (for testing without TTS credentials)."""
    n_samples = int(duration_seconds * fs)
    return np.zeros(n_samples, dtype=np.int16).tobytes()
