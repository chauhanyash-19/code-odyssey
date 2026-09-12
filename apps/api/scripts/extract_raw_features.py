import os
import sys
import json
import time
from pathlib import Path
import numpy as np
import soundfile as sf
import scipy.signal

sys.path.append(str(Path(__file__).parent.parent))

from dsp.phase_dispersion import compute_pdi
from dsp.micro_tremor import compute_tremor_score
from dsp.ensemble_score import compute_formant_stability

def load_audio(path):
    sig, fs = sf.read(path)
    if len(sig.shape) > 1:
        sig = sig.mean(axis=1)
    if fs != 16000:
        num_samples = int(len(sig) * 16000 / fs)
        sig = scipy.signal.resample(sig, num_samples)
        fs = 16000
    return sig.astype(np.float32), fs

def main():
    dataset_dir = r"d:\PhaseGuard\apps\api\dataset_v2"
    output_file = r"d:\PhaseGuard\apps\api\dataset_v2\raw_features.json"
    
    results = []
    
    for filename in os.listdir(dataset_dir):
        if not (filename.endswith(".wav") or filename.endswith(".mp3") or filename.endswith(".flac")):
            continue
            
        path = os.path.join(dataset_dir, filename)
        print(f"Extracting {filename}...")
        
        sig, fs = load_audio(path)
        if len(sig) > 15 * fs:
            sig = sig[:15 * fs]
            
        chunk_size = int(1.5 * fs)
        step_size = int(0.5 * fs)
        
        chunk_idx = 0
        
        for start in range(0, len(sig) - chunk_size + 1, step_size):
            chunk = sig[start:start+chunk_size]
            
            # Tremor
            tremor_res = compute_tremor_score(chunk, fs)
            tremor_raw = tremor_res['tremor_energy']
            
            # PDI
            pdi_scores = []
            for i in range(0, len(chunk) - 512, 256):
                res = compute_pdi(chunk[i:i+512], fs)
                if res['n_triads_analysed'] > 0:
                    pdi_scores.append(res['pdi_score'])
            pdi_raw = float(np.mean(pdi_scores)) if pdi_scores else 0.5
            
            # Formant (without state here, just raw chunk value)
            formant_raw = compute_formant_stability(chunk, fs=fs)
            
            results.append({
                "file": filename,
                "chunk_idx": chunk_idx,
                "start_s": start / fs,
                "pdi_raw": pdi_raw,
                "tremor_raw": float(tremor_raw),
                "formant_raw": float(formant_raw)
            })
            chunk_idx += 1

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Extraction complete! Saved to {output_file}")

if __name__ == "__main__":
    main()
