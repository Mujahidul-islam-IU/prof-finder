"""
ProfFinder — A4: Deep Profiler + Scorer Agent
Parallel profiling of up to 30 professors via asyncio.gather with Semaphore(10).
Fetches papers, embeds, computes cosine similarity, extracts lab page info.
"""

import json
import asyncio
from datetime import datetime, timezone
from openai import AsyncOpenAI
import httpx
from app.config import get_settings
from app.agents.state import SearchState
from app.services import semantic_scholar, openalex
from app.services.embedding import embed_text, embed_texts
from app.services.vector_store import compute_cosine_similarity, store_paper_vectors, get_student_collection
from app.services import tavily_search
from app.models.schemas import (
    ProfessorCandidate, ProfessorProfile, PaperInfo,
    EmailSource, FundingStatus, ResultTier,
)
from app.prompts.templates import LAB_PAGE_EXTRACTION_PROMPT


async def _profile_single_professor(
    candidate: ProfessorCandidate,
    student_embedding: list[float],
    student_keywords: set[str],
    student_tier: str,
    semaphore: asyncio.Semaphore,
    settings,
) -> ProfessorProfile | None:
    """Profile a single professor: fetch papers, embed, score, extract lab page."""
    async with semaphore:
        try:
            # ── Fetch papers ─────────────────────────────
            papers_raw = []
            if candidate.semantic_scholar_id:
                papers_raw = await semantic_scholar.get_author_papers(
                    candidate.semantic_scholar_id,
                    limit=settings.max_papers_per_professor,
                    year_from=2022,
                )
            elif candidate.openalex_id:
                papers_raw = await openalex.get_author_works(
                    candidate.openalex_id,
                    limit=settings.max_papers_per_professor,
                    year_from=2022,
                )

            if not papers_raw:
                return None  # Skip professors with no recent papers

            # ── Build PaperInfo objects ──────────────────
            papers = []
            paper_texts = []
            for p in papers_raw[:settings.max_papers_per_professor]:
                title = p.get("title", "")
                abstract = p.get("abstract", "") or ""
                if not title:
                    continue
                papers.append(PaperInfo(
                    title=title,
                    abstract=abstract,
                    year=p.get("year"),
                    venue=p.get("venue", ""),
                    semantic_scholar_id=p.get("paperId", p.get("semantic_scholar_id", "")),
                    openalex_id=p.get("openalex_id", ""),
                ))
                paper_texts.append(f"{title}. {abstract}")

            if not papers:
                return None

            # ── Embed papers ─────────────────────────────
            paper_embeddings = await embed_texts(paper_texts)

            # ── Compute cosine similarity ────────────────
            cosine_scores = []
            for i, emb in enumerate(paper_embeddings):
                score = compute_cosine_similarity(student_embedding, emb)
                papers[i].cosine_score = round(score, 4)
                cosine_scores.append(score)

            # Average top-3 cosine scores
            sorted_scores = sorted(cosine_scores, reverse=True)
            avg_top3 = sum(sorted_scores[:3]) / min(3, len(sorted_scores))

            # Mark top-3 papers
            sorted_papers = sorted(papers, key=lambda p: p.cosine_score, reverse=True)
            for i, paper in enumerate(sorted_papers[:3]):
                paper.is_top_match = True

            # ── Keyword overlap score ────────────────────
            prof_keywords = set()
            for paper in papers:
                words = (paper.title + " " + paper.abstract).lower().split()
                prof_keywords.update(words)
            overlap = len(student_keywords & prof_keywords) / max(len(student_keywords), 1)
            keyword_score = min(overlap * 100, 100)

            # ── Tier fit score ───────────────────────────
            # Based on h-index as proxy for university tier
            h = candidate.h_index or 0
            if student_tier == "A":
                tier_fit = 100 if h >= 30 else (60 if h >= 15 else 30)
            elif student_tier == "B":
                tier_fit = 100 if 10 <= h <= 40 else (60 if h > 40 else 30)
            else:  # C
                tier_fit = 100 if h <= 20 else (60 if h <= 35 else 30)

            # ── Recency score ────────────────────────────
            latest_year = max((p.year for p in papers if p.year), default=2020)
            current_year = datetime.now().year
            months_ago = (current_year - latest_year) * 12
            if months_ago <= 6:
                recency = 100
            elif months_ago <= 18:
                recency = 70
            elif months_ago <= 24:
                recency = 30
            else:
                recency = 0

            # ── Composite score ──────────────────────────
            composite = (
                avg_top3 * 100 * settings.weight_semantic
                + keyword_score * settings.weight_keyword
                + tier_fit * settings.weight_tier_fit
                + recency * settings.weight_recency
            )
            match_score = int(min(max(composite, 0), 100))

            # ── Determine result tier ────────────────────
            if match_score >= settings.tier_high_chance:
                result_tier = ResultTier.HIGH_CHANCE
            elif match_score >= settings.tier_good_chance:
                result_tier = ResultTier.GOOD_CHANCE
            else:
                result_tier = ResultTier.TRY_YOUR_LUCK

            # ── Lab page extraction ──────────────────────
            email = None
            email_source = None
            email_confidence = 0.0
            funding_status = FundingStatus.UNKNOWN
            funding_source_url = None
            funding_confidence = 0.0
            lab_page_url = None
            lab_page_fetched_at = None

            try:
                lab_results = await tavily_search.search_lab_page(
                    candidate.name, candidate.university
                )
                if lab_results:
                    lab_page_url = lab_results[0].get("url", "")
                    page_content = lab_results[0].get("content", "")

                    # Extract info using GPT-4o-mini with CONSERVATIVE prompt
                    client = AsyncOpenAI(api_key=settings.openai_api_key)
                    prompt = LAB_PAGE_EXTRACTION_PROMPT.format(
                        professor_name=candidate.name,
                        university=candidate.university,
                        page_content=page_content[:3000],
                    )
                    response = await client.chat.completions.create(
                        model=settings.openai_extraction_model,
                        messages=[
                            {"role": "system", "content": "Extract information conservatively. Return valid JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.0,
                    )
                    extracted = json.loads(response.choices[0].message.content)

                    email = extracted.get("email")
                    if extracted.get("email_source"):
                        email_source = EmailSource(extracted["email_source"])
                    email_confidence = float(extracted.get("email_confidence", 0))

                    if extracted.get("funding_status") == "funded":
                        fc = float(extracted.get("funding_confidence", 0))
                        if fc >= 0.8:
                            funding_status = FundingStatus.FUNDED
                            funding_confidence = fc
                        else:
                            funding_status = FundingStatus.UNKNOWN
                            funding_confidence = fc
                    funding_source_url = extracted.get("funding_source_url")
                    lab_page_fetched_at = datetime.now(timezone.utc)
            except Exception as e:
                print(f"[A4] Lab page error for {candidate.name}: {e}")

            # ── Store paper embeddings in ChromaDB ───────
            try:
                paper_ids = [
                    f"paper_{candidate.semantic_scholar_id or candidate.openalex_id}_{i}"
                    for i in range(len(papers))
                ]
                paper_metas = [
                    {"professor": candidate.name, "year": p.year or 0, "title": p.title[:200]}
                    for p in papers
                ]
                store_paper_vectors(paper_ids, paper_embeddings, paper_metas, paper_texts)
            except Exception as e:
                print(f"[A4] ChromaDB store error: {e}")

            # ── Build ProfessorProfile ───────────────────
            return ProfessorProfile(
                name=candidate.name,
                email=email,
                email_source=email_source,
                email_confidence=email_confidence,
                university=candidate.university,
                department=candidate.department,
                country=candidate.country,
                lab_page_url=lab_page_url,
                funding_status=funding_status,
                funding_source_url=funding_source_url,
                funding_confidence=funding_confidence,
                semantic_scholar_id=candidate.semantic_scholar_id,
                openalex_id=candidate.openalex_id,
                match_score=match_score,
                result_tier=result_tier,
                top_matched_papers=sorted_papers[:3],
                all_papers=papers,
                lab_page_fetched_at=lab_page_fetched_at,
                papers_fetched_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            print(f"[A4] Error profiling {candidate.name}: {e}")
            return None


async def deep_profiler(state: SearchState) -> SearchState:
    if isinstance(state, dict):
        state = SearchState.model_validate(state)

    """
    A4 — Deep Profiler + Scorer Agent.
    Runs PARALLEL via asyncio.gather with Semaphore(10) for all candidates.
    """
    if not state.professor_candidates or not state.student_profile:
        state.errors.append("A4: No professor candidates or student profile")
        return state

    settings = get_settings()
    semaphore = asyncio.Semaphore(settings.max_concurrent_profilers)

    await state.emit_status(
        "A4",
        f"Deep profiling {len(state.professor_candidates)} professors (parallel)...",
        f"0/{len(state.professor_candidates)}",
    )

    # ── Get student embedding from ChromaDB ──────────────
    student_collection = get_student_collection()
    student_data = student_collection.get(
        ids=[state.student_profile.vector_id],
        include=["embeddings", "documents"],
    )
    
    # Use explicit checks to avoid "ambiguous array" error with NumPy arrays
    embeddings = student_data.get("embeddings")
    documents = student_data.get("documents")
    
    student_embedding = embeddings[0] if (embeddings is not None and len(embeddings) > 0) else []
    student_doc = documents[0] if (documents is not None and len(documents) > 0) else ""
    student_keywords = set(student_doc.lower().split())

    student_tier = state.student_profile.tier.value if state.student_profile.tier else "B"

    # ── Run all profilers in parallel ────────────────────
    tasks = [
        _profile_single_professor(
            candidate=candidate,
            student_embedding=student_embedding,
            student_keywords=student_keywords,
            student_tier=student_tier,
            semaphore=semaphore,
            settings=settings,
        )
        for candidate in state.professor_candidates
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # ── Collect successful profiles ──────────────────────
    profiles = []
    for i, result in enumerate(results):
        if isinstance(result, ProfessorProfile):
            profiles.append(result)
            # Stream each completed professor to frontend
            await state.emit_professor(
                professor=result,
                requirements=None,
                progress=f"{len(profiles)}/{len(state.professor_candidates)}",
            )
        elif isinstance(result, Exception):
            print(f"[A4] Exception for candidate {i}: {result}")

    # Sort by match score descending
    profiles.sort(key=lambda p: p.match_score, reverse=True)

    await state.emit_status(
        "A4",
        f"Profiling complete. {len(profiles)} professors scored.",
        f"{len(profiles)}/{len(state.professor_candidates)}",
    )
    await state.emit_agent_output("A4", {"profile_count": len(profiles), "top_score": profiles[0].match_score if profiles else 0})

    state.professor_profiles = profiles
    return state
