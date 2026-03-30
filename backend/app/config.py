"""
ProfFinder — Application Settings
Reads all configuration from environment variables via pydantic-settings.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False)

    # ── App ─────────────────────────────────────────────
    jwt_secret: str = "local_super_secret_prof_finder_key"
    debug: bool = False
    cors_origins: list[str] = ["https://prof-finder.vercel.app", "https://prof-finder.vercel.app/"]

    # ── OpenAI ──────────────────────────────────────────
    openai_api_key: str = ""
    openai_reasoning_model: str = "gpt-4o"
    openai_extraction_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # ── Tavily ──────────────────────────────────────────
    tavily_api_key: str = ""

    # ── Hunter.io ───────────────────────────────────────
    hunter_api_key: str = ""

    # ── Supabase ────────────────────────────────────────
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # ── ChromaDB ────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_data"

    # ── Uploads ─────────────────────────────────────────
    upload_dir: str = "./uploads"

    # ── Limits (Hard Constraints) ───────────────────────
    max_professors_per_session: int = 30
    max_papers_per_professor: int = 10
    max_concurrent_profilers: int = 10  # asyncio.Semaphore cap

    # ── TTL (days) ──────────────────────────────────────
    ttl_professor_papers: int = 30
    ttl_lab_page: int = 14
    ttl_funding_status: int = 14
    ttl_application_deadlines: int = 60
    ttl_admission_requirements: int = 90
    deadline_warning_days: int = 45

    # ── Match Score Weights (v2: LLM-dominated) ──────────
    weight_llm_overall: float = 0.60     # LLM multi-dimensional reasoning score
    weight_semantic: float = 0.25        # Embedding cosine similarity (supplementary)
    weight_recency: float = 0.15         # Paper recency
    high_relevance_threshold: float = 0.72

    # ── Tier Thresholds ─────────────────────────────────
    tier_high_chance: int = 75
    tier_good_chance: int = 50


@lru_cache()
def get_settings():
    settings = Settings()
    # Explicit Fail-safe override for Render environment
    if not settings.openai_api_key:
        settings.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    if not settings.tavily_api_key:
        settings.tavily_api_key = os.environ.get("TAVILY_API_KEY", "")
    if not settings.supabase_url:
        settings.supabase_url = os.environ.get("SUPABASE_URL", "")
    if not settings.supabase_anon_key:
        # Check both possible keys used in the Render dashboard
        settings.supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_KEY", ""))
    if not settings.hunter_api_key:
        settings.hunter_api_key = os.environ.get("HUNTER_API_KEY", "")
    if not settings.jwt_secret or settings.jwt_secret == "local_super_secret_prof_finder_key":
        settings.jwt_secret = os.environ.get("JWT_SECRET", settings.jwt_secret)
    
    # Handle CORS origins list from comma-separated env var
    cors_env = os.environ.get("CORS_ORIGINS")
    if cors_env:
        settings.cors_origins = [o.strip() for o in cors_env.split(",") if o.strip()]
        
    return settings
