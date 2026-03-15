# 🎓 ProfFinder — Multi-Agent Professor Search System

AI-powered system that helps international students find the best-matched professors for graduate school (MSc/PhD) applications.

## Architecture

```
A1 (Profile Analyzer) → A2 (Country Ranker) → A3 (Professor Discovery)
→ A4 (Deep Profiler + Scorer) → A5 (QC + Verifier) → [SSE Stream to UI]
A6 (Cold Mail Drafter) — triggered manually by user
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python, async) |
| Agent Orchestration | LangGraph |
| LLM | GPT-4o (reasoning) + GPT-4o-mini (extraction) |
| Embeddings | text-embedding-3-small (1536d) |
| Vector Store | ChromaDB (local, persistent) |
| Database | Supabase (PostgreSQL) |
| Paper APIs | Semantic Scholar + OpenAlex |
| Web Search | Tavily Search API |
| Frontend | React + TanStack Table + React Query |
| Streaming | Server-Sent Events (SSE) |

## Setup

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

pip install -r requirements.txt

# Copy and fill in your API keys
copy .env.example .env
# Edit .env with your:
#   - OPENAI_API_KEY
#   - TAVILY_API_KEY
#   - SUPABASE_URL
#   - SUPABASE_ANON_KEY
```

### 2. Supabase Database

1. Create a free project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** in Supabase Dashboard
3. Run the contents of `backend/supabase_schema.sql`
4. Copy your **Project URL** and **anon key** from `Settings → API`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Run

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

## Hard Constraints

1. **NEVER** uses Google Scholar (ToS violation)
2. Funding is **NEVER** inferred — only marked "funded" if explicitly stated on lab page
3. Inferred emails are **ALWAYS** labeled in the UI with a warning
4. Hard cap: **30 professors/session**, **10 papers/professor**
5. A6 generates **DRAFTS only** — never sends email
6. Results stream via **SSE** as each professor completes
7. **Cache-first**: Supabase checked before every API call
8. **GPT-4o-mini** for all extraction; **GPT-4o** only for reasoning + email drafting

## Match Score Formula

```
Score (0-100) = cosine_similarity_avg_top3 × 50%
              + keyword_overlap × 20%
              + tier_fit_score × 15%
              + recency_score × 15%
```

## Project Structure

```
ProfFinder/
├── backend/
│   ├── app/
│   │   ├── agents/          # 6 LangGraph agents
│   │   ├── api/             # FastAPI routes + SSE
│   │   ├── models/          # Pydantic schemas
│   │   ├── prompts/         # LLM prompt templates
│   │   ├── services/        # External API clients
│   │   ├── config.py        # Settings
│   │   └── main.py          # Entry point
│   ├── requirements.txt
│   ├── supabase_schema.sql
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── hooks/           # useSSE hook
│   │   ├── services/        # API client
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
└── README.md
```
