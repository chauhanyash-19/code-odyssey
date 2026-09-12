"""
intel/company_verification.py — Entity/company verification signals module.

PURPOSE:
  This module produces SIGNALS FOR HUMAN JUDGMENT, not automated fraud
  determinations. The goal is to give the protected user and later
  investigators useful leads, not to make a legal claim about any specific
  company or person.

Checks performed:
  1. MCA Portal search link    — direct URL to verify company registration
                                   manually (no scraping, .gov.in is fragile).
  2. WHOIS domain age check    — flags recently registered domains (<6 months)
                                   as a mild caution signal.
  3. Public presence check     — uses the 3-tier search fallback to look for
                                   public news/wiki coverage of the claimed entity.
                                   Absence of coverage is a signal, not proof.

Output of verify_entity():
  {
    entity_name: str,
    mca_search_url: str,
    domain: str | None,
    domain_age_days: int | None,
    domain_flag: str | None,     # e.g. "recently registered (<6 months)"
    public_presence_found: bool,
    public_presence_sources: list[str],
    confidence_note: str,
  }

IMPORTANT: All fields are provided as investigative signals only.
None of them constitute legal evidence of fraud or legitimacy.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

_RECENT_DOMAIN_THRESHOLD_DAYS = 180  # domains younger than 6 months flagged as caution

_MCA_SEARCH_BASE = (
    "https://www.mca.gov.in/mcafoportal/companyLLPMasterData.do"
    "?companyname={name}"
)
_MCA_ALT_BASE = (
    "https://efiling.mca.gov.in/eFiling/helpdeskdata.do"
    "?companyname={name}"
)


# ── WHOIS domain age ──────────────────────────────────────────────────────────

def _check_domain_age(domain: str) -> tuple[Optional[int], Optional[str]]:
    """
    Look up WHOIS data for a domain and return (age_days, flag).
    Returns (None, None) if WHOIS data is unavailable or privacy-shielded.

    This is a SIGNAL: recently registered domains are more commonly
    associated with scam infrastructure, but many legitimate businesses
    also use new domains.
    """
    try:
        import whois  # python-whois

        w = whois.whois(domain)
        creation_date = w.creation_date

        if creation_date is None:
            return None, "WHOIS: creation date unavailable (privacy-shielded or unsupported TLD)"

        # python-whois sometimes returns a list
        if isinstance(creation_date, list):
            creation_date = creation_date[0]

        if not isinstance(creation_date, datetime):
            return None, "WHOIS: creation date in unexpected format"

        # Normalize to UTC
        if creation_date.tzinfo is None:
            creation_date = creation_date.replace(tzinfo=timezone.utc)

        age_days = (datetime.now(timezone.utc) - creation_date).days

        if age_days < _RECENT_DOMAIN_THRESHOLD_DAYS:
            flag = (
                f"recently registered ({age_days} days old) — exercise caution; "
                f"scam sites are typically short-lived"
            )
        elif age_days < 365:
            flag = f"registered {age_days} days ago (under 1 year old — mild caution)"
        else:
            flag = None  # established domain, no special flag

        return age_days, flag

    except Exception as exc:
        logger.debug("WHOIS lookup failed for %r: %s", domain, exc)
        return None, "WHOIS: lookup failed or registry unsupported"


# ── MCA search URL ────────────────────────────────────────────────────────────

def _build_mca_search_url(name: str) -> str:
    """
    Build a direct MCA Portal search URL for manual verification.
    No web scraping performed — this is a human-usable reference link.
    """
    encoded = quote_plus(name.strip())
    # MCA21 v3 portal search
    return (
        f"https://www.mca.gov.in/mcafoportal/viewCompanyMasterData.do"
        f"?companyname={encoded}"
    )


# ── Public presence cross-check ───────────────────────────────────────────────

async def _check_presence_split(
    name: str,
    context_terms: Optional[str] = None,
) -> tuple[bool, bool, List[str]]:
    """
    Runs TWO separate searches for the entity:
      1. Scam/fraud reports:  '{name} {context_terms} scam OR fraud reported India'
      2. Official policy:     '{name} {context_terms} official policy India'

    Returns (scam_found: bool, policy_found: bool, sources: list[str]).
    """
    from factcheck.search import execute_resilient_search

    # Truncate context_terms at word boundary (max 60 chars) so queries stay
    # compact enough for Tavily to respond within timeout.
    base = f'"{name}"'
    if context_terms:
        short_ctx = context_terms[:60].rsplit(" ", 1)[0] if len(context_terms) > 60 else context_terms
        base += f' {short_ctx}'

    # --- Query 1: scam / fraud reports ---
    scam_query = f'{base} scam OR fraud reported India'
    # --- Query 2: official policy ---
    policy_query = f'{base} official policy India'

    # Helper: run search AND verify entity name literally appears in snippets.
    # Tavily advanced-search returns topically related content even for
    # non-existent entities, so a raw success=True is not enough.
    name_lower = name.strip('"').lower()

    async def _search_with_name_check(query: str) -> bool:
        try:
            result = await execute_resilient_search(query)
            if not (result and result.get("success")):
                return False
            context: str = result.get("context", "")
            # Entity name must literally appear in the returned snippets
            return name_lower in context.lower()
        except Exception as exc:
            logger.warning("Search failed for %r: %s", name, exc)
            return False

    scam_task = asyncio.create_task(_search_with_name_check(scam_query))
    policy_task = asyncio.create_task(_search_with_name_check(policy_query))
    
    scam_res, policy_res = await asyncio.gather(scam_task, policy_task, return_exceptions=True)
    
    if isinstance(scam_res, Exception):
        logger.warning("Scam-check search failed for %r: %s", name, scam_res)
        scam_found = False
    else:
        scam_found = scam_res
        
    if isinstance(policy_res, Exception):
        logger.warning("Policy-check search failed for %r: %s", name, policy_res)
        policy_found = False
    else:
        policy_found = policy_res


    sources: List[str] = []
    if scam_found:
        sources.append("scam-reports search")
    if policy_found:
        sources.append("official-policy search")

    return scam_found, policy_found, sources


# Keep backward-compat thin wrapper used by other callers
async def _check_public_presence(name: str, context_terms: Optional[str] = None) -> tuple[bool, List[str]]:
    scam_found, policy_found, sources = await _check_presence_split(name, context_terms)
    return (scam_found or policy_found), sources



# ── Main entry point ──────────────────────────────────────────────────────────

async def verify_entity(
    name: str,
    domain: Optional[str] = None,
    sub_entity: Optional[str] = None,
    context_terms: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Produce a verification signal dossier for a claimed entity/company.

    Parameters
    ----------
    name : str
        The parent entity name (e.g. "Google").
    domain : str or None
        An optional domain/URL associated with the entity.
    sub_entity: str or None
        An optional claimed sub-entity or authority (e.g. "Google HR").
    Returns
    -------
    dict with keys:
        entity_name, mca_search_url, domain, domain_age_days,
        domain_flag, public_presence_found, public_presence_sources,
        confidence_note

    IMPORTANT: All fields are investigative signals, not legal conclusions.
    """
    logger.info("Verifying entity: %r (sub_entity=%r, domain=%r)", name, sub_entity, domain)

    # ── MCA link (no scraping, human-usable) ──────────────────────────────────
    mca_url = _build_mca_search_url(name)

    # ── WHOIS domain age ──────────────────────────────────────────────────────
    domain_age_days: Optional[int] = None
    domain_flag: Optional[str]     = None

    if domain:
        # Strip scheme/path — WHOIS only needs the bare domain
        bare_domain = domain.removeprefix("https://").removeprefix("http://").split("/")[0].strip()
        if bare_domain:
            domain_age_days, domain_flag = _check_domain_age(bare_domain)

    # ── Public presence check — split into scam vs policy ────────────────────
    parent_task = asyncio.create_task(_check_presence_split(name, context_terms))
    
    sub_task = None
    if sub_entity and sub_entity.lower() != name.lower():
        sub_task = asyncio.create_task(_check_presence_split(sub_entity, context_terms))

    parent_scam, parent_policy, presence_sources = await parent_task
    presence_found = parent_scam or parent_policy

    sub_scam:   Optional[bool] = None
    sub_policy: Optional[bool] = None
    if sub_task:
        sub_scam, sub_policy, _ = await sub_task

    # ── Confidence note builder ───────────────────────────────────────────────
    signals: List[str] = []

    if domain_flag:
        signals.append(f"Domain: {domain_flag}.")

    def _fmt_split(scam: Optional[bool], policy: Optional[bool], label: str) -> str:
        scam_str   = "scam/fraud reports: FOUND"       if scam   else "scam/fraud reports: none"
        policy_str = "official policy mentions: FOUND" if policy else "official policy mentions: none"
        return f"{label} -> {scam_str} | {policy_str}"

    # Parent entity line
    signals.append(_fmt_split(parent_scam, parent_policy, f'"{name}"'))

    # Sub-entity line (if checked)
    if sub_entity and sub_entity.lower() != name.lower() and sub_scam is not None:
        signals.append(_fmt_split(sub_scam, sub_policy, f'sub-entity "{sub_entity}"'))

        # Strong impersonation signal: parent real but sub-entity has zero trace
        if presence_found and not sub_scam and not sub_policy:
            signals.append(
                f"⚠ IMPERSONATION SIGNAL: Parent '{name}' has web presence but "
                f"claimed sub-entity '{sub_entity}' has NO scam reports AND no official policy trace."
            )

    note = (
        "SIGNAL ONLY — for human judgment: "
        + " | ".join(signals)
        + " | Verify manually via MCA link before drawing conclusions."
    )

    return {
        "entity_name":            name,
        "mca_search_url":         mca_url,
        "domain":                 domain,
        "domain_age_days":        domain_age_days,
        "domain_flag":            domain_flag,
        "public_presence_found":  presence_found,
        "public_presence_sources": presence_sources[:5],
        "confidence_note":        note,
    }
