import os
import urllib.request
import ssl
from gtts import gTTS

ssl._create_default_https_context = ssl._create_unverified_context

def fetch_holdout():
    os.makedirs("holdout_dataset", exist_ok=True)
    
    # 1. Download unseen Human Samples (LibriSpeech test clips from a public repo)
    human_urls = [
        ("human_1.flac", "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac"),
        ("human_2.flac", "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/2.flac"),
        ("human_3.flac", "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/3.flac")
    ]
    
    print("Fetching human samples...")
    for name, url in human_urls:
        path = os.path.join("holdout_dataset", name)
        if not os.path.exists(path):
            try:
                urllib.request.urlretrieve(url, path)
                print(f"Downloaded {name}")
            except Exception as e:
                print(f"Failed to download {name}: {e}")
        else:
            print(f"{name} already exists.")

    # 2. Generate unseen AI Samples (gTTS)
    tts_texts = [
        "Hello, this is a completely unseen synthetic voice test for deepfake detection.",
        "Your bank account was compromised and we require immediate verification.",
        "PhaseGuard analyzes micro tremor and phase dispersion to stop fraud."
    ]
    
    print("Generating TTS samples...")
    for i, text in enumerate(tts_texts):
        name = f"gtts_ai_{i+1}.mp3"
        path = os.path.join("holdout_dataset", name)
        if not os.path.exists(path):
            try:
                tts = gTTS(text, lang='en')
                tts.save(path)
                print(f"Generated {name}")
            except Exception as e:
                print(f"Failed to generate {name}: {e}")
        else:
            print(f"{name} already exists.")
            
    print("Holdout dataset ready in 'holdout_dataset/' directory.")

if __name__ == "__main__":
    fetch_holdout()
