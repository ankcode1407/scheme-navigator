import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["GROQ_RERANKING_ENABLED"] = "False"
os.environ["GROQ_INTENT_EXTRACTION_ENABLED"] = "False"

from app.agent.scheme_matching import match_schemes, load_schemes, filter_candidates, score_scheme, audit_eligibility, dump_model
from app.agent.clarification import detect_clarification_needed
import numpy as np

all_schemes = load_schemes()
ctx = {
    "state": "Meghalaya",
    "occupation": "farmer",
    "problem_statement": "agriculture training centre meghalaya",
    "problem_category": "skills",
}
case_ctx = {}
matching_query = "agriculture training centre meghalaya"

candidates = filter_candidates(all_schemes)
scheme_id_to_index = {s.get("scheme_id"): i for i, s in enumerate(all_schemes)}

from app.agent.scheme_matching import get_query_embedding, init_matcher
init_matcher(eager_warm=False)
query_emb = get_query_embedding(matching_query)

for s_id in ["batcs", "iatc"]:
    cand_scheme = [c for c in all_schemes if c.get("scheme_id") == s_id or c.get("id") == s_id][0]
    raw = dump_model(cand_scheme)
    scheme_idx = scheme_id_to_index.get(s_id)
    score, base_reasons = score_scheme(raw, ctx, case_ctx, query_emb, scheme_idx)
    print(f"\nScheme: {s_id}")
    print(f"  Score: {score}")
    print(f"  Reasons: {base_reasons}")
    # Let's inspect the keyword vs semantic components
    text = " ".join([
        raw.get("scheme_name", ""),
        raw.get("brief_description", ""),
        " ".join(raw.get("tags", []) or []),
        " ".join(raw.get("category", []) or [])
    ]).lower()
    print(f"  Text: {text[:200]}...")
