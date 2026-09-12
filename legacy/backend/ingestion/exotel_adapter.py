"""
ingestion/exotel_adapter.py — Real phone call audio ingestion via Exotel/Twilio.

Why Exotel (§1.7):
  Browser mic capture (AudioWorkletNode) only works for browser-based calls or
  audio played into a microphone. It does NOT intercept a real GSM/VoIP call.

  Exotel (Indian CPaaS, INR billing) and Twilio (global CPaaS) both allow
  real inbound/outbound phone calls to be bridged programmatically, streaming
  live call audio to your WebSocket server via webhooks.

  This is PURE API integration — no SIM box, no physical phone, no telecom
  hardware. Exotel is the preferred choice for the Indian market because:
    - Indian company, Indian number provisioning
    - Built for TRAI compliance
    - IVR/call-recording product line judges may already recognize
    - INR pricing and local support

Architecture:
  Exotel sends audio chunks to a webhook HTTP endpoint on this server.
  Each chunk is a small PCM/mulaw audio payload (typically 160–320 bytes).
  This adapter converts mulaw→PCM16LE (if needed) and feeds the same
  AudioBufferManager used by the browser-mic path.

  Both ingestion paths (browser_mic + exotel) feed ONE shared pipeline —
  the DSP engine, fact-checker, and forensics layers are identical regardless
  of audio source.  The active ingestion mode is selected via config.

Twilio Media Streams:
  Twilio streams audio as base64-encoded mulaw (8kHz) in JSON payloads over
  a WebSocket.  The ExotelAdapter also handles Twilio's format when
  INGESTION_MODE=twilio is set.  Audio is resampled from 8kHz→16kHz.
"""

from __future__ import annotations

import audioop  # mulaw decode (stdlib, available in Python 3.11)
import base64
import logging
from typing import Optional

import numpy as np
from scipy.signal import resample_poly

from dsp.audio_buffer import AudioBufferManager

logger = logging.getLogger(__name__)


class ExotelAdapter:
    """
    Ingestion adapter for Exotel Voice Streaming and Twilio Media Streams.

    Both APIs stream live call audio as small mulaw-encoded payloads.
    This adapter:
      1. Decodes mulaw → PCM16LE
      2. Resamples from 8kHz → 16kHz (if source is 8kHz)
      3. Pushes float32 into the shared AudioBufferManager

    One instance per active call.
    """

    def __init__(
        self,
        call_id: str,
        buffer: AudioBufferManager,
        source_sample_rate: int = 8000,
        target_sample_rate: int = 16000,
    ) -> None:
        self.call_id = call_id
        self._buffer = buffer
        self._src_fs = source_sample_rate
        self._tgt_fs = target_sample_rate
        self._total_frames = 0

        # Resample ratio (integer up/down)
        from math import gcd
        g = gcd(target_sample_rate, source_sample_rate)
        self._up = target_sample_rate // g
        self._down = source_sample_rate // g

        logger.info(
            "ExotelAdapter init: call_id=%r src_fs=%d target_fs=%d upsample=%d/%d",
            call_id,
            source_sample_rate,
            target_sample_rate,
            self._up,
            self._down,
        )

    # ── Exotel format handler ──────────────────────────────────────────────────

    def ingest_exotel_chunk(self, payload: bytes) -> int:
        """
        Accept a raw audio chunk from an Exotel Voice Streaming webhook.

        Exotel streams PCM16LE at 8kHz by default.
        Configure Exotel to use PCM format in your AppID stream config.

        Parameters
        ----------
        payload : bytes
            Raw PCM16LE audio bytes from Exotel webhook body.

        Returns
        -------
        int
            Number of samples pushed to the buffer.
        """
        if not payload:
            return 0

        # Convert PCM16LE to float32
        pcm16 = np.frombuffer(payload, dtype=np.int16).astype(np.float32) / 32768.0

        # Resample 8kHz → 16kHz
        if self._src_fs != self._tgt_fs:
            pcm16 = resample_poly(pcm16, self._up, self._down).astype(np.float32)

        # Re-encode as PCM16LE bytes for the buffer's ingest() method
        resampled_bytes = (pcm16 * 32768.0).clip(-32768, 32767).astype(np.int16).tobytes()
        n = self._buffer.ingest(resampled_bytes)
        self._total_frames += 1
        return n

    # ── Twilio Media Streams format handler ────────────────────────────────────

    def ingest_twilio_media_event(self, event: dict) -> int:
        """
        Accept a Twilio Media Streams WebSocket JSON event.

        Twilio streams audio as base64-encoded mulaw (PCMU) at 8000 Hz.
        Event format:
            {
                "event": "media",
                "media": {
                    "payload": "<base64-encoded mulaw bytes>",
                    "track": "inbound",
                    ...
                }
            }

        Parameters
        ----------
        event : dict
            Parsed Twilio Media Streams JSON event.

        Returns
        -------
        int
            Number of samples pushed to the buffer, or 0 for non-media events.
        """
        if event.get("event") != "media":
            return 0

        media = event.get("media", {})
        track = media.get("track", "")

        # Only process inbound (caller's voice) — skip outbound (our own TTS)
        if track not in ("inbound", ""):
            return 0

        payload_b64 = media.get("payload", "")
        if not payload_b64:
            return 0

        # Decode base64 → mulaw bytes
        mulaw_bytes = base64.b64decode(payload_b64)

        # Convert mulaw → PCM16LE (linear) using audioop
        try:
            pcm16_bytes = audioop.ulaw2lin(mulaw_bytes, 2)  # 2 = 16-bit output
        except audioop.error as exc:
            logger.warning("mulaw decode failed for call_id=%r: %s", self.call_id, exc)
            return 0

        # Resample and ingest
        return self.ingest_exotel_chunk(pcm16_bytes)

    def stats(self) -> dict:
        return {
            "call_id": self.call_id,
            "total_frames": self._total_frames,
            "src_fs": self._src_fs,
            "tgt_fs": self._tgt_fs,
        }


# ── FastAPI webhook endpoint handlers (to be wired into main.py) ──────────────

async def handle_exotel_stream_webhook(
    call_id: str,
    body: bytes,
    buffer: AudioBufferManager,
) -> dict:
    """
    HTTP POST handler for Exotel Voice Streaming webhook.
    Wire this to POST /exotel/stream/{call_id} in main.py.

    Exotel sends audio chunks as the raw POST body with:
      Content-Type: audio/l16 (PCM16LE) or audio/x-mulaw

    Returns acknowledgement for Exotel.
    """
    adapter = ExotelAdapter(call_id, buffer)
    n = adapter.ingest_exotel_chunk(body)
    return {"status": "ok", "samples_ingested": n}
