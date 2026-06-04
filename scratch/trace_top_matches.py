import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["GROQ_RERANKING_ENABLED"] = "False"
os.environ["GROQ_INTENT_EXTRACTION_ENABLED"] = "False"

from app.agent.scheme_matching import load_schemes, filter_candidates, score_scheme, dump_model
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

from app.agent.scheme_matching import get_query_embedding, init_matcher
init_matcher(eager_warm=False)
query_emb = get_query_embedding(matching_query)

scheme_id_to_index = {s.get("scheme_id"): i for i, s in enumerate(all_schemes)}

for s_id in ["maws", "mgfs", "mpfs", "marvs", "batcs", "iatc"]:
    cand = [c for c in all_schemes if c.get("scheme_id") == s_id or c.get("id") == s_id][0]
    raw = dump_model(cand)
    idx = scheme_id_to_index.get(s_id)
    score, reasons = score_scheme(raw, ctx, case_ctx, query_emb, idx)
    print(f"\nScheme: {s_id} - Score: {score}")
    print(f"  Reasons: {reasons}")
    # Print semantic similarity value
    if query_emb is not None and idx is not None:
        from app.agent.scheme_matching import _EMBEDDINGS
        sim = float(np.dot(query_emb, _EMBEDDINGS[idx]))
        print(f"  Raw similarity: {sim}")
