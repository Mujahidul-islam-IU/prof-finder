"""
ProfFinder — Semantic Scholar API Client
Primary academic paper and author search API.
Free, official API. Rate limit: 100 requests/5 minutes (no key needed).
"""

import asyncio
import httpx
from typing import Optional

BASE_URL = "https://api.semanticscholar.org/graph/v1"
TIMEOUT = httpx.Timeout(15.0, connect=10.0)

async def _request_with_retry(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
    for attempt in range(3):
        try:
            resp = await client.request(method, url, **kwargs)
            if resp.status_code == 429:
                wait = (attempt + 1) * 2
                print(f"[SemanticScholar] 429 detected, waiting {wait}s...")
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            if attempt == 2:
                raise e
            await asyncio.sleep(1)
    return None

async def search_authors(
    query: str,
    limit: int = 10,
    fields: str = "name,affiliations,paperCount,hIndex,externalIds",
) -> list[dict]:
    """Search for authors by name or research topic keywords."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await _request_with_retry(
                client, "GET", f"{BASE_URL}/author/search",
                params={"query": query, "limit": limit, "fields": fields}
            )
            if not resp:
                return []
            data = resp.json()
            return data.get("data", [])
        except Exception as e:
            print(f"[SemanticScholar] Author search error: {e}")
            return []


async def get_author_papers(
    author_id: str,
    limit: int = 10,
    fields: str = "title,abstract,year,venue,externalIds,publicationDate",
    year_from: int = 2022,
) -> list[dict]:
    """Get recent papers for a specific author by their Semantic Scholar ID."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await _request_with_retry(
                client, "GET", f"{BASE_URL}/author/{author_id}/papers",
                params={
                    "limit": limit,
                    "fields": fields,
                }
            )
            if not resp:
                return []
            data = resp.json()
            papers = data.get("data", [])
            # Filter by year
            return [
                p for p in papers
                if p.get("year") and p["year"] >= year_from
            ]
        except Exception as e:
            print(f"[SemanticScholar] Author papers error for {author_id}: {e}")
            return []


async def search_papers(
    query: str,
    limit: int = 10,
    year_from: int = 2022,
    fields: str = "title,abstract,year,venue,authors,externalIds",
) -> list[dict]:
    """Search for papers by keyword query."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await _request_with_retry(
                client, "GET", f"{BASE_URL}/paper/search",
                params={
                    "query": query,
                    "limit": limit,
                    "year": f"{year_from}-",
                    "fields": fields,
                }
            )
            if not resp:
                return []
            data = resp.json()
            return data.get("data", [])
        except Exception as e:
            print(f"[SemanticScholar] Paper search error: {e}")
            return []


async def get_paper_details(
    paper_id: str,
    fields: str = "title,abstract,year,venue,authors,externalIds,citationCount",
) -> Optional[dict]:
    """Get detailed info for a single paper by its Semantic Scholar ID."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/paper/{paper_id}",
                params={"fields": fields},
            )
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            print(f"[SemanticScholar] Paper details error for {paper_id}: {e}")
            return None


async def verify_publication(title: str) -> Optional[dict]:
    """Verify a publication exists by searching its title.
    Used by A1 to cross-check student's claimed publications."""
    # Clean title: remove citation noise like "[1]", author lists "Islam et al.", etc.
    import re
    clean_title = re.sub(r'\[\d+\]', '', title) # Remove [1], [22]
    clean_title = re.sub(r'^.*?,\s*', '', clean_title) # Remove leading author lists if followed by comma
    clean_title = clean_title.strip()

    papers = await search_papers(query=clean_title, limit=3)
    if not papers:
        return None
    # Fuzzy match: check if any result title is close enough
    title_lower = clean_title.lower().strip()
    for paper in papers:
        paper_title = paper.get("title", "").lower().strip()
        # Simple containment check
        if title_lower in paper_title or paper_title in title_lower:
            return paper
    # Return best match if no exact match
    return papers[0] if papers else None
