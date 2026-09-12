import sys
import os
from pathlib import Path
import numpy as np
import soundfile as sf
import scipy.signal

sys.path.append(str(Path(__file__).parent.parent))

from dsp.micro_tremor import compute_tremor_score
from dsp.phase_dispersion import compute_pdi
from dsp.ensemble_score import compute_formant_stability

def run_diagnostics():
    print("="*60)
    print("1. ISOLATED TREMOR TEST (Mathematical Baseline)")
    print("="*60)
    fs = 16000
    t = np.arange(1.5 * fs) / fs
    
    # Generate 300Hz carrier (like a vowel fundamental)
    carrier = np.sin(2 * np.pi * 300 * t) 
    
    # Generate physiological tremor (10Hz amplitude modulation)
    tremor_mod = 1.0 + 0.5 * np.sin(2 * np.pi * 10.0 * t) 
    
    synthetic_clean = carrier
    human_tremor = carrier * tremor_mod

    res_clean = compute_tremor_score(synthetic_clean, fs)
    res_tremor = compute_tremor_score(human_tremor, fs)
    
    print(f"Clean Sine Wave (No Tremor)    -> Tremor Energy: {res_clean['tremor_energy']:.4f}")
    print(f"10Hz AM Modulated (Max Tremor) -> Tremor Energy: {res_tremor['tremor_energy']:.4f}")
    if res_tremor['tremor_energy'] < 0.2:
        print(">>> ALERT: Tremor algorithm failed to detect a perfect mathematical 10Hz AM signal! It is mathematically broken.")
    else:
        print(">>> SUCCESS: Tremor algorithm correctly detected the mathematical 10Hz AM signal.")

    print("\n" + "="*60)
    print("2. RAW PDI AND FORMANT VOLATILITY (Human Sample)")
    print("="*60)
    
    path = r"d:\PhaseGuard\freesound_community-shortfilm-voice-56795.mp3"
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
        
    sig, fs_file = sf.read(path)
    if len(sig.shape) > 1: sig = sig.mean(axis=1)
    if fs_file != 16000:
        sig = scipy.signal.resample(sig, int(len(sig) * 16000 / fs_file))
    sig = sig.astype(np.float32)
    
    chunk_size = int(1.5 * 16000)
    step = int(0.5 * 16000)
    
    for i, start in enumerate(range(0, min(8 * step, len(sig) - chunk_size), step)):
        chunk = sig[start:start+chunk_size]
        
        # Raw PDI
        pdi_scores = []
        for j in range(0, len(chunk) - 512, 256):
            res = compute_pdi(chunk[j:j+512], 16000)
            if res['n_triads_analysed'] > 0:
                pdi_scores.append(res['pdi_score'])
        avg_raw_pdi = float(np.mean(pdi_scores)) if pdi_scores else 0.5
        scaled_pdi = np.clip((avg_raw_pdi - 0.70)/0.15, 0, 1)
        
        # Formant
        fmt = compute_formant_stability(chunk, 16000)
        
        print(f"Chunk {i:02d} [{start/16000:.1f}s-{start/16000+1.5:.1f}s]: Raw PDI = {avg_raw_pdi:.4f} (Scaled: {scaled_pdi:.4f}) | Formant = {fmt:.4f}")

if __name__ == "__main__":
    run_diagnostics()
