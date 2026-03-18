"""Quick diagnostic: check how LangGraph handles state passing."""
import asyncio
import sys
sys.path.insert(0, ".")

from langgraph.graph import StateGraph, END
from app.agents.state import SearchState


async def test_node(state):
    """Simple test node that sets student_profile_name."""
    if isinstance(state, dict):
        print(f"[TEST] State is DICT with keys: {list(state.keys())}")
        state = SearchState.model_validate(state)
    else:
        print(f"[TEST] State is {type(state).__name__}")

    # Try returning as dict (LangGraph-compatible)
    return {"current_agent": "test_passed", "errors": []}


async def check_node(state):
    """Check what we received."""
    if isinstance(state, dict):
        print(f"[CHECK] State is DICT: current_agent={state.get('current_agent')}")
    else:
        print(f"[CHECK] State is {type(state).__name__}: current_agent={state.current_agent}")
    return {"completed": True}


async def main():
    graph = StateGraph(SearchState)
    graph.add_node("test", test_node)
    graph.add_node("check", check_node)
    graph.set_entry_point("test")
    graph.add_edge("test", "check")
    graph.add_edge("check", END)
    pipeline = graph.compile()

    initial = SearchState(cv_file_path="test.pdf")
    result = await pipeline.ainvoke(initial)
    print(f"\n[RESULT] Type: {type(result)}")
    if isinstance(result, dict):
        print(f"[RESULT] Keys: {list(result.keys())}")
        print(f"[RESULT] current_agent: {result.get('current_agent')}")
        print(f"[RESULT] completed: {result.get('completed')}")
    else:
        print(f"[RESULT] current_agent: {result.current_agent}")
        print(f"[RESULT] completed: {result.completed}")

asyncio.run(main())
