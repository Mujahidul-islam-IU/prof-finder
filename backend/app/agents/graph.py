"""
ProfFinder — LangGraph DAG Orchestrator
Sequential pipeline: A1 → A2 → A3 → A4 → A5
A6 (Mail Drafter) is triggered separately via API endpoint.
"""

from langgraph.graph import StateGraph, END
from app.agents.state import SearchState
from app.agents.profile_analyzer import profile_analyzer
from app.agents.country_ranker import country_ranker
from app.agents.professor_discovery import professor_discovery
from app.agents.deep_profiler import deep_profiler
from app.agents.qc_verifier import qc_verifier


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

    # ── Add nodes ────────────────────────────────────────
    graph.add_node("profile_analyzer", profile_analyzer)
    graph.add_node("country_ranker", country_ranker)
    graph.add_node("professor_discovery", professor_discovery)
    graph.add_node("deep_profiler", deep_profiler)
    graph.add_node("qc_verifier", qc_verifier)

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
