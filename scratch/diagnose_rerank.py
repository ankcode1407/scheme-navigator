import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ["GROQ_RERANKING_ENABLED"] = "False"
os.environ["GROQ_INTENT_EXTRACTION_ENABLED"] = "False"

from app.agent.scheme_matching import match_schemes

ctx = {"state": "Tamil Nadu", "age": 65, "problem_category": "social_welfare"}
state = {
    "user_context": ctx,
    "case_context": {},
    "user_input": "old age pension Tamil Nadu",
    "matched_schemes": []
}

import app.agent.reranker
old_rerank_local = app.agent.reranker.rerank_local

def debug_rerank_local(query, user_context, candidates):
    res = old_rerank_local(query, user_context, candidates)
    print("\n--- Inside debug_rerank_local ---")
    print("Candidates sorted by rerank_local:")
    for idx, c in enumerate(res[:5]):
        # c is CandidateTuple
        raw = c[2]
        print(f"  Rank {idx+1}: {raw.get('scheme_id')} (Conf: {c[1]}, Score: {c[0]})")
    return res

app.agent.reranker.rerank_local = debug_rerank_local

match_schemes(state)
