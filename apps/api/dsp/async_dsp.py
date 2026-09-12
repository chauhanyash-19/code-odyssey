"""
dsp/async_dsp.py — Async wrappers for all CPU-bound DSP functions.

All DSP functions are synchronous and CPU-bound (NumPy/SciPy).
NEVER call them directly inside an `async def` WebSocket handler — doing so
blocks the entire asyncio event loop for all concurrent connections during
the computation (GIL contention).

Each wrapper here uses `run_in_executor` to offload the blocking call to the
shared ThreadPoolExecutor defined in workers/executor.py.

Usage:
    result = await analyze_bispectrum(window, fs=16000)
    result = await analyze_tremor(window, fs=16000)
    result = await analyze_ensemble(pdi_score, tremor_energy, audio_window)
"""

from __future__ import annotations

import numpy as np

from dsp.ensemble_score import compute_ensemble
from dsp.micro_tremor import compute_tremor_score
from dsp.phase_dispersion import compute_pdi
from workers.executor import run_in_dsp_executor


async def analyze_bispectrum(
    window: np.ndarray,
    fs: int = 16_000,
    threshold: float = 0.6,
) -> dict:
    """
    Async wrapper for compute_pdi.
    Runs in the shared ThreadPoolExecutor — does not block the event loop.
    """
    return await run_in_dsp_executor(compute_pdi, window, fs, threshold)


async def analyze_tremor(
    window: np.ndarray,
    fs: int = 16_000,
    threshold: float = 0.15,
) -> dict:
    """
    Async wrapper for compute_tremor_score.
    Runs in the shared ThreadPoolExecutor — does not block the event loop.
    """
    return await run_in_dsp_executor(compute_tremor_score, window, fs, threshold)


async def analyze_ensemble(
    pdi_score: float,
    tremor_energy: float,
    audio_window: np.ndarray | None = None,
    fs: int = 16_000,
) -> dict:
    """
    Async wrapper for compute_ensemble.
    Runs in the shared ThreadPoolExecutor — does not block the event loop.
    """
    return await run_in_dsp_executor(
        compute_ensemble, pdi_score, tremor_energy, audio_window, fs
    )
