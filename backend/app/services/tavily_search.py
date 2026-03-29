"""
ProfFinder — Tavily Search Service
Web search optimized for LLM consumption.
Free tier: 1000 calls/month.
"""

from tavily import AsyncTavilyClient
from app.config import get_settings

_client: AsyncTavilyClient | None = None


def _get_client() -> AsyncTavilyClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    return _client


async def search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> list[dict]:
    """Perform a Tavily web search.

    Args:
        query: Search query string.
        max_results: Number of results to return (1-10).
        search_depth: 'basic' or 'advanced' (advanced uses more API credits).
        include_domains: Optional list of domains to restrict search to.
        exclude_domains: Optional list of domains to exclude.

    Returns:
        List of result dicts with: title, url, content, score.
    """
    client = _get_client()
    try:
        response = await client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            include_domains=include_domains or [],
            exclude_domains=exclude_domains or [],
        )
        return response.get("results", [])
    except Exception as e:
        print(f"[Tavily] Search error: {e}")
        return []


async def search_lab_page(professor_name: str, university: str) -> list[dict]:
    """Search specifically for a professor's lab/personal page."""
    query = f"{professor_name} {university} lab page research group"
    return await search(
        query=query,
        max_results=3,
        # No domain filter — professors are at universities worldwide
    )


async def search_funding_info(professor_name: str, university: str) -> list[dict]:
    """Search for professor's funding/prospective student info."""
    query = f'{professor_name} {university} "prospective students" OR "PhD positions" OR "openings" OR "funding"'
    return await search(query=query, max_results=3)


async def search_program_requirements(
    university: str,
    department: str,
    degree_type: str,
) -> list[dict]:
    """Search for graduate program admission requirements."""
    query = (
        f"{university} {department} {degree_type} graduate admissions "
        f"requirements deadline international student application fee GRE IELTS"
    )
    return await search(query=query, max_results=5)


async def search_professors_web(
    field: str,
    methods: list[str],
    country: str,
    degree_type: str = "MSc",
) -> list[dict]:
    """Search the web for professors in a specific field+country, like a student would.
    
    This is the 'Claude strategy' — searching for labs and faculty pages
    rather than individual papers.
    """
    # Build a query that mimics what a real student would search
    method_str = " ".join(methods[:3]) if methods else field
    queries = [
        f"{field} professor {country} research lab {method_str}",
        f"{method_str} computational biology professor {country} accepting {degree_type} students",
    ]
    
    all_results = []
    for q in queries:
        results = await search(
            query=q,
            max_results=5,
            search_depth="basic",
        )
        all_results.extend(results)
    
    return all_results


async def search_country_info(country: str, field: str) -> list[dict]:
    """Search for country-specific study abroad information."""
    query = (
        f"studying {field} in {country} international student funding "
        f"scholarship visa work permit PR pathway 2025 2026"
    )
    return await search(query=query, max_results=5)
