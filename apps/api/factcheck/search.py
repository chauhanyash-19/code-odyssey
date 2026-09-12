import logging
import asyncio
import os
import traceback
from typing import Dict, Any

import httpx
from duckduckgo_search import DDGS
from tavily import TavilyClient

logger = logging.getLogger(__name__)

async def _search_tavily(query: str) -> dict:
    from core.config import get_settings
    tavily_api_key = get_settings().tavily_api_key
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY not set")
    
    async with httpx.AsyncClient(timeout=2.5) as client:
        payload = {"api_key": tavily_api_key, "query": query, "search_depth": "advanced"}
        try:
            resp = await client.post("https://api.tavily.com/search", json=payload)
            resp.raise_for_status()
            response = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Tavily HTTP Error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Tavily Exception: {type(e).__name__} - {str(e)}")
            raise
        
    snippets = [res.get("content", "") for res in response.get("results", []) if res.get("content")]
    context = "\n".join(snippets)
    if not context.strip():
        raise ValueError("Empty results")
    return {"source_tier": "Tavily", "context": context[:2500], "success": True}

async def _search_jina(query: str) -> dict:
    from core.config import get_settings
    jina_api_key = get_settings().jina_api_key
    if not jina_api_key:
        raise ValueError("JINA_API_KEY not set")
        
    async with httpx.AsyncClient(timeout=2.0) as client:
        headers = {"Accept": "text/plain", "X-Retain-Images": "none", "Authorization": f"Bearer {jina_api_key}"}
        resp = await client.get(f"https://s.jina.ai/{query}", headers=headers)
        resp.raise_for_status()
        context = resp.text[:2500]
        if not context.strip():
            raise ValueError("Empty results")
        return {"source_tier": "Jina AI", "context": context, "success": True}

async def _search_serper(query: str) -> dict:
    from core.config import get_settings
    serper_api_key = get_settings().serper_api_key
    if not serper_api_key:
        raise ValueError("SERPER_API_KEY not set")
    async with httpx.AsyncClient(timeout=2.0) as client:
        headers = {"X-API-KEY": serper_api_key, "Content-Type": "application/json"}
        payload = {"q": query, "gl": "in", "hl": "en", "num": 3}
        resp = await client.post("https://google.serper.dev/search", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("organic", [])[:3]
        snippets = [item.get("snippet", "") for item in items if item.get("snippet")]
        context = "\n".join(snippets)
        if not context.strip():
            raise ValueError("Empty results")
        return {"source_tier": "Serper.dev", "context": context[:2500], "success": True}

async def _search_ddg(query: str) -> dict:
    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(None, lambda: DDGS(timeout=2.0).text(query, max_results=3))
    snippets = [res.get("body", "") for res in results if res.get("body")]
    context = "\n".join(snippets)
    if not context.strip():
        raise ValueError("Empty results")
    return {"source_tier": "DuckDuckGo", "context": context[:2500], "success": True}

async def execute_resilient_search(query: str) -> dict:
    """
    Sequential Fallback Search Pipeline:
    Tries Tavily first. If it fails or times out, falls back to Serper, then DuckDuckGo, then Jina.
    """
    logger.info(f"Executing search fallback chain for: {query}")
    
    # 1. Tavily (AI Search - Best Quality)
    try:
        res = await _search_tavily(query)
        if res.get("success"):
            logger.info("Search succeeded via Tavily")
            return res
    except Exception as e:
        logger.warning(f"Tavily search failed: {type(e).__name__} - {str(e)}")
        
    # 2. Serper.dev (Google Raw)
    try:
        res = await _search_serper(query)
        if res.get("success"):
            logger.info("Search succeeded via Serper.dev")
            return res
    except Exception as e:
        logger.warning(f"Serper search failed: {type(e).__name__} - {str(e)}")

    # 3. DuckDuckGo (Raw)
    try:
        res = await _search_ddg(query)
        if res.get("success"):
            logger.info("Search succeeded via DuckDuckGo")
            return res
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {type(e).__name__} - {str(e)}")

    # 4. Jina AI (Raw Text)
    try:
        res = await _search_jina(query)
        if res.get("success"):
            logger.info("Search succeeded via Jina AI")
            return res
    except Exception as e:
        logger.warning(f"Jina AI search failed: {type(e).__name__} - {str(e)}")

    logger.error("All search tiers failed")
    return {
        "source_tier": "None",
        "context": "web verification unavailable",
        "success": False
    }

class SearchVerifier:
    async def verify_claim(self, claim: dict, call_id: str = None) -> dict:
        if isinstance(claim, dict):
            parts = []
            if claim.get('category'): parts.append(claim.get('category'))
            
            # Deduplicate entities
            for e in claim.get('entities_claimed', []):
                if e and e not in parts: parts.append(e)
                
            authority = claim.get('claimed_authority', '')
            if authority and authority not in parts: parts.append(authority)
            
            query = " ".join([str(p) for p in parts if p]).strip()
        else:
            query = str(claim)
            
        if not query:
            query = "scam check"
            
        try:
            # Global latency budget: max 4.0 seconds across all tiers
            result = await asyncio.wait_for(execute_resilient_search(query), timeout=4.0)
        except asyncio.TimeoutError:
            logger.error(f"Global search timeout (4.0s) exceeded for query: {query}")
            result = {"source_tier": "Timeout", "context": "", "success": False}
            
        return {
            "query_used": query,
            "source": result.get("source_tier", "Unknown"),
            "context": result.get("context", ""),
            "results": [{"body": result.get("context", "")}] if result.get("context") else [],
            "error": None if result.get("success") else "Search failed"
        }
