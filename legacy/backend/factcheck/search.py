"""
factcheck/search.py — Web verification of extracted scam claims.

Design:
  - Primary: Tavily API (semantic search, returns pre-extracted answer snippets)
  - Fallback: DuckDuckGo Instant Answer API (no key required, rate-limited)
  - Per-call claim cache: avoid re-searching identical scam scripts within a call
    session. Scammers often use scripted dialogs — caching saves API budget.

Cache key: SHA-256 of normalized claim text (category + entities + demands).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, TypedDict

import httpx

logger = logging.getLogger(__name__)

_DDGS_INSTANT_ANSWER_URL = "https://api.duckduckgo.com/"


class SearchResult(TypedDict):
    query: str
    results: List[Dict[str, str]]   # [{"title": ..., "url": ..., "snippet": ...}]
    source: str                      # "tavily" | "duckduckgo" | "cache"
    cached: bool


def _claim_cache_key(claim_data: dict) -> str:
    """Generate a stable cache key for a claim dict."""
    normalized = json.dumps(
        {k: claim_data.get(k) for k in ("category", "entities_claimed", "demands")},
        sort_keys=True,
    )
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _build_search_query(claim: dict) -> str:
    """Build a search query from an ExtractedClaim dict."""
    parts = []
    category = claim.get("category", "")
    entities = claim.get("entities_claimed", [])
    demands = claim.get("demands", [])
    authority = claim.get("claimed_authority", "")

    # India-specific context in query boosts relevance of official sources
    if category == "DIGITAL_ARREST":
        parts.append("digital arrest scam India CBI fake")
    elif category == "UPI_COLLECT_FRAUD":
        parts.append("UPI collect request scam India NPCI")
    elif category == "KYC_SIM_BLOCK":
        parts.append("KYC Aadhaar SIM block scam India TRAI")
    elif category == "ELECTRICITY_THREAT":
        parts.append("electricity disconnection scam India cyber crime")
    elif category == "COURIER_CUSTOMS":
        parts.append("parcel customs seizure scam India FedEx")
    elif category == "FAKE_JOB_TASK":
        parts.append("Telegram job scam India work from home fraud")
    elif category == "INVESTMENT_FRAUD":
        parts.append("investment trading scam India SEBI fraud")

    if authority:
        parts.append(f'"{authority}" scam impersonation')
    if entities:
        parts.extend(entities[:2])

    return " ".join(parts) + " India scam warning"


class SearchVerifier:
    """
    Claim verification engine with Tavily primary and DuckDuckGo fallback.
    Maintains a per-call in-memory cache.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, SearchResult] = {}

    async def verify_claim(self, claim: dict, call_id: str = "") -> SearchResult:
        """
        Search for web evidence about an extracted scam claim.

        Parameters
        ----------
        claim : dict
            ExtractedClaim dict from claim_extraction.py
        call_id : str
            For logging.

        Returns
        -------
        SearchResult dict
        """
        cache_key = _claim_cache_key(claim)
        if cache_key in self._cache:
            logger.debug(
                "Search cache hit for call_id=%r key=%s", call_id, cache_key
            )
            cached = self._cache[cache_key].copy()
            cached["cached"] = True
            return cached

        query = _build_search_query(claim)
        logger.info("Searching for claim evidence: %r (call_id=%s)", query, call_id)

        from core.config import get_settings
        cfg = get_settings()

        result = None
        if cfg.tavily_api_key:
            result = await _search_tavily(query, cfg.tavily_api_key)

        if result is None:
            result = await _search_duckduckgo(query)

        if result is None:
            result = SearchResult(
                query=query,
                results=[],
                source="none",
                cached=False,
            )

        self._cache[cache_key] = result
        return result


async def _search_tavily(query: str, api_key: str) -> Optional[SearchResult]:
    """Search via Tavily API — semantic search with pre-extracted snippets."""
    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=api_key)
        response = await client.search(
            query=query,
            search_depth="basic",
            max_results=5,
            include_domains=[
                "cybercrime.gov.in",
                "trai.gov.in",
                "npci.org.in",
                "cert-in.org.in",
                "mha.gov.in",
                "rbi.org.in",
                "sebi.gov.in",
                "pib.gov.in",
            ],  # Prefer official Indian government sources
        )
        results = [
            {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
            for r in response.get("results", [])
        ]
        return SearchResult(query=query, results=results, source="tavily", cached=False)

    except Exception as exc:
        logger.warning("Tavily search failed: %s — falling back to DuckDuckGo", exc)
        return None


async def _search_duckduckgo(query: str) -> Optional[SearchResult]:
    """
    Search via DuckDuckGo Instant Answer API (no key required).
    Limited to abstract/topic summaries — not full web results.
    """
    try:
        params = {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(_DDGS_INSTANT_ANSWER_URL, params=params)
            response.raise_for_status()
            data = response.json()

        results = []
        abstract = data.get("AbstractText", "")
        abstract_url = data.get("AbstractURL", "")
        if abstract:
            results.append({
                "title": data.get("AbstractSource", "DuckDuckGo"),
                "url": abstract_url,
                "snippet": abstract,
            })

        # Related topics
        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:100],
                    "url": topic.get("FirstURL", ""),
                    "snippet": topic.get("Text", ""),
                })

        return SearchResult(query=query, results=results, source="duckduckgo", cached=False)

    except Exception as exc:
        logger.error("DuckDuckGo search failed: %s", exc)
        return None
