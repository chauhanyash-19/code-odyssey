import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from factcheck.claim_extraction import ClaimExtractor
from factcheck.search import SearchVerifier
from factcheck.verdict import generate_verdict

async def test_pipeline():
    print("\n--- Testing E2E Pipeline (Groq + Search) ---")
    
    transcript = (
        "Hello, I am calling from Google HR department. Your account has an "
        "issue and you need to pay a processing fee of 500 rupees immediately to "
        "avoid suspension."
    )
    print(f"Input Transcript: '{transcript}'")
    
    # 1. Extraction (Groq)
    print("\n1. Extracting claims...")
    try:
        extractor = ClaimExtractor(debounce_chars=0)
        extraction_result = await extractor.extract(transcript, call_id="test-e2e")
        print("Extraction Result:")
        print(extraction_result)
        
        # 2. Search Verification
        print("\n2. Searching for evidence...")
        verifier = SearchVerifier()
        search_result = await verifier.verify_claim(extraction_result, call_id="test-e2e")
        print(f"Search Source: {search_result['source']}")
        print(f"Found {len(search_result['results'])} hits.")
        
        # 3. Final Verdict (Groq)
        print("\n3. Generating final verdict...")
        verdict_result = await generate_verdict(
            transcript=transcript,
            claim=extraction_result,
            search_result=search_result,
            call_id="test-e2e"
        )
        print("\nFINAL VERDICT:")
        print(verdict_result)
        
    except Exception as e:
        print(f"\nPipeline Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
