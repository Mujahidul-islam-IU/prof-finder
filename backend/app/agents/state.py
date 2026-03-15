"""
ProfFinder — LangGraph State
Shared state that flows through all agents in the graph.
"""

from __future__ import annotations
from typing import Optional, Annotated
from pydantic import BaseModel, Field
from app.models.schemas import (
    StudentProfile, CountryScore, ProfessorCandidate,
    ProfessorProfile, ProgramRequirements,
    SearchRequest, SSEProfessorEvent, SSEStatusEvent, SSEAgentOutputEvent,
)
import asyncio
import operator


class SearchState(BaseModel):
    """
    The shared state for the ProfFinder LangGraph.
    Each agent reads from and writes to this state.
    """

    # ── Inputs ───────────────────────────────────────────
    search_request: Optional[SearchRequest] = None
    cv_file_path: str = ""
    session_id: str = ""

    # ── A1 Output ────────────────────────────────────────
    student_profile: Optional[StudentProfile] = None

    # ── A2 Output ────────────────────────────────────────
    country_rankings: list[CountryScore] = Field(default_factory=list)

    # ── A3 Output ────────────────────────────────────────
    professor_candidates: list[ProfessorCandidate] = Field(default_factory=list)

    # ── A4 Output ────────────────────────────────────────
    professor_profiles: list[ProfessorProfile] = Field(default_factory=list)

    # ── A5 Output ────────────────────────────────────────
    verified_professors: list[ProfessorProfile] = Field(default_factory=list)
    program_requirements: list[ProgramRequirements] = Field(default_factory=list)

    # ── SSE Queue (for streaming to frontend) ────────────
    # This will be set externally to an asyncio.Queue
    sse_queue: Optional[object] = None  # asyncio.Queue, typed as object for Pydantic

    # ── Status tracking ──────────────────────────────────
    current_agent: str = ""
    errors: list[str] = Field(default_factory=list)
    completed: bool = False

    model_config = {"arbitrary_types_allowed": True}

    async def emit_status(self, agent: str, message: str, progress: str = ""):
        """Push a status update to the SSE queue."""
        if self.sse_queue:
            event = SSEStatusEvent(
                agent=agent,
                message=message,
                progress=progress,
            )
            await self.sse_queue.put(event.model_dump(mode='json'))

    async def emit_professor(self, professor: ProfessorProfile, requirements: Optional[ProgramRequirements], progress: str):
        """Push a completed professor result to the SSE queue."""
        if self.sse_queue:
            event = SSEProfessorEvent(
                professor=professor,
                requirements=requirements,
                progress=progress,
            )
            await self.sse_queue.put(event.model_dump(mode='json'))

    async def emit_agent_output(self, agent: str, data: dict):
        """Push agent-specific debug data to the SSE queue."""
        if self.sse_queue:
            event = SSEAgentOutputEvent(
                agent=agent,
                data=data,
            )
            await self.sse_queue.put(event.model_dump(mode='json'))
