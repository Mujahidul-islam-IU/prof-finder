import asyncio
import json
from app.config import get_settings
from app.agents.state import SearchState
from app.models.schemas import SearchRequest, DegreeType
from app.agents.profile_analyzer import profile_analyzer
from app.agents.country_ranker import country_ranker
from app.agents.professor_discovery import professor_discovery
from app.agents.deep_profiler import deep_profiler

class MockEmitter:
    async def emit_status(self, agent, msg, prog):
        print(f"[{agent} STATUS] {msg} ({prog})")
    async def emit_agent_output(self, agent, out):
        print(f"[{agent} OUTPUT] {json.dumps(out)[:200]}")
    async def emit_professor(self, *args, **kwargs):
        pass

async def run_test():
    settings = get_settings()
    print("OpenAI key:", "Present" if settings.openai_api_key else "Missing")
    print("Groq key:", "Present" if settings.groq_api_key else "Missing")

    state = SearchState(
        session_id="test-123",
        search_request=SearchRequest(
            target_field="Bioinformatics",
            degree_type=DegreeType.PHD,
            target_countries=["Germany"],
            intake_sessions=["Fall 2026"]
        )
    )
    # Monkey patch emit
    state.emit_status = MockEmitter().emit_status
    state.emit_agent_output = MockEmitter().emit_agent_output
    state.emit_professor = MockEmitter().emit_professor

    # Mock CV text
    from app.services.cv_parser import parse_cv_with_llm
    print("--- Testing A1 Parse CV ---")
    cv_text = "Mujahidul Islam, BSc Bioinformatics, GPA 3.8, IELTS 7.5. thesis: Genomic analysis."
    profile = await parse_cv_with_llm(cv_text)
    state.student_profile = profile
    print("[A1 Profile Extracted]:", profile.name)

    print("--- Testing A1 Tier ---")
    state = await profile_analyzer(state)

    print("--- Testing A2 Rank ---")
    state = await country_ranker(state)

    print("--- Testing A3 Discovery ---")
    state = await professor_discovery(state)
    print(f"Found {len(state.professor_candidates)} candidates")

    print("--- Testing A4 Profiler ---")
    state = await deep_profiler(state)
    print(f"Scored {len(state.professor_profiles)} profiles")

if __name__ == "__main__":
    asyncio.run(run_test())
