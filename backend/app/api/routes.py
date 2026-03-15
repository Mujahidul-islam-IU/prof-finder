"""
ProfFinder — API Routes
REST + SSE endpoints for the frontend.
"""

import os
import uuid
import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from app.config import get_settings
from app.models.schemas import (
    SearchRequest, MailDraftRequest, MailDraftResponse,
    SSECompleteEvent, DegreeType,
)
from app.agents.state import SearchState
from app.agents.graph import search_pipeline
from app.agents.mail_drafter import draft_cold_email
from app.services import supabase_client

router = APIRouter(prefix="/api", tags=["ProfFinder"])


@router.post("/search")
async def start_search(
    cv_file: UploadFile = File(...),
    target_field: str = Form(...),
    degree_type: str = Form(...),
    target_countries: str = Form(...),  # Comma-separated
    intake_sessions: str = Form("Fall 2026"),
    is_international: bool = Form(True),
    ielts_score: float = Form(None),
    gre_score: int = Form(None),
):
    """
    Start a professor search. Returns an SSE stream of results.
    The search pipeline runs all 5 agents sequentially, streaming results.
    """
    settings = get_settings()

    # ── Save uploaded CV ─────────────────────────────────
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_ext = os.path.splitext(cv_file.filename or "cv.pdf")[1]
    file_id = uuid.uuid4().hex[:12]
    file_path = os.path.abspath(os.path.join(settings.upload_dir, f"cv_{file_id}{file_ext}"))

    content = await cv_file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # ── Parse countries ──────────────────────────────────
    countries = [c.strip() for c in target_countries.split(",") if c.strip()]
    sessions = [s.strip() for s in intake_sessions.split(",") if s.strip()]

    # Map degree_type case-insensitively
    normalized_degree = degree_type.strip().lower()
    if normalized_degree == "phd":
        final_degree = DegreeType.PHD
    elif normalized_degree in ("msc", "ms"):
        final_degree = DegreeType.MSC if normalized_degree == "msc" else DegreeType.MS
    else:
        # Fallback to the original value if no match, 
        # which will trigger the standard Pydantic validation error if invalid.
        try:
            final_degree = DegreeType(degree_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid degree_type: {degree_type}. Expected: MSc, MS, or PhD")

    # ── Build search request ─────────────────────────────
    search_request = SearchRequest(
        target_field=target_field,
        degree_type=final_degree,
        target_countries=countries,
        intake_sessions=sessions,
        is_international=is_international,
        ielts_score=ielts_score,
        gre_score=gre_score,
    )

    # ── Create SSE stream ────────────────────────────────
    sse_queue = asyncio.Queue()

    async def run_pipeline():
        """Run the search pipeline and push results to SSE queue."""
        try:
            # Create session in Supabase
            session_id = ""
            try:
                session = supabase_client.create_session(
                    student_name="",  # Will be filled by A1
                    target_field=target_field,
                    degree_type=degree_type,
                    target_countries=countries,
                    tier="B",  # Will be updated by A1
                    gpa_normalized=None,
                    vector_id=None,
                )
                session_id = session.get("session_id", "")
            except Exception as e:
                print(f"[API] Session creation error: {e}")
                session_id = f"local_{uuid.uuid4().hex[:8]}"

            # Build initial state
            state = SearchState(
                search_request=search_request,
                cv_file_path=file_path,
                session_id=session_id,
                sse_queue=sse_queue,
            )

            # Run the LangGraph pipeline
            final_state = await search_pipeline.ainvoke(state)
            
            # Robustly extract verified professors list (handles dict or object)
            if isinstance(final_state, dict):
                verified_profs = final_state.get("verified_professors", [])
            else:
                verified_profs = getattr(final_state, "verified_professors", [])
            
            # Count tiers safely
            high_count = 0
            good_count = 0
            try_luck_count = 0
            
            for p in verified_profs:
                tier_val = ""
                # Handle object
                if hasattr(p, "result_tier") and p.result_tier:
                    tier_val = p.result_tier.value if hasattr(p.result_tier, "value") else str(p.result_tier)
                # Handle dict
                elif isinstance(p, dict) and p.get("result_tier"):
                    rt = p.get("result_tier")
                    if isinstance(rt, dict):
                        tier_val = rt.get("value", "")
                    else:
                        tier_val = str(rt)
                
                if tier_val == "High Chance":
                    high_count += 1
                elif tier_val == "Good Chance":
                    good_count += 1
                elif tier_val == "Try Your Luck":
                    try_luck_count += 1

            # Send completion event
            complete_event = SSECompleteEvent(
                total_professors=len(verified_profs),
                high_chance=high_count,
                good_chance=good_count,
                try_your_luck=try_luck_count,
            )
            await sse_queue.put(complete_event.model_dump(mode='json'))
            await sse_queue.put(None)  # Signal end of stream

        except Exception as e:
            error_event = {"event_type": "error", "message": str(e)}
            await sse_queue.put(error_event)
            await sse_queue.put(None)

    async def event_generator():
        """Generate SSE events from the queue."""
        # Start pipeline in background
        task = asyncio.create_task(run_pipeline())

        try:
            while True:
                event = await sse_queue.get()
                if event is None:
                    break
                yield {
                    "event": event.get("event_type", "message"),
                    "data": json.dumps(event),
                }
        except asyncio.CancelledError:
            task.cancel()
        finally:
            if not task.done():
                task.cancel()

    return EventSourceResponse(event_generator())


@router.post("/draft-email", response_model=MailDraftResponse)
async def draft_email(request: MailDraftRequest):
    """
    A6 — Generate a cold email draft.
    Triggered manually by user after reviewing professor results.
    NEVER sends the email — user copies and sends manually.
    """
    try:
        result = await draft_cold_email(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email drafting failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ProfFinder API",
    }
