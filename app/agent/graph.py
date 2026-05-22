from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agent.nodes import (
    check_completeness,
    detect_user_language,
    extract_context,
    finalize_response,
)

from app.agent.response_formatting import format_results
from app.agent.scheme_matching import match_schemes
from app.agent.state import AgentState


def route_after_language_gate(state: AgentState) -> str:
    if state.get("stop_after_language_gate"):
        return "finalize_response"
    return "extract_context"


def route_after_completeness_check(state: AgentState) -> str:
    if state.get("context_complete"):
        return "match_schemes"
    return "ask_followup"


def ask_followup(state: AgentState) -> AgentState:
    question = state.get("followup_question")

    if not question:
        from app.agent.constants import get_problem_first_question

        question = get_problem_first_question(
            state.get("preferred_language", "en-IN")
        )

    state["response_to_user"] = question
    state["response_tts_text"] = question
    state["response_language"] = (
        state.get("preferred_language")
        or "en-IN"
    )
    state["response_source_language"] = (
        state.get("preferred_language")
        or "en-IN"
    )
    state["should_play_tts"] = True

    return state


workflow = StateGraph(AgentState)

workflow.add_node("detect_user_language", detect_user_language)
workflow.add_node("extract_context", extract_context)
workflow.add_node("check_completeness", check_completeness)
workflow.add_node("match_schemes", match_schemes)
workflow.add_node("ask_followup", ask_followup)
workflow.add_node("format_results", format_results)
workflow.add_node("finalize_response", finalize_response)

workflow.set_entry_point("detect_user_language")

workflow.add_conditional_edges(
    "detect_user_language",
    route_after_language_gate,
    {
        "extract_context": "extract_context",
        "finalize_response": "finalize_response",
    },
)

workflow.add_edge(
    "extract_context",
    "check_completeness",
)

workflow.add_conditional_edges(
    "check_completeness",
    route_after_completeness_check,
    {
        "match_schemes": "match_schemes",
        "ask_followup": "ask_followup",
    },
)

workflow.add_edge(
    "match_schemes",
    "format_results",
)

workflow.add_edge(
    "format_results",
    "finalize_response",
)

workflow.add_edge(
    "ask_followup",
    "finalize_response",
)

workflow.add_edge(
    "finalize_response",
    END,
)

graph = workflow.compile()