"""
core/config.py — Centralized settings loaded from environment variables.
Uses pydantic-settings so every value is type-validated at startup.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
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
    groq_llm_model: str = Field(default="llama-3.3-70b-versatile")

    # ── Tavily (search) ────────────────────────────────────────────────────────
    tavily_api_key: str = Field(default="", description="Tavily search API key")

    # ── Exotel (real-call ingestion, no hardware) ──────────────────────────────
    exotel_api_key: str = Field(default="", description="Exotel API key")
    exotel_api_token: str = Field(default="", description="Exotel API token")
    exotel_sid: str = Field(default="", description="Exotel Account SID")

    # ── MSG91 (family-alert SMS) ───────────────────────────────────────────────
    msg91_auth_key: str = Field(default="", description="MSG91 authentication key")
    msg91_sender_id: str = Field(default="PHSGRD", description="MSG91 sender ID")

    # ── Twilio (SMS fallback + Media Streams) ─────────────────────────────────
    twilio_account_sid: str = Field(default="")
    twilio_auth_token: str = Field(default="")
    twilio_phone_number: str = Field(default="")

    # ── Bhashini (India language API) ─────────────────────────────────────────
    bhashini_user_id: str = Field(default="")
    bhashini_api_key: str = Field(default="")
    bhashini_pipeline_id: str = Field(default="")

    # ── Secret manager backend ────────────────────────────────────────────────
    # Rationale: never commit raw secrets to source in non-dev environments.
    secret_manager_backend: Literal["env", "doppler", "infisical", "gcp", "aws"] = (
        Field(default="env")
    )

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached after first call)."""
    return Settings()
