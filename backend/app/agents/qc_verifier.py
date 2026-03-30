"""
ProfFinder — A5: QC + Verifier Agent
Verifies lab URLs, validates emails, audits funding, fetches program requirements.
Writes verified data to Supabase. Streams each verified professor via SSE.
"""

import json
from datetime import datetime, timezone, date, timedelta
import httpx
from openai import AsyncOpenAI
from app.config import get_settings
from app.agents.state import SearchState
from app.services import tavily_search, supabase_client
from app.models.schemas import (
    ProfessorProfile, ProgramRequirements, FundingStatus, DegreeType, EmailSource
)
from app.services.hunter_io import find_email, verify_email, extract_domain_from_url
from app.prompts.templates import REQUIREMENTS_EXTRACTION_PROMPT


async def _verify_url(url: str) -> bool:
    """Verify a URL is reachable. HEAD first, fallback to GET."""
    if not url:
        return False
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(10.0),
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 ProfFinder/1.0"},
    ) as client:
        try:
            resp = await client.head(url)
            if resp.status_code < 400:
                return True
        except httpx.RequestError:
            pass
        # Fallback to GET with stream
        try:
            async with client.stream("GET", url) as resp:
                return resp.status_code < 400
        except httpx.RequestError:
            return False


def _validate_email_domain(email: str | None, university: str) -> bool:
    """Check if email domain matches university."""
    if not email or "@" not in email:
        return False
    domain = email.split("@")[1].lower()
    uni_words = university.lower().replace("university", "").replace("of", "").split()
    # Check if any significant university word appears in the domain
    return any(word in domain for word in uni_words if len(word) > 2)


