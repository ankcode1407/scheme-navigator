import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

# Force offline mode for CrossEncoder
os.environ["GROQ_RERANKING_ENABLED"] = "False"
os.environ["GROQ_INTENT_EXTRACTION_ENABLED"] = "False"

# We mock/configure RETRIEVAL_PROMOTION_FLOOR to 0 to see what happens before implementing the floor
os.environ["RETRIEVAL_PROMOTION_FLOOR"] = "0"

from app.agent.scheme_matching import load_schemes, score_scheme, audit_eligibility, dump_model, filter_candidates, get_query_embedding, init_matcher
from app.agent.reranker import rerank_local
from eval.run_eval import TEST_CASES

init_matcher(eager_warm=True)

all_schemes = load_schemes()
scheme_id_to_index = {s.get("scheme_id"): i for i, s in enumerate(all_schemes)}

def run_case_retrieval(case):
    ctx = case["user_context"]
    query = ctx.get("problem_statement") or ""
    query_emb = get_query_embedding(query)
    
    scored_candidates = []
    candidates = filter_candidates(all_schemes)
    for candidate in candidates:
        raw = dump_model(candidate)
        s_id = raw.get("scheme_id")
        s_idx = scheme_id_to_index.get(s_id)
        score, base_reasons = score_scheme(raw, ctx, {}, query_emb, s_idx)
        audit = audit_eligibility(raw.get("eligibility", {}), ctx)
        
        if score is None or audit["failed"]:
            confidence = "INELIGIBLE"
            score = -999
        elif audit["passed"] and not audit["missing"]:
            confidence = "HIGH"
            score += 5
        elif audit["missing"]:
            confidence = "NEEDS_VERIFICATION"
        else:
            confidence = "LIKELY" if score >= 4 else "NEEDS_VERIFICATION"
            
        raw_states = raw.get("state") or raw.get("eligibility", {}).get("state") or []
        if isinstance(raw_states, str):
            raw_states = [raw_states]
        scheme_states = [str(s).lower().strip() for s in raw_states if s]
        user_state = (ctx.get("state") or "").lower().strip()
        
        needs_state_verification = False
        if not user_state:
            is_restricted = scheme_states and not any(s == "all" for s in scheme_states)
            if is_restricted:
                needs_state_verification = True
                if "State" not in audit["missing"]:
                    audit["missing"].append("State")
                if confidence != "INELIGIBLE":
                    confidence = "NEEDS_VERIFICATION"
                    
        if score is not None and (score > -500 or confidence == "NEEDS_VERIFICATION"):
            scored_candidates.append((score, confidence, raw, base_reasons, audit, needs_state_verification))
            
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    return scored_candidates

# 1. Print health_004 candidates and their retrieval score distribution
health_004_case = next(c for c in TEST_CASES if c["id"] == "health_004")
health_004_candidates = run_case_retrieval(health_004_case)

print("=== health_004 Retrieval Score Distribution ===")
for cand in health_004_candidates:
    scheme_id = cand[2].get("scheme_id")
    name = cand[2].get("scheme_name")
    score = cand[0]
    print(f"  {scheme_id}: {score} ({name})")

# 2. Run analysis on all 60 cases to find correct scheme vs incorrectly promoted scheme (Rank 1)
print("\n=== Analysis on all 60 cases (without floor, i.e., floor=0) ===")
for case in TEST_CASES:
    expect_ids = case.get("expect_ids", [])
    if not expect_ids:
        continue
    
    candidates = run_case_retrieval(case)
    top_10 = candidates[:10]
    
    # Rerank local with floor=0
    reranked = rerank_local(case["user_context"].get("problem_statement") or "", case["user_context"], top_10)
    
    # Check what is Rank 1
    if not reranked:
        continue
        
    returned_rank_1_id = reranked[0][2].get("scheme_id")
    expected_rank_1_id = expect_ids[0]
    
    # Find expected rank in reranked
    expected_rank = None
    for idx, r in enumerate(reranked):
        if r[2].get("scheme_id") == expected_rank_1_id:
            expected_rank = idx + 1
            break
            
    if returned_rank_1_id != expected_rank_1_id:
        # Get retrieval score of Rank 1
        rank1_retr_score = next((c[0] for c in candidates if c[2].get("scheme_id") == returned_rank_1_id), None)
        expected_retr_score = next((c[0] for c in candidates if c[2].get("scheme_id") == expected_rank_1_id), None)
        
        print(f"Case {case['id']}: Wrong Rank 1! Returned: {returned_rank_1_id} (Retr score: {rank1_retr_score}), "
              f"Expected: {expected_rank_1_id} (Retr score: {expected_retr_score}, Actual rank: {expected_rank})")
