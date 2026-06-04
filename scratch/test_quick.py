import sys
from pathlib import Path
import os
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

# Force offline mode for CrossEncoder
os.environ["GROQ_RERANKING_ENABLED"] = "False"
os.environ["GROQ_INTENT_EXTRACTION_ENABLED"] = "False"

from app.agent.scheme_matching import load_schemes, score_scheme, audit_eligibility, dump_model, filter_candidates, get_query_embedding, init_matcher
from app.agent.reranker import _cross_encoder, build_scheme_text
from eval.run_eval import TEST_CASES

init_matcher(eager_warm=True)

case = next(c for c in TEST_CASES if c["id"] == "fin_002")
ctx = case["user_context"]
query = ctx.get("problem_statement") or ""
# Expand kcc
query = re.sub(r'\bkcc\b', 'kcc kishan credit card', query, flags=re.IGNORECASE)

print(f"Expanded Query: '{query}'")

all_schemes = load_schemes()
scheme_id_to_index = {s.get("scheme_id"): i for i, s in enumerate(all_schemes)}
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
top_matches = scored_candidates[:10]

pairs = []
for cand in top_matches:
    raw = cand[2]
    combined = build_scheme_text(raw, ctx)
    pairs.append((query, combined))
    
scores = _cross_encoder.predict(pairs)

ce_ranked = []
for score, cand in zip(scores, top_matches):
    ce_ranked.append({
        "scheme_id": cand[2].get("scheme_id"),
        "name": cand[2].get("scheme_name"),
        "confidence": cand[1],
        "ce_score": float(score),
        "retrieval_score": cand[0]
    })
    
CONFIDENCE_RANK = {"HIGH": 0, "LIKELY": 1, "NEEDS_VERIFICATION": 2, "INELIGIBLE": 999}
ce_ranked.sort(key=lambda x: (CONFIDENCE_RANK.get(x["confidence"], 1), -x["ce_score"]))

print("\nCrossEncoder Rerank:")
for i, item in enumerate(ce_ranked):
    print(f"  Rank {i+1}: {item['scheme_id']} - CE Score: {item['ce_score']:.4f} - Retr: {item['retrieval_score']}")
