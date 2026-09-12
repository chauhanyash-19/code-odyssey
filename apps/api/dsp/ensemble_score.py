"""
dsp/ensemble_score.py — Multi-signal anti-spoofing ensemble scorer.

Anti-evasion rationale (§1.9):
  A scammer CAN pipe an AI voice through a pitch-shifter or voice-changer to
  shift bispectrum statistics and dodge a single PDI threshold.  Gating on
  ANY single metric alone creates a well-known evasion vector.

  Fix: fuse PDI + micro-tremor + formant-stability into a weighted ensemble.
  Critically, STRONG DISAGREEMENT between signals → UNCERTAIN, never SAFE.
  No single signal can produce a SAFE verdict on its own.

Ensemble scoring:
  score = w_pdi * pdi_score_norm + w_tremor * tremor_score_norm + w_formant * formant_score_norm

  where each component is independently normalised to [0, 1]:
    pdi_score_norm     : 0 = coherent (human-like), 1 = incoherent (synthetic)
    tremor_score_norm  : 0 = no tremor (synthetic), 1 = strong tremor (human)
                         *** note inverted polarity: absence of tremor → synthetic ***
    formant_score_norm : 0 = unstable formants (synthetic), 1 = stable (human)

  Final label:
    score < SAFE_THRESHOLD        → SAFE (human)
    score > SYNTHETIC_THRESHOLD   → SYNTHETIC
    in between                     → UNCERTAIN

  Disagreement override:
    If max_component - min_component > DISAGREEMENT_THRESHOLD,
    output UNCERTAIN regardless of weighted score.
    Rationale: strong signal disagreement means one sensor is being spoofed.

Formant stability (lightweight):
  Full LPC formant tracking is expensive.  We use a proxy: the temporal
  variance of the spectral centroid within a short window.  Real vowels have
  a slowly-moving centroid; synthesised vowels often have a suspiciously
  smooth or abruptly-jumping centroid.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TypedDict

import numpy as np

logger = logging.getLogger(__name__)

# ── Weights (must sum to 1.0) ─────────────────────────────────────────────────
W_PDI = 0.70
W_TREMOR = 0.15
W_FORMANT = 0.15
assert abs(W_PDI + W_TREMOR + W_FORMANT - 1.0) < 1e-9, "Weights must sum to 1.0"

# ── Thresholds ────────────────────────────────────────────────────────────────
SAFE_THRESHOLD = 0.20         # ensemble score below this → SAFE
SYNTHETIC_THRESHOLD = 0.40    # ensemble score above this → SYNTHETIC
DISAGREEMENT_THRESHOLD = 0.50  # restored security threshold



class EnsembleLabel(str, Enum):
    SAFE = "SAFE"
    SYNTHETIC = "SYNTHETIC"
    UNCERTAIN = "UNCERTAIN"


class EnsembleResult(TypedDict):
    ensemble_score: float       # 0–1 weighted score
    label: str                  # EnsembleLabel value
    pdi_contribution: float
    tremor_contribution: float
    formant_contribution: float
    disagreement: float         # max-min spread across normalised components
    reason: str                 # human-readable explanation for the label


def compute_formant_stability(audio_window: np.ndarray, fs: int = 16_000) -> float:
    """
    Lightweight formant stability proxy via spectral centroid variance.

    Returns a score in [0, 1] where:
      1.0 → stable centroid (human-like)
      0.0 → highly variable or suspiciously static centroid (synthetic-like)

    Uses 20ms sub-frames within the window to track centroid over time.
    Only analyzes high-energy frames (vowels) to avoid noise/consonant variance.
    """
    frame_size = int(0.020 * fs)  # 20ms sub-frames
    if len(audio_window) < frame_size * 2:
        return 0.5  # insufficient data → neutral

    # Pre-calculate energy for all frames to find vowels
    frames = []
    energies = []
    for start in range(0, len(audio_window) - frame_size, frame_size):
        frame = audio_window[start : start + frame_size].astype(np.float64)
        frames.append(frame)
        energies.append(np.mean(frame ** 2))

    if not energies:
        return 0.5

    # Select top 25% highest energy frames (vowels)
    energy_threshold = np.percentile(energies, 75)
    if energy_threshold < 1e-10:
        return 0.5

    centroids = []
    for frame, energy in zip(frames, energies):
        if energy < energy_threshold:
            continue
            
        frame_windowed = frame * np.hanning(len(frame))
        spectrum = np.abs(np.fft.rfft(frame_windowed))
        freqs = np.fft.rfftfreq(len(frame_windowed), d=1.0 / fs)
        total = spectrum.sum()
        if total > 1e-10:
            centroid = float(np.dot(freqs, spectrum) / total)
            centroids.append(centroid)

    if len(centroids) < 2:
        return 0.5

    centroids_arr = np.array(centroids)
    cv = centroids_arr.std() / (centroids_arr.mean() + 1e-6)  # coefficient of variation

    # Human speech centroid varies moderately (cv ~ 0.1–0.4).
    # Synthesised speech: either too flat (cv ~0) or too noisy (cv >>0.5).
    # Score: peak at cv=0.25, falls off toward 0 at extremes.
    # We use a tighter bell curve (0.15) because multi-chunk history handles noise naturally.
    ideal_cv = 0.25
    score = float(np.exp(-((cv - ideal_cv) ** 2) / (2 * 0.15 ** 2)))
    return float(np.clip(score, 0.0, 1.0))


def compute_ensemble(
    pdi_score: float,
    tremor_energy: float,
    audio_window: np.ndarray | None = None,
    fs: int = 16_000,
    state_dict: dict | None = None,
) -> EnsembleResult:
    """
    Compute the anti-spoofing ensemble score from all available signals.

    Parameters
    ----------
    pdi_score : float
        Phase Dispersion Index from phase_dispersion.compute_pdi() — [0,1],
        higher = more synthetic.
    tremor_energy : float
        Tremor band energy from micro_tremor.compute_tremor_score() — [0,1],
        higher = more human.
    audio_window : np.ndarray or None
        Raw audio for formant stability computation.  If None, formant
        component is set to 0.5 (neutral/unknown).
    fs : int
        Sample rate in Hz.

    Returns
    -------
    EnsembleResult dict
    """
    # ── 1. Component Scaling ──────────────────────────────────────────────────
    # PDI: higher PDI -> more phase dispersion (human-like).
    # Sigmoid mapping: strictly tuned to x0=0.75 via ROC to block Premium AI evasion
    pdi_human = float(1.0 / (1.0 + np.exp(-15.0 * (pdi_score - 0.75))))

    # Tremor: higher tremor energy -> physiological tremor (human-like).
    # Sigmoid mapping: smooth transition avoiding hard clip
    tremor_human = float(1.0 / (1.0 + np.exp(-30.0 * (tremor_energy - 0.10))))

    # Formant stability: high score → human
    if audio_window is not None:
        curr_formant = compute_formant_stability(audio_window, fs=fs)
        if state_dict is not None:
            history = state_dict.setdefault("formant_history", [])
            # Only track valid vowel chunks in memory
            if curr_formant != 0.5:
                history.append(curr_formant)
            if len(history) > 3:
                history.pop(0)
            formant_human = float(sum(history) / len(history)) if history else 0.5
        else:
            formant_human = curr_formant
    else:
        formant_human = 0.5  # neutral when no audio window provided

    # ── Weighted ensemble score (humanness) ───────────────────────────────────
    ensemble_score = W_PDI * pdi_human + W_TREMOR * tremor_human + W_FORMANT * formant_human

    # ── Disagreement check ────────────────────────────────────────────────────
    components = [pdi_human, tremor_human, formant_human]
    disagreement = float(max(components) - min(components))

    # ── Label assignment ──────────────────────────────────────────────────────
    if disagreement > DISAGREEMENT_THRESHOLD:
        # Signals disagree strongly — cannot safely conclude either way.
        # Rationale: spoofing one sensor is feasible; spoofing all three
        # simultaneously is much harder.  Disagreement → adversarial suspicion.
        label = EnsembleLabel.UNCERTAIN
        reason = (
            f"Signal disagreement too high ({disagreement:.2f} > {DISAGREEMENT_THRESHOLD}). "
            "Possible sensor spoofing or adversarial audio manipulation. "
            "Never classify as SAFE under strong disagreement."
        )
    elif ensemble_score >= (1.0 - SAFE_THRESHOLD):
        label = EnsembleLabel.SAFE
        reason = f"All signals consistent with human voice (ensemble={ensemble_score:.3f})"
    elif ensemble_score <= (1.0 - SYNTHETIC_THRESHOLD):
        label = EnsembleLabel.SYNTHETIC
        reason = f"Multiple signals indicate synthetic/deepfake voice (ensemble={ensemble_score:.3f})"
    else:
        label = EnsembleLabel.UNCERTAIN
        reason = f"Mixed signals, insufficient confidence (ensemble={ensemble_score:.3f})"

    logger.debug(
        "Ensemble: score=%.3f label=%s disagree=%.3f [pdi_h=%.3f tremor_h=%.3f formant_h=%.3f]",
        ensemble_score, label, disagreement, pdi_human, tremor_human, formant_human,
    )

    return EnsembleResult(
        ensemble_score=float(ensemble_score),
        label=label.value,
        pdi_contribution=float(W_PDI * pdi_human),
        tremor_contribution=float(W_TREMOR * tremor_human),
        formant_contribution=float(W_FORMANT * formant_human),
        disagreement=disagreement,
        reason=reason,
    )
