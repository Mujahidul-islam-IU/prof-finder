"""
ProfFinder — A3: Professor Discovery Agent
Paper-first search: finds papers matching student's research, then extracts authors.
Tier-aware: distributes search across university tiers based on student tier.
"""

from openai import AsyncOpenAI
import json
from app.config import get_settings
from app.agents.state import SearchState
from app.services import openalex
from app.services import tavily_search
from app.models.schemas import ProfessorCandidate, SearchPriority, CountryScore
from app.prompts.templates import KEYWORD_GENERATION_PROMPT


# ── Tier-aware search distribution ──────────────────────────
# Maps student tier → (fraction_high_cited, fraction_mid, fraction_low)
TIER_DISTRIBUTION = {
    "A": (0.50, 0.30, 0.20),
    "B": (0.20, 0.50, 0.30),
    "C": (0.10, 0.30, 0.60),
}

# Approximate thresholds for institution quality (by cited_by_count)
# These are rough proxies — OpenAlex doesn't have ranking data directly
INSTITUTION_TIERS = {
    "high": 50000,   # cited_by_count >= this → top-tier
    "mid": 10000,    # >= this → mid-tier
    # below mid → lower-tier
}


def _is_individual_researcher(name: str) -> bool:
    """Heuristic to filter out collaborations, consortiums, and non-person entities."""
    if not name:
        return False
    lower_name = name.lower()
    blacklist = [
        "collaboration", "consortium", "group", "team", "network",
        "study", "investigators", "committee", "project", "initiative",
        "working group", "panel", "society", "association", "center",
        "institute", "foundation", "university", "college", "school"
    ]
    for word in blacklist:
        if word in lower_name:
            # Special case: "Group" is common in some names, but "The X Group" is usually an entity
            if word == "group" and len(name.split()) > 3:
                return False
            if word != "group":
                return False
    
    # Check for excessive length or very few words (usually a name is 2-4 words)
    words = name.split()
    if len(words) > 5 or len(words) < 2:
        return False
        
    return True


