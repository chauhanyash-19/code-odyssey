import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_settings
from factcheck.search import SearchVerifier

async def test_search():
    print("\n--- Testing Google Custom Search ---")
    cfg = get_settings()
    if not cfg.google_search_api_key or not cfg.google_search_engine_id:
        print("FAIL: Google keys not set.")
        return
        
    verifier = SearchVerifier()
    claim = {
        "category": "FAKE_JOB_TASK",
        "entities_claimed": ["Google HR"],
        "demands": ["processing fee"],
        "claimed_authority": "Google HR",
    }
    
    print("1. Real search with real keys...")
    result = await verifier.verify_claim(claim, call_id="test-001")
    print(f"  source : {result['source']}")
    print(f"  cached : {result['cached']}")
    print(f"  hits   : {len(result['results'])}")
    for i, r in enumerate(result["results"], 1):
        print(f"  [{i}] {r['title']}")
        print(f"       {r['url']}")
    
    print("\n2. Graceful fallback with blank key...")
    orig = cfg.google_search_api_key
    cfg.google_search_api_key = ""
    v2 = SearchVerifier()
    r3 = await v2.verify_claim({"category": "DIGITAL_ARREST"}, call_id="test-002")
    cfg.google_search_api_key = orig
    print(f"  source : {r3['source']}")
    if r3["source"] == "stub":
        print("  PASS - stub fallback worked")
    else:
        print("  FAIL - expected stub")

if __name__ == "__main__":
    asyncio.run(test_search())
