import sys
from pathlib import Path
import numpy as np
import soundfile as sf
import scipy.signal

sys.path.append(str(Path(r"D:\PhaseGuard\apps\api")))

from dsp.phase_dispersion import compute_pdi
from dsp.micro_tremor import compute_tremor_score
from dsp.ensemble_score import compute_ensemble

def load_audio(path):
    sig, fs = sf.read(path)
    if len(sig.shape) > 1:
        sig = sig.mean(axis=1)
    if fs != 16000:
        num_samples = int(len(sig) * 16000 / fs)
        sig = scipy.signal.resample(sig, num_samples)
        fs = 16000
    return sig.astype(np.float32), fs

def process_audio(sig, fs):
    # compute PDI over 512-sample windows with 256-sample hop
    window_size = 512
    hop_size = 256
    
    pdi_scores = []
    for i in range(0, len(sig) - window_size, hop_size):
        window = sig[i:i + window_size]
        res = compute_pdi(window, fs)
        if res['n_triads_analysed'] > 0:
            pdi_scores.append(res['pdi_score'])
            
    avg_pdi = np.mean(pdi_scores) if pdi_scores else 0.5
    
    tremor_res = compute_tremor_score(sig, fs)
    
    ensemble_res = compute_ensemble(avg_pdi, tremor_res['tremor_energy'], sig, fs)
    return ensemble_res

human_path = r"D:\PhaseGuard\freesound_community-shortfilm-voice-56795.mp3"
synth_paths = [
    r"D:\PhaseGuard\apps\api\scripts\samples\synthetic\synth_0.mp3",
    r"D:\PhaseGuard\apps\api\scripts\samples\synthetic\synth_1.mp3",
    r"D:\PhaseGuard\apps\api\scripts\samples\synthetic\synth_2.mp3",
]

print("--- HUMAN SAMPLES ---")
sig, fs = load_audio(human_path)
res = process_audio(sig, fs)
print(f"Human: {res['label']} - Score: {res['ensemble_score']:.4f}, Reason: {res['reason']}")
print(f"Details: pdi={res['pdi_contribution']:.4f}, tremor={res['tremor_contribution']:.4f}, formant={res['formant_contribution']:.4f}")

print("\n--- SYNTHETIC (TTS) SAMPLES ---")
for i, path in enumerate(synth_paths):
    sig, fs = load_audio(path)
    res = process_audio(sig, fs)
    print(f"Synthetic {i+1}: {res['label']} - Score: {res['ensemble_score']:.4f}, Reason: {res['reason']}")
    print(f"Details: pdi={res['pdi_contribution']:.4f}, tremor={res['tremor_contribution']:.4f}, formant={res['formant_contribution']:.4f}")
