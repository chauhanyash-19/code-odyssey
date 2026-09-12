import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    from factcheck.search import _search_tavily, _search_serper, _search_ddg
    
    query = "CBI_DIGITAL_ARREST_SCAM CBI CBI Officer"
    print(f"Comparing search quality for query: '{query}'\n")
    
    print("--- 1. Tavily (AI Search) ---")
    try:
        t_res = await _search_tavily(query)
        ctx = t_res.get("context", "")
        print(ctx.encode('ascii', 'ignore').decode('ascii'))
    except Exception as e:
        print(f"Tavily failed: {e}")
        
    print("\n--- 2. Serper.dev (Google Raw) ---")
    try:
        s_res = await _search_serper(query)
        ctx = s_res.get("context", "")
        print(ctx.encode('ascii', 'ignore').decode('ascii'))
    except Exception as e:
        print(f"Serper failed: {e}")

    print("\n--- 3. DuckDuckGo (Raw) ---")
    try:
        d_res = await _search_ddg(query)
        ctx = d_res.get("context", "")
        print(ctx.encode('ascii', 'ignore').decode('ascii'))
    except Exception as e:
        print(f"DDG failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
