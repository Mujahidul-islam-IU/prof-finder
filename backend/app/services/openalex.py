"""
ProfFinder — OpenAlex API Client
Secondary academic database. Completely free, no API key needed.
Docs: https://docs.openalex.org/
"""

import httpx
from typing import Optional

BASE_URL = "https://api.openalex.org"
TIMEOUT = httpx.Timeout(15.0, connect=10.0)

# Polite pool: add email for higher rate limits
HEADERS = {"User-Agent": "ProfFinder/1.0 (mailto:profinder@example.com)"}


async def search_authors(
    query: str,
    institution_country: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Search for authors/researchers by topic keywords or name."""
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        try:
            params = {
                "search": query,
                "per_page": limit,
                "select": "id,display_name,last_known_institutions,works_count,cited_by_count,x_concepts",
            }
            # Optionally filter by country
            if institution_country:
                params["filter"] = f"last_known_institutions.country_code:{institution_country}"

            resp = await client.get(f"{BASE_URL}/authors", params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])

            # Normalize to a common format
            normalized = []
            for author in results:
                institutions = author.get("last_known_institutions", [])
                inst_name = institutions[0].get("display_name", "") if institutions else ""
                inst_country = institutions[0].get("country_code", "") if institutions else ""
                openalex_id = author.get("id", "").replace("https://openalex.org/", "")

                normalized.append({
                    "openalex_id": openalex_id,
                    "name": author.get("display_name", ""),
                    "institution": inst_name,
                    "country": inst_country,
                    "works_count": author.get("works_count", 0),
                    "cited_by_count": author.get("cited_by_count", 0),
                    "concepts": [
                        c.get("display_name", "")
                        for c in (author.get("x_concepts", []) or [])[:5]
                    ],
                })
            return normalized
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            print(f"[OpenAlex] Author search error: {e}")
            return []


async def get_author_works(
    author_id: str,
    limit: int = 10,
    year_from: int = 2022,
) -> list[dict]:
    """Get recent works for an author by OpenAlex ID."""
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        try:
            # Remove URL prefix if present
            clean_id = author_id.replace("https://openalex.org/", "")
            params = {
                "filter": f"authorships.author.id:{clean_id},publication_year:>{year_from - 1}",
                "per_page": limit,
                "sort": "publication_date:desc",
                "select": "id,title,publication_year,primary_location,authorships,abstract_inverted_index",
            }
            resp = await client.get(f"{BASE_URL}/works", params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])

            normalized = []
            for work in results:
                # Reconstruct abstract from inverted index
                abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))
                venue = ""
                primary_loc = work.get("primary_location", {})
                if primary_loc and primary_loc.get("source"):
                    venue = primary_loc["source"].get("display_name", "")

                openalex_id = work.get("id", "").replace("https://openalex.org/", "")
                normalized.append({
                    "openalex_id": openalex_id,
                    "title": work.get("title", ""),
                    "abstract": abstract,
                    "year": work.get("publication_year"),
                    "venue": venue,
                })
            return normalized
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            print(f"[OpenAlex] Author works error for {author_id}: {e}")
            return []


def _reconstruct_abstract(inverted_index: Optional[dict]) -> str:
    """Reconstruct abstract text from OpenAlex inverted index format."""
    if not inverted_index:
        return ""
    # Build word-position pairs
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    # Sort by position and join
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)


async def search_institutions(
    query: str,
    country: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Search for institutions/universities."""
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        try:
            params = {
                "search": query,
                "per_page": limit,
                "select": "id,display_name,country_code,type,works_count",
            }
            if country:
                params["filter"] = f"country_code:{country}"

            resp = await client.get(f"{BASE_URL}/institutions", params=params)
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            print(f"[OpenAlex] Institution search error: {e}")
            return []