async def _generate_keywords_llm(state: SearchState) -> list[str]:
    """Generate niche search queries using LLM based on student profile and custom keywords."""
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    profile = state.student_profile
    if not profile:
        return [state.search_request.target_field] if state.search_request else ["Bioinformatics"]

    prompt = KEYWORD_GENERATION_PROMPT.format(
        research_interests=", ".join(profile.research_interests),
        thesis_summary=profile.thesis_summary or "N/A",
        target_field=state.search_request.target_field if state.search_request else "Academic Research",
        additional_keywords=", ".join(state.search_request.additional_keywords) if state.search_request and state.search_request.additional_keywords else "None"
    )

    try:
        response = await client.chat.completions.create(
            model=settings.openai_extraction_model,
            messages=[
                {"role": "system", "content": "You are a research scout. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        data = json.loads(response.choices[0].message.content)
        queries = data.get("search_queries", [])
        return queries if queries else [state.search_request.target_field]
    except Exception as e:
        print(f"[A3] Error generating keywords: {e}")
        return [state.search_request.target_field]


async def professor_discovery(state: SearchState) -> SearchState:
    if isinstance(state, dict):
        state = SearchState.model_validate(state)

    """
    A3 — Professor Discovery Agent (Paper-First).
    1. Generate keywords
    2. Search OpenAlex for PAPERS matching keywords + country
    3. Extract authors from those papers as professor candidates
    4. Deduplicate and apply tier-aware filtering
    5. Fallback to Tavily if academic results are low
    """
    settings = get_settings()
    target_field = state.search_request.target_field if state.search_request else ""
    student_tier = "B"  # default
    if state.student_profile and state.student_profile.tier:
        student_tier = state.student_profile.tier.value

    await state.emit_status("A3", f"Generating niche search queries for {target_field}...", "1/4")
    keywords = await _generate_keywords_llm(state)
    max_total = settings.max_professors_per_session

    await state.emit_status("A3", f"Searching for papers in {target_field}...", "2/4")
    print(f"[A3] Keywords: {keywords}")
    print(f"[A3] Student tier: {student_tier}")

    # Fallback for country rankings if empty
    rankings = state.country_rankings
    if not rankings and state.search_request:
        print("[A3] Warning: No country rankings found, using target_countries from request.")
        rankings = [
            CountryScore(country=c, overall_score=50, search_priority=SearchPriority.NORMAL)
            for c in state.search_request.target_countries
        ]

    # Map country names to codes
    country_codes = {
        "USA": "US", "United States": "US", "Canada": "CA",
        "UK": "GB", "United Kingdom": "GB", "Germany": "DE",
        "Australia": "AU", "Netherlands": "NL", "Sweden": "SE",
        "Switzerland": "CH", "Japan": "JP", "South Korea": "KR",
        "France": "FR", "Finland": "FI", "Norway": "NO",
        "Denmark": "DK", "Singapore": "SG", "Ireland": "IE",
    }

    all_candidates: list[ProfessorCandidate] = []
    seen_authors = set()  # Track by name+institution to avoid duplicates

    # ── Paper-First Search ───────────────────────────────
    await state.emit_status("A3", "Querying OpenAlex for matching papers...", "3/4")

    for ranking in rankings:
        country = ranking.country
        cc = country_codes.get(country, "")

        for keyword in keywords:
            if len(all_candidates) >= max_total:
                break

            print(f"[A3] Searching papers for '{keyword}' in {country} ({cc})...")
            
            # Prepend target_field to ensure relevance
            search_query = f"{target_field} {keyword}".strip()
            
            papers = await openalex.search_works(
                query=search_query,
                institution_country=cc if cc else None,
                year_from=2020,
                limit=10,
            )
            print(f"[A3]   Found {len(papers)} papers")

            for paper in papers:
                if len(all_candidates) >= max_total:
                    break

                # Extract authors from this paper
                for author_info in paper.get("authors", []):
                    author_id = author_info.get("openalex_id", "")
                    author_name = author_info.get("name", "")
                    institution = author_info.get("institution", "")
                    inst_country = author_info.get("institution_country", "")

                    # Skip if no ID, already seen, or not an individual
                    dedup_key = f"{author_name}|{institution}".lower()
                    if not author_id or dedup_key in seen_authors:
                        continue
                    
                    if not _is_individual_researcher(author_name):
                        print(f"[A3]   ! Skipping non-person entity: {author_name}")
                        continue

                    # Only take authors from the target country
                    if cc and inst_country and inst_country.upper() != cc.upper():
                        continue

                    seen_authors.add(dedup_key)
                    all_candidates.append(ProfessorCandidate(
                        name=author_name,
                        university=institution,
                        country=country,
                        openalex_id=author_id,
                        paper_count=0,  # Will be filled by A4
                    ))
                    print(f"[A3]   + Candidate: {author_name} ({institution})")

        # Fallback to Tavily if no candidates found for this country
        if not any(c.country == country for c in all_candidates):
            print(f"[A3] Paper search found nothing for {country}. Trying Tavily...")
            try:
                t_results = await tavily_search.search(
                    f"professors research group {target_field} {country}",
                    max_results=5,
                )
                for r in t_results:
                    # Better name extraction: "Title - University" or "Name | Dept"
                    parts = r.get("title", "").replace("|", "-").split("-")
                    name_uni = parts[0].strip()
                    
                    dedup_key = name_uni.lower()
                    if _is_individual_researcher(name_uni) and dedup_key not in seen_authors:
                        seen_authors.add(dedup_key)
                        all_candidates.append(ProfessorCandidate(
                            name=name_uni,
                            university=country,  # Placeholder
                            country=country,
                            paper_count=0,
                        ))
            except Exception as e:
                print(f"[A3] Tavily fallback error for {country}: {e}")

    # ── Cap and report ───────────────────────────────────
    all_candidates = all_candidates[:max_total]
    print(f"[A3] Total candidates found: {len(all_candidates)}")
    for i, c in enumerate(all_candidates):
        print(f"[A3]   {i+1}. {c.name} | {c.university} | {c.country} | OA:{c.openalex_id}")

    await state.emit_status(
        "A3",
        f"Found {len(all_candidates)} professor candidates.",
        "4/4"
    )

    await state.emit_agent_output("A3", {"candidates": [c.model_dump(mode='json') for c in all_candidates]})

    state.professor_candidates = all_candidates
    return state
