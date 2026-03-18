import asyncio
import sys
sys.path.insert(0, ".")

from app.agents.state import SearchState
from app.agents.deep_profiler import deep_profiler
from app.models.schemas import StudentProfile, SearchRequest, ProfessorCandidate, ResultTier

async def run_a4():
    print("Initializing A4 test...")
    state = SearchState(
        cv_file_path="mock.pdf",
        search_request=SearchRequest(
            target_field="Bioinformatics", 
            degree_type="MSc", 
            target_countries=["Canada"], 
            intake_sessions=["Fall 2026"], 
            is_international=True
        ),
        student_profile=StudentProfile(
            name="Test",
            tier="A",
            raw_text="mock",
            vector_id="nonexistent-for-test" # Might fail ChromaDB lookup?
        ),
        professor_candidates=[
            ProfessorCandidate(
                name="John E. Burke",
                university="University of Victoria",
                country="Canada",
                openalex_id="A5086921160",
                paper_count=0
            )
        ]
    )
    
    # We need to mock ChromaDB student collection lookup, or just let it fail and see
    try:
        res = await deep_profiler(state)
        print("Success! Profiles generated:", len(res.professor_profiles))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_a4())
