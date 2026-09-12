"""
dsp/hf_ml.py — Hugging Face Inference API integration for deepfake detection.

Uses a pre-trained Audio Classification model on HuggingFace to detect
spoofed/AI-generated audio as a replacement for pure DSP.
"""
import io
import time
import logging
import httpx
import numpy as np
import scipy.io.wavfile

from core.config import get_settings

logger = logging.getLogger(__name__)

# A public model for spoofing/deepfake detection on HF
# Selected as per prompt: ASVspoof2019 trained
HF_PRIMARY_URL = "https://api-inference.huggingface.co/models/caa-speech-detection-asvspoof2019/rawnet2"
HF_BACKUP_URL = "https://api-inference.huggingface.co/models/HyperMoon/wav2vec2-base-960h-finetuned-deepfake"

async def analyze_audio_hf(window: np.ndarray, fs: int = 16_000) -> dict:
    """
    Send the audio window to Hugging Face Inference API.
    Returns a dictionary with the ML analysis result.
    """
    cfg = get_settings()
    if not cfg.hf_api_token:
        return {"error": "No HF token"}

    t0 = time.perf_counter()

    # Convert float32 numpy array to 16-bit PCM WAV in memory
    buf = io.BytesIO()
    audio_int16 = (window * 32767).astype(np.int16)
    scipy.io.wavfile.write(buf, fs, audio_int16)
    audio_bytes = buf.getvalue()

    headers = {
        "Authorization": f"Bearer {cfg.hf_api_token}",
        "Content-Type": "audio/wav"
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        for url in [HF_PRIMARY_URL, HF_BACKUP_URL]:
            try:
                resp = await client.post(url, headers=headers, content=audio_bytes)
                
                # If model is loading (503) or other server error, try backup
                if resp.status_code >= 500:
                    logger.warning(f"HF API {url} returned {resp.status_code}. Trying next model...")
                    continue
                    
                resp.raise_for_status()
                data = resp.json()
                
                # Format expected from HF Audio Classification
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                    # Map labels
                    top_label = data[0].get("label", "unknown").lower()
                    score = data[0].get("score", 0.0)
                    is_synthetic = score > 0.5 if ("fake" in top_label or "spoof" in top_label) else False
                    
                    return {
                        "status": "success",
                        "is_synthetic": is_synthetic,
                        "top_label": top_label,
                        "score": score,
                        "compute_ms": (time.perf_counter() - t0) * 1000,
                        "raw_output": data,
                        "model_used": url
                    }
                return {"status": "error", "message": "Unexpected HF response format"}
                
            except Exception as e:
                logger.warning(f"HF API Error on {url}: {e}")
                continue
                
    # Fallback to DSP if HF fails
    logger.info("Falling back to local DSP ensemble for deepfake detection")
    from dsp.phase_dispersion import compute_pdi
    from dsp.micro_tremor import compute_tremor_score
    from dsp.ensemble_score import compute_ensemble
    
    try:
        # compute PDI over 512-sample windows with 256-sample hop
        window_size = 512
        hop_size = 256
        
        pdi_scores = []
        for i in range(0, len(window) - window_size, hop_size):
            win = window[i:i + window_size]
            res = compute_pdi(win, fs)
            if res['n_triads_analysed'] > 0:
                pdi_scores.append(res['pdi_score'])
                
        avg_pdi = float(np.mean(pdi_scores)) if pdi_scores else 0.5
        
        tremor_res = compute_tremor_score(window, fs)
        
        ensemble_res = compute_ensemble(avg_pdi, tremor_res['tremor_energy'], window, fs)
        
        is_synthetic = ensemble_res['label'] == 'SYNTHETIC'
        score = 1.0 - ensemble_res['ensemble_score'] if is_synthetic else ensemble_res['ensemble_score']
        
        return {
            "status": "success",
            "is_synthetic": is_synthetic,
            "top_label": "spoofed" if is_synthetic else "bonafide",
            "score": score,
            "compute_ms": (time.perf_counter() - t0) * 1000,
            "raw_output": ensemble_res,
            "model_used": "local_dsp_ensemble"
        }
    except Exception as e:
        logger.error(f"DSP Fallback failed: {e}")
        return {"status": "error", "message": "All HF models and DSP fallback failed"}
