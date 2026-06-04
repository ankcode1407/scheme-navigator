import sys
from pathlib import Path
import os

# Ensure we import from the project root directory
sys.path.insert(0, str(Path(__file__).parent.parent))

# Force offline mode for CrossEncoder during testing
os.environ["GROQ_RERANKING_ENABLED"] = "False"
os.environ["GROQ_INTENT_EXTRACTION_ENABLED"] = "False"

from app.agent.scheme_matching import COMMON_SCHEME_WORDS, audit_eligibility, match_schemes
from app.knowledge_base.scheme_loader import load_schemes, get_scheme_by_id

print("==========================================================")
print("VERIFICATION RUNNER FOR DETERMINISTIC PRECISION FIXES")
print("==========================================================\n")

# --------------------------------------------------------
# STEP 1: Verify COMMON_SCHEME_WORDS count and content
# --------------------------------------------------------
print("--- STEP 1: COMMON_SCHEME_WORDS COUNT & CONTENT ---")
print(f"COMMON_SCHEME_WORDS count: {len(COMMON_SCHEME_WORDS)}")

contains_list = ["scheme", "yojana", "national", "pradhan", "for", "of", "and"]
not_contains_list = ["gausevak", "biotechnology", "mahila", "fasal"]

all_contains_ok = True
print("Verifying expected words are in list:")
for w in contains_list:
    if w in COMMON_SCHEME_WORDS:
        print(f"  [PASS] Contains '{w}'")
    else:
        print(f"  [FAIL] Missing '{w}'")
        all_contains_ok = False

all_not_contains_ok = True
print("Verifying restricted words are NOT in list:")
for w in not_contains_list:
    if w not in COMMON_SCHEME_WORDS:
        print(f"  [PASS] Does NOT contain '{w}'")
    else:
        print(f"  [FAIL] Contains '{w}'")
        all_not_contains_ok = False

# --------------------------------------------------------
# STEP 2: Verify MMAPUY audit fires correctly
# --------------------------------------------------------
print("\n--- STEP 2: MMAPUY AUDIT VERIFICATION ---")
scheme = get_scheme_by_id("seh-tmdummapuy")
if not scheme:
    print("  [FAIL] Could not find scheme 'seh-tmdummapuy'")
else:
    eligibility_rules = scheme.get("eligibility", {})
    user_context = {"enrolled_programs": []}
    audit = audit_eligibility(eligibility_rules, user_context)
    print(f"Audit output for seh-tmdummapuy (no enrolled_programs): {audit}")
    
    # We should also run full match_schemes to see confidence and missing
    state = {
        "user_context": {"state": "Haryana", "enrolled_programs": []},
        "case_context": {},
        "user_input": "Scheme for Establishment of Hi-Tech and Mini Dairy Units under Mukhya Mantri Antyodaya Parivaar Utthan Yojana",
        "matched_schemes": []
    }
    res_state = match_schemes(state)
    target_match = None
    for m in res_state.get("matched_schemes", []):
        if m["scheme_id"] == "seh-tmdummapuy":
            target_match = m
            break
            
    if target_match:
        print(f"seh-tmdummapuy matched! Confidence: {target_match['confidence']}")
        print(f"Missing data: {target_match['missing_data']}")
        if target_match['confidence'] == "NEEDS_VERIFICATION" and any("Program enrollment: MMAPUY" in m for m in target_match['missing_data']):
            print("  [PASS] Confidence is NEEDS_VERIFICATION and missing contains 'Program enrollment: MMAPUY'")
        else:
            print("  [FAIL] Incorrect confidence or missing program enrollment list.")
    else:
        print("  [FAIL] seh-tmdummapuy not in matched schemes list.")

# --------------------------------------------------------
# STEP 4: Verify specific cases & sister-scheme clarification
# --------------------------------------------------------
print("\n--- STEP 4: TARGETED CASES AND SISTER-SCHEME CLARIFICATION ---")
# Case skill_003 user context
skill_003_ctx = {
    "state": "Meghalaya",
    "occupation": "farmer",
    "problem_statement": "agriculture training centre meghalaya",
    "problem_category": "skills",
}

state = {
    "user_context": skill_003_ctx,
    "case_context": {},
    "user_input": "agriculture training centre meghalaya",
    "matched_schemes": []
}

res_state = match_schemes(state)
clarification = res_state.get("training_centre_clarification")
print(f"Matched schemes for Meghalaya training query:")
for i, m in enumerate(res_state.get("matched_schemes", [])[:3]):
    print(f"  Rank {i+1}: {m['scheme_id']} - {m['scheme_name']}")
    
print(f"Clarification output: {clarification}")
if clarification == "Are you looking for basic vocational agriculture training (BATC) or advanced integrated agriculture training (IATC)?":
    print("  [PASS] Clarification question correctly fired for Meghalaya sister schemes!")
else:
    print("  [FAIL] Clarification did not fire or question mismatch.")

# --------------------------------------------------------
# STEP 5: Regression checks
# --------------------------------------------------------
print("\n--- STEP 5: REGRESSION CHECKS ---")
regression_queries = [
    {
        "name": "Crop Insurance Bihar",
        "query": "crop insurance Bihar farmer",
        "ctx": {"state": "Bihar", "occupation": "farmer", "problem_category": "agriculture"}
    },
    {
        "name": "SC Caste Scholarship",
        "query": "SC caste scholarship",
        "ctx": {"caste": "SC", "problem_category": "education"}
    },
    {
        "name": "Old Age Pension Tamil Nadu",
        "query": "old age pension Tamil Nadu",
        "ctx": {"state": "Tamil Nadu", "age": 65, "problem_category": "social_welfare"}
    },
    {
        "name": "Bakri Palan Uttarakhand",
        "query": "bakri palan Uttarakhand",
        "ctx": {"state": "Uttarakhand", "problem_category": "agriculture"}
    }
]

for q in regression_queries:
    state = {
        "user_context": q["ctx"],
        "case_context": {},
        "user_input": q["query"],
        "matched_schemes": []
    }
    res = match_schemes(state)
    print(f"Query: '{q['query']}'")
    for i, m in enumerate(res["matched_schemes"][:3]):
        print(f"  Rank {i+1}: {m['scheme_id']} - {m['scheme_name']} ({m['confidence']})")
    print("-" * 50)
