import os
import shutil
from gtts import gTTS

def main():
    api_dir = r"d:\PhaseGuard\apps\api"
    root_dir = r"d:\PhaseGuard"
    dataset_dir = os.path.join(api_dir, "dataset_v2")
    os.makedirs(dataset_dir, exist_ok=True)
    
    # 1. Move human files provided by user in root to dataset_v2
    # From earlier listing:
    # originalvo-medieval-gamer-voice-darkness-hunts-us-what-youx27ve-learned-stay-226596.mp3
    # sdking79-man-talking-unintelligibly-1-546038.mp3
    # universfield-are-you-home-voice-clip-323554.mp3
    # universfield-female-voice-good-morning-242169.mp3
    
    human_files = [
        "originalvo-medieval-gamer-voice-darkness-hunts-us-what-youx27ve-learned-stay-226596.mp3",
        "sdking79-man-talking-unintelligibly-1-546038.mp3",
        "universfield-are-you-home-voice-clip-323554.mp3",
        "universfield-female-voice-good-morning-242169.mp3",
        "freesound_community-shortfilm-voice-56795.mp3" # Previous good sample
    ]
    
    print("Moving human files...")
    for f in human_files:
        src = os.path.join(root_dir, f)
        if os.path.exists(src):
            dst = os.path.join(dataset_dir, f)
            shutil.copy(src, dst)
            print(f"Copied {f}")
        else:
            print(f"Skipped {f} (not found)")

    # 2. Generate Scam AI Voices
    print("\nGenerating AI Scam Voices...")
    scams = {
        "scam_bank_fraud": "Hello, this is the fraud detection department at your bank. We noticed a suspicious transaction of five hundred dollars on your account. Please confirm your identity by providing your social security number immediately, or your account will be frozen.",
        "scam_tech_support": "This is an urgent message from Microsoft Windows Support. Your computer has been infected with a dangerous virus. Do not shut down your computer. Call the toll-free number on your screen immediately so our technicians can remove the malware.",
        "scam_kidnapping": "Listen to me very carefully. We have your daughter. If you ever want to see her alive again, you will wire ten thousand dollars to the account I am about to give you. Do not call the police, or we will hurt her.",
        "scam_irs": "This is the Internal Revenue Service. You have an outstanding tax debt. An arrest warrant has been issued under your name. To avoid immediate arrest by local authorities, you must pay the balance using Apple iTunes gift cards right now."
    }
    
    for name, text in scams.items():
        dst = os.path.join(dataset_dir, f"{name}.mp3")
        if not os.path.exists(dst):
            try:
                tts = gTTS(text, lang='en')
                tts.save(dst)
                print(f"Generated {name}.mp3")
            except Exception as e:
                print(f"Failed {name}: {e}")
        else:
            print(f"{name}.mp3 already exists")
            
    print("\nDataset V2 compilation complete.")

if __name__ == "__main__":
    main()
