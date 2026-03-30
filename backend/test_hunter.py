import asyncio
from app.services.hunter_io import find_email, verify_email

async def main():
    print("Testing Hunter.io APIs...")
    
    # 1. Test Email Finder
    print("\n--- Testing Email Finder ---")
    print("Looking for: Alexis Ohanian @ reddit.com")
    finder_res = await find_email("reddit.com", "Alexis", "Ohanian")
    print("Result:", finder_res)
    
    # 2. Test Email Verifier
    print("\n--- Testing Email Verifier ---")
    print("Verifying: patrick@stripe.com")
    verifier_res = await verify_email("patrick@stripe.com")
    print("Result:", verifier_res)

if __name__ == "__main__":
    asyncio.run(main())
