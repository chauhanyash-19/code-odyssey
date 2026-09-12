import asyncio
from factcheck.claim_extraction import ClaimExtractor

async def main():
    phrases = [
        "Mera pension PF ka paisa atka hua hai, aadhaar verify karna hai",
        "Scan this QR code to receive the payment for the sofa on OLX",
        "Your GST return is pending, pay the fine or face arrest",
        "Please enter your u.p.i pin on the keypad to continue",
        "Verify the small number on the back of the card to unblock it"
    ]
    
    extractor = ClaimExtractor()
    for phrase in phrases:
        print(f"\nTesting phrase: '{phrase}'")
        res = await extractor.extract(phrase, call_id="test2")
        if res:
            print(f"Category: {res.category.value if hasattr(res.category, 'value') else res.category}")
            print(f"Entities: {res.entities_claimed}")
            print(f"Confidence: {res.confidence}")
            print(f"Critical: {res.critical}")
        else:
            print("No claim extracted or timed out.")

if __name__ == "__main__":
    asyncio.run(main())
