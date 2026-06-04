import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.scheme_matching import match_schemes
from app.agent.state import AgentState

queries = [
    {
        "query": "crop insurance Bihar farmer",
        "ctx": {"state": "Bihar", "occupation": "farmer", "problem_category": "agriculture"}
    },
    {
        "query": "SC caste scholarship",
        "ctx": {"caste": "SC", "problem_category": "education"}
    },
    {
        "query": "old age pension Tamil Nadu farmer",
        "ctx": {"state": "Tamil Nadu", "age": 65, "occupation": "farmer", "problem_category": "social_welfare"}
    },
    {
        "query": "bakri palan Uttarakhand",
        "ctx": {"state": "Uttarakhand", "problem_category": "agriculture"}
    }
]

print("=== REGRESSION CHECKS ===")
for q in queries:
    state = {
        "user_context": q["ctx"],
        "case_context": {},
        "user_input": q["query"],
        "matched_schemes": []
    }
    res = match_schemes(state)
    print(f"\nQuery: '{q['query']}'")
    for i, m in enumerate(res["matched_schemes"][:3]):
        print(f"  Rank {i+1}: {m['scheme_id']} - {m['scheme_name']} ({m['confidence']})")
