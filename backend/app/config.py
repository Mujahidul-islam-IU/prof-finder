"""
ProfFinder — Application Settings
Reads all configuration from environment variables via pydantic-settings.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── OpenAI ──────────────────────────────────────────
    openai_api_key: str = ""
    openai_reasoning_model: str = "gpt-4o"
    openai_extraction_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # ── Tavily ──────────────────────────────────────────
    tavily_api_key: str = ""

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

    # ── Match Score Weights ─────────────────────────────
    weight_semantic: float = 0.50
    weight_keyword: float = 0.20
    weight_tier_fit: float = 0.15
    weight_recency: float = 0.15
    high_relevance_threshold: float = 0.72

    # ── Tier Thresholds ─────────────────────────────────
    tier_high_chance: int = 70
    tier_good_chance: int = 45

    # ── App ─────────────────────────────────────────────
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
