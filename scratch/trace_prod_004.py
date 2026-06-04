import sys
from pathlib import Path

# Allow importing from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.scheme_matching import score_scheme, init_matcher, filter_candidates
from app.knowledge_base.scheme_loader import load_schemes
import numpy as np

init_matcher(eager_warm=True)
all_schemes = load_schemes()
scheme_id_to_index = {s.get("scheme_id"): i for i, s in enumerate(all_schemes)}

from app.agent.scheme_matching import get_query_embedding, dump_model

user_context = {
    "occupation": "farmer",
    "problem_statement": "Farmer with 10000 loan",
    "problem_category": "agriculture",
    "income": 10000
}

target_ids = ["kcc", "pcardbif", "pcardsia", "financial-assistance-scheme", "kccp", "fafiskc"]

query_text = user_context.get("problem_statement")
query_emb = get_query_embedding(query_text)

candidates = filter_candidates(all_schemes)

for tid in target_ids:
    for c in candidates:
        raw = dump_model(c)
        if raw.get("scheme_id") == tid:
            idx = scheme_id_to_index.get(tid)
            score, reasons = score_scheme(raw, user_context, {}, query_emb, idx)
            print(f"\n==========================================")
            print(f"Scheme: [{tid}] {raw.get('scheme_name')}")
            print(f"  Final Score: {score}")
            print(f"  Reasons: {reasons}")
