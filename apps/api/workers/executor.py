"""
workers/executor.py — Shared ThreadPoolExecutor for CPU-bound DSP tasks.

Rationale for not using ProcessPoolExecutor by default:
  - DSP functions are NumPy/SciPy calls that release the GIL internally,
    so threads are sufficient for concurrency.
  - ProcessPoolExecutor has higher serialization overhead (pickle roundtrip)
    for numpy arrays; threads share memory zero-copy.
  - If a call under test proves GIL-bound (pure Python loops), swap to
    ProcessPoolExecutor here — all callers use run_in_executor and are
    unaffected by the swap.

NEVER call DSP functions directly inside an async def WebSocket handler —
route everything through this executor via run_in_executor so the event loop
stays unblocked for all concurrent connections.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

# Pool size: 4 threads handles ~4 concurrent calls without fighting each other.
# Increase EXECUTOR_WORKERS via env if running many simultaneous calls.
import os

_WORKERS = int(os.getenv("EXECUTOR_WORKERS", "4"))

_executor: ThreadPoolExecutor | None = None


def get_executor() -> ThreadPoolExecutor:
    """Return the module-level shared executor, creating it on first call."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(
            max_workers=_WORKERS, thread_name_prefix="phaseguard-dsp"
        )
    return _executor


def shutdown_executor() -> None:
    """Gracefully shut down the executor (call from FastAPI lifespan shutdown)."""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=True)
        _executor = None


async def run_in_dsp_executor(fn, *args):
    """
    Convenience wrapper: run a synchronous DSP function in the shared executor.

    Usage:
        result = await run_in_dsp_executor(compute_pdi, window, fs)
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(get_executor(), fn, *args)
