# PhaseGuard Demo Pitch & Script

## Core Pitch
PhaseGuard is designed to be complementary to existing government infrastructure like I4C, Chakshu, and the 1930 National Cyber Crime Portal. 

We are NOT replacing these portals. Instead, PhaseGuard acts as the **real-time detection and evidence-gathering layer** that operates at the edge, during the critical window when a scam is actively occurring. Government portals remain the ultimate authority for legal action and reporting. PhaseGuard empowers citizens to detect threats instantly and seamlessly package high-quality, actionable forensic intelligence for the authorities.

## Demo Flow
1. **The Hook:** Start by establishing the problem — India's telecom scam epidemic, deepfakes, and the psychological manipulation of victims.
2. **Real-time Ingestion:** Show the live audio being ingested. Explain that this is raw PCM data, no bypasses.
3. **The Math (DSP):** Demonstrate the PhaseOrbitCanvas and StressMeter. Explain how the Bispectrum estimator detects synthetic voices (deepfakes) by analyzing phase dispersion, and how micro-tremor analysis detects caller stress. This is CPU-local, deterministic, and runs at ~150ms latency.
   
   > **HONESTY NOTE (Real-World Validation):** PDI threshold was tuned on synthetic sine-wave signals. Validation against real gTTS-generated speech showed severe overlap and inverted scoring with human samples (Human: ~0.89 PDI, TTS: ~0.73 PDI, both flagged as fake at 0.6 threshold). This indicates the current bispectrum approach needs further tuning or additional features (formant stability, ensemble scoring per Phase 4) before being presented as a standalone reliable deepfake detector. It functions as a genuine research-stage signal, not a production-validated classifier.
   
4. **The LLM Fact-Checker:** Show the Groq-powered live STT and Llama-3.3 claim extraction. Mention the deterministic UPI PIN guard ("A UPI PIN is never needed to receive money").
   > **KEY PITCH (Demographic Taxonomy):** Emphasize that PhaseGuard doesn't just catch one type of scam script — it recognizes the underlying demand pattern (OTP, PIN, upfront fee, gift card) across dozens of different pretexts targeting every age group (e.g., fake 'Dadi, main hospital mein hoon' calls for the elderly, fake internship fees for students, and fake HR calls for professionals).
5. **The Verdict & Scambaiter:** Trigger a CRITICAL verdict. Show the Scambaiter taking over to stall the scammer with a confused persona.
6. **Accessibility:** Highlight the local spoken warnings (TTS) in Hindi for the protected user, and the Offline-Fallback mode that keeps DSP running even if the internet drops.
7. **The Evidence (Govt Export):** Conclude by downloading the forensic PDF dossier and the Chakshu CSV export. Emphasize that nothing is auto-filed — the human confirms the escalation, sending pristine intelligence to 1930/Chakshu.
