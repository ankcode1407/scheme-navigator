from __future__ import annotations

from langgraph.graph import StateGraph, END

from app.agent.state import AgentState
from app.agent.nodes import (
    detect_user_language,
    extract_context,
    check_completeness,
    match_schemes,
    ask_followup,
    format_results,
    translate_response,
)


def route_after_language_gate(state: AgentState) -> str:
    if state.get("stop_after_language_gate"):
        return "translate_response"
    return "extract_context"


def route_after_completeness_check(state: AgentState) -> str:
    if state.get("context_complete"):
        return "match_schemes"
    return "ask_followup"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("detect_user_language", detect_user_language)
    graph.add_node("extract_context", extract_context)
    graph.add_node("check_completeness", check_completeness)
    graph.add_node("match_schemes", match_schemes)
    graph.add_node("ask_followup", ask_followup)
    graph.add_node("format_results", format_results)
    graph.add_node("translate_response", translate_response)

    graph.set_entry_point("detect_user_language")

    graph.add_conditional_edges(
        "detect_user_language",
        route_after_language_gate,
        {
            "extract_context": "extract_context",
            "translate_response": "translate_response",
        },
    )

    graph.add_edge("extract_context", "check_completeness")

    graph.add_conditional_edges(
        "check_completeness",
        route_after_completeness_check,
        {
            "match_schemes": "match_schemes",
            "ask_followup": "ask_followup",
        },
    )

    graph.add_edge("match_schemes", "format_results")
    graph.add_edge("format_results", "translate_response")
    graph.add_edge("ask_followup", "translate_response")
    graph.add_edge("translate_response", END)

    return graph.compile()


agent = build_graph()