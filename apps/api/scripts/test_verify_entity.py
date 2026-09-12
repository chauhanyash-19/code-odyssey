"""
scripts/test_verify_entity.py — Smoke test for company_verification.py.

Run from apps/api/:
    python scripts/test_verify_entity.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_settings
from intel.company_verification import verify_entity


async def run_test(name: str, domain: str | None = None, label: str = ""):
    print(f"\n{'='*60}")
    print(f"Entity: {name}  [{label}]")
    if domain:
        print(f"Domain: {domain}")
    print("-" * 60)

    result = await verify_entity(name=name, domain=domain)

    print(f"  mca_search_url        : {result['mca_search_url']}")
    print(f"  domain_age_days       : {result['domain_age_days']}")
    print(f"  domain_flag           : {result['domain_flag']}")
    print(f"  public_presence_found : {result['public_presence_found']}")
    print(f"  public_presence_sources ({len(result['public_presence_sources'])}):")
    for url in result["public_presence_sources"][:3]:
        print(f"    - {url}")
    print(f"  confidence_note       :")
    print(f"    {result['confidence_note'][:300]}")


async def main():
    cfg = get_settings()
    print("\n[PhaseGuard - Entity Verification Smoke Test]")
    cfg.log_startup_summary()

    # Test 1: Well-known real entity
    await run_test(name="Google", domain="google.com", label="REAL - should have presence")

    # Test 2: Known Indian institution
    await run_test(name="Reserve Bank of India", domain="rbi.org.in", label="REAL - should have presence")

    # Test 3: Clearly fabricated scam entity
    await run_test(
        name="XYZ Global Refund Services",
        domain="xyzrefund-processingnow.com",
        label="FAKE - should have NO presence",
    )

    # Test 4: Impersonation pattern from claims
    await run_test(
        name="Google HR",
        domain=None,
        label="IMPERSONATION - might have no specific presence as 'Google HR'",
    )

    print(f"\n{'='*60}")
    print("Test complete.")


if __name__ == "__main__":
    asyncio.run(main())
