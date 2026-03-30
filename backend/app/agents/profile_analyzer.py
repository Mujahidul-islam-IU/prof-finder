"""
ProfFinder — A1: Profile Analyzer Agent
Parses CV, normalizes GPA, embeds profile, cross-checks publications, classifies tier.
"""

import json
import uuid
from openai import AsyncOpenAI
from app.config import get_settings
from app.agents.state import SearchState
from app.services.cv_parser import parse_cv
from app.services.embedding import embed_text
from app.services.vector_store import store_student_vector
from app.services import semantic_scholar, supabase_client
from app.prompts.templates import TIER_CLASSIFICATION_PROMPT
from app.models.schemas import StudentProfile


async def profile_analyzer(state: SearchState) -> SearchState:
    if isinstance(state, dict):
        state = SearchState.model_validate(state)

    """
    A1 — Profile Analyzer Agent.
    1. Parse CV (PDF/DOCX)
    2. Merge with user-provided IELTS/GRE scores
    3. Cross-check publications on Semantic Scholar
    4. Embed student profile in ChromaDB
    5. Classify tier (A/B/C)
    """
    # ── Step 0: Check Cache ──────────────────────────────
    cv_hash = getattr(state, "cv_hash", None)
    if cv_hash:
        cached_profile_dict = supabase_client.get_cached_cv(cv_hash)
        if cached_profile_dict:
            await state.emit_status("A1", "Loaded your CV from cache instantly ⚡", "1/1")
            profile = StudentProfile.model_validate(cached_profile_dict)
            state.student_profile = profile
            await state.emit_agent_output("A1", {"cached": True, "profile": profile.model_dump(mode='json')})
            return state

    await state.emit_status("A1", "Parsing your CV...", "1/5")

    # ── Step 1: Parse CV ─────────────────────────────────
    try:
        profile = await parse_cv(state.cv_file_path)
    except Exception as e:
        error_msg = f"CV Parsing failed: {str(e)}"
        await state.emit_status("A1", f"Error: {error_msg}", "1/5")
        raise e  # Re-raise to let the graph wrapper handle it

    # ── Step 2: Merge user-provided data ─────────────────
    if state.search_request:
        if state.search_request.ielts_score:
            profile.ielts_score = state.search_request.ielts_score
        if state.search_request.gre_score:
            profile.gre_score = state.search_request.gre_score

    await state.emit_status("A1", "Cross-checking publications on Semantic Scholar...", "2/5")

    # ── Step 3: Cross-check publications ─────────────────
    verified_ids = []
    for pub_title in profile.publications[:10]:  # Cap at 10 publications
        try:
            result = await semantic_scholar.verify_publication(pub_title)
            if result and result.get("paperId"):
                verified_ids.append(result["paperId"])
        except Exception as e:
            print(f"[A1] Publication verify error: {e}")
    profile.publication_ids = verified_ids

    await state.emit_status("A1", "Creating your research profile embedding...", "3/5")

    # ── Step 4: Embed student profile in ChromaDB ────────
    # Concatenate all research-relevant text
    profile_text_parts = [
        f"Research interests: {', '.join(profile.research_interests)}",
        f"Skills: {', '.join(profile.skills)}",
        f"Publications: {'; '.join(profile.publications)}",
        f"Thesis: {profile.thesis_summary}",
        f"Degree: {profile.degree_details}",
        f"Experience: {profile.work_experience}",
    ]
    profile_text = " | ".join([p for p in profile_text_parts if p.split(": ", 1)[-1].strip()])

    embedding = await embed_text(profile_text)

    vector_id = f"student_{uuid.uuid4().hex[:12]}"
    store_student_vector(
        vector_id=vector_id,
        embedding=embedding,
        metadata={
            "name": profile.name,
            "field": state.search_request.target_field if state.search_request else "",
            "degree": state.search_request.degree_type.value if state.search_request else "",
        },
        document=profile_text,
    )
    profile.vector_id = vector_id

    await state.emit_status("A1", "Classifying your academic tier...", "4/5")

    # ── Step 5: Classify tier ────────────────────────────
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    prompt = TIER_CLASSIFICATION_PROMPT.format(
        gpa_normalized=profile.gpa_normalized or "N/A",
        university=profile.university,
        degree_details=profile.degree_details,
        ielts_score=profile.ielts_score or "N/A",
        gre_score=profile.gre_score or "N/A",
        publications_count=len(profile.publications),
        verified_count=len(verified_ids),
        publications="; ".join(profile.publications[:5]),
        research_interests=", ".join(profile.research_interests),
        skills=", ".join(profile.skills[:10]),
        thesis_summary=profile.thesis_summary[:500],
        work_experience=profile.work_experience[:500],
    )

    response = await client.chat.completions.create(
        model=settings.openai_extraction_model,  # GPT-4o-mini for extraction
        messages=[
            {"role": "system", "content": "You are an academic admissions advisor. Return valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    tier_result = json.loads(response.choices[0].message.content)
    from app.models.schemas import StudentTier
    profile.tier = StudentTier(tier_result.get("tier", "B"))

    await state.emit_status("A1", f"Profile analysis complete. Tier: {profile.tier.value}", "5/5")
    await state.emit_agent_output("A1", profile.model_dump(mode='json'))

    # Save to cache
    if cv_hash:
        try:
            supabase_client.save_cached_cv(cv_hash, profile.model_dump(mode='json'))
        except Exception as e:
            print(f"[A1] Failed to cache CV: {e}")

    state.student_profile = profile
    return state
