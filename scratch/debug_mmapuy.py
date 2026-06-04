import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["GROQ_RERANKING_ENABLED"] = "False"
os.environ["GROQ_INTENT_EXTRACTION_ENABLED"] = "False"

from app.agent.scheme_matching import match_schemes, load_schemes, filter_candidates, score_scheme, audit_eligibility, dump_model
import numpy as np

state = {
    "user_context": {"state": "Haryana", "enrolled_programs": []},
    "case_context": {},
    "user_input": "establishment of mini dairy units",
    "matched_schemes": []
}

res_state = match_schemes(state)
print("MATCHED SCHEMES COUNT:", len(res_state.get("matched_schemes", [])))
for i, m in enumerate(res_state.get("matched_schemes", [])):
    print(f"  Rank {i+1}: {m['scheme_id']} - {m['scheme_name']} ({m['confidence']})")

# Let's inspect the candidate directly
all_schemes = load_schemes()
cand = [c for c in all_schemes if c.get("scheme_id") == "seh-tmdummapuy" or c.get("id") == "seh-tmdummapuy"][0]
raw = dump_model(cand)

from app.agent.scheme_matching import get_query_embedding, init_matcher, filter_candidates
init_matcher(eager_warm=False)
query_emb = get_query_embedding("establishment of mini dairy units")
scheme_id_to_index = {s.get("scheme_id"): i for i, s in enumerate(all_schemes)}
idx = scheme_id_to_index.get("seh-tmdummapuy")

score, reasons = score_scheme(raw, state["user_context"], {}, query_emb, idx)
print("\nDirect Trace of seh-tmdummapuy:")
print(f"  Score: {score}")
print(f"  Reasons: {reasons}")

audit = audit_eligibility(raw.get("eligibility", {}), state["user_context"])
print(f"  Audit: {audit}")
