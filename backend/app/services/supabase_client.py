"""
ProfFinder — Supabase Client Service
CRUD operations with freshness tracking for professors, papers, and requirements.
Checks cache BEFORE any external API call (Hard Constraint #7).
"""

from supabase import create_client, Client
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.config import get_settings
from app.models.schemas import (
    ProfessorProfile, PaperInfo, ProgramRequirements,
    CountryScore, EmailSource, FundingStatus, ResultTier,
)

_client: Client | None = None


import os

def get_supabase() -> Client:
    """Get or create the Supabase client."""
    global _client
    if _client is None:
        settings = get_settings()
        key = os.environ.get("SUPABASE_KEY", settings.supabase_anon_key)
        _client = create_client(settings.supabase_url, key)
    return _client


# ── Cache Check Helpers ──────────────────────────────────────

def is_fresh(fetched_at: Optional[str], ttl_days: int) -> bool:
    """Check if a cached record is still fresh based on its TTL."""
    if not fetched_at:
        return False
    try:
        fetched = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        expiry = fetched + timedelta(days=ttl_days)
        return datetime.now(timezone.utc) < expiry
    except (ValueError, TypeError):
        return False


# ── Search Sessions ──────────────────────────────────────────

def create_session(
    student_name: str,
    target_field: str,
    degree_type: str,
    target_countries: list[str],
    tier: str,
    gpa_normalized: Optional[float],
    vector_id: Optional[str],
    user_id: Optional[str] = None,
) -> dict:
    """Create a new search session record."""
    db = get_supabase()
    data = {
        "student_name": student_name,
        "target_field": target_field,
        "degree_type": degree_type,
        "target_countries": target_countries,
        "tier": tier,
        "gpa_normalized": gpa_normalized,
        "vector_id": vector_id,
        "user_id": user_id,
    }
    result = db.table("search_sessions").insert(data).execute()
    return result.data[0] if result.data else {}

