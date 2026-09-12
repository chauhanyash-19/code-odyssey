"""
dsp/micro_tremor.py — Physiological micro-tremor detection (8–12 Hz VSA).

Micro-tremor background:
  Human voice production involves involuntary neurological micro-tremor from
  the laryngeal musculature, typically in the 8–12 Hz band (Titze 1994,
  Baken & Orlikoff 2000).  Under cognitive load or emotional stress, tremor
  energy in this band increases.  Synthetic/TTS voices have NO physiological
  tremor — they are generated from a static neural model that lacks any
  biologically-driven modulation at these frequencies.

Why a LONGER window than bispectrum:
  *** DO NOT use the same 32ms bispectrum window here. ***
  To resolve tremor at 8 Hz vs. 12 Hz we need sub-Hz FFT resolution:
    Δf = fs / N → we need Δf ≤ 1 Hz → N ≥ fs = 16000 samples → ≥ 1 second.
  At Δf = 0.67 Hz (1.5 s window) we can clearly distinguish 8 Hz (bin 12)
  from 9 Hz (bin 13.5) etc.  A 32ms window gives Δf=31 Hz — the entire
  8–12 Hz band fits in a single bin: useless for tremor analysis.

Method:
  1. Apply Hilbert transform to extract the analytic signal.
  2. Compute the instantaneous amplitude envelope (Hilbert envelope).
  3. Bandpass the envelope to the tremor band (6–14 Hz for margin).
  4. Compute FFT of the filtered envelope.
  5. Tremor energy = sum of power spectral density in the 8–12 Hz sub-band.
  6. Normalise against total envelope power → tremor_energy in [0, 1].

Output:
  tremor_energy ≈ 0.0 → flat amplitude envelope → likely synthetic
  tremor_energy ≈ 0.5+ → modulated envelope → possible genuine tremor
  has_tremor: True if tremor_energy > threshold (default 0.15)
"""

from __future__ import annotations

import logging
import time
from typing import TypedDict

import numpy as np
from scipy import signal

logger = logging.getLogger(__name__)

_TREMOR_LOW_HZ = 8.0
_TREMOR_HIGH_HZ = 12.0
_ENVELOPE_FILTER_LOW = 6.0   # slightly wider band for envelope extraction
_ENVELOPE_FILTER_HIGH = 14.0
_TREMOR_THRESHOLD = 0.15


class TremorResult(TypedDict):
    tremor_energy: float     # 0–1, normalised tremor band energy
    has_tremor: bool         # True if tremor_energy > threshold
    peak_tremor_hz: float    # Frequency of peak energy in 8–12 Hz band
    compute_time_ms: float


def compute_tremor_score(
    window: np.ndarray,
    fs: int = 16_000,
    threshold: float = _TREMOR_THRESHOLD,
) -> TremorResult:
    """
    Compute physiological micro-tremor score from a 1–2 second audio window.

    *** Minimum window: 1 second (16000 samples at 16kHz). ***
    See module docstring for the resolution rationale.

    Parameters
    ----------
    window : np.ndarray
        Float32 audio, ideally 1.5–2 s (24000–32000 samples at 16 kHz).
    fs : int
        Sample rate in Hz.
    threshold : float
        Normalised tremor energy above which has_tremor=True.

    Returns
    -------
    TremorResult dict
    """
    t0 = time.perf_counter()

    min_samples = fs  # 1 second minimum — see docstring
    if len(window) < min_samples:
        logger.warning(
            "compute_tremor_score: window too short (%d samples, need ≥%d). "
            "Sub-Hz resolution not achievable — result unreliable.",
            len(window),
            min_samples,
        )

    x = window.astype(np.float64)

    # Step 1: Hilbert transform → analytic signal
    analytic = signal.hilbert(x)

    # Step 2: Instantaneous amplitude envelope
    envelope = np.abs(analytic)  # shape: (N,)

    # Step 3: Decimate to ~200 Hz
    decimate_factor = max(1, fs // 200)
    envelope_ds = signal.decimate(envelope, decimate_factor, zero_phase=True)
    fs_ds = fs // decimate_factor

    # Step 4: Remove DC from the downsampled envelope
    envelope_ds -= envelope_ds.mean()

    # Step 5: Direct FFT of the envelope
    N_ds = len(envelope_ds)
    windowed = envelope_ds * np.hanning(N_ds)
    fft_env = np.fft.rfft(windowed, n=N_ds)
    psd = np.abs(fft_env) ** 2
    freqs_ds = np.fft.rfftfreq(N_ds, d=1.0 / fs_ds)

    # Step 6: Tremor energy = PSD sum in [8–12 Hz] / PSD sum in physiological AC band [1-20 Hz]
    valid_mask = (freqs_ds >= 1.0) & (freqs_ds <= 20.0)
    tremor_mask = (freqs_ds >= _TREMOR_LOW_HZ) & (freqs_ds <= _TREMOR_HIGH_HZ)
    
    total_valid_power = psd[valid_mask].sum()
    tremor_power = psd[tremor_mask].sum()

    if total_valid_power < 1e-12:
        tremor_energy = 0.0
        peak_hz = 0.0
    else:
        tremor_energy = float(np.clip(tremor_power / total_valid_power, 0.0, 1.0))
        if tremor_mask.any() and psd[tremor_mask].size > 0:
            peak_hz = float(freqs_ds[tremor_mask][np.argmax(psd[tremor_mask])])
        else:
            peak_hz = 0.0

    has_tremor = tremor_energy > threshold
    dt_ms = (time.perf_counter() - t0) * 1000.0

    logger.debug(
        "Tremor energy=%.4f (has_tremor=%s, peak=%.1f Hz), compute=%.1f ms",
        tremor_energy,
        has_tremor,
        peak_hz,
        dt_ms,
    )

    return TremorResult(
        tremor_energy=tremor_energy,
        has_tremor=has_tremor,
        peak_tremor_hz=peak_hz,
        compute_time_ms=dt_ms,
    )
