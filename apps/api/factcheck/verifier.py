import os
import json
import logging
import asyncio
from typing import Dict, Any

from groq import AsyncGroq
from .search import execute_resilient_search

logger = logging.getLogger(__name__)

class FactCheckVerifier:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        if not self.api_key:
            logger.warning("GROQ_API_KEY not set. FactCheckVerifier will not be able to call Groq API.")
        self.client = AsyncGroq(api_key=self.api_key)
        self.model = "openai/gpt-oss-120b"

    async def verify_transcript(self, transcript: str) -> Dict[str, Any]:
        """
        Orchestrates the entire fact-checking flow:
        1. Extract claim and form search query.
        2. Execute resilient 3-tier search.
        3. Synthesize final verdict using the search context.
        """
        if not self.api_key:
            return {"error": "GROQ_API_KEY is not configured"}

        # Step 1: Claim Extraction
        search_query = await self._extract_claim(transcript)
        if not search_query:
             logger.info("No actionable claim found in transcript.")
             return {"error": "No actionable claim found"}

        logger.info(f"Extracted search query: {search_query}")

        # Step 2: Search Execution
        search_result = await execute_resilient_search(search_query)
        logger.info(f"Search completed. Tier used: {search_result.get('source_tier')}")

        if not search_result.get("success"):
            logger.warning("Search failed to retrieve context.")
            return {"error": "Failed to retrieve search results"}

        # Step 3: Verdict Synthesis
        verdict = await self._synthesize_verdict(transcript, search_result)
        return verdict

    async def _extract_claim(self, transcript: str) -> str:
        """
        Extract entity/claim and form a targeted search query from the transcript.
        """
        prompt = f"""
Given the following transcript from a phone call, identify any suspicious claims (e.g., demands for money, fake hiring fees, digital arrest threats). 
If a suspicious claim exists, extract the core entities and formulate a concise web search query to verify the claim's authenticity (e.g., official policy of the company).
If no suspicious claim is found, return an empty string.

Transcript:
"{transcript}"

Respond ONLY with the search query text, or empty string. Do not include quotes or conversational text.
"""
        try:
            response = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert scam detection AI."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=0.1,
                max_tokens=50
            )
            query = response.choices[0].message.content.strip()
            return query
        except Exception as e:
            logger.error(f"Error during claim extraction: {e}")
            return ""

    async def _synthesize_verdict(self, transcript: str, search_result: dict) -> Dict[str, Any]:
        """
        Synthesize the final verdict using Llama-3.3 based on transcript and search context.
        """
        context = search_result.get("context", "")
        source_tier = search_result.get("source_tier", "Unknown")
        
        prompt = f"""
You are an expert scam detection AI. Analyze the phone call transcript and the provided web search context to determine if the call is a scam.

Transcript:
"{transcript}"

Web Search Context (Source: {source_tier}):
"{context}"

Return a JSON object strictly adhering to this format:
{{
  "is_scam": true/false,
  "confidence": 0.0 to 1.0,
  "risk_level": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
  "title": "Short title describing the detection",
  "explanation": "Brief explanation of why it is or is not a scam, referencing the policy/context",
  "source_used": "{source_tier}"
}}

Respond ONLY with valid JSON.
"""
        try:
            response = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a precise JSON-producing AI. Produce only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            verdict_json = json.loads(content)
            
            # Ensure the source used accurately reflects the search tier
            verdict_json["source_used"] = source_tier
            
            return verdict_json
        except Exception as e:
            logger.error(f"Error during verdict synthesis: {e}")
            return {"error": "Failed to synthesize verdict"}

