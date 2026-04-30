from app.agent.state import AgentState
from app.agent.nodes import extract_context, check_completeness

# Simulate a user message
state: AgentState = {
    "user_input": "Main UP mein kisan hoon, mere paas 1.5 hectare zameen hai",
    "conversation_history": [],
    "user_context": {},
    "missing_fields": [],
    "context_complete": False,
    "followup_question": None,
    "matched_schemes": [],
    "response_to_user": None
}

# Run Node 1
state = extract_context(state)
print("After extraction:")
print(state["user_context"])

# Run Node 2
state = check_completeness(state)
print("\nContext complete?", state["context_complete"])
print("Missing fields:", state["missing_fields"])
print("Follow-up question:", state["followup_question"])