"""
ProfFinder — A3: Professor Discovery Agent (v2)
Hybrid 3-strategy discovery: Web Search + Paper Search + Author Search.
Finds professors the way a real student would — by searching for labs and PIs.
"""

from openai import AsyncOpenAI
import json
from app.config import get_settings
from app.agents.state import SearchState
from app.services import openalex
from app.services import tavily_search
from app.models.schemas import ProfessorCandidate, SearchPriority, CountryScore
from app.prompts.templates import KEYWORD_GENERATION_PROMPT, PROFESSOR_EXTRACTION_PROMPT


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
            if word == "group" and len(name.split()) > 3:
                return False
            if word != "group":
                return False
    
    words = name.split()
    if len(words) > 5 or len(words) < 2:
        return False
        
    return True


async def _generate_keywords_llm(state: SearchState) -> dict:
    """Generate niche search queries using LLM — both web and academic queries."""
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    profile = state.student_profile
    if not profile:
        default = state.search_request.target_field if state.search_request else "Bioinformatics"
        return {
            "web_queries": [f"{default} professor lab"],
            "academic_queries": [default],
        }

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
        return {
            "web_queries": data.get("web_queries", [state.search_request.target_field]),
            "academic_queries": data.get("academic_queries", data.get("search_queries", [state.search_request.target_field])),
        }
    except Exception as e:
        print(f"[A3] Error generating keywords: {e}")
        return {
            "web_queries": [state.search_request.target_field],
            "academic_queries": [state.search_request.target_field],
        }


