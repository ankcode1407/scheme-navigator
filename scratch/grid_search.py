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

from app.agent.scheme_matching import get_query_embedding, dump_model, match_schemes

# We will patch score_scheme dynamically or run a simulation.
# Wait, let's write a custom simulator for match_schemes using a custom multiplier.

def simulate_match(user_context, multiplier):
    # This simulates match_schemes with a specific unknown state multiplier.
    ctx = user_context
    case_ctx = {}
    query_text = ctx.get("problem_statement")
    query_emb = get_query_embedding(query_text) if query_text else None
    
    candidates = filter_candidates(all_schemes)
    scored_candidates = []
    
    for candidate in candidates:
        raw = dump_model(candidate)
        scheme_id = raw.get("scheme_id")
        scheme_idx = scheme_id_to_index.get(scheme_id)
        
        # Call score_scheme (which uses the current 0.7x penalty)
        # We can reconstruct it or reverse engineering it.
        # Wait, if user state is unknown and scheme is state-restricted, the current score_scheme applied 0.7x.
        # We can undo it and apply our custom multiplier!
        
        scheme_states = [str(s).lower().strip() for s in (raw.get("state") or raw.get("eligibility", {}).get("state") or [])]
        scheme_states = [s for s in scheme_states if s]
        user_state = (ctx.get("state") or "").lower().strip()
        
        is_restricted = scheme_states and not any(s == "all" for s in scheme_states)
        is_restricted_unknown = (not user_state) and is_restricted
        
        score, base_reasons = score_scheme(raw, ctx, case_ctx, query_emb, scheme_idx)
        
        # Undo 0.7x if it was restricted unknown
        if is_restricted_unknown and score is not None:
            # score = int(round(relevance_score * (1.0 + demographic_multiplier) * 0.7))
            # Let's re-calculate score with custom multiplier
            # Since we don't have relevance_score directly, we can do:
            score_before = int(round(score / 0.7)) if score != 0 else 0
            score = int(round(score_before * multiplier))
            
        from app.agent.scheme_matching import audit_eligibility
        audit = audit_eligibility(raw.get("eligibility", {}), ctx)
        
        if score is None or audit["failed"]:
            confidence = "INELIGIBLE"
        elif audit["passed"] and not audit["missing"]:
            confidence = "HIGH"
            score += 5
        elif audit["missing"]:
            confidence = "NEEDS_VERIFICATION"
        else:
            confidence = "LIKELY" if score >= 4 else "NEEDS_VERIFICATION"
            
        if not user_state and is_restricted:
            if "State" not in audit["missing"]:
                audit["missing"].append("State")
            if confidence != "INELIGIBLE":
                confidence = "NEEDS_VERIFICATION"
                
        if score is not None and (score > -500 or confidence == "NEEDS_VERIFICATION"):
            scored_candidates.append((score, confidence, raw))
            
    scored_candidates.sort(key=lambda item: item[0], reverse=True)
    return [c[2].get("scheme_id") for c in scored_candidates[:5]]

# Test cases
cases = [
    # prod_004
    {
        "id": "prod_004",
        "ctx": {
            "occupation": "farmer",
            "problem_statement": "Farmer with 10000 loan",
            "problem_category": "agriculture",
            "income": 10000
        },
        "expect_ids": ["kcc"],
        "reject_ids": ["pcardbif", "pcardsia"]
    },
    # prod_008
    {
        "id": "prod_008",
        "ctx": {
            "occupation": "farmer",
            "problem_statement": "Need agriculture or farming support",
            "problem_category": "agriculture",
        },
        "expect_ids": ["nmsa-radg"],
        "reject_ids": ["uadtas", "dspvsfwcplguj"]
    }
]

for mult in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75]:
    print(f"\n--- Testing multiplier: {mult} ---")
    for case in cases:
        top5 = simulate_match(case["ctx"], mult)
        hit = any(eid in top5 for eid in case["expect_ids"])
        leak = any(rid in top5 for rid in case["reject_ids"])
        status = "PASS" if (hit and not leak) else "FAIL"
        print(f"  Case {case['id']}: {status} | Top-5: {top5} (Expect: {case['expect_ids']}, Reject: {case['reject_ids']})")
