import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

# Force offline mode for CrossEncoder
os.environ["GROQ_RERANKING_ENABLED"] = "False"
os.environ["GROQ_INTENT_EXTRACTION_ENABLED"] = "False"

from eval.run_eval import TEST_CASES, run_case
from app.agent.scheme_matching import load_schemes, score_scheme, audit_eligibility, dump_model, filter_candidates, get_query_embedding, init_matcher
import numpy as np

all_schemes = load_schemes()
schemes_lookup = {s.get("scheme_id"): s for s in all_schemes}
scheme_id_to_index = {s.get("scheme_id"): i for i, s in enumerate(all_schemes)}
init_matcher(eager_warm=False)

print("=== FINDING HIT@1 FAILURES ===")
for case in TEST_CASES:
    if not case.get("expect_ids"):
        continue
    
    res = run_case(case, verbose=False)
    hit_rank = res.get("hit_rank")
    if hit_rank != 1:
        print(f"\nCase ID: {case['id']} - Tag: {case['tag']} - Hit Rank: {hit_rank}")
        print(f"  Query: '{case['user_context'].get('problem_statement')}'")
        print(f"  User Context: {case['user_context']}")
        print(f"  Expected Rank 1: {case['expect_ids']}")
        print(f"  Returned Rank 1 (wrong scheme): {res['returned_ids'][0]} - Name: {res['returned_names'][0]}")
        
        # Trace retrieval scoring
        ctx = case["user_context"]
        query_text = ctx.get("problem_statement") or ""
        query_emb = get_query_embedding(query_text)
        
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
            
            # Check state verification
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
                scored_candidates.append((score, confidence, raw, base_reasons, audit))
        
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        print("  Retrieval Top 5 (scheme_id + name + score):")
        for i, item in enumerate(scored_candidates[:5]):
            print(f"    {i+1}: {item[2].get('scheme_id')} - Name: {item[2].get('scheme_name')} - Score: {item[0]} - Conf: {item[1]}")
            
        # Is expected in top 10?
        top10_ids = [x[2].get("scheme_id") for x in scored_candidates[:10]]
        expected_in_top10 = any(eid in top10_ids for eid in case["expect_ids"])
        print(f"  Is correct scheme in retrieval top 10? {expected_in_top10}")
        
        # Score delta
        wrong_id = res['returned_ids'][0]
        correct_id = case['expect_ids'][0]
        wrong_score = next((x[0] for x in scored_candidates if x[2].get("scheme_id") == wrong_id), None)
        correct_score = next((x[0] for x in scored_candidates if x[2].get("scheme_id") == correct_id), None)
        print(f"  Retrieval Scores -> Wrong: {wrong_score}, Correct: {correct_score}, Delta: {wrong_score - correct_score if wrong_score is not None and correct_score is not None else 'N/A'}")