async def _fetch_requirements(
    university: str,
    department: str,
    degree_type: str,
) -> ProgramRequirements | None:
    """Fetch and extract program requirements via Tavily + GPT-4o-mini."""
    settings = get_settings()

    # Check cache first (Hard Constraint #7)
    cached = supabase_client.get_cached_requirements(university, degree_type, settings.ttl_admission_requirements)
    if cached:
        req = ProgramRequirements(
            university=cached["university"],
            program_name=cached.get("program_name", ""),
            degree_type=DegreeType(cached["degree_type"]) if cached.get("degree_type") else None,
            deadline_fall=date.fromisoformat(cached["deadline_fall"]) if cached.get("deadline_fall") else None,
            deadline_spring=date.fromisoformat(cached["deadline_spring"]) if cached.get("deadline_spring") else None,
            deadline_type=cached.get("deadline_type", "unknown"),
            gre_required=cached.get("gre_required", "unknown"),
            ielts_required=cached.get("ielts_required"),
            ielts_min_score=cached.get("ielts_min_score"),
            wes_required=cached.get("wes_required"),
            application_fee_usd=cached.get("application_fee_usd"),
            source_url=cached.get("source_url", ""),
            confidence=cached.get("confidence", 0.0),
        )
        # Check deadline warning
        today = date.today()
        if req.deadline_fall and (req.deadline_fall - today).days <= settings.deadline_warning_days:
            req.deadline_warning = True
        if req.deadline_spring and (req.deadline_spring - today).days <= settings.deadline_warning_days:
            req.deadline_warning = True
        return req

    # Search via Tavily
    search_results = await tavily_search.search_program_requirements(
        university, department, degree_type
    )
    if not search_results:
        return None

    # Combine search results
    web_content = ""
    for r in search_results[:3]:
        web_content += f"Source: {r.get('url', '')}\n{r.get('content', '')}\n\n"

    # Extract with GPT-4o-mini
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = REQUIREMENTS_EXTRACTION_PROMPT.format(
        university=university,
        department=department,
        degree_type=degree_type,
        web_content=web_content[:3000],
    )

    try:
        response = await client.chat.completions.create(
            model=settings.openai_extraction_model,
            messages=[
                {"role": "system", "content": "Extract admission requirements precisely. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        extracted = json.loads(response.choices[0].message.content)

        req = ProgramRequirements(
            university=university,
            program_name=extracted.get("program_name", ""),
            degree_type=DegreeType(degree_type) if degree_type in ("MSc", "PhD") else None,
            deadline_fall=date.fromisoformat(extracted["deadline_fall"]) if extracted.get("deadline_fall") else None,
            deadline_spring=date.fromisoformat(extracted["deadline_spring"]) if extracted.get("deadline_spring") else None,
            deadline_type=extracted.get("deadline_type", "unknown"),
            gre_required=extracted.get("gre_required", "unknown"),
            ielts_required=extracted.get("ielts_required"),
            ielts_min_score=extracted.get("ielts_min_score"),
            wes_required=extracted.get("wes_required"),
            application_fee_usd=extracted.get("application_fee_usd"),
            source_url=extracted.get("source_url", search_results[0].get("url", "")),
            confidence=float(extracted.get("confidence", 0.5)),
        )

        # Deadline warning check
        today = date.today()
        if req.deadline_fall and (req.deadline_fall - today).days <= settings.deadline_warning_days:
            req.deadline_warning = True
        if req.deadline_spring and (req.deadline_spring - today).days <= settings.deadline_warning_days:
            req.deadline_warning = True

        return req
    except Exception as e:
        print(f"[A5] Requirements extraction error for {university}: {e}")
        return None


async def qc_verifier(state: SearchState) -> SearchState:
    if isinstance(state, dict):
        state = SearchState.model_validate(state)

    """
    A5 — QC + Verifier Agent.
    1. Verify lab page URLs (httpx HEAD/GET)
    2. Validate email domains
    3. Audit funding confidence
    4. Cross-check paper years >= 2022
    5. Fetch program requirements (Tavily + GPT-4o-mini)
    6. Save to Supabase
    7. Stream each verified professor via SSE
    """
    if not state.professor_profiles:
        state.errors.append("A5: No professor profiles to verify")
        return state

    # Sort professors by match_score descending so top matches are first (for API limits)
    state.professor_profiles.sort(key=lambda p: p.match_score, reverse=True)

    settings = get_settings()
    verified = []
    requirements_list = []

    await state.emit_status(
        "A5",
        f"Verifying {len(state.professor_profiles)} professors...",
        f"0/{len(state.professor_profiles)}",
    )

    for i, prof in enumerate(state.professor_profiles):
        # ── 1. Verify lab page URL ───────────────────────
        if prof.lab_page_url:
            prof.lab_page_verified = await _verify_url(prof.lab_page_url)

        # ── 2. Validate email & Hunter.io (Top 2 only) ───
        hunter_used = False
        if i < 2:
            if prof.email:
                # Verifier
                hunter_res = await verify_email(prof.email)
                if hunter_res:
                    hunter_used = True
                    prof.email_hunter_status = hunter_res.get("status")
                    if prof.email_hunter_status == "valid":
                        prof.email_confidence = 1.0
                        prof.email_source = EmailSource.HUNTER_VERIFIED
                    elif prof.email_hunter_status == "invalid":
                        prof.email_confidence = 0.1
            else:
                # Finder
                domain = extract_domain_from_url(prof.lab_page_url)
                if domain:
                    parts = prof.name.split()
                    first = parts[0]
                    last = parts[-1] if len(parts) > 1 else ""
                    hunter_res = await find_email(domain, first, last)
                    if hunter_res and hunter_res.get("email"):
                        hunter_used = True
                        prof.email = hunter_res["email"]
                        prof.email_source = EmailSource.HUNTER_VERIFIED
                        prof.email_confidence = hunter_res.get("score", 50) / 100.0
                        prof.email_hunter_status = "valid"

        if not hunter_used:
            # Fallback to standard validation
            if prof.email:
                domain_valid = _validate_email_domain(prof.email, prof.university)
                if not domain_valid and prof.email_source != EmailSource.SCRAPED:
                    prof.email_confidence = min(prof.email_confidence, 0.3)

        # ── 3. Funding audit ─────────────────────────────
        if prof.funding_status == FundingStatus.FUNDED and prof.funding_confidence < 0.8:
            prof.funding_status = FundingStatus.UNKNOWN  # Downgrade

        # ── 4. Cross-check paper years ───────────────────
        valid_papers = [p for p in prof.all_papers if p.year and p.year >= 2022]
        prof.all_papers = valid_papers
        prof.top_matched_papers = [p for p in prof.top_matched_papers if p.year and p.year >= 2022]

        # ── 5. Fetch program requirements ────────────────
        degree_type = state.search_request.degree_type.value if state.search_request else "PhD"
        req = await _fetch_requirements(
            prof.university, prof.department, degree_type
        )

        # ── 6. Save to Supabase ──────────────────────────
        try:
            if state.session_id:
                saved = supabase_client.upsert_professor(state.session_id, prof)
                prof_id = saved.get("professor_id", "")
                prof.professor_id = prof_id
                if prof.all_papers:
                    supabase_client.insert_papers(prof_id, prof.all_papers)
                if req:
                    supabase_client.upsert_requirements(req)
        except Exception as e:
            print(f"[A5] Supabase save error for {prof.name}: {e}")

        verified.append(prof)
        if req:
            requirements_list.append(req)

        # ── 7. Stream verified professor ─────────────────
        await state.emit_professor(
            professor=prof,
            requirements=req,
            progress=f"{i + 1}/{len(state.professor_profiles)}",
        )

        await state.emit_status(
            "A5",
            f"Verified: {prof.name} ({prof.university})",
            f"{i + 1}/{len(state.professor_profiles)}",
        )

    state.verified_professors = verified
    state.program_requirements = requirements_list

    await state.emit_status(
        "A5",
        f"Verification complete. {len(verified)} professors verified.",
        f"{len(verified)}/{len(state.professor_profiles)}",
    )

    return state
