"""
scripts/synthetic_test.py — PDI sanity check with synthetic signals.

Generates two signals:
  1. Phase-coherent signal: sine wave sum with deterministic phase relationships
     → bispectrum should show strong coupling → LOW PDI (human-like)

  2. Phase-randomized signal: same frequency content but random phases
     → bispectrum should show no coupling → HIGH PDI (synthetic-like)

Expected output:
  Coherent PDI  < 0.40  (human-like)
  Incoherent PDI > 0.60 (synthetic-like)

Run from apps/api directory:
  python scripts/synthetic_test.py
"""

from __future__ import annotations

import sys
import os

# Add parent directory to path so imports work when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from dsp.phase_dispersion import compute_pdi

FS = 16_000
DURATION = 0.5  # seconds of signal
N = int(FS * DURATION)

HARMONIC_FREQS = [200 * i for i in range(1, 16)]  # 200 Hz to 3000 Hz


def make_coherent_signal(n: int, fs: int) -> np.ndarray:
    """
    Phase-coherent signal: sum of harmonics with FIXED deterministic phases.
    Mimics human voice glottal excitation — consistent phase relationships.

    A real bispectrum estimator should see strong coupling at triads like
    (200 Hz, 400 Hz, 600 Hz) etc. → low phase dispersion → low PDI.
    """
    t = np.linspace(0, n / fs, n, endpoint=False)
    signal = np.zeros(n, dtype=np.float32)
    for i, freq in enumerate(HARMONIC_FREQS):
        phase = np.pi / 6 * i  # Fixed phase relationship between harmonics
        signal += np.sin(2 * np.pi * freq * t + phase).astype(np.float32)
    signal /= np.max(np.abs(signal) + 1e-9)  # Normalize
    return signal


def make_phase_randomized_signal(n: int, fs: int, rng_seed: int = 42) -> np.ndarray:
    """
    Phase-randomized signal: same frequency content but RANDOM phases.
    Mimics a TTS/deepfake voice with no glottal phase coupling.

    The bispectrum should show random phase angles → high circular variance → high PDI.
    """
    rng = np.random.default_rng(rng_seed)
    t = np.linspace(0, n / fs, n, endpoint=False)
    signal = np.zeros(n, dtype=np.float32)
    for freq in HARMONIC_FREQS:
        phase = rng.uniform(0, 2 * np.pi)  # Random phase per harmonic
        signal += np.sin(2 * np.pi * freq * t + phase).astype(np.float32)
    signal /= np.max(np.abs(signal) + 1e-9)
    return signal


def run_test() -> bool:
    """
    Run the PDI sanity check.
    Returns True if both assertions pass.
    """
    print("=" * 60)
    print("PhaseGuard PDI Sanity Test")
    print(f"  Signal duration: {DURATION}s ({N} samples at {FS} Hz)")
    print(f"  Harmonics: {HARMONIC_FREQS}")
    print("=" * 60)

    # Generate signals
    coherent = make_coherent_signal(N, FS)
    incoherent = make_phase_randomized_signal(N, FS)

    print("\n[1/2] Computing PDI for phase-COHERENT signal (expect: PDI < 0.40)…")
    coherent_result = compute_pdi(coherent, fs=FS)
    print(f"      PDI = {coherent_result['pdi_score']:.4f}  |  is_synthetic={coherent_result['is_synthetic']}")
    print(f"      Triads analysed: {coherent_result['n_triads_analysed']}")
    print(f"      Compute time: {coherent_result['compute_time_ms']:.1f} ms")

    print("\n[2/2] Computing PDI for phase-RANDOMIZED signal (expect: PDI > 0.60)…")
    incoherent_result = compute_pdi(incoherent, fs=FS)
    print(f"      PDI = {incoherent_result['pdi_score']:.4f}  |  is_synthetic={incoherent_result['is_synthetic']}")
    print(f"      Triads analysed: {incoherent_result['n_triads_analysed']}")
    print(f"      Compute time: {incoherent_result['compute_time_ms']:.1f} ms")

    print("\n" + "=" * 60)
    print("ASSERTIONS:")

    passed = True

    # Assertion 1: coherent signal should have lower PDI than incoherent
    if coherent_result["pdi_score"] < incoherent_result["pdi_score"]:
        print(f"  V PASS: Coherent PDI ({coherent_result['pdi_score']:.4f}) < "
              f"Incoherent PDI ({incoherent_result['pdi_score']:.4f})")
    else:
        print(f"  X FAIL: Expected coherent PDI < incoherent PDI")
        print(f"         Got: {coherent_result['pdi_score']:.4f} vs {incoherent_result['pdi_score']:.4f}")
        passed = False

    # Assertion 2: incoherent signal should be flagged as synthetic
    if incoherent_result["is_synthetic"]:
        print(f"  V PASS: Phase-randomized signal correctly flagged as SYNTHETIC")
    else:
        print(f"  X FAIL: Phase-randomized signal NOT flagged as synthetic "
              f"(PDI={incoherent_result['pdi_score']:.4f}, threshold={incoherent_result['threshold_used']})")
        passed = False

    print("=" * 60)
    if passed:
        print("ALL ASSERTIONS PASSED — DSP pipeline is correctly functioning V")
    else:
        print("SOME ASSERTIONS FAILED — review bispectrum/PDI parameters")

    return passed


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