async def _discover_via_web_search(
    state: SearchState,
    country: str,
    web_queries: list[str],
    seen_authors: set,
    settings,
) -> list[ProfessorCandidate]:
    """Strategy 1: Web search for labs and faculty pages (the Claude strategy)."""
    candidates = []
    target_field = state.search_request.target_field if state.search_request else ""
    
    # Get student's key methods for search
    methods = []
    if state.student_profile:
        methods = state.student_profile.skills[:5]
    
    # Search the web like a real student would
    try:
        web_results = await tavily_search.search_professors_web(
            field=target_field,
            methods=methods,
            country=country,
            degree_type=state.search_request.degree_type.value if state.search_request else "MSc",
        )
        
        # Also run the LLM-generated web queries
        for wq in web_queries[:3]:
            query_with_country = f"{wq} {country}"
            extra_results = await tavily_search.search(query_with_country, max_results=5)
            web_results.extend(extra_results)
        
        if not web_results:
            return candidates
            
        # Combine all web content
        combined_content = ""
        for r in web_results:
            combined_content += f"Title: {r.get('title', '')}\nURL: {r.get('url', '')}\nContent: {r.get('content', '')[:500]}\n\n"
        
        # Use GPT-4o-mini to extract professor names from web results
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        prompt = PROFESSOR_EXTRACTION_PROMPT.format(
            target_field=target_field,
            country=country,
            search_results=combined_content[:4000],
        )
        
        response = await client.chat.completions.create(
            model=settings.openai_extraction_model,
            messages=[
                {"role": "system", "content": "Extract professor names and affiliations. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        
        extracted = json.loads(response.choices[0].message.content)
        professors = extracted.get("professors", [])
        
        for prof in professors:
            name = prof.get("name", "")
            university = prof.get("university", "")
            department = prof.get("department", "")
            
            dedup_key = f"{name}|{university}".lower()
            if not name or dedup_key in seen_authors:
                continue
            if not _is_individual_researcher(name):
                continue
            
            seen_authors.add(dedup_key)
            candidates.append(ProfessorCandidate(
                name=name,
                university=university,
                department=department,
                country=country,
                paper_count=0,
            ))
            print(f"[A3]   + Web candidate: {name} ({university})")
            
    except Exception as e:
        print(f"[A3] Web search error for {country}: {e}")
    
    return candidates


async def _discover_via_paper_search(
    state: SearchState,
    country: str,
    cc: str,
    academic_queries: list[str],
    seen_authors: set,
    max_total: int,
) -> list[ProfessorCandidate]:
    """Strategy 2: OpenAlex paper-first search (improved from v1)."""
    candidates = []
    target_field = state.search_request.target_field if state.search_request else ""
    
    for keyword in academic_queries:
        if len(candidates) >= max_total:
            break

        search_query = f"{target_field} {keyword}".strip()
        
        papers = await openalex.search_works(
            query=search_query,
            institution_country=cc if cc else None,
            year_from=2020,
            limit=20,  # Increased from 10
        )
        print(f"[A3]   Paper search '{keyword[:40]}' in {country}: {len(papers)} papers")

        for paper in papers:
            if len(candidates) >= max_total:
                break

            authors = paper.get("authors", [])
            # Take first and last authors only (typically PI + lead student)
            pi_authors = []
            if len(authors) >= 1:
                pi_authors.append(authors[0])
            if len(authors) >= 3:
                pi_authors.append(authors[-1])
            
            for author_info in pi_authors:
                author_id = author_info.get("openalex_id", "")
                author_name = author_info.get("name", "")
                institution = author_info.get("institution", "")
                inst_country = author_info.get("institution_country", "")

                dedup_key = f"{author_name}|{institution}".lower()
                if not author_id or dedup_key in seen_authors:
                    continue
                
                if not _is_individual_researcher(author_name):
                    continue

                if cc and inst_country and inst_country.upper() != cc.upper():
                    continue

                seen_authors.add(dedup_key)
                candidates.append(ProfessorCandidate(
                    name=author_name,
                    university=institution,
                    country=country,
                    openalex_id=author_id,
                    paper_count=0,
                ))
                print(f"[A3]   + Paper candidate: {author_name} ({institution})")

    return candidates


async def _discover_via_author_search(
    state: SearchState,
    country: str,
    cc: str,
    academic_queries: list[str],
    seen_authors: set,
) -> list[ProfessorCandidate]:
    """Strategy 3: OpenAlex author search (directly search for researchers)."""
    candidates = []
    
    for keyword in academic_queries[:3]:
        try:
            authors = await openalex.search_authors(
                query=keyword,
                institution_country=cc if cc else None,
                limit=10,
            )
            
            for author in authors:
                name = author.get("name", "")
                institution = author.get("institution", "")
                author_id = author.get("openalex_id", "")
                
                dedup_key = f"{name}|{institution}".lower()
                if not name or dedup_key in seen_authors:
                    continue
                if not _is_individual_researcher(name):
                    continue
                
                seen_authors.add(dedup_key)
                candidates.append(ProfessorCandidate(
                    name=name,
                    university=institution,
                    country=country,
                    openalex_id=author_id,
                    paper_count=author.get("works_count", 0),
                ))
                print(f"[A3]   + Author candidate: {name} ({institution})")
                
        except Exception as e:
            print(f"[A3] Author search error for '{keyword}': {e}")
    
    return candidates


# Country name to code mapping
COUNTRY_CODES = {
    "USA": "US", "United States": "US", "Canada": "CA",
    "UK": "GB", "United Kingdom": "GB", "Germany": "DE",
    "Australia": "AU", "Netherlands": "NL", "Sweden": "SE",
    "Switzerland": "CH", "Japan": "JP", "South Korea": "KR",
    "France": "FR", "Finland": "FI", "Norway": "NO",
    "Denmark": "DK", "Singapore": "SG", "Ireland": "IE",
}


async def professor_discovery(state: SearchState) -> SearchState:
    if isinstance(state, dict):
        state = SearchState.model_validate(state)

    """
    A3 — Professor Discovery Agent (v2: Hybrid 3-Strategy).
    1. Generate niche keywords (web + academic)
    2. Strategy 1: Web search for labs (Tavily + LLM extraction)
    3. Strategy 2: Paper-first search (OpenAlex works)
    4. Strategy 3: Author search (OpenAlex authors)
    5. Merge, deduplicate, and report
    """
    settings = get_settings()
    target_field = state.search_request.target_field if state.search_request else ""

    await state.emit_status("A3", f"Generating niche search queries for {target_field}...", "1/5")
    keywords = await _generate_keywords_llm(state)
    web_queries = keywords.get("web_queries", [])
    academic_queries = keywords.get("academic_queries", [])
    max_total = settings.max_professors_per_session

    print(f"[A3] Web queries: {web_queries}")
    print(f"[A3] Academic queries: {academic_queries}")

    # Fallback for country rankings if empty
    rankings = state.country_rankings
    if not rankings and state.search_request:
        rankings = [
            CountryScore(country=c, overall_score=50, search_priority=SearchPriority.NORMAL)
            for c in state.search_request.target_countries
        ]

    all_candidates: list[ProfessorCandidate] = []
    seen_authors = set()

    for ranking in rankings:
        country = ranking.country
        cc = COUNTRY_CODES.get(country, "")

        # ── Strategy 1: Web Search (the Claude strategy) ─────
        await state.emit_status("A3", f"Searching the web for {target_field} labs in {country}...", "2/5")
        web_candidates = await _discover_via_web_search(
            state, country, web_queries, seen_authors, settings,
        )
        all_candidates.extend(web_candidates)
        print(f"[A3] Web search found {len(web_candidates)} candidates in {country}")

        # ── Strategy 2: Paper Search (improved) ──────────────
        await state.emit_status("A3", f"Searching academic papers in {country}...", "3/5")
        remaining = max_total - len(all_candidates)
        if remaining > 0:
            paper_candidates = await _discover_via_paper_search(
                state, country, cc, academic_queries, seen_authors, remaining,
            )
            all_candidates.extend(paper_candidates)
            print(f"[A3] Paper search found {len(paper_candidates)} candidates in {country}")

        # ── Strategy 3: Author Search ────────────────────────
        await state.emit_status("A3", f"Searching for researchers in {country}...", "4/5")
        remaining = max_total - len(all_candidates)
        if remaining > 0:
            author_candidates = await _discover_via_author_search(
                state, country, cc, academic_queries, seen_authors,
            )
            all_candidates.extend(author_candidates)
            print(f"[A3] Author search found {len(author_candidates)} candidates in {country}")

        if len(all_candidates) >= max_total:
            break

    # ── Cap and report ───────────────────────────────────
    all_candidates = all_candidates[:max_total]
    print(f"[A3] Total candidates found: {len(all_candidates)}")
    for i, c in enumerate(all_candidates):
        print(f"[A3]   {i+1}. {c.name} | {c.university} | {c.country} | OA:{c.openalex_id}")

    await state.emit_status(
        "A3",
        f"Found {len(all_candidates)} professor candidates via hybrid search.",
        "5/5"
    )

    await state.emit_agent_output("A3", {"candidates": [c.model_dump(mode='json') for c in all_candidates]})

    state.professor_candidates = all_candidates
    return state
