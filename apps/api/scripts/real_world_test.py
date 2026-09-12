import sys
from pathlib import Path
import numpy as np
import soundfile as sf
import scipy.signal
from gtts import gTTS
import os

# Add apps/api to sys.path so we can import dsp modules
sys.path.append(str(Path(__file__).parent.parent))

from dsp.phase_dispersion import compute_pdi

def generate_synthetic_samples():
    sentences = [
        "Hello, this is calling from your bank regarding your account.",
        "Your debit card has been blocked due to suspicious activity.",
        "Please provide your UPI pin to receive the refund amount.",
    ]
    os.makedirs("samples/synthetic", exist_ok=True)
    paths = []
    for i, text in enumerate(sentences):
        tts = gTTS(text, lang='en')
        path = f"samples/synthetic/synth_{i}.mp3"
        tts.save(path)
        paths.append(path)
    return paths

def load_audio(path):
    sig, fs = sf.read(path)
    # Convert to mono if stereo
    if len(sig.shape) > 1:
        sig = sig.mean(axis=1)
    
    # Resample to 16000 if necessary
    if fs != 16000:
        # Number of samples in new rate
        num_samples = int(len(sig) * 16000 / fs)
        sig = scipy.signal.resample(sig, num_samples)
        fs = 16000
    
    return sig, fs

def process_audio(sig, fs):
    # compute PDI over 512-sample windows with 256-sample hop
    window_size = 512
    hop_size = 256
    
    pdi_scores = []
    for i in range(0, len(sig) - window_size, hop_size):
        window = sig[i:i + window_size]
        res = compute_pdi(window, fs)
        # only consider windows where it actually analyzed triads
        if res['n_triads_analysed'] > 0:
            pdi_scores.append(res['pdi_score'])
            
    if not pdi_scores:
        return 0.5, 0.5, 0.5, False
        
    avg = np.mean(pdi_scores)
    min_val = np.min(pdi_scores)
    max_val = np.max(pdi_scores)
    is_synth = avg > 0.6
    return avg, min_val, max_val, is_synth

def main():
    print("Generating synthetic samples...")
    synth_paths = generate_synthetic_samples()
    
    print("Loading human sample...")
    human_path = r"D:\PhaseGuard\freesound_community-shortfilm-voice-56795.mp3"
    
    results = {}
    
    # Process Human
    print("\n--- HUMAN SAMPLES ---")
    sig, fs = load_audio(human_path)
    avg, min_v, max_v, synth = process_audio(sig, fs)
    print(f"Human Sample 1 ({Path(human_path).name}): Avg PDI = {avg:.4f} (Min: {min_v:.4f}, Max: {max_v:.4f}) | Classified as Synthetic: {synth}")
    human_scores = [avg]
    
    print("\n--- SYNTHETIC (TTS) SAMPLES ---")
    synth_scores = []
    for i, path in enumerate(synth_paths):
        sig, fs = load_audio(path)
        avg, min_v, max_v, synth = process_audio(sig, fs)
        print(f"Synthetic Sample {i+1} ({Path(path).name}): Avg PDI = {avg:.4f} (Min: {min_v:.4f}, Max: {max_v:.4f}) | Classified as Synthetic: {synth}")
        synth_scores.append(avg)
        
    print("\n--- OVERALL RESULTS ---")
    human_mean = np.mean(human_scores)
    synth_mean = np.mean(synth_scores)
    print(f"Mean Human PDI: {human_mean:.4f}")
    print(f"Mean Synth PDI: {synth_mean:.4f}")
    
    human_min_avg, human_max_avg = np.min(human_scores), np.max(human_scores)
    synth_min_avg, synth_max_avg = np.min(synth_scores), np.max(synth_scores)
    
    # Determine if there's an overlap (even partial)
    # Check if the ranges overlap
    if max(human_min_avg, synth_min_avg) <= min(human_max_avg, synth_max_avg):
        print(f"OVERLAP EXISTS: Human range [{human_min_avg:.4f}, {human_max_avg:.4f}], Synth range [{synth_min_avg:.4f}, {synth_max_avg:.4f}]")
        print(f"Overlap zone: [{max(human_min_avg, synth_min_avg):.4f}, {min(human_max_avg, synth_max_avg):.4f}]")
    else:
        # Check if the means are very close, indicating weak separation
        if abs(human_mean - synth_mean) < 0.1:
            print(f"WEAK SEPARATION: Means are very close. Human: {human_mean:.4f}, Synth: {synth_mean:.4f}")
            print(f"Human range [{human_min_avg:.4f}, {human_max_avg:.4f}], Synth range [{synth_min_avg:.4f}, {synth_max_avg:.4f}]")
        else:
            print("CLEAR SEPARATION: No overlap between human and synthetic ranges.")
            print(f"Human range [{human_min_avg:.4f}, {human_max_avg:.4f}], Synth range [{synth_min_avg:.4f}, {synth_max_avg:.4f}]")
        
    print("\n--- DEGRADED AUDIO TEST ---")
    # Simulate degraded audio for one synthetic sample (resample to 8kHz and back)
    print("Testing Degraded Synthetic Sample (resampled to 8kHz then 16kHz)")
    sig, fs = load_audio(synth_paths[0])
    sig_8k = scipy.signal.resample(sig, len(sig)//2)
    sig_16k_degraded = scipy.signal.resample(sig_8k, len(sig))
    avg, min_v, max_v, synth = process_audio(sig_16k_degraded, fs)
    print(f"Degraded Synth Sample 1: Avg PDI = {avg:.4f} (Min: {min_v:.4f}, Max: {max_v:.4f}) | Classified as Synthetic: {synth}")

if __name__ == '__main__':
    main()
