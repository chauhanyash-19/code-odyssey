import os
import sys
import numpy as np
import soundfile as sf
import pyttsx3
import scipy.signal

def add_noise(input_path, output_path, noise_level=0.015):
    sig, fs = sf.read(input_path)
    if len(sig.shape) > 1:
        sig = sig.mean(axis=1)
    
    # Generate white noise
    noise = np.random.normal(0, noise_level, len(sig))
    
    # Mix
    noisy_sig = sig + noise
    
    # Normalize to prevent clipping
    max_val = np.max(np.abs(noisy_sig))
    if max_val > 1.0:
        noisy_sig = noisy_sig / max_val
        
    sf.write(output_path, noisy_sig, fs)
    print(f"Generated noisy human sample: {output_path}")

def generate_fresh_ai(output_path):
    engine = pyttsx3.init()
    # Different script, completely different TTS engine from gTTS
    text = "Hello, this is a fresh test of the emergency broadcast system. If this were a real emergency, you would be instructed to evacuate immediately. Do not hang up."
    engine.save_to_file(text, output_path)
    engine.runAndWait()
    print(f"Generated fresh AI sample: {output_path}")

def main():
    holdout_dir = r"d:\PhaseGuard\apps\api\dataset_v3_holdout"
    os.makedirs(holdout_dir, exist_ok=True)
    
    # 1. Noisy Human
    # We will add white noise to an existing clean human sample to simulate bad connection
    human_src = r"d:\PhaseGuard\apps\api\dataset_v2\sdking79-man-talking-unintelligibly-1-546038.mp3"
    human_noisy_dest = os.path.join(holdout_dir, "human_noisy_volte.wav")
    
    if os.path.exists(human_src):
        add_noise(human_src, human_noisy_dest)
    else:
        print(f"Human source not found: {human_src}")
        
    # 2. Fresh AI
    ai_dest = os.path.join(holdout_dir, "fresh_ai_pyttsx3.wav")
    generate_fresh_ai(ai_dest)
    
    print("\nHoldout Dataset V3 complete.")

if __name__ == "__main__":
    main()
