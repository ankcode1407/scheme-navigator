import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

# Force offline mode for CrossEncoder
os.environ["GROQ_RERANKING_ENABLED"] = "False"
os.environ["GROQ_INTENT_EXTRACTION_ENABLED"] = "False"

from app.agent.scheme_matching import load_schemes, match_schemes, COMMON_SCHEME_WORDS, find_exact_name_match, tokenize
from app.agent.state import AgentState

query = "interest subvention kcc gujarat"
user_context = {
    "state": "Gujarat",
    "occupation": "farmer",
    "problem_statement": query,
    "problem_category": "financial",
}

state = AgentState(
    user_context=user_context,
    case_context={},
    user_input=query,
    matched_schemes=[],
    is_low_confidence=False,
    training_centre_clarification=None
)

res = match_schemes(state)
matches = res.get("matched_schemes", [])

print("=== MATCHED SCHEMES FOR fin_002 ===")
for i, m in enumerate(matches):
    print(f"Rank {i+1}: {m['scheme_id']} - {m['scheme_name']} (Confidence: {m['confidence']})")

print("\n=== TRACING EXACT NAME MATCH PRE-EMPTION ===")
all_schemes = load_schemes()
audit_candidates = []
for s in all_schemes:
    # Just mock confidence as LIKELY or HIGH
    audit_candidates.append({
        "confidence": "LIKELY",
        "name": s.get("scheme_name") or s.get("name") or "",
        "scheme_id": s.get("scheme_id")
    })

query_tokens = tokenize(query)
print(f"Query: '{query}' -> tokens: {query_tokens}")
print(f"COMMON_SCHEME_WORDS: {sorted(list(COMMON_SCHEME_WORDS))}")

for cand in audit_candidates:
    name = cand["name"]
    name_tokens = tokenize(name)
    distinctive = name_tokens - COMMON_SCHEME_WORDS
    if not distinctive:
        continue
    overlap = query_tokens & distinctive
    ratio = len(overlap) / len(distinctive)
    if ratio >= 0.6:
        print(f"Match candidate: {cand['scheme_id']} - '{name}'")
        print(f"  Name tokens: {name_tokens}")
        print(f"  Distinctive: {distinctive}")
        print(f"  Overlap: {overlap}")
        print(f"  Ratio: {ratio:.4f}")
