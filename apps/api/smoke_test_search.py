import asyncio, os, sys, logging
logging.basicConfig(level=logging.INFO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    from core.config import get_settings
    cfg = get_settings()
    print("=" * 60)
    cfg.log_startup_summary()
    print("=" * 60)

    print("\n[TEST 1] verify_claim() with live APIs...")
    from factcheck.search import SearchVerifier
    verifier = SearchVerifier()
    claim = {
        "category": "CBI_DIGITAL_ARREST_SCAM",
        "entities_claimed": ["CBI"],
        "demands": ["digital arrest warrant", "transfer money"],
        "claimed_authority": "CBI Officer",
    }
    result = await verifier.verify_claim(claim, call_id="smoke-001")
    print(f"  query  : {result.get('query_used')}")
    print(f"  source : {result['source']}")
    print(f"  error  : {result['error']}")
    print(f"  hits   : {len(result['results'])}")
    for i, r in enumerate(result["results"], 1):
        print(f"  [{i}] Context Preview:")
        preview = r.get('body', '')[:200]
        print(f"       {preview.encode('ascii', 'ignore').decode('ascii')}...")
    
    if result["source"] != "None" and result["source"] != "Unknown" and result["results"]:
        print(f"\n  PASS - {result['source']} returned real results")
    else:
        print(f"\n  FAIL or STUB - source={result['source']}, hits={len(result['results'])}")

    print("\n[TEST 2] Second call...")
    r2 = await verifier.verify_claim(claim, call_id="smoke-001")
    print("  PASS - Returned results" if r2["results"] else "  FAIL - no results")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
