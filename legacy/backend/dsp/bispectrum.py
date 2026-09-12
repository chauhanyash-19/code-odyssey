"""
dsp/bispectrum.py — Bispectrum estimator for voice deepfake detection.

Theory:
  The bispectrum B(f1, f2) = E[X(f1) · X(f2) · X*(f1+f2)] is the Fourier
  transform of the third-order cumulant.  For a truly linear Gaussian process
  (e.g., many speech synthesis vocoders), the bispectrum is theoretically zero.
  Real human speech has non-Gaussian statistics from the glottal excitation
  source, producing measurable phase coupling across harmonic triads.

  Deepfake/TTS voices generated via neural vocoders (WaveNet, HiFi-GAN, etc.)
  tend to have either (a) over-regularised phase statistics (too coherent) or
  (b) residual artefacts from vocoder windowing — both detectable via the Phase
  Dispersion Index computed in phase_dispersion.py.

Window size rationale:
  *** DO NOT reduce this to 128 samples. ***
  A 128-sample FFT at 16 kHz gives Δf = 16000/128 ≈ 125 Hz frequency
  resolution.  The harmonic spacing of a 100 Hz fundamental is 100 Hz, which
  is barely above the bin size — adjacent harmonic bins can't be resolved.
  At 512 samples: Δf ≈ 31 Hz — clear harmonic separation even at low F0.
  At 1024 samples: Δf ≈ 15 Hz — optimal but adds latency.
  512 is the recommended minimum for meaningful phase-triad analysis in the
  300–3400 Hz band.
"""

from __future__ import annotations

import logging
import time
from typing import TypedDict

import numpy as np

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
# Specification: 512-sample window, Hann-windowed, 50% overlap.
# DO NOT USE 128 SAMPLES — see module docstring above.
WINDOW_SAMPLES = 512
HOP_SAMPLES = 256  # 50% overlap


class BispectrumResult(TypedDict):
    bispectrum_matrix: np.ndarray  # Complex array shape (N//2, N//2)
    frequencies: np.ndarray  # Frequency bins corresponding to matrix axes
    compute_time_ms: float


def compute_bispectrum(window: np.ndarray, fs: int = 16_000) -> BispectrumResult:
    """
    Compute the direct bispectrum estimator for a single windowed frame.

    The direct estimator: B(f1,f2) = X(f1) * X(f2) * conj(X(f1+f2))
    where X(f) is the DFT of the Hann-windowed input.

    Parameters
    ----------
    window : np.ndarray
        Audio frame of length WINDOW_SAMPLES (512) samples, float32.
        If shorter, will be zero-padded; if longer, will be truncated.
    fs : int
        Sample rate in Hz.

    Returns
    -------
    BispectrumResult
        bispectrum_matrix : complex ndarray (N//2, N//2)
        frequencies       : real ndarray (N//2,)
        compute_time_ms   : wall-clock time for this call
    """
    t0 = time.perf_counter()

    N = WINDOW_SAMPLES
    # Ensure correct length
    if len(window) < N:
        window = np.pad(window, (0, N - len(window)))
    elif len(window) > N:
        window = window[:N]

    # Apply Hann window to reduce spectral leakage
    hann = np.hanning(N)
    windowed = window.astype(np.float64) * hann

    # DFT (only positive frequencies: DC to Nyquist)
    X = np.fft.rfft(windowed, n=N)  # shape: (N//2 + 1,)
    M = N // 2 + 1  # number of positive-frequency bins

    # Frequency axis
    freqs = np.fft.rfftfreq(N, d=1.0 / fs)  # shape: (M,)

    # Direct bispectrum estimator: B(f1, f2) = X(f1) * X(f2) * conj(X(f1+f2))
    # Only compute the principal domain: f1 >= 0, f2 >= f1, f1+f2 <= Nyquist
    # Using broadcasting for efficiency:
    #   B[i, j] = X[i] * X[j] * conj(X[i+j])  for i+j < M
    B = np.zeros((M, M), dtype=np.complex128)

    for i in range(M):
        max_j = M - i  # constraint: i + j < M
        if max_j <= 0:
            break
        j_range = np.arange(max_j)
        B[i, j_range] = X[i] * X[j_range] * np.conj(X[i + j_range])

    dt_ms = (time.perf_counter() - t0) * 1000.0

    if dt_ms > 150.0:
        logger.warning(
            "compute_bispectrum exceeded 150ms budget: %.1f ms — "
            "consider reducing WINDOW_SAMPLES or pre-filtering",
            dt_ms,
        )

    return {
        "bispectrum_matrix": B,
        "frequencies": freqs,
        "compute_time_ms": dt_ms,
    }
