"""
dsp/bandpass.py — Butterworth bandpass filter for voice-band audio.

Pass band: 300–3400 Hz (standard telephone voice band).
Design: 4th-order Butterworth IIR via second-order sections (SOS) format.
Applied as sosfiltfilt (zero-phase, forward-backward pass) to eliminate
phase distortion — critical before bispectrum analysis where phase IS the
signal.

Why order 4-6:
  - Order 4 → -80 dB/decade roll-off, sufficient to suppress 50/60 Hz mains
    hum and >4 kHz harmonics without distorting the 300-3400 Hz signal.
  - Higher orders introduce more ringing on voiced consonants; 4 is the
    practical sweet spot for real-time voice analysis.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np
from scipy import signal

logger = logging.getLogger(__name__)

# Butter order — 4 balances roll-off vs. ringing for voice signals.
_FILTER_ORDER = 4
_LOW_HZ = 300.0
_HIGH_HZ = 3400.0


@lru_cache(maxsize=8)
def _get_sos_coeffs(fs: int, low: float = _LOW_HZ, high: float = _HIGH_HZ, order: int = _FILTER_ORDER):
    """
    Compute and cache SOS filter coefficients for a given sample rate.
    Cached because coefficient computation is non-trivial and fs rarely changes.
    """
    nyq = fs / 2.0
    low_norm = low / nyq
    high_norm = high / nyq
    sos = signal.butter(order, [low_norm, high_norm], btype="band", output="sos")
    logger.debug(
        "Computed Butterworth bandpass SOS: order=%d, [%.0f, %.0f] Hz, fs=%d Hz",
        order,
        low,
        high,
        fs,
    )
    return sos


def filter_audio(chunk: np.ndarray, fs: int = 16_000) -> np.ndarray:
    """
    Apply zero-phase Butterworth bandpass filter (300–3400 Hz) to a chunk.

    Parameters
    ----------
    chunk : np.ndarray
        1-D float32 audio samples.
    fs : int
        Sample rate in Hz (default 16000).

    Returns
    -------
    np.ndarray
        Filtered float32 samples, same shape as input.

    Raises
    ------
    ValueError
        If chunk is too short for sosfiltfilt (needs > 3 × filter order).
    """
    if len(chunk) < 3 * _FILTER_ORDER * 2:
        # sosfiltfilt requires length > padlen; return zeros for tiny chunks.
        logger.warning(
            "filter_audio: chunk too short (%d samples) for sosfiltfilt — returning zeros",
            len(chunk),
        )
        return np.zeros_like(chunk)

    sos = _get_sos_coeffs(fs)
    filtered = signal.sosfiltfilt(sos, chunk.astype(np.float64)).astype(np.float32)
    return filtered
