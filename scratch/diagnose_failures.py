import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.scheme_matching import score_scheme, audit_eligibility, filter_candidates, load_schemes, get_query_embedding, init_matcher, dump_model, normalize_caste
import numpy as np

init_matcher()

all_schemes = load_schemes()
scheme_id_to_index = {s.get("scheme_id"): i for i, s in enumerate(all_schemes)}

matching_ctx = {
    "state": "Uttarakhand",
    "occupation": "farmer",
    "age": 45,
    "problem_statement": "special pension for disabled agricultural workers uttarakhand teelu rauteli",
    "problem_category": "social_welfare",
}
case_ctx = {}
query = "special pension for disabled agricultural workers uttarakhand teelu rauteli"
query_emb = get_query_embedding(query)

candidates = filter_candidates(all_schemes)

dp_f_scheme = None
for c in candidates:
    raw = dump_model(c)
    if raw.get("scheme_id") == "dp-f":
        dp_f_scheme = raw
        break

if not dp_f_scheme:
    print("Could not find dp-f")
else:
    idx = scheme_id_to_index.get("dp-f")
    score, reasons = score_scheme(dp_f_scheme, matching_ctx, case_ctx, query_emb, idx)
    audit = audit_eligibility(dp_f_scheme.get("eligibility", {}), matching_ctx)
    print(f"=== dp-f Stats ===")
    print("Score:", score)
    print("Reasons:", reasons)
    print("Audit:", audit)
