"""
ingestion/browser_mic.py — Browser microphone audio ingestion adapter.

Handles the binary WebSocket frame path:
  - Client buffers 128-sample AudioWorklet quanta and flushes every 20-50ms
    as ONE binary frame (never sends per 128-sample callback).
  - This module accepts those frames, validates them, and pushes PCM16LE
    bytes into the call's AudioBufferManager.

WebSocket chattiness fix (§1.2):
  AudioWorkletNode emits 128-sample quanta natively at ~125 msgs/sec.
  The client MUST buffer and flush every 20-50ms (320-800 samples) as one
  frame — this module enforces that by logging a warning if very small
  frames arrive, but still ingests them to avoid data loss.
"""

from __future__ import annotations

import logging
from typing import Optional

from dsp.audio_buffer import AudioBufferManager

logger = logging.getLogger(__name__)

# Warn if a frame is suspiciously small (client-side buffering not working).
_MIN_EXPECTED_FRAME_BYTES = 320 * 2  # 320 samples × 2 bytes/sample = 640 bytes


class BrowserMicIngestion:
    """
    Adapter for the browser-mic ingestion path.

    One instance per active call; feeds the call's shared AudioBufferManager.
    """

    def __init__(self, call_id: str, buffer: AudioBufferManager) -> None:
        self.call_id = call_id
        self._buffer = buffer
        self._total_bytes_ingested = 0
        self._frame_count = 0

    def ingest_frame(self, raw_bytes: bytes) -> int:
        """
        Accept a binary PCM16LE frame from the browser WebSocket and push it
        into the AudioBufferManager.

        Parameters
        ----------
        raw_bytes : bytes
            Raw PCM16LE audio (mono, 16 kHz assumed).

        Returns
        -------
        int
            Number of samples ingested.
        """
        if not raw_bytes:
            logger.debug("Browser mic: empty frame received for call_id=%r", self.call_id)
            return 0

        if len(raw_bytes) < _MIN_EXPECTED_FRAME_BYTES:
            logger.warning(
                "Browser mic: very small frame (%d bytes) for call_id=%r. "
                "Client may not be buffering properly — should flush every 20-50ms. "
                "Data will still be ingested.",
                len(raw_bytes),
                self.call_id,
            )

        if len(raw_bytes) % 2 != 0:
            # PCM16 must be an even number of bytes; truncate last byte.
            logger.warning(
                "Browser mic: odd byte count (%d) for call_id=%r — truncating last byte",
                len(raw_bytes),
                self.call_id,
            )
            raw_bytes = raw_bytes[:-1]

        n_samples = self._buffer.ingest(raw_bytes)
        self._total_bytes_ingested += len(raw_bytes)
        self._frame_count += 1

        logger.debug(
            "Browser mic: ingested %d samples (frame #%d, total_bytes=%d) for call_id=%r",
            n_samples,
            self._frame_count,
            self._total_bytes_ingested,
            self.call_id,
        )
        return n_samples

    def stats(self) -> dict:
        return {
            "call_id": self.call_id,
            "total_bytes": self._total_bytes_ingested,
            "frame_count": self._frame_count,
        }
