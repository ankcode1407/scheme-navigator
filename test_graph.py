from app.agent.graph import agent
from app.agent.state import AgentState

def run_turn(user_input: str, existing_context: dict = {}) -> dict:
    state: AgentState = {
        "user_input": user_input,
        "conversation_history": [],
        "user_context": existing_context,
        "missing_fields": [],
        "context_complete": False,
        "followup_question": None,
        "matched_schemes": [],
        "response_to_user": None
    }
    result = agent.invoke(state)
    return result

# ── TEST 1: Incomplete input — should ask follow-up ──────────────────────────
print("TEST 1 — Incomplete input")
print("-" * 50)
result1 = run_turn("Main UP mein kisan hoon, 1.5 hectare zameen hai")
print("Response:", result1["response_to_user"])
print("Context so far:", result1["user_context"])

# ── TEST 2: Complete input — should return schemes ───────────────────────────
print("\nTEST 2 — Complete input")
print("-" * 50)
result2 = run_turn(
    "I am a farmer in UP with 1.5 hectares of land, I live in a rural village, "
    "I have Aadhaar and a bank account, my income is below poverty line"
)
print("Response:", result2["response_to_user"])

# ── TEST 3: Hindi input — should return Hindi response ───────────────────────
print("\nTEST 3 — Hindi input, Hindi response")
print("-" * 50)
result3 = run_turn(
    "Main UP ke ek gaon mein rehta hoon, kisan hoon, "
    "mere paas 1.5 hectare zameen hai, BPL card hai"
)
print("Language detected:", result3["user_language"])
print("Response:\n", result3["response_to_user"])