def get_user_sessions(user_id: str) -> list[dict]:
    """Get all past search sessions for a user."""
    db = get_supabase()
    result = (
        db.table("search_sessions")
        .select("*, professors(*)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


# ── CV Caching ───────────────────────────────────────────────

def get_cached_cv(cv_hash: str) -> Optional[dict]:
    """Check if a CV was already deeply profiled."""
    try:
        db = get_supabase()
        result = db.table("cv_cache").select("*").eq("cv_hash", cv_hash).execute()
        if result.data:
            return result.data[0].get("student_profile")
    except Exception as e:
        print(f"[Supabase] get_cached_cv error: {e}")
    return None

def save_cached_cv(cv_hash: str, profile: dict) -> dict:
    """Save a parsed CV profile to cache."""
    try:
        db = get_supabase()
        data = {
            "cv_hash": cv_hash,
            "student_profile": profile,
        }
        result = db.table("cv_cache").upsert(data).execute()
        return result.data[0] if result.data else {}
    except Exception as e:
        print(f"[Supabase] save_cached_cv error: {e}")
        return {}


# ── Professors ───────────────────────────────────────────────

def get_cached_professor(
    semantic_scholar_id: str = "",
    openalex_id: str = "",
    ttl_days: int = 30,
) -> Optional[dict]:
    """Check if professor data is cached and fresh."""
    db = get_supabase()
    query = db.table("professors")

    if semantic_scholar_id:
        query = query.eq("semantic_scholar_id", semantic_scholar_id)
    elif openalex_id:
        query = query.eq("openalex_id", openalex_id)
    else:
        return None

    result = query.limit(1).execute()
    if not result.data:
        return None

    record = result.data[0]
    if is_fresh(record.get("papers_fetched_at"), ttl_days):
        return record
    return None  # Stale, needs refresh


def upsert_professor(
    session_id: str,
    professor: ProfessorProfile,
) -> dict:
    """Insert or update a professor record with freshness metadata."""
    db = get_supabase()
    data = {
        "session_id": session_id,
        "name": professor.name,
        "email": professor.email,
        "email_source": professor.email_source.value if professor.email_source else None,
        "email_confidence": professor.email_confidence,
        "university": professor.university,
        "department": professor.department,
        "country": professor.country,
        "lab_page_url": professor.lab_page_url,
        "lab_page_verified": professor.lab_page_verified,
        "funding_status": professor.funding_status.value,
        "funding_source_url": professor.funding_source_url,
        "semantic_scholar_id": professor.semantic_scholar_id,
        "openalex_id": professor.openalex_id,
        "match_score": professor.match_score,
        "result_tier": professor.result_tier.value if professor.result_tier else None,
        "lab_page_fetched_at": professor.lab_page_fetched_at.isoformat() if professor.lab_page_fetched_at else None,
        "papers_fetched_at": professor.papers_fetched_at.isoformat() if professor.papers_fetched_at else None,
    }
    result = db.table("professors").insert(data).execute()
    return result.data[0] if result.data else {}


# ── Professor Papers ─────────────────────────────────────────

def get_cached_papers(professor_id: str, ttl_days: int = 30) -> list[dict]:
    """Get cached papers for a professor if still fresh."""
    db = get_supabase()
    result = (
        db.table("professor_papers")
        .select("*")
        .eq("professor_id", professor_id)
        .execute()
    )
    if not result.data:
        return []

    # Check freshness of the first paper's fetch date
    first = result.data[0]
    if is_fresh(first.get("fetched_at"), ttl_days):
        return result.data
    return []  # Stale


def insert_papers(professor_id: str, papers: list[PaperInfo]) -> list[dict]:
    """Insert paper records for a professor."""
    db = get_supabase()
    records = []
    for paper in papers:
        records.append({
            "professor_id": professor_id,
            "title": paper.title,
            "abstract": paper.abstract,
            "year": paper.year,
            "venue": paper.venue,
            "semantic_scholar_id": paper.semantic_scholar_id,
            "openalex_id": paper.openalex_id,
            "cosine_score": paper.cosine_score,
            "is_top_match": paper.is_top_match,
            "embedding_stored": True,
            "api_ttl_days": 30,
        })
    if records:
        result = db.table("professor_papers").insert(records).execute()
        return result.data or []
    return []


# ── Program Requirements ─────────────────────────────────────

def get_cached_requirements(
    university: str,
    degree_type: str,
    ttl_days: int = 90,
) -> Optional[dict]:
    """Check cache for program requirements."""
    db = get_supabase()
    result = (
        db.table("program_requirements")
        .select("*")
        .eq("university", university)
        .eq("degree_type", degree_type)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None

    record = result.data[0]
    if is_fresh(record.get("extracted_at"), ttl_days):
        return record
    return None


def upsert_requirements(req: ProgramRequirements) -> dict:
    """Insert or update program requirements."""
    db = get_supabase()
    data = {
        "university": req.university,
        "program_name": req.program_name,
        "degree_type": req.degree_type.value if req.degree_type else None,
        "deadline_fall": req.deadline_fall.isoformat() if req.deadline_fall else None,
        "deadline_spring": req.deadline_spring.isoformat() if req.deadline_spring else None,
        "deadline_type": req.deadline_type,
        "gre_required": req.gre_required,
        "ielts_required": req.ielts_required,
        "ielts_min_score": req.ielts_min_score,
        "wes_required": req.wes_required,
        "application_fee_usd": req.application_fee_usd,
        "source_url": req.source_url,
        "confidence": req.confidence,
        "ttl_days": req.ttl_days if hasattr(req, 'ttl_days') else 90,
    }
    result = db.table("program_requirements").insert(data).execute()
    return result.data[0] if result.data else {}


# ── Country Rankings ─────────────────────────────────────────

def save_country_rankings(
    session_id: str,
    rankings: list[CountryScore],
) -> list[dict]:
    """Save country ranking results for a session."""
    db = get_supabase()
    records = []
    for rank in rankings:
        records.append({
            "session_id": session_id,
            "country": rank.country,
            "overall_score": rank.overall_score,
            "funding_score": rank.funding_score,
            "admission_score": rank.admission_score,
            "work_rights_score": rank.work_rights_score,
            "visa_score": rank.visa_score,
            "language_score": rank.language_score,
            "search_priority": rank.search_priority.value,
            "reasoning": rank.reasoning,
        })
    if records:
        result = db.table("country_rankings").insert(records).execute()
        return result.data or []
    return []
