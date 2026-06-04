import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["GROQ_RERANKING_ENABLED"] = "False"
os.environ["PYTHONIOENCODING"] = "utf-8"

from app.agent.scheme_matching import match_schemes

def run_query(query: str):
    state = {
        "user_context": {
            "state": "Meghalaya",
            "occupation": "farmer",
            "problem_statement": query,
            "problem_category": "skills",
        },
        "case_context": {},
        "user_input": query,
        "matched_schemes": [],
        "response_to_user": "",
    }
    res = match_schemes(state)
    matches = res.get("matched_schemes", [])
    ids = [m.get("scheme_id") for m in matches]
    names = [m.get("scheme_name") for m in matches]
    print(f"\nQuery: '{query}'")
    print(f"Matched IDs: {ids}")
    print(f"Matched Names: {names}")

if __name__ == "__main__":
    run_query("agriculture training centre meghalaya")
    run_query("agriculture training center meghalaya")
