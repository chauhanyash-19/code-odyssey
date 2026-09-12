"""
core/config.py — Centralized settings loaded from environment variables.
Uses pydantic-settings so every value is type-validated at startup.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All configuration for the PhaseGuard API.
    Values are read from environment variables (or a .env file in dev).
    In production, use the secrets.py abstraction to pull from a secret manager
    before these are consumed.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Server ─────────────────────────────────────────────────────────────────
    ws_host: str = Field(default="0.0.0.0", description="WebSocket server host")
    ws_port: int = Field(default=8000, description="WebSocket server port")
    debug: bool = Field(default=False, description="Enable FastAPI debug mode")
    environment: Literal["development", "staging", "production"] = Field(
        default="development"
    )

    # ── Auth ───────────────────────────────────────────────────────────────────
    jwt_secret: str = Field(
        default="CHANGE_ME_IN_PRODUCTION",
        description="HS256 signing secret for call tokens",
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_ttl_minutes: int = Field(default=15, description="Token TTL in minutes")

    # ── Groq (STT + LLM) ──────────────────────────────────────────────────────
    groq_api_key: str = Field(default="", description="Groq API key")
    groq_stt_model: str = Field(default="whisper-large-v3")
    groq_llm_model: str = Field(default="openai/gpt-oss-120b")

    # ── NewsAPI (3-tier search Tier 1) ────────────────────────────────────────
    # Get free key (no card) at: https://newsapi.org/register
    # Free tier: 100 requests/day for dev use.
    newsapi_key: str = Field(default="", description="NewsAPI.org API key")

    # ── Google Custom Search (disabled — billing not configured) ───────────────
    # Kept in settings so the key can be dropped in later without code change.
    google_search_api_key: str = Field(default="", description="Google Custom Search API key (disabled)")
    google_search_engine_id: str = Field(default="", description="Google Custom Search Engine ID (disabled)")

    # ── Serper (Alternative Google Search) ────────────────────────────────────
    serper_api_key: str = Field(default="", description="Serper.dev API key")
    
    # ── Tavily (AI Search - Primary Factcheck) ────────────────────────────────
    tavily_api_key: str = Field(default="", description="Tavily API key")

    # ── Jina (Raw Text Search Fallback) ───────────────────────────────────────
    jina_api_key: str = Field(default="", description="Jina AI API key")

    # ── TTS Backend ────────────────────────────────────────────────────────────
    tts_backend: str = Field(default="gtts", description="TTS backend (gtts | mock)")
    tts_language: str = Field(default="hi", description="TTS language")
    elevenlabs_api_key: str = Field(default="", description="Optional ElevenLabs API key")
    elevenlabs_voice_id: str = Field(default="", description="Optional ElevenLabs Voice ID")

    # ── WhatsApp (text scanner) ────────────────────────────────────────────────
    whatsapp_phone_number_id: str = Field(default="")
    whatsapp_access_token: str = Field(default="")

    # ── Exotel (real-call ingestion, no hardware) ──────────────────────────────
    exotel_api_key: str = Field(default="", description="Exotel API key")
    exotel_api_token: str = Field(default="", description="Exotel API token")
    exotel_sid: str = Field(default="", description="Exotel Account SID")

    # ── Twilio (SMS fallback + Media Streams) ─────────────────────────────────
    twilio_account_sid: str = Field(default="")
    twilio_auth_token: str = Field(default="")
    twilio_phone_number: str = Field(default="")

    # ── SMS Backend ────────────────────────────────────────────────────────────
    sms_backend: str = Field(default="simulated", description="SMS backend (simulated)")

    # ── Secret manager backend ────────────────────────────────────────────────
    # Rationale: never commit raw secrets to source in non-dev environments.
    secret_manager_backend: Literal["env", "doppler", "infisical", "gcp", "aws"] = (
        Field(default="env")
    )

    # ── DSP voice-detection feature gate ─────────────────────────────────────
    # EXPERIMENTAL: Real-world validation (2026-08-27) showed that bispectrum PDI
    # and micro-tremor both FAILED to separate real human speech from gTTS on real
    # audio (human avg PDI 0.89 vs gTTS 0.73 — inverted; tremor equally confused).
    # Disabled by default so it does NOT corrupt live demo results.
    # Set DSP_VOICE_DETECTION_ENABLED=true to re-enable for research/tuning.
    dsp_voice_detection_enabled: bool = Field(
        default=False,
        description=(
            "[EXPERIMENTAL] Enable bispectrum PDI + micro-tremor DSP loops. "
            "Disabled by default: real-world validation showed inverted/overlapping "
            "results vs gTTS. Enable only for research/tuning, not live demos."
        ),
    )

    hf_api_token: str = Field(default="", description="Hugging Face Inference API token")

    # ── DSP tuning ────────────────────────────────────────────────────────────
    sample_rate: int = Field(default=16000, description="Expected audio sample rate (Hz)")
    bispectrum_window_samples: int = Field(
        default=512,
        description=(
            "FFT window size for bispectrum. "
            "MUST be ≥512: a 128-sample window gives ~125 Hz resolution, "
            "too coarse for harmonic-triad analysis in the 300-3400 Hz band. "
            "512 gives ~31 Hz resolution; 1024 gives ~15 Hz."
        ),
    )
    bispectrum_hop_samples: int = Field(
        default=256, description="50% overlap hop size for bispectrum sliding window"
    )
    bispectrum_cadence_ms: float = Field(
        default=150.0, description="How often to emit a PDI update (ms)"
    )
    tremor_window_seconds: float = Field(
        default=1.5,
        description=(
            "Window length for micro-tremor analysis. "
            "MUST be ≥1 s: distinguishing 8 Hz from 12 Hz requires sub-Hz FFT "
            "resolution, which needs at least 1/Δf ≈ 1 s of signal."
        ),
    )
    tremor_cadence_seconds: float = Field(
        default=1.5, description="How often to emit a tremor update (s)"
    )
    pdi_threshold: float = Field(
        default=0.6, description="PDI score above which voice is flagged as synthetic"
    )

    # ── Ingestion mode ────────────────────────────────────────────────────────
    ingestion_mode: Literal["browser_mic", "exotel", "twilio"] = Field(
        default="browser_mic",
        description="Active audio ingestion adapter",
    )

    # ── Escalation ────────────────────────────────────────────────────────────
    cybercrime_cell_email: str = Field(
        default="",
        description="Email address of configured cybercrime cell for escalation",
    )
    escalation_webhook_url: str = Field(
        default="", description="Slack/Discord webhook URL for demo escalation"
    )
    family_contact_number: str = Field(
        default="", description="Default family/emergency SMS contact"
    )

    @field_validator("jwt_secret")
    @classmethod
    def _warn_default_secret(cls, v: str) -> str:
        if v == "CHANGE_ME_IN_PRODUCTION":
            import warnings

            warnings.warn(
                "jwt_secret is using the insecure default value. "
                "Set JWT_SECRET in your environment before deploying.",
                stacklevel=2,
            )
        return v

    @model_validator(mode="after")
    def validate_ingestion_mode(self) -> Settings:
        if self.ingestion_mode == "exotel":
            if not all([self.exotel_api_key, self.exotel_api_token, self.exotel_sid]):
                import logging
                logging.getLogger(__name__).error(
                    "Exotel/Twilio ingestion requires EXOTEL_API_KEY/... — falling back to browser_mic"
                )
                self.ingestion_mode = "browser_mic"
        elif self.ingestion_mode == "twilio":
            if not all([self.twilio_account_sid, self.twilio_auth_token, self.twilio_phone_number]):
                import logging
                logging.getLogger(__name__).error(
                    "Exotel/Twilio ingestion requires TWILIO_ACCOUNT_SID/... — falling back to browser_mic"
                )
                self.ingestion_mode = "browser_mic"
        return self

    def log_startup_summary(self):
        print("\n[PhaseGuard Startup]")
        if self.groq_api_key:
            print("[OK] Groq (STT + LLM): ACTIVE")
        else:
            print("[WARN] Groq (STT + LLM): NOT CONFIGURED")

        # Search Fallback Chain (matches factcheck/search.py)
        print("\n  [Search Fallback Chain]")
        if self.tavily_api_key:
            print("  [OK]   Tier 1 - Tavily API (Primary): ACTIVE")
        else:
            print("  [WARN] Tier 1 - Tavily API: NOT CONFIGURED (add TAVILY_API_KEY for best AI search)")
        
        print("  [OK]   Tier 2 - Jina AI: ACTIVE (no key required)")
        
        if self.serper_api_key:
            print("  [OK]   Tier 3 - Serper.dev: ACTIVE")
        else:
            print("  [INFO] Tier 3 - Serper.dev: NOT CONFIGURED")
            
        print("  [OK]   Tier 4 - DuckDuckGo: ACTIVE (no key required)")
        
        if self.newsapi_key:
            print("  [OK]   NewsAPI (Threat Intel): ACTIVE")
        else:
            print("  [WARN] NewsAPI (Threat Intel): NOT CONFIGURED (add NEWSAPI_KEY)")

        print(f"\n[OK] TTS Backend: ACTIVE ({self.tts_backend})")
        print("[OK] Company Verification (WHOIS + MCA link + public-presence check): ACTIVE")

        if self.whatsapp_access_token and self.whatsapp_phone_number_id:
            print("[OK] WhatsApp scanner: ACTIVE")
        else:
            print("[WARN] WhatsApp scanner: NOT CONFIGURED")

        print("[WARN] Family SMS alerts: SIMULATED (logged only, no real provider configured)")
        print("[WARN] Real call ingestion (Exotel/Twilio): DISABLED (browser_mic only)")
        print("[WARN] Bhashini localization: NOT WIRED (using Groq native multilingual)")

        if self.dsp_voice_detection_enabled:
            print("[WARN] DSP Voice Detection (Bispectrum + Tremor): ENABLED (EXPERIMENTAL — "
                  "real-world validation showed inverted results; not reliable standalone)")
        else:
            print("[INFO] DSP Voice Detection (Bispectrum + Tremor): DISABLED (experimental, "
                  "set DSP_VOICE_DETECTION_ENABLED=true to re-enable for research)")
        print()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached after first call)."""
    return Settings()
