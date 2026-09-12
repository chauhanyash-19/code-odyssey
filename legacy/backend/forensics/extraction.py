"""
forensics/extraction.py — LLM-based extraction of scam identifiers from transcript.

Purpose:
  Final LLM pass over the complete call transcript to extract all identifiers
  relevant to a police complaint / FIR:
    - UPI IDs (e.g. scammer@upi)
    - Phone numbers
    - Bank account numbers
    - QR code references
    - Alleged organization names (impersonated entities)
    - Website/URL references
    - Person names claimed by the scammer

Output is structured JSON suitable for inclusion in the forensic PDF dossier
and for submission to the National Cyber Crime Portal (1930).

Note: Regex extraction (deterministic) runs first; LLM only adds identifiers
that regex missed. This gives a reliable baseline that the LLM supplements.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, TypedDict

logger = logging.getLogger(__name__)

# ── Deterministic regex patterns ───────────────────────────────────────────────
_UPI_PATTERN = re.compile(r"[\w.\-+]{2,256}@[\w]{2,64}", re.IGNORECASE)
_PHONE_PATTERN = re.compile(r"(?:\+91[\s\-]?)?[6-9]\d{9}")
_BANK_ACCOUNT_PATTERN = re.compile(r"\b\d{9,18}\b")  # 9-18 digit bank account numbers
_URL_PATTERN = re.compile(r"https?://[^\s]+|www\.[^\s]+", re.IGNORECASE)
_IFSC_PATTERN = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")  # IFSC code


class ExtractedIdentifiers(TypedDict):
    upi_ids: List[str]
    phone_numbers: List[str]
    bank_accounts: List[str]
    ifsc_codes: List[str]
    urls: List[str]
    impersonated_entities: List[str]
    caller_claimed_names: List[str]
    additional_notes: str


_SYSTEM_PROMPT = """You are a forensic analyst extracting evidence from a scam call transcript.

Extract ALL identifiers a victim or police officer would need to file a complaint.
Output ONLY valid JSON — no prose.

Focus on:
- UPI IDs (format: something@upi or something@bank)
- Phone numbers (scammer's numbers or numbers they asked victim to call)
- Organization names they claimed to represent
- Names they claimed to be
- Any website or app they mentioned
- Any specific financial details (account numbers, IFSC codes)

If something is uncertain, still include it with a note.
"""

_USER_PROMPT = """{wrapped_transcript}

Extract forensic identifiers as JSON:
{{
  "upi_ids": [],
  "phone_numbers": [],
  "bank_accounts": [],
  "ifsc_codes": [],
  "urls": [],
  "impersonated_entities": [],
  "caller_claimed_names": [],
  "additional_notes": "<any other relevant details>"
}}"""


def _regex_extract(transcript: str) -> Dict[str, List[str]]:
    """Run all deterministic regex patterns on the transcript."""
    return {
        "upi_ids": list(set(_UPI_PATTERN.findall(transcript))),
        "phone_numbers": list(set(_PHONE_PATTERN.findall(transcript))),
        "bank_accounts": list(set(_BANK_ACCOUNT_PATTERN.findall(transcript))),
        "ifsc_codes": list(set(_IFSC_PATTERN.findall(transcript))),
        "urls": list(set(_URL_PATTERN.findall(transcript))),
    }


def _merge_identifiers(
    regex_result: Dict[str, List[str]],
    llm_result: Dict[str, Any],
) -> ExtractedIdentifiers:
    """Merge regex and LLM results, deduplicating each field."""
    return ExtractedIdentifiers(
        upi_ids=list(set(regex_result.get("upi_ids", []) + llm_result.get("upi_ids", []))),
        phone_numbers=list(
            set(regex_result.get("phone_numbers", []) + llm_result.get("phone_numbers", []))
        ),
        bank_accounts=list(
            set(regex_result.get("bank_accounts", []) + llm_result.get("bank_accounts", []))
        ),
        ifsc_codes=list(
            set(regex_result.get("ifsc_codes", []) + llm_result.get("ifsc_codes", []))
        ),
        urls=list(set(regex_result.get("urls", []) + llm_result.get("urls", []))),
        impersonated_entities=llm_result.get("impersonated_entities", []),
        caller_claimed_names=llm_result.get("caller_claimed_names", []),
        additional_notes=llm_result.get("additional_notes", ""),
    )


async def extract_identifiers(
    full_transcript: str,
    call_id: str = "",
) -> ExtractedIdentifiers:
    """
    Extract all forensically relevant identifiers from the full call transcript.

    Parameters
    ----------
    full_transcript : str
        Complete transcript of the call (all STT chunks concatenated).
    call_id : str
        For logging.

    Returns
    -------
    ExtractedIdentifiers dict
    """
    # Step 1: Deterministic regex extraction (always runs, LLM-independent)
    regex_result = _regex_extract(full_transcript)
    logger.info(
        "Extraction[%s]: regex found upi=%d phones=%d urls=%d",
        call_id,
        len(regex_result.get("upi_ids", [])),
        len(regex_result.get("phone_numbers", [])),
        len(regex_result.get("urls", [])),
    )

    # Step 2: LLM extraction for entities/names that regex can't catch
    from core.config import get_settings
    from factcheck.injection_guard import safe_transcript_for_prompt

    cfg = get_settings()
    if not cfg.groq_api_key:
        logger.warning("Extraction: GROQ_API_KEY not set — returning regex-only results")
        return ExtractedIdentifiers(
            **regex_result,
            impersonated_entities=[],
            caller_claimed_names=[],
            additional_notes="LLM extraction skipped (no API key)",
        )

    wrapped_transcript, _ = safe_transcript_for_prompt(full_transcript)
    user_prompt = _USER_PROMPT.format(wrapped_transcript=wrapped_transcript)

    from groq import AsyncGroq

    client = AsyncGroq(api_key=cfg.groq_api_key)

    try:
        response = await client.chat.completions.create(
            model=cfg.groq_llm_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,   # Deterministic for forensic reliability
            max_tokens=512,
            response_format={"type": "json_object"},
        )
        llm_result = json.loads(response.choices[0].message.content or "{}")
        merged = _merge_identifiers(regex_result, llm_result)
        logger.info(
            "Extraction[%s]: merged result: upi=%d phones=%d entities=%d",
            call_id,
            len(merged["upi_ids"]),
            len(merged["phone_numbers"]),
            len(merged["impersonated_entities"]),
        )
        return merged

    except Exception as exc:
        logger.error("Extraction[%s]: LLM error: %s — using regex-only results", call_id, exc)
        return ExtractedIdentifiers(
            **regex_result,
            impersonated_entities=[],
            caller_claimed_names=[],
            additional_notes=f"LLM extraction failed: {exc}",
        )
