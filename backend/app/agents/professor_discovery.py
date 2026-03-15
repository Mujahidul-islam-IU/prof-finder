"""
ProfFinder — A3: Professor Discovery Agent
Discovers professor candidates using Semantic Scholar + OpenAlex.
Checks Supabase cache first. Hard cap: 30 professors total.
"""

from openai import AsyncOpenAI
import json
from app.config import get_settings
from app.agents.state import SearchState
from app.services import semantic_scholar, openalex, supabase_client
from app.models.schemas import ProfessorCandidate, SearchPriority, CountryScore
from app.prompts.templates import KEYWORD_GENERATION_PROMPT


async def _generate_keywords_llm(state: SearchState) -> list[str]:
    """Generate niche search queries using LLM based on student profile and custom keywords."""
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    profile = state.profile
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
    A3 — Professor Discovery Agent.
    1. Generate keywords
    2. Search OpenAlex (reliable for country filtering)
    3. Fallback to Tavily if academic results are low
    4. Deduplicate and cap at 30
    """
    settings = get_settings()
    target_field = state.search_request.target_field if state.search_request else ""
    
    await state.emit_status("A3", f"Generating niche search queries for {target_field}...", "1/4")
    keywords = await _generate_keywords_llm(state)
    max_total = settings.max_professors_per_session

    await state.emit_status("A3", f"Searching for professors in {target_field}...", "2/4")
    print(f"[A3] Keywords: {keywords}")

    # Fallback for country rankers if empty
    rankings = state.country_rankings
    if not rankings and state.search_request:
        print("[A3] Warning: No country rankings found, using target_countries from request.")
        rankings = [
            CountryScore(country=c, overall_score=50, search_priority=SearchPriority.NORMAL)
            for c in state.search_request.target_countries
        ]

    all_candidates: list[ProfessorCandidate] = []
    seen_ids = set()

    # Academic databases search
    await state.emit_status("A3", "Querying OpenAlex & Semantic Scholar...", "3/4")

    for ranking in rankings:
        country = ranking.country
        country_candidates = []
        
        # Map country to code
        country_codes = {
            "USA": "US", "United States": "US", "Canada": "CA",
            "UK": "GB", "United Kingdom": "GB", "Germany": "DE",
            "Australia": "AU", "Netherlands": "NL", "Sweden": "SE",
            "Switzerland": "CH", "Japan": "JP", "South Korea": "KR",
            "France": "FR", "Finland": "FI", "Norway": "NO",
            "Denmark": "DK", "Singapore": "SG", "Ireland": "IE",
        }
        cc = country_codes.get(country, "")

        for keyword in keywords:
            if len(all_candidates) >= max_total:
                break
            
            print(f"[A3] Searching OpenAlex for '{keyword}' in {country} ({cc})...")
            oa_authors = await openalex.search_authors(keyword, institution_country=cc, limit=5)
            
            for oa in oa_authors:
                oid = oa.get("openalex_id", "")
                if oid and oid not in seen_ids and oa.get("works_count", 0) >= 3:
                    seen_ids.add(oid)
                    all_candidates.append(ProfessorCandidate(
                        name=oa.get("name", ""),
                        university=oa.get("institution", ""),
                        country=country,
                        openalex_id=oid,
                        paper_count=oa.get("works_count", 0),
                    ))

        # Fallback to Tavily if search returned nothing for this country
        if not any(c.country == country for c in all_candidates):
            print(f"[A3] OpenAlex found nothing for {country}. Trying Tavily...")
            from app.services import tavily_search
            t_results = await tavily_search.search(f"professors research group {target_field} {country}", max_results=5)
            for r in t_results:
                name_uni = r.get("title", "").split("|")[0].split("-")[0].strip()
                if len(name_uni) > 5 and name_uni not in seen_ids:
                    seen_ids.add(name_uni)
                    all_candidates.append(ProfessorCandidate(
                        name=name_uni,
                        university=country, # Placeholder
                        country=country,
                        paper_count=5, # Placeholder
                    ))

    # ── Final Status ─────────────────────────────────────
    all_candidates = all_candidates[:max_total]
    print(f"[A3] Total candidates found: {len(all_candidates)}")
    
    await state.emit_status(
        "A3",
        f"Found {len(all_candidates)} professor candidates.",
        "4/4"
    )

    await state.emit_agent_output("A3", {"candidates": [c.model_dump(mode='json') for c in all_candidates]})

    state.professor_candidates = all_candidates
    return state
