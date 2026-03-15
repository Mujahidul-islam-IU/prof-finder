"""
ProfFinder — Pydantic Schemas
All request/response models and internal data structures.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum


# ── Enums ────────────────────────────────────────────────────

class DegreeType(str, Enum):
    MSC = "MSc"
    MS = "MS"
    PHD = "PhD"


class StudentTier(str, Enum):
    A = "A"  # Top-100 viable
    B = "B"  # 100-400 range
    C = "C"  # 500+ regional


class ResultTier(str, Enum):
    HIGH_CHANCE = "High Chance"
    GOOD_CHANCE = "Good Chance"
    TRY_YOUR_LUCK = "Try Your Luck"


class EmailSource(str, Enum):
    SCRAPED = "scraped_direct"
    INFERRED = "inferred"


class FundingStatus(str, Enum):
    FUNDED = "funded"
    UNKNOWN = "unknown"


class SearchPriority(str, Enum):
    HIGH = "high"
    NORMAL = "normal"


# ── Request Models ───────────────────────────────────────────

class SearchRequest(BaseModel):
    """Initial search request from user."""
    target_field: str = Field(..., description="e.g. 'AI', 'Bioinformatics', 'Cyber Security'")
    degree_type: DegreeType
    target_countries: list[str] = Field(..., min_length=1)
    intake_sessions: list[str] = Field(default=["Fall 2026"], description="e.g. ['Fall 2026', 'Spring 2027']")
    is_international: bool = Field(default=True)
    ielts_score: Optional[float] = None
    gre_score: Optional[int] = None
    additional_keywords: list[str] = Field(default=[], description="e.g. ['scRNA-seq', 'LLM', 'Transformer']")


class MailDraftRequest(BaseModel):
    """Request to generate a cold email draft."""
    professor_name: str
    department: str
    university: str
    selected_paper_titles: list[str] = Field(..., min_length=1, max_length=3)
    selected_paper_abstracts: list[str] = Field(default=[])
    student_research_summary: str
    strongest_publication: Optional[str] = None
    degree_type: DegreeType
    intake_session: str = "Fall 2026"


# ── Student Profile ─────────────────────────────────────────

class StudentProfile(BaseModel):
    """Parsed and analyzed student profile."""
    name: str = ""
    email: str = ""
    phone: str = ""
    gpa_original: Optional[float] = None
    gpa_scale: Optional[str] = None  # e.g. "4.0", "5.0", "100"
    gpa_normalized: Optional[float] = None  # Normalized to 4.0
    degree_details: str = ""
    university: str = ""
    ielts_score: Optional[float] = None
    gre_score: Optional[int] = None
    skills: list[str] = []
    research_interests: list[str] = []
    publications: list[str] = []
    publication_ids: list[str] = []  # Semantic Scholar IDs
    thesis_summary: str = ""
    work_experience: str = ""
    raw_text: str = ""
    tier: Optional[StudentTier] = None
    vector_id: Optional[str] = None


# ── Country Ranking ──────────────────────────────────────────

class CountryScore(BaseModel):
    """Score for a single country."""
    country: str
    overall_score: float = 0.0
    funding_score: float = 0.0
    admission_score: float = 0.0
    work_rights_score: float = 0.0
    visa_score: float = 0.0
    language_score: float = 0.0
    search_priority: SearchPriority = SearchPriority.NORMAL
    reasoning: str = ""


# ── Professor Models ─────────────────────────────────────────

class PaperInfo(BaseModel):
    """A single academic paper."""
    title: str
    abstract: str = ""
    year: Optional[int] = None
    venue: str = ""
    semantic_scholar_id: str = ""
    openalex_id: str = ""
    cosine_score: float = 0.0
    is_top_match: bool = False


class ProfessorCandidate(BaseModel):
    """Professor discovered by A3."""
    name: str
    university: str
    department: str = ""
    country: str
    semantic_scholar_id: str = ""
    openalex_id: str = ""
    paper_count: int = 0
    h_index: Optional[int] = None


class ProfessorProfile(BaseModel):
    """Fully profiled professor from A4 + A5."""
    professor_id: str = ""
    name: str
    email: Optional[str] = None
    email_source: Optional[EmailSource] = None
    email_confidence: float = 0.0
    university: str
    department: str = ""
    country: str
    lab_page_url: Optional[str] = None
    lab_page_verified: bool = False
    funding_status: FundingStatus = FundingStatus.UNKNOWN
    funding_source_url: Optional[str] = None
    funding_confidence: float = 0.0
    semantic_scholar_id: str = ""
    openalex_id: str = ""
    match_score: int = 0
    result_tier: Optional[ResultTier] = None
    top_matched_papers: list[PaperInfo] = []
    all_papers: list[PaperInfo] = []
    lab_page_fetched_at: Optional[datetime] = None
    papers_fetched_at: Optional[datetime] = None


# ── Program Requirements ─────────────────────────────────────

class ProgramRequirements(BaseModel):
    """Admission requirements for a program."""
    university: str
    program_name: str = ""
    degree_type: Optional[DegreeType] = None
    deadline_fall: Optional[date] = None
    deadline_spring: Optional[date] = None
    deadline_type: str = "unknown"  # fixed | rolling | unknown
    gre_required: str = "unknown"  # required | optional | not_required | unknown
    ielts_required: Optional[bool] = None
    ielts_min_score: Optional[float] = None
    wes_required: Optional[bool] = None
    application_fee_usd: Optional[int] = None
    source_url: str = ""
    confidence: float = 0.0
    deadline_warning: bool = False  # True if within 45 days


# ── SSE Event Models ─────────────────────────────────────────

class SSEProfessorEvent(BaseModel):
    """Single professor result streamed via SSE."""
    event_type: str = "professor_result"
    professor: ProfessorProfile
    requirements: Optional[ProgramRequirements] = None
    progress: str = ""  # e.g. "5/30"


class SSEStatusEvent(BaseModel):
    """Status update streamed via SSE."""
    event_type: str = "status"
    agent: str = ""  # e.g. "A1", "A2", "A3", "A4", "A5"
    message: str = ""
    progress: str = ""


class SSEAgentOutputEvent(BaseModel):
    """Debug output for a specific agent."""
    event_type: str = "agent_output"
    agent: str = ""
    data: dict = Field(default_factory=dict)


class SSECompleteEvent(BaseModel):
    """Final event when search is complete."""
    event_type: str = "complete"
    total_professors: int = 0
    high_chance: int = 0
    good_chance: int = 0
    try_your_luck: int = 0


# ── Mail Draft Response ──────────────────────────────────────

class MailDraftResponse(BaseModel):
    """Generated cold email draft."""
    subject: str
    body: str
    word_count: int
    professor_name: str
    referenced_papers: list[str]
