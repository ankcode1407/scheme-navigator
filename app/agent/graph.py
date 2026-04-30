from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.nodes import (
    detect_user_language,
    extract_context,
    check_completeness,
    match_schemes,
    translate_response,
)

def route_after_completeness_check(state: AgentState) -> str:
    if state["context_complete"]:
        return "match_schemes"
    else:
        return "ask_followup"

def ask_followup(state: AgentState) -> AgentState:
    state["response_to_user"] = state["followup_question"]
    return state

def format_results(state: AgentState) -> AgentState:
    schemes = state.get("matched_schemes", [])

    if not schemes:
        state["response_to_user"] = (
            "Based on the information you provided, I could not find "
            "any matching schemes. Could you tell me more about your "
            "specific situation or problem?"
        )
        return state

    lines = [f"I found {len(schemes)} scheme(s) you may be eligible for:\n"]

    for i, s in enumerate(schemes, 1):
        lines.append(f"{'='*50}")
        lines.append(f"{i}. {s['scheme_name']}")
        lines.append(f"   Confidence: {s['confidence']}")
        lines.append(f"   Why you qualify: {s['reason']}")
        lines.append(f"\n   Documents needed:")
        for doc in s.get("documents_required", []):
            lines.append(f"   - {doc}")
        lines.append(f"\n   What to do now:")
        for step in s.get("action_steps", []):
            lines.append(f"   → {step}")
        lines.append(f"\n   Portal: {s['portal']}")
        lines.append(f"   Helpline: {s['helpline']}\n")

    state["response_to_user"] = "\n".join(lines)
    return state

def build_graph():
    graph = StateGraph(AgentState)

    # Register all nodes
    graph.add_node("detect_user_language", detect_user_language)
    graph.add_node("extract_context",      extract_context)
    graph.add_node("check_completeness",   check_completeness)
    graph.add_node("match_schemes",        match_schemes)
    graph.add_node("ask_followup",         ask_followup)
    graph.add_node("format_results",       format_results)
    graph.add_node("translate_response",   translate_response)

    # Flow
    graph.set_entry_point("detect_user_language")
    graph.add_edge("detect_user_language", "extract_context")
    graph.add_edge("extract_context",      "check_completeness")

    graph.add_conditional_edges(
        "check_completeness",
        route_after_completeness_check,
        {
            "match_schemes": "match_schemes",
            "ask_followup":  "ask_followup",
        }
    )

    graph.add_edge("match_schemes",   "format_results")
    graph.add_edge("format_results",  "translate_response")
    graph.add_edge("translate_response", END)
    graph.add_edge("ask_followup",    "translate_response")

    return graph.compile()

agent = build_graph()