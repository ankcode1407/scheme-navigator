import sys
from pathlib import Path
import os
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure offline mode is used for deterministic, fast diagnostics without rate limits
os.environ["GROQ_RERANKING_ENABLED"] = "False"
os.environ["PYTHONIOENCODING"] = "utf-8"

from app.agent.scheme_matching import match_schemes, score_scheme, filter_candidates, load_schemes, get_query_embedding, init_matcher, dump_model
from app.agent.reranker import rerank_local
from eval.run_eval import TEST_CASES

def get_detailed_diagnostics(case_id: str):
    case = [c for c in TEST_CASES if c["id"] == case_id][0]
    ctx = case["user_context"]
    query = ctx.get("problem_statement", "")
    
    # Run the standard matching pipeline to get intermediate states
    all_schemes = load_schemes()
    init_matcher(eager_warm=False)
    
    query_emb = get_query_embedding(query)
    candidates = filter_candidates(all_schemes)
    scored_candidates = []
    
    scheme_id_to_index = {s.get("scheme_id"): i for i, s in enumerate(all_schemes)}
    
    for candidate in candidates:
        raw = dump_model(candidate)
        scheme_id = raw.get("scheme_id")
        scheme_idx = scheme_id_to_index.get(scheme_id)
        
        score, base_reasons = score_scheme(raw, ctx, {}, query_emb, scheme_idx)
        if score is not None and score > -500:
            scored_candidates.append((score, "NEEDS_VERIFICATION", raw, base_reasons, {"passed":[], "failed":[], "missing":[]}, False))
            
    scored_candidates.sort(key=lambda item: item[0], reverse=True)
    top_10 = scored_candidates[:10]
    
    # 1. Retrieval top 5
    retrieval_top_5 = []
    for score, conf, raw, reasons, audit, state_verif in top_10[:5]:
        retrieval_top_5.append({
            "scheme_id": raw.get("scheme_id"),
            "name": raw.get("scheme_name"),
            "score": score
        })
        
    # 2. Reranker top 5
    reranked = rerank_local(query, top_10)
    reranked_top_5 = []
    for cand in reranked[:5]:
        raw = cand[2]
        reranked_top_5.append({
            "scheme_id": raw.get("scheme_id"),
            "name": raw.get("scheme_name")
        })
        
    return {
        "case_id": case_id,
        "query": query,
        "user_context": ctx,
        "retrieval_top_5": retrieval_top_5,
        "reranked_top_5": reranked_top_5,
        "expected_ids": case.get("expect_ids", [])
    }

def run_vague_query(query: str):
    state = {
        "user_context": {
            "problem_statement": query,
        },
        "case_context": {},
        "user_input": query,
        "matched_schemes": [],
        "response_to_user": "",
    }
    
    # We do a custom matching step to capture both retrieval top 5 and reranker top choice
    all_schemes = load_schemes()
    init_matcher(eager_warm=False)
    
    query_emb = get_query_embedding(query)
    candidates = filter_candidates(all_schemes)
    scored_candidates = []
    
    scheme_id_to_index = {s.get("scheme_id"): i for i, s in enumerate(all_schemes)}
    
    for candidate in candidates:
        raw = dump_model(candidate)
        scheme_id = raw.get("scheme_id")
        scheme_idx = scheme_id_to_index.get(scheme_id)
        
        score, base_reasons = score_scheme(raw, {"problem_statement": query}, {}, query_emb, scheme_idx)
        if score is not None and score > -500:
            scored_candidates.append((score, "NEEDS_VERIFICATION", raw, base_reasons, {"passed":[], "failed":[], "missing":[]}, False))
            
    scored_candidates.sort(key=lambda item: item[0], reverse=True)
    top_10 = scored_candidates[:10]
    
    retrieval_top_5 = []
    for score, conf, raw, reasons, audit, state_verif in top_10[:5]:
        retrieval_top_5.append({
            "scheme_id": raw.get("scheme_id"),
            "name": raw.get("scheme_name") or raw.get("name"),
            "score": score
        })
        
    reranked = rerank_local(query, top_10)
    reranker_choice = None
    if reranked:
        raw = reranked[0][2]
        reranker_choice = {
            "scheme_id": raw.get("scheme_id"),
            "name": raw.get("scheme_name") or raw.get("name")
        }
        
    return {
        "query": query,
        "retrieval_top_5": retrieval_top_5,
        "reranker_choice": reranker_choice
    }

def main():
    # Diagnostics for specific cases
    cases_to_diagnose = ["emp_001", "emp_003", "skill_001", "skill_002", "skill_003"]
    diagnostics = {}
    for cid in cases_to_diagnose:
        diagnostics[cid] = get_detailed_diagnostics(cid)
        
    print(json.dumps({"diagnostics": diagnostics}, indent=2))
    
    # Run vague queries
    vague_queries = [
        "need a job",
        "skill sikhna hai",
        "koi kaam chahiye",
        "training centre near me"
    ]
    
    vague_results = []
    for vq in vague_queries:
        vague_results.append(run_vague_query(vq))
        
    print(json.dumps({"vague_results": vague_results}, indent=2))

if __name__ == "__main__":
    main()
