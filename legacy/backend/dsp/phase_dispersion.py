"""
dsp/phase_dispersion.py — Phase Dispersion Index (PDI) from bispectrum.

The PDI quantifies how "random" the phase coupling is across harmonic triads
(f1, f2, f1+f2).

Human voice:
  - Glottal excitation produces consistent non-linear phase coupling
    across harmonics → bispectrum phase angles cluster → LOW PDI

Synthetic/deepfake voice:
  - Neural vocoders (WaveNet, HiFi-GAN) tend to either over-regularise phase
    (too coherent, detectable as anomalously LOW variance vs. natural speech)
    or produce incoherent phase artefacts (HIGH variance).
  - PDI is calibrated so that either extreme can be flagged; the default
    threshold (0.6) targets the HIGH-variance case (phase-randomised synthesis).

Computation:
  1. Extract bispectrum phase angles for all (f1, f2) pairs in the principal
     domain where |B(f1,f2)| > amplitude_threshold (ignore noise floor).
  2. Compute circular variance of those phase angles:
       Var_circ = 1 - |mean(exp(i·θ))|
     This is 0 for perfectly coherent phase, 1 for uniformly random phase.
  3. Normalise to 0–1.  PDI = circular_variance.

Output:
  PDI ≈ 0.0 → strong phase coupling → more likely human
  PDI ≈ 1.0 → random/incoherent phases → more likely synthetic
"""

from __future__ import annotations

import logging
import time
from typing import TypedDict

import numpy as np

from dsp.bandpass import filter_audio
from dsp.bispectrum import compute_bispectrum

logger = logging.getLogger(__name__)

# Minimum bispectrum magnitude to include a triad in the PDI calculation.
# Below this threshold we're looking at noise floor, not a real triad.
_AMP_THRESHOLD_PERCENTILE = 70  # use top 30% amplitude triads


class PDIResult(TypedDict):
    pdi_score: float          # 0–1, higher → more synthetic
    is_synthetic: bool        # True if pdi_score > threshold
    threshold_used: float
    n_triads_analysed: int
    compute_time_ms: float


def compute_pdi(
    window: np.ndarray,
    fs: int = 16_000,
    threshold: float = 0.6,
) -> PDIResult:
    """
    Compute the Phase Dispersion Index for one audio window.

    Parameters
    ----------
    window : np.ndarray
        Audio frame (ideally 512 samples, float32).  Will be bandpass-filtered
        internally before bispectrum computation.
    fs : int
        Sample rate in Hz.
    threshold : float
        PDI score above which the voice is classified as synthetic (0–1).
        Default 0.6 from config; overridable per-call.

    Returns
    -------
    PDIResult dict
    """
    t0 = time.perf_counter()

    # 1. Bandpass-filter to voice band (300–3400 Hz) before bispectrum.
    filtered = filter_audio(window, fs=fs)

    # 2. Compute bispectrum matrix.
    bispec = compute_bispectrum(filtered, fs=fs)
    B = bispec["bispectrum_matrix"]

    # 3. Extract amplitudes; select triads above noise floor.
    magnitudes = np.abs(B)
    if magnitudes.max() == 0:
        # All-zero — no signal, return uncertain mid-PDI
        logger.warning("compute_pdi: all-zero bispectrum (silence?) — returning PDI=0.5")
        return PDIResult(
            pdi_score=0.5,
            is_synthetic=False,
            threshold_used=threshold,
            n_triads_analysed=0,
            compute_time_ms=(time.perf_counter() - t0) * 1000.0,
        )

    amp_threshold = magnitudes.max() * 0.01  # Top 1% relative to peak to avoid noise
    mask = magnitudes > amp_threshold

    n_triads = int(mask.sum())
    if n_triads == 0:
        logger.warning("compute_pdi: no triads above amplitude threshold — returning PDI=0.5")
        return PDIResult(
            pdi_score=0.5,
            is_synthetic=False,
            threshold_used=threshold,
            n_triads_analysed=0,
            compute_time_ms=(time.perf_counter() - t0) * 1000.0,
        )

    # 4. Extract phase angles for selected triads.
    phases = np.angle(B[mask])  # radians in [-π, π]

    # 5. Circular variance = 1 - |mean(exp(i·θ))|
    # This is 0 for all phases identical (perfect coupling), 1 for uniform random.
    mean_resultant = np.abs(np.mean(np.exp(1j * phases)))
    circular_variance = 1.0 - mean_resultant  # [0, 1]

    # 6. PDI = circular_variance (already 0–1; no additional scaling needed).
    pdi_score = float(np.clip(circular_variance, 0.0, 1.0))
    is_synthetic = pdi_score > threshold

    dt_ms = (time.perf_counter() - t0) * 1000.0
    if dt_ms > 150.0:
        logger.warning("compute_pdi exceeded 150ms budget: %.1f ms", dt_ms)

    logger.debug(
        "PDI=%.4f (synthetic=%s), triads=%d, compute=%.1f ms",
        pdi_score,
        is_synthetic,
        n_triads,
        dt_ms,
    )

    return PDIResult(
        pdi_score=pdi_score,
        is_synthetic=is_synthetic,
        threshold_used=threshold,
        n_triads_analysed=n_triads,
        compute_time_ms=dt_ms,
    )
