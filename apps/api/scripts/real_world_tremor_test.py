import sys
from pathlib import Path
import numpy as np
import soundfile as sf
import scipy.signal

# Add apps/api to sys.path so we can import dsp modules
sys.path.append(str(Path(__file__).parent.parent))

from dsp.micro_tremor import compute_tremor_score
from dsp.phase_dispersion import compute_pdi

def load_audio(path):
    sig, fs = sf.read(path)
    if len(sig.shape) > 1:
        sig = sig.mean(axis=1)
    if fs != 16000:
        num_samples = int(len(sig) * 16000 / fs)
        sig = scipy.signal.resample(sig, num_samples)
        fs = 16000
    return sig, fs

def process_tremor(sig, fs):
    window_size = int(1.5 * fs)  # 1.5 seconds = 24000 samples
    hop_size = int(0.75 * fs)    # 0.75 seconds overlap = 12000 samples
    
    tremor_energies = []
    has_tremor_flags = []
    
    for i in range(0, len(sig) - window_size + 1, hop_size):
        window = sig[i:i + window_size]
        res = compute_tremor_score(window, fs)
        tremor_energies.append(res['tremor_energy'])
        has_tremor_flags.append(res['has_tremor'])
            
    if not tremor_energies:
        return 0.0, 0.0, 0.0, False
        
    avg = np.mean(tremor_energies)
    min_val = np.min(tremor_energies)
    max_val = np.max(tremor_energies)
    has_tremor_overall = avg > 0.15  # threshold
    return avg, min_val, max_val, has_tremor_overall

def process_combined(sig, fs):
    # For combination test: compute both on the clip and see if a rule works
    window_size_tremor = int(1.5 * fs)
    hop_size_tremor = int(0.75 * fs)
    window_size_pdi = 512
    hop_size_pdi = 256
    
    # Tremor
    t_energies = []
    for i in range(0, len(sig) - window_size_tremor + 1, hop_size_tremor):
        window = sig[i:i + window_size_tremor]
        t_energies.append(compute_tremor_score(window, fs)['tremor_energy'])
    avg_tremor = np.mean(t_energies) if t_energies else 0.0
    
    # PDI
    pdi_scores = []
    for i in range(0, len(sig) - window_size_pdi, hop_size_pdi):
        window = sig[i:i + window_size_pdi]
        res = compute_pdi(window, fs)
        if res['n_triads_analysed'] > 0:
            pdi_scores.append(res['pdi_score'])
    avg_pdi = np.mean(pdi_scores) if pdi_scores else 0.5
    
    return avg_tremor, avg_pdi

def main():
    human_path = r"D:\PhaseGuard\freesound_community-shortfilm-voice-56795.mp3"
    synth_paths = [
        "samples/synthetic/synth_0.mp3",
        "samples/synthetic/synth_1.mp3",
        "samples/synthetic/synth_2.mp3",
    ]
    
    print("--- HUMAN SAMPLE ---")
    sig_h, fs_h = load_audio(human_path)
    avg, min_v, max_v, flag = process_tremor(sig_h, fs_h)
    print(f"Human: Avg Tremor = {avg:.4f} (Min: {min_v:.4f}, Max: {max_v:.4f}) | has_tremor (genuine): {flag}")
    human_tremor = avg
    
    print("\n--- SYNTHETIC SAMPLES ---")
    synth_tremors = []
    for i, path in enumerate(synth_paths):
        sig, fs = load_audio(path)
        avg, min_v, max_v, flag = process_tremor(sig, fs)
        print(f"Synth {i+1}: Avg Tremor = {avg:.4f} (Min: {min_v:.4f}, Max: {max_v:.4f}) | has_tremor (genuine): {flag}")
        synth_tremors.append(avg)
        
    human_mean = human_tremor
    synth_mean = np.mean(synth_tremors)
    print(f"\nMean Human Tremor: {human_mean:.4f}")
    print(f"Mean Synth Tremor: {synth_mean:.4f}")
    
    h_min, h_max = human_tremor, human_tremor
    s_min, s_max = np.min(synth_tremors), np.max(synth_tremors)
    
    if max(h_min, s_min) <= min(h_max, s_max):
        print(f"OVERLAP EXISTS: Human range [{h_min:.4f}, {h_max:.4f}], Synth range [{s_min:.4f}, {s_max:.4f}]")
    else:
        print("CLEAR SEPARATION: No overlap between human and synthetic ranges.")
        
    print("\n--- DEGRADED AUDIO TEST ---")
    sig, fs = load_audio(synth_paths[0])
    sig_8k = scipy.signal.resample(sig, len(sig)//2)
    sig_16k_degraded = scipy.signal.resample(sig_8k, len(sig))
    avg, min_v, max_v, flag = process_tremor(sig_16k_degraded, fs)
    print(f"Degraded Synth 1: Avg Tremor = {avg:.4f} | has_tremor: {flag}")

    print("\n--- COMBINED (TREMOR + PDI) ANALYSIS ---")
    h_t, h_p = process_combined(sig_h, fs_h)
    print(f"Human:  Tremor={h_t:.4f}, PDI={h_p:.4f}")
    for i, path in enumerate(synth_paths):
        sig, fs = load_audio(path)
        s_t, s_p = process_combined(sig, fs)
        print(f"Synth {i+1}: Tremor={s_t:.4f}, PDI={s_p:.4f}")

if __name__ == '__main__':
    main()
