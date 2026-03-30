-- ============================================================
-- ProfFinder — Supabase Schema
-- Every mutable field carries: fetched_at, source_url, confidence
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Search Sessions ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS search_sessions (
    session_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_name   TEXT,
    target_field   TEXT NOT NULL,
    degree_type    TEXT NOT NULL CHECK (degree_type IN ('MSc', 'PhD')),
    target_countries TEXT[] NOT NULL,
    tier           TEXT CHECK (tier IN ('A', 'B', 'C')),
    gpa_normalized FLOAT,
    vector_id      TEXT,                -- ChromaDB vector reference
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ── Professors ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS professors (
    professor_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id          UUID REFERENCES search_sessions(session_id) ON DELETE CASCADE,
    name                TEXT NOT NULL,
    email               TEXT,
    email_source        TEXT CHECK (email_source IN ('scraped_direct', 'inferred')),
    email_confidence    FLOAT DEFAULT 0.0,
    university          TEXT NOT NULL,
    department          TEXT,
    country             TEXT NOT NULL,
    lab_page_url        TEXT,
    lab_page_verified   BOOLEAN DEFAULT FALSE,
    funding_status      TEXT DEFAULT 'unknown' CHECK (funding_status IN ('funded', 'unknown')),
    funding_source_url  TEXT,
    funding_confidence  FLOAT DEFAULT 0.0,
    semantic_scholar_id TEXT,
    openalex_id         TEXT,
    match_score         INT DEFAULT 0,
    result_tier         TEXT CHECK (result_tier IN ('High Chance', 'Good Chance', 'Try Your Luck')),
    lab_page_fetched_at TIMESTAMPTZ,
    papers_fetched_at   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_professors_session ON professors(session_id);
CREATE INDEX idx_professors_ss_id ON professors(semantic_scholar_id);

-- ── Professor Papers ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS professor_papers (
    paper_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    professor_id        UUID REFERENCES professors(professor_id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    abstract            TEXT,
    year                INT,
    venue               TEXT,
    semantic_scholar_id TEXT,
    openalex_id         TEXT,
    cosine_score        FLOAT DEFAULT 0.0,
    is_top_match        BOOLEAN DEFAULT FALSE,
    embedding_stored    BOOLEAN DEFAULT FALSE,
    fetched_at          TIMESTAMPTZ DEFAULT NOW(),
    api_ttl_days        INT DEFAULT 30
);

CREATE INDEX idx_papers_professor ON professor_papers(professor_id);
CREATE INDEX idx_papers_top_match ON professor_papers(is_top_match) WHERE is_top_match = TRUE;

-- ── Program Requirements ───────────────────────────────────
CREATE TABLE IF NOT EXISTS program_requirements (
    req_id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    university          TEXT NOT NULL,
    program_name        TEXT,
    degree_type         TEXT CHECK (degree_type IN ('MSc', 'PhD')),
    deadline_fall       DATE,
    deadline_spring     DATE,
    deadline_type       TEXT,        -- 'fixed' | 'rolling' | 'unknown'
    gre_required        TEXT DEFAULT 'unknown',  -- 'required' | 'optional' | 'not_required' | 'unknown'
    ielts_required      BOOLEAN,
    ielts_min_score     FLOAT,
    wes_required        BOOLEAN,
    application_fee_usd INT,
    source_url          TEXT,
    confidence          FLOAT DEFAULT 0.0,
    extracted_at        TIMESTAMPTZ DEFAULT NOW(),
    ttl_days            INT DEFAULT 90
);

CREATE INDEX idx_requirements_uni ON program_requirements(university);

-- ── Country Rankings (per session) ─────────────────────────
CREATE TABLE IF NOT EXISTS country_rankings (
    ranking_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id          UUID REFERENCES search_sessions(session_id) ON DELETE CASCADE,
    country             TEXT NOT NULL,
    overall_score       FLOAT NOT NULL,
    funding_score       FLOAT,
    admission_score     FLOAT,
    work_rights_score   FLOAT,
    visa_score          FLOAT,
    language_score      FLOAT,
    search_priority     TEXT DEFAULT 'normal' CHECK (search_priority IN ('high', 'normal')),
    reasoning           TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rankings_session ON country_rankings(session_id);

-- ── CV Cache (Intelligent caching for repeat searches) ──────
CREATE TABLE IF NOT EXISTS cv_cache (
    cv_hash         TEXT PRIMARY KEY,
    parsed_profile  JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 days')
);

CREATE INDEX idx_cv_cache_hash ON cv_cache(cv_hash);
