"""
dsp/audio_buffer.py — Per-call ring buffer with independent read cursors.

Design:
  Each active call owns one AudioBufferManager.  Multiple consumers (bispectrum
  engine, micro-tremor engine, STT accumulator) read from the same underlying
  buffer at different window sizes and on different cadences.

  Key invariant: consumers NEVER step on each other's read positions.
  Each consumer registers a named cursor; get_window() advances only *that*
  cursor and has no effect on any other.

  The ring buffer is a pre-allocated float32 numpy array.  Writes wrap around
  (overwrite oldest data when full).  All cursors must track the absolute
  write head to detect wrap-around and avoid reading future/stale samples.

  PCM16LE → float32 conversion: divide by 32768.0 to normalise to [-1, 1].
  Assumed input: 16 kHz, mono.
"""

from __future__ import annotations

import logging
import threading
from typing import Dict

import numpy as np

logger = logging.getLogger(__name__)

# Default ring buffer capacity: 30 seconds at 16 kHz = 480 000 samples.
_DEFAULT_CAPACITY = 480_000


class AudioBufferManager:
    """
    Thread-safe ring buffer with per-consumer independent read cursors.

    Parameters
    ----------
    capacity : int
        Maximum number of float32 samples to hold in the ring.
    sample_rate : int
        Expected input sample rate (used only for logging/docs).
    """

    def __init__(self, capacity: int = _DEFAULT_CAPACITY, sample_rate: int = 16_000) -> None:
        self._capacity = capacity
        self._sample_rate = sample_rate
        self._buf: np.ndarray = np.zeros(capacity, dtype=np.float32)

        # Absolute write head (never wraps — use modulo for ring indexing).
        self._write_head: int = 0

        # cursors[name] = absolute read position for that consumer.
        self._cursors: Dict[str, int] = {}

        self._lock = threading.Lock()

    # ── Cursor management ──────────────────────────────────────────────────────

    def register_cursor(self, name: str) -> None:
        """
        Register a named read cursor positioned at the current write head.
        Call once per consumer at call-start.
        """
        with self._lock:
            self._cursors[name] = self._write_head
            logger.debug("Cursor %r registered at write_head=%d", name, self._write_head)

    def get_cursor_position(self, name: str) -> int:
        """Return the absolute read position of a cursor (for diagnostics)."""
        with self._lock:
            return self._cursors.get(name, 0)

    def available_samples(self, cursor_name: str) -> int:
        """Return how many unread samples are available for a cursor."""
        with self._lock:
            pos = self._cursors.get(cursor_name, 0)
            return max(0, self._write_head - pos)

    # ── Write ──────────────────────────────────────────────────────────────────

    def ingest(self, pcm16_bytes: bytes) -> int:
        """
        Convert raw PCM16LE bytes to float32 and append to the ring buffer.

        Parameters
        ----------
        pcm16_bytes : bytes
            Raw little-endian 16-bit signed PCM audio (mono, 16 kHz assumed).

        Returns
        -------
        int
            Number of samples ingested in this call.
        """
        # Convert PCM16LE → float32 normalised to [-1.0, 1.0]
        samples = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        n = len(samples)
        if n == 0:
            return 0

        with self._lock:
            for i, s in enumerate(samples):
                idx = (self._write_head + i) % self._capacity
                self._buf[idx] = s
            self._write_head += n

        return n

    # ── Read ───────────────────────────────────────────────────────────────────

    def get_window(self, cursor_name: str, n_samples: int) -> np.ndarray | None:
        """
        Read exactly n_samples from a named cursor's current position.
        Advances the cursor by n_samples.

        Returns None if fewer than n_samples are available.
        Does NOT block — callers should poll or use asyncio.sleep between tries.

        Parameters
        ----------
        cursor_name : str
            Previously registered cursor name.
        n_samples : int
            Number of float32 samples to read.

        Returns
        -------
        numpy.ndarray of shape (n_samples,) dtype float32, or None.
        """
        with self._lock:
            if cursor_name not in self._cursors:
                raise KeyError(f"Cursor {cursor_name!r} not registered. Call register_cursor() first.")

            pos = self._cursors[cursor_name]
            available = self._write_head - pos

            if available < n_samples:
                return None  # Not enough data yet

            # Detect if oldest samples were overwritten (ring wrapped past cursor)
            if available > self._capacity:
                # Cursor is too far behind — jump it forward to the oldest valid sample.
                logger.warning(
                    "Cursor %r overrun detected (available=%d > capacity=%d). "
                    "Advancing cursor to oldest valid sample.",
                    cursor_name,
                    available,
                    self._capacity,
                )
                pos = self._write_head - self._capacity
                self._cursors[cursor_name] = pos

            # Extract samples from ring (may wrap around)
            start = pos % self._capacity
            end = (pos + n_samples) % self._capacity

            if start < end:
                window = self._buf[start:end].copy()
            else:
                # Wrap-around: two slices
                window = np.concatenate([self._buf[start:], self._buf[:end]])

            self._cursors[cursor_name] = pos + n_samples
            return window

    def get_all_available(self, cursor_name: str) -> np.ndarray:
        """
        Read all samples available for a cursor (up to buffer capacity).
        Useful for STT accumulator which grabs variable-length utterances.
        """
        with self._lock:
            if cursor_name not in self._cursors:
                raise KeyError(f"Cursor {cursor_name!r} not registered.")
            pos = self._cursors[cursor_name]
            available = min(self._write_head - pos, self._capacity)
            if available <= 0:
                return np.array([], dtype=np.float32)

        return self.get_window(cursor_name, available) or np.array([], dtype=np.float32)

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def stats(self) -> dict:
        with self._lock:
            return {
                "capacity": self._capacity,
                "write_head": self._write_head,
                "cursors": {k: {"pos": v, "lag": self._write_head - v} for k, v in self._cursors.items()},
            }
