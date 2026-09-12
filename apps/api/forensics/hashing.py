"""
forensics/hashing.py — SHA-256 integrity hash of call audio.

Purpose:
  The SHA-256 hash of the full recorded call audio is included in the
  forensic PDF dossier as a chain-of-custody evidence integrity marker.

  If the audio file is later modified (intentionally or by storage corruption),
  the hash will not match, making tampering detectable.

  This is legally significant when submitting to the National Cyber Crime
  Portal (1930) — the hash proves the audio has not been altered since capture.
"""

from __future__ import annotations

import hashlib
import logging
from typing import TypedDict

logger = logging.getLogger(__name__)


class HashResult(TypedDict):
    sha256_hex: str
    size_bytes: int
    size_samples: int  # at 16kHz PCM16: size_bytes / 2
    duration_seconds: float


def compute_audio_hash(pcm16_bytes: bytes, sample_rate: int = 16_000) -> HashResult:
    """
    Compute SHA-256 hash of raw PCM16LE audio bytes.

    Parameters
    ----------
    pcm16_bytes : bytes
        Raw PCM16LE audio bytes (full call recording).
    sample_rate : int
        Sample rate in Hz (default 16kHz). Used only for duration calculation.

    Returns
    -------
    HashResult dict
    """
    if not pcm16_bytes:
        logger.warning("compute_audio_hash: empty audio — returning zero hash")
        return HashResult(
            sha256_hex="0" * 64,
            size_bytes=0,
            size_samples=0,
            duration_seconds=0.0,
        )

    sha256 = hashlib.sha256(pcm16_bytes).hexdigest()
    size_bytes = len(pcm16_bytes)
    size_samples = size_bytes // 2  # PCM16 = 2 bytes per sample
    duration_seconds = size_samples / sample_rate

    logger.info(
        "Audio hash computed: sha256=%s size=%d bytes duration=%.1fs",
        sha256,
        size_bytes,
        duration_seconds,
    )

    return HashResult(
        sha256_hex=sha256,
        size_bytes=size_bytes,
        size_samples=size_samples,
        duration_seconds=duration_seconds,
    )
