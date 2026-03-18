import asyncio
import sys
sys.path.insert(0, ".")

from app.agents.state import SearchState
from app.agents.professor_discovery import professor_discovery
from app.models.schemas import StudentProfile, SearchRequest, CountryScore, SearchPriority, ResultTier

async def run_a3():
    print("Initializing A3 test...")
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
            raw_text="mock"
        ),
        country_rankings=[
            CountryScore(country="Canada", overall_score=80, search_priority=SearchPriority.HIGH)
        ]
    )
    
    try:
        res = await professor_discovery(state)
        print("Success! Candidates found:", len(res.professor_candidates))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_a3())
