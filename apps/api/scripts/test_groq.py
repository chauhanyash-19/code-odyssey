import asyncio
import os
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_settings
from groq import AsyncGroq

async def test_llm():
    print("\n--- Testing Groq LLM ---")
    cfg = get_settings()
    if not cfg.groq_api_key:
        print("FAIL: GROQ_API_KEY is not set.")
        return

    client = AsyncGroq(api_key=cfg.groq_api_key)
    try:
        response = await client.chat.completions.create(
            model=cfg.groq_llm_model,
            messages=[{"role": "user", "content": "Reply with exactly the word: WORKING"}],
            max_tokens=10
        )
        print("Raw LLM Response:")
        print(response.choices[0].message.content)
        print("LLM Call Status: PASS")
    except Exception as e:
        print(f"LLM Call Status: FAIL ({e})")

async def test_stt():
    print("\n--- Testing Groq STT ---")
    cfg = get_settings()
    if not cfg.groq_api_key:
        print("FAIL: GROQ_API_KEY is not set.")
        return

    import httpx
    client = AsyncGroq(api_key=cfg.groq_api_key, http_client=httpx.AsyncClient())
    
    # Generate a dummy wave file (1 sec silence)
    wav_path = "test_silence.wav"
    with wave.open(wav_path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(b"\x00" * 32000)
        
    try:
        with open(wav_path, "rb") as f:
            transcription = await client.audio.transcriptions.create(
                model=cfg.groq_stt_model,
                file=("test_silence.wav", f.read())
            )
        print("Raw STT Transcription Response:")
        print(transcription.text)
        print("STT Call Status: PASS")
    except Exception as e:
        print(f"STT Call Status: FAIL ({e})")
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)

async def main():
    await test_llm()
    await test_stt()

if __name__ == "__main__":
    asyncio.run(main())
