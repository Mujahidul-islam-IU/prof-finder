"""
ProfFinder — LangGraph DAG Orchestrator
Sequential pipeline: A1 → A2 → A3 → A4 → A5
A6 (Mail Drafter) is triggered separately via API endpoint.
Each agent is wrapped in fault-tolerant error handling.
"""

from langgraph.graph import StateGraph, END
from app.agents.state import SearchState
from app.agents.profile_analyzer import profile_analyzer
from app.agents.country_ranker import country_ranker
from app.agents.professor_discovery import professor_discovery
from app.agents.deep_profiler import deep_profiler
from app.agents.qc_verifier import qc_verifier


def _wrap_agent(agent_fn, agent_name: str):
    """
    Wrap an agent function in fault-tolerant error handling.
    If the agent crashes, the pipeline continues with partial state
    instead of failing entirely.
    """
    async def safe_agent(state):
        if isinstance(state, dict):
            state = SearchState.model_validate(state)
        try:
            return await agent_fn(state)
        except Exception as e:
            import traceback
            error_msg = f"{agent_name}: {str(e)}"
            print(f"[PIPELINE] Agent {agent_name} FAILED: {e}")
            traceback.print_exc()
            state.errors.append(error_msg)
            try:
                await state.emit_status(
                    agent_name,
                    f"Warning: {agent_name} failed. Error: {str(e)}",
                    "",
                )
            except Exception:
                pass
            return state  # Return partial state, don't crash pipeline

    safe_agent.__name__ = agent_fn.__name__
    return safe_agent


def build_search_graph() -> StateGraph:
    """
    Build the LangGraph DAG for the professor search pipeline.

    Flow:
        A1 (Profile Analyzer)
         │
         ▼
        A2 (Country Ranker)
         │
         ▼
        A3 (Professor Discovery)
         │
         ▼
        A4 (Deep Profiler + Scorer)  ← runs 30 profiles in parallel internally
         │
         ▼
        A5 (QC + Verifier)  ← streams each professor via SSE
         │
         ▼
        END
    """

    # Define the graph with SearchState
    graph = StateGraph(SearchState)

    # ── Add nodes (each wrapped in fault-tolerant handler) ─
    graph.add_node("profile_analyzer", _wrap_agent(profile_analyzer, "A1"))
    graph.add_node("country_ranker", _wrap_agent(country_ranker, "A2"))
    graph.add_node("professor_discovery", _wrap_agent(professor_discovery, "A3"))
    graph.add_node("deep_profiler", _wrap_agent(deep_profiler, "A4"))
    graph.add_node("qc_verifier", _wrap_agent(qc_verifier, "A5"))

    # ── Define edges (sequential pipeline) ───────────────
    graph.set_entry_point("profile_analyzer")
    graph.add_edge("profile_analyzer", "country_ranker")
    graph.add_edge("country_ranker", "professor_discovery")
    graph.add_edge("professor_discovery", "deep_profiler")
    graph.add_edge("deep_profiler", "qc_verifier")
    graph.add_edge("qc_verifier", END)

    return graph.compile()


# Singleton compiled graph
search_pipeline = build_search_graph()
