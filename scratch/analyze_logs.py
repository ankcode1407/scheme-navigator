import json
from pathlib import Path
import re

session_path = Path("data/sessions.json")
with session_path.open("r", encoding="utf-8") as f:
    sessions = json.load(f)

print(f"Total sessions in logs: {len(sessions)}")

queries = []
categories = {}
states = {}

for sid, sdata in sessions.items():
    history = sdata.get("conversation_history", [])
    ctx = sdata.get("user_context", {})
    
    # Extract user inputs
    user_inputs = [msg.get("content") for msg in history if msg.get("role") == "user" and msg.get("content")]
    
    prob_statement = ctx.get("problem_statement")
    prob_category = ctx.get("problem_category")
    state = ctx.get("state")
    occupation = ctx.get("occupation")
    
    # Track categories
    if prob_category:
        categories[prob_category] = categories.get(prob_category, 0) + 1
    if state:
        states[state] = states.get(state, 0) + 1
        
    if prob_statement:
        queries.append({
            "sid": sid,
            "problem": prob_statement,
            "category": prob_category,
            "state": state,
            "occupation": occupation,
            "inputs": user_inputs
        })

print(f"Total queries with problem statements: {len(queries)}")
print("\n--- PROBLEM CATEGORIES ---")
for k, v in sorted(categories.items(), key=lambda x: x[1], reverse=True):
    print(f"  {k}: {v}")

print("\n--- USER STATES ---")
for k, v in sorted(states.items(), key=lambda x: x[1], reverse=True):
    print(f"  {k}: {v}")

print("\n--- SAMPLE QUERIES ---")
for i, q in enumerate(queries[:30]):
    print(f"{i+1}. [{q['sid'][:8]}] State: {q['state']}, Occ: {q['occupation']}, Query: '{q['problem']}' (Inputs: {q['inputs']})")
