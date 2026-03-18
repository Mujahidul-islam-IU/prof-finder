"""
ProfFinder — OpenAlex API Client
Primary academic database. Completely free, no API key needed.
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
                openalex_id = (author.get("id") or "").replace("https://openalex.org/", "")

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


async def search_works(
    query: str,
    institution_country: str | None = None,
    year_from: int = 2020,
    limit: int = 15,
) -> list[dict]:
    """
    Paper-first search: find papers matching keywords, optionally filtered by
    country of the authors' institutions. Returns papers with author info.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        try:
            filters = [f"publication_year:>{year_from - 1}"]
            if institution_country:
                filters.append(
                    f"authorships.institutions.country_code:{institution_country}"
                )

            params = {
                "search": query,
                "per_page": limit,
                "filter": ",".join(filters),
                # "sort": "cited_by_count:desc", # Removed to allow relevance sorting
                "select": (
                    "id,title,publication_year,primary_location,"
                    "authorships,abstract_inverted_index,cited_by_count"
                ),
            }

            resp = await client.get(f"{BASE_URL}/works", params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])

            normalized = []
            for work in results:
                abstract = _reconstruct_abstract(
                    work.get("abstract_inverted_index")
                )
                venue = ""
                primary_loc = work.get("primary_location", {})
                if primary_loc and primary_loc.get("source"):
                    venue = primary_loc["source"].get("display_name", "")

                # Extract all authors with their institutions
                authors_info = []
                for authorship in work.get("authorships", []):
                    author = authorship.get("author", {})
                    institutions = authorship.get("institutions", [])
                    inst = institutions[0] if institutions else {}
                    author_id = (
                        (author.get("id") or "").replace("https://openalex.org/", "")
                    )
                    authors_info.append({
                        "openalex_id": author_id,
                        "name": author.get("display_name", ""),
                        "institution": inst.get("display_name", ""),
                        "institution_country": inst.get("country_code", ""),
                        "institution_id": (
                            (inst.get("id") or "").replace("https://openalex.org/", "")
                        ),
                    })

                openalex_id = (work.get("id") or "").replace(
                    "https://openalex.org/", ""
                )
                normalized.append({
                    "openalex_id": openalex_id,
                    "title": work.get("title", ""),
                    "abstract": abstract,
                    "year": work.get("publication_year"),
                    "venue": venue,
                    "cited_by_count": work.get("cited_by_count", 0),
                    "authors": authors_info,
                })
            return normalized
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            print(f"[OpenAlex] Works search error: {e}")
            return []


async def get_author_works(
    author_id: str,
    limit: int = 10,
    year_from: int = 2020,
) -> list[dict]:
    """Get recent works for an author by OpenAlex ID."""
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        try:
            # Ensure we have the full URL format for the filter
            if not author_id.startswith("https://openalex.org/"):
                full_id = f"https://openalex.org/{author_id}"
            else:
                full_id = author_id
                author_id = full_id.replace("https://openalex.org/", "")

            params = {
                "filter": f"authorships.author.id:{full_id},publication_year:>{year_from - 1}",
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

                openalex_id = (work.get("id") or "").replace("https://openalex.org/", "")
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
