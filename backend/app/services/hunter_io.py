import os
import httpx
from urllib.parse import urlparse
from app.config import get_settings

async def find_email(domain: str, first_name: str, last_name: str) -> dict | None:
    """Find an email using Hunter.io Email Finder."""
    settings = get_settings()
    if not settings.hunter_api_key:
        return None
        
    url = "https://api.hunter.io/v2/email-finder"
    params = {
        "domain": domain,
        "first_name": first_name,
        "last_name": last_name,
        "api_key": settings.hunter_api_key
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json().get("data", {})
                return {
                    "email": data.get("email"),
                    "score": data.get("score"),    # 0 to 100
                    "position": data.get("position")
                }
            elif response.status_code in [401, 429]:
                print(f"[Hunter.io] Rate limited or Unauthorized on Finder ({response.status_code})")
        except Exception as e:
            print(f"[Hunter.io] Error during Email Finder: {e}")
    return None

async def verify_email(email: str) -> dict | None:
    """Verify an email using Hunter.io Email Verifier."""
    settings = get_settings()
    if not settings.hunter_api_key:
        return None
        
    url = "https://api.hunter.io/v2/email-verifier"
    params = {
        "email": email,
        "api_key": settings.hunter_api_key
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json().get("data", {})
                return {
                    "status": data.get("status"),  # valid, invalid, accept_all, webmail, disposable, unknown
                    "score": data.get("score")     # 0 to 100
                }
            elif response.status_code in [401, 429]:
                print(f"[Hunter.io] Rate limited or Unauthorized on Verifier ({response.status_code})")
        except Exception as e:
            print(f"[Hunter.io] Error during Email Verifier: {e}")
    return None

def extract_domain_from_url(url: str) -> str | None:
    """Extract root domain from a URL (e.g. https://lab.stanford.edu/smith -> stanford.edu)"""
    if not url:
        return None
    try:
        if not url.startswith("http"):
            url = "http://" + url
        netloc = urlparse(url).netloc
        parts = netloc.split(".")
        if len(parts) >= 2:
            # Simple heuristic for university domains like .edu, .ac.uk
            if parts[-2] in ["ac", "edu", "gov", "org", "co"]:
                return ".".join(parts[-3:])
            return ".".join(parts[-2:])
    except Exception:
        pass
    return None
