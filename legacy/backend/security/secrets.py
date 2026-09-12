"""
security/secrets.py — Abstracted secret loader.

Rationale: never hardcode or read API keys directly from raw .env in
non-development deployments. This module provides a single get_secret()
interface that can be backed by:
  - "env"       : plain environment variables (dev only)
  - "doppler"   : Doppler CLI / SDK (secrets.doppler.com)
  - "infisical" : Infisical (infisical.com, self-hostable)
  - "gcp"       : Google Cloud Secret Manager
  - "aws"       : AWS Secrets Manager

Switch backends via SECRET_MANAGER_BACKEND env var — callers are unaffected.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=256)
def get_secret(key: str) -> str:
    """
    Retrieve a secret value by key.  The backend is selected at startup
    from the SECRET_MANAGER_BACKEND environment variable.

    Results are cached in-process (lru_cache) to avoid repeated network calls.
    Clear the cache with get_secret.cache_clear() if secrets are rotated.
    """
    backend = os.getenv("SECRET_MANAGER_BACKEND", "env").lower()

    if backend == "env":
        return _from_env(key)
    elif backend == "doppler":
        return _from_doppler(key)
    elif backend == "infisical":
        return _from_infisical(key)
    elif backend == "gcp":
        return _from_gcp(key)
    elif backend == "aws":
        return _from_aws(key)
    else:
        logger.warning("Unknown SECRET_MANAGER_BACKEND=%r, falling back to env", backend)
        return _from_env(key)


# ── Backends ───────────────────────────────────────────────────────────────────

def _from_env(key: str) -> str:
    """Read from OS environment (dev only)."""
    value = os.getenv(key, "")
    if not value:
        logger.warning("Secret %r not found in environment", key)
    return value


def _from_doppler(key: str) -> str:
    """
    Read from Doppler via the Doppler Python SDK.
    Requires: pip install doppler-sdk
    The SDK reads DOPPLER_TOKEN from the environment automatically.
    """
    try:
        from dopplersdk import DopplerSDK  # type: ignore[import]

        sdk = DopplerSDK()
        result = sdk.secrets.get(project="phaseguard", config="production", name=key)
        return result.secret.value or ""
    except Exception as exc:
        logger.error("Doppler secret fetch failed for %r: %s — falling back to env", key, exc)
        return _from_env(key)


def _from_infisical(key: str) -> str:
    """
    Read from Infisical via the Infisical Python SDK.
    Requires: pip install infisical-python
    """
    try:
        from infisical import InfisicalClient  # type: ignore[import]

        client = InfisicalClient(token=os.getenv("INFISICAL_TOKEN", ""))
        secret = client.get_secret(key, environment="prod", path="/")
        return secret.secret_value or ""
    except Exception as exc:
        logger.error("Infisical secret fetch failed for %r: %s — falling back to env", key, exc)
        return _from_env(key)


def _from_gcp(key: str) -> str:
    """
    Read from Google Cloud Secret Manager.
    Requires: pip install google-cloud-secret-manager
    Uses GCP_PROJECT_ID env var.
    """
    try:
        from google.cloud import secretmanager  # type: ignore[import]

        project_id = os.getenv("GCP_PROJECT_ID", "")
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{key}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("utf-8")
    except Exception as exc:
        logger.error("GCP secret fetch failed for %r: %s — falling back to env", key, exc)
        return _from_env(key)


def _from_aws(key: str) -> str:
    """
    Read from AWS Secrets Manager.
    Requires: pip install boto3
    """
    try:
        import json

        import boto3  # type: ignore[import]

        client = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION", "ap-south-1"))
        response = client.get_secret_value(SecretId=key)
        secret_string = response.get("SecretString", "{}")
        data = json.loads(secret_string)
        return data.get(key, "")
    except Exception as exc:
        logger.error("AWS secret fetch failed for %r: %s — falling back to env", key, exc)
        return _from_env(key)
