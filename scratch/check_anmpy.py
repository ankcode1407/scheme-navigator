import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.scheme_matching import score_scheme, audit_eligibility, filter_candidates, load_schemes, get_query_embedding, init_matcher, dump_model, find_exact_name_match
import numpy as np

init_matcher()

all_schemes = load_schemes()
scheme_id_to_index = {s.get("scheme_id"): i for i, s in enumerate(all_schemes)}

matching_ctx = {
    "state": "Arunachal Pradesh",
    "problem_statement": "Atma Nirbhar Matsya Palan Yojana loan/subsidy Arunachal Pradesh",
    "problem_category": "financial",
}
case_ctx = {}
query = "Atma Nirbhar Matsya Palan Yojana loan/subsidy Arunachal Pradesh"
query_emb = get_query_embedding(query)

candidates = filter_candidates(all_schemes)
scored_candidates = []

for c in candidates:
    raw = dump_model(c)
    scheme_id = raw.get("scheme_id")
    idx = scheme_id_to_index.get(scheme_id)
    score, reasons = score_scheme(raw, matching_ctx, case_ctx, query_emb, idx)
    audit = audit_eligibility(raw.get("eligibility", {}), matching_ctx)
    if score is not None and score > -500:
        confidence = "NEEDS_VERIFICATION"
        scored_candidates.append((score, confidence, raw, reasons, audit, False))

audit_candidates = []
for item in scored_candidates:
    score_val, conf_val, raw_val, base_reasons_val, audit_val, needs_state_verification_val = item
    audit_candidates.append({
        "confidence": conf_val,
        "name": raw_val.get("scheme_name") or raw_val.get("name") or "",
        "scheme_id": raw_val.get("scheme_id")
    })

matched_id = find_exact_name_match(query, audit_candidates)
print("Matched ID from find_exact_name_match:", matched_id)

for cand in audit_candidates:
    if cand["scheme_id"] == "anmpy":
        print("anmpy candidate dict in audit_candidates:", cand)
