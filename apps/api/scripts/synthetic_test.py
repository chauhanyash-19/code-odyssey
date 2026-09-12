import sys
from pathlib import Path
import numpy as np

# Add apps/api to sys.path so we can import dsp modules
sys.path.append(str(Path(__file__).parent.parent))

from dsp.phase_dispersion import compute_pdi

def generate_coherent_signal(fs: int, duration_sec: float) -> np.ndarray:
    """Generates a phase-coherent signal (simulating Natural human voice)."""
    t = np.linspace(0, duration_sec, int(fs * duration_sec), endpoint=False)
    f0 = 200.0
    # True harmonic series, perfectly coherent phases
    sig = np.sin(2 * np.pi * f0 * t)
    sig += 0.5 * np.sin(2 * np.pi * 2 * f0 * t)
    sig += 0.25 * np.sin(2 * np.pi * 3 * f0 * t)
    sig += 0.125 * np.sin(2 * np.pi * 4 * f0 * t)
    sig += 0.0625 * np.sin(2 * np.pi * 5 * f0 * t)
    return sig.astype(np.float32)

def generate_incoherent_signal(fs: int, duration_sec: float) -> np.ndarray:
    """Generates a phase-randomized signal (simulating Synthetic deepfake)."""
    t = np.linspace(0, duration_sec, int(fs * duration_sec), endpoint=False)
    # White noise has uniformly distributed, completely random phases
    sig = np.random.normal(0, 1, len(t))
    # To make it pass the amplitude threshold in PDI, we add some harmonic content but with randomized phases
    f0 = 200.0
    for i in range(1, 10):
        phase = np.random.uniform(0, 2 * np.pi)
        sig += (1.0 / i) * np.sin(2 * np.pi * i * f0 * t + phase)
    return sig.astype(np.float32)

def main():
    fs = 16000
    duration = 1.0  # 1 second of audio
    
    coherent_sig = generate_coherent_signal(fs, duration)
    incoherent_sig = generate_incoherent_signal(fs, duration)
    
    # We take a 512-sample window as expected by compute_pdi
    coherent_window = coherent_sig[:512]
    incoherent_window = incoherent_sig[:512]
    
    coherent_result = compute_pdi(coherent_window, fs)
    incoherent_result = compute_pdi(incoherent_window, fs)
    
    print("--- Phase Dispersion Index (PDI) Sanity Check ---")
    print(f"Coherent (Natural) Signal PDI:   {coherent_result['pdi_score']:.4f}")
    print(f"Incoherent (Synthetic) Signal PDI: {incoherent_result['pdi_score']:.4f}")
    
    if coherent_result['pdi_score'] < incoherent_result['pdi_score']:
        print("SUCCESS: Natural (Coherent) PDI is lower than Synthetic (Incoherent) PDI.")
    else:
        print("FAILURE: Natural PDI is not lower than Synthetic PDI.")

if __name__ == '__main__':
    main()
