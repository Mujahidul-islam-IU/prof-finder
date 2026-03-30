"""
ProfFinder — A2: Country Ranker Agent
Scores countries using Tavily search + GPT-4o reasoning.
Dimensions: Funding 30%, Admission 25%, Work Rights 20%, Visa 15%, Language 10%.
"""

import json
from app.config import get_settings
from app.services.llm import generate_json
from app.agents.state import SearchState
from app.services import tavily_search
from app.services import supabase_client
from app.models.schemas import CountryScore, SearchPriority
from app.prompts.templates import COUNTRY_RANKING_PROMPT


async def country_ranker(state: SearchState) -> SearchState:
    if isinstance(state, dict):
        state = SearchState.model_validate(state)

    """
    A2 — Country Ranker Agent.
    1. Tavily search per country for BD-specific info
    2. GPT-4o scores across 5 dimensions
    3. Assigns search_priority (high/normal) per country
    """
    if not state.student_profile or not state.search_request:
        state.errors.append("A2: Missing student profile or search request")
        return state

    countries = state.search_request.target_countries
    tier = state.student_profile.tier.value if state.student_profile.tier else "B"
    target_field = state.search_request.target_field

    await state.emit_status("A2", f"Researching {len(countries)} countries...", "1/3")

    # ── Step 1: Gather info per country via Tavily ───────
    all_search_results = []
    for country in countries:
        results = await tavily_search.search_country_info(country, target_field)
        country_text = f"\n--- {country} ---\n"
        for r in results:
            country_text += f"Source: {r.get('url', '')}\n{r.get('content', '')[:500]}\n\n"
        all_search_results.append(country_text)

    combined_results = "\n".join(all_search_results)

    await state.emit_status("A2", "Analyzing and ranking countries...", "2/3")

    # ── Step 2: GPT-4o/LLaMA reasoning for ranking ─────────────
    settings = get_settings()

    prompt = COUNTRY_RANKING_PROMPT.format(
        degree_type=state.search_request.degree_type.value,
        target_field=target_field,
        tier=tier,
        gpa_normalized=state.student_profile.gpa_normalized or "N/A",
        ielts_score=state.student_profile.ielts_score or "N/A",
        gre_score=state.student_profile.gre_score or "N/A",
        countries=", ".join(countries),
        search_results=combined_results[:4000],  # Cap context
    )

    messages=[
        {"role": "system", "content": "You are a expert graduate school advisor. Return a JSON object with a key 'rankings' containing an array of country rankings."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        raw = await generate_json(
            messages=messages, 
            temperature=0.3, 
            force_model=settings.openai_reasoning_model
        )
    except Exception as e:
        print(f"[A2] LLM Error: {e}")
        raw = {}

    # Handle various possible JSON structures
    rankings_list = []
    if isinstance(raw, list):
        rankings_list = raw
    elif isinstance(raw, dict):
        # Look for common keys
        for key in ["rankings", "countries", "results", "data"]:
            if key in raw and isinstance(raw[key], list):
                rankings_list = raw[key]
                break
        # If still empty but dict has entries, maybe it's a dict of countries
        if not rankings_list and len(raw) > 0:
            # Check if any value is a dict with country info
            first_val = next(iter(raw.values()))
            if isinstance(first_val, dict) and "country" in first_val:
                rankings_list = list(raw.values())
            elif "country" in raw: # It's a single country object
                rankings_list = [raw]

    # ── Step 3: Build CountryScore objects ────────────────
    rankings = []
    for item in rankings_list:
        if not isinstance(item, dict):
            continue
        try:
            score = CountryScore(
                country=item.get("country", ""),
                overall_score=float(item.get("overall_score", 0)),
                funding_score=float(item.get("funding_score", 0)),
                admission_score=float(item.get("admission_score", 0)),
                work_rights_score=float(item.get("work_rights_score", 0)),
                visa_score=float(item.get("visa_score", 0)),
                language_score=float(item.get("language_score", 0)),
                search_priority=SearchPriority.HIGH if float(item.get("overall_score", 0)) >= 70 else SearchPriority.NORMAL,
                reasoning=item.get("reasoning", ""),
            )
            rankings.append(score)
        except (ValueError, TypeError) as e:
            print(f"[A2] Skipping invalid ranking item: {item}. Error: {e}")

    # Fallback: if GPT return nothing, use input countries with default scores
    if not rankings and countries:
        print("[A2] Fallback: GPT returned no valid rankings, using defaults.")
        for country in countries:
            rankings.append(CountryScore(
                country=country,
                overall_score=50,
                search_priority=SearchPriority.NORMAL,
                reasoning="Default score due to analysis timeout or error."
            ))

    # Sort by overall score descending
    rankings.sort(key=lambda x: x.overall_score, reverse=True)

    # ── Save to Supabase ─────────────────────────────────
    if state.session_id:
        try:
            supabase_client.save_country_rankings(state.session_id, rankings)
        except Exception as e:
            print(f"[A2] Supabase save error: {e}")

    await state.emit_status(
        "A2",
        f"Country ranking complete. Top: {rankings[0].country if rankings else 'N/A'}",
        "3/3",
    )

    await state.emit_agent_output("A2", {"rankings": [r.model_dump(mode='json') for r in rankings]})

    state.country_rankings = rankings
    return state
